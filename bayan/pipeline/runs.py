"""Read-model over past generate runs: what ``bayan runs`` reports.

The inspection rules live here, not in the CLI: what counts as a readable
run, which artifacts a generate run produces, and how the records' cost
total relates to the run summary. The CLI only formats what this module
returns, so future consumers (an export command, a dashboard) reuse the
same answers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bayan.pipeline.coder import SCENE_FILENAME
from bayan.pipeline.planner import PLAN_FILENAME
from bayan.pipeline.records import total_cost_usd
from bayan.pipeline.spine import (
    DRAFT_FILENAME,
    PREVIEW_FILENAME,
    RUN_SUMMARY_FILENAME,
)

RUN_ARTIFACTS: tuple[str, ...] = (PLAN_FILENAME, SCENE_FILENAME, DRAFT_FILENAME, PREVIEW_FILENAME)
MEDIA_FILENAME = DRAFT_FILENAME


def iter_run_dirs(runs_root: Path) -> list[Path]:
    """A run's directory holds generated runs, sorted oldest to newest."""
    if not runs_root.is_dir():
        return []
    return sorted(path for path in runs_root.iterdir() if path.is_dir())


def load_run_summary(run_dir: Path) -> dict[str, Any] | None:
    """Read a run's summary, or None when missing or unreadable."""
    summary_path = run_dir / RUN_SUMMARY_FILENAME
    if not summary_path.is_file():
        return None
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def has_media(run_dir: Path) -> bool:
    """Whether the run produced its video artifact."""
    return (run_dir / MEDIA_FILENAME).is_file()


def records_cost(run_dir: Path) -> float | None:
    """Sum per-attempt costs from stage records; None when nothing recorded."""
    return total_cost_usd(run_dir)
