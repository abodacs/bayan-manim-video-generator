"""Lesson 04 — practical: the two default transitions, side by side.

CleanBreak fades everything (default between topics); CarryForward keeps one
key element when the next scene builds directly on it. Two small scenes in one
file is fine for a prototype; production splits per scene.

    manim -ql example-practical.py CleanBreak
    manim -ql example-practical.py CarryForward
"""

from manim import *

BG = "#1C1C1C"
PRIMARY = "#58C4DD"
ACCENT = "#FFFF00"


class CleanBreak(Scene):
    """Default when changing topics: leave nothing behind."""

    def construct(self):
        self.camera.background_color = BG

        term = MathTex(r"a^2 + b^2", font_size=48, color=PRIMARY)
        self.play(Write(term), run_time=1.5)
        self.wait(1.0)

        # Clean break: fade the whole scene, brief beat of silence.
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)
        self.wait(0.3)


class CarryForward(Scene):
    """Next scene builds on it: keep the key term, fade only the context."""

    def construct(self):
        self.camera.background_color = BG

        term = MathTex(r"a^2 + b^2", font_size=48, color=PRIMARY)
        note = Text("the parts", font_size=24)
        note.next_to(term, DOWN, buff=0.8)
        self.play(Write(term), run_time=1.5)
        self.wait(0.8)
        self.play(FadeIn(note, shift=UP * 0.2), run_time=0.5)
        self.wait(1.0)

        # Carry-forward: the term stays; only the context leaves.
        self.play(FadeOut(note), Circumscribe(term, color=ACCENT), run_time=0.8)
        self.wait(1.5)

        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
