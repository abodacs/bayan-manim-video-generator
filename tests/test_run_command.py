import json
from pathlib import Path

from typer.testing import CliRunner

from bayan.cli import app

runner = CliRunner()


def test_bayan_run_complete_workflow_offline(tmp_path: Path) -> None:
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

    # Workflow stops gracefully at 'render' stage as it is currently a stub
    assert result.exit_code == 1

    # 3. Verify valid stage artifacts exist while stub stages produced no fake outputs
    assert (output_dir / "scene_plan.json").exists()
    assert (output_dir / "scene.py").exists()
    assert (output_dir / "manifest.json").exists()

    # 4. Check manifest status reflects 'stub' state accurately
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "stub"
    assert manifest["stages"]["plan"]["status"] == "completed"
    assert manifest["stages"]["template_select"]["status"] == "completed"
    assert manifest["stages"]["render"]["status"] == "stub"

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
