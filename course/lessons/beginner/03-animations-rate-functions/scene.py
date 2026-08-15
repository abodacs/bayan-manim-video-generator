"""Lesson 03 — creation, visibility, transform, rate functions.

Run it:

    manim -ql scene.py AnimationChoices
"""

from manim import *

BG = "#1C1C1C"


class AnimationChoices(Scene):
    """Create, FadeIn, Transform — each chosen for what it means."""

    def construct(self):
        self.camera.background_color = BG

        circle = Circle(radius=1.0, color=BLUE).shift(LEFT * 2)
        square = Square(side_length=1.8, color=YELLOW).shift(RIGHT * 2)

        # Create builds the stroke; FadeIn reveals without drawing.
        self.play(Create(circle), run_time=1.0)
        self.wait(0.5)
        self.play(FadeIn(square, shift=DOWN * 0.3), run_time=0.8)
        self.wait(0.8)

        # Transform morphs one mobject into another — it shows a relationship.
        self.play(Transform(circle, Square(color=BLUE)), run_time=1.5)
        self.wait(1.0)

        # A rate function expresses intent: there_and_back = a passing emphasis.
        self.play(
            circle.animate.shift(RIGHT * 0.5),
            rate_func=there_and_back,
            run_time=1.0,
        )
        self.wait(1.0)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
