"""Docker lifecycle for untrusted Manim render workers."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

from bayan.renderer.errors import DockerError
from bayan.renderer.models import ImageMetadata, RenderSettings
from bayan.renderer.process import BoundedProcessRunner, CaptureResult, CommandResult
from bayan.renderer.security import docker_environment, security_args


def check_docker() -> tuple[str, str]:
    """Check that Docker is installed and its daemon is reachable."""
    docker = shutil.which("docker")
    if docker is None:
        raise DockerError(
            "Docker CLI was not found. Install Docker Desktop or Docker Engine, "
            "then run `docker info` and try again."
        )

    try:
        completed = subprocess.run(
            [docker, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=docker_environment(Path("/tmp/bayan-docker-check")),
            timeout=20,
        )
    except subprocess.TimeoutExpired as error:
        raise DockerError("Docker daemon did not respond within 20 seconds.") from error
    except OSError as error:
        raise DockerError(f"Docker preflight failed: {error}") from error

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise DockerError(
            "Docker is installed, but its daemon is unavailable. Start Docker and "
            f"give your user access to it. Details: {details}"
        )
    return docker, completed.stdout.strip()


class DockerExecutor:
    """Execute Docker builds and containers with explicit limits and cleanup."""

    def __init__(
        self,
        docker: str,
        run_directory: Path,
        source_directory: Path,
        container_user: str,
        settings: RenderSettings,
    ) -> None:
        self.docker = docker
        self.run_directory = run_directory
        self.source_directory = source_directory.resolve()
        self.container_user = container_user
        self.settings = settings
        self.environment = docker_environment(run_directory / ".docker-home")
        self.process = BoundedProcessRunner(
            self.environment,
            settings.max_log_bytes_per_phase,
        )

    def build_image(
        self,
        image: str,
        dockerfile: Path,
        context: Path,
        log_path: Path,
    ) -> CommandResult:
        """Build the image with a bounded log and a hard timeout."""
        command = (
            self.docker,
            "build",
            "--tag",
            image,
            "--file",
            str(dockerfile),
            str(context),
        )
        return self._run_streaming(
            command, "build image", log_path, self.settings.build_timeout_seconds
        )

    def inspect_image(self, image: str) -> ImageMetadata:
        """Read typed metadata from the exact local image used by the run."""
        captured = self._capture((self.docker, "image", "inspect", image), 20)
        if captured.returncode != 0:
            raise DockerError(
                f"The image {image!r} is not available. Build it first or remove `--skip-build`."
            )
        try:
            parsed: object = json.loads(captured.stdout)
        except json.JSONDecodeError as error:
            raise DockerError(f"Docker returned invalid metadata for image {image!r}.") from error

        if not isinstance(parsed, list) or not parsed or not isinstance(parsed[0], dict):
            raise DockerError(f"Docker returned an unexpected metadata shape for image {image!r}.")
        data = cast(dict[str, object], parsed[0])
        return ImageMetadata(
            reference=image,
            image_id=_optional_string(data, "Id"),
            repo_digests=_string_tuple(data.get("RepoDigests")),
            architecture=_optional_string(data, "Architecture"),
            operating_system=_optional_string(data, "Os"),
        )

    def run_container(
        self,
        image: str,
        command: Sequence[str],
        log_path: Path,
        timeout_seconds: int,
        *,
        include_source_mount: bool = False,
        output_directory: Path | None = None,
        output_read_only: bool = False,
        phase: str,
    ) -> CommandResult:
        """Run one container and forcibly remove it on every exit path."""
        container_name = self._container_name(phase)
        create_command = self.create_command(
            image,
            command,
            container_name=container_name,
            include_source_mount=include_source_mount,
            output_directory=output_directory,
            output_read_only=output_read_only,
        )
        created = self._capture(create_command, 30)
        self._append_capture(log_path, f"{phase} create", create_command, created)
        if created.timed_out:
            cleanup_error = self._cleanup_container(container_name, phase, log_path)
            return CommandResult(
                command=create_command,
                returncode=124,
                timed_out=True,
                error="Docker could not create the worker container within 30 seconds.",
                cleanup_error=cleanup_error,
            )
        if created.returncode != 0:
            detail = _tail_text(created.stderr or created.stdout).strip()
            return CommandResult(
                command=create_command,
                returncode=created.returncode,
                error=detail or "Docker could not create the worker container.",
            )

        start_command = (self.docker, "start", "--attach", container_name)
        result = CommandResult(
            command=start_command,
            returncode=None,
            error="Docker worker did not return a result.",
        )
        try:
            result = self._run_streaming(start_command, phase, log_path, timeout_seconds)
        finally:
            cleanup_error = self._cleanup_container(container_name, phase, log_path)
            if cleanup_error:
                result = replace(result, cleanup_error=cleanup_error)
        return result

    def create_command(
        self,
        image: str,
        command: Sequence[str],
        *,
        container_name: str | None = None,
        include_source_mount: bool,
        output_directory: Path | None,
        output_read_only: bool,
    ) -> tuple[str, ...]:
        """Build a Docker create command with the complete security policy."""
        args = security_args(
            self.container_user,
            self.settings,
            source_directory=self.source_directory if include_source_mount else None,
            output_directory=output_directory,
            output_read_only=output_read_only,
        )
        if container_name is not None:
            args.extend(("--name", container_name))
        return (self.docker, *args, image, *(str(part) for part in command))

    def _container_name(self, phase: str) -> str:
        """Create a deterministic, run-scoped name for cleanup by name."""
        seed = f"{self.run_directory.resolve()}:{phase}".encode()
        suffix = hashlib.sha256(seed).hexdigest()[:16]
        return f"bayan-smoke-{suffix}"

    def _cleanup_container(self, name: str, phase: str, log_path: Path) -> str | None:
        """Remove a worker by its run-scoped name and report cleanup failures."""
        cleanup_command = (self.docker, "rm", "--force", name)
        cleanup = self._capture(cleanup_command, 30)
        self._append_capture(log_path, f"{phase} cleanup", cleanup_command, cleanup)
        if cleanup.timed_out:
            return "Docker did not remove the worker container within 30 seconds."
        if cleanup.returncode != 0:
            detail = _tail_text(cleanup.stderr or cleanup.stdout).strip()
            return detail or "Docker could not remove the worker container."
        return None

    def _capture(self, command: Sequence[str], timeout_seconds: int) -> CaptureResult:
        """Delegate a short Docker control-plane command to the bounded runner."""
        return self.process.capture(command, timeout_seconds)

    def _run_streaming(
        self,
        command: Sequence[str],
        phase: str,
        log_path: Path,
        timeout_seconds: int,
    ) -> CommandResult:
        """Delegate a streamed command to the bounded process runner."""
        return self.process.stream(command, phase, log_path, timeout_seconds)

    def _append_capture(
        self,
        log_path: Path,
        phase: str,
        command: Sequence[str],
        result: CaptureResult,
    ) -> None:
        """Append a bounded Docker control-plane response to the log."""
        self.process.append_capture(log_path, phase, command, result)


def _tail_text(value: bytes | str, limit: int = 4096) -> str:
    """Return only the final bounded portion of a diagnostic value."""
    if isinstance(value, bytes):
        return value[-limit:].decode("utf-8", errors="replace")
    return value[-limit:]


def _optional_string(data: dict[str, object], key: str) -> str | None:
    """Read an optional string from Docker's untyped JSON response."""
    value = data.get(key)
    return value if isinstance(value, str) else None


def _string_tuple(value: object) -> tuple[str, ...]:
    """Read a string list from Docker's untyped JSON response."""
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))
