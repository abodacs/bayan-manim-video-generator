"""The generate pipeline spine: serial stages into a fresh ``runs/<id>/``.

Stages are a data-driven registry: each takes a :class:`RunContext` and its
own :class:`Stage`, does its work through a stage service (or the isolated
renderer), persists exactly one order-prefixed JSON record under
``records/``, and returns a :class:`StageOutcome`. The spine only sequences,
stops at the first failure, and writes ``run.json``. Later sub-issues append
stages to the registry without reworking the spine.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from bayan.pipeline.coder import CoderService, CodingError, SceneCodeProvider
from bayan.pipeline.models import LessonPlan
from bayan.pipeline.planner import PlannerService, PlanningError
from bayan.pipeline.preflight import gates_blocked, run_gates
from bayan.pipeline.provider import LessonPlanProvider
from bayan.pipeline.records import RECORDS_DIRNAME, write_stage_record
from bayan.renderer.executor import RenderError, render_scene_code
from bayan.utils.atomic_io import atomic_write_text

DRAFT_FILENAME = "draft.mp4"
PREVIEW_FILENAME = "preview.png"
RUN_SUMMARY_FILENAME = "run.json"

PLAN_RECORD_FILENAME = "01-plan.json"
PROFILE_RECORD_FILENAME = "02-profile.json"
CODE_RECORD_FILENAME = "03-code.json"
GATES_RECORD_FILENAME = "04-gates.json"
RENDER_RECORD_FILENAME = "05-render.json"


class LanguageProfile(StrEnum):
    """Language profiles a generate run can target."""

    msa_western = "msa-western"
    msa_arabic_indic = "msa-arabic-indic"
    egyptian = "egyptian"


KNOWN_PROFILES: tuple[str, ...] = tuple(profile.value for profile in LanguageProfile)


def make_run_id(prompt: str, *, now: datetime | None = None) -> str:
    """Build a sortable run id: UTC timestamp plus a short prompt hash."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%MZ")
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
    return f"{stamp}-{digest}"


def allocate_run_dir(runs_root: Path, prompt: str, *, now: datetime | None = None) -> Path:
    """Pick a fresh, format-preserving run directory for this prompt.

    Same-prompt runs in one timestamp second keep the id shape by salting the
    hash instead of appending a suffix, so ids stay sortable everywhere.
    """
    attempt = 0
    while True:
        candidate = prompt if attempt == 0 else f"{prompt}:{attempt}"
        run_dir = runs_root / make_run_id(candidate, now=now)
        if not run_dir.exists():
            return run_dir
        attempt += 1


@dataclass
class RunContext:
    """State one generate run carries through its stages."""

    run_dir: Path
    prompt: str
    profile: str
    quality: str
    planner: LessonPlanProvider
    coder: SceneCodeProvider
    plan: LessonPlan | None = None
    scene_code: str | None = None


@dataclass(frozen=True)
class StageOutcome:
    """What a stage reports back to the spine."""

    stage: str
    status: str
    failure: str | None = None


@dataclass(frozen=True)
class Stage:
    """One ordered pipeline step."""

    name: str
    record_filename: str
    run: Callable[[RunContext, Stage], StageOutcome]


@dataclass(frozen=True)
class RunResult:
    """What the spine reports back to the CLI."""

    run_id: str
    run_dir: Path
    status: str
    failure: str | None
    total_cost_estimate_usd: float


def _stage_record(
    stage: str,
    status: str,
    failure: str | None = None,
    **evidence: Any,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "failure": failure,
        **evidence,
    }


def _failed(context: RunContext, stage: Stage, failure: str, **evidence: Any) -> StageOutcome:
    write_stage_record(
        context.run_dir,
        _stage_record(stage.name, "failed", failure, **evidence),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="failed", failure=failure)


