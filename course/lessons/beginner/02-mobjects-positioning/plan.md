# Plan — Lesson 02: Mobjects & positioning

## Overview
- **Topic:** mobject choice + precise positioning + correct grouping.
- **Audience:** has rendered Lesson 01; knows `play`/`wait`.
- **Aha:** positioning is geometric (bounding boxes), not pixel guessing.
- **Arc:** build-up.
- **Grounding:** `mobjects.md`.

## Palette
- Background `#1C1C1C`; primary BLUE; accent YELLOW; ink white.

## Scene breakdown — `Positioning` (~10 s)
**One sentence:** three mobjects arranged and labelled without pixel coordinates.

| # | Beat | Animation | Wait |
|---|------|-----------|---:|
| 1 | Row appears | `Create(row)` rt=1.2 | 0.5 |
| 2 | Label writes | `Write(label)` rt=0.8 | 1.5 |
| 3 | Exit | `FadeOut(Group(*self.mobjects))` rt=0.6 | — |

## Key layout decisions
- `arrange(RIGHT, buff=0.6)` for even spacing.
- `to_edge(UP, buff=1.0)` keeps the row off the edge.
- `Group(*self.mobjects)` cleanup because `Text` is mixed in.
