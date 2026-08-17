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

    # Expected to fail initially because 'run' command is not implemented yet
    assert result.exit_code == 0

    # 3. Verify all required outputs and stage artifacts exist in run directory
    assert (output_dir / "lesson.json").exists()
    assert (output_dir / "scene_plan.json").exists()
    assert (output_dir / "scene.py").exists()
    assert (output_dir / "render.log").exists()
    assert (output_dir / "artifacts" / "draft.mp4").exists()
    assert (output_dir / "artifacts" / "preview.png").exists()
    assert (output_dir / "validation.json").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "review_packet.md").exists()

    # 4. Check manifest status and recorded stage states
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["stages"]["plan"]["status"] == "completed"
    assert manifest["stages"]["render"]["status"] == "completed"

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
    assert second_run.exit_code == 0
    assert "Skipping completed stage: plan" in second_run.output
