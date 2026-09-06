"""CreateCircle Arabic template using Manim CE."""

from manim import PINK, UP, Circle, Create, Scene, Write

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class CreateCircle(Scene):
    """Simple scene displaying a created pink circle with Arabic label."""

    def construct(self) -> None:
        circle = Circle()
        circle.set_fill(PINK, opacity=0.5)
        circle.flip()

        # Create the Arabic text label
        title = ArabicText("إنشاء دائرة")
        title.next_to(circle, UP)

        self.play(Create(circle), Write(rtl_glyphs(title)))
        self.wait(1)
