import os
from unittest.mock import MagicMock, patch

import pytest

from bayan.generator.llm_client import LLMClient

# -------------------------------------------------------------------------
# 1. Tests for Code Cleaner Function (_clean_code)
# -------------------------------------------------------------------------


def test_clean_code_with_markdown_wrapper():
    """Verify that pure code is extracted properly when enclosed in Markdown code blocks."""
    client = LLMClient(api_key="fake-api-key")
    raw_response = (
        "```python\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass\n```"
    )
    expected_clean_code = "class GeneratedScene(Scene):\n    def construct(self):\n        pass"
    assert client._clean_code(raw_response) == expected_clean_code


def test_clean_code_without_markdown_wrapper():
    """Verify that raw code is returned as-is if no Markdown wrappers are present."""
    client = LLMClient(api_key="fake-api-key")
    raw_response = "class GeneratedScene(Scene):\n    pass"
    assert client._clean_code(raw_response) == raw_response.strip()


# -------------------------------------------------------------------------
# 2. Unit Tests with API Mocking
# -------------------------------------------------------------------------


@patch("bayan.generator.llm_client.OpenAI")
def test_generate_manim_code_success(mock_openai_class):
    """Verify that correct API parameters are sent,
    and the response is received and cleaned successfully."""
    # Initialize Mock instance for OpenAI Client
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

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
def test_generate_manim_code_api_error_raises_runtime_error(mock_openai_class):
    """Verify that API communication/authentication errors
    are wrapped and raised as descriptive RuntimeErrors."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    # Simulate an exception during API request
    mock_client.chat.completions.create.side_effect = Exception("Connection timeout")

    client = LLMClient(api_key="fake-api-key")

    with pytest.raises(RuntimeError) as exc_info:
        client.generate_manim_code("Draw a square")

    assert "Failed to communicate with LLM provider" in str(exc_info.value)


# =========================================================================
# 3. Integration Test (Safely skipped if active quota is unavailable)
# =========================================================================


def has_active_bayan_quota():
    # Use the unified environmental variables updated configuration setup
    api_key = os.getenv("BAYAN_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False
    try:
        from openai import OpenAI

        base_url = os.getenv("BAYAN_BASE_URL", "https://api.z.ai/api/paas/v4/")
        model = os.getenv("BAYAN_LLM_MODEL", "glm-5.2")

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
