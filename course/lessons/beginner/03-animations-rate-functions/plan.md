# Plan — Lesson 03: Animations & rate functions

## Overview
- **Topic:** deliberate animation choice + rate functions.
- **Aha:** animation type and easing each carry meaning.
- **Arc:** build-up.
- **Grounding:** `animations.md`.

## Palette
BG `#1C1C1C`; BLUE, YELLOW; ink white.

## Scene breakdown — `AnimationChoices` (~12 s)
**One sentence:** create, fade, transform, and emphasise — each chosen on purpose.

| # | Beat | Animation | Wait |
|---|------|-----------|---:|
| 1 | Circle draws | `Create(circle)` rt=1.0 | 0.5 |
| 2 | Square fades in | `FadeIn(square, shift=DOWN*0.3)` rt=0.8 | 0.8 |
| 3 | Circle morphs to square | `Transform` rt=1.5 | 1.0 |
| 4 | Emphasis nudge | `animate.shift` `there_and_back` rt=1.0 | 1.0 |
| 5 | Exit | `FadeOut(Group(*self.mobjects))` rt=0.6 | — |

## Rate-function intent
- `linear` — mechanical / constant.
- `smooth` — natural easing (default for most reveals).
- `there_and_back` — a passing emphasis that returns.
