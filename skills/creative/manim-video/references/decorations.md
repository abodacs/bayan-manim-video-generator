# Decorations and Visual Polish

Decorations should explain a relationship or direct attention. Remove any decoration that does neither.

## Highlights and context

```python
box = SurroundingRectangle(term, color=YELLOW, buff=0.15)
backdrop = BackgroundRectangle(panel, fill_opacity=0.85, buff=0.2)
self.play(Create(box), run_time=0.5)
```

Use a `SurroundingRectangle` around the exact term or object being discussed. Dim context before highlighting the primary object.

## Braces and labels

```python
brace = Brace(group, DOWN, buff=0.15)
label = brace.get_text("shared structure", buff=0.1)
self.play(GrowFromCenter(brace), Write(label), run_time=0.8)
```

Use `BraceBetweenPoints` when the span is not a single mobject. Check that the label remains inside the safe frame.

## Arrows and guides

- `Arrow` or `CurvedArrow` for directed relationships.
- `LabeledArrow` or `LabeledLine` when a short label is part of the relationship.
- `DashedLine` or `DashedVMobject` for construction lines, asymptotes, and implied links.
- `Angle` and `RightAngle` for geometric constraints.

Arrows should point to a clear target and have enough buffer to avoid crossing text. Use a short label rather than a paragraph attached to an arrow.

## Color and text emphasis

Prefer `t2c`/`set_color_by_tex` for semantic equation highlighting and `MarkupText` for inline styled prose. Define color meaning once—do not use the same accent for unrelated concepts.

## Annotation lifecycle

Treat an annotation as a temporary object:

1. Reveal the target.
2. Add one annotation.
3. Pause while the narration explains it.
4. Fade or transform the annotation before introducing the next one.

Do not stack braces, boxes, arrows, and labels until the subject becomes unreadable. A clean frame with one strong highlight is usually more educational.
