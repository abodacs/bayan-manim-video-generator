"""Tests for the Arabic template catalogue and metadata validation."""

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from bayan.cli import app
from bayan.templates.catalogue import get_template_catalogue, validate_catalogue_entries

runner = CliRunner()


def test_catalogue_lists_all_six_templates() -> None:
    """Ensure the catalogue registers all 6 required Arabic quickstart templates."""
    catalogue = get_template_catalogue()

    expected_slugs = {
        "create-circle",
        "square-to-circle",
        "square-and-circle",
        "animated-square-to-circle",
        "different-rotations",
        "transform-cycle",
    }

    assert set(catalogue.keys()) == expected_slugs


def test_template_metadata_shape() -> None:
    """Verify that every template contains required metadata fields and Bayan provenance."""
    catalogue = get_template_catalogue()

    for slug, meta in catalogue.items():
        assert meta["name"] == slug
        assert isinstance(meta["purpose"], str) and len(meta["purpose"]) > 0
        assert isinstance(meta["arabic_title"], str) and len(meta["arabic_title"]) > 0
        assert meta["provenance"] == "bayan-authored"
        assert "dependencies" in meta


def test_missing_metadata_reports_template_by_name() -> None:
    """Verify that catalogue validation names corrupt templates without hiding others."""
    mock_catalogue: dict[str, dict[str, Any]] = {
        "valid-template": {
            "name": "valid-template",
            "purpose": "A valid test template",
            "arabic_title": "قالب صالح",
            "dependencies": "none",
            "provenance": "bayan-authored",
        },
        "broken-template": {
            "name": "broken-template",
            # missing purpose and arabic_title
            "provenance": "bayan-authored",
        },
    }

    errors = validate_catalogue_entries(mock_catalogue)
    assert len(errors) == 1
    assert "broken-template" in errors[0]


def test_cli_template_list() -> None:
    """Verify that 'bayan template list' prints all registered templates."""
    result = runner.invoke(app, ["template", "list"])
    assert result.exit_code == 0
    assert "create-circle" in result.stdout
    assert "إنشاء دائرة" in result.stdout


def test_cli_template_copy_success(tmp_path: Path) -> None:
    """Verify copying a valid template creates the file in output directory."""
    out_dir = tmp_path / "copied_templates"
    result = runner.invoke(app, ["template", "copy", "create-circle", "-o", str(out_dir)])

    assert result.exit_code == 0
    copied_file = out_dir / "create_circle.py"
    assert copied_file.exists()
    assert "class CreateCircle" in copied_file.read_text(encoding="utf-8")


def test_cli_template_copy_unknown_template(tmp_path: Path) -> None:
    """Verify copying an invalid template raises error."""
    result = runner.invoke(app, ["template", "copy", "non-existent-slug", "-o", str(tmp_path)])
    assert result.exit_code == 1
    assert "Error: Unknown template" in result.stdout
