"""Planning stage: Arabic prompt in, schema-validated LessonPlan out.

The service owns validation, bounded regeneration, cost estimation, and record
keeping behind one call. The run directory layout it writes is the pipeline
layout: ``plan.json`` at the run root, the stage record under ``records/``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bayan.generator.llm_client import LLMError
from bayan.pipeline.models import DEFAULT_PROFILE, LessonPlan
from bayan.pipeline.pricing import estimate_cost_usd
from bayan.planner.provider import ModelProvider
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
        provider: ModelProvider,
        run_dir: Path,
        *,
        max_attempts: int = MAX_PLANNING_ATTEMPTS,
    ) -> None:
        self.provider = provider
        self.run_dir = run_dir
        self.max_attempts = max_attempts

    def plan(self, prompt: str, *, profile: str = DEFAULT_PROFILE) -> LessonPlan:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        records_dir = self.run_dir / "records"
        records_dir.mkdir(exist_ok=True)
        record_path = records_dir / PLANNING_RECORD_FILENAME

        prompt_text = prompt.strip()
        if not prompt_text:
            failure = "Prompt is empty: describe the lesson in one Arabic sentence."
            self._write_record(
                record_path,
                status="failed",
                prompt=prompt_text,
                profile=profile,
                attempts=[],
                failure=failure,
            )
            raise PlanningError(failure, record_path)

        attempts: list[dict[str, Any]] = []
        for attempt_number in range(1, self.max_attempts + 1):
            try:
                evidence = self.provider.generate_lesson_plan(prompt_text, profile)
            except LLMError as error:
                attempts.append(
                    {
                        "attempt": attempt_number,
                        "status": "invalid_output",
                        "model": None,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                        "cost_estimate_usd": None,
                        "raw_response": None,
                        "error": str(error),
                    }
                )
                continue

            cost = estimate_cost_usd(evidence.model, evidence.usage)
            attempts.append(
                {
                    "attempt": attempt_number,
                    "status": "ok",
                    "model": evidence.model,
                    "prompt_tokens": evidence.usage.prompt_tokens if evidence.usage else None,
                    "completion_tokens": (
                        evidence.usage.completion_tokens if evidence.usage else None
                    ),
                    "total_tokens": evidence.usage.total_tokens if evidence.usage else None,
                    "cost_estimate_usd": round(cost, 6),
                    "raw_response": evidence.raw_response,
                    "error": None,
                }
            )
            self._write_plan(evidence.plan)
            self._write_record(
                record_path,
                status="completed",
                prompt=prompt_text,
                profile=profile,
                attempts=attempts,
                failure=None,
                provider_fingerprint=evidence.fingerprint,
            )
            return evidence.plan

        last_error = str(attempts[-1].get("error", "unknown"))
        failure = (
            f"Planning failed after {self.max_attempts} attempts: the provider never "
            f"returned a schema-valid lesson plan. Last error: {last_error}. "
            f"See {record_path} for every recorded attempt."
        )
        self._write_record(
            record_path,
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

    def _write_record(
        self,
        record_path: Path,
        *,
        status: str,
        prompt: str,
        profile: str,
        attempts: list[dict[str, Any]],
        failure: str | None,
        provider_fingerprint: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "stage": "planning",
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "prompt": prompt,
            "profile": profile,
            "max_attempts": self.max_attempts,
            "provider_fingerprint": provider_fingerprint,
            "attempts": attempts,
            "failure": failure,
            "plan": PLAN_FILENAME if status == "completed" else None,
        }
        atomic_write_text(
            record_path,
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        )
