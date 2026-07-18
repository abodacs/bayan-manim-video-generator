"""Orchestrate a deterministic Arabic render smoke run."""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from bayan.renderer.docker import DockerExecutor, check_docker
from bayan.renderer.errors import DockerError
from bayan.renderer.models import ImageMetadata, RenderSettings, SmokeManifest
from bayan.renderer.process import CommandResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IMAGE = "bayan/manim-smoke:0.20.1"
DEFAULT_OUTPUT_ROOT = Path("artifacts/container-smoke")
SCENE_PATH = "/workspace/bayan/utils/sanity_check.py"
SCENE_NAME = "ArabicSanityCheck"


class SmokeError(RuntimeError):
    """A recoverable setup, validation, or render failure."""


@dataclass(frozen=True)
class SmokeConfig:
    """Inputs and resource limits for one smoke run."""

    image: str = DEFAULT_IMAGE
    output_root: Path = DEFAULT_OUTPUT_ROOT
    skip_build: bool = False
    build_timeout: int = 900
    render_timeout: int = 180
    max_log_bytes: int = 1_048_576
    project_root: Path = PROJECT_ROOT


@dataclass(frozen=True)
class SmokeResult:
    """Paths and manifest returned after a successful run."""

    run_directory: Path
    video: Path
    preview: Path
    manifest: SmokeManifest


class SmokeRunner:
    """Run the Arabic sanity scene through the isolated Docker boundary."""

    def __init__(self, config: SmokeConfig) -> None:
        self.config = config
        self.run_directory: Path | None = None
        self.manifest: SmokeManifest | None = None

    def run(self) -> SmokeResult:
        """Build, render, validate, and collect the smoke artifacts."""
        try:
            docker, docker_server = check_docker()
        except DockerError as error:
            raise SmokeError(str(error)) from error
        project_root = self.config.project_root.resolve()
        output_root = self.config.output_root
        if not output_root.is_absolute():
            output_root = project_root / output_root
        run_directory = allocate_run_directory(output_root.resolve())
        self.run_directory = run_directory
        media_directory = run_directory / "manim-output"
        media_directory.mkdir()
        uid, gid = current_container_user()
        container_user = f"{uid}:{gid}"
        _prepare_media_directory(media_directory, uid, gid)

        settings = RenderSettings(
            build_timeout_seconds=self.config.build_timeout,
            render_timeout_seconds=self.config.render_timeout,
            max_log_bytes_per_phase=self.config.max_log_bytes,
            build_skipped=self.config.skip_build,
        )
        log_path = run_directory / "render.log"
        log_path.touch()
        manifest = SmokeManifest(
            scene=SCENE_NAME,
            quality="low",
            docker_server=docker_server,
            container_user=container_user,
            settings=settings,
            image=ImageMetadata(reference=self.config.image),
            source_hashes=source_hashes(project_root),
        )
        self.manifest = manifest
        manifest.write(run_directory)
        executor = DockerExecutor(
            docker=docker,
            run_directory=run_directory,
            source_directory=project_root / "bayan",
            container_user=container_user,
            settings=settings,
        )

        try:
            if not self.config.skip_build:
                build_result = executor.build_image(
                    self.config.image,
                    project_root / "Dockerfile",
                    project_root,
                    log_path,
                )
                self._record_phase("build image", build_result, log_path)
                require_success(
                    "Building the container image", build_result, self.config.build_timeout
                )

            manifest.image = executor.inspect_image(self.config.image)
            manifest.write(run_directory)

            font_result = executor.run_container(
                self.config.image,
                ("fc-match", "--format=%{family}\\n", "Noto Sans Arabic"),
                log_path,
                self.config.render_timeout,
                phase="check Arabic font",
            )
            self._record_phase("check Arabic font", font_result, log_path)
            require_success("Checking the Arabic font", font_result, self.config.render_timeout)
            if not font_result.output_tail.strip():
                raise SmokeError(
                    "The container has no usable Noto Sans Arabic font. Rebuild the image."
                )

            video_result = executor.run_container(
                self.config.image,
                (
                    "manim",
                    "-ql",
                    SCENE_PATH,
                    SCENE_NAME,
                    "--media_dir",
                    "/workspace/output/video",
                ),
                log_path,
                self.config.render_timeout,
                include_source_mount=True,
                output_directory=media_directory,
                phase="render video",
            )
            self._record_phase("render video", video_result, log_path)
            require_success("Rendering the Arabic video", video_result, self.config.render_timeout)

            preview_result = executor.run_container(
                self.config.image,
                (
                    "manim",
                    "-ql",
                    "-s",
                    "--format=png",
                    SCENE_PATH,
                    SCENE_NAME,
                    "--media_dir",
                    "/workspace/output/preview",
                ),
                log_path,
                self.config.render_timeout,
                include_source_mount=True,
                output_directory=media_directory,
                phase="render preview",
            )
            self._record_phase("render preview", preview_result, log_path)
            require_success(
                "Rendering the Arabic preview", preview_result, self.config.render_timeout
            )

            video_path = first_artifact(
                media_directory / "video",
                f"{SCENE_NAME}.mp4",
                "MP4 video",
            )
            preview_path = first_artifact(
                media_directory / "preview",
                f"{SCENE_NAME}*.png",
                "PNG preview",
            )
            self._validate_video(executor, media_directory, video_path, log_path)
            validate_png(preview_path)

            draft_path = run_directory / "draft.mp4"
            still_path = run_directory / "preview.png"
            shutil.copy2(video_path, draft_path)
            shutil.copy2(preview_path, still_path)
            manifest.status = "succeeded"
            manifest.outputs = {
                "video": str(draft_path.relative_to(run_directory)),
                "preview": str(still_path.relative_to(run_directory)),
                "log": str(log_path.relative_to(run_directory)),
                "raw_media": str(media_directory.relative_to(run_directory)),
            }
            manifest.write(run_directory)
            return SmokeResult(run_directory, draft_path, still_path, manifest)
        except (DockerError, OSError, SmokeError) as error:
            manifest.status = "failed"
            manifest.failure = str(error)
            manifest.write(run_directory)
            if isinstance(error, SmokeError):
                raise
            raise SmokeError(str(error)) from error

    def _record_phase(self, name: str, result: CommandResult, log_path: Path) -> None:
        """Persist each phase before deciding whether the run can continue."""
        assert self.run_directory is not None
        assert self.manifest is not None
        self.manifest.phases.append(result.as_phase_record(name, log_path, self.run_directory))
        self.manifest.write(self.run_directory)

    def _validate_video(
        self,
        executor: DockerExecutor,
        media_directory: Path,
        video_path: Path,
        log_path: Path,
    ) -> None:
        """Ask the same pinned image to parse the produced MP4."""
        relative_path = video_path.relative_to(media_directory)
        container_path = Path("/workspace/output") / relative_path
        result = executor.run_container(
            self.config.image,
            (
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(container_path),
            ),
            log_path,
            self.config.render_timeout,
            output_directory=media_directory,
            output_read_only=True,
            phase="validate video",
        )
        self._record_phase("validate video", result, log_path)
        require_success("Validating the MP4 video", result, self.config.render_timeout)
        if not result.output_tail.strip():
            raise SmokeError("The MP4 video has no readable duration. See render.log.")


