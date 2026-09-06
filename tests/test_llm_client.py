import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from bayan.generator.llm_client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LLMClient,
    LLMConfigError,
    LLMProviderError,
    LLMResponseFormatError,
    LLMUsage,
    clean_code_block,
)
from tests.helpers import mock_chat_response as _mock_response
from tests.helpers import mocked_client as _mocked_client

# -------------------------------------------------------------------------
# 1. Tests for the Code Cleaner Function (clean_code_block)
# -------------------------------------------------------------------------


def test_clean_code_with_markdown_wrapper():
    """Verify that pure code is extracted properly when enclosed in Markdown code blocks."""
    raw_response = (
        "```python\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass\n```"
    )
    expected_clean_code = "class GeneratedScene(Scene):\n    def construct(self):\n        pass"
    assert clean_code_block(raw_response) == expected_clean_code


def test_clean_code_without_markdown_wrapper():
    """Verify that raw code is returned as-is if no Markdown wrappers are present."""
    raw_response = "class GeneratedScene(Scene):\n    pass"
    assert clean_code_block(raw_response) == raw_response.strip()


# -------------------------------------------------------------------------
# 2. Unit Tests with API Mocking
# -------------------------------------------------------------------------


@patch("bayan.generator.llm_client.OpenAI")
def test_generate_manim_code_success(mock_openai_class):
    """Verify that correct API parameters are sent,
    and the response is received and cleaned successfully."""
    # Initialize Mock instance for OpenAI Client
    mock_client = _mocked_client(mock_openai_class)

    # Mock response structure returned from OpenAI (choices[0].message.content)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="```python\n# Clean Code\n```"))]
    mock_client.chat.completions.create.return_value = mock_response

    # Execute method under test using dynamic configurations fallback
    client = LLMClient(api_key="fake-api-key", model="glm-5.2")
    result = client.generate_manim_code("Draw a red circle")

    # Assert code output is cleaned correctly
    assert result == "# Clean Code"

    # Assert API was called once with accurate arguments matching configured environment models
    mock_client.chat.completions.create.assert_called_once()
    called_kwargs = mock_client.chat.completions.create.call_args[1]

    assert called_kwargs["model"] == "glm-5.2"
    assert called_kwargs["temperature"] == 0.2
    assert called_kwargs["messages"][0]["role"] == "system"
    assert "Draw a red circle" in called_kwargs["messages"][1]["content"]


@patch("bayan.generator.llm_client.OpenAI")
def test_generate_manim_code_api_error_raises_provider_error(mock_openai_class):
    """Verify that API communication/authentication errors
    are wrapped and raised as typed provider errors (still RuntimeError)."""
    mock_client = _mocked_client(mock_openai_class)

    # Simulate an exception during API request
    mock_client.chat.completions.create.side_effect = Exception("Connection timeout")

    client = LLMClient(api_key="fake-api-key")

    with pytest.raises(LLMProviderError) as exc_info:
        client.generate_manim_code("Draw a square")

    assert isinstance(exc_info.value, RuntimeError)
    assert "Failed to communicate with LLM provider" in str(exc_info.value)


# =========================================================================
# 3. Configuration and Error Typing
# =========================================================================


class _Quote(BaseModel):
    """Tiny response model used to exercise the structured-output seam."""

    item: str
    price: int


