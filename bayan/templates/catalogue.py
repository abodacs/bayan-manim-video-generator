"""Catalogue registry and validation logic for Bayan Arabic templates."""

from typing import Any

# Define the required metadata shape for all Bayan templates
CATALOGUE: dict[str, dict[str, Any]] = {
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


def get_template_catalogue() -> dict[str, dict[str, Any]]:
    """Return the registry of available Bayan Arabic templates."""
    return CATALOGUE


def validate_catalogue_entries(catalogue: dict[str, dict[str, Any]]) -> list[str]:
    """Validate catalogue metadata shape and report errors by template name."""
    errors: list[str] = []
    required_fields = {"name", "purpose", "arabic_title", "provenance", "dependencies"}

    for name, metadata in catalogue.items():
        missing = required_fields - set(metadata.keys())
        if missing:
            missing_str = ", ".join(sorted(missing))
            errors.append(f"Template '{name}' is missing required metadata fields: {missing_str}")

    return errors
