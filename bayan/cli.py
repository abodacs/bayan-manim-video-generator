from pathlib import Path
import typer
from bayan.generator.llm_client import LLMClient
from bayan.renderer.executor import execute_manim_script, RenderError

app = typer.Typer(
    name="bayan",
    help="Bayan: Arabic AI-Powered Manim Video Generator",
    no_args_is_help=True
)

# Root callback forces Typer to treat `bayan` as a CLI group with subcommands
@app.callback()
def main():
    """Bayan CLI root command."""
    pass

@app.command(name="render")
def render(
    prompt: str = typer.Option(..., "--prompt", "-p", help="The prompt describing the video content."),
    output_path: Path = typer.Option(Path("./output.mp4"), "--output", "-o", help="Target path for the finished video."),
    api_key: str = typer.Option(None, "--api-key", "-k", help="OpenAI / Groq API Key.")
):
    """
    Generates a Manim animation based on your educational prompt.
    """
    typer.echo("🤖 Initializing LLM generation client...")
    try:
        client = LLMClient(api_key=api_key)
    except Exception as e:
        typer.secho(f"Configuration Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo("🧠 Querying AI model for appropriate Manim code...")
    try:
        generated_code = client.generate_manim_code(prompt)
    except Exception as e:
        typer.secho(f"Generation Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo("🎬 Rendering video via local Manim engine (this may take a moment)...")
    try:
        temp_video = execute_manim_script(generated_code, "GeneratedScene")
    except RenderError as re:
        typer.secho(f"Rendering Failed:\n{re}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred during execution: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_video.replace(output_path)
    
    typer.secho(f"🎉 Success! Video successfully compiled and saved to: {output_path.resolve()}", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()