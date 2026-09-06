"""RepairService tests: classify, minimal fix, re-gate, capped at two attempts."""

import json

from bayan.pipeline.models import CheckResult, CodeAttemptEvidence, LessonPlan
from bayan.pipeline.preflight import run_gates
from bayan.pipeline.repair import MAX_REPAIR_ATTEMPTS, RepairService
from bayan.pipeline.taxonomy import (
    FailureClassification,
    classify_critic_results,
    classify_gate_results,
    classify_provider_error,
    classify_render_failure,
)
from bayan.testing import FakeProvider

ARABIC_PROMPT = "شرح القسمة على الأعداد ذات المنزلة الواحدة"


def _plan() -> LessonPlan:
    return FakeProvider().generate_lesson_plan(ARABIC_PROMPT, "msa-western").plan


def _evidence(code: str) -> CodeAttemptEvidence:
    return CodeAttemptEvidence(
        code=code, raw_response=code, fingerprint="scripted", model="scripted", usage=None
    )


class _ScriptedRepairer:
    """Replays queued repaired code texts, counting LLM repair calls."""

    def __init__(self, outcomes: list[str]) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    def repair_scene_code(
        self, *, code: str, classification: FailureClassification, plan: LessonPlan
    ) -> CodeAttemptEvidence:
        self.calls += 1
        return _evidence(self._outcomes.pop(0) if self._outcomes else code)


BANNED_IMPORT_SCENE = (
    "from manim import *\n"
    "import subprocess\n"
    "\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        pass\n"
)
RAW_ARABIC_SCENE = (
    "from manim import *\n"
    "\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    '        Text("مرحبا بكم")\n'
)
FIXED_SCENE = (
    "from manim import *\n"
    "from bayan.utils.arabic_helper import ArabicText, rtl_glyphs\n"
    "\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    '        message = ArabicText("نلاحظ أن 12")\n'
)


# -------------------------------------------------------------------------
# 1. Classification maps gate/check names onto the taxonomy
# -------------------------------------------------------------------------


def test_failure_classification_covers_all_sources():
    gate_results = run_gates(BANNED_IMPORT_SCENE)
    gate_classification = classify_gate_results(gate_results)
    assert gate_classification is not None
    assert gate_classification.type == "preflight"
    assert gate_classification.category == "disallowed_import"
    assert gate_classification.scope == "code"
    assert gate_classification.suggestion

    arabic_results = run_gates(RAW_ARABIC_SCENE)
    arabic_classification = classify_gate_results(arabic_results)
    assert arabic_classification is not None
    assert arabic_classification.category == "arabic_layout"

    check_results = [
        CheckResult(
            check="duration",
            status="failed",
            evidence="Measured 3.0s, below the 10s minimum.",
        )
    ]
    critic_classification = classify_critic_results(check_results)
    assert critic_classification is not None
    assert critic_classification.type == "critic"
    assert critic_classification.category == "duration_out_of_bounds"

    render_classification = classify_render_failure("render video timed out after 180s")
    assert render_classification.type == "render"
    assert render_classification.category == "render_timeout"

    crash_classification = classify_render_failure("worker exited with code 1")
    assert crash_classification.category == "render_crash"

    provider_classification = classify_provider_error("connection reset")
    assert provider_classification.type == "provider"
    assert provider_classification.category == "provider_error"

    assert classify_gate_results(run_gates(FIXED_SCENE)) is None


# -------------------------------------------------------------------------
# 2. Bounded repair loop with re-gating
# -------------------------------------------------------------------------


def test_repair_never_exceeds_two_attempts(tmp_path):
    provider = _ScriptedRepairer([BANNED_IMPORT_SCENE] * 10)
    service = RepairService(provider=provider, run_dir=tmp_path)
    classification = FailureClassification(
        type="preflight",
        category="disallowed_import",
        suggestion="remove the import",
    )

    for _ in range(5):
        outcome = service.repair_round(
            code=BANNED_IMPORT_SCENE, classification=classification, plan=_plan()
        )
        if outcome.status == "exhausted":
            break

    assert provider.calls <= MAX_REPAIR_ATTEMPTS
    assert outcome.status == "exhausted"


