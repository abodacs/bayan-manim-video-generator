import sys
from pathlib import Path

import numpy as np
from manim import *

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bayan.utils.arabic_helper import ArabicText, rtl_glyphs


class ChargeDot(VGroup):
    """A point charge: filled circle with its sign, standing in for manim-physics Charge."""

    def __init__(self, q: float, position: np.ndarray) -> None:
        super().__init__()
        color = RED if q > 0 else BLUE
        body = Circle(radius=0.22, color=color, fill_color=color, fill_opacity=1)
        sign = Text("+" if q > 0 else "-", color=WHITE, weight=BOLD).scale(0.5)
        sign.move_to(body.get_center())
        self.add(body, sign)
        self.q = q
        self.move_to(position)


def field_lines(charges: list[ChargeDot]) -> VGroup:
    """Trace field lines by integrating the Coulomb field outward from each
    positive charge, stopping at negative charges or the frame edge."""

    def coulomb(p: np.ndarray) -> np.ndarray:
        field = np.zeros(3)
        for charge in charges:
            offset = p - charge.get_center()
            field += charge.q * offset / np.linalg.norm(offset) ** 3
        return field

    step = 0.06
    max_steps = 400
    stop_radius = 0.3
    negatives = [c for c in charges if c.q < 0]

    lines = VGroup()
    for charge in charges:
        if charge.q <= 0:
            continue
        for k in range(12):
            angle = 2 * PI * k / 12
            current = charge.get_center() + 0.32 * np.array([np.cos(angle), np.sin(angle), 0.0])
            points = [current.copy()]
            for _ in range(max_steps):
                field = coulomb(current)
                norm = np.linalg.norm(field)
                if norm < 1e-9:
                    break
                current = current + step * field / norm
                if (
                    abs(current[0]) > config.frame_x_radius - 0.2
                    or abs(current[1]) > config.frame_y_radius - 0.2
                ):
                    break
                if any(np.linalg.norm(current - c.get_center()) < stop_radius for c in negatives):
                    break
                points.append(current.copy())
            if len(points) > 2:
                lines.add(
                    VMobject(
                        stroke_color=TEAL,
                        stroke_width=2.5,
                        stroke_opacity=0.9,
                    ).set_points_as_corners(points)
                )
    return lines


class ElectricFieldArabic(Scene):
    def construct(self) -> None:
        self.camera.background_color = BLACK

        title = ArabicText(
            "فيزياء المجال الكهربي",
            font="Arial",
            color=BLUE,
        ).scale(0.8)
        title.to_edge(UP, buff=0.5)

        self.play(Write(rtl_glyphs(title)), run_time=1.2)
        self.wait(0.3)

        positive_charge = ChargeDot(2, ORIGIN)
        self.play(FadeIn(positive_charge, scale=0.5), run_time=0.8)
        self.wait(0.3)

        field = field_lines([positive_charge])
        self.play(Create(field), run_time=2.0)
        self.wait(1.0)

        explanation1 = ArabicText(
            "الشحنة الموجبة تنبعث منها خطوط المجال للخارج",
            font="Arial",
            color=YELLOW,
        ).scale(0.55)
        explanation1.to_edge(DOWN, buff=0.6)

        self.play(FadeIn(explanation1, shift=UP), run_time=0.8)
        self.wait(1.5)

        self.play(
            FadeOut(field),
            FadeOut(explanation1),
            run_time=0.8,
        )

        negative_charge = ChargeDot(-2, RIGHT * 1.5)
        self.play(
            positive_charge.animate.shift(LEFT * 1.5),
            FadeIn(negative_charge, scale=0.5),
            run_time=1.2,
        )
        self.wait(0.3)

        field = field_lines([positive_charge, negative_charge])
        self.play(Create(field), run_time=2.0)
        self.wait(1.2)

        explanation2 = ArabicText(
            "خطوط المجال تتجه من الشحنة الموجبة إلى السالبة",
            font="Arial",
            color=GREEN,
        ).scale(0.55)
        explanation2.to_edge(DOWN, buff=0.6)

        self.play(FadeIn(explanation2, shift=UP), run_time=0.8)
        self.wait(1.5)

        self.play(
            FadeOut(field),
            FadeOut(explanation2),
            run_time=0.8,
        )

        third_charge = ChargeDot(-1, UP * 2.2)
        self.play(FadeIn(third_charge, scale=0.5), run_time=0.8)
        self.wait(0.3)

        field = field_lines([positive_charge, negative_charge, third_charge])
        self.play(ShowIncreasingSubsets(field, run_time=2.0))
        self.wait(1.5)

        self.play(
            positive_charge.animate.move_to(LEFT * 2.2 + DOWN * 0.8),
            negative_charge.animate.move_to(RIGHT * 2.2 + DOWN * 0.8),
            third_charge.animate.move_to(UP * 1.5),
            FadeOut(field, scale=0.9),
            run_time=2.0,
        )

        field = field_lines([positive_charge, negative_charge, third_charge])
        self.play(Create(field), run_time=1.8)
        self.wait(1.0)

        explanation3 = ArabicText(
            "تتداخل خطوط المجال لتشكل أنماطاً معقدة",
            font="Arial",
            color=PURPLE,
        ).scale(0.55)
        explanation3.to_edge(DOWN, buff=0.6)

        self.play(Write(rtl_glyphs(explanation3)), run_time=1.2)
        self.wait(2)

        self.play(
            title.animate.scale(1.1),
            explanation3.animate.scale(1.1),
            run_time=1.2,
        )
        self.wait(2)
