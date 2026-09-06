"""`bayan rerun` tests: cached artifacts in, reproduced artifacts out, zero LLM."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bayan.cli import app
from tests.conftest import MP4_BYTES, PNG_BYTES
from tests.test_generate_command import _only_run_dir, _run_generate

ARABIC_PROMPT = "شرح العامل المشترك الأكبر للأعداد ١٢ و ١٨"

runner = CliRunner()


def _generate_a_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root)
    assert result.exit_code == 0, result.output
    return _only_run_dir(runs_root)


def test_rerun_never_constructs_a_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    from bayan.generator.llm_client import LLMClient

    source = _generate_a_run(monkeypatch, tmp_path)

    def _poisoned_init(self: object, *args: object, **kwargs: object) -> None:
        raise AssertionError("rerun must never construct an LLM client")

    monkeypatch.setattr(LLMClient, "__init__", _poisoned_init)
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["rerun", source.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 0, result.output
    assert "Success!" in result.output


def test_rerun_reproduces_artifacts_into_a_new_linked_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    source = _generate_a_run(monkeypatch, tmp_path)
    source_snapshot = {path.name: path.read_bytes() for path in source.iterdir() if path.is_file()}
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["rerun", source.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 0, result.output
    run_dirs = [path for path in runs_root.iterdir() if path.is_dir()]
    assert len(run_dirs) == 2
    rerun_dir = next(path for path in run_dirs if path != source)

    for artifact in ("plan.json", "scene.py", "draft.mp4", "preview.png", "records", "run.json"):
        assert (rerun_dir / artifact).exists(), artifact
    assert (rerun_dir / "draft.mp4").read_bytes() == MP4_BYTES
    assert (rerun_dir / "preview.png").read_bytes() == PNG_BYTES
    # Cached code is reused verbatim: chained reruns must not drift.
    assert (rerun_dir / "scene.py").read_bytes() == (source / "scene.py").read_bytes()

    summary = json.loads((rerun_dir / "run.json").read_text(encoding="utf-8"))
    assert summary["rerun_of"] == source.name
    for record_path in sorted((rerun_dir / "records").glob("*.json")):
        record = json.loads(record_path.read_text(encoding="utf-8"))
        assert record["rerun_of"] == source.name, record_path.name

    # The source run is never mutated.
    assert {
        path.name: path.read_bytes() for path in source.iterdir() if path.is_file()
    } == source_snapshot


def test_rerun_missing_cache_fails_with_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    source = _generate_a_run(monkeypatch, tmp_path)
    (source / "scene.py").unlink()

    result = runner.invoke(app, ["rerun", source.name, "--runs-root", str(tmp_path / "runs")])

    assert result.exit_code == 1
    assert "bayan generate" in result.output


def test_rerun_unknown_run_id_fails_clearly(tmp_path: Path):
    result = runner.invoke(
        app, ["rerun", "20990101T0000Z-deadbeef", "--runs-root", str(tmp_path / "runs")]
    )

    assert result.exit_code == 1
    assert "not found" in result.output


def test_rerun_of_a_gate_blocked_run_surfaces_the_gate_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    """A tampered cache replays deterministically: the gate blocks again."""
    from bayan.pipeline.models import CodeAttemptEvidence

    source = _generate_a_run(monkeypatch, tmp_path)
    tampered = (
        "from manim import *\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        Text("مرحبا بكم")\n'
    )
    (source / "scene.py").write_text(tampered, encoding="utf-8")

    class _UngatedCoder:
        def generate_scene_code(self, *, plan, system_prompt, user_prompt):
            return CodeAttemptEvidence(
                code=tampered,
                raw_response=tampered,
                fingerprint="tampered",
                model="fake",
                usage=None,
            )

    runs_root = tmp_path / "runs"
    calls_at_start = len(fake_render)
    result = runner.invoke(app, ["rerun", source.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    # The gate failure must block the container: no new render calls during rerun.
    assert len(fake_render) == calls_at_start
    rerun_dir = next(path for path in runs_root.iterdir() if path.is_dir() and path != source)
    gates_record = json.loads((rerun_dir / "records" / "04-gates.json").read_text(encoding="utf-8"))
    assert gates_record["status"] == "failed"
    assert not (rerun_dir / "draft.mp4").exists()


def test_rerun_help_documents_no_api_key():
    result = runner.invoke(app, ["rerun", "--help"])

    assert result.exit_code == 0
    assert "API key" in result.output


def test_rerun_of_invalid_cached_plan_fails_with_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    source = _generate_a_run(monkeypatch, tmp_path)
    (source / "plan.json").write_text("{ not json", encoding="utf-8")

    result = runner.invoke(app, ["rerun", source.name, "--runs-root", str(tmp_path / "runs")])

    assert result.exit_code == 1
    assert "bayan generate" in result.output


def test_rerun_of_a_corrupt_summary_still_reruns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    """An unreadable run summary must not crash the rerun with a traceback."""
    source = _generate_a_run(monkeypatch, tmp_path)
    (source / "run.json").write_text("{ corrupted", encoding="utf-8")
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["rerun", source.name, "--runs-root", str(runs_root)])

    assert result.exit_code == 0, result.output
