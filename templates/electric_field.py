import sys
from pathlib import Path
from manim import *
from manim_physics import Charge, ElectricField

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bayan.utils.arabic_helper import ArabicText


class ElectricFieldArabic(Scene):
    def construct(self) -> None:
        self.camera.background_color = BLACK

        title = ArabicText(
            "فيزياء المجال الكهربي",
            font="Arial",
            color=BLUE,
        ).scale(0.8)
        title.to_edge(UP, buff=0.5)
        title.submobjects.reverse()

        self.play(Write(title), run_time=1.2)
        self.wait(0.3)

        positive_charge = Charge(2, ORIGIN)
        self.play(FadeIn(positive_charge, scale=0.5), run_time=0.8)
        self.wait(0.3)

        field = ElectricField(positive_charge)
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

        negative_charge = Charge(-1.5, RIGHT * 3)
        self.play(
            positive_charge.animate.shift(LEFT * 1.5),
            FadeIn(negative_charge, scale=0.5),
            run_time=1.2,
        )
        self.wait(0.3)

        field = ElectricField(positive_charge, negative_charge)
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

        third_charge = Charge(-1, UP * 2.2)
        self.play(FadeIn(third_charge, scale=0.5), run_time=0.8)
        self.wait(0.3)

        field = ElectricField(positive_charge, negative_charge, third_charge)
        self.play(ShowIncreasingSubsets(field, run_time=2.0))
        self.wait(1.5)

        self.play(
            positive_charge.animate.move_to(LEFT * 2.2 + DOWN * 0.8),
            negative_charge.animate.move_to(RIGHT * 2.2 + DOWN * 0.8),
            third_charge.animate.move_to(UP * 1.5),
            FadeOut(field, scale=0.9),
            run_time=2.0,
        )

        field = ElectricField(positive_charge, negative_charge, third_charge)
        self.play(Create(field), run_time=1.8)
        self.wait(1.0)

        explanation3 = ArabicText(
            "تتداخل خطوط المجال لتشكل أنماطاً معقدة",
            font="Arial",
            color=PURPLE,
        ).scale(0.55)
        explanation3.to_edge(DOWN, buff=0.6)
        explanation3.submobjects.reverse()

        self.play(Write(explanation3), run_time=1.2)
        self.wait(2)

        self.play(
            title.animate.scale(1.1),
            explanation3.animate.scale(1.1),
            run_time=1.2,
        )
        self.wait(2)