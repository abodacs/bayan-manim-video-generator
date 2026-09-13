from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from bayan.generator.llm_client import LLMClient, LLMConfigError
from bayan.orchestrator import ManifestError, StageStatus, WorkflowOrchestrator
from bayan.pipeline.coder import LLMCoderProvider
from bayan.pipeline.models import DEFAULT_PROFILE
from bayan.pipeline.profiles import UnknownProfileError, get_profile
from bayan.pipeline.provider import LLMPlanProvider
from bayan.pipeline.records import iter_stage_records, status_label
from bayan.pipeline.rerun import RerunError, run_rerun
from bayan.pipeline.runs import (
    RUN_ARTIFACTS,
    failure_category,
    has_media,
    iter_run_dirs,
    load_run_summary,
    records_cost,
)
from bayan.pipeline.spine import run_generate
from bayan.planner.service import run_planning_pipeline
from bayan.renderer.executor import RenderError, render_scene_code
from bayan.templates.catalogue import fixture_filename, get_template_catalogue

app = typer.Typer(
    name="bayan",
    help="Bayan: Arabic AI-Powered Manim Video Generator",
    no_args_is_help=True,
)

template_app = typer.Typer(
    help="Manage Arabic template catalogue.",
    no_args_is_help=True,
)
app.add_typer(template_app, name="template")

runs_app = typer.Typer(
    help="Inspect past generate runs (read-only).",
    no_args_is_help=True,
)
app.add_typer(runs_app, name="runs")


def _dash(value: object) -> str:
    return "-" if value in (None, "") else str(value)


@runs_app.command(name="list")
def list_runs(
    runs_root: Annotated[
        Path,
        typer.Option("--runs-root", help="Directory that holds generated runs."),
    ] = Path("./runs"),
) -> None:
    """List past generate runs, ids sorted oldest to newest."""
    run_dirs = iter_run_dirs(runs_root)
    if not run_dirs:
        typer.echo("No runs yet: generate a lesson with `bayan generate`.")
        return

    typer.echo(
        f"{'RUN ID':<26} {'STATUS':<10} {'PROFILE':<18} {'MODEL':<16} "
        f"{'REPAIRS':>7} {'COST (USD)':>12} {'MEDIA':>6}"
    )
    skipped: list[str] = []
    for run_dir in run_dirs:
        summary = load_run_summary(run_dir)
        if summary is None:
            skipped.append(run_dir.name)
            continue
        cost = summary.get("total_cost_estimate_usd")
        cost_text = f"{float(cost):.4f}" if isinstance(cost, int | float) else "-"
        typer.echo(
            f"{run_dir.name:<26} {_dash(summary.get('status')):<10} "
            f"{_dash(summary.get('profile')):<18} {_dash(summary.get('model')):<16} "
            f"{_dash(summary.get('repairs_used')):>7} {cost_text:>12} "
            f"{'yes' if has_media(run_dir) else '-':>6}"
        )
    for name in skipped:
        typer.secho(
            f"Skipped {name}: no readable run.json (incomplete or foreign directory).",
            fg=typer.colors.YELLOW,
        )


