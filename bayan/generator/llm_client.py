"""OpenAI-compatible LLM client, the single seam between Bayan and a provider.

Configuration resolves explicit arguments first, then ``BAYAN_*`` environment
variables, then ``OPENAI_API_KEY`` (see the README "Environment variables"
section). The client performs no retries -- bounded retry loops belong to the
services built on top of it -- and never lets key material reach an error.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import TypeVar

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import BaseModel, ValidationError

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_BASE_URL = "https://api.z.ai/api/coding/paas/v4/"
DEFAULT_MODEL = "glm-5.2"
MAX_ERROR_CHARS = 2_000
MAX_EXCERPT_CHARS = 400

SYSTEM_PROMPT = (
    "You are an expert animator using Manim (Community Edition). Your task is "
    "to generate valid, clean, and executable Python code that defines a single "
    "Manim Scene class.\n\n"
    "Rules:\n"
    "1. ALWAYS start the code with `from manim import *`.\n"
    "2. ONLY return executable Python code. Do not write explanations. Do not "
    "include markdown blocks like ```python.\n"
    "3. If there is any Arabic text in the video, you MUST:\n"
    "   - Import the helpers using: `from bayan.utils.arabic_helper import "
    "ArabicText, rtl_glyphs`\n"
    '   - Use `ArabicText("your arabic text")` instead of `Text(...)` or `Tex(...)`.\n'
    "4. ALL elements (both shapes like Circle and texts) MUST be explicitly "
    "animated using `self.play(...)` in sequence. Do NOT use `self.add()` or "
    "render static objects unless requested.\n"
    "5. Keep the scene name consistent, such as class GeneratedScene(Scene).\n"
    "6. ARABIC ANIMATION INSTRUCTIONS:\n"
    "   - NEVER add the ArabicText object to the scene before animating it.\n"
    "   - Set its position FIRST using `.next_to()`, `.to_edge()`, etc.\n"
    "   - Write Arabic smoothly from Right-to-Left using: "
    "`self.play(Write(rtl_glyphs(arabic_text)))`.\n"
)


class LLMError(RuntimeError):
    """Base class for every error this client raises."""


class LLMConfigError(LLMError):
    """Missing or invalid configuration, raised before any network call."""


class LLMProviderError(LLMError):
    """The provider call failed (network, HTTP, or API-level error)."""


class LLMResponseFormatError(LLMProviderError):
    """The provider reply was not the JSON the requested schema promised."""


@dataclass(frozen=True)
class LLMUsage:
    """Token counts reported by the provider for one call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


ModelT = TypeVar("ModelT", bound=BaseModel)

_JSON_FENCE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


def redact_secret(text: str, secret: str | None) -> str:
    """Scrub API key material out of provider text before it reaches an error."""
    if not secret:
        return text
    return text.replace(secret, "***redacted***")


def _bound(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} characters]"


def _extract_usage(response: object) -> LLMUsage | None:
    """Read token counts off a provider response, tolerating their absence."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    total = getattr(usage, "total_tokens", None)
    if not (isinstance(prompt, int) and isinstance(completion, int) and isinstance(total, int)):
        return None
    return LLMUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


def _strip_json_fence(text: str) -> str:
    """Undo the markdown fences providers add when they ignore response_format."""
    match = _JSON_FENCE.match(text.strip())
    return match.group(1).strip() if match else text.strip()


def _parse_structured(raw_content: str, response_model: type[ModelT]) -> ModelT:
    """Parse and validate a provider reply against its pydantic model."""
    reply = _strip_json_fence(raw_content)
    try:
        data = json.loads(reply)
    except json.JSONDecodeError as error:
        raise LLMResponseFormatError(
            f"Provider reply was not valid JSON for {response_model.__name__}: {error}. "
            f"Reply excerpt: {_bound(reply, MAX_EXCERPT_CHARS)!r}"
        ) from None
    try:
        return response_model.model_validate(data)
    except ValidationError as error:
        raise LLMResponseFormatError(
            f"Provider reply did not match the {response_model.__name__} schema: "
            f"{_bound(str(error), MAX_ERROR_CHARS)}. "
            f"Reply excerpt: {_bound(reply, MAX_EXCERPT_CHARS)!r}"
        ) from None


def _json_schema_response_format(response_model: type[BaseModel]) -> ResponseFormatJSONSchema:
    """Build the response_format payload that requests a pydantic-shaped reply."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": response_model.__name__,
            "schema": response_model.model_json_schema(),
        },
    }


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = (
            api_key or os.environ.get("BAYAN_API_KEY") or os.environ.get("OPENAI_API_KEY")
        )
        if not self.api_key:
            raise LLMConfigError(
                "Missing LLM API key: set BAYAN_API_KEY (or OPENAI_API_KEY) in the "
                "environment or a local .env file. Optional settings: BAYAN_BASE_URL "
                f"(default {DEFAULT_BASE_URL}) and BAYAN_LLM_MODEL (default "
                f"{DEFAULT_MODEL}). See the 'Environment variables' section in README.md."
            )

        self.base_url = base_url or os.environ.get("BAYAN_BASE_URL", DEFAULT_BASE_URL)
        self.model: str = model or os.environ.get("BAYAN_LLM_MODEL", DEFAULT_MODEL)
        self.last_usage: LLMUsage | None = None

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_manim_code(self, user_prompt: str) -> str:
        """Send the user prompt to the LLM and return the parsed Python script."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Create a Manim scene for: {user_prompt}",
            },
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
            )
            raw_content = response.choices[0].message.content or ""
        except Exception as error:
            raise self._provider_error(error) from None
        self.last_usage = _extract_usage(response)
        return self._clean_code(raw_content)

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ModelT],
        temperature: float = 0.2,
    ) -> ModelT:
        """Request JSON shaped like ``response_model`` and return a validated instance.

        The pydantic-derived JSON schema travels in ``response_format``; providers
        that ignore it still work because the reply is validated before returning.
        Raises ``LLMProviderError`` for call failures and
        ``LLMResponseFormatError`` when the reply is not valid, schema-shaped JSON.
        """
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format=_json_schema_response_format(response_model),
            )
            raw_content = response.choices[0].message.content or ""
        except Exception as error:
            raise self._provider_error(error) from None
        self.last_usage = _extract_usage(response)
        return _parse_structured(raw_content, response_model)

    def _provider_error(self, error: Exception) -> LLMProviderError:
        """Wrap a provider failure with the API key scrubbed from the message.

        The cause is suppressed rather than chained: Python prints chained
        exceptions verbatim, and the original text can carry the key.
        """
        detail = redact_secret(_bound(str(error), MAX_ERROR_CHARS), self.api_key)
        return LLMProviderError(f"Failed to communicate with LLM provider: {detail}")

    def _clean_code(self, raw_code: str) -> str:
        """Extract raw Python code out of LLM markdown wrappers if present."""
        pattern = r"```python(.*?)```"
        match = re.search(pattern, raw_code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_code.strip()
