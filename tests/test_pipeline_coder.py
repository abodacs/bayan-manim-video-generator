"""CoderService tests: validated LessonPlan in, Manim scene text out."""

import ast
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from bayan.generator.llm_client import LLMClient, LLMProviderError, LLMUsage
from bayan.pipeline.coder import (
    CoderService,
    CodingError,
    LLMCoderProvider,
    build_coder_prompt,
    select_few_shot_fixtures,
)
from bayan.pipeline.models import CodeAttemptEvidence, LessonPlan
from bayan.planner.provider import FakeProvider
from bayan.templates.catalogue import read_fixture_code
from tests.helpers import mock_chat_response as _mock_response
from tests.helpers import mocked_client as _mocked_client

ARABIC_PROMPT = "شرح القسمة على الأعداد ذات المنزلة الواحدة"
DEFAULT_PROFILE = "msa-western"

# The only ad-hoc-reversal literal allowed in this file: the negative fixture.
BANNED_SLICING_FIXTURE = "self.play(Write(text[::-1]))"


def _has_arabic_script(text: str) -> bool:
    return any("\u0600" <= character <= "\u06ff" for character in text)


def _plan() -> LessonPlan:
    return FakeProvider().generate_lesson_plan(ARABIC_PROMPT, DEFAULT_PROFILE).plan


def _read_record(run_dir: Path) -> dict[str, object]:
    record_path = run_dir / "records" / "coding.json"
    return json.loads(record_path.read_text(encoding="utf-8"))


class _ScriptedCoder:
    """Deterministic coder replaying queued code texts and counting calls."""

    def __init__(self, outcomes: list[str | Exception]) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    def generate_scene_code(
        self, *, plan: LessonPlan, system_prompt: str, user_prompt: str
    ) -> CodeAttemptEvidence:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return CodeAttemptEvidence(
            code=outcome,
            raw_response=outcome,
            fingerprint="scripted-fingerprint",
            model="scripted-model",
            usage=LLMUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )


# -------------------------------------------------------------------------
# 1. Deterministic happy path (FakeProvider)
# -------------------------------------------------------------------------


def test_fake_coder_output_parses_and_uses_helper(tmp_path):
    service = CoderService(provider=FakeProvider(), run_dir=tmp_path)

    code = service.code(_plan())

    ast.parse(code)
    assert "ArabicText(" in code
    assert "class GeneratedScene(Scene)" in code
    for match in re.finditer(r'\bText\("([^"]*)"', code):
        assert not _has_arabic_script(match.group(1))
    # The banned slicing fixture above is the file's only ad-hoc-reversal literal.
    assert BANNED_SLICING_FIXTURE not in code
    assert (tmp_path / "scene.py").read_text(encoding="utf-8") == code + "\n"


def test_coder_record_contains_prompt_model_and_usage(tmp_path):
    service = CoderService(provider=FakeProvider(), run_dir=tmp_path)

    service.code(_plan())

    record = _read_record(tmp_path)
    assert record["status"] == "completed"
    assert record["prompt"]
    assert record["system_prompt"]
    assert record["provider_fingerprint"]
    assert record["scene"] == "scene.py"
    attempt = record["attempts"][0]
    assert attempt["model"] == "fake-model-v1"
    assert attempt["total_tokens"] > 0
    assert attempt["cost_estimate_usd"] == 0.0
    assert attempt["raw_response"]


# -------------------------------------------------------------------------
# 2. Prompt grounding (plan beats verbatim + few-shot catalogue examples)
# -------------------------------------------------------------------------


def test_prompt_embeds_plan_beats_and_few_shot_examples():
    plan = _plan()
    slugs = select_few_shot_fixtures()
    assert len(slugs) == 2
    examples = [read_fixture_code(slug) for slug in slugs]

    system, user = build_coder_prompt(plan, DEFAULT_PROFILE, examples)

    for beat in plan.beats:
        assert beat.on_screen_text in user
    assert "from manim import *" in system
    assert "ArabicText" in system
    assert "rtl_glyphs" in system
    assert "GeneratedScene" in system
    assert "self.play" in system
    assert examples[0] in user
    assert examples[1] in user
    assert "::-1" not in system
    assert "::-1" not in user


def test_few_shot_selection_is_deterministic():
    assert select_few_shot_fixtures() == select_few_shot_fixtures()


# -------------------------------------------------------------------------
# 3. Typed failures (empty output, unparsable code, provider failure)
# -------------------------------------------------------------------------


def test_empty_output_refused_with_typed_error(tmp_path):
    provider = _ScriptedCoder(["   "])
    service = CoderService(provider=provider, run_dir=tmp_path)

    with pytest.raises(CodingError) as exc_info:
        service.code(_plan())

    assert "empty" in str(exc_info.value)
    assert "coding.json" in str(exc_info.value)
    assert exc_info.value.record_path == tmp_path / "records" / "coding.json"
    record = _read_record(tmp_path)
    assert record["status"] == "failed"
    assert not (tmp_path / "scene.py").exists()


def test_unparsable_code_refused_with_typed_error(tmp_path):
    provider = _ScriptedCoder(["def broken(:"])
    service = CoderService(provider=provider, run_dir=tmp_path)

    with pytest.raises(CodingError) as exc_info:
        service.code(_plan())

    assert "does not parse" in str(exc_info.value)
    record = _read_record(tmp_path)
    assert record["status"] == "failed"
    assert not (tmp_path / "scene.py").exists()


def test_provider_failure_writes_failure_record(tmp_path):
    provider = _ScriptedCoder([LLMProviderError("connection reset")])
    service = CoderService(provider=provider, run_dir=tmp_path)

    with pytest.raises(CodingError):
        service.code(_plan())

    record = _read_record(tmp_path)
    assert record["status"] == "failed"
    assert "connection reset" in str(record["attempts"][0]["error"])


def test_markdown_fences_are_stripped_by_the_service(tmp_path):
    fenced = "```python\nfrom manim import *\n```"
    provider = _ScriptedCoder([fenced])
    service = CoderService(provider=provider, run_dir=tmp_path)

    code = service.code(_plan())

    assert code == "from manim import *"


# -------------------------------------------------------------------------
# 4. Real provider adapter over the hardened client
# -------------------------------------------------------------------------


@patch("bayan.generator.llm_client.OpenAI")
def test_llm_coder_provider_builds_evidence_from_client(mock_openai_class):
    mock_client = _mocked_client(mock_openai_class)
    scene = "from manim import *\n"
    mock_client.chat.completions.create.return_value = _mock_response(
        f"```python\n{scene}```", usage=(15, 25, 40)
    )

    client = LLMClient(api_key="fake-api-key")

    provider = LLMCoderProvider(client=client)
    evidence = provider.generate_scene_code(
        plan=_plan(), system_prompt="system", user_prompt="user"
    )

    assert evidence.code == scene.strip()
    assert evidence.raw_response
    assert evidence.usage == LLMUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)
    assert evidence.model == client.model
    assert evidence.fingerprint

    create_kwargs = mock_client.chat.completions.create.call_args[1]
    assert create_kwargs["messages"][0]["content"] == "system"
    assert create_kwargs["messages"][1]["content"] == "user"
