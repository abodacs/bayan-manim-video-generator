import sys
from pathlib import Path
from manim import *
import numpy as np

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
# Configure 16:9 widescreen format
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_width = 16.0
config.frame_height = 9.0

GRID_LINE_COLOR = BLUE
X_AXIS_COLOR = "#00D9FF"
Y_AXIS_COLOR = "#FF006E"


# ==========================================
# SCENE IMPLEMENTATION
# ==========================================
class GridTransformVertical(Scene):
    def construct(self):
        # Create a colorful number plane grid
        grid = NumberPlane(
            x_range=[-8, 8, 1],
            y_range=[-5, 5, 1],
            background_line_style={
                "stroke_color": GRID_LINE_COLOR,
                "stroke_width": 2,
                "stroke_opacity": 0.6,
            },
        )

        # Style main axes with custom vibrant colors
        grid.x_axis.set_color(X_AXIS_COLOR)
        grid.y_axis.set_color(Y_AXIS_COLOR)

        # 1. Animate grid creation
        self.play(
            Create(grid, run_time=3, lag_ratio=0.1),
        )
        self.wait(1)

        # 2. Apply first non-linear transformation
        grid.prepare_for_nonlinear_transform()
        self.play(
            grid.animate.apply_function(
                lambda p: p
                + np.array(
                    [
                        np.sin(p[1]),
                        np.sin(p[0]),
                        0,
                    ]
                )
            ),
            run_time=4,
        )
        self.wait(2)

        # 3. Apply second secondary non-linear transformation
        grid.prepare_for_nonlinear_transform()
        self.play(
            grid.animate.apply_function(
                lambda p: p
                + np.array(
                    [
                        0.3 * np.sin(2 * p[1]),
                        0.3 * np.cos(2 * p[0]),
                        0,
                    ]
                )
            ),
            run_time=4,
        )
        self.wait(2)

        # 4. Fade out scene elements
        self.play(FadeOut(grid))
        self.wait()