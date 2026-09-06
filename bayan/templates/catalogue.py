"""Catalogue registry and validation logic for Bayan Arabic templates."""

from __future__ import annotations

from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Define the required metadata shape for all Bayan templates
CATALOGUE: dict[str, dict[str, object]] = {
    "create-circle": {
        "name": "create-circle",
        "purpose": "First shape + the Create animation",
        "arabic_title": "إنشاء دائرة",
        "concept": "Basic Mobject instantiation and rendering",
        "dependencies": "none",
        "provenance": "bayan-authored",
        "class_name": "CreateCircle",
    },
    "square-to-circle": {
        "name": "square-to-circle",
        "purpose": "Interpolating between shapes",
        "arabic_title": "تحويل المربع إلى دائرة",
        "concept": "Shape morphing and path interpolation",
        "dependencies": "none",
        "provenance": "bayan-authored",
        "class_name": "SquareToCircle",
    },
    "square-and-circle": {
        "name": "square-and-circle",
        "purpose": "Positioning mobjects relatively",
        "arabic_title": "مربع ودائرة",
        "concept": "Spatial alignment and relative layout",
        "dependencies": "none",
        "provenance": "bayan-authored",
        "class_name": "SquareAndCircle",
    },
    "animated-square-to-circle": {
        "name": "animated-square-to-circle",
        "purpose": ".animate animates method calls",
        "arabic_title": "تحريك المربع إلى دائرة",
        "concept": "Property interpolation via method chaining",
        "dependencies": "none",
        "provenance": "bayan-authored",
        "class_name": "AnimatedSquareToCircle",
    },
    "different-rotations": {
        "name": "different-rotations",
        "purpose": ".animate vs explicit Rotate",
        "arabic_title": "مقارنة الدوران",
        "concept": "Direct method animation vs explicit Animation objects",
        "dependencies": "none",
        "provenance": "bayan-authored",
        "class_name": "DifferentRotations",
    },
    "transform-cycle": {
        "name": "transform-cycle",
        "purpose": "Transform vs ReplacementTransform + lifecycle",
        "arabic_title": "دورة التحويل",
        "concept": "Object identity retention during transformations",
        "dependencies": "none",
        "provenance": "bayan-authored",
        "class_name": "TransformCycle",
    },
}


def get_template_catalogue() -> dict[str, dict[str, object]]:
    """Return a validated copy of the registry of available Bayan Arabic templates."""
    errors = validate_catalogue_entries(CATALOGUE)
    if errors:
        raise RuntimeError(f"The template catalogue is malformed: {'; '.join(errors)}")
    return {slug: dict(metadata) for slug, metadata in CATALOGUE.items()}


def fixture_filename(slug: str) -> str:
    """Return the fixture scene filename for a catalogue slug."""
    return f"{slug.replace('-', '_')}.py"


def read_fixture_code(slug: str) -> str:
    """Read an approved catalogue fixture scene from disk."""
    return (FIXTURES_DIR / fixture_filename(slug)).read_text(encoding="utf-8")


def validate_catalogue_entries(catalogue: dict[str, dict[str, object]]) -> list[str]:
    """Validate catalogue metadata shape and report errors by template name."""
    errors: list[str] = []
    required_fields = {
        "name",
        "purpose",
        "arabic_title",
        "class_name",
        "provenance",
        "dependencies",
    }

    for name, metadata in catalogue.items():
        missing = required_fields - set(metadata.keys())
        if missing:
            missing_str = ", ".join(sorted(missing))
            errors.append(f"Template '{name}' is missing required metadata fields: {missing_str}")

    return errors
