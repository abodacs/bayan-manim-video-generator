"""Lesson 04 — a planned scene: build-up arc, timed beats, clean exit.

Written from plan.md (this directory): seed -> perturb -> generalise,
every beat with run_time and a deliberate wait after each reveal.

    manim -ql scene.py PlannedArc
"""

from manim import *

BG = "#1C1C1C"
PRIMARY = "#58C4DD"
ACCENT = "#FFFF00"


class PlannedArc(Scene):
    """A build-up arc in miniature, transcribed from the beat table."""

    def construct(self):
        self.camera.background_color = BG

        # Beat 1 — seed: one familiar dot. (rt=0.5, wait=0.5)
        dot = Dot(radius=0.25, color=PRIMARY).shift(LEFT * 2)
        self.play(FadeIn(dot), run_time=0.5)
        self.wait(0.5)

        # Beat 2 — perturb: a second, different dot joins. (rt=0.8, wait=0.8)
        dot2 = Dot(radius=0.25, color=ACCENT).shift(RIGHT * 2)
        self.play(Create(dot2), run_time=0.8)
        self.wait(0.8)

        # Beat 3 — generalise: both become the same shape. (rt=1.5, wait=1.0)
        self.play(Transform(dot, Square(side_length=0.5, color=PRIMARY)), run_time=1.5)
        self.wait(1.0)

        # Beat 4 — key insight: the caption IS the payoff. (rt=1.5, wait=2.5)
        caption = Text("same rule, different size", font_size=28)
        caption.next_to(Group(dot, dot2), DOWN, buff=0.8)
        self.play(Write(caption), run_time=1.5)
        self.wait(2.5)

        # Beat 5 — clean exit. (rt=0.6)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
