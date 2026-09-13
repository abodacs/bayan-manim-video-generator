"""The failure taxonomy: the repair loop's shared vocabulary.

Every pipeline failure -- a preflight gate, a critic check, a container
crash, or a provider error -- classifies into a typed record mapping the
gate names (#80) and check names (#82) onto repair categories. It is a
mapping, never string re-parsing, and it lives beside the repair stage it
serves: the renderer's own errors stay in :mod:`bayan.renderer.errors`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from bayan.pipeline.models import CheckResult
    from bayan.pipeline.preflight import GateResult


FailureType = Literal["preflight", "render", "critic", "provider"]

RepairCategory = Literal[
    "syntax",
    "disallowed_import",
    "banned_construct",
    "arabic_layout",
    "render_crash",
    "render_timeout",
    "missing_artifact",
    "duration_out_of_bounds",
    "text_overflow",
    "provider_error",
    "unknown",
]

# Categories that are treated as policy violations: they never trigger an
# LLM repair attempt and go straight to the human review packet.
POLICY_CATEGORIES: frozenset[str] = frozenset({"banned_construct"})

GATE_CATEGORIES: dict[str, RepairCategory] = {
    "syntax": "syntax",
    "imports": "disallowed_import",
    "bans": "banned_construct",
    "arabic": "arabic_layout",
}

CHECK_CATEGORIES: dict[str, RepairCategory] = {
    "render_artifacts": "missing_artifact",
    "duration": "duration_out_of_bounds",
    "overflow": "text_overflow",
    "beat_coverage": "arabic_layout",
    "vlm": "unknown",
}


@dataclass(frozen=True)
class FailureClassification:
    """Typed classification of one pipeline failure for bounded repair."""

    type: FailureType
    category: RepairCategory
    suggestion: str
    scope: str = "code"
    evidence: str = ""


def classify_gate_evidence(gate_results: list[dict[str, Any]]) -> RepairCategory | None:
    """Map a gates stage record's serialized gate results onto the taxonomy.

    The dict-level twin of :func:`classify_gate_results`: stage records
    keep their gate evidence as plain JSON, so readers of past runs
    classify through this adapter instead of restating the mapping.
    """
    return _first_failed_category(gate_results, "gate", GATE_CATEGORIES)


def classify_critic_evidence(check_results: list[dict[str, Any]]) -> RepairCategory | None:
    """Map a critic stage record's serialized check results onto the taxonomy."""
    return _first_failed_category(check_results, "check", CHECK_CATEGORIES)


def _first_failed_category(
    results: list[dict[str, Any]],
    key: str,
    mapping: dict[str, RepairCategory],
) -> RepairCategory | None:
    """The first failed result's category, or None when nothing failed."""
    for result in results:
        if result.get("status") == "failed":
            return mapping.get(str(result.get(key) or ""), "unknown")
    return None


def classify_gate_results(gate_results: list[GateResult]) -> FailureClassification | None:
    """Map the first failed preflight gate onto the taxonomy."""
    for result in gate_results:
        if result.status != "failed":
            continue
        category = GATE_CATEGORIES.get(result.gate, "unknown")
        location = f" (line {result.line})" if result.line else ""
        return FailureClassification(
            type="preflight",
            category=category,
            suggestion=result.suggestion or "Fix the reported violation.",
            evidence=f"{result.gate}{location}: {result.excerpt or ''}",
        )
    return None


def classify_critic_results(check_results: list[CheckResult]) -> FailureClassification | None:
    """Map the first failed critic check onto the taxonomy."""
    for result in check_results:
        if result.status != "failed":
            continue
        category = CHECK_CATEGORIES.get(result.check, "unknown")
        return FailureClassification(
            type="critic",
            category=category,
            suggestion=result.suggestion or "Fix the reported artifact problem.",
            evidence=f"{result.check}: {result.evidence}",
        )
    return None


def classify_render_failure(evidence: str) -> FailureClassification:
    """Map a render-stage failure message onto crash or timeout."""
    if "timed out" in evidence.lower():
        return FailureClassification(
            type="render",
            category="render_timeout",
            suggestion="The scene is too slow for the render timeout; simplify the "
            "animations or reduce the number of played animations.",
            evidence=evidence,
        )
    return FailureClassification(
        type="render",
        category="render_crash",
        suggestion="The scene crashed inside the worker; check the animation calls "
        "against the Manim API and the single GeneratedScene contract.",
        evidence=evidence,
    )


def classify_provider_error(evidence: str) -> FailureClassification:
    """Map a provider/LLM failure onto the provider category."""
    return FailureClassification(
        type="provider",
        category="provider_error",
        suggestion=f"The provider call failed: {evidence}. Retry once conditions recover.",
        evidence=evidence,
    )
