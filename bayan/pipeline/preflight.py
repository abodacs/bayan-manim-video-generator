"""Preflight gates: static, host-side inspection of generated scene code.

The gates are pure functions over the code text -- ``ast`` parsing and
string/token analysis only, never an import, an ``exec``, or any other
execution of the target code (AgDR-0002). A single failed gate blocks the
render; every failure carries gate name, line, excerpt, and a plain-English
suggestion so the repair classifier can work without re-parsing.
"""

from __future__ import annotations

import ast
import io
import json
import re
import tokenize
from dataclasses import asdict, dataclass
from typing import Final, Literal

from bayan.pipeline.models import DEFAULT_PROFILE
from bayan.pipeline.profiles import LanguageProfile, get_profile

ALLOWED_MODULES: Final[frozenset[str]] = frozenset({"manim", "math", "bayan.utils.arabic_helper"})

BANNED_CALLABLES: Final[frozenset[str]] = frozenset(
    {"eval", "exec", "__import__", "open", "system", "popen"}
)

BANNED_ROOT_MODULES: Final[frozenset[str]] = frozenset(
    {"subprocess", "socket", "urllib", "requests", "http"}
)

BANNED_DOTTED_CALLS: Final[frozenset[str]] = frozenset({"os.system", "os.popen"})

