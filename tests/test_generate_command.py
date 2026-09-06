"""End-to-end tests for `bayan generate` through the pipeline spine."""

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bayan.cli import app
from bayan.generator.llm_client import LLMConfigError, LLMResponseFormatError
from bayan.planner.provider import FakeProvider
from tests.conftest import MP4_BYTES, PNG_BYTES

ARABIC_PROMPT = "شرح العامل المشترك الأكبر للأعداد ١٢ و ١٨"
RUN_ID_PATTERN = re.compile(r"^\d{8}T\d{4}Z-[0-9a-f]{8}$")

runner = CliRunner()


def _fake_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("bayan.cli._build_providers", lambda: (FakeProvider(), FakeProvider()))


def _run_generate(monkeypatch: pytest.MonkeyPatch, runs_root: Path, *args: str):
    _fake_providers(monkeypatch)
    return runner.invoke(
        app,
        ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root), *args],
    )


def _only_run_dir(runs_root: Path) -> Path:
    run_dirs = [path for path in runs_root.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    return run_dirs[0]


def test_generate_happy_path_creates_run_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root)
    assert result.exit_code == 0, result.output
    assert "Success!" in result.output

    run_dir = _only_run_dir(runs_root)
    assert RUN_ID_PATTERN.match(run_dir.name)
    for artifact in ("plan.json", "scene.py", "draft.mp4", "preview.png", "records", "run.json"):
        assert (run_dir / artifact).exists(), artifact

    assert (run_dir / "draft.mp4").read_bytes() == MP4_BYTES
    assert (run_dir / "preview.png").read_bytes() == PNG_BYTES

    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed"
    assert summary["prompt"] == ARABIC_PROMPT
    assert summary["profile"] == "msa-western"
    assert summary["model"] == "fake-model-v1"
    assert summary["stages"] == {
        "plan": "completed",
        "profile": "completed",
        "code": "completed",
        "render": "completed",
    }
    assert summary["failure"] is None


def test_every_stage_writes_one_ordered_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root)
    assert result.exit_code == 0, result.output

    records_dir = _only_run_dir(runs_root) / "records"
    assert sorted(path.name for path in records_dir.glob("*.json")) == [
        "01-plan.json",
        "02-profile.json",
        "03-code.json",
        "04-render.json",
    ]
    for record_path in sorted(records_dir.glob("*.json")):
        record = json.loads(record_path.read_text(encoding="utf-8"))
        assert record["status"] == "completed"
        assert record["created_at"]


def test_failing_plan_stage_stops_later_stages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class _FailingPlanner:
        def generate_lesson_plan(self, prompt: str, profile: str) -> object:
            raise LLMResponseFormatError("provider returned no usable plan")

    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (_FailingPlanner(), FakeProvider()),
    )
    runs_root = tmp_path / "runs"
    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    assert "Generation failed" in result.output
    assert "provider returned no usable plan" in result.output

    run_dir = _only_run_dir(runs_root)
    records = sorted(path.name for path in (run_dir / "records").glob("*.json"))
    assert records == ["01-plan.json"]
    assert not (run_dir / "plan.json").exists()
    assert not (run_dir / "scene.py").exists()
    assert not (run_dir / "draft.mp4").exists()

    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["stages"] == {"plan": "failed"}


def test_missing_api_key_fails_fast_before_any_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("BAYAN_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def _no_credentials() -> tuple[object, object]:
        raise LLMConfigError("Missing LLM API key: set BAYAN_API_KEY.")

    monkeypatch.setattr("bayan.cli._build_providers", _no_credentials)
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    assert "Configuration Error" in result.output
    assert not runs_root.exists() or list(runs_root.iterdir()) == []


def test_run_id_is_deterministic_format(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root)
    assert result.exit_code == 0, result.output
    assert RUN_ID_PATTERN.match(_only_run_dir(runs_root).name)


def test_unknown_profile_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _fake_providers(monkeypatch)
    runs_root = tmp_path / "runs"
    result = runner.invoke(
        app,
        ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root), "--profile", "bogus"],
    )

    assert result.exit_code != 0
    assert not runs_root.exists() or list(runs_root.iterdir()) == []


def test_generate_help_shows_usage():
    result = runner.invoke(app, ["generate", "--help"])

    assert result.exit_code == 0
    assert "Free-form Arabic lesson prompt" in result.output
    assert "--profile" in result.output
    assert "--runs-root" in result.output


def test_console_script_is_declared():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert "[project.scripts]" in text
    assert 'bayan = "bayan.cli:app"' in text
