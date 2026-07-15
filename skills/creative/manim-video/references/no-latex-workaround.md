# No-LaTeX Workaround

`MathTex`, `Tex`, `Matrix`, `Axes(include_numbers=True)`, `DecimalNumber`, and `Integer` require care with LaTeX. In Manim CE 0.20.1, `DecimalNumber` defaults to `mob_class=MathTex`, and `Integer` inherits from it. `Text`, `MarkupText`, `Paragraph`, shapes, `NumberPlane`, and `Axes(include_numbers=False)` do not invoke LaTeX by default.

## Capability decision

1. Detect `latex`/`pdflatex` before generating a scene.
2. Use LaTeX for precise mathematical typesetting when available.
3. Use Unicode symbols and manual labels for simple annotations when it is not.
4. Block or queue human review for formulas that cannot be represented faithfully without LaTeX.

Unicode is a fallback for simple display text, not an equivalent typesetting engine:

```python
Text("P ∝ cos(θ)", font_size=36)
Text("α + β = 180°", font_size=28)
Text("x → ∞", font_size=28)
```

Useful symbols include `α β θ π ∑ ∞ ≈ ≠ ≤ ≥ × ± → √ °`. Verify the selected font contains the required glyphs, especially for Arabic and mixed RTL/LTR text.

## Manual axis labels

```python
axes = Axes(
    x_range=[0, 100, 10], y_range=[0, 100, 10],
    x_length=8, y_length=4,
    axis_config={"include_numbers": False},
)
labels = VGroup()
for value in [0, 20, 40, 60, 80, 100]:
    point = axes.c2p(value, 0)
    labels.add(Text(str(value), font_size=16).move_to(point + DOWN * 0.3))
self.add(axes, labels)
```

Keep labels sparse and position them inside the safe frame. Prefer a legend with numbered regions over long labels above narrow bars.

## Capability matrix

| Feature | Default behavior | No-LaTeX path |
|---|---|---|
| `Text`, `MarkupText`, `Paragraph` | No LaTeX | Supported |
| Shapes, arrows, braces, `NumberPlane` | No LaTeX | Supported |
| `Axes(include_numbers=False)` | No LaTeX | Add manual labels if needed |
| `DecimalNumber` | Requires LaTeX by default (`mob_class=MathTex`) | Use `Text` for simple counters or test `mob_class=Text`; validate units/ellipsis |
| `Integer` | Requires LaTeX by default; inherits `DecimalNumber` | Use `Text` for simple counters or test `mob_class=Text` |
| `Axes(include_numbers=True)` | Uses LaTeX for tick labels | Disable numbers and add manual labels |
| `MathTex`, `Tex`, `Matrix` | Require LaTeX | No faithful fallback; install LaTeX or queue review |
