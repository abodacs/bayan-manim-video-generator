from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LessonSegment(BaseModel):
    """Represents a validated lesson request segment."""

    learning_objective: str = Field(
        ..., description="Primary learning objective derived from request"
    )
    language: str = Field(default="ar", description="Language code (e.g. 'ar')")
    raw_request: str = Field(..., description="Original natural-language input request")


class PlanRenderPreferences(BaseModel):
    """Configuration settings required for scene rendering."""

    quality: str = Field(default="medium_quality")
    preview: bool = Field(default=False)


class ScenePlan(BaseModel):
    """Typed Scene plan output structure."""

    learning_objective: str
    language: str = "ar"
    visual_concept: str
    selected_template: str
    render_settings: PlanRenderPreferences = Field(default_factory=PlanRenderPreferences)
    provider_fingerprint: str
    extra_details: dict[str, Any] | None = None
