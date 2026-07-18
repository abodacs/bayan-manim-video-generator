from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

# شحن متغيرات البيئة من ملف .env فوراً وقبل استيراد محتويات المشروع
load_dotenv()

from bayan.generator.llm_client import LLMClient
from bayan.renderer.executor import RenderError, execute_manim_script

app = typer.Typer(
    name="bayan",
    help="Bayan: Arabic AI-Powered Manim Video Generator",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Bayan CLI root command."""


@app.command(name="render")
def render(
    prompt: Annotated[
        str, typer.Argument(help="The prompt describing the video content.")
    ],
    output_path: Annotated[
        Path,
        typer.Option(
            "--output", "-o", help="Target path for the finished video."
        ),
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
    """
    Generates a Manim animation based on your educational prompt.
    """
    typer.echo(f"🚀 Initializing rendering pipeline for prompt: '{prompt}'")

    try:
        # Pass configuration dynamically to follow the decoupled provider interface
        client = LLMClient(api_key=api_key, base_url=base_url, model=model)
    except Exception as e:
        typer.secho(f"Configuration Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e

    typer.echo("🧠 Querying AI model for appropriate Manim code...")
    try:
        generated_code = client.generate_manim_code(prompt)
    except Exception as e:
        typer.secho(f"Generation Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e

    typer.echo("🎬 Rendering video via local Manim engine (this may take a moment)...")
    try:
        # Pass the output_path directly to eliminate race conditions
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
        f"🎉 Success! Video successfully compiled and saved to: {output_path.resolve()}",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()