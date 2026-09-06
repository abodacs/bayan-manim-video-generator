"""StageRecord contract tests: typed reads and the status vocabulary.

The record contract's shared identity keys, attempt trail, and status
vocabulary are typed in ``bayan.pipeline.records``; these tests pin the
round-trip through disk, the vocabulary's strictness, and the display
labels ``bayan runs`` renders.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bayan.pipeline.models import AttemptRecord
from bayan.pipeline.records import (
    STAGE_STATUSES,
    StageRecord,
    iter_stage_records,
    stage_record,
    status_label,
    total_cost_usd,
    write_stage_record,
)


def _write_raw(run_dir: Path, name: str, payload: dict) -> None:
    records_dir = run_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    (records_dir / name).write_text(
        json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def test_stage_record_round_trips_through_disk(tmp_path: Path):
    record = stage_record(
        "gates",
        "completed",
        None,
        rerun_of=None,
        gates=[{"gate": "syntax", "status": "passed"}],
    )
    write_stage_record(tmp_path, record, "04-gates.json")

    read_back = list(iter_stage_records(tmp_path))

    assert len(read_back) == 1
    parsed = read_back[0]
    assert parsed.stage == "gates"
    assert parsed.status == "completed"
    assert parsed.failure is None
    # Stage-specific evidence survives the typed round-trip at the top level.
    assert parsed.model_dump(mode="json")["gates"][0]["gate"] == "syntax"


def test_attempt_evidence_beyond_the_shared_shape_survives(tmp_path: Path):
    """Stage-specific attempt keys (repair's classification) round-trip."""
    entry = {
        "attempt": 1,
        "status": "ok",
        "model": "fake",
        "classification": {"type": "preflight", "category": "disallowed_import"},
        "code_after": "from manim import *",
    }
    write_stage_record(
        tmp_path, stage_record("repair", "attempted", None, attempts=[entry]), "07-repair.json"
    )

    parsed = next(iter(iter_stage_records(tmp_path)))

    dumped = parsed.attempts[0].model_dump()
    assert dumped["classification"]["category"] == "disallowed_import"
    assert dumped["code_after"] == "from manim import *"


def test_status_outside_the_vocabulary_is_rejected_on_build():
    with pytest.raises(ValidationError):
        StageRecord(stage="gates", status="mysterious", created_at="2026-09-07T00:00:00+00:00")


def test_unparseable_records_are_skipped(tmp_path: Path):
    _write_raw(
        tmp_path,
        "01-foreign.json",
        {"stage": "foreign", "status": "mysterious", "created_at": "2026-09-07T00:00:00+00:00"},
    )
    write_stage_record(tmp_path, stage_record("gates", "failed", "nope"), "02-gates.json")

    statuses = [record.status for record in iter_stage_records(tmp_path)]

    assert statuses == ["failed"]


def test_status_labels_cover_the_vocabulary_and_fall_through():
    for status in STAGE_STATUSES:
        assert status_label(status)

    assert status_label("policy_blocked") == "repair policy-blocked"
    assert status_label("mysterious") == "mysterious"


def test_total_cost_reads_the_typed_attempt_trail(tmp_path: Path):
    record = stage_record(
        "coding",
        "completed",
        None,
        attempts=[AttemptRecord(attempt=1, status="ok", model="m", cost_estimate_usd=0.25)],
    )
    write_stage_record(tmp_path, record, "03-code.json")

    assert total_cost_usd(tmp_path) == 0.25
