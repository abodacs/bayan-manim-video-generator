"""Errors of the isolated render boundary.

``DockerError`` is the render worker's original error, raised by the Docker
preflight and worker lifecycle code. The repair loop's failure taxonomy is
pipeline vocabulary and lives in :mod:`bayan.pipeline.taxonomy`; this module
stays renderer-only because it is copied into the isolated container image
(see ``bayan/renderer/smoke.py``).
"""

from __future__ import annotations


class DockerError(RuntimeError):
    """A Docker preflight or worker lifecycle failure."""
