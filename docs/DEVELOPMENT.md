# Development guide

This guide describes the development loop for Bayan. The root
[`README.md`](../README.md) remains the canonical setup guide for native
dependencies and the initial Arabic rendering check.

## Start here

1. Install the prerequisites and Python environment from the README.
2. Render `ArabicSanityCheck` to verify Manim, Cairo, Pango, FFmpeg, and Arabic
   font support.
3. Read [`PROJECT_NORTH_STAR.md`](PROJECT_NORTH_STAR.md) and
   [`ARCHITECTURE.md`](ARCHITECTURE.md) before adding product-facing modules.
4. Use the terms in [`CONTEXT.md`](../CONTEXT.md) when naming domain concepts.

## Daily development loop

Make the smallest coherent change, then run the checks relevant to that change:

~~~bash
uv run ruff check .
uv run ruff format --check .
uv run mypy bayan
uv run pytest
~~~

When a change affects rendering, also run the Arabic sanity scene and inspect
the generated video. Unit tests cannot replace visual verification of glyph
connections, reading direction, frame composition, or animation order.

## Code boundaries

### Domain and orchestration code

- Keep ordinary Python logic typed under strict mypy.
- Keep lesson and scene-plan concepts independent of Manim and model SDKs.
- Prefer explicit data passed between stages over hidden global state.
- Return structured failures that identify the stage and relevant inputs.

### Manim scenes

- Keep scene files thin and focused on composition and animation.
- Put reusable, non-rendering logic in typed modules.
- Add a render-level sanity check when a change affects Arabic layout or visual
  behavior.

### Generated code

- Treat all generated scene code as untrusted input.
- Do not execute it in the application host.
- Follow the boundary proposed in
  [`AgDR-0002-render-isolation.md`](agdr/AgDR-0002-render-isolation.md).

## Testing strategy

- **Unit tests** cover deterministic helpers and domain rules that do not need
  native rendering.
- **Smoke tests** verify that the package and utility namespace import cleanly.
- **Render checks** exercise Manim, native dependencies, Arabic shaping, and
  visual output.
- **Validation checks** should report evidence, not only a boolean status.

Keep tests close to the boundary they protect. If a scene contains logic that
needs substantial unit coverage, extract that logic into a typed module first.

## Documentation rules

- Update the README when installation or the first successful workflow changes.
- Update `CONTEXT.md` when a domain term is clarified or a competing synonym is
  rejected.
- Add an AgDR when a hard-to-reverse architectural trade-off would otherwise be
  surprising to the next contributor.
- Keep roadmap statements in `PROJECT_NORTH_STAR.md` clearly separate from
  implemented behavior.
