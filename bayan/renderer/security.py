"""Environment, resource, and mount policy for render containers."""

from __future__ import annotations

import os
from pathlib import Path

from bayan.renderer.errors import DockerError
from bayan.renderer.models import RenderSettings


def docker_environment(home: Path) -> dict[str, str]:
    """Return an allowlisted environment for Docker CLI subprocesses."""
    path = os.environ.get("PATH", "/usr/bin:/bin")
    return {
        "PATH": path,
        "HOME": str(home),
        "DOCKER_CONFIG": str(home / "config"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def security_args(
    user: str,
    settings: RenderSettings,
    *,
    source_directory: Path | None,
    output_directory: Path | None,
    output_read_only: bool,
) -> list[str]:
    """Return the common, explicit container restrictions."""
    args = [
        "create",
        "--network",
        settings.network,
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(settings.pids_limit),
        "--cpus",
        settings.cpu_limit,
        "--memory",
        settings.memory_limit,
        "--stop-timeout",
        "10",
        "--user",
        user,
        "--tmpfs",
        f"/tmp:rw,noexec,nosuid,size={settings.tmpfs_size}",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "XDG_CACHE_HOME=/tmp/cache",
        "--env",
        "LANG=C.UTF-8",
        "--env",
        "LC_ALL=C.UTF-8",
        "--env",
        "PYTHONNOUSERSITE=1",
    ]
    if source_directory is not None:
        args.extend(
            [
                "--mount",
                _mount_spec(source_directory, "/workspace/bayan", read_only=True),
            ]
        )
    if output_directory is not None:
        args.extend(
            [
                "--mount",
                _mount_spec(output_directory, "/workspace/output", read_only=output_read_only),
            ]
        )
    return args


def _mount_spec(source: Path, destination: str, *, read_only: bool) -> str:
    """Build a bind mount value and reject ambiguous comma-containing paths."""
    resolved = source.resolve()
    if "," in str(resolved):
        raise DockerError(f"Docker bind mount paths cannot contain commas: {resolved}")
    suffix = ",readonly" if read_only else ""
    return f"type=bind,source={resolved},destination={destination}{suffix}"
