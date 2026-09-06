"""Typed contracts for the generate pipeline.

``LessonPlan`` is the new lesson-plan contract (topic, ordered beats with
Arabic on-screen text). It is deliberately distinct from the template-oriented
``ScenePlan`` in :mod:`bayan.planner.models`, which the ``bayan run``
orchestrator depends on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

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
class TokenUsage:
    """Token counts for one provider call, in the pipeline's own vocabulary.

    Deliberately neutral: the LLM client's usage type stays in the generator
    layer, and provider adapters map onto this at the seam, so the pipeline
    contracts do not depend on a model SDK (docs/ARCHITECTURE.md).
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class AttemptEvidence:
    """What one provider call produced, recorded verbatim by a stage service."""

    raw_response: str
    fingerprint: str
    model: str
    usage: TokenUsage | None


@dataclass(frozen=True)
class PlanAttemptEvidence(AttemptEvidence):
    """A planning call's outcome: the validated plan plus its audit trail."""

    plan: LessonPlan


@dataclass(frozen=True)
class CodeAttemptEvidence(AttemptEvidence):
    """A coding call's outcome: the produced code plus its audit trail."""

    code: str


class AttemptRecord(BaseModel):
    """One provider attempt as serialized into a stage record.

    Stages extend attempts with their own evidence keys (the repair loop
    adds the classification and the fixed code); ``extra="allow"`` keeps
    those keys verbatim through the typed record round-trip instead of
    dropping them at validation.
    """

    model_config = ConfigDict(extra="allow")

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
    def accepted(cls, attempt: int, evidence: AttemptEvidence, cost: float) -> AttemptRecord:
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


class CheckResult(BaseModel):
    """One critic check's machine-readable verdict."""

    check: str
    status: Literal["passed", "failed", "not_applicable", "not_implemented"]
    evidence: str
    suggestion: str | None = None
