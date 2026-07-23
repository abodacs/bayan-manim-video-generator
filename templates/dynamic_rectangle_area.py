import sys
from pathlib import Path

from manim import *

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


RECTANGLE_AREA = 25
INITIAL_X = 5
X_RANGE = [0, 10]
Y_RANGE = [0, 10]


class DynamicRectangleArea(Scene):
    def construct(self):
        axes = self._create_axes()

        x_tracker = ValueTracker(INITIAL_X)

        curve = self._create_curve(axes)

        rectangle = self._create_dynamic_rectangle(
            axes,
            x_tracker,
        )

        moving_point = self._create_moving_point(
            axes,
            x_tracker,
        )

        self.add(
            axes,
            curve,
            moving_point,
        )

        self.play(Create(rectangle))

        self.play(
            x_tracker.animate.set_value(10)
        )

        self.play(
            x_tracker.animate.set_value(
                RECTANGLE_AREA / 10
            )
        )

        self.play(
            x_tracker.animate.set_value(
                INITIAL_X
            )
        )

        self.wait()

    def _create_axes(self):
        return Axes(
            x_range=X_RANGE,
            y_range=Y_RANGE,
            x_length=6,
            y_length=6,
            axis_config={
                "include_tip": False,
            },
        )

    def _create_curve(self, axes):
        return axes.plot(
            lambda x: RECTANGLE_AREA / x,
            x_range=[
                RECTANGLE_AREA / 10,
                X_RANGE[1],
                0.01,
            ],
            color=RED,
            use_smoothing=False,
        )

    def _create_dynamic_rectangle(
        self,
        axes,
        x_tracker,
    ):
        return always_redraw(
            lambda: Polygon(
                *[
                    axes.c2p(x, y)
                    for x, y in self._rectangle_vertices(
                        x_tracker.get_value()
                    )
                ]
            )
            .set_fill(
                TEAL,
                opacity=0.5,
            )
            .set_stroke(
                PURPLE,
                width=1,
            )
        )

    def _create_moving_point(
        self,
        axes,
        x_tracker,
    ):
        point = Dot(
            color=YELLOW,
        )

        point.set_z_index(10)

        point.add_updater(
            lambda mob: mob.move_to(
                axes.c2p(
                    x_tracker.get_value(),
                    RECTANGLE_AREA / x_tracker.get_value(),
                )
            )
        )

        return point

    def _rectangle_vertices(
        self,
        x_value,
    ):
        y_value = RECTANGLE_AREA / x_value

        return [
            (x_value, y_value),
            (0, y_value),
            (0, 0),
            (x_value, 0),
        ]