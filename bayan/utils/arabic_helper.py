import arabic_reshaper
from bidi.algorithm import get_display
from manim import Text, VGroup


def reshape_arabic_text(raw_text: str) -> str:
    """
    Takes a raw Arabic string, applies reshaping ligatures, and resolves
    bi-directional flow for correct RTL rendering.
    """
    if not raw_text.strip():
        return raw_text

    # 1. Reshape the letters
    reshaped = arabic_reshaper.reshape(raw_text)
    # 2. Apply the BiDi algorithm to reverse ordering correctly
    bidi_text = get_display(reshaped)
    return bidi_text


class ArabicText(Text):
    """Text that delegates Arabic shaping and RTL layout to Manim/Pango."""

    def __init__(self, text: str, font: str = "Noto Sans Arabic", **kwargs):
        self.raw_text = text
        super().__init__(text, font=font, **kwargs)


def rtl_glyphs(text: Text) -> VGroup:
    """Return a text's glyphs in visual right-to-left order."""
    return VGroup(*reversed(text.submobjects))
