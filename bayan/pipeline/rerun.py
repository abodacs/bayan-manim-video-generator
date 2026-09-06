"""Rerun (#84): replay a past run's deterministic stages with zero LLM calls.

The cached plan and scene code are reused verbatim; only the profile pass,
gates, render, and critic re-run, into a fresh run directory whose records
and summary carry ``rerun_of`` pointing at the source. No provider is ever
constructed -- the rerun path must not spend tokens or need an API key.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from bayan.pipeline.coder import SCENE_FILENAME
from bayan.pipeline.models import LessonPlan
from bayan.pipeline.planner import PLAN_FILENAME
from bayan.pipeline.spine import (
    RUN_SUMMARY_FILENAME,
    STAGES,
    GeneratePipeline,
    RunArtifacts,
    RunContext,
    RunInputs,
    RunResult,
    allocate_run_dir,
)
from bayan.utils.atomic_io import atomic_write_text

RERUN_STAGE_NAMES = ("profile", "gates", "render", "critic")


class RerunError(RuntimeError):
    """The requested run cannot be replayed from its cached artifacts."""


def _load_cached_run(source_dir: Path) -> tuple[LessonPlan, str, str]:
    """Read the cached plan, scene code, and prompt from a completed run."""
    plan_path = source_dir / PLAN_FILENAME
    scene_path = source_dir / SCENE_FILENAME
    missing = [path.name for path in (plan_path, scene_path) if not path.exists()]
    if missing:
        raise RerunError(
            f"Run '{source_dir.name}' has no cached {', '.join(missing)}; "
            "only runs produced by `bayan generate` can be rerun."
        )
    try:
        plan = LessonPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    except ValidationError as error:
        raise RerunError(
            f"The cached plan in '{source_dir.name}' is invalid ({error}); "
            "generate the lesson again with `bayan generate`."
        ) from None

    prompt = "rerun"
    summary_path = source_dir / RUN_SUMMARY_FILENAME
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            prompt = str(summary.get("prompt") or prompt)
        except (OSError, json.JSONDecodeError):
            prompt = "rerun"
    return plan, scene_path.read_text(encoding="utf-8"), prompt


def run_rerun(
    *,
    run_id: str,
    runs_root: Path,
    quality: str = "draft",
    vlm: bool = False,
) -> RunResult:
    """Replay the deterministic stages of a past run into a fresh run dir.

    Zero LLM calls: the cached plan and scene code are reused verbatim and
    only the profile pass, gates, render, and critic re-run. The new run's
    records and summary carry ``rerun_of`` pointing at the source.
    """
    source_dir = runs_root / run_id
    if not source_dir.is_dir():
        raise RerunError(
            f"Run '{run_id}' not found under {runs_root}. "
            "Generate a lesson first with `bayan generate`."
        )

    plan, scene_code, prompt = _load_cached_run(source_dir)
    run_dir = allocate_run_dir(runs_root, prompt)
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(run_dir / SCENE_FILENAME, scene_code)
    context = RunContext(
        inputs=RunInputs(
            run_dir=run_dir,
            prompt=prompt,
            profile=plan.profile,
            quality=quality,
            vlm=vlm,
            rerun_of=run_id,
        ),
        artifacts=RunArtifacts(plan=plan, scene_code=scene_code),
    )
    rerun_stages = tuple(stage for stage in STAGES if stage.name in RERUN_STAGE_NAMES)
    return GeneratePipeline(stages=rerun_stages).run(context)
