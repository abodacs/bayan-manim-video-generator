from __future__ import annotations

import hashlib
from typing import Protocol

from bayan.planner.models import LessonSegment, PlanRenderPreferences, ScenePlan


class ModelProvider(Protocol):
    """Protocol defining the LLM provider seam."""

    def generate_plan(self, segment: LessonSegment) -> ScenePlan: ...


class FakeProvider:
    """Deterministic local provider for offline testing."""

    def __init__(self, model_name: str = "fake-model-v1") -> None:
        self.model_name = model_name

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
            selected_template="arabic_template",
            render_settings=PlanRenderPreferences(),
            provider_fingerprint=fingerprint,
        )
