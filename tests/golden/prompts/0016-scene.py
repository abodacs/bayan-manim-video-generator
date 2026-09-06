from manim import *

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class GeneratedScene(Scene):
    def construct(self):
        message_0 = ArabicText("نقسم 99 على 3، الخطوة 1")
        message_0.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_0)))
        message_1 = ArabicText("نقسم 99 على 3، الخطوة 2")
        message_1.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_1)))
        message_2 = ArabicText("نقسم 99 على 3، الخطوة 3")
        message_2.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_2)))
        message_3 = ArabicText("الناتج 33 والباقي 0")
        message_3.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_3)))
        self.wait(1)
