# 0001 — Course foundation & enforced conventions

**Date:** 2026-07-25
**Status:** Accepted
**Topic:** How the Manim CE course is grounded and what conventions it enforces.

## Context
The `/teach` invocation asked for a rigorous, static, browser-based Manim CE course under `course/`,
grounded in `.agents/skills/manim-video/`. Before writing any lesson, we established the source of
truth and the non-negotiable conventions so every lesson stays consistent and the generated scenes
match what the `bayan` automation already enforces.

## Decision
- Source of truth = `SKILL.md` + the 16 `references/*.md`. Lesson→reference mapping follows the
  progressive-disclosure router in `references/index.md`.
- Generator = zero-dep **Python** (`course/generator.py`): scans `lessons/`, `exams/`, `capstone/`,
  validates each `quiz.json`/`*-gate.json` against an inline schema, renders README markdown to HTML,
  and emits a single landing `index.html` plus per-lesson/gate/capstone pages. No Manim/FFmpeg/LaTeX
  at build; scenes are syntax-checked (`py_compile`), never executed.
- Progress = browser `localStorage` only.
- Conventions enforced in every scene: treat Manim Python as untrusted input; security sandbox rules;
  geometry before algebra; one concept per scene; semantic color; pause after every reveal;
  `MovingCameraScene` for any `self.camera.frame` use; raw LaTeX strings only for
  `MathTex`/`Tex`/`Matrix`/numbered axes; `DecimalNumber`/`Integer` treated as LaTeX-backed (0.20.1);
  `VGroup` for compatible VMobjects, `Group(*self.mobjects)` for mixed cleanup; never `aligned_edge=None`.

## Consequences
- Lessons can be authored independently and still pass the generator's validation.
- The course's "truth" never drifts from the repo's skill, so a learner's habits transfer directly to
  working in `bayan`.
- Assessment is mastery-gated (≥ 85% per tier, 1 attempt / 24h) and Bloom-laddered, with Create items
  self-assessed against a model answer + rubric.

## Open questions
- Should gates also sample from earlier tiers cumulatively beyond what the spec states? (Spec says
  "cumulative re-test allowed" — we will include a few earlier-tier items in higher gates.)
