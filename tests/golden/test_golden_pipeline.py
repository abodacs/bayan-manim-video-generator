"""Golden pipeline tests: ~20 curriculum prompts, deterministic, no Docker.

Every case runs the spine up to and including the preflight gates with a
fixture-driven provider -- zero network, zero API keys, zero container
calls. Rendering golden prompts for real is a manual local action with
Docker; these tests must never render. Negative cases pin BDD scenario
#70: weakening a gate turns the matching golden test red, naming the
prompt file (test id) and the stage (gates record).
"""

import json
from pathlib import Path
from typing import Any

import pytest

from bayan.pipeline.models import (
    CodeAttemptEvidence,
    LessonPlan,
    PlanAttemptEvidence,
)
from bayan.pipeline.spine import GeneratePipeline, RunContext, RunInputs

GOLDEN_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = GOLDEN_DIR / "prompts"

EXECUTED_RECORDS = ["01-plan.json", "02-profile.json", "03-code.json", "04-gates.json"]


def _golden_cases() -> list[tuple[Path, dict[str, Any]]]:
    cases: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(PROMPTS_DIR.glob("*.json")):
        if path.name.endswith("-plan.json"):
            continue
        cases.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return cases


GOLDEN_CASES = _golden_cases()


class GoldenProvider:
    """Deterministic scripted provider replaying the recorded fixtures."""

    def __init__(self, plan: LessonPlan, scene: str, prompt_id: str) -> None:
        self._plan = plan
        self._scene = scene
        self._id = prompt_id

    def generate_lesson_plan(self, prompt: str, profile: str):
        return PlanAttemptEvidence(
            plan=self._plan,
            raw_response=self._plan.model_dump_json(ensure_ascii=False),
            fingerprint=f"golden:{self._id}",
            model="golden",
            usage=None,
        )

    def generate_scene_code(self, *, plan, system_prompt, user_prompt):
        return CodeAttemptEvidence(
            code=self._scene,
            raw_response=self._scene,
            fingerprint=f"golden:{self._id}",
            model="golden",
            usage=None,
        )


def _context_for(record: dict[str, Any], provider: GoldenProvider, run_dir: Path) -> RunContext:
    return RunContext(
        inputs=RunInputs(
            run_dir=run_dir,
            prompt=record["prompt"],
            profile=record["profile"],
            quality="draft",
            planner=provider,
            coder=provider,
        )
    )


def test_one_prompt_runs_to_preflight_offline(tmp_path: Path):
    prompt_path, record = GOLDEN_CASES[0]
    plan = LessonPlan.model_validate_json(
        (PROMPTS_DIR / f"{record['id']}-plan.json").read_text(encoding="utf-8")
    )
    scene = (PROMPTS_DIR / f"{record['id']}-scene.py").read_text(encoding="utf-8")
    provider = GoldenProvider(plan, scene, record["id"])
    run_dir = tmp_path / "run"

    result = GeneratePipeline().run(_context_for(record, provider, run_dir), stop_after="gates")

    assert result.status == "completed"
    executed = sorted(path.name for path in (run_dir / "records").glob("*.json"))
    assert executed == EXECUTED_RECORDS
    assert not (run_dir / "draft.mp4").exists()
    assert not (run_dir / "records" / "05-render.json").exists()
    assert not (run_dir / "records" / "06-critic.json").exists()


@pytest.mark.parametrize(
    "prompt_path", [path for path, _ in GOLDEN_CASES], ids=[path.stem for path, _ in GOLDEN_CASES]
)
def test_golden_prompt_matches_expected_gates(prompt_path: Path, tmp_path: Path):
    record = json.loads(prompt_path.read_text(encoding="utf-8"))
    plan = LessonPlan.model_validate_json(
        (PROMPTS_DIR / f"{record['id']}-plan.json").read_text(encoding="utf-8")
    )
    assert len(plan.beats) == record["expected"]["beats"]
    scene = (PROMPTS_DIR / f"{record['id']}-scene.py").read_text(encoding="utf-8")
    provider = GoldenProvider(plan, scene, record["id"])
    run_dir = tmp_path / "run"

    result = GeneratePipeline().run(_context_for(record, provider, run_dir), stop_after="gates")

    executed = sorted(path.name for path in (run_dir / "records").glob("*.json"))
    assert executed == EXECUTED_RECORDS
    assert not (run_dir / "draft.mp4").exists()

    expected = record["expected"]["gates"]
    gates_record = json.loads((run_dir / "records" / "04-gates.json").read_text(encoding="utf-8"))
    if expected == "pass":
        assert result.status == "completed", gates_record
        assert gates_record["status"] == "completed"
        assert all(gate["status"] == "passed" for gate in gates_record["gates"])
    else:
        failing_gate = expected.split(":", 1)[1]
        assert result.status == "failed"
        assert gates_record["status"] == "failed"
        assert any(
            entry["gate"] == failing_gate and entry["status"] == "failed"
            for entry in gates_record["gates"]
        ), gates_record["gates"]


def test_two_consecutive_runs_produce_identical_records(tmp_path: Path):
    prompt_path, record = GOLDEN_CASES[0]
    plan = LessonPlan.model_validate_json(
        (PROMPTS_DIR / f"{record['id']}-plan.json").read_text(encoding="utf-8")
    )
    scene = (PROMPTS_DIR / f"{record['id']}-scene.py").read_text(encoding="utf-8")

    def normalized(run_dir: Path) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for record_path in sorted((run_dir / "records").glob("*.json")):
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record.pop("created_at", None)
            out[record_path.name] = record
        return out

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    GeneratePipeline().run(
        _context_for(record, GoldenProvider(plan, scene, "d"), first_dir), stop_after="gates"
    )
    GeneratePipeline().run(
        _context_for(record, GoldenProvider(plan, scene, "d"), second_dir), stop_after="gates"
    )

    assert normalized(first_dir) == normalized(second_dir)


def test_golden_set_size_and_no_network_imports():
    prompts = [path for path, _ in GOLDEN_CASES]
    assert 18 <= len(prompts) <= 22
    for path in sorted(PROMPTS_DIR.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert "requests" not in text
        assert "OpenAI(" not in text
