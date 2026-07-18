import pytest

from bayan.renderer.executor import RenderError, execute_manim_script

# Valid Manim code snippet containing a simple animation to guarantee .mp4 output generation
VALID_MANIM_CODE = """
from manim import *

class TestScene(Scene):
    def construct(self):
        square = Square()
        self.play(Create(square))
"""

# Invalid Python/Manim code snippet designed to test error handling and parsing
INVALID_MANIM_CODE = """
from manim import *

class TestScene(Scene):
    def construct(self):
        square = Square(
        self.add(square
"""

# Integration test snippet for Arabic rendering using the custom arabic_helper module
ARABIC_MANIM_CODE = """
from manim import *
# Import classes and functions directly from the project package path
from bayan.utils.arabic_helper import ArabicText, rtl_glyphs

class ArabicTestScene(Scene):
    def construct(self):
        title = ArabicText(
            "مرحبا بالحالم",
            font="Noto Sans Arabic",
            font_size=48,
        )
        glyphs = rtl_glyphs(title)
        self.play(Write(glyphs))
        self.wait(1)
"""


def test_execute_manim_script_success(tmp_path):
    """
    Test successful execution of Manim script rendering:
    Verifies valid code execution and atomic generation at the requested output path.
    """
    scene_name = "TestScene"
    target_output = tmp_path / f"{scene_name}.mp4"

    # Pass the target destination explicitly to match the updated executor contract
    output_path = execute_manim_script(
        VALID_MANIM_CODE, output_path=target_output, scene_class_name=scene_name
    )

    assert output_path == target_output
    assert output_path.exists()
    assert output_path.suffix == ".mp4"


def test_execute_manim_script_syntax_error(tmp_path):
    """
    Test render failure handling:
    Verifies that RenderError is raised when broken code is provided
    and contains traceback details.
    """
    scene_name = "BrokenScene"
    target_output = tmp_path / f"{scene_name}.mp4"

    with pytest.raises(RenderError) as exc_info:
        execute_manim_script(
            INVALID_MANIM_CODE,
            output_path=target_output,
            scene_class_name=scene_name,
        )

    error_message = str(exc_info.value)
    assert "Manim Render Failed" in error_message
    assert "SyntaxError" in error_message


def test_execute_manim_script_arabic_rendering(tmp_path):
    """
    Test Arabic rendering integration:
    Verifies that the executor can successfully render scenes
    containing Arabic text using internal project helpers.
    """
    scene_name = "ArabicTestScene"
    target_output = tmp_path / f"{scene_name}.mp4"

    # Pass the target destination explicitly to match the updated executor contract
    output_path = execute_manim_script(
        ARABIC_MANIM_CODE,
        output_path=target_output,
        scene_class_name=scene_name,
    )

    assert output_path == target_output
    assert output_path.exists()
    assert output_path.suffix == ".mp4"
