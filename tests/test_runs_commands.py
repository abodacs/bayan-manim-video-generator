"""`bayan runs list|show` tests: read-only inspection of past run directories."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bayan.cli import app
from bayan.pipeline.runs import failure_category
from bayan.pipeline.spine import (
    CODE_RECORD_FILENAME,
    CRITIC_RECORD_FILENAME,
    GATES_RECORD_FILENAME,
    PLAN_RECORD_FILENAME,
    PROFILE_RECORD_FILENAME,
    RENDER_RECORD_FILENAME,
)

runner = CliRunner()

# The spine's record layout: summary stage name -> (record filename, the
# `stage` value the record carries). Filenames come from the spine's own
# constants so drift fails loudly; plan and code records carry the stage
# services' process names (planning/coding), while the spine itself writes
# the remaining stages under the stage's own name.
RECORD_LAYOUT = {
    "plan": (PLAN_RECORD_FILENAME, "planning"),
    "profile": (PROFILE_RECORD_FILENAME, "profile"),
    "code": (CODE_RECORD_FILENAME, "coding"),
    "gates": (GATES_RECORD_FILENAME, "gates"),
    "render": (RENDER_RECORD_FILENAME, "render"),
    "critic": (CRITIC_RECORD_FILENAME, "critic"),
}


def _record_filename(stage: str) -> str:
    """The spine's record filename behind a summary stage name."""
    return RECORD_LAYOUT[stage][0]


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
    for stage, stage_status in stages.items():
        _write_record(
            run_dir,
            _record_filename(stage),
            {
                "stage": RECORD_LAYOUT[stage][1],
                "status": stage_status,
                **record_defaults,
                "attempts": [
                    {
                        "attempt": 1,
                        "status": "ok",
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
        _record_filename("gates"),
        {
            "stage": "gates",
            "status": "failed",
            "created_at": "2026-09-06T12:01:05+00:00",
            "rerun_of": None,
            "failure": "the gates rejected the code",
        },
    )
    # A corrupted (non-UTF-8) record is skipped like unreadable JSON
    # instead of crashing the listing.
    (failed / "records" / PROFILE_RECORD_FILENAME).write_bytes(b"\xff\xfe not utf-8")
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


def test_runs_show_of_failed_run_names_failure_category(two_runs):
    runs_root, _, failed = two_runs
    _write_record(
        failed,
        _record_filename("gates"),
        {
            "stage": "gates",
            "status": "failed",
            "created_at": "2026-09-06T12:01:05+00:00",
            "rerun_of": None,
            "failure": "arabic (line 3): Arabic text must use ArabicText.",
            "gates": [
                {
                    "gate": "syntax",
                    "status": "passed",
                    "line": None,
                    "excerpt": "",
                    "suggestion": "",
                },
                {
                    "gate": "arabic",
                    "status": "failed",
                    "line": 3,
                    "excerpt": 'Text("مرحبا بكم")',
                    "suggestion": "Arabic text must use ArabicText.",
                },
            ],
        },
    )

    result = runner.invoke(app, ["runs", "show", failed.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 0
    assert "Failure category (gates): arabic_layout" in result.output


def test_failure_category_follows_the_named_stage(tmp_path: Path):
    crashed = _fabricate_run(
        tmp_path,
        "20260906T1203Z-44444444",
        status="failed",
        stages={"plan": "completed", "render": "failed"},
    )
    _write_record(
        crashed,
        _record_filename("render"),
        {
            "stage": "render",
            "status": "failed",
            "created_at": "2026-09-06T12:03:05+00:00",
            "rerun_of": None,
            "failure": "the scene crashed inside the worker",
        },
    )
    unconfigured = _fabricate_run(
        tmp_path,
        "20260906T1204Z-55555555",
        status="failed",
        stages={"plan": "failed"},
    )
    _write_record(
        unconfigured,
        _record_filename("plan"),
        {
            "stage": "planning",
            "status": "failed",
            "created_at": "2026-09-06T12:04:05+00:00",
            "rerun_of": None,
            "failure": "the provider call failed",
            "attempts": [
                {
                    "attempt": 1,
                    "status": "invalid_output",
                    "error": "the provider returned invalid output",
                }
            ],
        },
    )
    # The code stage failed once, was repaired, and the re-gated run
    # exhausted repair at gates: the stale failed code record stays on
    # disk while the summary names gates as the failing stage.
    stale = _fabricate_run(
        tmp_path,
        "20260906T1205Z-66666666",
        status="failed",
        stages={"plan": "completed", "code": "repaired", "gates": "failed"},
        repairs_used=2,
    )
    _write_record(
        stale,
        _record_filename("code"),
        {
            "stage": "coding",
            "status": "failed",
            "created_at": "2026-09-06T12:05:05+00:00",
            "rerun_of": None,
            "failure": "the coder produced invalid output",
        },
    )
    _write_record(
        stale,
        _record_filename("gates"),
        {
            "stage": "gates",
            "status": "failed",
            "created_at": "2026-09-06T12:05:10+00:00",
            "rerun_of": None,
            "failure": "arabic (line 3): Arabic text must use ArabicText.",
            "gates": [
                {
                    "gate": "arabic",
                    "status": "failed",
                    "line": 3,
                    "excerpt": 'Text("مرحبا بكم")',
                    "suggestion": "Arabic text must use ArabicText.",
                }
            ],
        },
    )
    clean = _fabricate_run(
        tmp_path,
        "20260906T1206Z-77777777",
        status="completed",
        stages={"plan": "completed"},
    )
    _write_record(
        clean,
        _record_filename("code"),
        {
            "stage": "coding",
            "status": "failed",
            "created_at": "2026-09-06T12:06:05+00:00",
            "rerun_of": None,
            "failure": "repaired away",
        },
    )

    assert failure_category(crashed, "render") == "render_crash"
    assert failure_category(unconfigured, "plan") == "provider_error"
    # The stale failed code record does not override the named stage.
    assert failure_category(stale, "gates") == "arabic_layout"
    # A completed run reports no category even with stale failed records.
    assert failure_category(clean, "gates") is None
    # Unknown stage names and missing run directories report no category.
    assert failure_category(crashed, "nope") is None
    assert failure_category(tmp_path / "missing", "gates") is None


def test_failure_category_classifies_critic_evidence(tmp_path: Path):
    """The critic branch maps a failed run's serialized checks onto the taxonomy."""
    judged = _fabricate_run(
        tmp_path,
        "20260906T1207Z-88888888",
        status="failed",
        stages={
            "plan": "completed",
            "code": "completed",
            "gates": "completed",
            "render": "completed",
            "critic": "failed",
        },
    )
    _write_record(
        judged,
        _record_filename("critic"),
        {
            "stage": "critic",
            "status": "failed",
            "created_at": "2026-09-06T12:07:05+00:00",
            "rerun_of": None,
            "failure": "the critic rejected the rendered artifacts",
            "checks": [
                {
                    "check": "duration",
                    "status": "failed",
                    "evidence": "45s exceeds the 42s bound",
                    "suggestion": "Trim the closing animation.",
                }
            ],
        },
    )

    assert failure_category(judged, "critic") == "duration_out_of_bounds"

    result = runner.invoke(app, ["runs", "show", judged.name, "--runs-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Failure category (critic): duration_out_of_bounds" in result.output

    # The critic's one cross-domain mapping: an uncovered beat is an
    # Arabic-layout defect, not an unknown failure.
    _write_record(
        judged,
        _record_filename("critic"),
        {
            "stage": "critic",
            "status": "failed",
            "created_at": "2026-09-06T12:07:05+00:00",
            "rerun_of": None,
            "failure": "the critic rejected the rendered artifacts",
            "checks": [
                {
                    "check": "beat_coverage",
                    "status": "failed",
                    "evidence": "beat 3 has no scene",
                    "suggestion": "Cover every beat of the plan.",
                }
            ],
        },
    )

    assert failure_category(judged, "critic") == "arabic_layout"


def test_failure_category_reports_unknown_without_a_provider_attempt(tmp_path: Path):
    """Failures recorded before any provider call are not provider errors."""
    misconfigured = _fabricate_run(
        tmp_path,
        "20260906T1208Z-99999999",
        status="failed",
        stages={"plan": "completed", "profile": "failed"},
    )
    _write_record(
        misconfigured,
        _record_filename("profile"),
        {
            "stage": "profile",
            "status": "failed",
            "created_at": "2026-09-06T12:08:05+00:00",
            "rerun_of": None,
            "failure": "unknown profile: farsi-western",
        },
    )
    empty_prompt = _fabricate_run(
        tmp_path,
        "20260906T1209Z-aaaaaaaa",
        status="failed",
        stages={"plan": "failed"},
    )
    _write_record(
        empty_prompt,
        _record_filename("plan"),
        {
            "stage": "planning",
            "status": "failed",
            "created_at": "2026-09-06T12:09:05+00:00",
            "rerun_of": None,
            "failure": "Prompt is empty: describe the lesson in one Arabic sentence.",
        },
    )

    # The provider category suggests retrying the call, which would
    # mislead for a configuration or validation failure.
    assert failure_category(misconfigured, "profile") == "unknown"
    assert failure_category(empty_prompt, "plan") == "unknown"


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
