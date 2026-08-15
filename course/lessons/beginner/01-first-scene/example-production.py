"""Lesson 01 — production example: every core convention, applied.

This scene is small but obeys the conventions the rest of the course enforces:
named semantic colours, opacity layering (primary / context / structure), an
explicit pause after every reveal, a subcaption per beat, and a Group cleanup.

    manim -qh example-production.py ConventionsDemo
"""

from manim import *

# Shared, stable constants (see scene-planning.md "Cross-Scene Consistency").
BG = "#1C1C1C"
PRIMARY = "#58C4DD"  # the thing being explained
CONTEXT = "#FFFFFF"  # supporting text
ACCENT = "#FFFF00"  # the key result / focus


class ConventionsDemo(Scene):
    """Show one concept: a shape and its label, with disciplined timing."""

    def construct(self):
        self.camera.background_color = BG

        shape = Square(side_length=2.0, color=PRIMARY, fill_opacity=0.25)
        shape.set_stroke(width=6)
        label = Text("a square", font_size=28, color=CONTEXT).next_to(shape, DOWN, buff=0.4)

        # Dimmed structural guide (opacity ~0.4) sits behind the focus.
        guide = SurroundingRectangle(shape, color=ACCENT, buff=0.2)
        guide.set_opacity(0.4)

        self.play(Create(shape), run_time=0.8)
        self.add_subcaption("create the shape", duration=0.8)
        self.wait(0.5)

        self.play(FadeIn(label), run_time=0.6)
        self.add_subcaption("label it", duration=0.6)
        self.wait(0.5)

        # Highlight is the single strong focal point at the "aha" beat.
        self.play(Create(guide), run_time=0.6)
        self.add_subcaption("and frame the key idea", duration=0.8)
        self.wait(2.0)  # the key pause: let the idea sink in

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