def test_exhaustion_writes_failure_record(tmp_path):
    provider = _ScriptedRepairer([BANNED_IMPORT_SCENE] * 5)
    service = RepairService(provider=provider, run_dir=tmp_path)
    classification = FailureClassification(
        type="preflight",
        category="disallowed_import",
        suggestion="remove the import",
    )

    for _ in range(5):
        outcome = service.repair_round(
            code=BANNED_IMPORT_SCENE, classification=classification, plan=_plan()
        )
        if outcome.status == "exhausted":
            break

    assert outcome.status == "exhausted"
    record = json.loads((tmp_path / "records" / "repair.json").read_text(encoding="utf-8"))
    assert record["status"] == "exhausted"
    assert record["last_evidence"]


def test_identical_fix_is_detected_as_a_loop(tmp_path):
    provider = _ScriptedRepairer([BANNED_IMPORT_SCENE])
    service = RepairService(provider=provider, run_dir=tmp_path)
    classification = FailureClassification(
        type="preflight",
        category="disallowed_import",
        suggestion="remove the import",
    )

    first = service.repair_round(
        code=BANNED_IMPORT_SCENE, classification=classification, plan=_plan()
    )
    second = service.repair_round(
        code=first.code or BANNED_IMPORT_SCENE, classification=classification, plan=_plan()
    )

    assert second.status == "exhausted"
    assert "identical" in (second.failure or "")


def test_policy_category_short_circuits_to_review_packet(tmp_path):
    provider = _ScriptedRepairer([])
    service = RepairService(provider=provider, run_dir=tmp_path)

    outcome = service.repair_round(
        code=BANNED_IMPORT_SCENE,
        classification=FailureClassification(
            type="preflight",
            category="banned_construct",
            suggestion="dynamic execution is banned",
        ),
        plan=_plan(),
    )

    assert provider.calls == 0
    assert outcome.status == "policy_blocked"
    assert (tmp_path / "review_packet.md").exists()
    record = json.loads((tmp_path / "records" / "repair.json").read_text(encoding="utf-8"))
    assert record["status"] == "policy_blocked"


def test_render_failure_classification_feeds_the_loop(tmp_path):
    provider = _ScriptedRepairer([FIXED_SCENE])
    service = RepairService(provider=provider, run_dir=tmp_path)

    outcome = service.repair_round(
        code=RAW_ARABIC_SCENE,
        classification=classify_render_failure("worker exited with code 1"),
        plan=_plan(),
    )

    assert outcome.status == "completed"
    assert provider.calls == 1


# -------------------------------------------------------------------------
# 3. Deterministic FakeProvider repair
# -------------------------------------------------------------------------


def test_fake_provider_repair_strips_banned_import():
    provider = FakeProvider()

    evidence = provider.repair_scene_code(
        code=BANNED_IMPORT_SCENE,
        classification=FailureClassification(
            type="preflight",
            category="disallowed_import",
            suggestion="remove the import",
        ),
        plan=_plan(),
    )

    from bayan.pipeline.preflight import gates_blocked, run_gates

    assert "subprocess" not in evidence.code
    assert not gates_blocked(run_gates(evidence.code))


def test_fake_provider_repair_swaps_text_for_arabic_text():
    provider = FakeProvider()

    evidence = provider.repair_scene_code(
        code=RAW_ARABIC_SCENE,
        classification=FailureClassification(
            type="preflight",
            category="arabic_layout",
            suggestion="use ArabicText",
        ),
        plan=_plan(),
    )

    assert "ArabicText(" in evidence.code
    from bayan.pipeline.preflight import gates_blocked, run_gates

    assert not gates_blocked(run_gates(evidence.code))
