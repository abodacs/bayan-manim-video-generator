"""Shared OpenAI mocking helpers for tests that exercise the LLM seam."""

from unittest.mock import MagicMock


def mocked_client(mock_openai_class: MagicMock) -> MagicMock:
    """Wire one mocked OpenAI class to a mocked client and hand the client back."""
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    return mock_client


def mock_chat_response(content: str, usage: tuple[int, int, int] | None = None) -> MagicMock:
    """Build a provider response carrying ``content`` and optional token counts."""
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    if usage is not None:
        response.usage.prompt_tokens = usage[0]
        response.usage.completion_tokens = usage[1]
        response.usage.total_tokens = usage[2]
    return response
