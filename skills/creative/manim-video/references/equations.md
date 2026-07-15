# Equations and LaTeX Reference

Use this reference only when the scene needs mathematical notation. Check [no-latex-workaround.md](no-latex-workaround.md) first when LaTeX may not be available.

## Raw strings are mandatory

```python
eq = MathTex(r"E = mc^2")
fraction = MathTex(r"\frac{1}{2}")
```

Without a raw string, sequences such as `\f` can become Python control characters before LaTeX receives them.

## Build a derivation

Show the destination dimmed or introduce one meaningful step at a time. Keep each equation readable, highlight the term being discussed, and pause after the reveal.

```python
step_a = MathTex(r"a^2 + b^2 = c^2")
step_b = MathTex(r"a^2 = c^2 - b^2")
self.play(Write(step_a), run_time=2.0)
self.wait(2.0)
self.play(TransformMatchingTex(step_a, step_b), run_time=1.5)
self.wait(1.5)
```

## Selective color and matching

Split important terms into submobjects or use `substrings_to_isolate`:

```python
eq = MathTex(r"E", r"=", r"m", r"c^2")
eq[0].set_color(YELLOW)
eq[2].set_color(BLUE)
```

Use `TransformMatchingTex` when the viewer should see which terms persist. Use `key_map` when notation changes but the conceptual identity remains.

## Layout

- Use `align_to`, `arrange`, and `next_to` rather than manual guesses.
- Use `aligned_edge=LEFT` or another explicit edge when needed; do not pass `aligned_edge=None` on versions where it crashes.
- Keep one main equation on screen at a time unless the comparison is the lesson.
- Use `buff >= 0.5` near frame edges and shrink or split dense equations.

## Common structures

`MathTex` supports matrices, cases, aligned multi-line derivations, and `substrings_to_isolate`. Test complicated expressions in a tiny scene first; a LaTeX compile error can hide the actual layout issue.

## Mathematical correctness gate

Do not treat a successfully rendered equation as correct. Extract every claim and equation, check definitions and units, substitute known values, test an edge case, and have an independent reviewer challenge the derivation. This gate is required for generated educational content.
