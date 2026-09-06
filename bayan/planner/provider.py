"""The lesson-plan provider seam: narrow protocol plus the real LLM adapter.

The deterministic offline double (:class:`bayan.testing.FakeProvider`) also
satisfies these protocols structurally, so the offline ``bayan run
--provider fake`` path and offline tests can inject it here. The dependency
direction is one-way: the legacy planner package may import pipeline
contracts, never the reverse.
"""

from __future__ import annotations

from typing import Protocol

from bayan.generator.llm_client import LLMClient, LLMUsage
from bayan.pipeline.models import LessonPlan, PlanAttemptEvidence, TokenUsage
from bayan.pipeline.records import evidence_fingerprint
from bayan.planner.models import LessonSegment, ScenePlan


class ModelProvider(Protocol):
    """Protocol defining the LLM provider seam for the orchestrator path.

    The generate pipeline reaches models through the narrower
    ``bayan.pipeline.provider.LessonPlanProvider`` protocol instead;
    ``bayan.testing.FakeProvider`` satisfies both.
    """

    def generate_plan(self, segment: LessonSegment) -> ScenePlan: ...


def as_token_usage(usage: LLMUsage | None) -> TokenUsage | None:
    """Map the client's usage onto the pipeline's neutral TokenUsage.

    The client's usage type belongs to the generator layer; provider adapters
    translate at the seam so pipeline evidence never carries it.
    """
    if usage is None:
        return None
    return TokenUsage(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )


LESSON_PLAN_SYSTEM_PROMPT = (
    "You plan Arabic math lessons for Egyptian grade-6 students as strict JSON. "
    "Reply with JSON only; it must match the requested schema. Rules:\n"
    "1. topic names the lesson concept concisely.\n"
    "2. Order 2 to 5 beats from concrete to abstract; each beat is one visual step.\n"
    "3. Every beat's on_screen_text is short Arabic that fits on one screen line.\n"
    "4. insight_move is one of: reveal, animate_count, compare, summarize.\n"
    "5. numbers lists the numeric values the beat works with.\n"
    "6. Never include commentary, markdown, or code outside the JSON."
)


class LessonPlanProvider(Protocol):
    """The seam the planning stage reaches through for lesson plans."""

    def generate_lesson_plan(self, prompt: str, profile: str) -> PlanAttemptEvidence: ...


class LLMPlanProvider:
    """Real provider adapter over the hardened client's structured-output mode."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def generate_lesson_plan(self, prompt: str, profile: str) -> PlanAttemptEvidence:
        plan: LessonPlan = self.client.generate_structured(
            system_prompt=LESSON_PLAN_SYSTEM_PROMPT,
            user_prompt=f"Lesson request: {prompt.strip()}\nLanguage profile: {profile}",
            response_model=LessonPlan,
        )
        return PlanAttemptEvidence(
            plan=plan,
            raw_response=self.client.last_raw_content or "",
            fingerprint=evidence_fingerprint(
                self.client.model, self.client.base_url, f"{profile}:{prompt.strip()}"
            ),
            model=self.client.model,
            usage=as_token_usage(self.client.last_usage),
        )
