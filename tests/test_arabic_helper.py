import arabic_reshaper
from bidi.algorithm import get_display

from bayan.utils.arabic_helper import reshape_arabic_text


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