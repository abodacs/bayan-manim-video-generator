from manim import *

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class GeneratedScene(Scene):
    def construct(self):
        message_0 = ArabicText("نقسم 34 على 10، الخطوة 1")
        message_0.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_0)))
        message_1 = ArabicText("الناتج 3 والباقي 4")
        message_1.next_to(ORIGIN, UP)
        self.play(Write(rtl_glyphs(message_1)))
        self.wait(1)
