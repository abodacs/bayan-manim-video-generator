"""TransformCycle Arabic template using Manim CE."""

from manim import (
    BLUE,
    GREEN,
    RED,
    UP,
    Circle,
    Create,
    ReplacementTransform,
    Scene,
    Square,
    Triangle,
    Write,
)

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class TransformCycle(Scene):
    """Scene demonstrating shape lifecycle transitions with Arabic label."""

    def construct(self) -> None:
        square = Square(color=BLUE)
        circle = Circle(color=GREEN)
        triangle = Triangle(color=RED)

        title = ArabicText("دورة التحويل")
        title.to_edge(UP)

        self.play(Write(rtl_glyphs(title)))
        self.play(Create(square))
        self.play(ReplacementTransform(square, circle))
        self.play(ReplacementTransform(circle, triangle))
        self.wait(1)
