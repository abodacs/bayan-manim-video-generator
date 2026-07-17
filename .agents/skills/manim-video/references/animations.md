# Animations Reference

Animations are objects passed to `self.play()`. Set `run_time` explicitly for important beats.

## Common choices

```python
self.play(Create(circle), run_time=0.8)
self.play(Write(title), run_time=1.2)
self.play(FadeIn(group, shift=UP * 0.2), run_time=0.6)
self.play(FadeOut(group), run_time=0.4)
```

- `Create`, `Write`, `DrawBorderThenFill`, `GrowFromCenter`: introduce an object.
- `FadeIn`, `FadeOut`, `Uncreate`, `ShrinkToCenter`: control visibility.
- `Transform`, `ReplacementTransform`, `TransformMatchingTex`, `FadeTransform`: change one state into another.
- `Indicate`, `Circumscribe`, `Flash`, `ShowPassingFlash`: direct attention without changing the model.

## `.animate`

Use chained method calls for a single coherent state change:

```python
self.play(dot.animate.shift(RIGHT).set_color(YELLOW), run_time=1.0)
```

The mobject must already be on screen, or the animation must be a creation animation such as `Create(dot)`. Do not separately animate the same property in competing animations in one `play` call.

## Composition

- `AnimationGroup`: simultaneous animations with optional lag.
- `LaggedStart`: stagger repeated appearances.
- `Succession`: sequential animations within one `play` call.
- `ShowPassingFlash`: useful for data flow along a path.

Use composition to clarify relationships, not to create visual noise. Keep the active focus to one or two moving elements.

## Rate functions and paths

Use `smooth`, `linear`, `there_and_back`, `rush_into`, or a custom rate function to express intent. Use `MoveAlongPath` for meaningful trajectories. Use `Rotate` for a one-time rotation and an updater for continuous rotation.

## Reactive visuals

Use `ValueTracker`, `always_redraw`, or an updater when a label, brace, line, or curve must remain attached to a moving value. See [updaters-and-trackers.md](updaters-and-trackers.md) before adding per-frame logic.

## Timing patterns

```python
self.play(Write(equation), run_time=2.0)
self.wait(2.0)                 # reading time
self.play(Circumscribe(term), run_time=0.6)
self.wait(1.0)
```

Every reveal needs a pause. Use `FadeOut(Group(*self.mobjects))` for a mixed-mobject scene exit, not `VGroup(*self.mobjects)`.
