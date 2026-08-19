"""Crash-safe file writes shared across workflow modules."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, text: str) -> None:
    """Write text to a unique sibling temporary file, then replace the target.

    A reader either sees the previous complete content or the new complete
    content, never a partially written file. The temporary name is unique per
    call, so concurrent writers to one path cannot clobber each other's
    temporary files, and the bytes are flushed to disk before the replace.
    """
    handle_fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
