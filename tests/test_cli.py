from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bayan.cli import app
from bayan.renderer.executor import RenderError

runner = CliRunner()


@patch("bayan.cli.render_scene_code")
@patch("bayan.cli.LLMClient")
def test_cli_render_success(mock_llm_client_class, mock_render, tmp_path):
    """Test successful execution of `bayan render` command using positional argument."""
    # 1. Setup mock instance for LLMClient
    mock_client_instance = MagicMock()
    mock_client_instance.generate_manim_code.return_value = "class GeneratedScene(Scene): pass"
    mock_llm_client_class.return_value = mock_client_instance

    output_file = tmp_path / "final_output.mp4"

    # 2. Simulate the worker render: writing the video to output_path when invoked
    def side_effect_action(code_content, output_path, scene_class_name):
        output_path.write_text("dummy video content", encoding="utf-8")
        return output_path

    mock_render.side_effect = side_effect_action

    # 3. Explicitly target the "render" subcommand followed by the positional prompt argument
    result = runner.invoke(app, ["render", "Draw a red circle", "-o", str(output_file)])

    # 4. Assert clean execution exit code, mock verification, and successful file existence
    assert result.exit_code == 0
    assert "Success! Video successfully compiled" in result.output
    assert output_file.exists()
    mock_render.assert_called_once_with(
        code_content="class GeneratedScene(Scene): pass",
        output_path=output_file,
        scene_class_name="GeneratedScene",
    )


@patch("bayan.cli.render_scene_code")
@patch("bayan.cli.LLMClient")
def test_cli_render_failure_handling(mock_llm_client_class, mock_render):
    """Test error handling when rendering fails and verify appropriate error output."""
    mock_client_instance = MagicMock()
    mock_client_instance.generate_manim_code.return_value = "broken code"
    mock_llm_client_class.return_value = mock_client_instance

    mock_render.side_effect = RenderError("Rendering the video failed: SyntaxError")

    # Target the "render" subcommand followed by the positional prompt argument
    result = runner.invoke(app, ["render", "Broken prompt"])

    assert result.exit_code == 1
    assert "Rendering Failed" in result.output
