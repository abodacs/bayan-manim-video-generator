"""Shared fixtures for pipeline CLI tests: the container render is faked."""

import base64
from pathlib import Path

import pytest

from bayan.renderer.models import ImageMetadata
from bayan.renderer.process import CommandResult

# A minimal valid PNG (1x1 pixel) with the required 8-byte signature.
PNG_BYTES = base64.b64decode(
    # Standard 1x1 transparent PNG.
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9aw"
    "AAAABJRU5ErkJggg=="
)
# A non-empty MP4-shaped stub; artifact collection only checks size.
MP4_BYTES = b"\x00\x00\x00\x18ftypmp42fake-manim-video-payload"


@pytest.fixture()
def fake_render(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Fabricate container render artifacts without Docker.

    Returns the list of commands the fake container run received so tests
    can assert that no container ever started.

    Patches the executor seam so ``render_scene_code`` runs fully offline:
    ``check_docker`` and ``inspect_image`` succeed without a daemon, and
    ``run_container`` writes the video/preview artifacts manim would produce
    into the run directory that is passed as the output mount.
    """

    def fake_run_container(
        self: object,
        image: str,
        command: list[str],
        log_path: Path,
        timeout_seconds: int,
        *,
        include_source_mount: bool = False,
        output_directory: Path | None = None,
        output_read_only: bool = False,
        phase: str = "",
    ) -> CommandResult:
        assert output_directory is not None
        scene_index = next(index for index, part in enumerate(command) if part.endswith(".py"))
        class_name = command[scene_index + 1]
        kind = "preview" if "--format=png" in command else "video"
        media_dir = output_directory / "media" / kind
        media_dir.mkdir(parents=True, exist_ok=True)
        artifact = media_dir / f"{class_name}.{'png' if kind == 'preview' else 'mp4'}"
        artifact.write_bytes(PNG_BYTES if kind == "preview" else MP4_BYTES)
        return CommandResult(
            command=tuple(command),
            returncode=0,
            output_tail="fake render",
        )

    monkeypatch.setattr(
        "bayan.renderer.executor.check_docker",
        lambda: (object(), "fake-docker-server"),
    )
    monkeypatch.setattr(
        "bayan.renderer.docker.DockerExecutor.inspect_image",
        lambda self, image: ImageMetadata(reference=image),
    )
    container_commands: list[tuple[str, ...]] = []

    def logging_run_container(
        self: object, image: str, command: list[str], *args: object, **kwargs: object
    ) -> CommandResult:
        container_commands.append(tuple(str(part) for part in command))
        return fake_run_container(self, image, command, *args, **kwargs)

    monkeypatch.setattr(
        "bayan.renderer.docker.DockerExecutor.run_container",
        logging_run_container,
    )
    return container_commands
