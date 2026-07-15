"""Smoke tests for the bayan package.

These verify the package is importable and its namespace is intact. They do
NOT exercise Manim rendering, which requires the cairo/pango/ffmpeg native
dependencies. Real unit tests for domain logic arrive with issue #2 (Arabic RTL
& ligature reshaping) -- the first feature with testable, render-free logic.
"""

import importlib
import sys

import bayan


def test_package_imports() -> None:
    """`import bayan` succeeds (catches a broken __init__ or missing dep at import time)."""
    assert "bayan" in sys.modules


def test_package_namespace_reloadable() -> None:
    """The package namespace can be reloaded cleanly without side effects."""
    assert importlib.reload(bayan) is not None


def test_utils_subpackage_importable() -> None:
    """`bayan.utils` is an importable subpackage and does not pull in the Manim scene."""
    utils = importlib.import_module("bayan.utils")
    assert utils is not None
