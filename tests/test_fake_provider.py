"""FakeProvider tests: the repair allowlist cannot drift from the gates.

The fake's repairer derives what it keeps from the preflight allowlist
(``ALLOWED_MODULES``), so pipeline import policy exists in exactly one
place; these tests pin that derivation.
"""

import pytest

from bayan.pipeline.preflight import ALLOWED_MODULES, gates_blocked, run_gates
from bayan.pipeline.taxonomy import FailureClassification
from bayan.testing import FakeProvider, imports_allowed_module

DISALLOWED_IMPORT_SCENE = (
    "from manim import *\n"
    "import subprocess\n"
    "\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        pass\n"
)


def _repair(code: str) -> str:
    evidence = FakeProvider().repair_scene_code(
        code=code,
        classification=FailureClassification(
            type="preflight",
            category="disallowed_import",
            suggestion="drop the disallowed import",
        ),
        plan=None,
    )
    return evidence.code


def test_repair_strips_disallowed_imports_and_passes_the_gates():
    repaired = _repair(DISALLOWED_IMPORT_SCENE)

    assert "subprocess" not in repaired
    assert not gates_blocked(run_gates(repaired))


@pytest.mark.parametrize("module", sorted(ALLOWED_MODULES))
def test_repair_keeps_every_module_the_gates_allow(module):
    """Every allowlisted import survives repair and the repaired scene gates."""
    scene = (
        "from manim import *\n"
        f"import {module}\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        pass\n"
    )

    repaired = _repair(scene)

    assert f"import {module}" in repaired
    assert not gates_blocked(run_gates(repaired))


def test_import_matching_is_not_prefix_based():
    """``import mathx`` must not ride on the ``math`` allowlist entry."""
    assert imports_allowed_module("import math")
    assert not imports_allowed_module("import mathx")
    assert imports_allowed_module("from bayan.utils.arabic_helper import ArabicText")


def test_gate_tightening_tightens_the_fake(monkeypatch: pytest.MonkeyPatch):
    """The derivation is live: shrink the allowlist and the fake keeps less."""
    monkeypatch.setattr("bayan.testing.ALLOWED_MODULES", frozenset({"manim"}))

    repaired = _repair(DISALLOWED_IMPORT_SCENE.replace("subprocess", "math"))

    assert "import math" not in repaired
    assert "from manim import *" in repaired
