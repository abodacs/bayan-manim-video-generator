import json
from pathlib import Path

from typer.testing import CliRunner

from bayan.cli import app
from bayan.planner.service import run_planning_pipeline


def test_bayan_plan_with_fake_provider(tmp_path: Path):
    # 1. Prepare input lesson.json file
    input_file = tmp_path / "lesson.json"
    input_file.write_text(
        json.dumps(
            {
                "request": "شرح مفهوم الجمع للأطفال",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "run"

    # 2. Run CLI command: bayan plan --input lesson.json --output run/
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["plan", "--input", str(input_file), "--output", str(output_dir)],
    )

    # 3. Assertions
    assert result.exit_code == 0

    scene_plan_file = output_dir / "scene_plan.json"
    assert scene_plan_file.exists()

    with open(scene_plan_file, encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("language") == "ar"


def test_bayan_plan_fails_if_output_dir_exists_without_force(tmp_path: Path):
    input_file = tmp_path / "lesson.json"
    input_file.write_text(
        json.dumps({"request": "اختبار"}, ensure_ascii=False),
        encoding="utf-8",
    )

    output_dir = tmp_path / "run"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "existing_file.txt").write_text("data")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["plan", "--input", str(input_file), "--output", str(output_dir)],
    )

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_bayan_plan_overwrites_with_force(tmp_path: Path):
    input_file = tmp_path / "lesson.json"
    input_file.write_text(
        json.dumps({"request": "اختبار مع force"}, ensure_ascii=False),
        encoding="utf-8",
    )

    output_dir = tmp_path / "run"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "old_plan.json").write_text("old data")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "plan",
            "--input",
            str(input_file),
            "--output",
            str(output_dir),
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "scene_plan.json").exists()


def test_run_planning_pipeline_default_provider(tmp_path: Path):
    input_file = tmp_path / "lesson.json"
    input_file.write_text(
        json.dumps({"request": "افتراضي"}, ensure_ascii=False),
        encoding="utf-8",
    )
    output_dir = tmp_path / "run_default"

    run_planning_pipeline(input_path=input_file, output_dir=output_dir)

    assert (output_dir / "scene_plan.json").exists()
