import arabic_reshaper
from bidi.algorithm import get_display
from manim import Text

from bayan.utils.arabic_helper import ArabicText, reshape_arabic_text, rtl_glyphs


def test_arabic_text_uses_native_pango_shaping():
    """
    ArabicText must preserve the source string and let Manim/Pango shape it.
    """
    text = ArabicText("مرحبا بالعالم", font="Noto Sans Arabic")

    assert isinstance(text, Text)
    assert text.raw_text == "مرحبا بالعالم"
    assert text.text == "مرحبابالعالم"
    assert text.disable_ligatures is False


def test_rtl_glyphs_are_ordered_from_right_to_left():
    """The reveal sequence starts at the visual right edge of Arabic text."""
    text = ArabicText("مرحبا بالعالم", font="Noto Sans Arabic")
    glyphs = rtl_glyphs(text)
    positions = [float(glyph.get_center()[0]) for glyph in glyphs.submobjects]

    assert positions == sorted(positions, reverse=True)


def test_reshape_arabic_text():
    """
    Verify that Arabic text is correctly reshaped and reordered for RTL display.
    """
    text = "مرحبا"
    expected = get_display(arabic_reshaper.reshape(text))

    assert reshape_arabic_text(text) == expected


def test_empty_string():
    """
    Empty strings should pass through unchanged.
    """
    assert reshape_arabic_text("") == ""


def test_english_text():
    """
    Basic English text should pass through gracefully.
    """
    text = "Hello"
    expected = get_display(arabic_reshaper.reshape(text))

    assert reshape_arabic_text(text) == expected
