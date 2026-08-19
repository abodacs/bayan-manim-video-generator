import json
import sys
import time
from pathlib import Path

import pytest

from bayan.renderer.docker import DockerExecutor, check_docker
from bayan.renderer.errors import DockerError
from bayan.renderer.models import ImageMetadata, PhaseRecord, RenderSettings, SmokeManifest
from bayan.renderer.process import CaptureResult, CommandResult
from bayan.renderer.security import security_args
from bayan.renderer.smoke import (
    CONTAINER_OUTPUT_ROOT,
    FIXTURES_ROOT,
    MAX_RETAINED_RUN_DIRECTORIES,
    SmokeConfig,
    SmokeError,
    SmokeRunner,
    allocate_run_directory,
    current_container_user,
    first_artifact,
    prune_run_directories,
    validate_png,
)
from bayan.templates.catalogue import fixture_filename, get_template_catalogue


def make_executor(tmp_path: Path, *, max_log_bytes: int = 1_048_576) -> DockerExecutor:
    """Build a Docker executor without contacting a daemon."""
    run_directory = tmp_path / "run"
    run_directory.mkdir()
    return DockerExecutor(
        docker="docker",
        run_directory=run_directory,
        source_directory=tmp_path,
        container_user="1000:1000",
        settings=RenderSettings(max_log_bytes_per_phase=max_log_bytes),
    )


def test_allocate_run_directory_preserves_previous_runs(tmp_path: Path) -> None:
    first = allocate_run_directory(tmp_path / "smoke")
    second = allocate_run_directory(tmp_path / "smoke")

    assert first.name == "run"
    assert second.name == "run-001"
    assert first.exists()
    assert second.exists()


def test_prune_run_directories_keeps_the_newest(tmp_path: Path) -> None:
    run_root = tmp_path / "render-runs"
    run_root.mkdir()
    created = [allocate_run_directory(run_root) for _ in range(MAX_RETAINED_RUN_DIRECTORIES + 3)]
    # A foreign directory and file must never be pruned.
    (run_root / "evidence").mkdir()
    (run_root / "notes.txt").write_text("keep me", encoding="utf-8")

    prune_run_directories(run_root)

    remaining = {path.name for path in run_root.iterdir()}
    expected = {path.name for path in created[3:]}  # the 3 oldest run dirs are pruned
    expected |= {"evidence", "notes.txt"}
    assert remaining == expected
    assert (run_root / "notes.txt").read_text(encoding="utf-8") == "keep me"


def test_security_args_deny_network_and_host_privileges(tmp_path: Path) -> None:
    args = security_args(
        "1000:1000",
        RenderSettings(),
        source_directory=tmp_path / "source",
        output_directory=tmp_path / "output",
        output_read_only=False,
    )

    assert args[0] == "create"
    assert "none" in args
    assert "--read-only" in args
    assert "--cap-drop=ALL" in args
    assert "no-new-privileges" in args
    assert "--user" in args
    assert "1000:1000" in args
    assert "destination=/workspace/bayan,readonly" in " ".join(args)
    assert "destination=/workspace/output" in " ".join(args)


def test_executor_command_has_a_run_scoped_container_name(tmp_path: Path) -> None:
    executor = make_executor(tmp_path)

    command = executor.create_command(
        "bayan/manim-smoke:0.20.1",
        ("fc-match", "Noto Sans Arabic"),
        container_name="bayan-smoke-test",
        include_source_mount=False,
        output_directory=None,
        output_read_only=False,
    )

    assert command[0:2] == ("docker", "create")
    assert ("--name", "bayan-smoke-test") in zip(command, command[1:], strict=False)
    assert command[-3:] == ("bayan/manim-smoke:0.20.1", "fc-match", "Noto Sans Arabic")


def test_current_container_user_never_returns_root() -> None:
    uid, gid = current_container_user()

    assert uid != "0"
    assert gid.isdigit()


def test_check_docker_explains_missing_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bayan.renderer.docker.shutil.which", lambda _: None)

    with pytest.raises(DockerError, match="Docker CLI was not found"):
        check_docker()


