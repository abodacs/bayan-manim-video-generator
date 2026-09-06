"""AnimatedSquareToCircle Arabic template using Manim CE."""

from manim import BLUE, PI, UP, Circle, Create, ReplacementTransform, Scene, Square, Write

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class AnimatedSquareToCircle(Scene):
    """Scene animating method calls using .animate syntax with Arabic label."""

    def construct(self) -> None:
        circle = Circle()
        square = Square()
        square.set_fill(BLUE, opacity=0.5)

        title = ArabicText("تحريك المربع إلى دائرة")
        title.to_edge(UP)

        self.play(Write(rtl_glyphs(title)))
        self.play(Create(square))
        self.play(square.animate.rotate(PI / 4))
        self.play(ReplacementTransform(square, circle))
        self.wait(1)
