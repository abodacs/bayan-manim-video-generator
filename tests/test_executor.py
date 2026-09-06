from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from bayan.renderer.docker import DockerExecutor
from bayan.renderer.executor import RenderError, render_scene_code
from bayan.renderer.models import ImageMetadata, RenderSettings
from bayan.renderer.process import CommandResult
from bayan.renderer.smoke import CONTAINER_OUTPUT_ROOT, MAX_RETAINED_RUN_DIRECTORIES

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
        command: Sequence[str],
        log_path: Path,
        timeout_seconds: int,
        **kwargs: object,
    ) -> CommandResult:
        del image, log_path, timeout_seconds
        if rendered is not None:
            rendered.append(tuple(str(part) for part in command))
        run_dir = cast(Path, kwargs["output_directory"])
        (run_dir / "media" / "video").mkdir(parents=True, exist_ok=True)
        (run_dir / "media" / "video" / "GeneratedScene.mp4").write_bytes(b"fake video bytes")
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
    run_dirs = list((tmp_path / "final-runs").iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "generated_scene.py").read_text(encoding="utf-8") == GENERATED_CODE
    # The generated scene runs from the writable output mount, never the host.
    assert rendered[0][rendered[0].index("--media_dir") - 2] == str(
        CONTAINER_OUTPUT_ROOT / "generated_scene.py"
    )
    assert rendered[0][rendered[0].index("--media_dir") + 1] == "/workspace/output/media/video"


def test_render_scene_code_mounts_only_a_fresh_run_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The untrusted scene may only ever write inside its fresh run directory."""
    executor = DockerExecutor(
        docker="docker",
        run_directory=tmp_path,
        source_directory=tmp_path,
        container_user="1000:1000",
        settings=RenderSettings(render_timeout_seconds=77),
    )
    monkeypatch.setattr(executor, "inspect_image", lambda image: ImageMetadata(reference=image))
    argvs: list[tuple[str, ...]] = []
    timeouts: list[int] = []

    def spy_run_container(
        image: str,
        command: Sequence[str],
        log_path: Path,
        timeout_seconds: int,
        **kwargs: object,
    ) -> CommandResult:
        del log_path
        timeouts.append(timeout_seconds)
        argvs.append(
            executor.create_command(
                image,
                command,
                container_name="render-spy",
                include_source_mount=cast(bool, kwargs["include_source_mount"]),
                output_directory=cast(Path, kwargs["output_directory"]),
                output_read_only=cast(bool, kwargs.get("output_read_only", False)),
            )
        )
        run_dir = cast(Path, kwargs["output_directory"])
        (run_dir / "media" / "video").mkdir(parents=True, exist_ok=True)
        (run_dir / "media" / "video" / "GeneratedScene.mp4").write_bytes(b"fake video bytes")
        return CommandResult(command=("docker",), returncode=0, output_tail="done\n")

    monkeypatch.setattr(executor, "run_container", spy_run_container)

    output_path = render_scene_code(
        GENERATED_CODE, output_path=tmp_path / "final.mp4", executor=executor
    )

    assert output_path.read_bytes() == b"fake video bytes"
    # The executor's settings drive the timeout, not a detached module constant.
    assert timeouts == [77]

    argv = argvs[0]
    assert argv[0:2] == ("docker", "create")
    assert "--read-only" in argv
    assert "--cap-drop=ALL" in argv
    assert "1000:1000" in argv
    specs = [token for index, token in enumerate(argv) if argv[index - 1] == "--mount"]
    writable = [spec for spec in specs if not spec.endswith(",readonly")]
    assert len(writable) == 1  # exactly one writable mount ...
    source = Path(writable[0].split("source=", 1)[1].split(",", 1)[0])
    assert source.parent == (tmp_path / "final-runs").resolve()  # ... under the run root ...
    assert source.name == "run" or source.name.startswith("run-")
    assert source != tmp_path.resolve()  # ... and never the output parent itself.
    assert any(spec.endswith("destination=/workspace/bayan,readonly") for spec in specs)

    # Nothing leaks next to the requested output except the run root, the
    # video, and the host-owned render log (kept outside the writable mount).
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "final-runs",
        "final.mp4",
        "final.render.log",
    ]


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


def test_render_scene_code_prunes_old_run_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated renders to one output keep only the latest run directories."""
    executor = _fake_successful_render(tmp_path, monkeypatch)
    output_path = tmp_path / "final.mp4"

    for _ in range(MAX_RETAINED_RUN_DIRECTORIES + 2):
        render_scene_code(GENERATED_CODE, output_path=output_path, executor=executor)

    run_root = tmp_path / "final-runs"
    remaining = sorted(path.name for path in run_root.iterdir() if path.is_dir())
    assert len(remaining) == MAX_RETAINED_RUN_DIRECTORIES
    # The run directory of the most recent render is always retained.
    assert remaining[-1] != "run"
    assert output_path.read_bytes() == b"fake video bytes"
