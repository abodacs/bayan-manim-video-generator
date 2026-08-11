# Mission: Manim Community Edition — Beginner → Master

## Why
Build and ship a rigorous, self-contained, browser-based course that takes a learner from zero to
production-grade Manim CE (≥ 0.20.1) authoring. The course is grounded in the repo's own
`.agents/skills/manim-video/` skill (the same source of truth the `bayan` generator and templates
obey), so what the student learns matches what the project's automation enforces. Mastery here means
the learner can write grounded, render-ready Manim scenes that pass the project's security, math,
layout, and production gates — not just "code that runs."

## Success looks like
- A learner can install Manim CE and render a first scene from the command line.
- A learner can read the project's `templates/` and `references/` and reproduce their techniques.
- A learner writes scenes that respect: geometry before algebra, one concept per scene, semantic
  color, pause-after-reveal, `MovingCameraScene` for `self.camera.frame`, raw LaTeX strings only for
  `MathTex`/`Tex`/`Matrix`/numbered axes, `VGroup` vs `Group` cleanup.
- A learner passes all four tier-gate exams (≥ 85%) and the Tier 4 research-paper-explainer capstone.
- The site rebuilds fully offline from folders via the zero-dep generator.

## Constraints
- Static site only: no server, no build server, no npm, no rendering at build time (no Manim/FFmpeg/LaTeX invoked during generation).
- English content.
- Zero-dep generator (stdlib Python or Node).
- Browser `localStorage` is the only progress store.
- Grounded in `.agents/skills/manim-video/` — do not invent Manim APIs; validate against CE 0.20.1.

## Out of scope
- Running/rendering scenes inside the browser (scenes are render-ready code artifacts, read + copied locally).
- A backend, accounts, or analytics.
- Audio/voiceover production (the skill defers audio; the course teaches it as an option only).
- Non-Manim animation libraries.
