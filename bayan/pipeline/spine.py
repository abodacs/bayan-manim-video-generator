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
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bayan.pipeline.coder import SCENE_FILENAME, CoderService, CodingError, SceneCodeProvider
from bayan.pipeline.critic import critic_blocked, run_critic
from bayan.pipeline.models import CheckResult, LessonPlan
from bayan.pipeline.planner import PLAN_FILENAME, PlannerService, PlanningError
from bayan.pipeline.preflight import GateResult, gates_blocked, run_gates
from bayan.pipeline.profiles import UnknownProfileError, get_profile, normalize_plan
from bayan.pipeline.provider import LessonPlanProvider
from bayan.pipeline.records import RECORDS_DIRNAME, write_stage_record
from bayan.pipeline.repair import CodeRepairProvider, RepairService
from bayan.renderer.errors import (
    classify_critic_results,
    classify_gate_results,
    classify_provider_error,
    classify_render_failure,
)
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
CRITIC_RECORD_FILENAME = "06-critic.json"
REPAIR_RECORD_FILENAME = "07-repair.json"


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
    planner: LessonPlanProvider | None = None
    coder: SceneCodeProvider | None = None
    repairer: CodeRepairProvider | None = None
    vlm: bool = False
    rerun_of: str | None = None
    plan: LessonPlan | None = None
    scene_code: str | None = None
    gate_results: list[GateResult] = field(default_factory=list)
    check_results: list[CheckResult] = field(default_factory=list)


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
    repairs_used: int


def _stage_record(
    stage: str,
    status: str,
    rerun_of: str | None,
    failure: str | None = None,
    **evidence: Any,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "rerun_of": rerun_of,
        "failure": failure,
        **evidence,
    }


def _failed(context: RunContext, stage: Stage, failure: str, **evidence: Any) -> StageOutcome:
    write_stage_record(
        context.run_dir,
        _stage_record(stage.name, "failed", context.rerun_of, failure, **evidence),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="failed", failure=failure)


