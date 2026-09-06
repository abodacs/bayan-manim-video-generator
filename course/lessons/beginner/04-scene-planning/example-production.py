"""Lesson 04 — production: the full planning checklist applied.

Opacity layering (primary 1.0 / context 0.4 / scaffolding 0.15), shared color
constants with fixed meanings, subcaptions on every beat, one >= 2.0 s
thinking pause, safe edge buffing, and a clean Group exit.

    manim -qh example-production.py OpacityLayers
"""

from manim import *

BG = "#1C1C1C"
PRIMARY = "#58C4DD"  # the thing being explained
SECONDARY = "#83C167"  # supporting structure
ACCENT = "#FFFF00"  # the key result / focus
INK = "#FFFFFF"

OPACITY_PRIMARY = 1.0
OPACITY_CONTEXT = 0.4
OPACITY_SCAFFOLD = 0.15


class OpacityLayers(Scene):
    """Hierarchy without adding a single new mobject type."""

    def construct(self):
        self.camera.background_color = BG

        # Scaffolding: a grid the viewer should feel, not read.
        grid = NumberPlane(x_range=(-6, 6, 1), y_range=(-3, 3, 1))
        grid.set_opacity(OPACITY_SCAFFOLD)
        self.play(Create(grid), run_time=1.0)
        self.add_subcaption("a grid to anchor positions", duration=1.0)
        self.wait(1.0)

        # Context: a secondary curve, present but recessed.
        line = FunctionGraph(lambda x: 0.5 * x, x_range=(-4, 4), color=SECONDARY)
        line.set_opacity(OPACITY_CONTEXT)
        self.play(Create(line), run_time=1.0)
        self.add_subcaption("and a familiar line for reference", duration=1.2)
        self.wait(1.0)

        # Primary: the thing being explained, full opacity.
        curve = FunctionGraph(lambda x: 0.1 * x * x, x_range=(-4, 4), color=PRIMARY)
        self.play(Create(curve), run_time=1.5)
        self.add_subcaption("the curve of interest", duration=1.2)
        self.wait(1.0)

        # Key insight: the minimum sits on the reference line.
        dot = Dot(radius=0.12, color=ACCENT).move_to(ORIGIN)
        self.play(FadeIn(dot, scale=2.0), run_time=0.8)
        self.add_subcaption("its minimum sits exactly on the line", duration=1.5)
        self.wait(2.0)  # the thinking pause — longest hold in the scene

        caption = Text("hierarchy is opacity, not size", font_size=24, color=INK)
        caption.to_edge(DOWN, buff=0.8)
        self.play(Write(caption), run_time=0.8)
        self.wait(1.5)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
