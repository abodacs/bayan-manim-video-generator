from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class LessonSegment(BaseModel):
    """Represents a validated lesson request segment."""

    learning_objective: str = Field(
        ..., description="Primary learning objective derived from request"
    )
    language: str = Field(default="ar", description="Language code (e.g. 'ar')")
    raw_request: str = Field(
        ..., description="Original natural-language input request"
    )


class RenderSettings(BaseModel):
    """Configuration settings required for scene rendering."""

    quality: str = Field(default="medium_quality")
    preview: bool = Field(default=False)


class ScenePlan(BaseModel):
    """Typed Scene plan output structure."""

    learning_objective: str
    language: str = "ar"
    visual_concept: str
    selected_template: str
    render_settings: RenderSettings = Field(default_factory=RenderSettings)
    provider_fingerprint: str
    extra_details: Optional[Dict[str, Any]] = None