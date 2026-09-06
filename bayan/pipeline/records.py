"""Shared run-record plumbing for pipeline stage services.

Every stage writes one JSON record under ``records/`` in the run directory.
Records share the identity keys (``stage``, ``status``, ``created_at``,
``failure``); evidence keys are stage-specific, and each stage names its
artifact pointer after the artifact it delivers (``plan``, ``scene``,
``draft``/``preview``) so ``bayan runs show`` can render them uniformly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bayan.utils.atomic_io import atomic_write_text

RECORDS_DIRNAME = "records"


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


def evidence_fingerprint(model: str, base_url: str, payload: str) -> str:
    """Stable fingerprint of one provider call's identity and input payload."""
    return hashlib.sha256(f"{model}:{base_url}:{payload}".encode()).hexdigest()
