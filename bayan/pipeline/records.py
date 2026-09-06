"""Shared run-record plumbing for pipeline stage services.

Every stage writes one JSON record under ``records/`` in the run directory.
Records share the identity keys (``stage``, ``status``, ``created_at``,
``failure``); evidence keys are stage-specific, and each stage names its
artifact pointer after the artifact it delivers (``plan``, ``scene``,
``draft``/``preview``) so ``bayan runs show`` can render them uniformly.

This module is the record contract's single owner: stage services build
their records through :func:`stage_record`, and every reader that aggregates
across records (the run summary, ``bayan runs``) goes through
:func:`iter_stage_records`, :func:`total_cost_usd`, and :func:`first_model`
instead of re-walking the record shape.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bayan.utils.atomic_io import atomic_write_text

RECORDS_DIRNAME = "records"


def stage_record(
    stage: str,
    status: str,
    failure: str | None,
    **evidence: Any,
) -> dict[str, Any]:
    """Build one stage record's shared identity keys, plus stage evidence.

    Every stage record starts from this shape; the per-stage builders only
    supply their evidence keys. ``created_at`` is stamped here so no stage
    can forget it.
    """
    return {
        "stage": stage,
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "failure": failure,
        **evidence,
    }


def write_stage_record(run_dir: Path, record: dict[str, Any], filename: str | None = None) -> Path:
    """Atomically write a stage record under the run's records directory.

    The record's ``stage`` key names the file by default (``planning.json``,
    ``coding.json``); callers that own the layout -- the generate pipeline
    spine, with its order-prefixed names -- pass ``filename`` explicitly.
    """
    records_dir = run_dir / RECORDS_DIRNAME
    records_dir.mkdir(parents=True, exist_ok=True)
    record_path = records_dir / (filename or f"{record['stage']}.json")
    atomic_write_text(
        record_path,
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
    )
    return record_path


def iter_stage_records(run_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed stage records in pipeline order, skipping unreadable ones."""
    records_dir = run_dir / RECORDS_DIRNAME
    if not records_dir.is_dir():
        return
    for record_path in sorted(records_dir.glob("*.json")):
        try:
            yield json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
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
        for attempt in record.get("attempts") or []:
            cost = attempt.get("cost_estimate_usd")
            if isinstance(cost, int | float):
                readable = True
                total += float(cost)
    return round(total, 6) if readable else None


def first_model(run_dir: Path) -> str | None:
    """Return the model name recorded by the first stage that used one."""
    for record in iter_stage_records(run_dir):
        for attempt in record.get("attempts") or []:
            if attempt.get("model"):
                return str(attempt["model"])
    return None


def evidence_fingerprint(model: str, base_url: str, payload: str) -> str:
    """Stable fingerprint of one provider call's identity and input payload."""
    return hashlib.sha256(f"{model}:{base_url}:{payload}".encode()).hexdigest()
