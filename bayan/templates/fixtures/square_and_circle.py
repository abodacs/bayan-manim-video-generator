"""SquareAndCircle Arabic template using Manim CE."""

from manim import BLUE, GREEN, LEFT, UP, Circle, Create, Scene, Square, Write

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class SquareAndCircle(Scene):
    """Scene displaying shapes positioned relatively with Arabic label."""

    def construct(self) -> None:
        circle = Circle()
        circle.set_fill(GREEN, opacity=0.5)

        square = Square()
        square.set_fill(BLUE, opacity=0.5)

        square.next_to(circle, LEFT, buff=0.5)

        title = ArabicText("مربع ودائرة")
        title.to_edge(UP)

        self.play(Write(rtl_glyphs(title)))
        self.play(Create(square), Create(circle))
        self.wait(1)
