"""Lesson 01 — your first Manim scene.

Run it (Manim CE >= 0.20.1):

    manim -ql scene.py HelloManim      # low-quality draft
    manim -qh scene.py HelloManim      # production quality (after review)
"""

from manim import *

BG = "#1C1C1C"  # Manim's default canvas colour, as a named constant


class HelloManim(Scene):
    """Write a title, draw a circle, pause after each reveal, then clean up."""

    def construct(self):
        self.camera.background_color = BG

        title = Text("Hello, Manim", font_size=56)
        circle = Circle(radius=1.2, color=BLUE)

        # Reveal the title, then hold so the viewer can read it.
        self.play(Write(title), run_time=1.5)
        self.wait(1.0)

        # Lift the title to make room, then create the circle.
        self.play(title.animate.to_edge(UP), run_time=0.8)
        self.play(Create(circle), run_time=1.0)
        self.wait(1.5)

        # Clean exit: fade every on-screen mobject together.
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
