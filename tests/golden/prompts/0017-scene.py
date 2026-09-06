from manim import *

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class GeneratedScene(Scene):
    def construct(self):
        message_0 = ArabicText("نقسم 95 على 10، الخطوة 1")
        message_0.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_0)))
        message_1 = ArabicText("نقسم 95 على 10، الخطوة 2")
        message_1.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_1)))
        message_2 = ArabicText("نقسم 95 على 10، الخطوة 3")
        message_2.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_2)))
        message_3 = ArabicText("الناتج 9 والباقي 5")
        message_3.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_3)))
        self.wait(1)
