import sys
from pathlib import Path

from manim import *

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bayan.utils.arabic_helper import ArabicText

HIGHLIGHT_PADDING = 0.15


class EquationMovingArabic(Scene):
    def construct(self):
        FONT_NAME = "Arial"

        # 1. Prepare Arabic text elements (Pango applies shaping and bidi once)
        energy = ArabicText("ط", font=FONT_NAME)
        equal = Text("=", font=FONT_NAME)
        mass = ArabicText("ك", font=FONT_NAME)

        # 2. Construct the superscripted speed element
        speed_base = ArabicText("س", font=FONT_NAME)
        speed_exponent = Text("2", font=FONT_NAME).scale(0.55)

        # Position exponent '2' at the upper-left corner of the speed base,
        # as expected in right-to-left math layout
        speed_exponent.move_to(speed_base.get_corner(UL)).shift(LEFT * 0.08 + UP * 0.05)

        speed = VGroup(speed_base, speed_exponent)

        # 3. Position the speed element to the left of mass (following RTL layout)
        speed.next_to(mass, LEFT, buff=0.15)

        # 4. Group the Left-Hand Side (LHS)
        lhs = VGroup(mass, speed)

        # 5. Arrange the full equation from Right to Left (RTL)
        equal.next_to(energy, LEFT, buff=0.35)
        lhs.next_to(equal, LEFT, buff=0.35)

        sentence = VGroup(energy, equal, lhs)
        sentence.move_to(ORIGIN)

        # 6. Create highlight bounding boxes matching the sentence structure
        framebox1 = SurroundingRectangle(sentence[0], buff=HIGHLIGHT_PADDING, color=YELLOW)
        framebox2 = SurroundingRectangle(sentence[2], buff=HIGHLIGHT_PADDING, color=YELLOW)

        # 7. Animation sequence
        self.play(Write(sentence))
        self.play(Create(framebox1))
        self.wait()

        self.play(ReplacementTransform(framebox1, framebox2))
        self.wait()