def allocate_run_directory(output_root: Path) -> Path:
    """Create a fresh run directory without a time-of-check race."""
    output_root.mkdir(parents=True, exist_ok=True)
    suffix = 0
    while True:
        name = "run" if suffix == 0 else f"run-{suffix:03d}"
        candidate = output_root / name
        try:
            candidate.mkdir()
        except FileExistsError:
            suffix += 1
            continue
        return candidate


def current_container_user() -> tuple[str, str]:
    """Return a non-root UID and GID for the container process."""
    uid = os.getuid() if hasattr(os, "getuid") else 10001
    gid = os.getgid() if hasattr(os, "getgid") else 10001
    if uid == 0:
        return "10001", "10001"
    return str(uid), str(gid)


def first_artifact(directory: Path, pattern: str, label: str) -> Path:
    """Find exactly one final artifact matching a safe output pattern."""
    matches = sorted(path for path in directory.rglob(pattern) if path.is_file())
    if not matches:
        raise SmokeError(f"The container finished, but no {label} was found. See render.log.")
    if len(matches) > 1:
        locations = ", ".join(str(path.relative_to(directory)) for path in matches)
        raise SmokeError(f"Expected one {label}, but found {len(matches)}: {locations}")
    artifact = matches[0]
    if artifact.stat().st_size == 0:
        raise SmokeError(f"The {label} is empty: {artifact}")
    return artifact


def validate_png(path: Path) -> None:
    """Validate the PNG signature before exposing the preview artifact."""
    with path.open("rb") as image:
        signature = image.read(8)
    if signature != b"\x89PNG\r\n\x1a\n":
        raise SmokeError(f"The preview is not a valid PNG file: {path}")


def source_hashes(project_root: Path) -> dict[str, str]:
    """Hash the build inputs and mounted scene code into the manifest."""
    files = {
        "Dockerfile": project_root / "Dockerfile",
        ".dockerignore": project_root / ".dockerignore",
        "container/pyproject.toml": project_root / "container/pyproject.toml",
        "container/uv.lock": project_root / "container/uv.lock",
        "scripts/container_smoke.py": project_root / "scripts/container_smoke.py",
        "bayan/renderer/docker.py": project_root / "bayan/renderer/docker.py",
        "bayan/renderer/errors.py": project_root / "bayan/renderer/errors.py",
        "bayan/renderer/models.py": project_root / "bayan/renderer/models.py",
        "bayan/renderer/process.py": project_root / "bayan/renderer/process.py",
        "bayan/renderer/security.py": project_root / "bayan/renderer/security.py",
        "bayan/renderer/smoke.py": project_root / "bayan/renderer/smoke.py",
        "bayan/utils/arabic_helper.py": project_root / "bayan/utils/arabic_helper.py",
        "bayan/utils/sanity_check.py": project_root / "bayan/utils/sanity_check.py",
    }
    return {name: sha256_file(path) for name, path in files.items()}


def sha256_file(path: Path) -> str:
    """Hash a file in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_success(phase: str, result: CommandResult, timeout_seconds: int) -> None:
    """Turn a bounded command result into a plain-English failure."""
    if result.succeeded:
        return
    if result.timed_out:
        raise SmokeError(f"{phase} exceeded its {timeout_seconds}-second limit. See render.log.")
    if result.output_limited:
        raise SmokeError(f"{phase} exceeded its output limit. See render.log.")
    detail = (result.error or result.output_tail).strip().splitlines()
    summary = detail[-1] if detail else "No diagnostic was returned."
    code = result.returncode if result.returncode is not None else "unknown"
    raise SmokeError(f"{phase} failed with exit code {code}: {summary}")


def _prepare_media_directory(directory: Path, uid: str, gid: str) -> None:
    """Make the dedicated output bind mount writable for a root host user."""
    if os.getuid() != 0 or not hasattr(os, "chown"):
        return
    try:
        os.chown(directory, int(uid), int(gid))
    except OSError:
        directory.chmod(0o777)