def test_runner_reports_missing_docker_as_a_user_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_preflight() -> tuple[str, str]:
        raise DockerError("Docker daemon is unavailable")

    monkeypatch.setattr("bayan.renderer.smoke.check_docker", fail_preflight)

    with pytest.raises(SmokeError, match="Docker daemon is unavailable"):
        SmokeRunner(SmokeConfig(output_root=tmp_path)).run()


def test_first_artifact_rejects_missing_multiple_and_empty_files(tmp_path: Path) -> None:
    directory = tmp_path / "video"

    with pytest.raises(SmokeError, match="no MP4 video"):
        first_artifact(directory, "ArabicSanityCheck.mp4", "MP4 video")

    (directory / "a").mkdir(parents=True)
    (directory / "b").mkdir()
    (directory / "a" / "ArabicSanityCheck.mp4").write_bytes(b"video")
    (directory / "b" / "ArabicSanityCheck.mp4").write_bytes(b"video")
    with pytest.raises(SmokeError, match="Expected one MP4 video"):
        first_artifact(directory, "ArabicSanityCheck.mp4", "MP4 video")

    (directory / "b" / "ArabicSanityCheck.mp4").unlink()
    (directory / "a" / "ArabicSanityCheck.mp4").write_bytes(b"")
    with pytest.raises(SmokeError, match="is empty"):
        first_artifact(directory, "ArabicSanityCheck.mp4", "MP4 video")


def test_validate_png_checks_signature(tmp_path: Path) -> None:
    valid = tmp_path / "valid.png"
    valid.write_bytes(b"\x89PNG\r\n\x1a\nrest")
    validate_png(valid)

    invalid = tmp_path / "invalid.png"
    invalid.write_bytes(b"not-png")
    with pytest.raises(SmokeError, match="not a valid PNG"):
        validate_png(invalid)


def test_manifest_is_typed_and_json_serializable(tmp_path: Path) -> None:
    manifest = SmokeManifest(
        scene="ArabicSanityCheck",
        quality="low",
        docker_server="27.0",
        container_user="1000:1000",
        settings=RenderSettings(),
        image=ImageMetadata(reference="bayan/manim-smoke:0.20.1", image_id="sha256:test"),
        source_hashes={"Dockerfile": "abc"},
        phases=[
            PhaseRecord(
                name="check Arabic font",
                status="passed",
                command=("fc-match",),
                returncode=0,
                log="render.log",
            )
        ],
    )
    manifest.write(tmp_path)

    saved = json.loads((tmp_path / "smoke_manifest.json").read_text(encoding="utf-8"))
    assert saved["schema_version"] == 2
    assert saved["status"] == "running"
    assert saved["image"]["image_id"] == "sha256:test"
    assert saved["phases"][0]["status"] == "passed"


def test_cleanup_runs_after_a_timed_out_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = make_executor(tmp_path)
    log_path = tmp_path / "render.log"
    log_path.touch()
    captured_commands: list[tuple[str, ...]] = []

    def fake_capture(command: tuple[str, ...], timeout_seconds: int) -> CaptureResult:
        del timeout_seconds
        captured_commands.append(command)
        if command[1] == "create":
            return CaptureResult(returncode=0, stdout="container-id\n")
        return CaptureResult(returncode=0)

    monkeypatch.setattr(executor, "_capture", fake_capture)
    monkeypatch.setattr(
        executor.process,
        "stream",
        lambda command, phase, log, timeout: CommandResult(
            tuple(command), returncode=124, timed_out=True
        ),
    )

    result = executor.run_container(
        "bayan/manim-smoke:0.20.1",
        ("manim", "--version"),
        log_path,
        1,
        phase="render video",
    )

    assert result.timed_out
    assert any(command[1:4] == ("rm", "--force", command[3]) for command in captured_commands)


def test_streaming_output_is_bounded(tmp_path: Path) -> None:
    executor = make_executor(tmp_path, max_log_bytes=128)
    log_path = tmp_path / "render.log"
    log_path.touch()

    result = executor.process.stream(
        (sys.executable, "-c", "print('x' * 10000)"),
        "large output",
        log_path,
        10,
    )

    assert result.output_limited
    assert not result.succeeded
    assert len(result.output_tail) <= 4096


