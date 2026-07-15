import arabic_reshaper
from bidi.algorithm import get_display
from manim import Text


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
    def __init__(self, text: str, font: str = "Amiri", **kwargs):
        processed_text = reshape_arabic_text(text)

        print("Original :", repr(text))
        print("Processed:", repr(processed_text))

        kwargs.setdefault("disable_ligatures", True)
        super().__init__(processed_text, font=font, **kwargs)