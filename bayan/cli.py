from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from bayan.generator.llm_client import LLMClient, LLMConfigError
from bayan.orchestrator import ManifestError, StageStatus, WorkflowOrchestrator
from bayan.pipeline.coder import LLMCoderProvider
from bayan.pipeline.provider import LLMPlanProvider
from bayan.pipeline.spine import LanguageProfile, run_generate
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


def _build_providers() -> tuple[LLMPlanProvider, LLMCoderProvider]:
    """Build the real provider adapters over one hardened client."""
    client = LLMClient()
    return LLMPlanProvider(client), LLMCoderProvider(client)


@app.command(name="generate")
def generate(
    prompt: Annotated[
        str,
        typer.Argument(help="Free-form Arabic lesson prompt."),
    ],
    profile: Annotated[
        LanguageProfile,
        typer.Option("--profile", "-p", help="Language profile for digits and dialect."),
    ] = LanguageProfile.msa_western,
    runs_root: Annotated[
        Path,
        typer.Option("--runs-root", help="Directory that holds generated runs."),
    ] = Path("./runs"),
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            help="Render quality; wired through by the render-quality sub-issue.",
        ),
    ] = "draft",
    vlm: Annotated[
        bool,
        typer.Option("--vlm", help="Enable the VLM critic (default off; critic lands later)."),
    ] = False,
) -> None:
    """Generate a lesson video from one free-form Arabic prompt."""
    try:
        planner, coder = _build_providers()
    except LLMConfigError as error:
        typer.secho(f"Configuration Error: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None

    typer.echo("Planning the lesson...")
    result = run_generate(
        prompt=prompt,
        profile=profile,
        runs_root=runs_root,
        planner=planner,
        coder=coder,
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


if __name__ == "__main__":
    app()
