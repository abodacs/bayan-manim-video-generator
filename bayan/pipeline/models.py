"""Typed contracts for the generate pipeline.

``LessonPlan`` is the new lesson-plan contract (topic, ordered beats with
Arabic on-screen text). It is deliberately distinct from the template-oriented
``ScenePlan`` in :mod:`bayan.planner.models`, which the ``bayan run``
orchestrator depends on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

from pydantic import BaseModel, Field

from bayan.generator.llm_client import LLMUsage

DEFAULT_PROFILE = "msa-western"

InsightMove = Literal["reveal", "animate_count", "compare", "summarize"]

INSIGHT_MOVES: tuple[InsightMove, ...] = get_args(InsightMove)


class LessonBeat(BaseModel):
    """One ordered step of a lesson, with the Arabic text shown on screen."""

    title: str = Field(min_length=1, description="Short beat label")
    on_screen_text: str = Field(
        min_length=1,
        description="Arabic text rendered on screen during this beat",
    )
    insight_move: InsightMove = Field(
        description="Pedagogic move for this beat",
    )
    numbers: list[float] = Field(
        default_factory=list,
        description="Numeric values this beat works with",
    )


class LessonPlan(BaseModel):
    """Schema-validated lesson plan produced by the planning stage."""

    topic: str = Field(min_length=1)
    language: str = "ar"
    profile: str = DEFAULT_PROFILE
    beats: list[LessonBeat] = Field(min_length=1)


@dataclass(frozen=True)
class PlanAttemptEvidence:
    """What one provider call produced, recorded verbatim by the planner.

    ``raw_response``, ``usage``, and ``fingerprint`` feed the planning run
    record so every attempt stays auditable from disk alone.
    """

    plan: LessonPlan
    raw_response: str
    fingerprint: str
    model: str
    usage: LLMUsage | None


class AttemptRecord(BaseModel):
    """One provider attempt as serialized into the planning stage record."""

    attempt: int
    status: Literal["ok", "invalid_output"]
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_estimate_usd: float | None = None
    raw_response: str | None = None
    error: str | None = None

    @classmethod
    def accepted(cls, attempt: int, evidence: PlanAttemptEvidence, cost: float) -> AttemptRecord:
        usage = evidence.usage
        return cls(
            attempt=attempt,
            status="ok",
            model=evidence.model,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            cost_estimate_usd=round(cost, 6),
            raw_response=evidence.raw_response,
        )

    @classmethod
    def rejected(cls, attempt: int, error: str, raw_response: str | None = None) -> AttemptRecord:
        return cls(
            attempt=attempt,
            status="invalid_output",
            raw_response=raw_response,
            error=error,
        )
