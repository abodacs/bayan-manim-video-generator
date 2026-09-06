"""Shared run-record plumbing for pipeline stage services.

Every stage writes one JSON record under ``records/`` in the run directory,
with the same key shape (stage, status, attempts, failure, artifact pointer)
so ``bayan runs show`` can render them uniformly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bayan.utils.atomic_io import atomic_write_text

RECORDS_DIRNAME = "records"


def write_stage_record(run_dir: Path, record: dict[str, Any]) -> Path:
    """Atomically write a stage record under the run's records directory.

    The record's ``stage`` key names the file, so planning records land in
    ``records/planning.json`` and coding records in ``records/coding.json``.
    """
    records_dir = run_dir / RECORDS_DIRNAME
    records_dir.mkdir(parents=True, exist_ok=True)
    record_path = records_dir / f"{record['stage']}.json"
    atomic_write_text(
        record_path,
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
    )
    return record_path


def evidence_fingerprint(model: str, base_url: str, payload: str) -> str:
    """Stable fingerprint of one provider call's identity and input payload."""
    return hashlib.sha256(f"{model}:{base_url}:{payload}".encode()).hexdigest()
