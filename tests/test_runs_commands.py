"""`bayan runs list|show` tests: read-only inspection of past run directories."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bayan.cli import app

runner = CliRunner()


def _write_record(run_dir: Path, name: str, record: dict) -> None:
    records_dir = run_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    (records_dir / name).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _fabricate_run(
    runs_root: Path,
    run_id: str,
    *,
    status: str,
    stages: dict[str, str],
    repairs_used: int = 0,
    cost: float = 0.5,
) -> Path:
    run_dir = runs_root / run_id
    records_dir = run_dir / "records"
    records_dir.mkdir(parents=True)
    created = "2026-09-06T12:00:00+00:00"
    record_defaults = {"created_at": created, "rerun_of": None}
    for index, (stage, stage_status) in enumerate(stages.items(), start=1):
        _write_record(
            run_dir,
            f"{index:02d}-{stage}.json",
            {
                "stage": stage,
                "status": stage_status,
                **record_defaults,
                "attempts": [
                    {
                        "attempt": 1,
                        "model": "fake-model-v1",
                        "cost_estimate_usd": cost,
                    }
                ]
                if stage in {"plan", "code"}
                else [],
            },
        )
    for artifact in ("plan.json", "scene.py", "draft.mp4", "preview.png"):
        (run_dir / artifact).write_bytes(b"x" if artifact.endswith("4") else b"{}")
    summary = {
        "run_id": run_id,
        "status": status,
        "created_at": created,
        "prompt": "شرح القسمة",
        "profile": "msa-western",
        "quality": "draft",
        "model": "fake-model-v1",
        "total_cost_estimate_usd": cost,
        "stages": stages,
        "repairs_used": repairs_used,
        "rerun_of": None,
        "failure": "the gates rejected the code" if status == "failed" else None,
    }
    (run_dir / "run.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return run_dir


@pytest.fixture()
def two_runs(tmp_path: Path) -> tuple[Path, Path, Path]:
    runs_root = tmp_path / "runs"
    ok = _fabricate_run(
        runs_root,
        "20260906T1200Z-11111111",
        status="completed",
        stages={"plan": "completed", "profile": "completed", "render": "completed"},
    )
    failed = _fabricate_run(
        runs_root,
        "20260906T1201Z-22222222",
        status="failed",
        stages={"plan": "completed", "gates": "failed"},
        repairs_used=2,
        cost=0.75,
    )
    _write_record(
        failed,
        "02-gates.json",
        {
            "stage": "gates",
            "status": "failed",
            "created_at": "2026-09-06T12:01:05+00:00",
            "rerun_of": None,
            "failure": "the gates rejected the code",
        },
    )
    return runs_root, ok, failed


def test_runs_list_prints_one_row_per_run(two_runs):
    runs_root, ok, failed = two_runs

    result = runner.invoke(app, ["runs", "list", "--runs-root", str(runs_root)])

    assert result.exit_code == 0
    assert ok.name in result.output
    assert failed.name in result.output
    assert "completed" in result.output
    assert "failed" in result.output
    assert "msa-western" in result.output
    assert "fake-model-v1" in result.output


def test_runs_list_is_sorted_by_run_id(two_runs):
    runs_root, ok, failed = two_runs

    result = runner.invoke(app, ["runs", "list", "--runs-root", str(runs_root)])

    lines = [line for line in result.output.splitlines() if line.startswith("2026")]
    assert [line.split()[0] for line in lines] == [ok.name, failed.name]


def test_runs_show_prints_stage_timeline(two_runs):
    runs_root, ok, _ = two_runs

    result = runner.invoke(app, ["runs", "show", ok.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 0
    assert "plan" in result.output
    assert "completed" in result.output
    assert "total cost" in result.output.lower()
    assert "0.5000" in result.output


def test_runs_show_of_failed_run_names_stage_and_repairs(two_runs):
    runs_root, _, failed = two_runs

    result = runner.invoke(app, ["runs", "show", failed.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 0
    assert "gates" in result.output
    assert "failed" in result.output
    assert "repairs used: 2" in result.output.lower()
    # The timeline reads the real record files, timestamps included.
    assert "2026-09-06T12:01:05" in result.output
    assert "the gates rejected the code" in result.output


def test_runs_show_prints_rerun_lineage(two_runs, tmp_path: Path):
    runs_root, ok, _ = two_runs
    rerun = _fabricate_run(
        runs_root,
        "20260906T1202Z-33333333",
        status="completed",
        stages={"profile": "completed"},
    )
    summary_path = rerun / "run.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["rerun_of"] = ok.name
    summary_path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")

    result = runner.invoke(app, ["runs", "show", rerun.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 0
    assert f"Rerun of: {ok.name}" in result.output


def test_unknown_run_id_fails_cleanly(two_runs):
    runs_root = two_runs[0]

    result = runner.invoke(
        app,
        ["runs", "show", "20990101T0000Z-deadbeef", "--runs-root", str(runs_root)],
    )

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "bayan runs list" in result.output


def test_empty_runs_root_exits_zero(two_runs, tmp_path: Path):
    result = runner.invoke(app, ["runs", "list", "--runs-root", str(tmp_path / "empty")])

    assert result.exit_code == 0
    assert "no runs yet" in result.output.lower()


def test_malformed_run_dirs_are_skipped_with_a_note(two_runs):
    runs_root, ok, failed = two_runs
    (runs_root / "not-a-run").mkdir()
    corrupt = runs_root / "corrupt-run"
    corrupt.mkdir()
    (corrupt / "run.json").write_text("{ not json", encoding="utf-8")

    result = runner.invoke(app, ["runs", "list", "--runs-root", str(runs_root)])

    assert result.exit_code == 0
    assert ok.name in result.output
    assert failed.name in result.output
    assert "not-a-run" in result.output
    assert "corrupt-run" in result.output


def test_commands_are_strictly_read_only(two_runs):
    runs_root, ok, failed = two_runs

    def snapshot() -> dict[Path, tuple]:
        return {
            path: (path.stat().st_mtime_ns, path.read_bytes())
            for path in sorted(runs_root.rglob("*"))
            if path.is_file()
        }

    before = snapshot()
    runner.invoke(app, ["runs", "list", "--runs-root", str(runs_root)])
    runner.invoke(app, ["runs", "show", ok.name, "--runs-root", str(runs_root)])
    runner.invoke(app, ["runs", "show", failed.name, "--runs-root", str(runs_root)])

    assert snapshot() == before
