"""Typed agent roles with bounded repair semantics.

``RepairAgent`` is wired into the generate pipeline through
:class:`bayan.pipeline.repair.RepairService`: it owns the attempt budget
(max 2 per run), the policy/security short-circuit to the review packet,
and loop detection via input hashes. Its ``agent_records/`` entries are the
agent's own audit trail; the run's repair record of truth is
``records/07-repair.json`` written by RepairService. The legacy orchestrator
(``bayan run``) does not use these roles.
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


class RepairAgent(BaseAgent):
    role_name = "repair"

    def __init__(self, run_dir: Path, max_attempts: int = 2) -> None:
        super().__init__(run_dir=run_dir)
        self.max_attempts = max_attempts
        self.attempts = 0
        self.seen_signatures: set[str] = set()

    def _create_review_packet(self, reason: str) -> None:
        """Writes review packet atomically using a temporary file."""
        atomic_write_text(
            self.run_dir / "review_packet.md",
            f"# Human Review Required\n\nReason: {reason}\n",
        )

    def attempt_repair(self, error_evidence: dict[str, Any]) -> dict[str, Any]:
        # Stop immediately if the error is policy/security related.
        if error_evidence.get("category") in ("security", "policy"):
            message = str(error_evidence.get("message") or "no message recorded")
            self._create_review_packet(
                f"Security/Policy violation detected ({error_evidence.get('category')}): {message}"
            )
            result = {
                "role": self.role_name,
                "attempt": self.attempts,
                "status": "policy_blocked",
                "timestamp": datetime.now(UTC).isoformat(),
                "next_action": "human_review",
                "evidence": error_evidence,
            }
            self._write_record(result)
            return result

        self.attempts += 1

        if self.attempts > self.max_attempts:
            self._create_review_packet("Repair attempts exhausted.")
            result = {
                "role": self.role_name,
                "attempt": self.attempts,
                "status": "exhausted",
                "timestamp": datetime.now(UTC).isoformat(),
                "next_action": "human_review",
                "evidence": error_evidence,
            }
            self._write_record(result)
            return result

        result = {
            "role": self.role_name,
            "attempt": self.attempts,
            "status": "attempted",
            "timestamp": datetime.now(UTC).isoformat(),
            "next_action": "re_render",
            "evidence": error_evidence,
        }
        self._write_record(result)
        return result

    def run_with_loop_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        input_hash = self._hash_input(payload)
        signature = f"{self.role_name}:{input_hash}"

        if signature in self.seen_signatures:
            self._create_review_packet("Loop detected.")
            result = {
                "role": self.role_name,
                "input_hash": input_hash,
                "status": "loop_detected",
                "timestamp": datetime.now(UTC).isoformat(),
                "next_action": "human_review",
            }
            self._write_record(result)
            return result

        self.seen_signatures.add(signature)
        return self.run(payload)