@patch("bayan.generator.llm_client.OpenAI")
def test_missing_key_error_names_the_env_vars(mock_openai_class, monkeypatch):
    """Missing credentials fail offline with a typed, actionable config error."""
    monkeypatch.delenv("BAYAN_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMConfigError) as exc_info:
        LLMClient()

    message = str(exc_info.value)
    assert "BAYAN_API_KEY" in message
    assert "OPENAI_API_KEY" in message
    assert "BAYAN_BASE_URL" in message
    assert "BAYAN_LLM_MODEL" in message
    assert "README" in message
    # Fail fast must happen before any provider client is built.
    mock_openai_class.assert_not_called()


@patch("bayan.generator.llm_client.OpenAI")
def test_provider_error_never_contains_the_api_key(mock_openai_class):
    """Provider failures are typed and the key is scrubbed from the message."""
    secret = "sk-proj-super-secret-key-value"
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.side_effect = Exception(
        f"auth failed for key {secret} (HTTP 401)"
    )

    client = LLMClient(api_key=secret)

    with pytest.raises(LLMProviderError) as exc_info:
        client.generate_manim_code("Draw a square")

    message = str(exc_info.value)
    assert secret not in message
    assert "***" in message
    assert "Failed to communicate with LLM provider" in message


@patch("bayan.generator.llm_client.OpenAI")
def test_generate_code_result_carries_the_call_evidence(mock_openai_class):
    """Token usage rides on the returned result, not on mutable client state."""
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response(
        "```python\nx = 1\n```", usage=(9, 4, 13)
    )

    client = LLMClient(api_key="fake-api-key")
    result = client.generate_code(system_prompt="system", user_prompt="user")

    assert result.content == "x = 1"
    assert result.usage == LLMUsage(prompt_tokens=9, completion_tokens=4, total_tokens=13)
    assert result.model == client.model
    assert result.base_url == client.base_url


@patch("bayan.generator.llm_client.OpenAI")
def test_result_usage_is_none_when_provider_omits_usage(mock_openai_class):
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response("print(1)")

    client = LLMClient(api_key="fake-api-key")
    result = client.generate_code(system_prompt="system", user_prompt="user")

    assert result.usage is None


@patch("bayan.generator.llm_client.OpenAI")
def test_result_keeps_raw_and_cleaned_content_apart(mock_openai_class):
    """Run records need the raw reply; the coder needs the cleaned code."""
    raw = "```python\nx = 1\n```"
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response(raw)

    client = LLMClient(api_key="fake-api-key")
    result = client.generate_code(system_prompt="system", user_prompt="user")

    assert result.content == "x = 1"
    assert result.raw_content == raw


@patch("bayan.generator.llm_client.OpenAI")
def test_results_are_frozen_snapshots_immune_to_later_calls(mock_openai_class):
    """A second call can never rewrite the first call's evidence."""
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.side_effect = [
        _mock_response("x = 1", usage=(9, 4, 13)),
        _mock_response("y = 2", usage=(1, 1, 2)),
    ]

    client = LLMClient(api_key="fake-api-key")
    first = client.generate_code(system_prompt="system", user_prompt="first")
    second = client.generate_code(system_prompt="system", user_prompt="second")

    assert first.content == "x = 1"
    assert first.usage == LLMUsage(prompt_tokens=9, completion_tokens=4, total_tokens=13)
    assert second.content == "y = 2"
    assert second.usage == LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
    with pytest.raises(AttributeError):
        first.usage = None  # type: ignore[misc]


@patch("bayan.generator.llm_client.OpenAI")
def test_generate_code_returns_cleaned_code_with_caller_prompts(mock_openai_class):
    raw = "```python\nfrom manim import *\n```"
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response(raw, usage=(7, 3, 10))

    client = LLMClient(api_key="fake-api-key")

    result = client.generate_code(system_prompt="system rules", user_prompt="user plan")

    assert result.content == "from manim import *"
    assert result.raw_content == raw
    assert result.usage == LLMUsage(prompt_tokens=7, completion_tokens=3, total_tokens=10)

    create_kwargs = mock_client.chat.completions.create.call_args[1]
    assert create_kwargs["messages"][0]["content"] == "system rules"
    assert create_kwargs["messages"][1]["content"] == "user plan"


# =========================================================================
# 4. Structured Output Mode
# =========================================================================


@patch("bayan.generator.llm_client.OpenAI")
def test_structured_mode_returns_parsed_json_and_usage(mock_openai_class):
    """Structured mode sends the JSON schema and returns evidence plus the model."""
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response(
        '{"item": "dates", "price": 7}', usage=(11, 5, 16)
    )

    client = LLMClient(api_key="fake-api-key")
    result = client.generate_structured(
        system_prompt="Return JSON only.",
        user_prompt="What is the price of dates?",
        response_model=_Quote,
    )

    assert result.data == _Quote(item="dates", price=7)
    assert result.content == '{"item": "dates", "price": 7}'
    assert result.usage == LLMUsage(prompt_tokens=11, completion_tokens=5, total_tokens=16)

    called_kwargs = mock_client.chat.completions.create.call_args[1]
    response_format = called_kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    json_schema = response_format["json_schema"]
    assert json_schema["name"] == "_Quote"
    assert json_schema["schema"]["properties"]["item"]["type"] == "string"


@patch("bayan.generator.llm_client.OpenAI")
def test_structured_mode_accepts_markdown_fenced_json(mock_openai_class):
    """Providers that ignore response_format may wrap JSON in fences; still parsed."""
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response(
        '```json\n{"item": "milk", "price": 3}\n```'
    )

    client = LLMClient(api_key="fake-api-key")
    result = client.generate_structured(
        system_prompt="Return JSON only.",
        user_prompt="What is the price of milk?",
        response_model=_Quote,
    )

    assert result.data == _Quote(item="milk", price=3)


@patch("bayan.generator.llm_client.OpenAI")
def test_structured_mode_malformed_json_raises_typed_error_with_bounded_excerpt(
    mock_openai_class,
):
    """Non-JSON replies raise a typed error carrying a bounded raw excerpt."""
    mock_client = _mocked_client(mock_openai_class)
    reply_tail = "x" * 2_000
    mock_client.chat.completions.create.return_value = _mock_response(
        f"Sorry, I cannot help with that. {reply_tail}"
    )

    client = LLMClient(api_key="fake-api-key")

    with pytest.raises(LLMResponseFormatError) as exc_info:
        client.generate_structured(
            system_prompt="Return JSON only.",
            user_prompt="What is the price of dates?",
            response_model=_Quote,
        )

    message = str(exc_info.value)
    assert "Sorry, I cannot help with that." in message
    assert reply_tail not in message


@patch("bayan.generator.llm_client.OpenAI")
def test_structured_mode_schema_mismatch_raises_typed_error(mock_openai_class):
    """Replies that parse as JSON but violate the schema raise the same typed error."""
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response(
        '{"item": 3, "price": "not a number"}'
    )

    client = LLMClient(api_key="fake-api-key")

    with pytest.raises(LLMResponseFormatError) as exc_info:
        client.generate_structured(
            system_prompt="Return JSON only.",
            user_prompt="What is the price of dates?",
            response_model=_Quote,
        )

    assert "_Quote" in str(exc_info.value)


@patch("bayan.generator.llm_client.OpenAI")
def test_structured_mode_provider_error_redacts_key_and_suppresses_cause(mock_openai_class):
    secret = "sk-proj-super-secret-key-value"
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.side_effect = Exception(f"quota exhausted for key {secret}")

    client = LLMClient(api_key=secret)

    with pytest.raises(LLMProviderError) as exc_info:
        client.generate_structured(
            system_prompt="Return JSON only.",
            user_prompt="What is the price of dates?",
            response_model=_Quote,
        )

    assert secret not in str(exc_info.value)
    # Suppression is load-bearing: chained exceptions print verbatim.
    assert exc_info.value.__cause__ is None


@patch("bayan.generator.llm_client.OpenAI")
def test_structured_mode_reply_containing_the_key_is_redacted(mock_openai_class):
    """The redaction guarantee covers reply excerpts, not just call failures."""
    secret = "sk-proj-super-secret-key-value"
    mock_client = _mocked_client(mock_openai_class)
    mock_client.chat.completions.create.return_value = _mock_response(
        f"echo back {secret} and stop"
    )

    client = LLMClient(api_key=secret)

    with pytest.raises(LLMResponseFormatError) as exc_info:
        client.generate_structured(
            system_prompt="Return JSON only.",
            user_prompt="What is the price of dates?",
            response_model=_Quote,
        )

    assert secret not in str(exc_info.value)


# =========================================================================
# 5. Integration Test (opt-in via BAYAN_LIVE_LLM_CHECK=1)
# =========================================================================


def has_active_bayan_quota():
    """Live calls only run when explicitly requested, keeping the suite offline."""
    if os.getenv("BAYAN_LIVE_LLM_CHECK") != "1":
        return False
    api_key = os.getenv("BAYAN_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False
    try:
        from openai import OpenAI

        base_url = os.getenv("BAYAN_BASE_URL", DEFAULT_BASE_URL)
        model = os.getenv("BAYAN_LLM_MODEL", DEFAULT_MODEL)

        client = OpenAI(api_key=api_key, base_url=base_url)
        # Fast lightweight request to verify active balance/quota on target provider
        client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=1
        )
        return True
    except Exception:
        # Catch quota exhaustion or network error to safely skip integration tests deterministically
        return False


@pytest.mark.skipif(
    not has_active_bayan_quota(),
    reason="This integration test requires an active Bayan API provider key with sufficient quota.",
)
def test_integration_live_llm_call():
    """Live API integration test: validates actual endpoint
    connectivity and generated Python code syntax."""
    client = LLMClient()
    prompt = "Draw a blue circle that fades in"

    # Call live API
    generated_code = client.generate_manim_code(prompt)

    # 1. Assert response is a non-empty string
    assert isinstance(generated_code, str)
    assert len(generated_code) > 0

    # 2. Assert clean code output with no Markdown wrappers
    assert "```python" not in generated_code
    assert "```" not in generated_code

    # 3. Validate Python syntax compilation of generated code
    try:
        compile(generated_code, "<string>", "exec")
    except SyntaxError as e:
        pytest.fail(f"Generated code contains Python syntax errors: {e}")
