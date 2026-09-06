"""Repair stage: classify, ask for a minimal fix, re-gate; capped at two.

The service wraps :class:`bayan.agents.roles.RepairAgent` -- which owns the
attempt budget (max 2), the policy short-circuit to the review packet, and
loop detection via input hashes -- so the cap is global to the run, not per
call. Every candidate fix re-runs ALL preflight gates here; a repaired scene
never skips straight to the container.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from bayan.agents.roles import RepairAgent
from bayan.generator.llm_client import LLMError
from bayan.pipeline.models import DEFAULT_PROFILE, CodeAttemptEvidence, LessonPlan
from bayan.pipeline.preflight import gates_blocked, run_gates
from bayan.pipeline.records import write_stage_record
from bayan.renderer.errors import POLICY_CATEGORIES, FailureClassification

MAX_REPAIR_ATTEMPTS = 2
REPAIR_RECORD_FILENAME = "repair.json"

_REFUSAL_MARKERS = ("safety", "refus")


class CodeRepairProvider(Protocol):
    """The seam the repair stage reaches through for fixed scene code."""

    def repair_scene_code(
        self, *, code: str, classification: FailureClassification, plan: LessonPlan | None
    ) -> CodeAttemptEvidence: ...


@dataclass(frozen=True)
class RepairOutcome:
    """What one repair round reports back to the spine.

    ``completed`` carries the fixed code; ``still_failing`` means the fix was
    applied but the gates rejected it (the spine may classify the new failure
    and spend another attempt); ``exhausted`` and ``policy_blocked`` end the
    loop with a human-review pointer.
    """

    status: str  # completed | still_failing | exhausted | policy_blocked
    code: str | None
    failure: str | None


class RepairService:
    """One repair round: classify-aware fix from the provider, then re-gate.

    The wrapped :class:`RepairAgent` owns the run-global attempt budget, so
    ``provider_calls`` never exceeds ``max_attempts`` no matter how many
    rounds the spine runs.
    """

    def __init__(
        self,
        provider: CodeRepairProvider,
        run_dir: Path,
        *,
        max_attempts: int = MAX_REPAIR_ATTEMPTS,
        record_filename: str = REPAIR_RECORD_FILENAME,
    ) -> None:
        self.provider = provider
        self.run_dir = run_dir
        self.record_filename = record_filename
        self.attempts: list[dict[str, Any]] = []
        self.agent = RepairAgent(run_dir=run_dir, max_attempts=max_attempts)

    @property
    def provider_calls(self) -> int:
        return len(self.attempts)

    def repair_round(
        self,
        *,
        code: str,
        classification: FailureClassification | None,
        plan: LessonPlan | None,
        profile: str = DEFAULT_PROFILE,
    ) -> RepairOutcome:
        """Run one classify -> fix -> re-gate round for the current failure."""
        if classification is None:
            classification = FailureClassification(
                type="preflight",
                category="unknown",
                suggestion="Review the run manually; the failure could not be classified.",
            )
        if classification.category in POLICY_CATEGORIES:
            return self._policy_block(classification)

        loop_result = self.agent.run_with_loop_check(
            {"code": code, "category": classification.category}
        )
        if loop_result.get("status") == "loop_detected":
            return self._exhausted(
                "Provider kept returning an identical fix (loop detected); human review required."
            )

        agent_result = self.agent.attempt_repair(
            {
                "category": classification.category,
                "message": classification.evidence or classification.suggestion,
            }
        )
        if agent_result["status"] == "policy_blocked":
            return self._policy_block(classification)
        if agent_result["status"] == "exhausted":
            return self._exhausted(
                "Repair attempts exhausted; the gates kept failing. Human review required."
            )

        try:
            evidence = self.provider.repair_scene_code(
                code=code, classification=classification, plan=plan
            )
        except LLMError as error:
            self._write_record(
                status="failed",
                failure=f"Repair failed: the provider call did not return code ({error}).",
            )
            return RepairOutcome(
                status="exhausted",
                code=None,
                failure=f"Repair failed: the provider call did not return code ({error}).",
            )
        gate_results = run_gates(evidence.code, profile=profile)
        self.attempts.append(
            {
                "attempt": agent_result["attempt"],
                "classification": asdict(classification),
                "evidence": classification.evidence or classification.suggestion,
                "code_after": evidence.code,
                "gates_passed": not gates_blocked(gate_results),
                "gate_results": [asdict(result) for result in gate_results],
            }
        )

        if gates_blocked(gate_results):
            self._write_record("attempted", failure="The gates rejected the repaired code.")
            return RepairOutcome(
                status="still_failing",
                code=evidence.code,
                failure="The gates rejected the repaired code.",
            )

        self._write_record("completed", failure=None)
        return RepairOutcome(status="completed", code=evidence.code, failure=None)

    def _policy_block(self, classification: FailureClassification) -> RepairOutcome:
        agent_result = self.agent.attempt_repair(
            {"category": "security", "message": classification.evidence}
        )
        self._write_record(
            status="policy_blocked",
            failure=f"Policy violation ({classification.category}); human review required.",
            agent_status=agent_result["status"],
        )
        return RepairOutcome(
            status="policy_blocked",
            code=None,
            failure=f"Policy violation ({classification.category}); the scene requires "
            "human review. See review_packet.md.",
        )

    def _exhausted(self, failure: str) -> RepairOutcome:
        self._write_record("exhausted", failure=failure)
        return RepairOutcome(status="exhausted", code=None, failure=failure)

    def _write_record(
        self,
        status: str,
        *,
        failure: str | None,
        agent_status: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "stage": "repair",
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "max_attempts": self.agent.max_attempts,
            "attempts": self.attempts,
            "repairs_used": len(self.attempts),
            "failure": failure,
            "last_evidence": (self.attempts[-1].get("evidence") or failure)
            if self.attempts
            else failure,
        }
        if agent_status:
            record["agent_status"] = agent_status
        write_stage_record(self.run_dir, record, self.record_filename)
