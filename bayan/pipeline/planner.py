"""Planning stage: Arabic prompt in, schema-validated LessonPlan out.

The service owns validation, bounded regeneration, cost estimation, and record
keeping behind one call. The run directory layout it writes is the pipeline
layout: ``plan.json`` at the run root, the stage record under ``records/``.
"""

from __future__ import annotations

from pathlib import Path

from bayan.generator.llm_client import LLMError, LLMResponseFormatError
from bayan.pipeline.models import (
    DEFAULT_PROFILE,
    AttemptRecord,
    LessonPlan,
)
from bayan.pipeline.pricing import estimate_cost_usd
from bayan.pipeline.provider import LessonPlanProvider
from bayan.pipeline.records import (
    RECORDS_DIRNAME,
    StageStatus,
    stage_record,
    write_stage_record,
)
from bayan.utils.atomic_io import atomic_write_text

MAX_PLANNING_ATTEMPTS = 3

PLAN_FILENAME = "plan.json"
PLANNING_RECORD_FILENAME = "planning.json"


class PlanningError(RuntimeError):
    """The provider never produced a schema-valid plan within the attempt cap."""

    def __init__(self, message: str, record_path: Path) -> None:
        super().__init__(message)
        self.record_path = record_path


class PlannerService:
    """Prompt in: a validated LessonPlan, plus plan.json and a planning record.

    Schema-invalid or failed provider calls are retried up to
    ``max_attempts`` total calls; every attempt is recorded with its raw
    response, token usage, and cost estimate. Exhaustion raises
    :class:`PlanningError` after writing a plain-English failure record.
    """

    def __init__(
        self,
        provider: LessonPlanProvider,
        run_dir: Path,
        *,
        max_attempts: int = MAX_PLANNING_ATTEMPTS,
        record_filename: str = PLANNING_RECORD_FILENAME,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self.provider = provider
        self.run_dir = run_dir
        self.max_attempts = max_attempts
        self.record_filename = record_filename

    def plan(self, prompt: str, *, profile: str = DEFAULT_PROFILE) -> LessonPlan:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        record_path = self.run_dir / RECORDS_DIRNAME / PLANNING_RECORD_FILENAME

        prompt_text = prompt.strip()
        if not prompt_text:
            failure = "Prompt is empty: describe the lesson in one Arabic sentence."
            self._record_path(
                status="failed",
                prompt=prompt_text,
                profile=profile,
                attempts=[],
                failure=failure,
            )
            raise PlanningError(failure, record_path)

        attempts: list[AttemptRecord] = []
        for attempt_number in range(1, self.max_attempts + 1):
            try:
                evidence = self.provider.generate_lesson_plan(prompt_text, profile)
            except LLMResponseFormatError as error:
                attempts.append(
                    AttemptRecord.rejected(attempt_number, str(error), error.raw_content)
                )
                continue
            except LLMError as error:
                attempts.append(AttemptRecord.rejected(attempt_number, str(error)))
                continue

            attempts.append(
                AttemptRecord.accepted(
                    attempt_number,
                    evidence,
                    estimate_cost_usd(evidence.model, evidence.usage),
                )
            )
            self._write_plan(evidence.plan)
            record_path = self._record_path(
                status="completed",
                prompt=prompt_text,
                profile=profile,
                attempts=attempts,
                failure=None,
                provider_fingerprint=evidence.fingerprint,
            )
            return evidence.plan

        last_error = str(attempts[-1].error)
        failure = (
            f"Planning failed after {self.max_attempts} attempts: the provider never "
            f"returned a schema-valid lesson plan. Last error: {last_error}. "
            f"See records/{PLANNING_RECORD_FILENAME} for every recorded attempt."
        )
        self._record_path(
            status="failed",
            prompt=prompt_text,
            profile=profile,
            attempts=attempts,
            failure=failure,
        )
        raise PlanningError(failure, record_path)

    def _write_plan(self, plan: LessonPlan) -> None:
        atomic_write_text(
            self.run_dir / PLAN_FILENAME,
            plan.model_dump_json(indent=2, ensure_ascii=False) + "\n",
        )

    def _record_path(
        self,
        *,
        status: StageStatus,
        prompt: str,
        profile: str,
        attempts: list[AttemptRecord],
        failure: str | None,
        provider_fingerprint: str | None = None,
    ) -> Path:
        record = stage_record(
            "planning",
            status,
            failure,
            prompt=prompt,
            profile=profile,
            max_attempts=self.max_attempts,
            provider_fingerprint=provider_fingerprint,
            attempts=[attempt.model_dump() for attempt in attempts],
            plan=PLAN_FILENAME if status == "completed" else None,
        )
        return write_stage_record(self.run_dir, record, self.record_filename)
