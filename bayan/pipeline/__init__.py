"""Pipeline package for the `bayan generate` path: staged prompt-to-video services.

Each stage is a deep module: typed inputs, validated outputs, and its own run
record. The orchestrator path (`bayan run`) is untouched and keeps its
template-oriented contracts.
"""
