import sys
from pathlib import Path
from manim import *

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ==========================================
# CONSTANTS & CONFIGURATION
# ==========================================
CIRCLE_RADIUS = 0.8
CIRCLE_FILL_OPACITY = 0.7
CIRCLE_COLORS = [RED, BLUE, GREEN, YELLOW, PURPLE]


# ==========================================
# SCENE IMPLEMENTATION (RTL ORDER)
# ==========================================
class CircleSquareScene(Scene):
    def construct(self):
        # Create 5 colorful circles
        circles = [
            Circle(radius=CIRCLE_RADIUS, color=col, fill_opacity=CIRCLE_FILL_OPACITY)
            for col in CIRCLE_COLORS
        ]

        # 1. Position circles in a horizontal line progressing Right-to-Left
        # Starting from right (+4) to left (-4)
        for i, circle in enumerate(circles):
            circle.move_to(RIGHT * 4 + LEFT * i * 2)

        # 2. Create circles sequentially from Right to Left
        for circle in circles:
            self.play(Create(circle), run_time=0.5)

        # 3. Scale up all circles simultaneously
        self.play(
            *[circle.animate.scale(1.3) for circle in circles],
            run_time=1.5
        )

        # 4. Move circles into a circular pentagon formation
        positions = [
            UP * 2,
            UP * 0.618 + RIGHT * 1.902,
            DOWN * 1.618 + RIGHT * 1.176,
            DOWN * 1.618 + LEFT * 1.176,
            UP * 0.618 + LEFT * 1.902,
        ]

        self.play(
            *[circles[i].animate.move_to(positions[i]) for i in range(5)],
            run_time=2
        )

        # 5. Rotate the entire formation around origin
        self.play(
            *[Rotate(circle, 2 * PI, about_point=ORIGIN) for circle in circles],
            run_time=3
        )

        # 6. Scale back to original size
        self.play(
            *[circle.animate.scale(1 / 1.3) for circle in circles],
            run_time=1
        )

        # 7. Return to initial Right-to-Left row layout
        self.play(
            *[circles[i].animate.move_to(RIGHT * 4 + LEFT * i * 2) for i in range(5)],
            run_time=2
        )

        # Final pause
        self.wait(2)