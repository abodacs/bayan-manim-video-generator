import pytest
import pathlib
from bayan.renderer.executor import execute_manim_script, RenderError

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

def test_execute_manim_script_success():
    """
    Test successful execution of Manim script rendering:
    Verifies valid code execution, MP4 generation, and moving to final destination path.
    """
    scene_name = "TestScene"
    expected_output_path = pathlib.Path.cwd() / "media" / f"{scene_name}.mp4"
    
    # Ensure cleanup of any leftover output file from previous runs
    if expected_output_path.exists():
        expected_output_path.unlink()

    try:
        output_path = execute_manim_script(VALID_MANIM_CODE, scene_class_name=scene_name)
        
        assert output_path == expected_output_path
        assert output_path.exists()
        assert output_path.suffix == ".mp4"
        
    finally:
        if expected_output_path.exists():
            expected_output_path.unlink()


def test_execute_manim_script_syntax_error():
    """
    Test render failure handling:
    Verifies that RenderError is raised when broken code is provided and contains traceback details.
    """
    scene_name = "BrokenScene"
    
    with pytest.raises(RenderError) as exc_info:
        execute_manim_script(INVALID_MANIM_CODE, scene_class_name=scene_name)
    
    error_message = str(exc_info.value)
    assert "Manim Render Failed" in error_message
    assert "SyntaxError" in error_message


def test_execute_manim_script_arabic_rendering():
    """
    Test Arabic rendering integration:
    Verifies that the executor can successfully render scenes containing Arabic text using internal project helpers.
    """
    scene_name = "ArabicTestScene"
    expected_output_path = pathlib.Path.cwd() / "media" / f"{scene_name}.mp4"
    
    if expected_output_path.exists():
        expected_output_path.unlink()

    try:
        output_path = execute_manim_script(ARABIC_MANIM_CODE, scene_class_name=scene_name)
        
        assert output_path == expected_output_path
        assert output_path.exists()
        assert output_path.suffix == ".mp4"
        
    finally:
        if expected_output_path.exists():
            expected_output_path.unlink()