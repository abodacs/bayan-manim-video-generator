"""Lesson 01 — practical example: a reusable title card.

A title card is one of the first things you will build. Keep it to one beat at a
time and always pause after a reveal so the viewer can read it.

    manim -ql example-practical.py TitleCard
    manim -ql --format=png -s example-practical.py TitleCard   # single still
"""

from manim import *

BG = "#1C1C1C"


class TitleCard(Scene):
    """Fade in a title and subtitle, hold, then fade out."""

    def construct(self):
        self.camera.background_color = BG

        title = Text("Linear Algebra", font_size=52, weight=BOLD)
        subtitle = Text("vectors, spaces, and meaning", font_size=28)
        subtitle.set_opacity(0.7)

        # arrange() repositions the children in place; no assignment needed.
        VGroup(title, subtitle).arrange(DOWN, buff=0.4)

        self.play(FadeIn(title, shift=UP * 0.2), run_time=0.8)
        self.wait(0.8)
        self.play(FadeIn(subtitle, shift=UP * 0.1), run_time=0.6)
        self.wait(1.5)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
