"""Deterministic critic tests over fabricated artifacts (no Docker, no LLM)."""

from pathlib import Path

import pytest
from PIL import Image

from bayan.pipeline.critic import (
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    check_beat_coverage,
    check_duration,
    check_overflow,
    critic_blocked,
    probe_duration_seconds,
    run_critic,
)
from bayan.pipeline.models import LessonBeat, LessonPlan
from bayan.pipeline.vlm import vlm_critique


def _png(path: Path, edge_touch: bool) -> Path:
    """A 100x60 black frame with a centered white block, optionally clipped."""
    image = Image.new("L", (100, 60), 0)
    if edge_touch:
        image.paste(255, (92, 0, 100, 60))
    else:
        image.paste(255, (40, 20, 60, 40))
    image.save(path)
    return path


def _code_with(*texts: str) -> str:
    lines = ["from manim import *", "from bayan.utils.arabic_helper import ArabicText"]
    lines.extend(f'message = ArabicText("{text}")' for text in texts)
    return "\n".join(lines) + "\n"


def _plan() -> LessonPlan:
    return LessonPlan(
        topic="اختبار الناقد",
        beats=[LessonBeat(title="الخطوة ١", on_screen_text="نلاحظ أن 12", insight_move="reveal")],
    )


def test_passing_artifacts_get_a_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    draft = tmp_path / "draft.mp4"
    draft.write_bytes(b"\x00\x00\x00\x18ftypmp42fake")
    preview = _png(tmp_path / "preview.png", edge_touch=False)
    monkeypatch.setattr("bayan.pipeline.critic.probe_duration_seconds", lambda video: 30.0)

    results = run_critic(
        plan=_plan(),
        code=_code_with("نلاحظ أن 12"),
        draft_path=draft,
        preview_path=preview,
        render_status="completed",
    )

    assert not critic_blocked(results)
    statuses = {result.check: result.status for result in results}
    assert statuses == {
        "render_artifacts": "passed",
        "duration": "passed",
        "overflow": "passed",
        "beat_coverage": "passed",
    }


def test_missing_or_empty_artifacts_fail_with_paths_named(tmp_path: Path):
    (tmp_path / "draft.mp4").write_bytes(b"")
    results = run_critic(
        plan=None,
        code=None,
        draft_path=tmp_path / "draft.mp4",
        preview_path=tmp_path / "preview.png",
        render_status="completed",
    )

    artifacts = results[0]
    assert artifacts.check == "render_artifacts"
    assert artifacts.status == "failed"
    assert "preview.png" in artifacts.evidence


def test_failed_render_record_fails_the_check(tmp_path: Path):
    draft = tmp_path / "draft.mp4"
    draft.write_bytes(b"fake")
    preview = _png(tmp_path / "preview.png", edge_touch=False)

    results = run_critic(
        plan=None,
        code=None,
        draft_path=draft,
        preview_path=preview,
        render_status="failed",
    )

    assert results[0].status == "failed"
    assert "render record status" in results[0].evidence


@pytest.mark.parametrize(
    ("measured", "word"),
    [(float(MIN_DURATION_SECONDS) - 7.0, "below"), (float(MAX_DURATION_SECONDS) + 220.0, "above")],
)
def test_duration_bounds_fail_with_measured_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, measured: float, word: str
):
    video = tmp_path / "draft.mp4"
    video.write_bytes(b"fake")
    monkeypatch.setattr("bayan.pipeline.critic.probe_duration_seconds", lambda video_path: measured)

    result = check_duration(video)

    assert result.status == "failed"
    assert word in result.evidence
    assert f"{measured:.1f}s" in result.evidence
    assert result.suggestion


def test_duration_is_not_applicable_without_ffprobe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("shutil.which", lambda name: None)
    video = tmp_path / "draft.mp4"
    video.write_bytes(b"fake")

    result = check_duration(video)

    assert result.status == "not_applicable"
    assert result.suggestion is None


def test_overflow_heuristic_flags_text_at_frame_edge(tmp_path: Path):
    clean = _png(tmp_path / "clean.png", edge_touch=False)
    clipped = _png(tmp_path / "clipped.png", edge_touch=True)

    assert check_overflow(clean).status == "passed"
    failed = check_overflow(clipped)
    assert failed.status == "failed"
    assert "border band" in failed.evidence
    assert failed.suggestion


def test_beat_text_coverage_fails_when_a_beat_is_missing():
    plan = LessonPlan(
        topic="t",
        beats=[
            LessonBeat(title="الخطوة ١", on_screen_text="الناتج 24", insight_move="reveal"),
            LessonBeat(title="الخطوة ٢", on_screen_text="الناتج 48", insight_move="summarize"),
        ],
    )
    code = _code_with("الناتج 24")

    results = check_beat_coverage(plan, code)

    assert len(results) == 1
    assert results[0].status == "failed"
    assert "beat 2" in results[0].evidence
    assert "الناتج 48" in results[0].evidence


def test_vlm_stub_records_not_implemented():
    result = vlm_critique()

    assert result.check == "vlm"
    assert result.status == "not_implemented"
    assert "epic #68" in result.evidence


def test_run_critic_appends_vlm_verdict_only_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    draft = tmp_path / "draft.mp4"
    draft.write_bytes(b"fake")
    preview = _png(tmp_path / "preview.png", edge_touch=False)
    monkeypatch.setattr("bayan.pipeline.critic.probe_duration_seconds", lambda video_path: 30.0)
    plan = _plan()
    code = _code_with("نلاحظ أن 12")

    without = run_critic(
        plan=plan, code=code, draft_path=draft, preview_path=preview, render_status="completed"
    )
    with_vlm = run_critic(
        plan=plan,
        code=code,
        draft_path=draft,
        preview_path=preview,
        render_status="completed",
        vlm=True,
    )

    assert "vlm" not in {result.check for result in without}
    verdicts = {result.check: result.status for result in with_vlm}
    assert verdicts["vlm"] == "not_implemented"
    assert not critic_blocked(with_vlm)


def _ffprobe_stub(tmp_path: Path, output: str) -> str:
    script = tmp_path / "ffprobe"
    script.write_text(f"#!/bin/sh\ncat <<'EOF'\n{output}\nEOF\n")
    script.chmod(0o755)
    return str(script)


def test_probe_duration_reads_ffprobe_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("shutil.which", lambda name: _ffprobe_stub(tmp_path, "42.5"))

    duration = probe_duration_seconds(tmp_path / "draft.mp4")

    assert duration == 42.5


def test_probe_duration_returns_none_on_garbage_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("shutil.which", lambda name: _ffprobe_stub(tmp_path, "N/A"))

    assert probe_duration_seconds(tmp_path / "draft.mp4") is None
