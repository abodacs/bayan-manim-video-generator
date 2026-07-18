import json
import sys
from pathlib import Path

import pytest

from bayan.renderer.docker import DockerExecutor, check_docker
from bayan.renderer.errors import DockerError
from bayan.renderer.models import ImageMetadata, PhaseRecord, RenderSettings, SmokeManifest
from bayan.renderer.process import CaptureResult, CommandResult
from bayan.renderer.security import security_args
from bayan.renderer.smoke import (
    SmokeConfig,
    SmokeError,
    SmokeRunner,
    allocate_run_directory,
    current_container_user,
    first_artifact,
    validate_png,
)


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
        executor,
        "_run_streaming",
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

    result = executor._run_streaming(
        (sys.executable, "-c", "print('x' * 10000)"),
        "large output",
        log_path,
        10,
    )

    assert result.output_limited
    assert not result.succeeded
    assert len(result.output_tail) <= 4096
