import sys
from pathlib import Path

import numpy as np
from manim import *

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pendulum_accel(theta: np.ndarray) -> np.ndarray:
    """Angular accelerations of a double pendulum from the standard EOM."""

    t1, t2, w1, w2 = theta
    m1 = m2 = 1.0
    l1 = l2 = 2.0
    g = 9.81
    delta = t1 - t2
    denom = 2.0 * m1 + m2 - m2 * np.cos(2.0 * delta)
    a1 = (
        -g * (2.0 * m1 + m2) * np.sin(t1)
        - m2 * g * np.sin(t1 - 2.0 * t2)
        - 2.0 * np.sin(delta) * m2 * (w2 * w2 * l2 + w1 * w1 * l1 * np.cos(delta))
    ) / (l1 * denom)
    a2 = (
        2.0
        * np.sin(delta)
        * (
            w1 * w1 * l1 * (m1 + m2)
            + g * (m1 + m2) * np.cos(t1)
            + w2 * w2 * l2 * m2 * np.cos(delta)
        )
    ) / (l2 * denom)
    return np.array([a1, a2])


class MultiPendulumVertical(Scene):
    def construct(self):
        self.camera.background_color = BLACK

        neon_colors = [
            "#FF1493",
            "#00FFFF",
            "#FF6600",
            "#39FF14",
            "#FF073A",
            "#BF00FF",
            "#FFFF00",
            "#00FF7F",
        ]

        l1 = l2 = 2.0
        anchor = ORIGIN
        state = np.array([np.pi / 2, np.pi / 2 + 0.35, 0.0, 0.0])
        pivot = always_redraw(lambda: Dot(anchor, radius=0.08, color=WHITE))

        def bob_point(index: int) -> np.ndarray:
            t1, t2 = state[0], state[1]
            if index == 0:
                return anchor + np.array([l1 * np.sin(t1), -l1 * np.cos(t1), 0.0])
            elbow = anchor + np.array([l1 * np.sin(t1), -l1 * np.cos(t1), 0.0])
            return elbow + np.array([l2 * np.sin(t2), -l2 * np.cos(t2), 0.0])

        rods = VGroup(
            always_redraw(
                lambda: Line(
                    anchor,
                    bob_point(0),
                    stroke_width=6,
                    stroke_opacity=0.9,
                    color=neon_colors[0],
                )
            ),
            always_redraw(
                lambda: Line(
                    bob_point(0),
                    bob_point(1),
                    stroke_width=6,
                    stroke_opacity=0.9,
                    color=neon_colors[1],
                )
            ),
        )

        bobs = VGroup(
            *[
                always_redraw(
                    lambda i=i: Dot(
                        bob_point(i),
                        radius=0.4,
                        color=neon_colors[i % len(neon_colors)],
                        fill_color=neon_colors[i % len(neon_colors)],
                        fill_opacity=1,
                    ).set_sheen(0.5, UL)
                )
                for i in range(2)
            ]
        )

        glows = VGroup()
        inner_glows = VGroup()
        for i in range(2):
            color = neon_colors[i % len(neon_colors)]
            glows.add(
                always_redraw(
                    lambda i=i, c=color: Circle(
                        radius=0.55,
                        color=c,
                        stroke_width=8,
                        stroke_opacity=0.4,
                        arc_center=bob_point(i),
                    )
                )
            )
            inner_glows.add(
                always_redraw(
                    lambda i=i: Circle(
                        radius=0.48,
                        color=WHITE,
                        stroke_width=3,
                        stroke_opacity=0.3,
                        arc_center=bob_point(i),
                    )
                )
            )

        self.add(pivot, rods, glows, inner_glows, bobs)

        for i in range(2):
            color = neon_colors[i % len(neon_colors)]
            self.add(
                TracedPath(
                    lambda i=i: bob_point(i),
                    stroke_color=color,
                    stroke_width=5,
                    stroke_opacity=0.9,
                )
            )
            self.add(
                TracedPath(
                    lambda i=i: bob_point(i),
                    stroke_color=color,
                    stroke_width=12,
                    stroke_opacity=0.3,
                )
            )

        def advance(dt: float) -> None:
            # RK4 keeps the chaotic trajectory stable at the frame step size.
            nonlocal state
            k1 = np.concatenate([state[2:], pendulum_accel(state)])
            k2 = np.concatenate([state[2:] + dt / 2 * k1[2:], pendulum_accel(state + dt / 2 * k1)])
            k3 = np.concatenate([state[2:] + dt / 2 * k2[2:], pendulum_accel(state + dt / 2 * k2)])
            k4 = np.concatenate([state[2:] + dt * k3[2:], pendulum_accel(state + dt * k3)])
            state = state + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

        self.add_updater(lambda frame_dt: advance(frame_dt))
        self.wait(15)
