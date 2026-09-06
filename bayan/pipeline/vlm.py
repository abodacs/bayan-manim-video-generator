"""VLM critic stub: records an honest verdict instead of pretending to run.

The vision-model critique is out of scope for the MVP (epic #68 out-of-scope
note). Only this stub exists -- no network calls, no client construction --
so `bayan generate --vlm` can record `not_implemented` and complete on the
deterministic verdict.
"""

from __future__ import annotations

from bayan.pipeline.models import CheckResult


def vlm_critique() -> CheckResult:
    """Return the placeholder verdict for the vision-model critique."""
    return CheckResult(
        check="vlm",
        status="not_implemented",
        evidence="The VLM critic is not implemented; it is out of scope for the MVP per epic #68.",
        suggestion="Rely on the deterministic checks plus teacher review.",
    )
