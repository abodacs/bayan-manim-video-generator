"""Reject non-English alphabetic characters in Python comments.

This check intentionally uses a conservative, dependency-free rule: alphabetic
characters in comments must be ASCII English letters. Non-ASCII text in Python
strings is allowed, which keeps Arabic lesson content valid while keeping source
comments readable to the whole project team.
"""

from __future__ import annotations

import argparse
import io
import sys
import tokenize
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommentViolation:
    line: int
    column: int
    letters: tuple[str, ...]


def non_english_letters(comment: str) -> tuple[str, ...]:
    """Return distinct alphabetic characters outside the English alphabet."""
    letters: list[str] = []
    for character in comment:
        is_english = "A" <= character <= "Z" or "a" <= character <= "z"
        if character.isalpha() and not is_english and character not in letters:
            letters.append(character)
    return tuple(letters)


def find_comment_violations(source: str) -> list[CommentViolation]:
    """Find Python comments containing non-English alphabetic characters."""
    violations: list[CommentViolation] = []
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)

    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue

        letters = non_english_letters(token.string)
        if letters:
            violations.append(
                CommentViolation(
                    line=token.start[0],
                    column=token.start[1],
                    letters=letters,
                )
            )

    return violations


def check_file(path: Path) -> list[CommentViolation]:
    """Read a Python file using its declared source encoding and check comments."""
    with tokenize.open(str(path)) as source_file:
        return find_comment_violations(source_file.read())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that alphabetic characters in Python comments are English.",
    )
    parser.add_argument("paths", nargs="+", help="Python files to inspect")
    args = parser.parse_args(argv)

    failed = False
    for filename in args.paths:
        path = Path(filename)
        try:
            violations = check_file(path)
        except (OSError, SyntaxError, UnicodeError, tokenize.TokenError) as error:
            print(f"{path}: unable to inspect Python comments: {error}", file=sys.stderr)
            failed = True
            continue

        for violation in violations:
            letters = ", ".join(repr(letter) for letter in violation.letters)
            print(
                f"{path}:{violation.line}:{violation.column + 1}: "
                f"Python comments must use English letters; found {letters}",
                file=sys.stderr,
            )
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
