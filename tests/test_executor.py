from pathlib import Path

import pytest

from bayan.renderer.docker import DockerExecutor
from bayan.renderer.executor import RenderError, render_scene_code
from bayan.renderer.models import ImageMetadata, RenderSettings
from bayan.renderer.process import CommandResult
from bayan.renderer.smoke import CONTAINER_OUTPUT_ROOT

GENERATED_CODE = "class GeneratedScene(Scene):\n    pass\n"


def _make_worker(tmp_path: Path) -> DockerExecutor:
    """A real executor whose Docker calls are faked per test."""
    return DockerExecutor(
        docker="docker",
        run_directory=tmp_path,
        source_directory=tmp_path,
        container_user="1000:1000",
        settings=RenderSettings(),
    )


def _fake_successful_render(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rendered: list[tuple[str, ...]] | None = None,
) -> DockerExecutor:
    executor = _make_worker(tmp_path)
    monkeypatch.setattr(executor, "inspect_image", lambda image: ImageMetadata(reference=image))

    def fake_run_container(
        image: str,
        command: object,
        log_path: Path,
        timeout_seconds: int,
        **kwargs: object,
    ) -> CommandResult:
        del image, log_path, timeout_seconds, kwargs
        if rendered is not None:
            rendered.append(tuple(str(part) for part in command))
        (tmp_path / "media" / "video").mkdir(parents=True, exist_ok=True)
        (tmp_path / "media" / "video" / "GeneratedScene.mp4").write_bytes(b"fake video bytes")
        return CommandResult(command=("docker",), returncode=0, output_tail="done\n")

    monkeypatch.setattr(executor, "run_container", fake_run_container)
    return executor


def test_render_scene_code_renders_in_the_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered)

    output_path = render_scene_code(
        GENERATED_CODE, output_path=tmp_path / "final.mp4", executor=executor
    )

    assert output_path == tmp_path / "final.mp4"
    assert output_path.read_bytes() == b"fake video bytes"
    assert (tmp_path / "generated_scene.py").read_text(encoding="utf-8") == GENERATED_CODE
    # The generated scene runs from the writable output mount, never the host.
    assert rendered[0][rendered[0].index("--media_dir") - 2] == str(
        CONTAINER_OUTPUT_ROOT / "generated_scene.py"
    )
    assert rendered[0][rendered[0].index("--media_dir") + 1] == "/workspace/output/media/video"


def test_render_scene_code_wraps_worker_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = _make_worker(tmp_path)
    monkeypatch.setattr(executor, "inspect_image", lambda image: ImageMetadata(reference=image))
    monkeypatch.setattr(
        executor,
        "run_container",
        lambda *args, **kwargs: CommandResult(
            command=("docker",), returncode=1, error="Manim raised an exception"
        ),
    )

    with pytest.raises(RenderError, match="Rendering the video"):
        render_scene_code("broken code", output_path=tmp_path / "final.mp4", executor=executor)
