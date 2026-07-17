# Updaters and Value Trackers

Use updaters when a relationship must remain true on every frame. Use ordinary animations when the transition is discrete and no dependency needs continuous enforcement.

## ValueTracker pattern

```python
t = ValueTracker(0)
dot = always_redraw(lambda: Dot(axes.c2p(t.get_value(), f(t.get_value()))))
tangent = always_redraw(lambda: tangent_for(t.get_value()))
self.add(dot, tangent)
self.play(t.animate.set_value(2), run_time=2.0)
```

Create the tracker, define dependent objects, then animate the tracker. Keep the redraw function small and deterministic.

## Updater types

- Lambda/updater: keep a label next to a moving object or an edge connected to nodes.
- `dt` updater: continuous rotation, drift, or time-based motion.
- `always_redraw`: rebuild a dependent object each frame; useful for curves, braces, and labels.
- `UpdateFromFunc`/`UpdateFromAlphaFunc`: apply custom per-animation updates.
- `turn_animation_into_updater`: repeat an animation continuously when that is intentional.

## Live values

Use `DecimalNumber`, `Integer`, or `Variable` with a tracker for counters and parameters. Format units and precision explicitly; do not replace a whole `Text` object every frame.

## Practical patterns

- Dot tracing a function with a tracker.
- Area under a curve that follows the moving boundary.
- A line and label that stay attached to a moving point.
- A graph whose parameter changes while the audience watches the effect.

## Lifecycle and performance

Remove or suspend updaters when the relationship is no longer needed. Avoid expensive LaTeX compilation or large object reconstruction inside a per-frame updater. If a scene becomes slow or visually unstable, replace the updater with a small number of explicit animation states.

## Common mistakes

- Forgetting to add the dependent object.
- Capturing a mutable variable with the wrong value in a lambda.
- Leaving an updater active while transforming the same object manually.
- Creating dozens of redraws for a static scene.
- Using an updater to hide a layout problem instead of fixing the layout.
