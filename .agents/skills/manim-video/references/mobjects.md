# Mobjects Reference

Everything visible in Manim is a mobject. Choose the smallest object that expresses the visual idea, then compose it into a named group.

## Text and equations

```python
title = Text("Hello", font_size=48, weight=BOLD)
body = Paragraph("First line", "Second line", font_size=28)
eq = MathTex(r"E = mc^2", font_size=40)
```

Use `MarkupText` for inline styling and `ArabicText` from `bayan.utils.arabic_helper` for project Arabic scenes. Validate fonts on the actual render worker.

## Shapes and geometry

Common primitives include `Circle`, `Square`, `Rectangle`, `Dot`, `Line`, `Arrow`, `Arc`, `Polygon`, `RegularPolygon`, `Sector`, and `Annulus`. Use `VMobject` with `set_points_smoothly` for custom curves.

`CubicBezier` requires four explicit anchor/control points; it is not a blank free-form curve. For arbitrary points, create a `VMobject` and call `set_points_smoothly(points)`.

## Group versus VGroup

- `VGroup` accepts only `VMobject` children.
- `Group` accepts mixed `Mobject` types, including `Text` and caption objects.

Use `VGroup` for shape-only composition and `Group` for mixed scene cleanup:

```python
cleanup = Group(*self.mobjects)
self.play(FadeOut(cleanup), run_time=0.5)
```

Do not assume `Group` supports every `VMobject` convenience method such as `save_state`; save/restore individual compatible mobjects when necessary.

## Positioning and styling

Use `move_to`, `next_to`, `to_edge`, `to_corner`, `arrange`, and `arrange_in_grid`. Check bounding boxes after placement. Use `set_fill`, `set_stroke`, `set_opacity`, `set_color`, `scale`, `set_width`, and `set_height` for styling.

For `Line` and generic `VMobject`, set stroke opacity/width with `set_stroke()` when constructor keywords are not supported by the installed version.

## Specialized objects

- `Matrix` and `DecimalMatrix` for structured arrays; confirm LaTeX availability.
- `Variable` for a labeled live value.
- `SVGMobject` for approved vector assets; inspect submobjects before animating them.
- `ImageMobject` for approved raster assets; never let generated code fetch an image from the network.
- `SurroundingRectangle`, `Brace`, `Angle`, and `DashedLine` for annotations; see [decorations.md](decorations.md).

## Lifecycle rule

Name important mobjects, add them before property animations, and remove or transform them deliberately. Avoid anonymous piles of objects that cannot be debugged or reviewed.
