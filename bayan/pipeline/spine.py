"""The generate pipeline spine: serial stages into a fresh ``runs/<id>/``.

Stages are a data-driven registry: each takes a :class:`RunContext` and its
own :class:`Stage`, does its work through a stage service (or the isolated
renderer), persists exactly one order-prefixed JSON record under
``records/``, and returns a :class:`StageOutcome`. The spine only sequences,
stops at the first failure, and writes ``run.json``. Later sub-issues append
stages to the registry without reworking the spine.

A run's state is split by mutability: :class:`RunInputs` is the frozen set
of configuration and provider seams, and :class:`RunArtifacts` is the
append-only bag of stage outputs whose typed readers name the stage that
must have run before. ``stop_after`` is the determinism seam the golden
prompt tests (#87) use to halt the pipeline after a named stage; production
callers leave it ``None``. The rerun feature lives in
:mod:`bayan.pipeline.rerun`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bayan.pipeline.coder import CoderService, CodingError, SceneCodeProvider
from bayan.pipeline.critic import critic_blocked, run_critic
from bayan.pipeline.models import CheckResult, LessonPlan
from bayan.pipeline.planner import PLAN_FILENAME, PlannerService, PlanningError
from bayan.pipeline.preflight import GateResult, gates_blocked, run_gates
from bayan.pipeline.profiles import UnknownProfileError, get_profile, normalize_plan
from bayan.pipeline.provider import LessonPlanProvider
from bayan.pipeline.records import first_model, stage_record, total_cost_usd, write_stage_record
from bayan.pipeline.repair import CodeRepairProvider, RepairService
from bayan.pipeline.taxonomy import (
    FailureClassification,
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


@dataclass(frozen=True)
class RunInputs:
    """One run's immutable configuration and provider seams.

    Nothing here changes once the run starts; stages read what they need and
    write nothing.
    """

    run_dir: Path
    prompt: str
    profile: str
    quality: str
    planner: LessonPlanProvider | None = None
    coder: SceneCodeProvider | None = None
    repairer: CodeRepairProvider | None = None
    vlm: bool = False
    rerun_of: str | None = None


class StagePreconditionError(RuntimeError):
    """A stage's predecessor has not run, or a seam was never provided.

    The registry orders stages so a well-built run cannot hit this; raising
    a typed error (instead of a scattered ``assert``) means a mis-ordered
    registry or a mis-built context fails loudly with the artifact named.
    """


@dataclass
class RunArtifacts:
    """Append-only, typed bag of stage outputs, in pipeline order.

    Each artifact has exactly one producing stage -- ``plan`` the plan
    stage, ``scene_code`` the code stage, ``gate_results`` the gates stage,
    ``check_results`` the critic, ``render_status`` the render stage. The
    one sanctioned refinement is the profile stage re-writing ``plan`` with
    its normalized digits and dialect. Readers go through the ``require_*``
    accessors, so "which stage ran before me" is carried by the accessor's
    type and error, not by asserts at every call site.
    """

    plan: LessonPlan | None = None
    scene_code: str | None = None
    gate_results: list[GateResult] = field(default_factory=list)
    check_results: list[CheckResult] = field(default_factory=list)
    render_status: str | None = None

    def put_plan(self, plan: LessonPlan) -> None:
        self.plan = plan

    def require_plan(self) -> LessonPlan:
        if self.plan is None:
            raise StagePreconditionError("the plan artifact is missing: the plan stage never ran")
        return self.plan

    def put_scene_code(self, code: str) -> None:
        self.scene_code = code

    def require_scene_code(self) -> str:
        if self.scene_code is None:
            raise StagePreconditionError("the scene code is missing: the code stage never ran")
        return self.scene_code

    def put_gate_results(self, results: list[GateResult]) -> None:
        self.gate_results = results

    def put_check_results(self, results: list[CheckResult]) -> None:
        self.check_results = results

    def put_render_status(self, status: str) -> None:
        self.render_status = status


@dataclass
class RunContext:
    """State one generate run carries through its stages.

    The frozen :class:`RunInputs` plus the append-only
    :class:`RunArtifacts`: stages read configuration and providers from
    ``inputs``, consume their predecessors' outputs through the artifacts'
    typed readers, and hand their own outputs to the bag.
    """

    inputs: RunInputs
    artifacts: RunArtifacts = field(default_factory=RunArtifacts)

    @property
    def run_dir(self) -> Path:
        return self.inputs.run_dir


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


def _failed(context: RunContext, stage: Stage, failure: str, **evidence: Any) -> StageOutcome:
    write_stage_record(
        context.run_dir,
        stage_record(stage.name, "failed", failure, rerun_of=context.inputs.rerun_of, **evidence),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="failed", failure=failure)


def run_plan_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Turn the prompt into a validated LessonPlan via the planning service."""
    inputs = context.inputs
    if inputs.planner is None:
        raise StagePreconditionError("the plan stage needs a planner provider on the run inputs")
    service = PlannerService(
        provider=inputs.planner,
        run_dir=inputs.run_dir,
        record_filename=stage.record_filename,
    )
    try:
        plan = service.plan(inputs.prompt, profile=inputs.profile)
    except PlanningError as error:
        return StageOutcome(stage=stage.name, status="failed", failure=str(error))
    context.artifacts.put_plan(plan)
    return StageOutcome(stage=stage.name, status="completed")