def test_windows_stream_branch_terminates_a_silent_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The win32 read path must honor its deadline even with no output."""
    executor = make_executor(tmp_path)
    log_path = tmp_path / "render.log"
    log_path.touch()
    monkeypatch.setattr(sys, "platform", "win32")
    started = time.monotonic()

    result = executor.process.stream(
        (sys.executable, "-c", "import time; time.sleep(30)"),
        "silent child",
        log_path,
        1,
    )

    assert result.timed_out
    assert result.returncode is not None
    assert time.monotonic() - started < 15


def test_windows_stream_branch_collects_output_until_eof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = make_executor(tmp_path)
    log_path = tmp_path / "render.log"
    log_path.touch()
    monkeypatch.setattr(sys, "platform", "win32")

    result = executor.process.stream(
        (sys.executable, "-c", "print('win32-probe')"),
        "windows output",
        log_path,
        10,
    )

    assert result.succeeded
    assert "win32-probe" in result.output_tail


def test_windows_stream_branch_bounds_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = make_executor(tmp_path, max_log_bytes=128)
    log_path = tmp_path / "render.log"
    log_path.touch()
    monkeypatch.setattr(sys, "platform", "win32")

    result = executor.process.stream(
        (sys.executable, "-c", "print('win32-probe'); print('x' * 10000)"),
        "windows output",
        log_path,
        10,
    )

    assert result.output_limited
    assert "win32-probe" in result.output_tail
    assert len(result.output_tail) <= 4096


def test_catalogue_templates_are_rendered_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every catalogue fixture must produce video+preview evidence in the manifest."""
    run_directory = tmp_path / "smoke-run"
    run_directory.mkdir()
    media_directory = run_directory / "manim-output"
    media_directory.mkdir()
    log_path = run_directory / "render.log"
    log_path.touch()

    smoke_runner = SmokeRunner(SmokeConfig(output_root=tmp_path))
    smoke_runner.run_directory = run_directory
    smoke_runner.manifest = SmokeManifest(
        scene="ArabicSanityCheck",
        quality="low",
        docker_server="27.0",
        container_user="1000:1000",
        settings=RenderSettings(),
        image=ImageMetadata(reference="bayan/manim-smoke:0.20.1"),
    )
    executor = make_executor(tmp_path)
    rendered: list[tuple[str, ...]] = []

    def fake_run_container(
        image: str,
        command: tuple[str, ...],
        log: Path,
        timeout_seconds: int,
        **kwargs: object,
    ) -> CommandResult:
        del image, log, timeout_seconds, kwargs
        normalized = tuple(str(part) for part in command)
        rendered.append(normalized)
        if command[0] == "ffprobe":
            return CommandResult(command=("docker", *normalized), returncode=0, output_tail="6.2\n")
        media_root_arg = Path(normalized[normalized.index("--media_dir") + 1])
        host_dir = media_directory / media_root_arg.relative_to(CONTAINER_OUTPUT_ROOT)
        host_dir.mkdir(parents=True, exist_ok=True)
        class_name = normalized[normalized.index("--media_dir") - 1]
        if "--format=png" in normalized:
            (host_dir / f"{class_name}_00000.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        else:
            (host_dir / f"{class_name}.mp4").write_bytes(b"fake video bytes")
        return CommandResult(command=("docker", *normalized), returncode=0, output_tail="done\n")

    monkeypatch.setattr(executor, "run_container", fake_run_container)

    outputs = smoke_runner._render_catalogue_templates(executor, media_directory, log_path)

    catalogue = get_template_catalogue()
    # Two manim renders plus one ffprobe validation per template.
    assert len(rendered) == 3 * len(catalogue)
    for slug in catalogue:
        scene_path = str(FIXTURES_ROOT / fixture_filename(slug))
        slug_commands = [cmd for cmd in rendered if scene_path in cmd]
        assert len(slug_commands) == 2
        assert catalogue[slug]["class_name"] in slug_commands[0]
        assert f"template_{slug}_video" in outputs
        assert f"template_{slug}_preview" in outputs
        assert any(cmd[0] == "ffprobe" and f"templates/{slug}/" in cmd[-1] for cmd in rendered)
    assert len(smoke_runner.manifest.phases) == 3 * len(catalogue)
    assert all(phase.status == "passed" for phase in smoke_runner.manifest.phases)
