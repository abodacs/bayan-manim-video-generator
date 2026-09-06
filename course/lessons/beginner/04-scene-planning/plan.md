# Plan — Lesson 04: Scene planning & the plan file

The plan for a lesson *about* planning — written first, as the lesson teaches.

## Overview
- **Topic:** plan-before-code; arc, one-concept-per-scene, timing, transitions.
- **Aha:** the pause after a reveal matters more than the animation; a one-sentence
  test catches overloaded scenes before any code exists.
- **Arc:** build-up — seed (one familiar scene), perturb (why it overloads),
  generalize (the plan discipline), apply (plan template + checklist).
- **Grounding:** `scene-planning.md`.

## Palette
BG `#1C1C1C`; PRIMARY `#58C4DD` (the thing being explained); ACCENT `#FFFF00`
(the key result); INK white. Same constants as Lessons 01–03 — cross-scene
consistency is itself part of the lesson.

## Scene breakdown — `PlannedArc` (~13 s)
**One sentence:** a build-up arc in miniature — seed, perturb, generalise —
with every beat timed from the timing table.

| # | Beat | Animation | Wait |
|---|------|-----------|---:|
| 1 | Seed: one dot appears | `FadeIn(dot)` rt=0.5 | 0.5 |
| 2 | Perturb: a second, different dot | `Create(dot2)` rt=0.8 | 0.8 |
| 3 | Generalise: both become squares | `Transform` rt=1.5 | 1.0 |
| 4 | Key insight caption | `Write(caption)` rt=1.5 | 2.5 |
| 5 | Clean exit | `FadeOut(Group(*self.mobjects))` rt=0.6 | 0.3 |

## Worked examples
- **`example-practical.py`** — `CleanBreak` + `CarryForward`: the two default
  transitions side by side, so the difference is visible.
- **`example-production.py`** — `OpacityLayers`: the full checklist applied —
  colour constants, opacity layering (1.0 / 0.4 / 0.15), subcaptions, a
  ≥ 2.0 s thinking pause, and a clean exit.
