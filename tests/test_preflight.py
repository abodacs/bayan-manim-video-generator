"""Preflight gate tests: static, host-side checks over generated scene code."""

from bayan.pipeline.preflight import (
    contains_arabic_script,
    contains_presentation_forms,
    gates_blocked,
    gates_to_json,
    run_gates,
)
from bayan.templates.catalogue import get_template_catalogue, read_fixture_code

FAILED = "failed"
PASSED = "passed"


def _failures(results, gate):
    return [result for result in results if result.gate == gate and result.status == FAILED]


def test_raw_text_with_arabic_is_rejected():
    code = (
        "from manim import *\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        Text("مرحبا بكم")\n'
    )

    results = run_gates(code)

    arabic_failures = _failures(results, "arabic")
    assert arabic_failures
    assert arabic_failures[0].line == 5
    assert "ArabicText" in arabic_failures[0].suggestion
    assert "مرحبا بكم" in arabic_failures[0].excerpt
    assert gates_blocked(results)


def test_banned_imports_are_rejected_by_module_name():
    scenes = {
        "subprocess import": "import subprocess\n",
        "socket import": "import socket\n",
        "dotted urllib import": "import urllib.request\n",
    }
    for label, code in scenes.items():
        results = run_gates(code)
        assert _failures(results, "imports"), label
        assert gates_blocked(results)


def test_banned_constructs_are_rejected_by_gate_three():
    scenes = {
        "os.system call": "import os\n\nos.system('ls')\n",
        "os.popen call": "import os\n\nos.popen('ls')\n",
        "eval call": "eval('1 + 1')\n",
        "exec call": "exec('x = 1')\n",
        "open call": "open('scene.py')\n",
        "dotted subprocess call": "subprocess.run(['ls'])\n",
    }
    for label, code in scenes.items():
        results = run_gates(code)
        failures = _failures(results, "bans")
        assert failures, label
        assert all(result.suggestion and result.excerpt for result in failures)


def test_bypass_call_pattern_is_caught_by_literal_backstop():
    """The literal backstop flags call-shaped exec/eval text, even in strings.

    Deliberately conservative: a generated scene has no business containing
    call-shaped execution text at all.
    """
    code = 'from manim import *\n\nnote = "never exec(something) in scenes"\n'

    results = run_gates(code)

    assert any("exec" in (result.excerpt or "") for result in _failures(results, "bans"))


def test_prose_mentioning_banned_modules_is_not_flagged():
    """English prose and Arabic lesson text may name banned modules freely."""
    code = (
        "from manim import *\n"
        "from bayan.utils.arabic_helper import ArabicText\n"
        "# This scene shows a socket and a plug, no networking involved.\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        message = ArabicText("رابط المقبس socket")\n'
    )

    results = run_gates(code)

    assert not _failures(results, "bans")


def test_reversal_and_presentation_forms_are_rejected():
    reversal = (
        "from manim import *\n"
        "from bayan.utils.arabic_helper import ArabicText\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        message = ArabicText("مرحبا")\n'
        "        self.play(Write(message[::-1]))\n"
    )
    results = run_gates(reversal)
    reversal_failures = _failures(results, "arabic")
    assert any("rtl_glyphs" in (result.suggestion or "") for result in reversal_failures)

    pre_shaped = (
        "from manim import *\n"
        "from bayan.utils.arabic_helper import ArabicText\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        ArabicText("\ufee3\ufea9\ufe8d\ufef4")\n'
    )
    results = run_gates(pre_shaped)
    assert any(
        "presentation forms" in (result.suggestion or "") for result in _failures(results, "arabic")
    )


def test_arabic_inside_comments_is_rejected():
    code = (
        "from manim import *\n"
        "\n"
        "# نص في تعليق\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        pass\n"
    )

    results = run_gates(code)

    comment_failures = _failures(results, "arabic")
    assert comment_failures
    assert comment_failures[0].line == 3
    assert "string literal" in (comment_failures[0].suggestion or "")


def test_syntax_errors_fail_with_evidence_and_skip_other_gates():
    results = run_gates("def broken(:\n")

    assert len(results) == 1
    assert results[0].gate == "syntax"
    assert results[0].line == 1
    assert results[0].suggestion
    assert gates_blocked(results)


def test_relative_imports_are_rejected():
    results = run_gates("from .helpers import thing\n")

    assert _failures(results, "imports")
    assert any("Relative imports" in (result.suggestion or "") for result in results)


def test_clean_catalogue_fixtures_pass_all_gates():
    for slug in sorted(get_template_catalogue()):
        results = run_gates(read_fixture_code(slug))
        assert not gates_blocked(results), (slug, results)


def test_gate_results_serialize_for_the_repair_classifier():
    import json

    results = run_gates("open('x')\n")
    payload = json.loads(gates_to_json(results))

    assert payload
    for entry in payload:
        assert {"gate", "status", "line", "excerpt", "suggestion"} <= set(entry)


def test_arabic_predicates_are_range_exact():
    assert contains_arabic_script("مرحبا")
    assert not contains_arabic_script("hello")
    assert contains_presentation_forms("\ufee3\ufea9")
    assert not contains_presentation_forms("مرحبا")
