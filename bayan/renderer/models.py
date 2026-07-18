"""Serializable models for an isolated render run."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

RunStatus = Literal["running", "succeeded", "failed"]
PhaseStatus = Literal["passed", "failed", "timed_out", "output_limited"]


@dataclass(frozen=True)
class RenderSettings:
    """Security and resource settings applied to every render container."""

    network: str = "none"
    read_only_root: bool = True
    cpu_limit: str = "2"
    memory_limit: str = "2g"
    pids_limit: int = 128
    tmpfs_size: str = "512m"
    build_timeout_seconds: int = 900
    render_timeout_seconds: int = 180
    max_log_bytes_per_phase: int = 1_048_576
    build_skipped: bool = False

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""
        return {
            "network": self.network,
            "read_only_root": self.read_only_root,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "pids_limit": self.pids_limit,
            "tmpfs_size": self.tmpfs_size,
            "build_timeout_seconds": self.build_timeout_seconds,
            "render_timeout_seconds": self.render_timeout_seconds,
            "max_log_bytes_per_phase": self.max_log_bytes_per_phase,
            "build_skipped": self.build_skipped,
        }


@dataclass(frozen=True)
class ImageMetadata:
    """Metadata captured from the image actually used for a run."""

    reference: str
    image_id: str | None = None
    repo_digests: tuple[str, ...] = ()
    architecture: str | None = None
    operating_system: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""
        return {
            "reference": self.reference,
            "image_id": self.image_id,
            "repo_digests": list(self.repo_digests),
            "architecture": self.architecture,
            "os": self.operating_system,
        }


@dataclass(frozen=True)
class PhaseRecord:
    """The durable result of one build, validation, or render phase."""

    name: str
    status: PhaseStatus
    command: tuple[str, ...]
    returncode: int | None
    log: str
    output_limited: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""
        return {
            "name": self.name,
            "status": self.status,
            "command": list(self.command),
            "returncode": self.returncode,
            "log": self.log,
            "output_limited": self.output_limited,
            "error": self.error,
        }


@dataclass
class SmokeManifest:
    """Typed manifest written during and after a smoke run."""

    scene: str
    quality: str
    docker_server: str
    container_user: str
    settings: RenderSettings
    image: ImageMetadata
    source_hashes: dict[str, str] = field(default_factory=dict)
    status: RunStatus = "running"
    phases: list[PhaseRecord] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    failure: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the public JSON shape of the manifest."""
        return {
            "schema_version": 2,
            "status": self.status,
            "scene": self.scene,
            "quality": self.quality,
            "docker_server": self.docker_server,
            "container_user": self.container_user,
            "settings": self.settings.to_dict(),
            "image": self.image.to_dict(),
            "source_hashes": dict(self.source_hashes),
            "phases": [phase.to_dict() for phase in self.phases],
            "outputs": dict(self.outputs),
            "failure": self.failure,
        }

    def write(self, run_directory: Path) -> None:
        """Atomically update the manifest in the run directory."""
        manifest_path = run_directory / "smoke_manifest.json"
        temporary_path = run_directory / "smoke_manifest.json.tmp"
        temporary_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(manifest_path)
