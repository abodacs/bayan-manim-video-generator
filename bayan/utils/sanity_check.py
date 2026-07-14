from manim import *

class SanityCheckScene(Scene):
    def construct(self):
        square = Square()
        self.play(Create(square))
        self.wait(1)