def run_profile_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Normalize the validated plan's digits and dialect for the profile."""
    inputs = context.inputs
    try:
        profile = get_profile(inputs.profile)
    except UnknownProfileError as error:
        return _failed(context, stage, str(error))

    normalized = normalize_plan(context.artifacts.require_plan(), inputs.profile)
    context.artifacts.put_plan(normalized)
    atomic_write_text(
        inputs.run_dir / PLAN_FILENAME,
        normalized.model_dump_json(indent=2, ensure_ascii=False) + "\n",
    )
    write_stage_record(
        inputs.run_dir,
        stage_record(
            stage.name,
            "completed",
            None,
            rerun_of=inputs.rerun_of,
            profile=profile.name,
            digit_style=profile.digit_style.value,
            font=profile.font,
        ),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


def run_code_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Turn the validated plan into scene code via the coding service."""
    inputs = context.inputs
    if inputs.coder is None:
        raise StagePreconditionError("the code stage needs a coder provider on the run inputs")
    service = CoderService(
        provider=inputs.coder,
        run_dir=inputs.run_dir,
        record_filename=stage.record_filename,
    )
    try:
        code = service.code(context.artifacts.require_plan(), profile=inputs.profile)
    except CodingError as error:
        return StageOutcome(stage=stage.name, status="failed", failure=str(error))
    context.artifacts.put_scene_code(code)
    return StageOutcome(stage=stage.name, status="completed")


def run_gates_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Statically gate the scene code; any failed gate blocks the render."""
    inputs = context.inputs
    results = run_gates(context.artifacts.require_scene_code(), profile=inputs.profile)
    context.artifacts.put_gate_results(results)
    gate_evidence = [asdict(result) for result in results]
    if gates_blocked(results):
        failure = "; ".join(
            f"{result.gate} (line {result.line}): {result.suggestion}"
            for result in results
            if result.status != "passed"
        )
        write_stage_record(
            inputs.run_dir,
            stage_record(
                stage.name, "failed", failure, rerun_of=inputs.rerun_of, gates=gate_evidence
            ),
            stage.record_filename,
        )
        return StageOutcome(stage=stage.name, status="failed", failure=failure)
    write_stage_record(
        inputs.run_dir,
        stage_record(stage.name, "completed", None, rerun_of=inputs.rerun_of, gates=gate_evidence),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


def run_critic_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Run the deterministic critic over the produced artifacts."""
    inputs = context.inputs
    results = run_critic(
        plan=context.artifacts.require_plan(),
        code=context.artifacts.require_scene_code(),
        draft_path=inputs.run_dir / DRAFT_FILENAME,
        preview_path=inputs.run_dir / PREVIEW_FILENAME,
        render_status=context.artifacts.render_status,
        vlm=inputs.vlm,
    )
    context.artifacts.put_check_results(results)
    checks = [result.model_dump() for result in results]
    if critic_blocked(results):
        failure = "; ".join(
            f"{result.check}: {result.evidence}" for result in results if result.status == "failed"
        )
        write_stage_record(
            inputs.run_dir,
            stage_record(stage.name, "failed", failure, rerun_of=inputs.rerun_of, checks=checks),
            stage.record_filename,
        )
        return StageOutcome(stage=stage.name, status="failed", failure=failure)
    write_stage_record(
        inputs.run_dir,
        stage_record(stage.name, "completed", None, rerun_of=inputs.rerun_of, checks=checks),
        stage.record_filename,
    )
    return StageOutcome(stage=stage.name, status="completed")


def run_render_stage(context: RunContext, stage: Stage) -> StageOutcome:
    """Render the scene code in the isolated container worker."""
    inputs = context.inputs
    try:
        render_scene_code(
            code_content=context.artifacts.require_scene_code(),
            output_path=inputs.run_dir / DRAFT_FILENAME,
            scene_class_name="GeneratedScene",
            preview_path=inputs.run_dir / PREVIEW_FILENAME,
            quality=inputs.quality,
        )
    except RenderError as error:
        return _failed(context, stage, str(error))
    context.artifacts.put_render_status("completed")
    write_stage_record(
        inputs.run_dir,
        stage_record(
            stage.name,
            "completed",
            None,
            rerun_of=inputs.rerun_of,
            quality=inputs.quality,
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
    render, critic) enter the repair loop owned by :class:`RepairService`:
    classify, minimal fix, then replay from the gates onward -- the gates
    stage is the single place a repaired scene is re-gated, before any
    container starts. The spine owns only sequencing; exhaustion fails the
    run.
    """

    def __init__(self, stages: tuple[Stage, ...] = STAGES) -> None:
        self.stages = stages

    def run(self, context: RunContext, *, stop_after: str | None = None) -> RunResult:
        """Run the stages in order, writing ``run.json`` at the end.

        ``stop_after`` halts the pipeline once that stage completes -- the
        determinism seam the golden prompt tests (#87) use to exercise the
        pipeline up to and including the preflight gates, never rendering.
        Production callers leave it ``None``.
        """
        inputs = context.inputs
        inputs.run_dir.mkdir(parents=True, exist_ok=True)

        stage_names = [stage.name for stage in self.stages]
        gates_index = stage_names.index("gates")
        repairable = {"code", "gates", "render", "critic"}

        stage_statuses: dict[str, str] = {}
        failure: str | None = None
        # Reruns omit the repairer: their failures surface without repair
        # (no LLM is allowed on the rerun path).
        repair_service = (
            RepairService(
                provider=inputs.repairer,
                run_dir=inputs.run_dir,
                record_filename=REPAIR_RECORD_FILENAME,
            )
            if inputs.repairer is not None
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
                if stop_after is not None and stage.name == stop_after:
                    break
                index += 1
                continue

            failure = outcome.failure
            if stage.name not in repairable or repair_service is None:
                break

            round_outcome = repair_service.repair_round(
                code=context.artifacts.scene_code or "",
                classification=self._classify(stage.name, context, outcome),
                plan=context.artifacts.plan,
            )
            if round_outcome.status == "fixed":
                # A candidate fix re-enters at the gates: the gates stage
                # re-runs every gate once, before any container starts.
                context.artifacts.put_scene_code(round_outcome.code or "")
                failure = None
                stage_statuses[stage.name] = "repaired"
                index = gates_index
                continue
            failure = round_outcome.failure or failure
            break

        status = "completed" if failure is None else "failed"
        recorded_cost = total_cost_usd(inputs.run_dir)
        total_cost = recorded_cost if recorded_cost is not None else 0.0
        summary: dict[str, Any] = {
            "run_id": inputs.run_dir.name,
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "prompt": inputs.prompt,
            "profile": inputs.profile,
            "quality": inputs.quality,
            "rerun_of": inputs.rerun_of,
            "model": first_model(inputs.run_dir),
            "total_cost_estimate_usd": total_cost,
            "stages": stage_statuses,
            "repairs_used": repair_service.provider_calls if repair_service else 0,
            "failure": failure,
        }
        atomic_write_text(
            inputs.run_dir / RUN_SUMMARY_FILENAME,
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        )
        return RunResult(
            run_id=inputs.run_dir.name,
            run_dir=inputs.run_dir,
            status=status,
            failure=failure,
            total_cost_estimate_usd=total_cost,
            repairs_used=repair_service.provider_calls if repair_service else 0,
        )

    def _classify(
        self, stage_name: str, context: RunContext, outcome: StageOutcome
    ) -> FailureClassification | None:
        """Map the failed stage's typed results onto the failure taxonomy.

        Run-time twin of ``_record_category`` (bayan.pipeline.runs), which
        reclassifies past runs from their serialized records; a new stage
        or evidence kind must update both dispatches.
        """
        if stage_name == "gates":
            return classify_gate_results(context.artifacts.gate_results)
        if stage_name == "critic":
            return classify_critic_results(context.artifacts.check_results)
        if stage_name == "render":
            return classify_render_failure(outcome.failure or "")
        return classify_provider_error(outcome.failure or "unknown")


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
        inputs=RunInputs(
            run_dir=run_dir,
            prompt=prompt,
            profile=profile,
            quality=quality,
            vlm=vlm,
            planner=planner,
            coder=coder,
            repairer=repairer,
        )
    )
    return GeneratePipeline().run(context)
