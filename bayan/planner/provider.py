"""The lesson-plan provider seam for the orchestrator path.

The deterministic offline double (:class:`bayan.testing.FakeProvider`)
satisfies this protocol structurally, so the offline ``bayan run
--provider fake`` path and offline tests can inject it here. The generate
pipeline reaches models through the narrower
``bayan.pipeline.provider.LessonPlanProvider`` protocol plus its
:class:`bayan.pipeline.provider.LLMPlanProvider` adapter instead; the
dependency direction is one-way -- the legacy planner package may import
pipeline contracts, never the reverse.
"""

from __future__ import annotations

from typing import Protocol

from bayan.planner.models import LessonSegment, ScenePlan


class ModelProvider(Protocol):
    """Protocol defining the LLM provider seam for the orchestrator path.

    The generate pipeline reaches models through the narrower
    ``bayan.pipeline.provider.LessonPlanProvider`` protocol instead;
    ``bayan.testing.FakeProvider`` satisfies both.
    """

    def generate_plan(self, segment: LessonSegment) -> ScenePlan: ...
