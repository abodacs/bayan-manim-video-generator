import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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
        record_path = self._get_record_path()
        record_path.write_text(json.dumps(record_data, indent=2), encoding="utf-8")

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
        review_packet_path = self.run_dir / "review_packet.md"
        review_packet_path.write_text(
            f"# Human Review Required\n\nReason: {reason}",
            encoding="utf-8",
        )

    def attempt_repair(self, error_evidence: dict[str, Any]) -> dict[str, Any]:
        # إيقاف التكرار فوراً إذا كان الخطأ متعلقاً بالسياسات أو الأمان
        if error_evidence.get("category") in ("security", "policy"):
            self._create_review_packet(
                f"Security/Policy violation detected: {error_evidence.get('category')}"
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
