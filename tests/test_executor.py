import pytest
import pathlib
from bayan.renderer.executor import execute_manim_script, RenderError

# كود مانيم سليم ويحتوي على حركة بسيطة لضمان إنتاج ملف فيديو .mp4
VALID_MANIM_CODE = """
from manim import *

class TestScene(Scene):
    def construct(self):
        square = Square()
        self.play(Create(square))
"""

# كود بايثون مكسور برمجياً لتجربة التقاط الأخطاء
INVALID_MANIM_CODE = """
from manim import *

class TestScene(Scene):
    def construct(self):
        square = Square(
        self.add(square
"""

# اختبار حقيقي لرندر اللغة العربية باستخدام موديول الـ arabic_helper الخاص بك
ARABIC_MANIM_CODE = """
from manim import *
# نستورد الكلاسات والدوال مباشرة من المسار الصحيح للمشروع
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
    اختبار نجاح الريندر:
    يتأكد من تمرير كود سليم، وإنتاج ملف MP4، ونقله بنجاح للمسار النهائي.
    """
    scene_name = "TestScene"
    expected_output_path = pathlib.Path.cwd() / "media" / f"{scene_name}.mp4"
    
    # التأكد من مسح أي ملف قديم متبقي من تجارب سابقة
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
    اختبار فشل الريندر:
    يتأكد من إطلاق RenderError عند تمرير كود مكسور، مع التحقق من وجود تفاصيل الخطأ.
    """
    scene_name = "BrokenScene"
    
    with pytest.raises(RenderError) as exc_info:
        execute_manim_script(INVALID_MANIM_CODE, scene_class_name=scene_name)
    
    error_message = str(exc_info.value)
    assert "Manim Render Failed" in error_message
    assert "SyntaxError" in error_message


def test_execute_manim_script_arabic_rendering():
    """
    اختبار رندر العربي:
    يتأكد من قدرة الـ Executor على رندر مشهد يحتوي على نصوص عربية واستيراد الـ helper بنجاح.
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