"""DifferentRotations Arabic template using Manim CE."""

from manim import BLUE, LEFT, PI, RED, RIGHT, UP, Create, Rotate, Scene, Square, Write

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class DifferentRotations(Scene):
    """Scene comparing .animate rotation vs explicit Rotate animation with Arabic label."""

    def construct(self) -> None:
        left_square = Square(color=BLUE).shift(LEFT * 2)
        right_square = Square(color=RED).shift(RIGHT * 2)

        title = ArabicText("مقارنة الدوران")
        title.to_edge(UP)

        self.play(Write(rtl_glyphs(title)))
        self.play(Create(left_square), Create(right_square))
        self.play(
            left_square.animate.rotate(PI / 4),
            Rotate(right_square, angle=PI / 4),
        )
        self.wait(1)
