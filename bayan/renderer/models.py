"""Serializable models for an isolated render run."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from bayan.utils.atomic_io import atomic_write_text

RunStatus = Literal["running", "succeeded", "failed"]
PhaseStatus = Literal["passed", "failed", "timed_out", "output_limited"]
JobStatus = Literal["requested", "running", "succeeded", "failed"]


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
    build_cache_from: tuple[str, ...] = ()

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
            "build_cache_from": list(self.build_cache_from),
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
        atomic_write_text(
            run_directory / "smoke_manifest.json",
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
        )


@dataclass
class RenderJob:
    """Represents the lifecycle and metadata of a rendering job."""

    job_id: str
    status: JobStatus
    scene_plan_id: str
    template_id: str
    # Reproducibility evidence, mirroring SmokeManifest: the image actually
    # used, the security/resource settings applied, and a hash of the fixture
    # source that was rendered.
    image: ImageMetadata | None = None
    settings: RenderSettings | None = None
    fixture_hash: str | None = None
    quality: str | None = None
    failure_stage: str | None = None
    exit_reason: str | None = None
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible representation."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "scene_plan_id": self.scene_plan_id,
            "template_id": self.template_id,
            "image": self.image.to_dict() if self.image is not None else None,
            "settings": self.settings.to_dict() if self.settings is not None else None,
            "fixture_hash": self.fixture_hash,
            "quality": self.quality,
            "failure_stage": self.failure_stage,
            "exit_reason": self.exit_reason,
            "artifacts": dict(self.artifacts),
        }
