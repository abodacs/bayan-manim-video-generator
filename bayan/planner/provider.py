from __future__ import annotations

import hashlib
import json
from typing import Protocol

from bayan.generator.llm_client import LLMClient, LLMUsage
from bayan.pipeline.models import LessonBeat, LessonPlan, PlanAttemptEvidence
from bayan.planner.models import LessonSegment, PlanRenderPreferences, ScenePlan
from bayan.templates.catalogue import get_template_catalogue

INSIGHT_MOVES = ("reveal", "animate_count", "compare", "summarize")

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


class ModelProvider(Protocol):
    """Protocol defining the LLM provider seam.

    ``generate_plan`` serves the template-oriented orchestrator path;
    ``generate_lesson_plan`` serves the generate pipeline. Both are the only
    ways services reach a model.
    """

    def generate_plan(self, segment: LessonSegment) -> ScenePlan: ...

    def generate_lesson_plan(self, prompt: str, profile: str) -> PlanAttemptEvidence: ...


class FakeProvider:
    """Deterministic local provider for offline testing.

    Lesson plans are derived from a hash of the prompt, so identical prompts
    always yield identical plans -- the golden prompt set depends on this.
    """

    def __init__(self, model_name: str = "fake-model-v1") -> None:
        self.model_name = model_name
        # Plans must select a template the render preflight will accept.
        self.default_template = sorted(get_template_catalogue())[0]

    def _generate_fingerprint(self, segment: LessonSegment) -> str:
        content = (
            f"{self.model_name}:{segment.learning_objective}:"
            f"{segment.language}:{segment.raw_request}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def generate_plan(self, segment: LessonSegment) -> ScenePlan:
        fingerprint = self._generate_fingerprint(segment)
        return ScenePlan(
            learning_objective=segment.learning_objective,
            language=segment.language,
            visual_concept=f"Visual explanation for: {segment.learning_objective}",
            selected_template=self.default_template,
            render_settings=PlanRenderPreferences(),
            provider_fingerprint=fingerprint,
        )

    def generate_lesson_plan(self, prompt: str, profile: str) -> PlanAttemptEvidence:
        fingerprint = hashlib.sha256(
            f"{self.model_name}:{profile}:{prompt.strip()}".encode()
        ).hexdigest()

        beat_count = 2 + int(fingerprint[0], 16) % 3
        dividend = int(fingerprint[1:3], 16) % 90 + 10
        divisor = int(fingerprint[3:5], 16) % 9 + 2
        quotient = dividend // divisor
        remainder = dividend % divisor

        beats = [
            LessonBeat(
                title=f"الخطوة {index + 1}",
                on_screen_text=f"نقسم {dividend} على {divisor}، الخطوة {index + 1}",
                insight_move=INSIGHT_MOVES[int(fingerprint[index], 16) % len(INSIGHT_MOVES)],
                numbers=[float(dividend), float(divisor)],
            )
            for index in range(beat_count)
        ]
        beats[-1] = LessonBeat(
            title=beats[-1].title,
            on_screen_text=f"الناتج {quotient} والباقي {remainder}",
            insight_move="summarize",
            numbers=[float(quotient), float(remainder)],
        )

        plan = LessonPlan(topic=prompt.strip(), profile=profile, beats=beats)
        prompt_tokens = 50 + int(fingerprint[5:8], 16) % 50
        completion_tokens = 200 + int(fingerprint[8:11], 16) % 300
        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        return PlanAttemptEvidence(
            plan=plan,
            raw_response=json.dumps(plan.model_dump(mode="json"), indent=2, ensure_ascii=False),
            fingerprint=fingerprint,
            model=self.model_name,
            usage=usage,
        )


class LLMPlanProvider:
    """Real provider adapter over the hardened client's structured-output mode."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def generate_lesson_plan(self, prompt: str, profile: str) -> PlanAttemptEvidence:
        plan = self.client.generate_structured(
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
