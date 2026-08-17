"""Render job execution behind the isolated container worker.

Generated and catalogue scene code is untrusted input (AgDR-0002): it runs in
the Docker worker with the same security policy as the container smoke run,
never in the application process.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Protocol

from bayan.renderer.docker import DockerExecutor, check_docker
from bayan.renderer.errors import DockerError
from bayan.renderer.models import RenderJob, RenderSettings
from bayan.renderer.smoke import (
    CONTAINER_OUTPUT_ROOT,
    DEFAULT_IMAGE,
    FIXTURES_ROOT,
    PROJECT_ROOT,
    SmokeError,
    current_container_user,
    first_artifact,
    require_success,
    validate_png,
)
from bayan.templates.catalogue import fixture_filename, get_template_catalogue
from bayan.utils.atomic_io import atomic_write_text

# Derive allowlist directly from template catalogue keys to prevent catalog drift
APPROVED_TEMPLATES = set(get_template_catalogue().keys())

RENDER_TIMEOUT_SECONDS = 180


class PlanLike(Protocol):
    """Protocol interface to decouple renderer from planner domain models."""

    selected_template: str
    provider_fingerprint: str


class RenderError(Exception):
    """Custom exception raised when Manim fails to render the scene."""


class RenderJobRunner:
    """Executes rendering jobs with preflight checks and isolation."""

    def __init__(self, executor: DockerExecutor | None = None, image: str = DEFAULT_IMAGE) -> None:
        self._executor = executor
        self._image = image

    def run_job(self, plan: PlanLike, output_dir: Path) -> RenderJob:
        # Preflight validation: fail fast before invoking container
        if plan.selected_template not in APPROVED_TEMPLATES:
            raise ValueError(f"Unknown or unapproved template: '{plan.selected_template}'")

        job_id = f"job-{uuid.uuid4().hex[:8]}"
        fallback_plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        output_dir.mkdir(parents=True, exist_ok=True)
        job = RenderJob(
            job_id=job_id,
            status="running",
            scene_plan_id=plan.provider_fingerprint or fallback_plan_id,
            scene_id=plan.selected_template,
        )
        job_path = output_dir / "render_job.json"

        failure_stage = "setup"
        try:
            executor = _resolve_executor(self._executor, output_dir)
            executor.inspect_image(self._image)

            catalogue = get_template_catalogue()
            class_name = str(catalogue[plan.selected_template]["class_name"])
            scene_path = str(FIXTURES_ROOT / fixture_filename(plan.selected_template))

            self._persist_job(job_path, job)
            log_path = output_dir / "render.log"
            log_path.touch()

            failure_stage = "render video"
            _run_manim(executor, self._image, scene_path, class_name, output_dir, log_path, "video")

            failure_stage = "render preview"
            _run_manim(
                executor, self._image, scene_path, class_name, output_dir, log_path, "preview"
            )

            failure_stage = "collect artifacts"
            video_path = first_artifact(
                output_dir / "media" / "video", f"{class_name}.mp4", "MP4 video"
            )
            preview_path = first_artifact(
                output_dir / "media" / "preview", f"{class_name}*.png", "PNG preview"
            )
            validate_png(preview_path)
            draft_path = output_dir / "draft.mp4"
            still_path = output_dir / "preview.png"
            shutil.copy2(video_path, draft_path)
            shutil.copy2(preview_path, still_path)

            job.status = "succeeded"
            job.artifacts = {"video": str(draft_path), "preview": str(still_path)}
            self._persist_job(job_path, job)
            return job
        except (DockerError, SmokeError) as error:
            job.status = "failed"
            job.failure_stage = failure_stage
            job.exit_reason = str(error)
            self._persist_job(job_path, job)
            raise RenderError(str(error)) from error

    def _persist_job(self, job_path: Path, job: RenderJob) -> None:
        atomic_write_text(job_path, json.dumps(job.to_dict(), indent=2) + "\n")


def render_scene_code(
    code_content: str,
    output_path: Path,
    scene_class_name: str = "GeneratedScene",
    executor: DockerExecutor | None = None,
    image: str = DEFAULT_IMAGE,
) -> Path:
    """Render generated scene code in the isolated worker.

    The code is written next to the requested output, mounted into the worker
    as its only writable surface, and the produced video is placed at
    ``output_path``.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scene_file = output_path.parent / "generated_scene.py"
    scene_file.write_text(code_content, encoding="utf-8")

    try:
        resolved_executor = _resolve_executor(executor, output_path.parent)
        resolved_executor.inspect_image(image)
        log_path = output_path.parent / "render.log"
        log_path.touch()
        scene_path = str(CONTAINER_OUTPUT_ROOT / "generated_scene.py")
        _run_manim(
            resolved_executor,
            image,
            scene_path,
            scene_class_name,
            output_path.parent,
            log_path,
            "video",
        )
        video_path = first_artifact(
            output_path.parent / "media" / "video",
            f"{scene_class_name}.mp4",
            "MP4 video",
        )
        shutil.copy2(video_path, output_path)
        return output_path
    except (DockerError, SmokeError) as error:
        raise RenderError(str(error)) from error


def _resolve_executor(executor: DockerExecutor | None, run_directory: Path) -> DockerExecutor:
    """Return the injected executor, or build one from the local Docker host."""
    if executor is not None:
        return executor
    docker, _server_version = check_docker()
    uid, gid = current_container_user()
    return DockerExecutor(
        docker=docker,
        run_directory=run_directory,
        source_directory=PROJECT_ROOT / "bayan",
        container_user=f"{uid}:{gid}",
        settings=RenderSettings(),
    )


def _run_manim(
    executor: DockerExecutor,
    image: str,
    scene_path: str,
    class_name: str,
    output_dir: Path,
    log_path: Path,
    kind: str,
) -> None:
    """Render one scene to a video or PNG preview inside the worker."""
    media_dir = CONTAINER_OUTPUT_ROOT / "media" / kind
    command: list[str] = ["manim", "-ql"]
    if kind == "preview":
        command.extend(("-s", "--format=png"))
    command.extend((scene_path, class_name, "--media_dir", str(media_dir)))
    result = executor.run_container(
        image,
        command,
        log_path,
        RENDER_TIMEOUT_SECONDS,
        include_source_mount=True,
        output_directory=output_dir,
        phase=f"render {kind}",
    )
    require_success(f"Rendering the {kind}", result, RENDER_TIMEOUT_SECONDS)
