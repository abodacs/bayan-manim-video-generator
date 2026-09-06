"""The lesson-plan provider seam: narrow protocol plus the real LLM adapter.

``FakeProvider`` in :mod:`bayan.planner.provider` also satisfies this protocol
structurally, so offline tests can inject it here. The dependency direction is
one-way: the legacy planner package may import pipeline contracts, never the
reverse.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from bayan.generator.llm_client import LLMClient
from bayan.pipeline.models import LessonPlan, PlanAttemptEvidence

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
        fingerprint = hashlib.sha256(
            f"{self.client.model}:{self.client.base_url}:{profile}:{prompt.strip()}".encode()
        ).hexdigest()
        return PlanAttemptEvidence(
            plan=plan,
            raw_response=self.client.last_raw_content or "",
            fingerprint=fingerprint,
            model=self.client.model,
            usage=self.client.last_usage,
        )
