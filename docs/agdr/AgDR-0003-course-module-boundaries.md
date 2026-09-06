# Keep the course module outside strict type checking

**Status:** Accepted

## Context

CONTRIBUTING.md keeps ordinary Python logic typed under strict mypy, with
dynamic boundaries documented in an AgDR (see AgDR-0001-type-checker.md). The
`course/` module adds two kinds of code that do not fit that boundary:

- Lesson scenes (`course/lessons/**/scene.py` and example files) are runnable
  Manim programs authored with `from manim import *`, mirroring the
  long-standing `templates/*.py` convention. They are content, not package
  logic.
- `course/generator.py` is a standalone, stdlib-only site builder. It never
  runs inside the Bayan application host, never executes lesson code (it only
  `compile()`-checks it), and is gated by ruff, its own schema validation, and
  the CI `course-gate` job (validation plus a full rebuild freshness check).

## Decision

`course/` is excluded from the strict mypy project boundary, as recorded in
`pyproject.toml`. The rationale mirrors AgDR-0001 for `bayan/utils/sanity_check.py`:
the code is dynamic by design (Manim star-imports) or is a build-time tool
outside the runtime dependency graph.

## Consequences

- Type regressions in `course/` are not caught by mypy; ruff, the generator's
  own validation, and the course-gate freshness check are the effective gates.
- If any part of the generator becomes runtime code for the product, that part
  must move under `bayan/` and be typed strictly like the rest of the package.
