"""Lesson 02 — mobjects, positioning, grouping.

Run it:

    manim -ql scene.py Positioning
"""

from manim import *

BG = "#1C1C1C"


class Positioning(Scene):
    """Arrange three mobjects in a row and label them — no pixel guessing."""

    def construct(self):
        self.camera.background_color = BG

        circle = Circle(radius=0.8, color=BLUE)
        square = Square(side_length=1.4, color=YELLOW)
        triangle = Triangle(color=GREEN)

        # arrange() lays out a VGroup of compatible VMobjects with even spacing.
        row = VGroup(circle, square, triangle).arrange(RIGHT, buff=0.6)
        row.to_edge(UP, buff=1.0)

        # next_to places one mobject relative to another's bounding box.
        label = Text("positioned, not guessed", font_size=24)
        label.next_to(row, DOWN, buff=0.8)

        self.play(Create(row), run_time=1.2)
        self.wait(0.5)
        self.play(Write(label), run_time=0.8)
        self.wait(1.5)

        # Mixed cleanup (VGroup + Text) uses Group, not VGroup.
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
