"""Shared run-record plumbing for pipeline stage services.

Every stage writes one JSON record under ``records/`` in the run directory.
Records share the identity keys (``stage``, ``status``, ``created_at``,
``failure``); evidence keys are stage-specific, and each stage names its
artifact pointer after the artifact it delivers (``plan``, ``scene``,
``draft``/``preview``) so ``bayan runs show`` can render them uniformly.

This module is the record contract's single owner: stage services build
their records through :func:`stage_record`, readers consume the typed
:class:`StageRecord` (status vocabulary included) instead of parsing raw
dicts, and every reader that aggregates across records (the run summary,
``bayan runs``) goes through :func:`iter_stage_records`,
:func:`total_cost_usd`, and :func:`first_model`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bayan.pipeline.models import AttemptRecord
from bayan.utils.atomic_io import atomic_write_text

RECORDS_DIRNAME = "records"

StageStatus = Literal["completed", "failed", "attempted", "exhausted", "policy_blocked"]

STAGE_STATUSES: Final[tuple[StageStatus, ...]] = get_args(StageStatus)

# The run summary's stage map adds one transient verdict: a stage whose
# failure the repair loop fixed is marked ``repaired`` for that run.
RunStageStatus = Literal[StageStatus, "repaired"]

RUN_STAGE_STATUSES: Final[tuple[RunStageStatus, ...]] = get_args(RunStageStatus)

# One display label per status across the run vocabulary; ``bayan runs``
# renders these instead of raw storage values. Unknown statuses fall
# through unchanged so foreign records stay readable.
STATUS_LABELS: Final[dict[str, str]] = {
    "completed": "completed",
    "failed": "failed",
    "repaired": "repaired",
    "attempted": "repair attempted",
    "exhausted": "repair exhausted",
    "policy_blocked": "repair policy-blocked",
    "ok": "ok",
    "invalid_output": "invalid output",
}


def status_label(status: str) -> str:
    """The human-readable label for a run-vocabulary status."""
    return STATUS_LABELS.get(status, status)


class StageRecord(BaseModel):
    """One stage record under ``records/`` -- the typed read/write contract.

    Evidence keys are stage-specific (``gates``, ``checks``, ``quality``,
    ``prompt``, ...), so the model keeps them verbatim at the top level via
    ``extra="allow"``; the shared identity keys and the per-attempt trail
    are typed, and consumers read those through attributes instead of
    parsing raw dicts.
    """

    model_config = ConfigDict(extra="allow")

    stage: str
    status: StageStatus
    created_at: datetime
    failure: str | None = None
    rerun_of: str | None = None
    attempts: list[AttemptRecord] = Field(default_factory=list)


def stage_record(
    stage: str,
    status: StageStatus,
    failure: str | None,
    **evidence: Any,
) -> StageRecord:
    """Build one stage record's shared identity keys, plus stage evidence.

    Every stage record starts from this shape; the per-stage builders only
    supply their evidence keys. ``created_at`` is stamped here so no stage
    can forget it.
    """
    return StageRecord(
        stage=stage,
        status=status,
        created_at=datetime.now(UTC),
        failure=failure,
        **evidence,
    )


def write_stage_record(run_dir: Path, record: StageRecord, filename: str | None = None) -> Path:
    """Atomically write a stage record under the run's records directory.

    The record's ``stage`` key names the file by default (``planning.json``,
    ``coding.json``); callers that own the layout -- the generate pipeline
    spine, with its order-prefixed names -- pass ``filename`` explicitly.
    """
    records_dir = run_dir / RECORDS_DIRNAME
    records_dir.mkdir(parents=True, exist_ok=True)
    record_path = records_dir / (filename or f"{record.stage}.json")
    atomic_write_text(
        record_path,
        json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
    )
    return record_path


def iter_stage_records(run_dir: Path) -> Iterator[StageRecord]:
    """Yield typed stage records in pipeline order, skipping unreadable ones.

    A record that fails validation (a foreign file, or a status outside the
    vocabulary) is skipped, exactly like unreadable JSON, so consumers
    never see a half-parsed record.
    """
    records_dir = run_dir / RECORDS_DIRNAME
    if not records_dir.is_dir():
        return
    for record_path in sorted(records_dir.glob("*.json")):
        try:
            data = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # ValueError covers json.JSONDecodeError and the
            # UnicodeDecodeError of a corrupted (non-UTF-8) file alike.
            continue
        if not isinstance(data, dict):
            continue
        try:
            yield StageRecord.model_validate(data)
        except ValidationError:
            continue


def total_cost_usd(run_dir: Path) -> float | None:
    """Sum every recorded attempt cost across the run's stage records.

    Returns ``None`` when the run carries no readable cost data (no records
    directory, or no attempt recorded a numeric cost) so callers can
    distinguish "nothing cost anything" from "nothing was recorded".
    """
    total = 0.0
    readable = False
    for record in iter_stage_records(run_dir):
        for attempt in record.attempts:
            if attempt.cost_estimate_usd is not None:
                readable = True
                total += attempt.cost_estimate_usd
    return round(total, 6) if readable else None


def first_model(run_dir: Path) -> str | None:
    """Return the model name recorded by the first stage that used one."""
    for record in iter_stage_records(run_dir):
        for attempt in record.attempts:
            if attempt.model:
                return attempt.model
    return None


def evidence_fingerprint(model: str, base_url: str, payload: str) -> str:
    """Stable fingerprint of one provider call's identity and input payload."""
    return hashlib.sha256(f"{model}:{base_url}:{payload}".encode()).hexdigest()
