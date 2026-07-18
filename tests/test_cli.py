from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bayan.cli import app
from bayan.renderer.executor import RenderError

runner = CliRunner()


@patch("bayan.cli.LLMClient")
@patch("bayan.cli.execute_manim_script")
def test_cli_render_success(mock_execute, mock_llm_client_class, tmp_path):
    """Test successful execution of `bayan render` command using positional argument."""
    # 1. Setup mock instance for LLMClient
    mock_client_instance = MagicMock()
    mock_client_instance.generate_manim_code.return_value = "class GeneratedScene(Scene): pass"
    mock_llm_client_class.return_value = mock_client_instance

    output_file = tmp_path / "final_output.mp4"

    # 2. Simulate the new atomic executor behavior: writing directly to output_path when invoked
    def side_effect_action(code_content, output_path, scene_class_name):
        output_path.write_text("dummy video content", encoding="utf-8")
        return output_path

    mock_execute.side_effect = side_effect_action

    # 3. Explicitly target the "render" subcommand followed by the positional prompt argument
    result = runner.invoke(app, ["render", "Draw a red circle", "-o", str(output_file)])

    # 4. Assert clean execution exit code, mock verification, and successful file existence
    assert result.exit_code == 0
    assert "Success! Video successfully compiled" in result.output
    assert output_file.exists()
    mock_execute.assert_called_once_with(
        code_content="class GeneratedScene(Scene): pass",
        output_path=output_file,
        scene_class_name="GeneratedScene",
    )


@patch("bayan.cli.LLMClient")
@patch("bayan.cli.execute_manim_script")
def test_cli_render_failure_handling(mock_execute, mock_llm_client_class):
    """Test error handling when rendering fails and verify appropriate error output."""
    mock_client_instance = MagicMock()
    mock_client_instance.generate_manim_code.return_value = "broken code"
    mock_llm_client_class.return_value = mock_client_instance

    mock_execute.side_effect = RenderError("SyntaxError: invalid syntax")

    # Target the "render" subcommand followed by the positional prompt argument
    result = runner.invoke(app, ["render", "Broken prompt"])

    assert result.exit_code == 1
    assert "Rendering Failed" in result.output
