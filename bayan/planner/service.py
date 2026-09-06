from __future__ import annotations

import json
from pathlib import Path

from bayan.planner.models import LessonSegment
from bayan.planner.provider import FakeProvider, ModelProvider
from bayan.utils.atomic_io import atomic_write_text


def run_planning_pipeline(
    input_path: Path,
    output_dir: Path,
    provider: ModelProvider | None = None,
    force: bool = False,
) -> None:
    """Reads input lesson, creates typed models, and outputs files atomically."""
    if provider is None:
        provider = FakeProvider()

    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise FileExistsError(
            f"Output directory '{output_dir}' already exists and is not empty. "
            "Use --force to overwrite."
        )

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found at '{input_path}'")

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON content in input file '{input_path}': {e}") from e

    raw_request = data.get("request", "")
    if not isinstance(raw_request, str) or not raw_request.strip():
        raise ValueError(f"Input file '{input_path}' must contain a non-empty 'request' field.")
    learning_objective = data.get("learning_objective", raw_request)

    segment = LessonSegment(
        learning_objective=learning_objective,
        language=data.get("language", "ar"),
        raw_request=raw_request,
    )

    plan = provider.generate_plan(segment)

    # Save outputs atomically
    atomic_write_text(
        output_dir / "lesson.json",
        segment.model_dump_json(indent=2, ensure_ascii=False) + "\n",
    )
    atomic_write_text(
        output_dir / "scene_plan.json",
        plan.model_dump_json(indent=2, ensure_ascii=False) + "\n",
    )
