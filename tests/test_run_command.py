import json
from pathlib import Path

from typer.testing import CliRunner

from bayan.cli import app
from bayan.renderer.models import RenderJob
from bayan.templates.catalogue import fixture_filename, get_template_catalogue

runner = CliRunner()

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "bayan" / "templates" / "fixtures"


class FakeRenderJobRunner:
    """Offline stand-in that records the render stage as succeeded."""

    def run_job(self, plan: object, output_dir: Path) -> RenderJob:
        selected = plan.selected_template
        (output_dir / "draft.mp4").write_bytes(b"fake video bytes")
        (output_dir / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return RenderJob(
            job_id="job-test",
            status="succeeded",
            scene_plan_id="plan-test",
            scene_id=selected,
        )


def test_bayan_run_complete_workflow_offline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("bayan.orchestrator.RenderJobRunner", FakeRenderJobRunner)

    # 1. Setup lesson input file
    lesson_file = tmp_path / "lesson.json"
    lesson_data = {
        "topic": "Shapes and Rotations",
        "prompt": "Create a scene showing a circle and square transforming",
    }
    lesson_file.write_text(json.dumps(lesson_data), encoding="utf-8")

    output_dir = tmp_path / "run"

    # 2. Invoke bayan run command in offline mode with fake provider
    result = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(lesson_file),
            "--output",
            str(output_dir),
            "--provider",
            "fake",
        ],
    )

    # Workflow stops gracefully at 'validate' stage as it is currently a stub
    assert result.exit_code == 1

    # 3. Verify valid stage artifacts exist while stub stages produced no fake outputs
    assert (output_dir / "scene_plan.json").exists()
    assert (output_dir / "scene.py").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "draft.mp4").exists()

    # 4. Check manifest status reflects the 'validate' stub accurately
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "stub"
    assert manifest["stages"]["plan"]["status"] == "completed"
    assert manifest["stages"]["template_select"]["status"] == "completed"
    assert manifest["stages"]["render"]["status"] == "completed"
    assert manifest["stages"]["validate"]["status"] == "stub"

    # 5. Run command a second time to verify resume logic (completed stages skipped)
    second_run = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(lesson_file),
            "--output",
            str(output_dir),
            "--provider",
            "fake",
        ],
    )
    assert second_run.exit_code == 1
    assert "Skipping completed stage: plan" in second_run.output
    assert "Skipping completed stage: render" in second_run.output


def test_bayan_run_selects_the_template_from_the_scene_plan(tmp_path: Path, monkeypatch) -> None:
    """The plan's selected_template must drive template selection end to end."""
    monkeypatch.setattr("bayan.orchestrator.RenderJobRunner", FakeRenderJobRunner)

    lesson_file = tmp_path / "lesson.json"
    lesson_file.write_text(json.dumps({"request": "shapes"}), encoding="utf-8")
    output_dir = tmp_path / "run"

    result = runner.invoke(
        app,
        ["run", "--input", str(lesson_file), "--output", str(output_dir), "--provider", "fake"],
    )

    assert result.exit_code == 1  # still stops at the validate stub

    scene_plan = json.loads((output_dir / "scene_plan.json").read_text(encoding="utf-8"))
    selected = scene_plan["selected_template"]
    assert selected in get_template_catalogue()

    fixture = (FIXTURES_DIR / fixture_filename(selected)).read_text(encoding="utf-8")
    assert (output_dir / "scene.py").read_text(encoding="utf-8") == fixture


def test_bayan_run_reports_missing_scene_plan(tmp_path: Path, monkeypatch) -> None:
    """A resume without the plan artifact must fail with a named stage error."""
    monkeypatch.setattr("bayan.orchestrator.RenderJobRunner", FakeRenderJobRunner)

    lesson_file = tmp_path / "lesson.json"
    lesson_file.write_text(json.dumps({"request": "shapes"}), encoding="utf-8")
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text(
        json.dumps({"run_id": "run", "stages": {"plan": {"status": "completed"}}}),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["run", "--input", str(lesson_file), "--output", str(output_dir), "--provider", "fake"],
    )

    assert result.exit_code == 1
    assert "Scene plan not found" in result.output
    assert "template_select" in result.output


def test_bayan_run_reports_corrupt_manifest_without_traceback(tmp_path: Path) -> None:
    lesson_file = tmp_path / "lesson.json"
    lesson_file.write_text('{"request": "shapes"}', encoding="utf-8")
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text("{ not valid json", encoding="utf-8")

    result = runner.invoke(
        app,
        ["run", "--input", str(lesson_file), "--output", str(output_dir)],
    )

    assert result.exit_code == 1
    assert "Manifest Error" in result.output
    assert "unreadable manifest" in result.output
    assert "Traceback" not in result.output


def test_bayan_run_reports_foreign_manifest_shape_without_traceback(tmp_path: Path) -> None:
    lesson_file = tmp_path / "lesson.json"
    lesson_file.write_text('{"request": "shapes"}', encoding="utf-8")
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    (output_dir / "manifest.json").write_text(
        json.dumps({"stages": {"plan": {"bogus_field": 1}}}), encoding="utf-8"
    )

    result = runner.invoke(
        app,
        ["run", "--input", str(lesson_file), "--output", str(output_dir)],
    )

    assert result.exit_code == 1
    assert "Manifest Error" in result.output
    assert "Traceback" not in result.output
