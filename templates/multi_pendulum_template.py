import sys
from pathlib import Path
from manim import *
from manim_physics import *

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class MultiPendulumVertical(SpaceScene):
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

        p = MultiPendulum(
            RIGHT * 2,
            LEFT * 2,
            bob_style={"color": WHITE, "fill_opacity": 1, "radius": 0.4},
        )
        p.shift(UP * 5)

        for i, bob in enumerate(p.bobs):
            color = neon_colors[i % len(neon_colors)]
            bob.set_color(color)
            bob.set_fill(color, opacity=1)
            bob.set_sheen(0.5, UL)

            glow = Circle(
                radius=0.55, color=color, stroke_width=8, stroke_opacity=0.4
            )
            glow.move_to(bob.get_center())
            glow.add_updater(lambda m, b=bob: m.move_to(b.get_center()))
            self.add(glow)

            inner_glow = Circle(
                radius=0.48, color=WHITE, stroke_width=3, stroke_opacity=0.3
            )
            inner_glow.move_to(bob.get_center())
            inner_glow.add_updater(lambda m, b=bob: m.move_to(b.get_center()))
            self.add(inner_glow)

        for i, rod in enumerate(p.rods):
            color = neon_colors[i % len(neon_colors)]
            rod.set_color(color)
            rod.set_stroke(width=6, opacity=0.9)

        self.add(p)
        self.make_rigid_body(*p.bobs)
        p.start_swinging()

        for i, bob in enumerate(p.bobs):
            color = neon_colors[i % len(neon_colors)]
            self.add(
                TracedPath(
                    bob.get_center,
                    stroke_color=color,
                    stroke_width=5,
                    stroke_opacity=0.9,
                )
            )
            self.add(
                TracedPath(
                    bob.get_center,
                    stroke_color=color,
                    stroke_width=12,
                    stroke_opacity=0.3,
                )
            )

        self.wait(15)