def run_plan_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Turn the prompt into a validated LessonPlan via the planning service."""
    service = PlannerService(
        provider=context.planner,
        run_dir=context.run_dir,
        record_filename=stage.record_filename,
    )
    try:
        context.plan = service.plan(context.prompt, profile=context.profile)
    except PlanningError as error:
        return StageOutcome(stage=stage.name, status="failed", failure=str(error))
    return StageOutcome(stage=stage.name, status="completed")


def run_profile_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Apply the language-profile normalization hook.

    The profile name is validated and applied as-is today; the
    language-profiles sub-issue replaces this stage's internals without
    changing the seam.
    """
    if context.profile not in KNOWN_PROFILES:
        return _failed(
            context,
            stage,
            f"Unknown language profile {context.profile!r}. "
            f"Known profiles: {', '.join(KNOWN_PROFILES)}.",
        )
    write_stage_record(
        context.run_dir,
        _stage_record(stage.name, "completed", profile=context.profile),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


def run_code_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Turn the validated plan into scene code via the coding service."""
    # The spine stops at the first failure, so the plan stage always ran.
    assert context.plan is not None
    service = CoderService(
        provider=context.coder,
        run_dir=context.run_dir,
        record_filename=stage.record_filename,
    )
    try:
        context.scene_code = service.code(context.plan, profile=context.profile)
    except CodingError as error:
        return StageOutcome(stage=stage.name, status="failed", failure=str(error))
    return StageOutcome(stage=stage.name, status="completed")


def run_gates_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Statically gate the scene code; any failed gate blocks the render."""
    # The spine stops at the first failure, so the code stage always ran.
    assert context.scene_code is not None
    results = run_gates(context.scene_code, profile=context.profile)
    gate_evidence = [asdict(result) for result in results]
    if gates_blocked(results):
        failure = "; ".join(
            f"{result.gate} (line {result.line}): {result.suggestion}"
            for result in results
            if result.status != "passed"
        )
        write_stage_record(
            context.run_dir,
            _stage_record(stage.name, "failed", failure, gates=gate_evidence),
            stage.record_filename,
        )
        return StageOutcome(stage=stage.name, status="failed", failure=failure)
    write_stage_record(
        context.run_dir,
        _stage_record(stage.name, "completed", gates=gate_evidence),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


def run_render_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Render the scene code in the isolated container worker."""
    # The spine stops at the first failure, so the code stage always ran.
    assert context.scene_code is not None
    try:
        render_scene_code(
            code_content=context.scene_code,
            output_path=context.run_dir / DRAFT_FILENAME,
            scene_class_name="GeneratedScene",
            preview_path=context.run_dir / PREVIEW_FILENAME,
            quality=context.quality,
        )
    except RenderError as error:
        return _failed(context, stage, str(error))
    write_stage_record(
        context.run_dir,
        _stage_record(
            stage.name,
            "completed",
            quality=context.quality,
            draft=DRAFT_FILENAME,
            preview=PREVIEW_FILENAME,
        ),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


STAGES: tuple[Stage, ...] = (
    Stage("plan", PLAN_RECORD_FILENAME, run_plan_stage),
    Stage("profile", PROFILE_RECORD_FILENAME, run_profile_stage),
    Stage("code", CODE_RECORD_FILENAME, run_code_stage),
    Stage("gates", GATES_RECORD_FILENAME, run_gates_stage),
    Stage("render", RENDER_RECORD_FILENAME, run_render_stage),
)


class GeneratePipeline:
    """Sequence stages into a run directory; the first failure stops the run."""

    def __init__(self, stages: tuple[Stage, ...] = STAGES) -> None:
        self.stages = stages

    def run(self, context: RunContext) -> RunResult:
        context.run_dir.mkdir(parents=True, exist_ok=True)

        stage_statuses: dict[str, str] = {}
        failure: str | None = None
        for stage in self.stages:
            outcome = stage.run(context, stage)
            stage_statuses[outcome.stage] = outcome.status
            if outcome.status != "completed":
                failure = outcome.failure
                break

        status = "completed" if failure is None else "failed"
        total_cost = _total_cost_estimate(context.run_dir)
        summary: dict[str, Any] = {
            "run_id": context.run_dir.name,
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "prompt": context.prompt,
            "profile": context.profile,
            "quality": context.quality,
            "model": _first_model(context.run_dir),
            "total_cost_estimate_usd": total_cost,
            "stages": stage_statuses,
            "failure": failure,
        }
        atomic_write_text(
            context.run_dir / RUN_SUMMARY_FILENAME,
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        )
        return RunResult(
            run_id=context.run_dir.name,
            run_dir=context.run_dir,
            status=status,
            failure=failure,
            total_cost_estimate_usd=total_cost,
        )


def _iter_stage_records(run_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed stage records in pipeline order, skipping unreadable ones."""
    records_dir = run_dir / RECORDS_DIRNAME
    if not records_dir.is_dir():
        return
    for record_path in sorted(records_dir.glob("*.json")):
        try:
            yield json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue


def _total_cost_estimate(run_dir: Path) -> float:
    """Sum every recorded attempt cost across the run's stage records."""
    total = 0.0
    for record in _iter_stage_records(run_dir):
        for attempt in record.get("attempts") or []:
            cost = attempt.get("cost_estimate_usd")
            if isinstance(cost, int | float):
                total += float(cost)
    return round(total, 6)


def _first_model(run_dir: Path) -> str | None:
    """Return the model name recorded by the first stage that used one."""
    for record in _iter_stage_records(run_dir):
        for attempt in record.get("attempts") or []:
            if attempt.get("model"):
                return str(attempt["model"])
    return None


def run_generate(
    prompt: str,
    *,
    profile: str,
    quality: str = "draft",
    runs_root: Path,
    planner: LessonPlanProvider,
    coder: SceneCodeProvider,
) -> RunResult:
    """Allocate a fresh run directory and execute the pipeline over it."""
    run_dir = allocate_run_dir(runs_root, prompt)
    context = RunContext(
        run_dir=run_dir,
        prompt=prompt,
        profile=profile,
        quality=quality,
        planner=planner,
        coder=coder,
    )
    return GeneratePipeline().run(context)
