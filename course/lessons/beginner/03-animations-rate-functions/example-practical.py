"""Lesson 03 — practical: compare rate functions side by side.

Two dots cross the screen; one linear (constant speed), one smooth (ease in/out).
Seeing them together is the fastest way to internalise rate functions.

    manim -ql example-practical.py RateCompare
"""

from manim import *

BG = "#1C1C1C"


class RateCompare(Scene):
    """Linear vs smooth: same distance, different feel."""

    def construct(self):
        self.camera.background_color = BG

        linear_dot = Dot(color=YELLOW).to_edge(LEFT)
        smooth_dot = Dot(color=BLUE).to_edge(LEFT)
        VGroup(linear_dot, smooth_dot).arrange(UP, buff=1.0)

        labels = VGroup(
            Text("linear", font_size=22, color=YELLOW),
            Text("smooth", font_size=22, color=BLUE),
        )
        labels[0].next_to(linear_dot, LEFT, buff=0.3)
        labels[1].next_to(smooth_dot, LEFT, buff=0.3)

        target = RIGHT * 6
        self.play(linear_dot.animate.shift(target), rate_func=linear, run_time=2.0)
        self.wait(0.5)
        linear_dot.to_edge(LEFT)
        self.play(smooth_dot.animate.shift(target), rate_func=smooth, run_time=2.0)
        self.wait(1.0)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