def run_plan_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Turn the prompt into a validated LessonPlan via the planning service."""
    # The spine stops at the first failure; the plan stage only runs in generate.
    assert context.planner is not None
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
    """Normalize the validated plan's digits and dialect for the profile."""
    try:
        profile = get_profile(context.profile)
    except UnknownProfileError as error:
        return _failed(context, stage, str(error))

    if context.plan is not None:
        context.plan = normalize_plan(context.plan, context.profile)
        atomic_write_text(
            context.run_dir / PLAN_FILENAME,
            context.plan.model_dump_json(indent=2, ensure_ascii=False) + "\n",
        )
    write_stage_record(
        context.run_dir,
        _stage_record(
            stage.name,
            "completed",
            context.rerun_of,
            profile=profile.name,
            digit_style=profile.digit_style.value,
            font=profile.font,
        ),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


def run_code_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Turn the validated plan into scene code via the coding service."""
    # The spine stops at the first failure, so the plan stage always ran.
    assert context.plan is not None
    # The spine stops at the first failure; the code stage only runs in generate.
    assert context.coder is not None
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
    context.gate_results = results
    gate_evidence = [asdict(result) for result in results]
    if gates_blocked(results):
        failure = "; ".join(
            f"{result.gate} (line {result.line}): {result.suggestion}"
            for result in results
            if result.status != "passed"
        )
        write_stage_record(
            context.run_dir,
            _stage_record(stage.name, "failed", context.rerun_of, failure, gates=gate_evidence),
            stage.record_filename,
        )
        return StageOutcome(stage=stage.name, status="failed", failure=failure)
    write_stage_record(
        context.run_dir,
        _stage_record(stage.name, "completed", context.rerun_of, gates=gate_evidence),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


def run_critic_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Run the deterministic critic over the produced artifacts."""
    # The spine stops at the first failure, so the predecessors always ran.
    assert context.plan is not None and context.scene_code is not None
    render_record_path = context.run_dir / "records" / RENDER_RECORD_FILENAME
    render_status = (
        json.loads(render_record_path.read_text(encoding="utf-8")).get("status")
        if render_record_path.exists()
        else None
    )
    results = run_critic(
        plan=context.plan,
        code=context.scene_code,
        draft_path=context.run_dir / DRAFT_FILENAME,
        preview_path=context.run_dir / PREVIEW_FILENAME,
        render_status=render_status,
        vlm=context.vlm,
    )
    context.check_results = results
    checks = [result.model_dump() for result in results]
    if critic_blocked(results):
        failure = "; ".join(
            f"{result.check}: {result.evidence}" for result in results if result.status == "failed"
        )
        write_stage_record(
            context.run_dir,
            _stage_record(stage.name, "failed", context.rerun_of, failure, checks=checks),
            stage.record_filename,
        )
        return StageOutcome(stage=stage.name, status="failed", failure=failure)
    write_stage_record(
        context.run_dir,
        _stage_record(stage.name, "completed", context.rerun_of, checks=checks),
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
            context.rerun_of,
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
    Stage("critic", CRITIC_RECORD_FILENAME, run_critic_stage),
)


class GeneratePipeline:
    """Sequence stages into a run directory; a failure triggers bounded repair.

    Plan and profile failures stop the run immediately (plan repair is out
    of scope in phase 1). Failures of the code-driven stages (code, gates,
    render, critic) enter the repair loop: classify, minimal fix, re-gate,
    then replay the stages from the gates onward. At most
    ``max_repairs`` repair attempts; exhaustion fails the run.
    """

    def __init__(self, stages: tuple[Stage, ...] = STAGES) -> None:
        self.stages = stages

    def run(self, context: RunContext) -> RunResult:
        context.run_dir.mkdir(parents=True, exist_ok=True)

        stage_names = [stage.name for stage in self.stages]
        gates_index = stage_names.index("gates")
        repairable = {"code", "gates", "render", "critic"}

        stage_statuses: dict[str, str] = {}
        failure: str | None = None
        # Reruns omit the repairer: their failures surface without repair
        # (no LLM is allowed on the rerun path).
        repair_service = (
            RepairService(
                provider=context.repairer,
                run_dir=context.run_dir,
                record_filename=REPAIR_RECORD_FILENAME,
            )
            if context.repairer is not None
            else None
        )

        index = 0
        while index < len(self.stages):
            stage = self.stages[index]
            outcome = stage.run(context, stage)
            stage_statuses[outcome.stage] = outcome.status
            if outcome.status == "completed":
                # A repaired replay clears the earlier failure.
                failure = None
                index += 1
                continue

            failure = outcome.failure
            if stage.name not in repairable or repair_service is None:
                break

            round_outcome = repair_service.repair_round(
                code=context.scene_code or "",
                classification=self._classify(stage.name, context, outcome),
                plan=context.plan,
                profile=context.profile,
            )
            if round_outcome.status == "completed":
                context.scene_code = round_outcome.code
                failure = None
                stage_statuses[stage.name] = "repaired"
                index = gates_index  # a fix re-enters at the gates, never the container
                continue
            if round_outcome.status == "still_failing":
                # The fix was applied but rejected; re-run the stage so the
                # next classification sees the new gate results.
                context.scene_code = round_outcome.code or context.scene_code
                failure = None
                continue
            failure = round_outcome.failure or failure
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
            "rerun_of": context.rerun_of,
            "model": _first_model(context.run_dir),
            "total_cost_estimate_usd": total_cost,
            "stages": stage_statuses,
            "repairs_used": repair_service.provider_calls if repair_service else 0,
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
            repairs_used=repair_service.provider_calls if repair_service else 0,
        )

    def _classify(self, stage_name: str, context: RunContext, outcome: StageOutcome) -> Any:
        """Map the failed stage's typed results onto the failure taxonomy."""
        if stage_name == "gates":
            return classify_gate_results(context.gate_results)
        if stage_name == "critic":
            return classify_critic_results(context.check_results)
        if stage_name == "render":
            return classify_render_failure(outcome.failure or "")
        return classify_provider_error(ValueError(outcome.failure or "unknown"))


def iter_stage_records(run_dir: Path) -> Iterator[dict[str, Any]]:
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
    for record in iter_stage_records(run_dir):
        for attempt in record.get("attempts") or []:
            cost = attempt.get("cost_estimate_usd")
            if isinstance(cost, int | float):
                total += float(cost)
    return round(total, 6)


def _first_model(run_dir: Path) -> str | None:
    """Return the model name recorded by the first stage that used one."""
    for record in iter_stage_records(run_dir):
        for attempt in record.get("attempts") or []:
            if attempt.get("model"):
                return str(attempt["model"])
    return None


def run_generate(
    prompt: str,
    *,
    profile: str,
    quality: str = "draft",
    vlm: bool = False,
    runs_root: Path,
    planner: LessonPlanProvider,
    coder: SceneCodeProvider,
    repairer: CodeRepairProvider,
) -> RunResult:
    """Allocate a fresh run directory and execute the pipeline over it."""
    run_dir = allocate_run_dir(runs_root, prompt)
    context = RunContext(
        run_dir=run_dir,
        prompt=prompt,
        profile=profile,
        quality=quality,
        vlm=vlm,
        planner=planner,
        coder=coder,
        repairer=repairer,
    )
    return GeneratePipeline().run(context)


class RerunError(RuntimeError):
    """The requested run cannot be replayed from its cached artifacts."""


RERUN_STAGE_NAMES = ("profile", "gates", "render", "critic")


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
        run_dir=run_dir,
        prompt=prompt,
        profile=plan.profile,
        quality=quality,
        vlm=vlm,
        rerun_of=run_id,
        plan=plan,
        scene_code=scene_code,
    )
    rerun_stages = tuple(stage for stage in STAGES if stage.name in RERUN_STAGE_NAMES)
    return GeneratePipeline(stages=rerun_stages).run(context)
