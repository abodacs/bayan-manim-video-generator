import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / ".agents" / "skills" / "manim-video"

EXPECTED_REFERENCES = {
    "animation-design-thinking.md",
    "animations.md",
    "camera-and-3d.md",
    "decorations.md",
    "equations.md",
    "graphs-and-data.md",
    "mobjects.md",
    "no-latex-workaround.md",
    "paper-explainer.md",
    "production-quality.md",
    "rendering.md",
    "scene-planning.md",
    "troubleshooting.md",
    "updaters-and-trackers.md",
    "visual-design.md",
}


def _frontmatter() -> str:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must begin with YAML frontmatter"
    return match.group(1)


def test_skill_frontmatter_has_required_credit_and_platform_fields() -> None:
    frontmatter = _frontmatter()

    description = re.search(r"^description: (.+)$", frontmatter, re.MULTILINE)
    assert description
    assert len(description.group(1)) <= 60
    assert description.group(1).endswith(".")

    assert re.search(r"^version: \d+\.\d+\.\d+$", frontmatter, re.MULTILINE)
    assert re.search(r"^platforms: \[[^]]+\]$", frontmatter, re.MULTILINE)
    assert re.search(
        r"^author: .*Abdullah Mohammed \(@abodacs\).*Hermes Agent",
        frontmatter,
        re.MULTILINE,
    )


def test_skill_uses_modern_section_order() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    sections = [
        "## When to Use",
        "## Prerequisites",
        "## How to Run",
        "## Quick Reference",
        "## Procedure",
        "## Pitfalls",
        "## Verification",
    ]
    positions = [text.index(section) for section in sections]
    assert positions == sorted(positions)


def test_progressive_reference_inventory_is_complete() -> None:
    index = (SKILL_DIR / "references" / "index.md").read_text(encoding="utf-8")
    for reference in EXPECTED_REFERENCES:
        assert f"]({reference})" in index
        assert (SKILL_DIR / "references" / reference).is_file()


def test_moving_camera_example_uses_the_moving_camera_scene() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    text = (SKILL_DIR / "references" / "camera-and-3d.md").read_text(encoding="utf-8")
    assert re.search(r"class ZoomScene\(MovingCameraScene\):", skill)
    assert "self.camera.frame" in text
    assert re.search(r"class ZoomExample\(MovingCameraScene\):", text)
    assert not re.search(r"class ZoomExample\(Scene\):", text)


def test_no_latex_table_matches_manim_0201_number_behavior() -> None:
    text = (SKILL_DIR / "references" / "no-latex-workaround.md").read_text(encoding="utf-8")
    assert "`DecimalNumber` | Requires LaTeX by default" in text
    assert "`Integer` | Requires LaTeX by default" in text
    assert "`DecimalNumber`, `Integer`, shapes" not in text


def test_skill_preserves_direct_code_and_risk_gates() -> None:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "canonical generated artifact is Manim Python" in text
    assert "human-in-the-loop" in text
    assert "incorrect math" in text
    assert "no network" in text
