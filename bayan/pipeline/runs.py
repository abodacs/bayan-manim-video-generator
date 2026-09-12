"""Read-model over past generate runs: what ``bayan runs`` reports.

The inspection rules live here, not in the CLI: what counts as a readable
run, which artifacts a generate run produces, and how the records' cost
total relates to the run summary. The CLI only formats what this module
returns, so future consumers (an export command, a dashboard) reuse the
same answers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bayan.pipeline.coder import SCENE_FILENAME
from bayan.pipeline.planner import PLAN_FILENAME
from bayan.pipeline.records import (
    RECORDS_DIRNAME,
    StageRecord,
    total_cost_usd,
)
from bayan.pipeline.spine import (
    DRAFT_FILENAME,
    PREVIEW_FILENAME,
    RUN_SUMMARY_FILENAME,
    STAGES,
)
from bayan.pipeline.taxonomy import (
    RepairCategory,
    classify_critic_evidence,
    classify_gate_evidence,
    classify_provider_error,
    classify_render_failure,
)

RUN_ARTIFACTS: tuple[str, ...] = (PLAN_FILENAME, SCENE_FILENAME, DRAFT_FILENAME, PREVIEW_FILENAME)
MEDIA_FILENAME = DRAFT_FILENAME

# The spine's registry owns the stage order and each stage's record file;
# the read model reuses it to look up the record behind a summary's
# failing stage name instead of restating the layout.
STAGE_RECORD_FILENAMES: dict[str, str] = {stage.name: stage.record_filename for stage in STAGES}


def iter_run_dirs(runs_root: Path) -> list[Path]:
    """A run's directory holds generated runs, sorted oldest to newest."""
    if not runs_root.is_dir():
        return []
    return sorted(path for path in runs_root.iterdir() if path.is_dir())


def load_run_summary(run_dir: Path) -> dict[str, Any] | None:
    """Read a run's summary, or None when missing or unreadable."""
    summary_path = run_dir / RUN_SUMMARY_FILENAME
    if not summary_path.is_file():
        return None
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def has_media(run_dir: Path) -> bool:
    """Whether the run produced its video artifact."""
    return (run_dir / MEDIA_FILENAME).is_file()


def records_cost(run_dir: Path) -> float | None:
    """Sum per-attempt costs from stage records; None when nothing recorded."""
    return total_cost_usd(run_dir)


def failure_category(run_dir: Path, stage: str) -> RepairCategory | None:
    """The taxonomy category of the named failing stage, or None.

    Reads that stage's record — the same typed evidence the spine
    classified at run time — so the answer follows the summary's failing
    stage even when an earlier stage failed once and was repaired (its
    stale failed record stays on disk). The stage-to-record mapping comes
    from the spine's registry; unknown stage names yield None.
    """
    record_filename = STAGE_RECORD_FILENAMES.get(stage)
    if record_filename is None:
        return None
    record = _load_stage_record(run_dir / RECORDS_DIRNAME / record_filename)
    if record is None or record.status != "failed":
        return None
    return _record_category(record)


def _load_stage_record(record_path: Path) -> StageRecord | None:
    """Read one stage record by path, or None when missing or invalid."""
    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return StageRecord.model_validate(data)
    except ValidationError:
        return None


def _record_category(record: StageRecord) -> RepairCategory:
    """Map one failed stage record's typed evidence onto the taxonomy."""
    gates = _evidence_results(record, "gates")
    if gates:
        return classify_gate_evidence(gates) or "unknown"
    checks = _evidence_results(record, "checks")
    if checks:
        return classify_critic_evidence(checks) or "unknown"
    if record.stage == "render":
        return classify_render_failure(record.failure or "").category
    if record.stage in ("planning", "coding", "profile"):
        return classify_provider_error(record.failure or "unknown").category
    return "unknown"


def _evidence_results(record: StageRecord, key: str) -> list[dict[str, Any]]:
    """A record's stage-specific evidence list, or an empty list."""
    results = (record.model_extra or {}).get(key)
    if not isinstance(results, list):
        return []
    return [result for result in results if isinstance(result, dict)]
