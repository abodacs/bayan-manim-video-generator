"""Build and run the known-good Arabic scene in an isolated container."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

DEFAULT_IMAGE = "bayan/manim-smoke:0.20.1"
DEFAULT_OUTPUT_ROOT = Path("artifacts/container-smoke")


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


def main(argv: Sequence[str] | None = None) -> int:
    """Build, render, validate, and report the smoke run."""
    args = parser().parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from bayan.renderer.smoke import SmokeConfig, SmokeError, SmokeRunner

    runner = SmokeRunner(
        SmokeConfig(
            image=args.image,
            output_root=args.output,
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

    print(f"Smoke render succeeded. Run directory: {result.run_directory}")
    print(f"Video: {result.video}")
    print(f"Preview: {result.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
