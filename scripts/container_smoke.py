"""Build and run the known-good Arabic scene in an isolated container."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

DEFAULT_IMAGE = "bayan/manim-smoke:0.20.1"
DEFAULT_OUTPUT_ROOT = Path("artifacts/container-smoke")


class _SeamRenderPreferences:
    """Render preferences for the worker-seam check."""

    quality = "low_quality"


class _SeamScenePlan:
    """Minimal scene-plan payload driving the RenderJobRunner seam check.

    This entrypoint runs on a bare CI interpreter without the project
    dependencies installed, so the check satisfies the runner's structural
    PlanLike protocol directly instead of importing the pydantic planner
    models.
    """

    def __init__(self, template: str) -> None:
        self.selected_template = template
        self.provider_fingerprint = "container-smoke-worker-seam"
        self.render_settings = _SeamRenderPreferences()


def parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the smoke runner."""
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image tag to build and run.")
    result.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output directory root. A fresh run directory is created inside it.",
    )
    result.add_argument(
        "--skip-build",
        action="store_true",
        help="Use an existing image instead of building it.",
    )
    result.add_argument("--build-timeout", type=int, default=900, help="Build timeout in seconds.")
    result.add_argument(
        "--render-timeout", type=int, default=180, help="Render and validation timeout in seconds."
    )
    result.add_argument(
        "--max-log-bytes",
        type=int,
        default=1_048_576,
        help="Maximum captured worker output per phase.",
    )
    return result


def run_render_job_seam_check(image: str, output_root: Path) -> Path:
    """Render one catalogue fixture through RenderJobRunner against the image.

    The unit tests fake the Docker boundary, so this exercises the worker
    seam end to end: the mount mapping, the media_dir layout under the
    fresh run directory, and the PNG naming that those fakes assume.
    """
    from bayan.renderer.executor import RenderJobRunner
    from bayan.renderer.smoke import SmokeError, validate_png
    from bayan.templates.catalogue import get_template_catalogue

    slug = sorted(get_template_catalogue())[0]
    job_dir = output_root / "render-job-seam"
    # run_job raises RenderError on any failure, so returning means success.
    RenderJobRunner(image=image).run_job(_SeamScenePlan(slug), output_dir=job_dir)

    video = job_dir / "draft.mp4"
    preview = job_dir / "preview.png"
    if not video.is_file() or video.stat().st_size == 0:
        raise SmokeError(f"The render job succeeded but produced no draft.mp4 in {job_dir}.")
    validate_png(preview)

    record = json.loads((job_dir / "render_job.json").read_text(encoding="utf-8"))
    if record.get("status") != "succeeded":
        raise SmokeError(f"render_job.json records status {record.get('status')!r}.")
    missing = [key for key in ("image", "settings", "fixture_hash") if not record.get(key)]
    if missing:
        raise SmokeError(f"render_job.json lacks reproducibility evidence: {', '.join(missing)}.")

    # The worker's writable mount must hold the media layout the test fakes
    # assume: media/video/<Class>.mp4 and media/preview/<Class>*.png.
    run_root = job_dir / "render-runs"
    if not list(run_root.glob("run*/media/video/**/*.mp4")):
        raise SmokeError(f"No worker MP4 under {run_root} (expected media/video/).")
    if not list(run_root.glob("run*/media/preview/**/*.png")):
        raise SmokeError(f"No worker PNG under {run_root} (expected media/preview/).")
    return job_dir


def main(argv: Sequence[str] | None = None) -> int:
    """Build, render, validate, and report the smoke run."""
    args = parser().parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from bayan.renderer.executor import RenderError
    from bayan.renderer.smoke import SmokeConfig, SmokeError, SmokeRunner

    output_root = args.output if args.output.is_absolute() else project_root / args.output
    runner = SmokeRunner(
        SmokeConfig(
            image=args.image,
            output_root=output_root,
            skip_build=args.skip_build,
            build_timeout=args.build_timeout,
            render_timeout=args.render_timeout,
            max_log_bytes=args.max_log_bytes,
        )
    )
    try:
        result = runner.run()
    except (OSError, SmokeError) as error:
        if runner.run_directory is not None:
            print(f"Smoke render failed. Run directory: {runner.run_directory}", file=sys.stderr)
        print(f"Smoke render failed: {error}", file=sys.stderr)
        return 1

    try:
        seam_dir = run_render_job_seam_check(args.image, output_root)
    except (OSError, SmokeError, RenderError) as error:
        print(f"Render job seam check failed: {error}", file=sys.stderr)
        return 1

    print(f"Smoke render succeeded. Run directory: {result.run_directory}")
    print(f"Video: {result.video}")
    print(f"Preview: {result.preview}")
    print(f"Render job seam check succeeded. Job directory: {seam_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
