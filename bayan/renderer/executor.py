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
    allocate_run_directory,
    current_container_user,
    first_artifact,
    prepare_writable_directory,
    prune_run_directories,
    require_success,
    validate_png,
)
from bayan.templates.catalogue import fixture_filename, get_template_catalogue
from bayan.utils.atomic_io import atomic_write_text


class PlanRenderSettingsLike(Protocol):
    """Render preferences the renderer consumes from a scene plan."""

    @property
    def quality(self) -> str: ...


class PlanLike(Protocol):
    """Protocol interface to decouple renderer from planner domain models."""

    selected_template: str
    provider_fingerprint: str

    @property
    def render_settings(self) -> PlanRenderSettingsLike: ...


class RenderError(Exception):
    """Custom exception raised when Manim fails to render the scene."""


# Manim quality flags for the scene plan's render quality names.
QUALITY_FLAGS = {
    "low_quality": "-ql",
    "medium_quality": "-qm",
    "high_quality": "-qh",
    "highest_quality": "-qk",
}


def _quality_flag(quality: str) -> str:
    """Map a scene plan render quality onto its Manim quality flag."""
    try:
        return QUALITY_FLAGS[quality]
    except KeyError:
        raise RenderError(f"Unknown render quality: {quality!r}") from None


def approved_templates() -> set[str]:
    """Derive the template allowlist from the catalogue at call time."""
    return set(get_template_catalogue().keys())


class RenderJobRunner:
    """Executes rendering jobs with preflight checks and isolation."""

    def __init__(self, executor: DockerExecutor | None = None, image: str = DEFAULT_IMAGE) -> None:
        self._executor = executor
        self._image = image

    def run_job(self, plan: PlanLike, output_dir: Path) -> RenderJob:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        fallback_plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        output_dir.mkdir(parents=True, exist_ok=True)
        job = RenderJob(
            job_id=job_id,
            status="running",
            scene_plan_id=plan.provider_fingerprint or fallback_plan_id,
            template_id=plan.selected_template,
        )
        job_path = output_dir / "render_job.json"

        # Preflight validation: fail fast, but leave failure evidence behind.
        if plan.selected_template not in approved_templates():
            message = f"Unknown or unapproved template: '{plan.selected_template}'"
            job.status = "failed"
            job.failure_stage = "preflight"
            job.exit_reason = message
            self._persist_job(job_path, job)
            raise RenderError(message)

        failure_stage = "setup"
        try:
            executor = _resolve_executor(self._executor, output_dir)
            executor.inspect_image(self._image)

            catalogue = get_template_catalogue()
            class_name = str(catalogue[plan.selected_template]["class_name"])
            scene_path = str(FIXTURES_ROOT / fixture_filename(plan.selected_template))
            quality_flag = _quality_flag(plan.render_settings.quality)

            # The fresh run directory is the container's only writable mount, so
            # render_job.json and render.log stay outside the worker's reach.
            run_root = output_dir / "render-runs"
            # Prune before allocating: failed renders must not accumulate
            # unbounded run directories on the host either.
            prune_run_directories(run_root)
            render_run = allocate_run_directory(run_root)
            _prepare_writable_mount(render_run, executor)

            self._persist_job(job_path, job)
            log_path = output_dir / "render.log"
            log_path.touch()

            failure_stage = "render video"
            _run_manim(
                executor,
                self._image,
                scene_path,
                class_name,
                render_run,
                log_path,
                "video",
                quality_flag,
            )

            failure_stage = "render preview"
            _run_manim(
                executor,
                self._image,
                scene_path,
                class_name,
                render_run,
                log_path,
                "preview",
                quality_flag,
            )

            failure_stage = "collect artifacts"
            video_path = first_artifact(
                render_run / "media" / "video", f"{class_name}.mp4", "MP4 video"
            )
            preview_path = first_artifact(
                render_run / "media" / "preview", f"{class_name}*.png", "PNG preview"
            )
            validate_png(preview_path)
            draft_path = output_dir / "draft.mp4"
            still_path = output_dir / "preview.png"
            shutil.copy2(video_path, draft_path)
            shutil.copy2(preview_path, still_path)

            job.status = "succeeded"
            job.artifacts = {
                "video": str(draft_path.relative_to(output_dir)),
                "preview": str(still_path.relative_to(output_dir)),
            }
            self._persist_job(job_path, job)
            prune_run_directories(output_dir / "render-runs")
            return job
        except (DockerError, OSError, SmokeError, RenderError) as error:
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

    The untrusted code is written into a fresh per-render run directory that
    is mounted as the worker's only writable surface, and the produced video
    is copied to ``output_path``.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_root = output_path.parent / f"{output_path.stem}-runs"
    # Prune before allocating so failed renders stay bounded too.
    prune_run_directories(run_root)
    render_run = allocate_run_directory(run_root)
    atomic_write_text(render_run / "generated_scene.py", code_content)

    try:
        resolved_executor = _resolve_executor(executor, render_run)
        _prepare_writable_mount(render_run, resolved_executor)
        resolved_executor.inspect_image(image)
        # The log must stay outside the run directory: it is the container's
        # only writable mount, and untrusted scene code must not be able to
        # truncate or forge its own diagnostics.
        log_path = output_path.with_suffix(".render.log")
        log_path.touch()
        scene_path = str(CONTAINER_OUTPUT_ROOT / "generated_scene.py")
        # Generated-code renders have no scene plan; default to low quality.
        _run_manim(
            resolved_executor,
            image,
            scene_path,
            scene_class_name,
            render_run,
            log_path,
            "video",
            "-ql",
        )
        video_path = first_artifact(
            render_run / "media" / "video",
            f"{scene_class_name}.mp4",
            "MP4 video",
        )
        shutil.copy2(video_path, output_path)
        prune_run_directories(run_root)
        return output_path
    except (DockerError, SmokeError, OSError) as error:
        raise RenderError(f"{error} (run directory: {render_run})") from error


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


def _prepare_writable_mount(render_run: Path, executor: DockerExecutor) -> None:
    """Make the fresh render run directory writable for the container user."""
    uid_text, _, gid_text = executor.container_user.partition(":")
    prepare_writable_directory(render_run, uid_text, gid_text or uid_text)


def _run_manim(
    executor: DockerExecutor,
    image: str,
    scene_path: str,
    class_name: str,
    render_run: Path,
    log_path: Path,
    kind: str,
    quality_flag: str,
) -> None:
    """Render one scene to a video or PNG preview inside the worker."""
    media_dir = CONTAINER_OUTPUT_ROOT / "media" / kind
    timeout_seconds = executor.settings.render_timeout_seconds
    if kind == "preview":
        # A preview is a single final frame; it stays fast at low quality.
        command: list[str] = ["manim", "-ql", "-s", "--format=png"]
    else:
        command = ["manim", quality_flag]
    command.extend((scene_path, class_name, "--media_dir", str(media_dir)))
    result = executor.run_container(
        image,
        command,
        log_path,
        timeout_seconds,
        include_source_mount=True,
        output_directory=render_run,
        phase=f"render {kind}",
    )
    require_success(f"Rendering the {kind}", result, timeout_seconds)
