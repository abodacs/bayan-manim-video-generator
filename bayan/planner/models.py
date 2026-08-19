from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RenderQuality = Literal["low_quality", "medium_quality", "high_quality", "highest_quality"]


class LessonSegment(BaseModel):
    """Represents a validated lesson request segment."""

    learning_objective: str = Field(
        ..., description="Primary learning objective derived from request"
    )
    language: str = Field(default="ar", description="Language code (e.g. 'ar')")
    raw_request: str = Field(
        ..., min_length=1, description="Original natural-language input request"
    )


class PlanRenderPreferences(BaseModel):
    """Configuration settings required for scene rendering."""

    quality: RenderQuality = Field(default="medium_quality")
    preview: bool = Field(default=False)


class ScenePlan(BaseModel):
    """Typed Scene plan output structure."""

    learning_objective: str
    language: str = "ar"
    visual_concept: str
    selected_template: str
    render_settings: PlanRenderPreferences = Field(default_factory=PlanRenderPreferences)
    provider_fingerprint: str
    extra_details: dict[str, object] | None = None
