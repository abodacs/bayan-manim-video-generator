import hashlib
from typing import Protocol

from bayan.planner.models import LessonSegment, RenderSettings, ScenePlan


class ModelProvider(Protocol):
    """Protocol defining the LLM provider seam."""

    def generate_plan(self, segment: LessonSegment) -> ScenePlan: ...


class FakeProvider:
    """Deterministic local provider for offline testing."""

    def __init__(self, model_name: str = "fake-model-v1") -> None:
        self.model_name = model_name

    def _generate_fingerprint(self, payload: str) -> str:
        content = f"{self.model_name}:{payload}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def generate_plan(self, segment: LessonSegment) -> ScenePlan:
        fingerprint = self._generate_fingerprint(segment.raw_request)
        return ScenePlan(
            learning_objective=segment.learning_objective,
            language=segment.language,
            visual_concept=f"Visual explanation for: {segment.learning_objective}",
            selected_template="default_arabic_template",
            render_settings=RenderSettings(),
            provider_fingerprint=fingerprint,
        )
