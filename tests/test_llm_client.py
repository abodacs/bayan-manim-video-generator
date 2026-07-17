import os
import pytest
from unittest.mock import MagicMock, patch
from bayan.generator.llm_client import LLMClient

# -------------------------------------------------------------------------
# 1. Tests for Code Cleaner Function (_clean_code)
# -------------------------------------------------------------------------

def test_clean_code_with_markdown_wrapper():
    """Verify that pure code is extracted properly when enclosed in Markdown code blocks."""
    client = LLMClient(api_key="fake-api-key")
    raw_response = (
        "```python\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        pass\n"
        "```"
    )
    expected_clean_code = (
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        pass"
    )
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
    """Verify that correct API parameters are sent, and the response is received and cleaned successfully."""
    # Initialize Mock instance for OpenAI Client
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # Mock response structure returned from OpenAI (choices[0].message.content)
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="```python\n# Clean Code\n```"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    # Execute method under test
    client = LLMClient(api_key="fake-api-key")
    result = client.generate_manim_code("Draw a red circle")

    # Assert code output is cleaned correctly
    assert result == "# Clean Code"

    # Assert API was called once with accurate arguments
    mock_client.chat.completions.create.assert_called_once()
    called_kwargs = mock_client.chat.completions.create.call_args[1]
    
    assert called_kwargs["model"] == "gpt-4o"
    assert called_kwargs["temperature"] == 0.2
    assert called_kwargs["messages"][0]["role"] == "system"
    assert "Draw a red circle" in called_kwargs["messages"][1]["content"]


@patch("bayan.generator.llm_client.OpenAI")
def test_generate_manim_code_api_error_raises_runtime_error(mock_openai_class):
    """Verify that API communication/authentication errors are wrapped and raised as descriptive RuntimeErrors."""
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

def has_active_openai_quota():
    if not os.getenv("OPENAI_API_KEY"):
        return False
    try:
        from openai import OpenAI
        client = OpenAI()
        # Fast lightweight request to verify active balance/quota
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        return True
    except Exception as e:
        # Catch quota exhaustion or network error to safely skip integration tests
        if "quota" in str(e).lower() or "insufficient_quota" in str(e).lower():
            return False
        return False

@pytest.mark.skipif(
    not has_active_openai_quota(),
    reason="This integration test requires an active OpenAI API key with sufficient quota."
)
def test_integration_live_llm_call():
    """Live API integration test: validates actual endpoint connectivity and generated Python code syntax."""
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