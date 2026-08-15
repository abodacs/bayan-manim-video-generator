# Notes

Working notes & preferences for this teaching workspace.

## Build strategy
- The deliverable is the static `course/` site (spec in the `/teach` invocation). The interactive
  `lessons/*.html` per-lesson system from the `/teach` skill is superseded by `course/lessons/**`,
  which already embeds README + code + per-lesson quiz per page. Do not duplicate.
- Staged across sessions: spine → Tier 1 → Tier 2 → Tier 3 → Tier 4. Progress tracked in the task list.
- Generator language: **Python, stdlib-only** (matches the repo's language; the source of truth is Python).

## Conventions to enforce in every scene across the course
- Canonical artifact = Manim Python; treat as untrusted input.
- Security: no network/Docker socket/host secrets, non-root, read-only root, output-only writes,
  bounded CPU/mem/time; no dynamic imports/file/process/socket access in any `scene.py`.
- Story: geometry before algebra, one concept per scene, semantic colors, pause after every reveal.
- Camera: subclass `MovingCameraScene` whenever `self.camera.frame` is touched.
- LaTeX: raw strings; only `MathTex`/`Tex`/`Matrix`/numbered axes; never `aligned_edge=None`.
  `DecimalNumber`/`Integer` ARE LaTeX-backed in 0.20.1 — do not call them LaTeX-free.
- Grouping: `VGroup` for compatible `VMobject`s; `Group(*self.mobjects)` for mixed cleanup.

## Quiz authoring rules (rigor + anti-luck)
- ≥ 6 items per lesson, spanning all six Bloom levels (Remember→Create).
- Item types: single-choice, multi-select, fill-blank (exact/regex), predict-output, bug-spot, code-ordering, create.
- Every item: `{id, type, bloom, prompt, options|answer, explanation, ref}`. Explanations show only AFTER answering.
- Create items: self-assessed against model answer + rubric (no local Manim run-check).
- Options equal-length where feasible to avoid leaking the answer.
- Tier gates: 15–25 items, ≥ 85% to unlock next tier, 1 attempt / 24h, cumulative re-test.
- Option order shuffled client-side; ≥ 2 variants per concept in gates.

## Verification gates (run before declaring a tier done)
- `python3 -m py_compile` on every `scene.py` + `example-*.py` (syntax-valid, render-ready — NOT executed).
- Generator validates every `quiz.json` + `*-gate.json` against the schema (Bloom ladder present, types valid).
- Rebuild the site from folders offline: `python3 course/generator.py`.

## Known gotchas to bake into lessons
- `DecimalNumber`/`Integer` default to `mob_class=MathTex` (LaTeX) in 0.20.1.
- `CubicBezier` needs 4 control points; arbitrary curves use `VMobject().set_points_smoothly(points)`.
- Don't animate a mobject before `Create`/`add`; don't pass `aligned_edge=None`.
- `Line`/`VMobject` stroke via `.set_stroke()` when constructor kwargs unsupported on the version.
- Cleanup of mixed mobjects uses `Group(*self.mobjects)`, never `VGroup(*self.mobjects)`.
