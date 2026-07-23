"""Errors raised by the isolated render boundary."""


class DockerError(RuntimeError):
    """A Docker preflight or worker lifecycle failure."""
