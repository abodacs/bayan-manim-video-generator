# Type checker: mypy (strict, Manim scenes excluded)

> In the context of bayan's greenfield dev-quality baseline (issue #7), facing the choice between mypy and pyright for static type checking of a Manim-based codebase, I decided mypy with strict mode (excluding Manim scene files) to achieve early type safety with ecosystem-standard tooling, accepting that the dynamic `from manim import *` API cannot be meaningfully type-checked.

## Context

bayan is built on Manim, whose public API is heavily dynamic: `from manim import *` star-imports hundreds of names, `Scene` subclasses rely on metaclass magic, and `self.play(...)` / Mobject construction are hard for any static analyser to follow. Issue #7 asks for static type checking as part of the dev-quality baseline (alongside CI, ruff, tests). The codebase is currently a skeleton (empty `bayan/__init__.py`, one 8-line scene), so this decision sets the tool the team standardises on *before* the domain code in issues #2–#5 lands.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **mypy** (strict) | Python-ecosystem standard; `--strict` is well understood; portable across editors and CI; mature plugin ecosystem | Slower than pyright; stricter defaults fight dynamic APIs; weaker inline DX than Pylance |
| **pyright** | Fast; excellent VS Code/Pylance DX; more lenient on dynamic patterns by default | Newer; different error flavour; Pylance coupling assumes VS Code |

## Decision

Chosen: **mypy**, strict mode, with Manim scene files (`bayan/utils/sanity_check.py` and future `Scene` subclasses) **excluded** from checking.

Justification: mypy is the ecosystem default and the most portable choice across editors and CI. Strict mode catches real bugs in the domain logic that #3/#4/#5 will introduce (LLM client, render engine, CLI orchestration). Excluding the Manim scenes is pragmatic, not lazy — a star-imported, metaclass-driven rendering API cannot be typed meaningfully, and attempting it produces noise that drowns the real signal. The domain layers (prompt → Manim-code generation → orchestration) are where types pay off, and those are ordinary Python that mypy strict handles well.

## Consequences

- New domain code in `bayan/` (outside scene files) is held to mypy strict from the first commit.
- Scene files are exempt; if a scene grows non-trivial logic, extract that logic into a typed, non-scene module and unit-test it there.
- Both the mypy config and the coverage threshold are "wired but lightly loaded" today — they become load-bearing as #2–#5 land.
- Revisit if the team standardises on VS Code/Pylance and wants the tighter inline loop (would warrant re-evaluating pyright).
