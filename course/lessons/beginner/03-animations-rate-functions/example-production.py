"""Lesson 03 — production: a build-up with composition + timing.

Demonstrates LaggedStart (staggered reveals), AnimationGroup (simultaneous),
explicit run_time on every beat, subcaptions, and a deliberate key pause.

    manim -qh example-production.py BuildUp
"""

from manim import *

BG = "#1C1C1C"
PRIMARY = "#58C4DD"
ACCENT = "#FFFF00"
INK = "#FFFFFF"


class BuildUp(Scene):
    """Grow a row of boxes, then highlight the last as the 'result'."""

    def construct(self):
        self.camera.background_color = BG

        boxes = VGroup(*[Square(side_length=0.9, color=PRIMARY) for _ in range(4)])
        boxes.arrange(RIGHT, buff=0.4)

        # LaggedStart staggers repeated appearances — clarifies "a sequence".
        self.play(LaggedStart(*[GrowFromCenter(b) for b in boxes], lag_ratio=0.2))
        self.add_subcaption("build the sequence", duration=1.2)
        self.wait(0.6)

        # The last box becomes the result; one strong focal highlight.
        self.play(
            boxes[3].animate.set_color(ACCENT).scale(1.15),
            run_time=0.8,
        )
        self.add_subcaption("and the result emerges", duration=1.0)
        self.wait(2.0)  # key pause

        caption = Text("the fourth term is special", font_size=24, color=INK)
        caption.next_to(boxes, DOWN, buff=0.6)
        self.play(Write(caption), run_time=0.8)
        self.wait(1.5)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
