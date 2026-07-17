# Contributing to Bayan

Thanks for contributing to Bayan. The project is an early-stage Python toolkit
for generating Arabic-first Manim videos, so keep changes small, typed, and
easy to review.

## Before you start

Read the documents relevant to your change:

1. [`AGENTS.md`](AGENTS.md) for repository and pull-request instructions.
2. [`README.md`](README.md) for installation and the first rendering check.
3. [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the development loop.
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
   [`docs/DOMAIN_MODEL.md`](docs/DOMAIN_MODEL.md) for system boundaries and
   domain concepts.
5. The relevant decision records in [`docs/agdr/`](docs/agdr/) when changing a
   documented technical boundary.

## Set up the project

Follow the native-dependency and environment setup in the
[`README.md`](README.md), then run:

~~~bash
uv sync
~~~

The repository uses `uv` for dependency management. Keep `uv.lock` up to date
when dependency declarations change.

## Development checks

Run the checks relevant to your change. The full local suite is:

~~~bash
uv run ruff check .
uv run ruff format --check .
uv run mypy bayan
uv run pytest
uv run pre-commit run --all-files
~~~

When changing Arabic layout, glyph ordering, or rendering behavior, also run
the sanity scene and inspect its output:

~~~bash
uv run manim -ql bayan/utils/sanity_check.py ArabicSanityCheck
~~~

Unit tests do not replace visual verification of Arabic shaping, right-to-left
direction, frame composition, or animation order.

## Code guidelines

- Keep reusable, non-rendering logic in typed modules under `bayan/`.
- Keep Manim scene files thin and focused on composition and animation.
- Keep content and scene-plan concepts independent of Manim and model SDKs.
- Treat generated scene code as untrusted input; do not execute it in the
  application host.
- Use English alphabetic characters in Python comments. Put Arabic content in
  string literals instead.
- Use the canonical terms in [`CONTEXT.md`](CONTEXT.md): `Lesson`, `Lesson
  segment`, `Scene plan`, `Scene`, `Render job`, `Artifact`, `Validation
  result`, and `Review`.

The package is checked with strict mypy. The Manim sanity scene is excluded from
the type-checking boundary because its star-import API is dynamic; keep new
non-rendering logic outside that scene.

## Documentation and decisions

Keep the documentation hierarchy consistent:

- Update `README.md` when installation or the first successful workflow
  changes.
- Update `CONTEXT.md` when a domain term is clarified or a competing synonym is
  rejected.
- Update the relevant document under `docs/` when the product direction,
  architecture, domain model, or development loop changes.
- Add an AgDR under [`docs/agdr/`](docs/agdr/) for a hard-to-reverse technical
  choice or a change to an established development boundary.
- Keep proposed roadmap statements in
  [`docs/PROJECT_NORTH_STAR.md`](docs/PROJECT_NORTH_STAR.md) separate from
  implemented behavior.

## Branches and commits

Create short-lived branches from the latest `main` and use a prefix that
describes the change:

- `feature/` for a new capability
- `fix/` for a bug fix
- `docs/` for documentation-only work
- `chore/` for tooling or dependency changes
- `refactor/` for behavior-preserving restructuring

Use Conventional Commits, for example:

~~~text
docs: clarify the development guide
fix(arabic): preserve glyph order in helper output
~~~

Keep one concern per branch and commit only files related to that concern.

## Pull requests

Open a pull request for every change to `main`. Include:

- a concise summary of the user or maintainer outcome;
- the relevant design or documentation context;
- validation commands and their results; and
- any manual rendering checks or known limitations.

Before requesting review, confirm that the working tree contains no generated
artifacts or unrelated changes and that the applicable checks pass.
