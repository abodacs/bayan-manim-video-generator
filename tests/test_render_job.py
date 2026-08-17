import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from bayan.planner.models import PlanRenderPreferences, ScenePlan
from bayan.renderer.docker import DockerExecutor
from bayan.renderer.errors import DockerError
from bayan.renderer.executor import RenderError, RenderJobRunner
from bayan.renderer.models import ImageMetadata, RenderJob, RenderSettings
from bayan.renderer.process import CommandResult
from bayan.renderer.smoke import CONTAINER_OUTPUT_ROOT, FIXTURES_ROOT
from bayan.templates.catalogue import fixture_filename, get_template_catalogue


def test_render_job_dataclass_lifecycle() -> None:
    job = RenderJob(
        job_id="job-123",
        status="succeeded",
        scene_plan_id="plan-123",
        scene_id="create-circle",
    )
    assert job.artifacts == {}

    data = job.to_dict()
    assert data["job_id"] == "job-123"
    assert data["status"] == "succeeded"
    assert data["artifacts"] == {}


def _plan_for(template: str) -> ScenePlan:
    return ScenePlan(
        learning_objective="اختبار القالب",
        language="ar",
        visual_concept="دائرة متحرّكة",
        selected_template=template,
        render_settings=PlanRenderPreferences(),
        provider_fingerprint="fake-provider-hash",
    )


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
        normalized = tuple(str(part) for part in command)
        if rendered is not None:
            rendered.append(normalized)
        media_root = Path(normalized[normalized.index("--media_dir") + 1])
        host_dir = cast(Path, kwargs["output_directory"]) / media_root.relative_to(
            CONTAINER_OUTPUT_ROOT
        )
        host_dir.mkdir(parents=True, exist_ok=True)
        class_name = normalized[normalized.index("--media_dir") - 1]
        if "--format=png" in normalized:
            (host_dir / f"{class_name}_00000.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        else:
            (host_dir / f"{class_name}.mp4").write_bytes(b"fake video bytes")
        return CommandResult(command=("docker", *normalized), returncode=0, output_tail="done\n")

    monkeypatch.setattr(executor, "run_container", fake_run_container)
    return executor


@pytest.mark.parametrize("slug", sorted(get_template_catalogue().keys()))
def test_every_catalogue_template_renders_in_the_worker(
    slug: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = _fake_successful_render(tmp_path, monkeypatch)
    runner = RenderJobRunner(executor=executor)

    job = runner.run_job(_plan_for(slug), output_dir=tmp_path)

    assert job.status == "succeeded"
    assert job.scene_id == slug
    assert job.artifacts["video"] == "draft.mp4"
    assert job.artifacts["preview"] == "preview.png"
    assert (tmp_path / "draft.mp4").read_bytes() == b"fake video bytes"
    assert (tmp_path / "preview.png").exists()

    record = json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))
    assert record["status"] == "succeeded"
    assert record["scene_id"] == slug


def test_render_job_uses_the_catalogue_fixture_scene(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered)

    RenderJobRunner(executor=executor).run_job(_plan_for("create-circle"), output_dir=tmp_path)

    class_name = str(get_template_catalogue()["create-circle"]["class_name"])
    assert len(rendered) == 2  # video + preview
    for command in rendered:
        assert str(FIXTURES_ROOT / fixture_filename("create-circle")) in command
        assert class_name in command


def test_render_job_records_failure_and_raises_render_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = _make_worker(tmp_path)
    monkeypatch.setattr(executor, "inspect_image", lambda image: ImageMetadata(reference=image))

    def failing_run_container(*args: object, **kwargs: object) -> CommandResult:
        del args, kwargs
        return CommandResult(command=("docker",), returncode=1, error="SyntaxError: invalid syntax")

    monkeypatch.setattr(executor, "run_container", failing_run_container)

    with pytest.raises(RenderError, match="Rendering the video"):
        RenderJobRunner(executor=executor).run_job(_plan_for("create-circle"), output_dir=tmp_path)

    record = json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))
    assert record["status"] == "failed"
    assert record["failure_stage"] == "render video"
    assert "SyntaxError" in record["exit_reason"]


def test_render_job_reports_missing_worker_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = _make_worker(tmp_path)

    def missing_image(image: str) -> ImageMetadata:
        raise DockerError(f"The image {image!r} is not available.")

    monkeypatch.setattr(executor, "inspect_image", missing_image)

    with pytest.raises(RenderError, match="not available"):
        RenderJobRunner(executor=executor).run_job(_plan_for("create-circle"), output_dir=tmp_path)

    record = json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))
    assert record["status"] == "failed"
    assert record["failure_stage"] == "setup"


@pytest.mark.parametrize(
    "template",
    [
        "arabic_template",
        "ArabicSanityCheck",
        "إنشاء دائرة",
        "unknown_template_xyz",
        "../../etc/passwd",
    ],
)
def test_non_catalogue_template_fails_preflight(template: str, tmp_path: Path) -> None:
    runner = RenderJobRunner()

    with pytest.raises(ValueError, match="Unknown or unapproved template"):
        runner.run_job(_plan_for(template), output_dir=tmp_path)

    record = json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))
    assert record["status"] == "failed"
    assert record["failure_stage"] == "preflight"
    assert "Unknown or unapproved template" in record["exit_reason"]


def test_render_job_mounts_only_a_fresh_render_run_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker's writable surface is the per-attempt run directory, not the run dir."""
    executor = _make_worker(tmp_path)
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
        normalized = tuple(str(part) for part in command)
        media_root = Path(normalized[normalized.index("--media_dir") + 1])
        host_dir = cast(Path, kwargs["output_directory"]) / media_root.relative_to(
            CONTAINER_OUTPUT_ROOT
        )
        host_dir.mkdir(parents=True, exist_ok=True)
        class_name = normalized[normalized.index("--media_dir") - 1]
        if "--format=png" in normalized:
            (host_dir / f"{class_name}_00000.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        else:
            (host_dir / f"{class_name}.mp4").write_bytes(b"fake video bytes")
        return CommandResult(command=("docker", *normalized), returncode=0, output_tail="done\n")

    monkeypatch.setattr(executor, "run_container", spy_run_container)

    job = RenderJobRunner(executor=executor).run_job(
        _plan_for("create-circle"), output_dir=tmp_path
    )

    assert job.status == "succeeded"
    assert timeouts == [RenderSettings().render_timeout_seconds] * 2
    # The job record and final artifacts stay outside the worker's writable mount.
    assert json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))["status"] == (
        "succeeded"
    )
    assert (tmp_path / "draft.mp4").read_bytes() == b"fake video bytes"

    assert len(argvs) == 2  # video + preview passes share one fresh run directory
    mounted: set[Path] = set()
    for argv in argvs:
        assert argv[0:2] == ("docker", "create")
        specs = [token for index, token in enumerate(argv) if argv[index - 1] == "--mount"]
        writable = [spec for spec in specs if not spec.endswith(",readonly")]
        assert len(writable) == 1
        source = Path(writable[0].split("source=", 1)[1].split(",", 1)[0])
        assert source.parent == (tmp_path / "render-runs").resolve()
        assert source.name == "run" or source.name.startswith("run-")
        assert source != tmp_path.resolve()
        assert any(spec.endswith("destination=/workspace/bayan,readonly") for spec in specs)
        mounted.add(source)
    assert len(mounted) == 1
