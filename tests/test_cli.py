import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from bayan.cli import app
from bayan.renderer.executor import RenderError

runner = CliRunner()

@patch("bayan.cli.LLMClient")
@patch("bayan.cli.execute_manim_script")
def test_cli_render_success(mock_execute, mock_llm_client_class, tmp_path):
    """Test successful execution of `bayan render` command and output file moving."""
    # 1. Setup mock instance for LLMClient
    mock_client_instance = MagicMock()
    mock_client_instance.generate_manim_code.return_value = "class GeneratedScene(Scene): pass"
    mock_llm_client_class.return_value = mock_client_instance

    # 2. Create a dummy video file in the temporary path
    fake_video = tmp_path / "GeneratedScene.mp4"
    fake_video.write_text("dummy video content")
    mock_execute.return_value = fake_video

    output_file = tmp_path / "final_output.mp4"

    # 3. Direct invocation without subcommands
    result = runner.invoke(
        app,
        ["-p", "Draw a red circle", "-o", str(output_file)]
    )

    # 4. Assert clean execution exit code and successful file move
    assert result.exit_code == 0
    assert "Success! Video successfully compiled" in result.output
    assert output_file.exists()


@patch("bayan.cli.LLMClient")
@patch("bayan.cli.execute_manim_script")
def test_cli_render_failure_handling(mock_execute, mock_llm_client_class):
    """Test error handling when rendering fails and verify appropriate error output."""
    mock_client_instance = MagicMock()
    mock_client_instance.generate_manim_code.return_value = "broken code"
    mock_llm_client_class.return_value = mock_client_instance

    mock_execute.side_effect = RenderError("SyntaxError: invalid syntax")

    result = runner.invoke(
        app,
        ["-p", "Broken prompt"]
    )

    assert result.exit_code == 1
    assert "Rendering Failed" in result.output