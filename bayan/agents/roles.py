"""Typed agent roles for the (future) agent layer.

These roles are plain record-keepers today. Bounded repair is owned end to
end by :mod:`bayan.pipeline.repair` -- budget, loop detection, and the
policy short-circuit -- which absorbed the former ``RepairAgent``; the
repair record of truth is ``records/07-repair.json``. The legacy
orchestrator (``bayan run``) does not use these roles.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bayan.utils.atomic_io import atomic_write_text


class BaseAgent:
    """Base class for all typed agent roles."""

    role_name: str = "base"

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.records_dir = run_dir / "agent_records"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.history: list[dict[str, Any]] = []

    def _get_record_path(self) -> Path:
        return self.records_dir / f"{self.role_name}.json"

    def _write_record(self, record_data: dict[str, Any]) -> None:
        """Saves agent execution record atomically using a temporary file."""
        atomic_write_text(self._get_record_path(), json.dumps(record_data, indent=2) + "\n")

    def _hash_input(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        input_hash = self._hash_input(payload)
        output = {
            "role": self.role_name,
            "input_hash": input_hash,
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "next_action": "continue",
            "payload": payload,
        }
        self._write_record(output)
        return output


class PlannerAgent(BaseAgent):
    role_name = "planner"


class TemplateAgent(BaseAgent):
    role_name = "template"


class RenderAgent(BaseAgent):
    role_name = "render"


class ValidationAgent(BaseAgent):
    role_name = "validation"
