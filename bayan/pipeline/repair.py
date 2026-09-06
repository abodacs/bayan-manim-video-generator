"""Repair stage: classify, ask for a minimal fix, re-gate; capped at two.

The service wraps :class:`bayan.agents.roles.RepairAgent` for attempt
accounting, the policy short-circuit, and loop detection, and re-runs ALL
preflight gates on every candidate fix -- a repaired scene never skips
straight to the container.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from bayan.agents.roles import RepairAgent
from bayan.pipeline.models import DEFAULT_PROFILE, CodeAttemptEvidence, LessonPlan
from bayan.pipeline.preflight import gates_blocked, run_gates
from bayan.pipeline.records import evidence_fingerprint, write_stage_record
from bayan.renderer.errors import (
    POLICY_CATEGORIES,
    FailureClassification,
    classify_gate_results,
)

MAX_REPAIR_ATTEMPTS = 2
REPAIR_RECORD_FILENAME = "repair.json"


class CodeRepairProvider(Protocol):
    """The seam the repair stage reaches through for fixed scene code."""

    def repair_scene_code(
        self, *, code: str, classification: FailureClassification, plan: LessonPlan | None
    ) -> CodeAttemptEvidence: ...


@dataclass(frozen=True)
class RepairOutcome:
    """What the repair loop reports back to the spine."""

    status: str  # completed | exhausted | policy_blocked
    code: str | None
    attempts: int
    failure: str | None


class RepairService:
    """Classify a failure, request a minimal fix, and re-gate the result.

    At most ``max_attempts`` provider calls; policy categories go straight
    to the review packet; a provider fix identical to the input stops the
    loop (exhausted) instead of spinning.
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
        self.max_attempts = max_attempts
        self.record_filename = record_filename

    def repair(
        self,
        *,
        code: str,
        classification: FailureClassification | None,
        plan: LessonPlan | None,
        profile: str = DEFAULT_PROFILE,
    ) -> RepairOutcome:
        if classification is None:
            classification = FailureClassification(
                type="preflight",
                category="unknown",
                suggestion="Review the run manually; the failure could not be classified.",
            )
        if classification.category in POLICY_CATEGORIES:
            return self._policy_block(classification)

        agent = RepairAgent(run_dir=self.run_dir, max_attempts=self.max_attempts)
        attempts: list[dict[str, Any]] = []
        current_code = code
        for attempt_number in range(1, self.max_attempts + 1):
            loop_result = agent.run_with_loop_check(
                {"code": current_code, "category": classification.category}
            )
            if loop_result.get("status") == "loop_detected":
                return self._exhausted(
                    agent,
                    attempts,
                    f"Provider returned an identical fix (loop detected) after "
                    f"{attempt_number - 1} repair attempt(s).",
                )

            agent_result = agent.attempt_repair(
                {
                    "category": classification.category,
                    "message": classification.evidence or classification.suggestion,
                }
            )
            if agent_result["status"] == "policy_blocked":
                return self._policy_block(classification)
            if agent_result["status"] == "exhausted":
                return self._exhausted(
                    agent,
                    attempts,
                    f"Repair attempts exhausted after {attempts} attempt(s). "
                    f"Last failure: {classification.evidence or classification.suggestion}",
                )

            evidence = self.provider.repair_scene_code(
                code=current_code, classification=classification, plan=plan
            )
            gate_results = run_gates(evidence.code, profile=profile)
            gate_evidence = [asdict(result) for result in gate_results]
            attempts.append(
                {
                    "attempt": attempt_number,
                    "category": classification.category,
                    "evidence": classification.evidence or classification.suggestion,
                    "code_fingerprint": evidence_fingerprint(
                        evidence.model, "repair", evidence.code
                    ),
                    "gates_passed": not gates_blocked(gate_results),
                    "gate_results": gate_evidence,
                }
            )
            if not gates_blocked(gate_results):
                self._write_record("completed", attempts=attempts, failure=None)
                return RepairOutcome(
                    status="completed", code=evidence.code, attempts=attempt_number, failure=None
                )

            classification = classify_gate_results(gate_results) or classification
            current_code = evidence.code

        return self._exhausted(
            agent,
            attempts,
            f"Repair attempts exhausted after {len(attempts)} attempt(s). "
            f"Last failure: {classification.evidence or classification.suggestion}",
        )

    def _policy_block(self, classification: FailureClassification) -> RepairOutcome:
        agent = RepairAgent(run_dir=self.run_dir, max_attempts=self.max_attempts)
        agent_result = agent.attempt_repair(
            {"category": "security", "message": classification.evidence}
        )
        self._write_record(
            status="policy_blocked",
            attempts=[],
            failure=f"Policy violation ({classification.category}); human review required.",
            agent_status=agent_result["status"],
        )
        return RepairOutcome(
            status="policy_blocked",
            code=None,
            attempts=0,
            failure=f"Policy violation ({classification.category}); the scene requires "
            "human review. See review_packet.md.",
        )

    def _exhausted(
        self, agent: RepairAgent, attempts: list[dict[str, Any]], failure: str
    ) -> RepairOutcome:
        self._write_record("exhausted", attempts=attempts, failure=failure)
        return RepairOutcome(status="exhausted", code=None, attempts=len(attempts), failure=failure)

    def _write_record(
        self,
        status: str,
        *,
        attempts: list[dict[str, Any]],
        failure: str | None,
        agent_status: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "stage": "repair",
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "max_attempts": self.max_attempts,
            "attempts": attempts,
            "repairs_used": len(attempts),
            "gate_runs": len(attempts),
            "failure": failure,
            "last_evidence": (attempts[-1].get("evidence") or failure) if attempts else failure,
        }
        if agent_status:
            record["agent_status"] = agent_status
        write_stage_record(self.run_dir, record, self.record_filename)
