"""PlannerService tests: Arabic prompt in, validated LessonPlan and run record out."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bayan.generator.llm_client import LLMClient, LLMResponseFormatError, LLMUsage
from bayan.pipeline.models import PlanAttemptEvidence
from bayan.pipeline.planner import PlannerService, PlanningError
from bayan.pipeline.pricing import PRICE_TABLE_USD_PER_1M, estimate_cost_usd
from bayan.planner.provider import FakeProvider, LLMPlanProvider

ARABIC_PROMPT = "شرح القسمة على الأعداد ذات المنزلة الواحدة"
DEFAULT_PROFILE = "msa-western"


def _has_arabic_script(text: str) -> bool:
    return any("\u0600" <= character <= "\u06ff" for character in text)


def _mocked_client(mock_openai_class: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    return mock_client


def _mock_response(content: str, usage: tuple[int, int, int] | None = None) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    if usage is not None:
        response.usage.prompt_tokens = usage[0]
        response.usage.completion_tokens = usage[1]
        response.usage.total_tokens = usage[2]
    return response


def _read_record(run_dir: Path) -> dict[str, object]:
    record_path = run_dir / "records" / "planning.json"
    return json.loads(record_path.read_text(encoding="utf-8"))


class _ScriptedProvider:
    """Deterministic provider replaying queued outcomes and counting calls."""

    def __init__(self, outcomes: list[PlanAttemptEvidence | Exception]) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    def generate_lesson_plan(self, prompt: str, profile: str) -> PlanAttemptEvidence:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# -------------------------------------------------------------------------
# 1. Deterministic happy path (FakeProvider)
# -------------------------------------------------------------------------


def test_fake_provider_yields_valid_typed_plan(tmp_path):
    service = PlannerService(provider=FakeProvider(), run_dir=tmp_path)

    plan = service.plan(ARABIC_PROMPT)

    assert plan.topic
    assert plan.language == "ar"
    assert plan.profile == DEFAULT_PROFILE
    assert len(plan.beats) >= 2
    for beat in plan.beats:
        assert beat.on_screen_text
        assert _has_arabic_script(beat.on_screen_text)
        assert beat.insight_move
        assert beat.numbers

    # Identical prompts must produce identical plans (golden-set dependency).
    again = PlannerService(provider=FakeProvider(), run_dir=tmp_path / "second").plan(ARABIC_PROMPT)
    assert again.model_dump() == plan.model_dump()

    plan_json = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    assert plan_json["topic"] == plan.topic
    assert len(plan_json["beats"]) == len(plan.beats)

    record = _read_record(tmp_path)
    assert record["status"] == "completed"
    assert record["prompt"] == ARABIC_PROMPT
    assert record["provider_fingerprint"]
    assert record["max_attempts"] == 3
    attempt = record["attempts"][0]
    assert attempt["model"] == "fake-model-v1"
    assert attempt["total_tokens"] > 0
    assert "cost_estimate_usd" in attempt
    assert attempt["raw_response"]


# -------------------------------------------------------------------------
# 2. Bounded regeneration (3 total provider calls)
# -------------------------------------------------------------------------


def test_invalid_plans_are_retried_within_three_total_calls(tmp_path):
    good = FakeProvider().generate_lesson_plan(ARABIC_PROMPT, DEFAULT_PROFILE)
    provider = _ScriptedProvider(
        [
            LLMResponseFormatError("reply was not valid JSON"),
            LLMResponseFormatError("reply did not match the LessonPlan schema"),
            good,
        ]
    )
    service = PlannerService(provider=provider, run_dir=tmp_path)

    plan = service.plan(ARABIC_PROMPT)

    assert provider.calls == 3
    assert plan.topic
    record = _read_record(tmp_path)
    assert record["status"] == "completed"
    assert len(record["attempts"]) == 3
    assert "not valid JSON" in str(record["attempts"][0]["error"])
    assert record["attempts"][0]["model"] is None
    assert record["attempts"][2]["raw_response"]


def test_never_valid_provider_writes_failure_record_and_raises(tmp_path):
    provider = _ScriptedProvider([LLMResponseFormatError("not json")] * 5)
    service = PlannerService(provider=provider, run_dir=tmp_path)

    with pytest.raises(PlanningError) as exc_info:
        service.plan(ARABIC_PROMPT)

    assert provider.calls == 3
    assert "not json" in str(exc_info.value)
    assert "planning.json" in str(exc_info.value)
    record = _read_record(tmp_path)
    assert record["status"] == "failed"
    assert len(record["attempts"]) == 3
    assert "failed after 3 attempts" in str(record["failure"])
    assert not (tmp_path / "plan.json").exists()


def test_empty_prompt_fails_without_provider_call(tmp_path):
    provider = _ScriptedProvider([])
    service = PlannerService(provider=provider, run_dir=tmp_path)

    with pytest.raises(PlanningError):
        service.plan("   ")

    assert provider.calls == 0
    record = _read_record(tmp_path)
    assert record["status"] == "failed"
    assert record["attempts"] == []


# -------------------------------------------------------------------------
# 3. Real provider adapter over the hardened client
# -------------------------------------------------------------------------


@patch("bayan.generator.llm_client.OpenAI")
def test_llm_plan_provider_builds_evidence_from_structured_mode(mock_openai_class):
    mock_client = _mocked_client(mock_openai_class)
    payload = {
        "topic": "قسمة الأعداد",
        "language": "ar",
        "profile": DEFAULT_PROFILE,
        "beats": [
            {
                "title": "الخطوة الأولى",
                "on_screen_text": "نقسم 24 على 2",
                "insight_move": "reveal",
                "numbers": [24, 2],
            }
        ],
    }
    mock_client.chat.completions.create.return_value = _mock_response(
        json.dumps(payload, ensure_ascii=False), usage=(20, 30, 50)
    )

    client = LLMClient(api_key="fake-api-key")
    provider = LLMPlanProvider(client=client)

    evidence = provider.generate_lesson_plan(ARABIC_PROMPT, DEFAULT_PROFILE)

    assert evidence.plan.topic == "قسمة الأعداد"
    assert evidence.plan.beats[0].numbers == [24.0, 2.0]
    assert evidence.usage == LLMUsage(prompt_tokens=20, completion_tokens=30, total_tokens=50)
    assert evidence.model == client.model
    assert evidence.fingerprint
    assert evidence.raw_response

    called_kwargs = mock_client.chat.completions.create.call_args[1]
    response_format = called_kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "LessonPlan"
    assert called_kwargs["messages"][0]["role"] == "system"


@patch("bayan.generator.llm_client.OpenAI")
def test_llm_plan_provider_surfaces_invalid_output_as_provider_error(mock_openai_class):
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response("definitely not json")

    provider = LLMPlanProvider(client=LLMClient(api_key="fake-api-key"))

    with pytest.raises(LLMResponseFormatError):
        provider.generate_lesson_plan(ARABIC_PROMPT, DEFAULT_PROFILE)


def test_client_captures_last_raw_content(tmp_path):
    """The raw reply is available for run records without changing return types."""
    provider = FakeProvider()
    service = PlannerService(provider=provider, run_dir=tmp_path)
    service.plan(ARABIC_PROMPT)

    # The service records the raw response for every accepted attempt.
    record = _read_record(tmp_path)
    assert record["attempts"][0]["raw_response"].startswith("{")


# -------------------------------------------------------------------------
# 4. Cost estimation (pure function)
# -------------------------------------------------------------------------


def test_cost_estimate_uses_price_table():
    usage = LLMUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000, total_tokens=2_000_000)
    input_price, output_price = PRICE_TABLE_USD_PER_1M["gpt-4o-mini"]

    assert estimate_cost_usd("gpt-4o-mini", usage) == pytest.approx(input_price + output_price)
    assert estimate_cost_usd("model-without-published-pricing", usage) == 0.0
    assert estimate_cost_usd("gpt-4o-mini", None) == 0.0


def test_recorded_cost_comes_from_provider_usage(tmp_path):
    provider = _ScriptedProvider(
        [FakeProvider().generate_lesson_plan(ARABIC_PROMPT, DEFAULT_PROFILE)]
    )
    service = PlannerService(provider=provider, run_dir=tmp_path)

    service.plan(ARABIC_PROMPT)

    attempt = _read_record(tmp_path)["attempts"][0]
    usage = LLMUsage(
        prompt_tokens=int(attempt["prompt_tokens"]),
        completion_tokens=int(attempt["completion_tokens"]),
        total_tokens=int(attempt["total_tokens"]),
    )
    assert attempt["cost_estimate_usd"] == pytest.approx(
        round(estimate_cost_usd("fake-model-v1", usage), 6)
    )
