"""Run the known-good Arabic scene inside a bounded Docker container."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = "bayan/manim-smoke:0.20.1"
DEFAULT_OUTPUT_ROOT = Path("artifacts/container-smoke")
SCENE_PATH = "/workspace/bayan/utils/sanity_check.py"
SCENE_NAME = "ArabicSanityCheck"


class CommandResult(NamedTuple):
    """The captured result of one external command."""

    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class SmokeError(RuntimeError):
    """A recoverable setup or render failure with a user-facing message."""


def allocate_run_directory(output_root: Path) -> Path:
    """Create a fresh run directory without deleting an earlier run."""
    output_root.mkdir(parents=True, exist_ok=True)
    candidate = output_root / "run"
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = output_root / f"run-{suffix:03d}"
    candidate.mkdir()
    return candidate


def current_container_user() -> tuple[str, str]:
    """Return a non-root UID and GID for the container process."""
    uid = os.getuid() if hasattr(os, "getuid") else 10001
    gid = os.getgid() if hasattr(os, "getgid") else 10001
    if uid == 0:
        return "10001", "10001"
    return str(uid), str(gid)


def run_command(command: Sequence[str], timeout: int) -> CommandResult:
    """Run a command without a shell and capture bounded diagnostic output."""
    normalized = tuple(str(part) for part in command)
    try:
        completed = subprocess.run(
            normalized,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as error:
        return CommandResult(normalized, 127, "", str(error))
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        message = f"Command timed out after {timeout}s.\n{stderr}"
        return CommandResult(normalized, 124, stdout, message)

    return CommandResult(normalized, completed.returncode, completed.stdout, completed.stderr)


def check_docker() -> tuple[str, str]:
    """Check that the Docker CLI and daemon are available before creating a run."""
    docker = shutil.which("docker")
    if docker is None:
        raise SmokeError(
            "Docker CLI was not found. Install Docker Desktop or Docker Engine, "
            "then run `docker info` and try again."
        )

    result = run_command([docker, "info", "--format", "{{.ServerVersion}}"], timeout=20)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise SmokeError(
            "Docker is installed, but its daemon is unavailable. Start Docker and "
            f"give your user access to it. Details: {details}"
        )
    return docker, result.stdout.strip()


def image_metadata(docker: str, image: str) -> dict[str, Any]:
    """Read the local image ID and repository digests for the manifest."""
    result = run_command([docker, "image", "inspect", image], timeout=20)
    if result.returncode != 0:
        raise SmokeError(
            f"The image {image!r} is not available. Build it first or remove `--skip-build`."
        )

    try:
        image_data = json.loads(result.stdout)[0]
    except (IndexError, json.JSONDecodeError) as error:
        message = f"Docker returned invalid metadata for image {image!r}: {error}"
        raise SmokeError(message) from error

    return {
        "reference": image,
        "id": image_data.get("Id"),
        "repo_digests": image_data.get("RepoDigests", []),
        "architecture": image_data.get("Architecture"),
        "os": image_data.get("Os"),
    }


def security_args(user: str, include_output_mount: bool = False) -> list[str]:
    """Return the common container restrictions used for every worker command."""
    args = [
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "128",
        "--cpus",
        "2",
        "--memory",
        "2g",
        "--stop-timeout",
        "10",
        "--user",
        user,
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=512m",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "XDG_CACHE_HOME=/tmp/cache",
    ]
    if include_output_mount:
        args.extend(
            [
                "--mount",
                "type=bind,source={source},destination=/workspace/bayan,readonly".format(
                    source=PROJECT_ROOT / "bayan"
                ),
            ]
        )
    return args


def worker_command(
    docker: str,
    image: str,
    user: str,
    output_dir: Path | None,
    command: Sequence[str],
) -> list[str]:
    """Build one Docker command with only the required mounts."""
    args = [docker, *security_args(user, include_output_mount=output_dir is not None)]
    if output_dir is not None:
        args.extend(
            [
                "--mount",
                f"type=bind,source={output_dir},destination=/workspace/output",
            ]
        )
    args.extend([image, *command])
    return args


def write_phase_log(log_path: Path, phase: str, result: CommandResult) -> None:
    """Append a phase result without exposing environment secrets."""
    command = " ".join(shlex.quote(part) for part in result.command)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"## {phase}\n$ {command}\nexit_code={result.returncode}\n")
        if result.stdout:
            log.write(f"stdout:\n{result.stdout}\n")
        if result.stderr:
            log.write(f"stderr:\n{result.stderr}\n")


def record_phase(
    manifest: dict[str, Any], phase: str, result: CommandResult, log_path: Path
) -> None:
    """Record a phase result using a path relative to the run directory."""
    run_dir = log_path.parent
    manifest["phases"].append(
        {
            "name": phase,
            "command": list(result.command),
            "returncode": result.returncode,
            "log": str(log_path.relative_to(run_dir)),
        }
    )


def write_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Write the current manifest atomically enough for a local smoke run."""
    manifest_path = run_dir / "smoke_manifest.json"
    temporary_path = run_dir / "smoke_manifest.json.tmp"
    temporary_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(manifest_path)


def require_success(phase: str, result: CommandResult, timeout: int) -> None:
    """Turn an external command failure into a plain-English smoke error."""
    if result.returncode == 0:
        return
    if result.returncode == 124:
        raise SmokeError(f"{phase} exceeded its {timeout}-second limit. See render.log.")
    detail = (result.stderr or result.stdout).strip().splitlines()
    summary = detail[-1] if detail else "No diagnostic was returned."
    raise SmokeError(f"{phase} failed with exit code {result.returncode}: {summary}")


