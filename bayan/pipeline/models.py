"""Typed contracts for the generate pipeline.

``LessonPlan`` is the new lesson-plan contract (topic, ordered beats with
Arabic on-screen text). It is deliberately distinct from the template-oriented
``ScenePlan`` in :mod:`bayan.planner.models`, which the ``bayan run``
orchestrator depends on.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from bayan.generator.llm_client import LLMUsage

DEFAULT_PROFILE = "msa-western"


class LessonBeat(BaseModel):
    """One ordered step of a lesson, with the Arabic text shown on screen."""

    title: str = Field(min_length=1, description="Short beat label")
    on_screen_text: str = Field(
        min_length=1,
        description="Arabic text rendered on screen during this beat",
    )
    insight_move: str = Field(
        min_length=1,
        description="Pedagogic move for this beat, e.g. reveal, animate_count, compare",
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
