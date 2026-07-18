# Manim loads scene files as standalone modules and puts the file's own
# directory on sys.path (not the project root), so we import the sibling
# module directly rather than via the `bayan.utils` package path.
from arabic_helper import ArabicText, rtl_glyphs
from manim import LaggedStart, Scene, Write


class ArabicSanityCheck(Scene):
    """
    Integration visual test for Arabic RTL rendering.

    Run this scene and verify that:
    - Arabic letters are connected.
    - Text flows from right to left.
    """

    def construct(self):
        title = ArabicText(
            "مرحبا بالعالم",
            font="Noto Sans Arabic",
            font_size=48,
        )

        glyphs = rtl_glyphs(title)
        self.play(
            LaggedStart(
                *(Write(glyph) for glyph in glyphs.submobjects),
                lag_ratio=0.15,
                run_time=1.5,
            )
        )
        self.wait(1)
