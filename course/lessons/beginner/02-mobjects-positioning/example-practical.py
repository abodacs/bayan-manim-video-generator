"""Lesson 02 — practical: a labeled geometric diagram.

A right triangle with its right-angle marker and a leg label. This is the shape
of most "geometry before algebra" explanations.

    manim -ql example-practical.py RightTriangle
"""

from manim import *

BG = "#1C1C1C"


class RightTriangle(Scene):
    """Build a right triangle from points and annotate one leg."""

    def construct(self):
        self.camera.background_color = BG

        a = np.array([-1.5, -1.0, 0.0])
        b = np.array([1.5, -1.0, 0.0])
        c = np.array([-1.5, 1.5, 0.0])
        tri = Polygon(a, b, c, color=BLUE)

        right_angle = RightAngle(Line(a, b), Line(a, c), length=0.4, color=YELLOW)
        leg = Tex(r"a", font_size=36).next_to(Line(a, b), DOWN, buff=0.2)

        self.play(Create(tri), run_time=1.0)
        self.wait(0.5)
        self.play(Create(right_angle), Write(leg), run_time=0.8)
        self.wait(1.5)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
