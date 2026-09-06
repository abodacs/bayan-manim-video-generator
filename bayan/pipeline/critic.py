"""Phase-1 deterministic critic: typed checks over a run's artifacts.

Every check is a pure function over (plan, scene code, artifacts): the video
is analyzed on the host with ffprobe -- trusted tooling, not generated code
(AgDR-0002) -- and the preview frame with Pillow. Nothing here executes scene
code. The overflow heuristic is deliberately coarse: it catches text clipped
at the frame edge, not subtler layout problems; those are the teacher
reviewer's job in the final review round.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from bayan.pipeline.models import CheckResult, LessonPlan
from bayan.pipeline.preflight import contains_arabic_script

MIN_DURATION_SECONDS = 10
MAX_DURATION_SECONDS = 180
BORDER_BAND_FRACTION = 0.05
BACKGROUND_TOLERANCE = 8


def vlm_critique() -> CheckResult:
    """The vision-model critique's placeholder verdict.

    The VLM critic is out of scope for the MVP (epic #68 out-of-scope note):
    this stub records an honest ``not_implemented`` verdict -- no network
    calls, no client construction -- so ``bayan generate --vlm`` can record
    it and still complete on the deterministic verdict.
    """
    return CheckResult(
        check="vlm",
        status="not_implemented",
        evidence="The VLM critic is not implemented; it is out of scope for the MVP per epic #68.",
        suggestion="Rely on the deterministic checks plus teacher review.",
    )


def critic_blocked(results: list[CheckResult]) -> bool:
    """Whether any check verdict fails the run."""
    return any(result.status == "failed" for result in results)


def check_render_artifacts(
    draft_path: Path, preview_path: Path, render_status: str | None
) -> CheckResult:
    """The video and preview exist, are non-empty, and the render succeeded."""
    missing: list[str] = []
    for artifact in (draft_path, preview_path):
        if not artifact.exists() or artifact.stat().st_size == 0:
            missing.append(str(artifact))
    if missing:
        return CheckResult(
            check="render_artifacts",
            status="failed",
            evidence=f"Missing or empty artifacts: {', '.join(missing)}",
            suggestion="Re-run the pipeline; the render stage must produce draft.mp4 "
            "and preview.png before critique.",
        )
    if render_status != "completed":
        return CheckResult(
            check="render_artifacts",
            status="failed",
            evidence=f"The render record status is {render_status!r}, not 'completed'.",
            suggestion="Inspect records/05-render.json for the render failure.",
        )
    return CheckResult(
        check="render_artifacts",
        status="passed",
        evidence=f"{draft_path.name} and {preview_path.name} are present and non-empty.",
    )


def probe_duration_seconds(video_path: Path) -> float | None:
    """Read a video's duration with ffprobe, or None when unavailable/invalid.

    Runs trusted host tooling against a produced artifact; generated code is
    never involved.
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 -- fixed argv, no shell
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return float(result.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def check_duration(video_path: Path) -> CheckResult:
    """Video duration must sit within the declared bounds."""
    duration = probe_duration_seconds(video_path)
    if duration is None:
        return CheckResult(
            check="duration",
            status="not_applicable",
            evidence="ffprobe could not measure the duration (tool missing or invalid file).",
        )
    if duration < MIN_DURATION_SECONDS:
        return CheckResult(
            check="duration",
            status="failed",
            evidence=f"Measured {duration:.1f}s, below the {MIN_DURATION_SECONDS}s minimum.",
            suggestion="Add more beats or slow the animations so the lesson is watchable.",
        )
    if duration > MAX_DURATION_SECONDS:
        return CheckResult(
            check="duration",
            status="failed",
            evidence=f"Measured {duration:.1f}s, above the {MAX_DURATION_SECONDS}s maximum.",
            suggestion="Split the lesson or shorten animations to keep the video focused.",
        )
    return CheckResult(
        check="duration",
        status="passed",
        evidence=f"Measured {duration:.1f}s, within the "
        f"{MIN_DURATION_SECONDS}-{MAX_DURATION_SECONDS}s bounds.",
    )


def _background_level(image: Image.Image) -> int:
    """The most common grayscale level, i.e. the frame's background."""
    histogram = image.histogram()
    return max(range(len(histogram)), key=lambda level: histogram[level])


def check_overflow(preview_path: Path) -> CheckResult:
    """Flag non-background pixels in the outer border band of the preview.

    Heuristic: grayscale the frame, take the most common level as background,
    and scan the outer band (BORDER_BAND_FRACTION of each side). Content
    touching the band usually means clipped or edge-crowded text.
    """
    if not preview_path.exists() or preview_path.stat().st_size == 0:
        return CheckResult(
            check="overflow",
            status="not_applicable",
            evidence=f"No preview frame at {preview_path}; the overflow heuristic did not run.",
        )
    image = Image.open(preview_path).convert("L")
    width, height = image.size
    band_x = max(1, int(width * BORDER_BAND_FRACTION))
    band_y = max(1, int(height * BORDER_BAND_FRACTION))
    background = _background_level(image)

    # Vectorized: mark every pixel differing from the background, erase the
    # interior, and look for remaining marks -- i.e. marks in the border band.
    mask = image.point(lambda level: 255 if abs(level - background) > BACKGROUND_TOLERANCE else 0)
    mask.paste(0, (band_x, band_y, width - band_x, height - band_y))
    band_bbox = mask.getbbox()
    if band_bbox is not None:
        x, y = band_bbox[0], band_bbox[1]
        return CheckResult(
            check="overflow",
            status="failed",
            evidence=f"Non-background content at ({x}, {y}) inside the outer "
            f"{BORDER_BAND_FRACTION:.0%} border band.",
            suggestion="Move text away from the frame edge; keep a margin so "
            "nothing clips at the border.",
        )
    return CheckResult(
        check="overflow",
        status="passed",
        evidence=f"Border band ({BORDER_BAND_FRACTION:.0%}) is clean background.",
    )


def _string_literals(code: str) -> str:
    """All string-literal text in the scene code, joined."""
    literals: list[str] = []
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
    return "\n".join(literals)


def check_beat_coverage(plan: LessonPlan | None, code: str | None) -> list[CheckResult]:
    """Every beat's normalized on-screen text must appear in scene literals."""
    if plan is None or code is None:
        return [
            CheckResult(
                check="beat_coverage",
                status="not_applicable",
                evidence="No validated plan or scene code is available to compare.",
            )
        ]
    try:
        literals = _string_literals(code)
    except SyntaxError:
        return [
            CheckResult(
                check="beat_coverage",
                status="not_applicable",
                evidence="Scene code does not parse; the syntax gate already reported it.",
            )
        ]

    failures: list[CheckResult] = []
    for index, beat in enumerate(plan.beats):
        text = beat.on_screen_text.strip()
        if not text or text not in literals:
            script = "Arabic" if contains_arabic_script(text) else "non-Arabic"
            failures.append(
                CheckResult(
                    check="beat_coverage",
                    status="failed",
                    evidence=f"On-screen text of beat {index + 1} ({beat.title}) is absent "
                    f'from the scene literals ({script}): "{text[:80]}"',
                    suggestion="Add an ArabicText(...) line whose text matches the beat's "
                    "on-screen text exactly.",
                )
            )
    if not failures:
        return [
            CheckResult(
                check="beat_coverage",
                status="passed",
                evidence=f"All {len(plan.beats)} beats appear in the scene literals.",
            )
        ]
    return failures


def run_critic(
    *,
    plan: LessonPlan | None,
    code: str | None,
    draft_path: Path,
    preview_path: Path,
    render_status: str | None,
    vlm: bool = False,
) -> list[CheckResult]:
    """Run every deterministic check and return the verdicts in order."""
    results = [
        check_render_artifacts(draft_path, preview_path, render_status),
        check_duration(draft_path),
        check_overflow(preview_path),
        *check_beat_coverage(plan, code),
    ]
    if vlm:
        results.append(vlm_critique())
    return results
