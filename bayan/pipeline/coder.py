"""Coding stage: validated LessonPlan in, Manim scene code out.

The service owns prompt grounding (plan beats verbatim plus deterministic
few-shot catalogue examples), fence stripping, a parse-only sanity check, and
record keeping. It never executes, imports, or compiles-and-runs the code it
produces; ``ast.parse`` and writing ``scene.py`` are the maximum.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from bayan.generator.llm_client import LLMClient, LLMError, clean_code_block
from bayan.pipeline.models import (
    DEFAULT_PROFILE,
    AttemptRecord,
    CodeAttemptEvidence,
    LessonPlan,
)
from bayan.pipeline.pricing import estimate_cost_usd
from bayan.pipeline.records import evidence_fingerprint, write_stage_record
from bayan.templates.catalogue import get_template_catalogue, read_fixture_code
from bayan.utils.atomic_io import atomic_write_text

SCENE_FILENAME = "scene.py"
CODING_RECORD_FILENAME = "coding.json"

FIXTURE_EXEMPLAR_COUNT = 2

CODER_SYSTEM_PROMPT = (
    "You write Manim (Community Edition) scene code for Arabic math lessons as "
    "strict Python. Reply with executable Python only: no markdown, no prose. Rules:\n"
    "1. Start the file with: from manim import *\n"
    "2. Arabic text ONLY through the helper: from bayan.utils.arabic_helper import "
    "ArabicText, rtl_glyphs. Never build Arabic with Text(...) or Tex(...).\n"
    "3. Define exactly one scene: class GeneratedScene(Scene) with construct(self).\n"
    "4. Every element is animated with self.play(...) in order; never self.add().\n"
    "5. Animate Arabic right-to-left with: self.play(Write(rtl_glyphs(text))). "
    "Never reverse text by slicing (ad-hoc reversal).\n"
    "6. No file, network, socket, subprocess, or os.system usage; pure animation only.\n"
    "7. Arabic literals only inside string literals, never in comments.\n"
    "8. The lesson plan in the user message is the contract: cover its beats in order."
)


class SceneCodeProvider(Protocol):
    """The seam the coding stage reaches through for scene code."""

    def generate_scene_code(
        self, *, plan: LessonPlan, system_prompt: str, user_prompt: str
    ) -> CodeAttemptEvidence: ...


class CodingError(RuntimeError):
    """The provider output never became parsable, non-empty scene code."""

    def __init__(self, message: str, record_path: Path) -> None:
        super().__init__(message)
        self.record_path = record_path


def select_few_shot_fixtures() -> list[str]:
    """Pick catalogue fixture slugs as few-shot style exemplars.

    The exemplars anchor code style (helper usage, animation discipline), not
    lesson semantics, so the first fixtures in slug order are used and every
    run grounds the prompt identically.
    """
    return sorted(get_template_catalogue())[:FIXTURE_EXEMPLAR_COUNT]


def build_coder_prompt(plan: LessonPlan, profile: str, example_codes: list[str]) -> tuple[str, str]:
    """Build the system and user prompts, embedding the plan beats verbatim."""
    beats_json = json.dumps(
        {"beats": [beat.model_dump() for beat in plan.beats]},
        ensure_ascii=False,
        indent=2,
    )
    examples = "\n\n".join(
        f"# Approved catalogue example {index + 1}\n{code}"
        for index, code in enumerate(example_codes)
    )
    system = CODER_SYSTEM_PROMPT
    user = (
        f"Lesson plan (the contract), language profile: {profile}\n"
        f"{beats_json}\n\n"
        "Follow the style of these approved catalogue examples:\n\n"
        f"{examples}"
    )
    return system, user


class CoderService:
    """Plan in: scene code text, plus scene.py and a coding record on disk.

    One provider call per run -- bounded repair arrives later in the
    pipeline. Empty or unparsable output raises :class:`CodingError` after
    writing a failure record; the produced code is only ever parsed, never
    executed.
    """

    def __init__(
        self,
        provider: SceneCodeProvider,
        run_dir: Path,
        *,
        record_filename: str = CODING_RECORD_FILENAME,
    ) -> None:
        self.provider = provider
        self.run_dir = run_dir
        self.record_filename = record_filename

    def code(self, plan: LessonPlan, *, profile: str = DEFAULT_PROFILE) -> str:
        self.run_dir.mkdir(parents=True, exist_ok=True)

        examples = [read_fixture_code(slug) for slug in select_few_shot_fixtures()]
        system_prompt, user_prompt = build_coder_prompt(plan, profile, examples)

        try:
            evidence = self.provider.generate_scene_code(
                plan=plan, system_prompt=system_prompt, user_prompt=user_prompt
            )
        except LLMError as error:
            raise self._fail(
                f"Coding failed: the provider call did not return code. Last error: {error}.",
                [AttemptRecord.rejected(1, str(error))],
                user_prompt,
                system_prompt,
                profile,
            ) from error

        cleaned = clean_code_block(evidence.code)
        if not cleaned:
            raise self._fail(
                "Coding failed: the provider returned empty scene code.",
                [AttemptRecord.rejected(1, "empty output", evidence.raw_response)],
                user_prompt,
                system_prompt,
                profile,
            )

        try:
            ast.parse(cleaned)
        except SyntaxError as error:
            raise self._fail(
                f"Coding failed: the produced scene code does not parse ({error}).",
                [AttemptRecord.rejected(1, f"does not parse: {error}", evidence.raw_response)],
                user_prompt,
                system_prompt,
                profile,
            ) from None

        atomic_write_text(self.run_dir / SCENE_FILENAME, cleaned + "\n")
        write_stage_record(
            self.run_dir,
            self._record(
                status="completed",
                prompt=user_prompt,
                system_prompt=system_prompt,
                profile=profile,
                attempts=[
                    AttemptRecord.accepted(
                        1, evidence, estimate_cost_usd(evidence.model, evidence.usage)
                    ).model_dump()
                ],
                failure=None,
                provider_fingerprint=evidence.fingerprint,
            ),
            self.record_filename,
        )
        return cleaned

    def _fail(
        self,
        failure: str,
        attempts: list[AttemptRecord],
        prompt: str,
        system_prompt: str,
        profile: str,
    ) -> CodingError:
        """Write the failure record and return the typed error to raise."""
        record_path = write_stage_record(
            self.run_dir,
            self._record(
                status="failed",
                prompt=prompt,
                system_prompt=system_prompt,
                profile=profile,
                attempts=[attempt.model_dump() for attempt in attempts],
                failure=f"{failure} See records/{self.record_filename}.",
            ),
            self.record_filename,
        )
        return CodingError(f"{failure} See {record_path}.", record_path)

    def _record(
        self,
        *,
        status: str,
        prompt: str,
        system_prompt: str,
        profile: str,
        attempts: list[dict[str, Any]],
        failure: str | None,
        provider_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        return {
            "stage": "coding",
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "prompt": prompt,
            "system_prompt": system_prompt,
            "profile": profile,
            "provider_fingerprint": provider_fingerprint,
            "attempts": attempts,
            "failure": failure,
            "scene": SCENE_FILENAME if status == "completed" else None,
        }


class LLMCoderProvider:
    """Real provider adapter over the hardened client's code mode."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def generate_scene_code(
        self, *, plan: LessonPlan, system_prompt: str, user_prompt: str
    ) -> CodeAttemptEvidence:
        code = self.client.generate_code(system_prompt=system_prompt, user_prompt=user_prompt)
        return CodeAttemptEvidence(
            code=code,
            raw_response=self.client.last_raw_content or "",
            fingerprint=evidence_fingerprint(
                self.client.model, self.client.base_url, plan.model_dump_json()
            ),
            model=self.client.model,
            usage=self.client.last_usage,
        )
