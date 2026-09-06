import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from bayan.planner.models import PlanRenderPreferences, RenderQuality, ScenePlan
from bayan.renderer.docker import DockerExecutor
from bayan.renderer.errors import DockerError
from bayan.renderer.executor import RenderError, RenderJobRunner, render_scene_code
from bayan.renderer.models import ImageMetadata, RenderJob, RenderSettings
from bayan.renderer.process import CommandResult
from bayan.renderer.smoke import (
    CONTAINER_OUTPUT_ROOT,
    DEFAULT_IMAGE,
    FIXTURES_ROOT,
    MAX_RETAINED_RUN_DIRECTORIES,
    PROJECT_ROOT,
    sha256_file,
)
from bayan.templates.catalogue import fixture_filename, get_template_catalogue


def test_render_job_dataclass_lifecycle() -> None:
    job = RenderJob(
        job_id="job-123",
        status="succeeded",
        scene_plan_id="plan-123",
        template_id="create-circle",
    )
    assert job.artifacts == {}

    data = job.to_dict()
    assert data["job_id"] == "job-123"
    assert data["status"] == "succeeded"
    assert data["artifacts"] == {}
    # Evidence fields are absent until setup captures them.
    assert data["image"] is None
    assert data["settings"] is None
    assert data["fixture_hash"] is None


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
    assert job.template_id == slug
    assert job.artifacts["video"] == "draft.mp4"
    assert job.artifacts["preview"] == "preview.png"
    assert (tmp_path / "draft.mp4").read_bytes() == b"fake video bytes"
    assert (tmp_path / "preview.png").exists()

    record = json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))
    assert record["status"] == "succeeded"
    assert record["template_id"] == slug
    # Reproducibility evidence: the image used, the settings in force, and a
    # hash of the exact fixture source that was rendered.
    assert record["image"]["reference"] == DEFAULT_IMAGE
    assert record["settings"]["network"] == "none"
    assert record["fixture_hash"] == sha256_file(
        PROJECT_ROOT / "bayan" / "templates" / "fixtures" / fixture_filename(slug)
    )


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

    with pytest.raises(RenderError, match="Unknown or unapproved template"):
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


@pytest.mark.parametrize(
    ("quality", "flag"),
    [
        ("low_quality", "-ql"),
        ("medium_quality", "-qm"),
        ("high_quality", "-qh"),
        ("highest_quality", "-qk"),
    ],
)
def test_render_job_maps_the_plan_quality_onto_manim(
    quality: RenderQuality,
    flag: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The video pass honors ScenePlan.render_settings.quality."""
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered)
    plan = ScenePlan(
        learning_objective="objective",
        language="ar",
        visual_concept="concept",
        selected_template="create-circle",
        render_settings=PlanRenderPreferences(quality=quality),
        provider_fingerprint="fake-provider-hash",
    )

    RenderJobRunner(executor=executor).run_job(plan, output_dir=tmp_path)

    assert len(rendered) == 2
    video_command, preview_command = rendered
    assert flag in video_command
    # The preview stays a fast low-quality single frame.
    assert "-ql" in preview_command


def test_failed_render_still_prunes_old_run_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated failing renders must not accumulate run directories."""
    executor = _make_worker(tmp_path)
    monkeypatch.setattr(executor, "inspect_image", lambda image: ImageMetadata(reference=image))

    def failing_run_container(*args: object, **kwargs: object) -> CommandResult:
        del args, kwargs
        return CommandResult(command=("docker",), returncode=1, error="SyntaxError: boom")

    monkeypatch.setattr(executor, "run_container", failing_run_container)

    run_root = tmp_path / "render-runs"
    run_root.mkdir()
    for index in range(MAX_RETAINED_RUN_DIRECTORIES + 3):
        (run_root / f"run-{index:03d}").mkdir()

    with pytest.raises(RenderError):
        RenderJobRunner(executor=executor).run_job(_plan_for("create-circle"), output_dir=tmp_path)

    remaining = [path for path in run_root.iterdir() if path.is_dir()]
    # Pruning before allocation bounds failures at the retained window plus
    # the one fresh directory the failed render used.
    assert len(remaining) == MAX_RETAINED_RUN_DIRECTORIES + 1


# -------------------------------------------------------------------------
# Render quality plumbing (draft by default; flag chosen in one mapping)
# -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("quality_name", "expected_flag"),
    [
        ("low_quality", "-ql"),
        ("medium_quality", "-qm"),
        ("high_quality", "-qh"),
    ],
)
def test_quality_flag_reaches_manim_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    quality_name: RenderQuality,
    expected_flag: str,
) -> None:
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered=rendered)
    plan = _plan_for("create-circle")
    plan.render_settings = PlanRenderPreferences(quality=quality_name)

    RenderJobRunner(executor=executor).run_job(plan, output_dir=tmp_path)

    video_commands = [command for command in rendered if "--format=png" not in command]
    assert video_commands
    for command in video_commands:
        assert command[1] == expected_flag

    job_record = json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))
    assert job_record["quality"] == quality_name


def test_render_scene_code_defaults_to_draft_quality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered=rendered)

    render_scene_code("from manim import *", tmp_path / "draft.mp4", executor=executor)

    video_commands = [command for command in rendered if "--format=png" not in command]
    assert video_commands
    assert all(command[1] == "-ql" for command in video_commands)


def test_render_scene_code_accepts_named_qualities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered=rendered)

    render_scene_code(
        "from manim import *",
        tmp_path / "draft.mp4",
        executor=executor,
        quality="high_quality",
    )

    video_commands = [command for command in rendered if "--format=png" not in command]
    assert video_commands
    assert all(command[1] == "-qh" for command in video_commands)


def test_unknown_quality_fails_before_any_container_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered=rendered)

    with pytest.raises(RenderError, match="Unknown render quality"):
        render_scene_code(
            "from manim import *",
            tmp_path / "draft.mp4",
            executor=executor,
            quality="ultra",
        )

    assert rendered == []


def test_run_job_unknown_quality_fails_before_container_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[tuple[str, ...]] = []
    executor = _fake_successful_render(tmp_path, monkeypatch, rendered=rendered)
    # model_construct bypasses the literal validation on purpose: the runner
    # must still fail safely when an unvalidated quality reaches it.
    plan = _plan_for("create-circle").model_copy(
        update={"render_settings": PlanRenderPreferences.model_construct(quality="bogus")}
    )

    with pytest.raises(RenderError, match="Unknown render quality"):
        RenderJobRunner(executor=executor).run_job(plan, output_dir=tmp_path)

    assert rendered == []
    job_record = json.loads((tmp_path / "render_job.json").read_text(encoding="utf-8"))
    assert job_record["status"] == "failed"
    assert job_record["quality"] == "bogus"
