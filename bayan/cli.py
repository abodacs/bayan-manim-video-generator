import shutil
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from bayan.generator.llm_client import LLMClient
from bayan.orchestrator import WorkflowOrchestrator
from bayan.planner.service import run_planning_pipeline
from bayan.renderer.executor import RenderError, execute_manim_script
from bayan.templates.catalogue import get_template_catalogue

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
        typer.echo(f"{slug:<28} {meta['arabic_title']:<22} {meta['purpose']}")


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
    source_file = Path(__file__).parent / "templates" / "fixtures" / f"{name.replace('-', '_')}.py"
    target_file = output_dir / f"{name.replace('-', '_')}.py"

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

    typer.echo("Rendering video via local Manim engine (this may take a moment)...")
    try:
        execute_manim_script(
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
    except Exception as e:
        typer.secho(f"Planning Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command(name="run")
def run(
    input: Annotated[
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
    """Executes the complete Bayan educator workflow."""
    orchestrator = WorkflowOrchestrator(input_path=input, output_dir=output, provider=provider)
    success = orchestrator.run()
    if not success:
        raise typer.Exit(code=1)