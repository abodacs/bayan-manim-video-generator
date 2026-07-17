# Troubleshooting

Classify the failure before repairing it: dependency, Python syntax, Manim API, layout, resource limit, or mathematical/content failure. Preserve the exact traceback and the smallest failing scene.

## LaTeX

- Use raw strings: `MathTex(r"\frac{1}{2}")`.
- Check balanced braces and required packages.
- Verify `latex`/`pdflatex` is on the render worker’s path.
- If LaTeX is intentionally unavailable, use the documented fallback for simple labels or queue review for proper formulas.

## Group types

`VGroup` accepts only `VMobject` children; `Text` and caption-related objects may be plain `Mobject`. Use `Group` for mixed collections and for `FadeOut(Group(*self.mobjects))`.

## Animation lifecycle

```python
circle = Circle()
self.play(Create(circle), run_time=0.8)
self.play(circle.animate.set_color(RED), run_time=0.5)
```

Do not animate a property on an object that has not been created/added. Chain related `.animate` operations rather than competing animations in one call.

## Common API traps

- Do not overwrite Manim’s reserved `.target` attribute with a custom target object; use a distinct name and `animate.become`/`Transform` appropriately.
- Python lists concatenate; use NumPy arrays for vector addition.
- Omit `aligned_edge=None`; use an explicit edge or omit the argument.
- `Text` does not accept `letter_spacing` on all versions; use `MarkupText` for Pango styling.
- `interpolate_color` expects `ManimColor` values, not raw hex strings, on affected versions.
- `Line`/`VMobject` stroke opacity and width may need `.set_stroke()` after construction.
- `CubicBezier` needs four control/anchor points; use a `VMobject` with `set_points_smoothly` for arbitrary point lists.

## Layout failures

Render a still and inspect bounding boxes. Clamp objects inside the safe frame, use adequate `buff`, shrink dense text, and replace stacked labels with a legend. If more than four visual layers are needed, split the scene.

## Arabic and fonts

Run the repository’s Arabic sanity scene. Check the actual rendered glyphs, connections, RTL order, mixed Arabic/Latin direction, and font availability. Do not infer visual correctness from the Python string alone.

## Resource and environment failures

Check FFmpeg, Cairo, Pango, fonts, LaTeX, memory, CPU, process count, and disk/output quotas separately. Reproduce with `-ql` and one scene before changing the generated script.

## Debug loop

1. Capture the exact command, traceback, environment, and scene name.
2. Reduce to the smallest failing scene.
3. Classify the failure.
4. Make one focused repair.
5. Render a low-quality regression frame.
6. Stop after the configured retry budget and create the human review packet.
