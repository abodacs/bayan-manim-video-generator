# 02 — Mobjects, positioning, and grouping

> **Objective.** Choose the smallest mobject for the idea, position it precisely
> in Manim's coordinate system, and group it correctly.
>
> **Misconception it kills.** *“Positions are pixel coordinates you eyeball.”*
> They are not. Manim uses a **math coordinate system**: the origin is screen
> center, and `UP/DOWN/LEFT/RIGHT` are unit vectors. You place objects with
> `move_to` / `next_to` / `to_edge` / `arrange` and **verify** with bounding boxes.
>
> **Prerequisites.** [01 — First Scene](../01-first-scene/index.html).
>
> **Source reference.** `mobjects.md`.

## Pick the smallest mobject

Everything visible is a **mobject**. Use the smallest object that expresses the
idea, then compose named mobjects into a group.

- Text: `Text`, `Paragraph` (prose); `MathTex`/`Tex` (math, raw strings).
- Shapes: `Circle`, `Square`, `Rectangle`, `Polygon`, `Triangle`, `Dot`, `Line`,
  `Arrow`, `Arc`, `RegularPolygon`.
- Annotations: `Brace`, `SurroundingRectangle`, `Angle`, `DashedLine`.

## Position precisely

```python
row = VGroup(circle, square, triangle).arrange(RIGHT, buff=0.6)  # even spacing
row.to_edge(UP, buff=1.0)                                         # edge + buffer
label.next_to(row, DOWN, buff=0.8)                                # relative to bbox
dot.move_to(np.array([2.0, 1.0, 0.0]))                            # explicit coords
```

`next_to` and `arrange` position relative to **bounding boxes**, so layouts stay
correct as content changes. Use `buff >= 0.5` near frame edges. After placement,
check the result by rendering a still (`--format=png -s`).

## VGroup vs Group — the rule that bites

- **`VGroup`** accepts only compatible **`VMobject`** children (shapes, `Tex`).
- **`Group`** accepts **mixed** `Mobject` types (shapes + `Text` + captions).

For scene cleanup, always use `Group(*self.mobjects)` because a scene can contain
non-`VMobject` types:

```python
self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
```

Do **not** assume `Group` supports every `VMobject` convenience (e.g.
`save_state`); save/restore individual compatible mobjects when needed.

## Annotated minimal scene

See `scene.py`. Three shapes are arranged into a `VGroup`, pushed to the top
edge, and labelled. Cleanup uses `Group` because `Text` is mixed in.

## One practical + one production example

- **`example-practical.py` — `RightTriangle`.** A geometry diagram: build a
  triangle from points, add a `RightAngle` marker, label a leg. This is the
  skeleton of "geometry before algebra".
- **`example-production.py` — `GridHierarchy`.** A 2×2 grid with opacity
  layering (context dimmed, one framed focus, a caption) — full visual hierarchy.

## Pitfalls and detection

| Pitfall | Symptom | Detection |
|---|---|---|
| `VGroup` with a non-`VMobject` child | Error at creation | Use `Group` for mixed types. |
| Animating before `add`/`Create` | Nothing moves | Creation animations put the object on screen first. |
| Guessing positions | Overlaps, clipping | Use `next_to`/`arrange`; render a still; check bbox. |
| Tiny `buff` at edges | Text clipped | `buff >= 0.5` near the frame edge. |

## Verification step

1. Render `scene.py` at `-ql`. The three shapes sit in an even row at the top,
   the label is centered below them, no overlaps.
2. Render a still of `example-production.py`. Confirm the focus rectangle wraps
   exactly one cell and nothing is clipped at the edges.