BANNED_CALL_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b(?:eval|exec|__import__)\s*\(")

_ARABIC_SCRIPT_RANGES: Final[tuple[tuple[int, int], ...]] = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
)
PRESENTATION_FORM_RANGES: Final[tuple[tuple[int, int], ...]] = (
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def contains_arabic_script(text: str) -> bool:
    """Whether the text contains Arabic-script letters and marks."""
    return any(
        start <= ord(character) <= end for character in text for start, end in _ARABIC_SCRIPT_RANGES
    )


def contains_presentation_forms(text: str) -> bool:
    """Whether the text contains pre-shaped Arabic presentation forms."""
    return any(
        start <= ord(character) <= end
        for character in text
        for start, end in PRESENTATION_FORM_RANGES
    )


@dataclass(frozen=True)
class GateResult:
    """Machine-readable result of one preflight gate (or one violation)."""

    gate: str
    status: Literal["passed", "failed"]
    line: int | None = None
    excerpt: str | None = None
    suggestion: str | None = None


def _passed(gate: str) -> GateResult:
    return GateResult(gate=gate, status="passed")


def _failed(gate: str, line: int | None, excerpt: str, suggestion: str) -> GateResult:
    return GateResult(
        gate=gate,
        status="failed",
        line=line,
        excerpt=excerpt[:200],
        suggestion=suggestion,
    )


def _static_string(argument: ast.AST) -> str | None:
    """Return the constant text of an argument, including f-string parts."""
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value
    if isinstance(argument, ast.JoinedStr):
        return "".join(
            value.value
            for value in argument.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        )
    return None


def _dotted_path(node: ast.expr) -> str | None:
    """Return the dotted name a Name/Attribute chain refers to, if any."""
    parts: list[str] = []
    current: ast.expr | None = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _check_syntax(code: str) -> tuple[ast.Module | None, GateResult | None]:
    try:
        return ast.parse(code), None
    except SyntaxError as error:
        result = _failed(
            "syntax",
            error.lineno,
            (error.text or "").strip(),
            f"Fix the Python syntax error at line {error.lineno}, column {error.offset}; "
            "the renderer needs parseable Python.",
        )
        return None, result


def _check_imports(tree: ast.Module) -> list[GateResult]:
    failures: list[GateResult] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_MODULES:
                    failures.append(
                        _failed(
                            "imports",
                            node.lineno,
                            f"import {alias.name}",
                            f"Import '{alias.name}' is not allowed. Only manim, math, and "
                            "bayan.utils.arabic_helper may be imported.",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                failures.append(
                    _failed(
                        "imports",
                        node.lineno,
                        "from . import ...",
                        "Relative imports are not allowed in generated scenes; import manim "
                        "and bayan.utils.arabic_helper only.",
                    )
                )
                continue
            module = node.module or ""
            if module not in ALLOWED_MODULES:
                failures.append(
                    _failed(
                        "imports",
                        node.lineno,
                        f"from {module} import ...",
                        f"Import '{module}' is not allowed. Only manim, math, and "
                        "bayan.utils.arabic_helper may be imported.",
                    )
                )
    return failures


def _check_bans(tree: ast.Module, code: str) -> list[GateResult]:
    failures: list[GateResult] = []

    def _ban(line: int, construct: str, reason: str) -> None:
        failures.append(_failed("bans", line, construct, reason))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLABLES:
                _ban(
                    node.lineno,
                    f"{node.func.id}(...)",
                    f"'{node.func.id}' is banned in generated scenes: no execution, "
                    "introspection, or file access on the host or in the worker.",
                )
            path = _dotted_path(node.func)
            if path:
                root = path.split(".")[0]
                if path in BANNED_DOTTED_CALLS:
                    _ban(
                        node.lineno,
                        f"{path}(...)",
                        f"'{path}' is banned: generated scenes have no legitimate "
                        "operating-system access.",
                    )
                elif root in BANNED_ROOT_MODULES:
                    _ban(
                        node.lineno,
                        f"{path}(...)",
                        f"'{path}' is banned: generated scenes must not touch "
                        "subprocess, socket, urllib, requests, or http.",
                    )
        elif isinstance(node, ast.Attribute):
            path = _dotted_path(node)
            if path and path.split(".")[0] in BANNED_ROOT_MODULES:
                _ban(
                    node.lineno,
                    path,
                    f"References to '{path.split('.')[0]}' are banned: generated scenes "
                    "must not touch subprocess, socket, urllib, requests, or http.",
                )

    flagged_lines = {failure.line for failure in failures}
    for match in BANNED_CALL_PATTERN.finditer(code):
        line = code.count("\n", 0, match.start()) + 1
        if line in flagged_lines:
            continue
        failures.append(
            _failed(
                "bans",
                line,
                match.group(0),
                "Dynamic execution is banned, even where the static walk might miss it.",
            )
        )
    return failures


def _check_arabic_literals(tree: ast.Module) -> list[GateResult]:
    failures: list[GateResult] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else (func.attr if isinstance(func, ast.Attribute) else None)
            )
            if name in {"Text", "Tex"}:
                for argument in [*node.args, *node.keywords]:
                    value = argument.value if isinstance(argument, ast.keyword) else argument
                    text = _static_string(value)
                    if text is not None and contains_arabic_script(text):
                        failures.append(
                            _failed(
                                "arabic",
                                node.lineno,
                                f'{name}("{text}")',
                                "Arabic text must use ArabicText(...) from "
                                "bayan.utils.arabic_helper, not Text/Tex.",
                            )
                        )
        if isinstance(node, ast.Subscript):
            step = getattr(node.slice, "step", None)
            if isinstance(step, ast.UnaryOp) and isinstance(step.op, ast.USub):
                failures.append(
                    _failed(
                        "arabic",
                        node.lineno,
                        "[::-1] slicing",
                        "Deliberate text reversal is banned; animate right-to-left with "
                        "rtl_glyphs(text) instead.",
                    )
                )
    return failures


def _check_string_constants(tree: ast.Module, profile: LanguageProfile) -> list[GateResult]:
    """Presentation forms and digit-family checks against the profile."""
    failures: list[GateResult] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if contains_presentation_forms(node.value):
            failures.append(
                _failed(
                    "arabic",
                    node.lineno,
                    node.value[:80],
                    "Arabic presentation forms (pre-shaped glyphs) are banned; pass "
                    "plain Arabic text and let ArabicText shape it.",
                )
            )
        unexpected_digits = sorted(
            {
                character
                for character in node.value
                if character.isdigit() and character not in profile.expected_digits
            }
        )
        if unexpected_digits:
            failures.append(
                _failed(
                    "arabic",
                    node.lineno,
                    node.value[:80],
                    f"The {profile.name} profile expects the digits "
                    f"{''.join(profile.expected_digits)}; found "
                    f"{''.join(unexpected_digits)} in on-screen text.",
                )
            )
    return failures


def _check_comments(code: str) -> list[GateResult]:
    failures: list[GateResult] = []
    for token in tokenize.generate_tokens(io.StringIO(code).readline):
        if token.type == tokenize.COMMENT and contains_arabic_script(token.string):
            failures.append(
                _failed(
                    "arabic",
                    token.start[0],
                    token.string,
                    "Arabic must not appear in comments (house rule): move it into a "
                    "string literal, e.g. an ArabicText argument.",
                )
            )
    return failures


def run_gates(code: str, *, profile: str = DEFAULT_PROFILE) -> list[GateResult]:
    """Run every preflight gate over generated scene code.

    Pure: parse and inspect only, no execution. When the syntax gate fails
    the remaining gates cannot evaluate anything meaningful, so its failure
    is the whole result. A passing gate contributes one ``passed`` result; a
    failing gate contributes one result per violation. The profile decides
    the expected digit family: under a Western-digit profile, Arabic-Indic
    digits inside string literals fail the Arabic gate.
    """
    profile_data = get_profile(profile)
    tree, syntax_failure = _check_syntax(code)
    if syntax_failure is not None or tree is None:
        return [syntax_failure] if syntax_failure else []

    results = [_passed("syntax")]
    gates_with_failures = (
        ("imports", _check_imports(tree)),
        ("bans", _check_bans(tree, code)),
        (
            "arabic",
            [
                *_check_arabic_literals(tree),
                *_check_string_constants(tree, profile_data),
                *_check_comments(code),
            ],
        ),
    )
    for gate, failures in gates_with_failures:
        if failures:
            results.extend(failures)
        else:
            results.append(_passed(gate))
    return results


def gates_blocked(results: list[GateResult]) -> bool:
    """Whether any gate result blocks the render."""
    return any(result.status != "passed" for result in results)


def gates_to_json(results: list[GateResult]) -> str:
    """Serialize gate results for a stage record."""
    return json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False)
