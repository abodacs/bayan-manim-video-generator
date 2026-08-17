"""Orchestrator for managing the complete Bayan educator workflow and manifest lifecycle."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, cast

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


StageStatus = Literal["pending", "completed", "failed", "stub"]


@dataclass
class StageState:
    status: StageStatus = "pending"
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
    status: StageStatus = "pending"
    created_at: str = field(default_factory=_get_utc_now)
    updated_at: str = field(default_factory=_get_utc_now)
    stages: dict[str, StageState] = field(
        default_factory=lambda: {s: StageState() for s in DEFAULT_STAGES}
    )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Manifest:
        stages_data = cast(dict[str, dict[str, Any]], data.get("stages", {}))
        # Guard against KeyError if stage sets differ across versions
        stages = {
            s: StageState(**stages_data[s]) if s in stages_data else StageState()
            for s in DEFAULT_STAGES
        }
        return cls(
            run_id=str(data["run_id"]),
            status=cast(StageStatus, data.get("status", "pending")),
            created_at=str(data.get("created_at", _get_utc_now())),
            updated_at=str(data.get("updated_at", _get_utc_now())),
            stages=stages,
        )


class StageReporter(Protocol):
    """Presentation port for workflow progress events.

    Orchestration owns stage execution and state; the presenter owns how
    progress is rendered. Implementations print, log, or stay silent.
    """

    def stage_skipped(self, name: str) -> None: ...

    def stage_started(self, name: str) -> None: ...

    def stage_finished(self, name: str, status: StageStatus, error: str | None) -> None: ...

    def workflow_finished(self, success: bool) -> None: ...


class _NullReporter:
    """Discard progress events when no presenter is attached."""

    def stage_skipped(self, name: str) -> None:
        pass

    def stage_started(self, name: str) -> None:
        pass

    def stage_finished(self, name: str, status: StageStatus, error: str | None) -> None:
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

        manifest = Manifest(run_id=self.output_dir.name or self.output_dir.resolve().name)
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

        saw_stub = False
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
                # A stubbed stage is recorded, not fatal: later stages that do
                # not depend on it (like the review packet) still run.
                stage_state.status = "stub"
                stage_state.error = str(exc)
                saw_stub = True
                self.manifest.status = "stub"
                self._save_manifest(self.manifest)
                report.stage_finished(stage_name, "stub", str(exc))
                continue
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

        self.manifest.status = "stub" if saw_stub else "completed"
        self._save_manifest(self.manifest)
        report.workflow_finished(not saw_stub)
        return not saw_stub

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
        if not source_file.exists():
            raise RuntimeError(
                f"Fixture scene '{fixture_name}' for template '{template_name}' not found."
            )

        # The render stage reads the fixture from the read-only source mount,
        # so record the selection instead of copying the scene code again.
        selection = {
            "template": template_name,
            "fixture": fixture_name,
            "class_name": str(catalogue[template_name]["class_name"]),
        }
        atomic_write_text(
            self.output_dir / "template_selection.json", json.dumps(selection, indent=2) + "\n"
        )

    def _run_render_stage(self) -> None:
        plan = self._load_scene_plan()
        RenderJobRunner().run_job(plan, output_dir=self.output_dir)

    def _run_validate_stage(self) -> None:
        raise NotImplementedError("Validation stage is not yet implemented.")

    def _run_review_packet_stage(self) -> None:
        # Namespaced apart from agents/roles.py repair escalation packets.
        labels = {
            "plan": "Planning",
            "template_select": "Template Selection",
            "render": "Render",
            "validate": "Validation",
        }
        lines = ["# Lesson Review Packet", "", "## Status"]
        for stage_name, label in labels.items():
            state = self.manifest.stages[stage_name]
            lines.append(f"- {label}: {state.status.upper()}")
        review_file = self.output_dir / "lesson_review_packet.md"
        atomic_write_text(review_file, "\n".join(lines) + "\n")
