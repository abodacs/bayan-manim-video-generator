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
DEFAULT_COLOR = WHITE
TEAL_LINE_COLOR = TEAL
ORANGE_LINE_COLOR = ORANGE
PURPLE_LINE_COLOR = PURPLE
RED_DOT_COLOR = RED

LETTER_SCALE = 0.3
LETTER_STROKE_WIDTH = 3.5
PROJECTION_STROKE_WIDTH = 2
MOVING_DOT_RADIUS = 0.08

ROTATION_SPEED = 0.25
X_ADVANCE_FACTOR = 4.0
ANIMATION_DURATION = 8.5


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def _point(x: float, y: float, z: float = 0.0) -> np.ndarray:
    """Helper function to cleanly create 3D coordinate arrays."""
    return np.array([x, y, z])


def create_arabic_taa(color=DEFAULT_COLOR, scale_factor=LETTER_SCALE) -> VMobject:
    """Constructs a smooth vector-based Arabic 'Taa' letter using Bezier curves."""
    arabic_taa = VMobject(color=color, stroke_width=LETTER_STROKE_WIDTH)

    # Bezier curve for the smooth main loop of the letter Taa
    letter_loop = CubicBezier(
        _point(-0.4, -0.15),
        _point(-0.1, 0.4),
        _point(0.4, 0.35),
        _point(0.4, -0.15),
    )

    # Base horizontal line and vertical stroke
    baseline = Line(
        _point(-0.5, -0.15), _point(0.6, -0.15), color=color, stroke_width=LETTER_STROKE_WIDTH
    )
    vertical_stroke = Line(
        _point(-0.22, -0.1), _point(-0.25, 0.8), color=color, stroke_width=LETTER_STROKE_WIDTH
    )

    arabic_taa.add(letter_loop, baseline, vertical_stroke)
    arabic_taa.scale(scale_factor)
    return arabic_taa


# ==========================================
# SCENE IMPLEMENTATION (RTL DIRECTION)
# ==========================================
class SineWaveDemo(Scene):
    def construct(self):
        # 1. Reversed origins for Right-to-Left (RTL) rendering
        self.origin_point = _point(4, 0)      # Reference circle placed on the RIGHT
        self.curve_start = _point(3, 0)       # Curve starts from right moving LEFT

        x_axis, y_axis, axis_labels = self._create_axes_and_labels()
        reference_circle = self._create_reference_circle()

        moving_dot, radius_line, projection_line, sine_curve = (
            self._setup_dynamic_elements(reference_circle)
        )

        self.add(x_axis, y_axis, axis_labels, reference_circle)
        self.add(moving_dot, radius_line, projection_line, sine_curve)

        self.wait(ANIMATION_DURATION)

    def _create_axes_and_labels(self):
        x_axis = Line(_point(-6, 0), _point(6, 0))
        y_axis = Line(_point(4, -2), _point(4, 2))

        axis_labels = VGroup()

        # Create axis labels (Taa, 2*Taa, 3*Taa, 4*Taa) progressing Right to Left
        for i in range(1, 5):
            taa_symbol = create_arabic_taa(color=DEFAULT_COLOR)

            if i == 1:
                label = taa_symbol
            else:
                num_text = Text(str(i), font_size=24, color=DEFAULT_COLOR)
                label = VGroup(num_text, taa_symbol)
                label.arrange(LEFT, buff=0.08)

            # Move labels towards the LEFT side
            label.move_to(_point(1 - 2 * (i - 1), -0.5))
            axis_labels.add(label)

        return x_axis, y_axis, axis_labels

    def _create_reference_circle(self) -> Circle:
        reference_circle = Circle(radius=1)
        reference_circle.move_to(self.origin_point)
        return reference_circle

    def _setup_dynamic_elements(self, reference_circle: Circle):
        moving_dot = Dot(radius=MOVING_DOT_RADIUS, color=RED_DOT_COLOR)
        moving_dot.move_to(reference_circle.point_from_proportion(0))

        self.animation_progress = 0

        def update_dot_position(mob, dt):
            self.animation_progress += dt * ROTATION_SPEED
            mob.move_to(
                reference_circle.point_from_proportion(self.animation_progress % 1)
            )

        def create_radius_line():
            return Line(
                self.origin_point, moving_dot.get_center(), color=TEAL_LINE_COLOR
            )

        def create_projection_line():
            # Advance towards the LEFT (- X_ADVANCE_FACTOR)
            x = self.curve_start[0] - self.animation_progress * X_ADVANCE_FACTOR
            y = moving_dot.get_center()[1]
            return Line(
                moving_dot.get_center(),
                _point(x, y),
                color=ORANGE_LINE_COLOR,
                stroke_width=PROJECTION_STROKE_WIDTH,
            )

        self.sine_curve = VGroup()
        self.sine_curve.add(Line(self.curve_start, self.curve_start))

        def update_sine_curve():
            last_line = self.sine_curve[-1]
            # Draw wave towards the LEFT
            x = self.curve_start[0] - self.animation_progress * X_ADVANCE_FACTOR
            y = moving_dot.get_center()[1]
            new_line = Line(
                last_line.get_end(), _point(x, y), color=PURPLE_LINE_COLOR
            )
            self.sine_curve.add(new_line)
            return self.sine_curve

        moving_dot.add_updater(update_dot_position)

        radius_line = always_redraw(create_radius_line)
        projection_line = always_redraw(create_projection_line)
        sine_curve = always_redraw(update_sine_curve)

        return moving_dot, radius_line, projection_line, sine_curve