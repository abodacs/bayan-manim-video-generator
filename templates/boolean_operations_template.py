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
FONT_FAMILY = "Arial"


# ==========================================
# SCENE IMPLEMENTATION (RTL LAYOUT)
# ==========================================
class BooleanOperations(Scene):
    def construct(self):
        # Create base shape geometry
        ellipse1 = Ellipse(
            width=4.0, height=5.0, fill_opacity=0.5, color=PURPLE, stroke_width=10
        ).move_to(LEFT * 0.5)
        ellipse2 = ellipse1.copy().set_color(color=TEAL).move_to(RIGHT * 0.5)

        # Title text using MarkupText for Arabic RTL support
        bool_ops_text = MarkupText(
            "<u>العمليات المنطقية</u>", font=FONT_FAMILY, font_size=36
        ).next_to(ellipse1, UP * 3)

        # Place the main group on the RIGHT side
        ellipse_group = Group(bool_ops_text, ellipse1, ellipse2).move_to(RIGHT * 3)
        self.play(FadeIn(ellipse_group))

        # 1. Intersection Operation (التقاطع) -> Moving to Top Left
        i = Intersection(ellipse1, ellipse2, color=GOLD, fill_opacity=0.5)
        self.play(i.animate.scale(0.25).move_to(LEFT * 5 + UP * 2.5))
        intersection_text = MarkupText("التقاطع", font=FONT_FAMILY, font_size=20).next_to(i, UP)
        self.play(FadeIn(intersection_text))

        # 2. Union Operation (الاتحاد) -> Below Intersection
        u = Union(ellipse1, ellipse2, color=MAROON, fill_opacity=0.5)
        union_text = MarkupText("الاتحاد", font=FONT_FAMILY, font_size=20)
        self.play(u.animate.scale(0.3).next_to(i, DOWN, buff=union_text.height * 3))
        union_text.next_to(u, UP)
        self.play(FadeIn(union_text))

        # 3. Exclusion Operation (الاستبعاد) -> Below Union
        e = Exclusion(ellipse1, ellipse2, color=BLUE_C, fill_opacity=0.5)
        exclusion_text = MarkupText("الاستبعاد", font=FONT_FAMILY, font_size=20)
        self.play(e.animate.scale(0.3).next_to(u, DOWN, buff=exclusion_text.height * 3.5))
        exclusion_text.next_to(e, UP)
        self.play(FadeIn(exclusion_text))

        # 4. Difference Operation (الفرق) -> To the Right of Union (towards center)
        d = Difference(ellipse1, ellipse2, color=LIGHT_PINK, fill_opacity=0.5)
        difference_text = MarkupText("الفرق", font=FONT_FAMILY, font_size=20)
        self.play(d.animate.scale(0.3).next_to(u, RIGHT, buff=difference_text.height * 3.5))
        difference_text.next_to(d, UP)
        self.play(FadeIn(difference_text))

        self.wait(2)