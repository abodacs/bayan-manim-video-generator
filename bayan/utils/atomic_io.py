"""Crash-safe file writes shared across workflow modules."""

from __future__ import annotations

from pathlib import Path


def atomic_write_text(path: Path, text: str) -> None:
    """Write text to a sibling temporary file, then replace the target.

    A reader either sees the previous complete content or the new complete
    content, never a partially written file.
    """
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)
