from manim import Scene, Write

# Manim loads scene files as standalone modules and puts the file's own
# directory on sys.path (not the project root), so we import the sibling
# module directly rather than via the `bayan.utils` package path.
from arabic_helper import ArabicText


class ArabicSanityCheck(Scene):
    """
    Integration visual test for Arabic RTL rendering.

    Run this scene and verify that:
    - Arabic letters are connected.
    - Text flows from right to left.
    """

    def construct(self):
        title = ArabicText(
            "مرحبا بالعالم",
            font="Amiri",
            font_size=48,
        )

        self.play(Write(title))
        self.wait(1)