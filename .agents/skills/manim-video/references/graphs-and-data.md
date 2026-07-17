# Graphs, Plots, and Data Visualization

Use chart objects to make a relationship visible, then animate only the change that matters.

## Axes and plots

```python
axes = Axes(
    x_range=[-3, 3, 1], y_range=[-2, 2, 1],
    x_length=8, y_length=5,
    axis_config={"include_numbers": False},
)
curve = axes.plot(lambda x: x**2, x_range=[-2, 2], color=BLUE)
self.play(Create(axes), Create(curve), run_time=1.5)
```

`Axes(include_numbers=True)` may require LaTeX. If LaTeX is unavailable, set `include_numbers=False` and add manual `Text` labels; see [no-latex-workaround.md](no-latex-workaround.md).

## Animated plots

Use a `ValueTracker` with `always_redraw` for a moving point, tangent, or parameter. Keep the function and its units visible so the motion has meaning.

## Charts and counters

- Use `BarChart` for comparisons, but label categories clearly and keep the number of bars small.
- Use `DecimalNumber` or `Integer` with a tracker for smooth counters instead of replacing `Text` every frame.
- Reveal a baseline before the treatment/result and use one consistent accent for the key difference.

## Algorithm visualization

For sorting, search, dynamic programming, or graph algorithms:

1. Show the data structure and invariant.
2. Highlight the active items.
3. Animate one operation.
4. Pause and state what changed.
5. Repeat only while the invariant remains legible.

Do not animate every internal operation if it obscures the algorithm’s idea.

## Graphs and vector fields

Use `Graph`/`DiGraph` for nodes and edges, `ArrowVectorField` for local direction, and `StreamLines` for flow. Build edges after nodes and use a moving dot or `ShowPassingFlash` to make data direction explicit.

## Complex and polar planes

Use `ComplexPlane` or `PolarPlane` when coordinate structure is the concept. Label only the axes and points needed for the current beat; fade labels that have become context.

## Data integrity

Ground every number, label units, preserve the source’s rounding policy, and test the plotted values independently. A beautiful chart with incorrect data is a failed video.
