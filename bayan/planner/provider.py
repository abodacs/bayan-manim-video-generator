from __future__ import annotations

import hashlib
import json
from typing import Protocol

from bayan.generator.llm_client import LLMUsage
from bayan.pipeline.models import (
    INSIGHT_MOVES,
    CodeAttemptEvidence,
    LessonBeat,
    LessonPlan,
    PlanAttemptEvidence,
)
from bayan.pipeline.records import evidence_fingerprint
from bayan.planner.models import LessonSegment, PlanRenderPreferences, ScenePlan
from bayan.renderer.errors import FailureClassification
from bayan.templates.catalogue import get_template_catalogue


class ModelProvider(Protocol):
    """Protocol defining the LLM provider seam for the orchestrator path.

    The generate pipeline reaches models through the narrower
    ``bayan.pipeline.provider.LessonPlanProvider`` protocol instead;
    ``FakeProvider`` below satisfies both.
    """

    def generate_plan(self, segment: LessonSegment) -> ScenePlan: ...


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
        fingerprint = evidence_fingerprint(self.model_name, "fake", f"{profile}:{prompt.strip()}")

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

    def generate_scene_code(
        self, *, plan: LessonPlan, system_prompt: str, user_prompt: str
    ) -> CodeAttemptEvidence:
        plan_hash = evidence_fingerprint(self.model_name, "fake", plan.model_dump_json())
        lines = [
            "from manim import *",
            "from bayan.utils.arabic_helper import ArabicText, rtl_glyphs",
            "",
            "class GeneratedScene(Scene):",
            "    def construct(self):",
        ]
        for index, beat in enumerate(plan.beats):
            lines.append(f"        message_{index} = ArabicText({beat.on_screen_text!r})")
            lines.append(f"        message_{index}.next_to(ORIGIN, UP)")
            lines.append(f"        self.play(Write(rtl_glyphs(message_{index})))")
        lines.append("        self.wait(1)")
        scene = "\n".join(lines) + "\n"
        prompt_tokens = 40 + int(plan_hash[0:3], 16) % 60
        completion_tokens = 150 + int(plan_hash[3:6], 16) % 250
        return CodeAttemptEvidence(
            code=scene,
            raw_response=scene,
            fingerprint=plan_hash,
            model=self.model_name,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    def repair_scene_code(
        self, *, code: str, classification: FailureClassification, plan: LessonPlan
    ) -> CodeAttemptEvidence:
        """Deterministic minimal fixes for the two repairable gate families."""
        if classification.category == "disallowed_import":
            allowed_prefixes = (
                "from manim",
                "from bayan.utils.arabic_helper",
                "import manim",
                "import math",
            )
            lines = [
                line
                for line in code.splitlines()
                if not (
                    line.startswith(("import ", "from ")) and not line.startswith(allowed_prefixes)
                )
            ]
            code = "\n".join(lines) + "\n"
        if classification.category == "arabic_layout":
            code = code.replace("Text(", "ArabicText(")
            if "arabic_helper" not in code:
                helper_import = (
                    "from manim import *\n"
                    "from bayan.utils.arabic_helper import ArabicText, rtl_glyphs\n"
                )
                code = code.replace("from manim import *\n", helper_import)
        return CodeAttemptEvidence(
            code=code,
            raw_response=code,
            fingerprint=evidence_fingerprint(self.model_name, "fake", f"repair:{code}"),
            model=self.model_name,
            usage=None,
        )
