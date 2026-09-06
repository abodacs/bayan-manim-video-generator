# 03 — play/wait, Create/FadeIn/Transform, and rate functions

> **Objective.** Choose creation, visibility, and transform animations
> deliberately, and pick rate functions that express intent.
>
> **Misconception it kills.** *“Animation choice is cosmetic.”* It carries
> meaning: `Create` **builds**, `FadeIn` **reveals**, `Transform` **relates**.
> Rate functions express intent — `linear` = machine/constant, `smooth` = natural
> ease, `there_and_back` = a passing emphasis.
>
> **Prerequisites.** [02 — Mobjects & positioning](../02-mobjects-positioning/index.html).
>
> **Source reference.** `animations.md`.

## The three families

```python
self.play(Create(circle), run_time=1.0)  # build the stroke
self.play(FadeIn(square, shift=DOWN * 0.3))  # reveal without drawing
self.play(Transform(circle, square))  # morph: show a relationship
```

- **Creation:** `Create`, `Write`, `DrawBorderThenFill`, `GrowFromCenter`.
- **Visibility:** `FadeIn`, `FadeOut`, `Uncreate`, `ShrinkToCenter`.
- **Transform:** `Transform`, `ReplacementTransform`, `TransformMatchingTex`,
  `FadeTransform`. `TransformMatchingTex` is ideal when the viewer should see
  which terms persist across an equation.
- **Attention (no model change):** `Indicate`, `Circumscribe`, `Flash`,
  `ShowPassingFlash`.

> Do **not** separately animate the same property in competing animations within
> one `play` call. Chain related changes with `.animate` instead.

## Rate functions express intent

```python
self.play(dot.animate.shift(RIGHT * 2), rate_func=linear, run_time=2.0)
self.play(dot.animate.shift(RIGHT * 2), rate_func=smooth, run_time=2.0)
self.play(dot.animate.shift(RIGHT * 0.5), rate_func=there_and_back, run_time=1.0)
```

Use `MoveAlongPath` for meaningful trajectories and `Rotate` for a one-time
rotation (an updater for continuous rotation — see Lesson 10).

## Composition

- `AnimationGroup(...)` — simultaneous, with optional lag.
- `LaggedStart(...)` — staggered repeated appearances (a sequence).
- `Succession(...)` — sequential within one `play` call.

Keep the active focus to one or two moving elements.

## Timing rule (recap)

Every reveal needs a pause; the **key reveal** gets the longest pause. A fast
reveal + long hold beats a slow reveal with no reading time.

| Beat | run_time | Wait after |
|---|---:|---:|
| Simple create | 0.5–0.8 s | 0.5 s |
| Formula / key reveal | 1.5–2.5 s | 1.5–2.5 s |
| Aha moment | 1.5–2.5 s | 2.0–3.0 s |

## One practical + one production example

- **`example-practical.py` — `RateCompare`.** Two dots cross the screen, one
  `linear`, one `smooth`. Seeing them together is the fastest way to feel the
  difference.
- **`example-production.py` — `BuildUp`.** A `LaggedStart` of boxes, then a
  single highlighted "result" — composition + the key-pause discipline.

## Pitfalls and detection

| Pitfall | Symptom | Detection |
|---|---|---|
| Competing animations on one property | Jitter / override | Chain via `.animate`; one state change per `play`. |
| No `run_time` on key beats | Feels arbitrary | Set `run_time` explicitly. |
| Wrong rate function | Motion feels "off" for the idea | `linear` for mechanical; `smooth`/`there_and_back` for emphasis. |
| `Transform` between very different point counts | Ugly morph | Use `FadeTransform`, or morph via an intermediate. |

## Verification step

1. Render `scene.py`. Confirm the circle *draws*, the square *fades*, the circle
   *morphs* into a blue square, and the `there_and_back` nudge returns.
2. Render `example-practical.py`. The yellow dot moves at constant speed; the
   blue dot eases in and out over the same distance.
