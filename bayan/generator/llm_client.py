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
from openai._types import Omit, omit
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
    """The provider reply was not the JSON the requested schema promised.

    ``raw_content`` keeps the full (key-redacted) reply so run records stay
    auditable without reaching back into the client.
    """

    def __init__(self, message: str, raw_content: str = "") -> None:
        super().__init__(message)
        self.raw_content = raw_content


@dataclass(frozen=True)
class LLMUsage:
    """Token counts reported by the provider for one call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


ModelT = TypeVar("ModelT", bound=BaseModel)

_CODE_FENCE = re.compile(r"```python(.*?)```", re.DOTALL)
_JSON_FENCE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


def _redact(text: str, secret: str) -> str:
    """Scrub API key material out of provider text before it reaches an error."""
    return text.replace(secret, "***redacted***")


def _bound(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [truncated {len(text) - limit} characters]"


def _extract_usage(response: object) -> LLMUsage | None:
    """Read token counts off a provider response, tolerating their absence.

    OpenAI-compatible providers vary in what they return here, so the counts
    are taken only when all three arrive as plain integers.
    """
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


def clean_code_block(raw_code: str) -> str:
    """Extract raw Python code out of LLM markdown wrappers if present."""
    match = _CODE_FENCE.search(raw_code)
    if match:
        return match.group(1).strip()
    return raw_code.strip()


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
        resolved_key = (
            api_key or os.environ.get("BAYAN_API_KEY") or os.environ.get("OPENAI_API_KEY")
        )
        if not resolved_key:
            raise LLMConfigError(
                "Missing LLM API key: set BAYAN_API_KEY (or OPENAI_API_KEY) in the "
                "environment or a local .env file. Optional settings: BAYAN_BASE_URL "
                f"(default {DEFAULT_BASE_URL}) and BAYAN_LLM_MODEL (default "
                f"{DEFAULT_MODEL}). See the 'Environment variables' section in README.md."
            )

        self.api_key: str = resolved_key
        self.base_url = base_url or os.environ.get("BAYAN_BASE_URL", DEFAULT_BASE_URL)
        self.model: str = model or os.environ.get("BAYAN_LLM_MODEL", DEFAULT_MODEL)
        self.last_usage: LLMUsage | None = None
        self.last_raw_content: str | None = None

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_manim_code(self, user_prompt: str) -> str:
        """Send the user prompt to the LLM and return the parsed Python script."""
        return self.generate_code(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Create a Manim scene for: {user_prompt}",
        )

    def generate_code(
        self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2
    ) -> str:
        """Free-form code generation with caller-supplied prompts.

        Returns the fence-stripped Python text; the raw reply stays available
        as ``last_raw_content`` for run records.
        """
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return clean_code_block(self._complete(messages, temperature=temperature))

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
        raw_content = self._complete(
            messages,
            response_format=_json_schema_response_format(response_model),
            temperature=temperature,
        )
        return self._parse_structured(raw_content, response_model)

    def _complete(
        self,
        messages: list[ChatCompletionMessageParam],
        response_format: ResponseFormatJSONSchema | Omit = omit,
        temperature: float = 0.2,
    ) -> str:
        """Run one chat completion and return its text content.

        Centralizes the provider-failure policy: the key is scrubbed from the
        message and the cause is suppressed (tracebacks print chained
        exceptions verbatim, and the original text can carry the key). Usage
        is captured from every successful response.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
            )
            raw_content = response.choices[0].message.content or ""
        except Exception as error:
            detail = _bound(_redact(str(error), self.api_key), MAX_ERROR_CHARS)
            raise LLMProviderError(f"Failed to communicate with LLM provider: {detail}") from None
        self.last_usage = _extract_usage(response)
        self.last_raw_content = raw_content
        return raw_content

    def _parse_structured(self, raw_content: str, response_model: type[ModelT]) -> ModelT:
        """Parse and validate a provider reply against its pydantic model."""
        reply = _strip_json_fence(raw_content)
        redacted_reply = _redact(reply, self.api_key)
        try:
            data = json.loads(reply)
        except json.JSONDecodeError as error:
            summary = f"Provider reply was not valid JSON for {response_model.__name__}: {error}"
            raise LLMResponseFormatError(
                self._reply_error(summary, redacted_reply), redacted_reply
            ) from None
        try:
            return response_model.model_validate(data)
        except ValidationError as error:
            summary = (
                f"Provider reply did not match the {response_model.__name__} schema: "
                f"{_redact(str(error), self.api_key)}"
            )
            raise LLMResponseFormatError(
                self._reply_error(summary, redacted_reply), redacted_reply
            ) from None

    def _reply_error(self, summary: str, reply: str) -> str:
        """Assemble a bounded, key-free failure message for a bad provider reply."""
        excerpt = _bound(_redact(reply, self.api_key), MAX_EXCERPT_CHARS)
        return _bound(f"{summary}. Reply excerpt: {excerpt!r}", MAX_ERROR_CHARS)