def first_artifact(directory: Path, pattern: str, label: str) -> Path:
    """Find one Manim artifact or raise a useful failure."""
    matches = sorted(directory.rglob(pattern))
    if not matches:
        raise SmokeError(f"The container finished, but no {label} was found. See render.log.")
    return matches[0]


def parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the smoke runner."""
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag to build and run.")
    result.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output directory root. A fresh run directory is created inside it.",
    )
    result.add_argument(
        "--skip-build",
        action="store_true",
        help="Use an existing image instead of building it.",
    )
    result.add_argument("--build-timeout", type=int, default=900, help="Build timeout in seconds.")
    result.add_argument(
        "--render-timeout", type=int, default=180, help="Render timeout in seconds."
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Build the image, render the smoke scene, and write a reproducibility manifest."""
    args = parser().parse_args(argv)
    docker: str | None = None
    run_dir: Path | None = None
    manifest: dict[str, Any] | None = None

    try:
        docker, docker_server = check_docker()
        output_root = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
        run_dir = allocate_run_directory(output_root.resolve())
        media_dir = run_dir / "manim-output"
        media_dir.mkdir()
        log_path = run_dir / "render.log"
        uid, gid = current_container_user()
        container_user = f"{uid}:{gid}"
        manifest = {
            "schema_version": 1,
            "status": "running",
            "scene": SCENE_NAME,
            "quality": "low",
            "docker_server": docker_server,
            "container_user": container_user,
            "settings": {
                "network": "none",
                "read_only_root": True,
                "cpu_limit": "2",
                "memory_limit": "2g",
                "pids_limit": 128,
                "render_timeout_seconds": args.render_timeout,
            },
            "image": {"reference": args.image},
            "phases": [],
            "outputs": {},
            "failure": None,
        }
        write_manifest(run_dir, manifest)

        if not args.skip_build:
            build_result = run_command(
                [
                    docker,
                    "build",
                    "--tag",
                    args.image,
                    "--file",
                    str(PROJECT_ROOT / "Dockerfile"),
                    str(PROJECT_ROOT),
                ],
                timeout=args.build_timeout,
            )
            write_phase_log(log_path, "build image", build_result)
            record_phase(manifest, "build image", build_result, log_path)
            write_manifest(run_dir, manifest)
            require_success("Building the container image", build_result, args.build_timeout)

        manifest["image"] = image_metadata(docker, args.image)
        write_manifest(run_dir, manifest)

        font_result = run_command(
            worker_command(
                docker,
                args.image,
                container_user,
                None,
                ["fc-match", "--format=%{family}\\n", "Noto Sans Arabic"],
            ),
            timeout=args.render_timeout,
        )
        write_phase_log(log_path, "check Arabic font", font_result)
        record_phase(manifest, "check Arabic font", font_result, log_path)
        write_manifest(run_dir, manifest)
        require_success("Checking the Arabic font", font_result, args.render_timeout)
        if not font_result.stdout.strip():
            raise SmokeError(
                "The container has no usable Noto Sans Arabic font. Rebuild the image."
            )

        video_result = run_command(
            worker_command(
                docker,
                args.image,
                container_user,
                media_dir,
                [
                    "manim",
                    "-ql",
                    SCENE_PATH,
                    SCENE_NAME,
                    "--media_dir",
                    "/workspace/output/video",
                ],
            ),
            timeout=args.render_timeout,
        )
        write_phase_log(log_path, "render video", video_result)
        record_phase(manifest, "render video", video_result, log_path)
        write_manifest(run_dir, manifest)
        require_success("Rendering the Arabic video", video_result, args.render_timeout)

        preview_result = run_command(
            worker_command(
                docker,
                args.image,
                container_user,
                media_dir,
                [
                    "manim",
                    "-ql",
                    "-s",
                    "--format=png",
                    SCENE_PATH,
                    SCENE_NAME,
                    "--media_dir",
                    "/workspace/output/preview",
                ],
            ),
            timeout=args.render_timeout,
        )
        write_phase_log(log_path, "render preview", preview_result)
        record_phase(manifest, "render preview", preview_result, log_path)
        write_manifest(run_dir, manifest)
        require_success("Rendering the Arabic preview", preview_result, args.render_timeout)

        video_path = first_artifact(media_dir / "video", "*.mp4", "MP4 video")
        preview_path = first_artifact(media_dir / "preview", "*.png", "PNG preview")
        draft_path = run_dir / "draft.mp4"
        still_path = run_dir / "preview.png"
        shutil.copy2(video_path, draft_path)
        shutil.copy2(preview_path, still_path)
        manifest["status"] = "succeeded"
        manifest["outputs"] = {
            "video": str(draft_path.relative_to(run_dir)),
            "preview": str(still_path.relative_to(run_dir)),
            "log": str(log_path.relative_to(run_dir)),
            "raw_media": str(media_dir.relative_to(run_dir)),
        }
        write_manifest(run_dir, manifest)
        print(f"Smoke render succeeded. Run directory: {run_dir}")
        print(f"Video: {draft_path}")
        print(f"Preview: {still_path}")
        return 0
    except (OSError, SmokeError) as error:
        if run_dir is not None and manifest is not None:
            manifest["status"] = "failed"
            manifest["failure"] = {"message": str(error)}
            write_manifest(run_dir, manifest)
            print(f"Smoke render failed. Run directory: {run_dir}", file=sys.stderr)
        print(f"Smoke render failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