@runs_app.command(name="show")
def show_run(
    run_id: Annotated[
        str,
        typer.Argument(help="Run id produced by bayan generate."),
    ],
    runs_root: Annotated[
        Path,
        typer.Option("--runs-root", help="Directory that holds generated runs."),
    ] = Path("./runs"),
) -> None:
    """Show one run's stage timeline, artifacts, costs, and lineage."""
    run_dir = runs_root / run_id
    if not run_dir.is_dir():
        typer.secho(
            f"Run '{run_id}' not found under {runs_root}. "
            "Use `bayan runs list` to see available runs.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)
    summary = load_run_summary(run_dir)
    if summary is None:
        typer.secho(
            f"Run '{run_id}' has no readable run.json summary; the run is incomplete.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Run: {summary.get('run_id', run_id)}")
    typer.echo(f"Status: {_dash(summary.get('status'))}")
    typer.echo(f"Profile: {_dash(summary.get('profile'))}")
    typer.echo(f"Quality: {_dash(summary.get('quality'))}")
    typer.echo(f"Model: {_dash(summary.get('model'))}")
    if summary.get("rerun_of"):
        typer.echo(f"Rerun of: {summary['rerun_of']}")
    typer.echo(f"Repairs used: {_dash(summary.get('repairs_used'))}")

    stages: dict[str, str] = summary.get("stages") or {}
    if stages:
        typer.echo("")
        typer.echo("Stage timeline:")
        for record in iter_stage_records(run_dir):
            typer.echo(
                f"  {record.stage:<10} {status_label(record.status):<10} "
                f"{_dash(record.created_at.isoformat())}"
            )
            if record.failure:
                typer.echo(f"    failure: {record.failure}")

    failed_stages = [name for name, status in stages.items() if status == "failed"]
    if failed_stages:
        typer.echo(f"Failing stage(s): {', '.join(failed_stages)}")
        for stage in failed_stages:
            category = failure_category(run_dir, stage)
            if category:
                typer.echo(f"Failure category ({stage}): {category}")
    if summary.get("failure"):
        typer.echo(f"Failure: {summary['failure']}")

    typer.echo("")
    typer.echo("Artifacts:")
    for artifact in RUN_ARTIFACTS:
        marker = "yes" if (run_dir / artifact).is_file() else "no"
        typer.echo(f"  {artifact:<12} {marker}")

    records_total = records_cost(run_dir)
    summary_total = summary.get("total_cost_estimate_usd")
    typer.echo("")
    if records_total is not None:
        typer.echo(f"Total cost estimate (from records): {records_total:.4f} USD")
        if isinstance(summary_total, int | float):
            summary_cost = float(summary_total)
            if abs(records_total - summary_cost) > 1e-6:
                typer.echo(
                    f"Note: run.json reports {summary_cost:.4f} USD; "
                    "the stage records disagree and were preferred."
                )
    else:
        typer.echo(f"Total cost estimate: {_dash(summary_total)} USD")


class TyperStageReporter:
    """Render orchestrator progress events on the terminal."""

    def stage_skipped(self, name: str) -> None:
        typer.echo(f"Skipping completed stage: {name}")

    def stage_started(self, name: str) -> None:
        typer.echo(f"Executing stage: {name}...")

    def stage_finished(self, name: str, status: str, error: str | None) -> None:
        if status == "completed":
            typer.secho(f"Stage '{name}': SUCCESS", fg=typer.colors.GREEN)
        elif status == "stub":
            typer.secho(f"Stage '{name}' (STUB): {error}", fg=typer.colors.YELLOW)
        else:
            typer.secho(f"Stage '{name}' FAILED: {error}", fg=typer.colors.RED)

    def workflow_finished(self, status: StageStatus) -> None:
        if status == "completed":
            typer.secho("\nWorkflow completed successfully!", fg=typer.colors.GREEN, bold=True)
        elif status == "stub":
            typer.secho(
                "\nWorkflow incomplete: some stages are not implemented yet (stubs). "
                "See manifest.json and lesson_review_packet.md for details.",
                fg=typer.colors.YELLOW,
                bold=True,
            )
        else:
            typer.secho(
                "\nWorkflow failed. See manifest.json for the failing stage.",
                fg=typer.colors.RED,
                bold=True,
            )


@app.callback()
def main() -> None:
    """Bayan CLI root command."""
    load_dotenv()


@template_app.command(name="list")
def list_templates() -> None:
    """List all available Arabic templates in the catalogue."""
    catalogue = get_template_catalogue()
    typer.echo(f"{'NAME':<28} {'ARABIC TITLE':<22} {'PURPOSE'}")
    typer.echo("-" * 85)
    for slug, meta in catalogue.items():
        typer.echo(f"{slug:<28} {str(meta['arabic_title']):<22} {meta['purpose']}")


@template_app.command(name="copy")
def copy_template(
    name: Annotated[str, typer.Argument(help="Name of the template to copy.")],
    output_dir: Annotated[
        Path,
        typer.Option("--output", "-o", help="Target output directory."),
    ],
) -> None:
    """Copy an approved template into a target directory."""
    catalogue = get_template_catalogue()
    if name not in catalogue:
        typer.secho(f"Error: Unknown template '{name}'.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    output_dir.mkdir(parents=True, exist_ok=True)
    source_file = Path(__file__).parent / "templates" / "fixtures" / fixture_filename(name)
    target_file = output_dir / fixture_filename(name)

    if not source_file.exists():
        typer.secho(f"Error: Source file for template '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    shutil.copy(source_file, target_file)
    typer.secho(f"Copied template '{name}' to {target_file}", fg=typer.colors.GREEN)


@app.command(name="render")
def render(
    prompt: Annotated[str, typer.Argument(help="The prompt describing the video content.")],
    output_path: Annotated[
        Path,
        typer.Option("--output", "-o", help="Target path for the finished video."),
    ] = Path("./output.mp4"),
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            help="Custom API Key to override environment variable.",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Custom Base URL to override environment variable."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Custom model name to override environment variable."),
    ] = None,
) -> None:
    """Generates a Manim animation based on your educational prompt."""
    typer.echo(f"Initializing rendering pipeline for prompt: '{prompt}'")

    try:
        client = LLMClient(api_key=api_key, base_url=base_url, model=model)
    except Exception as e:
        typer.secho(f"Configuration Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e

    typer.echo("Querying AI model for appropriate Manim code...")
    try:
        generated_code = client.generate_manim_code(prompt)
    except Exception as e:
        typer.secho(f"Generation Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e

    typer.echo("Rendering video in the isolated Manim worker (this may take a moment)...")
    try:
        render_scene_code(
            code_content=generated_code,
            output_path=output_path,
            scene_class_name="GeneratedScene",
        )
    except RenderError as re:
        typer.secho(f"Rendering Failed:\n{re}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from re
    except Exception as e:
        typer.secho(
            f"An unexpected error occurred during execution: {e}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1) from e

    typer.secho(
        f"Success! Video successfully compiled and saved to: {output_path.resolve()}",
        fg=typer.colors.GREEN,
    )


@app.command(name="plan")
def plan(
    input_path: Annotated[
        Path,
        typer.Option("--input", "-i", help="Path to input lesson JSON file."),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output", "-o", help="Target output directory for run files."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite output directory if it exists."),
    ] = False,
) -> None:
    """Turns a natural-language request into a typed Scene plan."""
    try:
        run_planning_pipeline(input_path=input_path, output_dir=output_dir, force=force)
        typer.secho(
            f"Scene plan generated successfully in: {output_dir.resolve()}",
            fg=typer.colors.GREEN,
        )
    except FileNotFoundError as e:
        typer.secho(f"Input File Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e
    except ValueError as e:  # json.JSONDecodeError is a ValueError subclass
        typer.secho(f"JSON Parse / Validation Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e
    except FileExistsError as e:
        typer.secho(f"Output Directory Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e
    except Exception as e:
        typer.secho(f"Planning Error: {type(e).__name__}: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command(name="run")
def run(
    input_path: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Path to the lesson input JSON file.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path to the output run directory.",
        ),
    ],
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            "-p",
            help="LLM provider for planning.",
        ),
    ] = "fake",
) -> None:
    """Executes the complete Bayan educator workflow.

    Exit codes: 0 when every implemented stage completed (not-yet-implemented
    stub stages are reported as incomplete, not fatal); 1 when any stage
    failed.
    """
    try:
        orchestrator = WorkflowOrchestrator(
            input_path=input_path, output_dir=output, provider=provider
        )
    except ManifestError as e:
        typer.secho(f"Manifest Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e
    except ValueError as e:
        typer.secho(f"Provider Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e

    success = orchestrator.run(reporter=TyperStageReporter())
    if not success:
        raise typer.Exit(code=1)


def _build_providers() -> tuple[LLMPlanProvider, LLMCoderProvider, LLMCoderProvider]:
    """Build the real provider adapters over one hardened client."""
    client = LLMClient()
    coder = LLMCoderProvider(client)
    return LLMPlanProvider(client), coder, coder


@app.command(name="generate")
def generate(
    prompt: Annotated[
        str,
        typer.Argument(help="Free-form Arabic lesson prompt."),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Language profile for digits and dialect."),
    ] = DEFAULT_PROFILE,
    runs_root: Annotated[
        Path,
        typer.Option("--runs-root", help="Directory that holds generated runs."),
    ] = Path("./runs"),
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            help="Render quality: draft, medium_quality, high_quality, highest_quality.",
        ),
    ] = "draft",
    vlm: Annotated[
        bool,
        typer.Option("--vlm", help="Record a VLM critique pass (stub; default off)."),
    ] = False,
) -> None:
    """Generate a lesson video from one free-form Arabic prompt."""
    try:
        get_profile(profile)
    except UnknownProfileError as error:
        typer.secho(f"Configuration Error: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None

    try:
        planner, coder, repairer = _build_providers()
    except LLMConfigError as error:
        typer.secho(f"Configuration Error: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None

    typer.echo("Planning the lesson...")
    result = run_generate(
        prompt=prompt,
        profile=profile,
        quality=quality,
        vlm=vlm,
        runs_root=runs_root,
        planner=planner,
        coder=coder,
        repairer=repairer,
    )

    if result.status != "completed":
        typer.secho(f"Generation failed: {result.failure}", fg=typer.colors.RED)
        typer.secho(f"Run directory: {result.run_dir}", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    typer.secho(
        f"Success! Run directory: {result.run_dir} "
        f"(cost estimate: ${result.total_cost_estimate_usd:.4f})",
        fg=typer.colors.GREEN,
    )


@app.command(name="rerun")
def rerun(
    run_id: Annotated[
        str,
        typer.Argument(help="Run id produced by bayan generate."),
    ],
    runs_root: Annotated[
        Path,
        typer.Option("--runs-root", help="Directory that holds generated runs."),
    ] = Path("./runs"),
) -> None:
    """Re-render a past run from its cached plan and code.

    No API key is required: rerun makes zero LLM calls.
    """
    try:
        result = run_rerun(run_id=run_id, runs_root=runs_root)
    except RerunError as error:
        typer.secho(f"Rerun Error: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None

    if result.status != "completed":
        typer.secho(f"Rerun failed: {result.failure}", fg=typer.colors.RED)
        typer.secho(f"Run directory: {result.run_dir}", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    typer.secho(
        f"Success! Rerun directory: {result.run_dir}",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()
