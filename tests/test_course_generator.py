"""Unit tests for the course generator's pure helpers.

``course/generator.py`` is a standalone stdlib script (not a package), so it is
loaded by path. These tests cover the quiz/gate schema validators — the same
code the CI ``course-gate`` job enforces — and the markdown/JSON embedding
helpers. Full-site validation remains the generator's own ``--check`` run.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_GEN_PATH = Path(__file__).resolve().parents[1] / "course" / "generator.py"
_spec = importlib.util.spec_from_file_location("course_generator", _GEN_PATH)
assert _spec is not None and _spec.loader is not None
gen: ModuleType = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _item(**overrides: Any) -> dict:
    """A minimal valid single-choice item; overrides tweak one field at a time."""
    base = {
        "id": "q1",
        "type": "single-choice",
        "bloom": "Remember",
        "prompt": "p",
        "options": ["a", "b"],
        "answer": 0,
        "explanation": "e",
        "ref": "mobjects.md",
    }
    base.update(overrides)
    return base


VALID_BY_TYPE = {
    "single-choice": {"options": ["a", "b"], "answer": 1},
    "multi-select": {"type": "multi-select", "options": ["a", "b"], "answer": [0]},
    "fill-blank": {"type": "fill-blank", "answer": "next_to"},
    "predict-output": {
        "type": "predict-output",
        "code": "x = 1",
        "answer": {"regex": r"\d+"},
    },
    "bug-spot": {
        "type": "bug-spot",
        "code": "x = 1",
        "brokenLine": 1,
        "options": ["fix a", "fix b"],
        "answer": 0,
    },
    "code-ordering": {
        "type": "code-ordering",
        "options": ["first", "second"],
        "answer": [0, 1],
    },
    "create": {
        "type": "create",
        "modelAnswer": "code",
        "rubric": [{"criterion": "c", "weight": 100}],
    },
}


class TestValidateItem:
    @pytest.mark.parametrize("extra", VALID_BY_TYPE.values(), ids=VALID_BY_TYPE)
    def test_every_item_type_has_a_valid_shape(self, extra: dict) -> None:
        assert gen.validate_item(_item(**extra)) == []

    @pytest.mark.parametrize(
        "bad",
        [
            _item(type="nonsense"),
            _item(bloom="Memorize"),
            _item(prompt=""),
            _item(ref=None),
            _item(answer=5),  # index out of range
            _item(answer="0"),  # not an int
            _item(options=["only one"]),
        ],
        ids=[
            "bad-type",
            "bad-bloom",
            "empty-prompt",
            "null-ref",
            "answer-index-out-of-range",
            "answer-not-int",
            "too-few-options",
        ],
    )
    def test_invalid_items_are_rejected(self, bad: dict) -> None:
        assert gen.validate_item(bad) != []

    def test_duplicate_keys_are_not_required_unique_by_item(self) -> None:
        """Item ids only need uniqueness within an assessment, not per item."""
        assert gen.validate_item(_item()) == []


class TestRegexAnswers:
    def test_invalid_regex_is_rejected(self) -> None:
        errs = gen.validate_item(_item(type="fill-blank", answer={"regex": "(unclosed"}))
        assert any("invalid regex" in e for e in errs)

    def test_non_string_regex_is_rejected(self) -> None:
        errs = gen.validate_item(_item(type="fill-blank", answer={"regex": 3}))
        assert any("must be a string" in e for e in errs)

    def test_multiselect_answer_indexes_must_be_in_range(self) -> None:
        ok = gen.validate_item(_item(type="multi-select", options=["a", "b"], answer=[0, 1]))
        assert ok == []

        out_of_range = gen.validate_item(
            _item(type="multi-select", options=["a", "b"], answer=[0, 5])
        )
        assert any("int indexes into options" in e for e in out_of_range)

        string_el = gen.validate_item(_item(type="multi-select", options=["a", "b"], answer=["0"]))
        assert any("int indexes into options" in e for e in string_el)

    def test_valid_regex_is_accepted(self) -> None:
        assert gen.validate_item(_item(type="fill-blank", answer={"regex": r"v\d+\.\d+"})) == []

    def test_predict_output_regex_is_checked_too(self) -> None:
        errs = gen.validate_item(
            _item(type="predict-output", code="x = 1", answer={"regex": "[bad"})
        )
        assert any("invalid regex" in e for e in errs)


def _quiz(items: list) -> dict:
    return {"id": "quiz", "title": "t", "items": items}


class TestValidateAssessment:
    def test_quiz_needs_six_items_and_full_bloom_ladder(self) -> None:
        blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        items = [
            _item(id=f"q{i}", bloom=b, **VALID_BY_TYPE["single-choice"])
            for i, b in enumerate(blooms, 1)
        ]
        assert gen.validate_assessment(_quiz(items), "where", "quiz") == []

        short = gen.validate_assessment(_quiz(items[:5]), "where", "quiz")
        assert any(">=6 items" in e for e in short)

        no_evaluate = [i for i in items if i["bloom"] != "Evaluate"]
        filler = _item(id="qx", bloom="Analyze", **VALID_BY_TYPE["single-choice"])
        ladder = gen.validate_assessment(_quiz(no_evaluate + [filler]), "where", "quiz")
        assert any("missing Bloom levels" in e for e in ladder)

    def test_duplicate_item_ids_are_rejected(self) -> None:
        blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        items = [_item(id="same", bloom=b, **VALID_BY_TYPE["single-choice"]) for b in blooms]
        dup = gen.validate_assessment(_quiz(items), "w", "quiz")
        assert any("duplicate item id" in e for e in dup)

    def test_gate_rejects_create_items_and_bad_threshold(self) -> None:
        blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        scored = [
            _item(id=f"g{i}", bloom=blooms[i % 6], **VALID_BY_TYPE["single-choice"])
            for i in range(15)
        ]
        gate15 = {"id": "g", "title": "t", "items": scored, "threshold": 0.85}
        assert gen.validate_assessment(gate15, "w", "gate") == []

        with_create = scored + [
            _item(
                id="gx",
                type="create",
                bloom="Create",
                modelAnswer="m",
                rubric=[{"criterion": "c", "weight": 1}],
            )
        ]
        gate_create = gen.validate_assessment(
            {"id": "g", "title": "t", "items": with_create}, "w", "gate"
        )
        assert any("'create'" in e for e in gate_create)

        assert any(
            "threshold" in e
            for e in gen.validate_assessment(
                {"id": "g", "title": "t", "items": scored, "threshold": 1.5}, "w", "gate"
            )
        )


class TestMarkdown:
    def test_headings_lists_and_fences(self) -> None:
        html = gen.md_to_html("# Title\n\n- one\n- two\n\n```py\nx = 1\n```")
        assert "<h1>Title</h1>" in html
        assert "<ul>" in html and "<li>one</li>" in html
        assert '<pre class="code"><code class="language-py">x = 1</code></pre>' in html

    def test_escaping_and_code_spans(self) -> None:
        html = gen.md_to_html("a <b> & `x < 1`")
        assert "a &lt;b&gt; &amp;" in html
        assert "<code>x &lt; 1</code>" in html

    def test_tables_render_as_kvtable(self) -> None:
        html = gen.md_to_html("| k | v |\n|---|---|\n| a | b |")
        assert '<table class="kvtable">' in html
        assert "<th>k</th>" in html and "<td>b</td>" in html


class TestJsonForScript:
    def test_closes_are_escaped_and_round_trip(self) -> None:
        embedded = gen.json_for_script({"answer": "</script>"})
        assert "</" not in embedded
        assert json.loads(embedded) == {"answer": "</script>"}

    def test_plain_data_is_unchanged(self) -> None:
        assert gen.json_for_script({"a": 1}) == '{"a": 1}'


class TestEscapingAndScriptOrder:
    def test_esc_neutralizes_attribute_breakouts(self) -> None:
        out = gen.esc("a\"b'c<d>&e")
        assert '"' not in out and "'" not in out and "<" not in out
        assert out == "a&quot;b&#39;c&lt;d&gt;&amp;e"

    def test_page_puts_extra_js_after_quiz_js(self) -> None:
        # The index dashboard needs window.ManimProgress (defined by quiz.js);
        # if its script lands earlier, the dashboard silently never renders.
        html = gen.page("t", "<p>body</p>", "assets/", "", extra_js="<script>INDEXJS</script>")
        assert html.index("quiz.js") < html.index("INDEXJS")
