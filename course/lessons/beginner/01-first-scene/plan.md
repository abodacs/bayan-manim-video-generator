# Plan — Lesson 01: First Scene

> A `plan.md` exists even for a one-scene lesson, to instill the habit from
> `scene-planning.md`: plan audience, arc, beats, palette, timing **before** code.

## Overview
- **Topic:** install + first render.
- **Audience:** absolute beginner; can run shell commands, no Manim experience.
- **Hook:** "render your first animation in under five minutes."
- **Aha moment:** a `.py` file becomes a real `.mp4`.
- **Length:** ~20 s of video.
- **Resolution:** 480p draft / 1080p final.
- **Arc:** build-up (seed → reveal → payoff → clean exit).
- **Grounding:** `.agents/skills/manim-video/references/rendering.md`, `mobjects.md`.

## Palette
- Background: `#1C1C1C`
- Primary: `BLUE` (the circle)
- Context: white text (the title)

## Scene breakdown — `HelloManim` (~20 s)
**One sentence:** install works and a Python Scene renders to video.

| # | Beat | Animation | Wait after |
|---|------|-----------|---:|
| 1 | Title appears | `Write(title)` rt=1.5 | 1.0 |
| 2 | Title lifts, circle draws | `animate.to_edge(UP)`; `Create(circle)` rt=0.8/1.0 | 1.5 |
| 3 | Clean exit | `FadeOut(Group(*self.mobjects))` rt=0.6 | — |

## Self-critique (before code)
1. One sentence per scene? Yes.
2. Payoff? The rendered file.
3. Geometry before algebra? N/A (no math).
4. Pauses? Every reveal has a hold.
