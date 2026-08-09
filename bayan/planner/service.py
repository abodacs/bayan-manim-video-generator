import json
from pathlib import Path

from bayan.planner.models import LessonSegment
from bayan.planner.provider import FakeProvider, ModelProvider


def run_planning_pipeline(
    input_path: Path,
    output_dir: Path,
    provider: ModelProvider | None = None,
    force: bool = False,
) -> None:
    """Reads input lesson, creates typed LessonSegment and ScenePlan, and outputs files."""
    if provider is None:
        provider = FakeProvider()

    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise FileExistsError(
            f"Output directory '{output_dir}' already exists and is not empty. "
            "Use --force to overwrite."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    raw_request = data.get("request", "")
    learning_objective = data.get("learning_objective", raw_request)

    segment = LessonSegment(
        learning_objective=learning_objective,
        language=data.get("language", "ar"),
        raw_request=raw_request,
    )

    plan = provider.generate_plan(segment)

    # Save outputs
    lesson_out = output_dir / "lesson.json"
    scene_plan_out = output_dir / "scene_plan.json"

    with open(lesson_out, "w", encoding="utf-8") as f:
        f.write(segment.model_dump_json(indent=2, ensure_ascii=False))

    with open(scene_plan_out, "w", encoding="utf-8") as f:
        f.write(plan.model_dump_json(indent=2, ensure_ascii=False))
