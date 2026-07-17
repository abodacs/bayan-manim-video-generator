# Type checker: mypy (strict, Manim scenes excluded)

> In the context of bayan's greenfield dev-quality baseline (issue #7), facing the choice between mypy and pyright for static type checking of a Manim-based codebase, I decided mypy with strict mode (excluding Manim scene files) to achieve early type safety with ecosystem-standard tooling, accepting that the dynamic `from manim import *` API cannot be meaningfully type-checked.

## Context

bayan is built on Manim, whose public API is heavily dynamic: `from manim import *` star-imports hundreds of names, `Scene` subclasses rely on metaclass magic, and `self.play(...)` / Mobject construction are hard for any static analyser to follow. Issue #7 asked for static type checking as part of the dev-quality baseline (alongside CI, ruff, and tests). At the time of this decision, the codebase was a skeleton with an empty `bayan/__init__.py` and one short scene, so the decision set the team standard before product domain code landed.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **mypy** (strict) | Python-ecosystem standard; `--strict` is well understood; portable across editors and CI; mature plugin ecosystem | Slower than pyright; stricter defaults fight dynamic APIs; weaker inline DX than Pylance |
| **pyright** | Fast; excellent VS Code/Pylance DX; more lenient on dynamic patterns by default | Newer; different error flavour; Pylance coupling assumes VS Code |

## Decision

Chosen: **mypy**, strict mode, with Manim scene files (`bayan/utils/sanity_check.py` and future `Scene` subclasses) **excluded** from checking.

Justification: mypy is the ecosystem default and the most portable choice across editors and CI. Strict mode catches real bugs in the domain logic as generation, rendering, and CLI orchestration land. Excluding the Manim scenes is pragmatic, not lazy — a star-imported, metaclass-driven rendering API cannot be typed meaningfully, and attempting it produces noise that drowns the real signal. The domain layers (prompt → Manim-code generation → orchestration) are where types pay off, and those are ordinary Python that mypy strict handles well.

## Consequences

- New domain code in `bayan/` (outside scene files) is held to mypy strict from the first commit.
- Scene files are exempt; if a scene grows non-trivial logic, extract that logic into a typed, non-scene module and unit-test it there.
- The mypy config is now exercised against the package and CI. The Arabic
  helper has landed with focused tests; the coverage threshold remains
  intentionally permissive until the generation, rendering, and validation
  boundaries have testable contracts.
- Revisit if the team standardises on VS Code/Pylance and wants the tighter inline loop (would warrant re-evaluating pyright).
