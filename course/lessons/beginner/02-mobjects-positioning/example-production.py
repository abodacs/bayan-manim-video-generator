"""Lesson 02 — production: positioning with opacity hierarchy.

Demonstrates: named palette, primary/context/structure opacity layering,
arrange_in_grid, buff >= 0.5 at edges, and Group cleanup.

    manim -qh example-production.py GridHierarchy
"""

from manim import *

BG = "#1C1C1C"
PRIMARY = "#58C4DD"
ACCENT = "#FFFF00"
INK = "#FFFFFF"


class GridHierarchy(Scene):
    """A 2x2 grid of concepts with a framed focus and a caption."""

    def construct(self):
        self.camera.background_color = BG

        titles = ["vector", "space", "basis", "transform"]
        cells = VGroup(
            *[
                VGroup(Circle(radius=0.5, color=PRIMARY), Text(t, font_size=22, color=INK))
                for t in titles
            ]
        )
        for cell in cells:
            cell[1].next_to(cell[0], DOWN, buff=0.15)
        cells.arrange_in_grid(rows=2, cols=2, buff=0.8)
        cells.set_opacity(0.45)  # context layer

        focus = SurroundingRectangle(cells[2], color=ACCENT, buff=0.2)
        caption = Text("the basis is the focus", font_size=24, color=ACCENT)
        caption.next_to(cells, DOWN, buff=0.6)

        self.play(Create(cells), run_time=1.2)
        self.wait(0.8)
        self.play(Create(focus), run_time=0.6)  # single strong focal point
        self.wait(0.3)
        self.play(Write(caption), run_time=0.8)
        self.wait(2.0)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
