"""Repair stage: classify, ask for a minimal fix, hand back for re-gating.

One module owns the whole bounded repair policy: the attempt budget (max 2
provider calls per run), loop detection over request hashes, the
policy/security short-circuit to the human-review packet, and the single
repair record trail (``records/07-repair.json``). A round hands the
candidate fix back to the spine, which re-enters the pipeline at the
preflight gates: a repaired scene re-runs ALL gates exactly once, before
any container starts, and the spine keeps owning only sequencing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from bayan.generator.llm_client import LLMError
from bayan.pipeline.models import AttemptRecord, CodeAttemptEvidence, LessonPlan
from bayan.pipeline.pricing import estimate_cost_usd
from bayan.pipeline.records import StageStatus, stage_record, write_stage_record
from bayan.pipeline.taxonomy import POLICY_CATEGORIES, FailureClassification
from bayan.utils.atomic_io import atomic_write_text

MAX_REPAIR_ATTEMPTS = 2
REPAIR_RECORD_FILENAME = "repair.json"


class CodeRepairProvider(Protocol):
    """The seam the repair stage reaches through for fixed scene code."""

    def repair_scene_code(
        self, *, code: str, classification: FailureClassification, plan: LessonPlan | None
    ) -> CodeAttemptEvidence: ...


@dataclass(frozen=True)
class RepairOutcome:
    """What one repair round reports back to the spine.

    ``fixed`` carries the candidate code -- the spine re-enters at the gates
    stage, which re-runs every preflight gate before any container starts;
    ``exhausted`` and ``policy_blocked`` end the loop with a human-review
    pointer.
    """

    status: str  # fixed | exhausted | policy_blocked
    code: str | None
    failure: str | None


class RepairService:
    """The bounded repair loop: budget, loop detection, policy short-circuit.

    Provider calls never exceed ``max_attempts`` no matter how many rounds
    the spine runs, and a request identical to an earlier one stops the loop
    immediately -- the provider is repeating itself, so more attempts cannot
    help. Each attempt is one entry in the shared ``AttemptRecord`` shape
    extended with the repair evidence; every status the record can carry is
    ``attempted``, ``exhausted``, or ``policy_blocked``.
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
        self.attempts: list[dict[str, Any]] = []
        self._seen_requests: set[str] = set()

    @property
    def provider_calls(self) -> int:
        return len(self.attempts)

    def repair_round(
        self,
        *,
        code: str,
        classification: FailureClassification | None,
        plan: LessonPlan | None,
    ) -> RepairOutcome:
        """Run one classify -> fix round for the current failure.

        The round ends by handing the candidate fix to the spine; the
        re-gate happens in the pipeline's gates stage, the single place the
        gates run for a repaired scene.
        """
        if classification is None:
            classification = FailureClassification(
                type="preflight",
                category="unknown",
                suggestion="Review the run manually; the failure could not be classified.",
            )
        if classification.category in POLICY_CATEGORIES:
            return self._policy_block(classification)

        request_hash = self._hash_request(code, classification.category)
        if request_hash in self._seen_requests:
            return self._exhausted(
                "Provider kept returning an identical fix (loop detected); human review required."
            )
        self._seen_requests.add(request_hash)

        if len(self.attempts) >= self.max_attempts:
            return self._exhausted(
                "Repair attempts exhausted; the gates kept failing. Human review required."
            )

        try:
            evidence = self.provider.repair_scene_code(
                code=code, classification=classification, plan=plan
            )
        except LLMError as error:
            self.attempts.append(
                self._attempt_entry(
                    AttemptRecord.rejected(len(self.attempts) + 1, str(error)),
                    classification,
                    None,
                )
            )
            failure = f"Repair failed: the provider call did not return code ({error})."
            self._write_record("exhausted", failure=failure)
            return RepairOutcome(status="exhausted", code=None, failure=failure)

        self.attempts.append(
            self._attempt_entry(
                AttemptRecord.accepted(
                    len(self.attempts) + 1,
                    evidence,
                    estimate_cost_usd(evidence.model, evidence.usage),
                ),
                classification,
                evidence.code,
            )
        )
        self._write_record("attempted", failure=None)
        return RepairOutcome(status="fixed", code=evidence.code, failure=None)

    def _hash_request(self, code: str, category: str) -> str:
        payload = json.dumps({"code": code, "category": category}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _attempt_entry(
        self, attempt: AttemptRecord, classification: FailureClassification, code_after: str | None
    ) -> dict[str, Any]:
        """One attempt in the shared AttemptRecord shape plus repair evidence."""
        return {
            **attempt.model_dump(),
            "classification": asdict(classification),
            "evidence": classification.evidence or classification.suggestion,
            "code_after": code_after,
        }

    def _policy_block(self, classification: FailureClassification) -> RepairOutcome:
        """Security/policy findings never reach the LLM; they go to review."""
        message = classification.evidence or classification.suggestion
        self._write_review_packet(f"Policy violation ({classification.category}): {message}")
        failure = (
            f"Policy violation ({classification.category}); the scene requires "
            "human review. See review_packet.md."
        )
        self._write_record("policy_blocked", failure=failure)
        return RepairOutcome(status="policy_blocked", code=None, failure=failure)

    def _exhausted(self, failure: str) -> RepairOutcome:
        self._write_review_packet(failure)
        self._write_record("exhausted", failure=failure)
        return RepairOutcome(status="exhausted", code=None, failure=failure)

    def _write_review_packet(self, reason: str) -> None:
        atomic_write_text(
            self.run_dir / "review_packet.md",
            f"# Human Review Required\n\nReason: {reason}\n",
        )

    def _write_record(self, status: StageStatus, *, failure: str | None) -> None:
        record = stage_record(
            "repair",
            status,
            failure,
            max_attempts=self.max_attempts,
            attempts=self.attempts,
            repairs_used=len(self.attempts),
            last_evidence=(self.attempts[-1].get("evidence") or failure)
            if self.attempts
            else failure,
        )
        write_stage_record(self.run_dir, record, self.record_filename)
