"""Orchestrator for managing the complete Bayan educator workflow and manifest lifecycle."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from bayan.planner.models import ScenePlan
from bayan.planner.service import run_planning_pipeline
from bayan.renderer.executor import RenderJobRunner
from bayan.templates.catalogue import fixture_filename, get_template_catalogue
from bayan.utils.atomic_io import atomic_write_text


def _get_utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ManifestError(RuntimeError):
    """The run directory holds a manifest that cannot be trusted."""


@dataclass
class StageState:
    status: str = "pending"  # pending, completed, failed, stub
    attempts: int = 0
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


DEFAULT_STAGES = [
    "plan",
    "template_select",
    "render",
    "validate",
    "review_packet",
]


@dataclass
class Manifest:
    run_id: str
    status: str = "pending"  # pending, completed, failed, stub
    created_at: str = field(default_factory=_get_utc_now)
    updated_at: str = field(default_factory=_get_utc_now)
    stages: dict[str, StageState] = field(
        default_factory=lambda: {s: StageState() for s in DEFAULT_STAGES}
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Manifest:
        stages_data = data.get("stages", {})
        # Guard against KeyError if stage sets differ across versions
        stages = {
            s: StageState(**stages_data[s]) if s in stages_data else StageState()
            for s in DEFAULT_STAGES
        }
        return cls(
            run_id=data["run_id"],
            status=data.get("status", "pending"),
            created_at=data.get("created_at", _get_utc_now()),
            updated_at=data.get("updated_at", _get_utc_now()),
            stages=stages,
        )


class StageReporter(Protocol):
    """Presentation port for workflow progress events.

    Orchestration owns stage execution and state; the presenter owns how
    progress is rendered. Implementations print, log, or stay silent.
    """

    def stage_skipped(self, name: str) -> None: ...

    def stage_started(self, name: str) -> None: ...

    def stage_finished(self, name: str, status: str, error: str | None) -> None: ...

    def workflow_finished(self, success: bool) -> None: ...


class _NullReporter:
    """Discard progress events when no presenter is attached."""

    def stage_skipped(self, name: str) -> None:
        pass

    def stage_started(self, name: str) -> None:
        pass

    def stage_finished(self, name: str, status: str, error: str | None) -> None:
        pass

    def workflow_finished(self, success: bool) -> None:
        pass


class WorkflowOrchestrator:
    """Coordinates stages, retries, and manifest persistence for bayan run."""

    def __init__(self, input_path: Path, output_dir: Path, provider: str = "fake") -> None:
        self.input_path = input_path
        self.output_dir = output_dir
        self.provider_name = provider
        self.manifest_path = self.output_dir / "manifest.json"
        self.manifest = self._load_or_create_manifest()

    def _load_or_create_manifest(self) -> Manifest:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                return Manifest.from_dict(data)
            except (json.JSONDecodeError, TypeError, KeyError) as error:
                raise ManifestError(
                    f"Run '{self.output_dir.name}' has an unreadable manifest at "
                    f"{self.manifest_path}: {error}. Delete the file or fix it before "
                    "resuming this run."
                ) from error

        manifest = Manifest(run_id=self.output_dir.name)
        self._save_manifest(manifest)
        return manifest

    def _save_manifest(self, manifest: Manifest) -> None:
        """Saves manifest using atomic file replace pattern to avoid partial writes."""
        manifest.updated_at = _get_utc_now()
        atomic_write_text(self.manifest_path, json.dumps(manifest.to_dict(), indent=2) + "\n")

    def run(self, reporter: StageReporter | None = None) -> bool:
        """Executes all workflow stages sequentially with state tracking."""
        report = reporter if reporter is not None else _NullReporter()
        stages = [
            ("plan", self._run_plan_stage),
            ("template_select", self._run_template_select_stage),
            ("render", self._run_render_stage),
            ("validate", self._run_validate_stage),
            ("review_packet", self._run_review_packet_stage),
        ]

        for stage_name, stage_fn in stages:
            stage_state = self.manifest.stages[stage_name]
            if stage_state.status == "completed":
                report.stage_skipped(stage_name)
                continue

            report.stage_started(stage_name)
            stage_state.started_at = _get_utc_now()
            stage_state.attempts += 1

            try:
                stage_fn()
            except NotImplementedError as exc:
                stage_state.status = "stub"
                stage_state.error = str(exc)
                self.manifest.status = "stub"
                self._save_manifest(self.manifest)
                report.stage_finished(stage_name, "stub", str(exc))
                return False
            except Exception as exc:
                stage_state.status = "failed"
                stage_state.error = str(exc)
                self.manifest.status = "failed"
                self._save_manifest(self.manifest)
                report.stage_finished(stage_name, "failed", str(exc))
                return False

            stage_state.status = "completed"
            stage_state.completed_at = _get_utc_now()
            stage_state.error = None
            self._save_manifest(self.manifest)
            report.stage_finished(stage_name, "completed", None)

        self.manifest.status = "completed"
        self._save_manifest(self.manifest)
        report.workflow_finished(True)
        return True

    def _run_plan_stage(self) -> None:
        # run_planning_pipeline either raises or always writes scene_plan.json.
        run_planning_pipeline(input_path=self.input_path, output_dir=self.output_dir, force=True)

    def _load_scene_plan(self) -> ScenePlan:
        """Read the typed Scene plan written by the plan stage."""
        plan_path = self.output_dir / "scene_plan.json"
        try:
            return ScenePlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise RuntimeError(
                f"Scene plan not found at {plan_path}. Re-run the plan stage."
            ) from error
        except ValidationError as error:
            raise RuntimeError(f"Scene plan at {plan_path} is invalid: {error}") from error

    def _run_template_select_stage(self) -> None:
        plan = self._load_scene_plan()
        catalogue = get_template_catalogue()
        template_name = plan.selected_template
        if template_name not in catalogue:
            raise RuntimeError(f"Template '{template_name}' not found in catalogue")

        fixture_name = fixture_filename(template_name)
        source_file = Path(__file__).parent / "templates" / "fixtures" / fixture_name
        target_scene = self.output_dir / "scene.py"

        if source_file.exists():
            shutil.copy(source_file, target_scene)
        else:
            raise RuntimeError(
                f"Fixture scene '{fixture_name}' for template '{template_name}' not found."
            )

    def _run_render_stage(self) -> None:
        plan = self._load_scene_plan()
        RenderJobRunner().run_job(plan, output_dir=self.output_dir)

    def _run_validate_stage(self) -> None:
        raise NotImplementedError("Validation stage is not yet implemented.")

    def _run_review_packet_stage(self) -> None:
        # Namespaced apart from agents/roles.py repair escalation packets.
        review_md = (
            "# Lesson Review Packet\n\n"
            "## Status\n"
            "- Planning & Template Selection: COMPLETED\n"
            "- Render & Validation: STUB (Not Yet Implemented)\n"
        )
        review_file = self.output_dir / "lesson_review_packet.md"
        atomic_write_text(review_file, review_md)
