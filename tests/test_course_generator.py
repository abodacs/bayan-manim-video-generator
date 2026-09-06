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
            _item(id='x" onmouseover=1'),  # unsafe id charset
        ],
        ids=[
            "bad-type",
            "bad-bloom",
            "empty-prompt",
            "null-ref",
            "answer-index-out-of-range",
            "answer-not-int",
            "too-few-options",
            "unsafe-id-charset",
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
        assert gen.validate_assessment(_quiz(items), "where", "quiz", gen.Report()) == []

        short = gen.validate_assessment(_quiz(items[:5]), "where", "quiz", gen.Report())
        assert any(">=6 items" in e for e in short)

        no_evaluate = [i for i in items if i["bloom"] != "Evaluate"]
        filler = _item(id="qx", bloom="Analyze", **VALID_BY_TYPE["single-choice"])
        ladder = gen.validate_assessment(
            _quiz(no_evaluate + [filler]), "where", "quiz", gen.Report()
        )
        assert any("missing Bloom levels" in e for e in ladder)

    def test_duplicate_item_ids_are_rejected(self) -> None:
        blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        items = [_item(id="same", bloom=b, **VALID_BY_TYPE["single-choice"]) for b in blooms]
        dup = gen.validate_assessment(_quiz(items), "w", "quiz", gen.Report())
        assert any("duplicate item id" in e for e in dup)

    def test_gate_rejects_create_items_and_bad_threshold(self) -> None:
        blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        scored = [
            _item(id=f"g{i}", bloom=blooms[i % 6], **VALID_BY_TYPE["single-choice"])
            for i in range(15)
        ]
        gate15 = {"id": "g", "title": "t", "items": scored, "threshold": 0.85}
        assert gen.validate_assessment(gate15, "w", "gate", gen.Report()) == []

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
            {"id": "g", "title": "t", "items": with_create}, "w", "gate", gen.Report()
        )
        assert any("'create'" in e for e in gate_create)

        assert any(
            "threshold" in e
            for e in gen.validate_assessment(
                {"id": "g", "title": "t", "items": scored, "threshold": 1.5},
                "w",
                "gate",
                gen.Report(),
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


def _lesson_dict(tmp: Any, lid: str, tier: int, prereqs: list) -> dict:
    """Minimal lesson shape accepted by render_lesson."""
    ldir = tmp / "lessons" / gen.TIER_DIR[tier] / lid
    ldir.mkdir(parents=True, exist_ok=True)
    return {
        "id": lid,
        "tier": tier,
        "tierName": gen.TIER_NAME[tier],
        "slug": lid,
        "title": f"T {lid}",
        "status": "reviewed",
        "objective": "o",
        "misconception": "m",
        "prereqs": prereqs,
        "ref": "mobjects.md",
        "body_html": "<p>b</p>",
        "code_files": {},
        "quiz": None,
        "url": f"lessons/{gen.TIER_DIR[tier]}/{lid}/index.html",
        "dir": str(ldir),
    }


class TestPrereqLinks:
    def test_cross_tier_prereq_resolves_to_its_own_tier(self, tmp_path: Any) -> None:
        # A tier-2 lesson prereqing a tier-1 lesson must not emit "../<id>/",
        # which would resolve inside the tier-2 directory and 404.
        by_id = {"01-first-scene": _lesson_dict(tmp_path, "01-first-scene", 1, [])}
        lesson = _lesson_dict(tmp_path, "05-next-level", 2, ["01-first-scene"])
        out = gen.render_lesson(lesson, by_id)
        html = Path(out).read_text(encoding="utf-8")
        assert 'href="../../beginner/01-first-scene/index.html"' in html
        assert 'href="../01-first-scene/index.html"' not in html

    def test_same_tier_prereq_href_unchanged(self, tmp_path: Any) -> None:
        by_id = {
            "03-animations-rate-functions": _lesson_dict(
                tmp_path, "03-animations-rate-functions", 1, []
            )
        }
        lesson = _lesson_dict(tmp_path, "04-scene-planning", 1, ["03-animations-rate-functions"])
        html = Path(gen.render_lesson(lesson, by_id)).read_text(encoding="utf-8")
        assert 'href="../03-animations-rate-functions/index.html"' in html


class TestLessonDirName:
    def test_unsafe_dir_name_is_rejected(self, tmp_path: Any) -> None:
        bad = tmp_path / 'x" onmouseover=1'
        bad.mkdir()
        (bad / "status.json").write_text(json.dumps({"status": "reviewed"}), encoding="utf-8")
        report = gen.Report()
        gen.read_lesson(1, str(bad), report)
        assert any("invalid lesson dir name" in e for e in report.errors)


class TestGateAndCapstoneRendering:
    """The gate/capstone renderers had zero coverage — verify they emit pages."""

    def _gate(self) -> dict:
        blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        items = [
            {
                "id": f"g{i}",
                "type": "single-choice",
                "bloom": blooms[i % 6],
                "prompt": "p",
                "options": ["a", "b"],
                "answer": 0,
                "explanation": "e",
                "ref": "mobjects.md",
            }
            for i in range(15)
        ]
        return {
            "kind": "gate",
            "id": "beginner-gate",
            "tier": 1,
            "title": "Beginner Gate",
            "items": items,
            "threshold": 0.85,
        }

    def test_render_gate_emits_parseable_page(self, tmp_path: Any, monkeypatch: Any) -> None:
        monkeypatch.setattr(gen, "HERE", str(tmp_path))
        out = gen.render_gate(self._gate(), 1)
        html = Path(out).read_text(encoding="utf-8")
        assert html.startswith("<!doctype html>")
        assert "Beginner Tier Gate" in html
        block = html.split('id="exam-data">', 1)[1].split("</script>", 1)[0]
        data = json.loads(block.replace("\\/", "/"))
        assert len(data["items"]) == 15

    def test_render_capstone_emits_parseable_page(self, tmp_path: Any) -> None:
        cdir = tmp_path / "capstone" / "1"
        cdir.mkdir(parents=True)
        capstone = {
            "tier": 1,
            "brief_html": "<p>brief</p>",
            "rubric_html": "<p>rubric</p>",
            "solution": {"solution.py": "from manim import *"},
            "url": "capstone/1/index.html",
            "dir": str(cdir),
        }
        out = gen.render_capstone(capstone, 1)
        html = Path(out).read_text(encoding="utf-8")
        assert html.startswith("<!doctype html>")
        assert "Beginner Capstone" in html
        assert "solution.py" in html


def _write_lesson_dir(root: Any, lid: str, prereqs: list) -> None:
    """A complete, gate-valid lesson: status.json + 6-item Bloom quiz."""
    ldir = root / "lessons" / "beginner" / lid
    (ldir / "assessment").mkdir(parents=True)
    (ldir / "status.json").write_text(
        json.dumps(
            {
                "id": lid,
                "tier": 1,
                "slug": lid,
                "status": "reviewed",
                "title": f"T {lid}",
                "objective": "o",
                "misconception": "m",
                "prereqs": prereqs,
                "ref": "mobjects.md",
            }
        ),
        encoding="utf-8",
    )
    blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    quiz = {
        "kind": "quiz",
        "id": lid,
        "tier": 1,
        "title": f"Quiz {lid}",
        "items": [
            {
                "id": f"q{i}",
                "type": "single-choice",
                "bloom": b,
                "prompt": "p",
                "options": ["a", "b"],
                "answer": 0,
                "explanation": "e",
                "ref": "mobjects.md",
            }
            for i, b in enumerate(blooms, 1)
        ],
    }
    (ldir / "assessment" / "quiz.json").write_text(json.dumps(quiz), encoding="utf-8")


class TestFirstBuild:
    def test_new_prereq_pair_builds_from_scratch(self, tmp_path: Any, monkeypatch: Any) -> None:
        # Regression: the prereq link check once required the TARGET'S
        # GENERATED PAGE to exist — impossible on a first build that adds a
        # lesson and its prereq together, deadlocking before any render.
        import sys as _sys

        monkeypatch.setattr(gen, "HERE", str(tmp_path))
        _write_lesson_dir(tmp_path, "01-a", [])
        _write_lesson_dir(tmp_path, "02-b", ["01-a"])
        monkeypatch.setattr(_sys, "argv", ["generator.py"])
        assert gen.main() == 0
        assert (tmp_path / "lessons/beginner/02-b/index.html").exists()
