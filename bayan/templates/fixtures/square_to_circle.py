"""SquareToCircle Arabic template using Manim CE."""

from manim import BLUE, GREEN, UP, Circle, Create, Scene, Square, Transform, Write

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class SquareToCircle(Scene):
    """Scene demonstrating interpolation between shapes with Arabic label."""

    def construct(self) -> None:
        circle = Circle()
        circle.set_fill(GREEN, opacity=0.5)

        square = Square()
        square.set_fill(BLUE, opacity=0.5)

        title = ArabicText("تحويل المربع إلى دائرة")
        title.to_edge(UP)

        self.play(Write(rtl_glyphs(title)))
        self.play(Create(square))
        self.play(Transform(square, circle))
        self.wait(1)
