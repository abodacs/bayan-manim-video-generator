# Animation Design Thinking

Decide what the viewer must understand before deciding which Manim API to use.

## Animate or show static?

Animate when a sequence unfolds, a spatial relationship changes, something is built from parts, two states are compared, or time itself is the concept. Show a static diagram when the content is one labeled layout, a dense reference chart, or something the viewer needs to study without motion competing for attention.

Rule of thumb: if the explanation says “first X, then Y, then Z,” animate it. If it says “look at these parts of one picture,” start static.

## Convert narration into beats

Write the narration before the code. Mark each visual beat—the moment the screen changes—and make the visual appear slightly before the narration names it.

```text
“Consider a function.”       -> axes and curve appear
“At this point...”            -> dot appears
“The slope is positive.”     -> tangent and arrow appear
```

Each beat is one `self.play()` call or a small, intentional group of simultaneous animations. Keep the viewer’s attention on one or two moving elements at a time.

## Pacing

| Beat | Animation | Minimum pause |
|---|---:|---:|
| New object | 0.4–0.8s | 0.5s |
| New concept label | 0.8–1.2s | 1.0s |
| Formula or key reveal | 1.5–2.5s | 1.5–2.5s |
| Aha moment | 1.5–2.5s | 2.0–3.0s |
| Scene transition | 0.3–0.5s | 0.2–0.5s |

These are floors, not targets. If unsure, lengthen the pause. A fast reveal followed by a long hold is easier to understand than a slow reveal with no reading time. Vary tempo: build slowly, use quick supporting details, and create a deliberate pause before the key insight.

## Patterns that scale

- **Dim and reveal:** show the destination at low opacity, then brighten one term or object at a time.
- **Pipeline build:** introduce a box, grow the connecting arrow, then introduce the next box.
- **Zoom and return:** show the overview, zoom into one detail, explain it, and return to context.
- **Transform bridge:** preserve a visual identity when one scene’s result becomes the next scene’s starting point.

Do not animate everything, show equations without context, skip the “why,” or use identical timings for every beat.

## Optional creative divergence

Use this only when the user asks for an experimental or unconventional explanation:

- **SCAMPER:** substitute the usual metaphor, combine geometric and formal views, reverse the derivation, exaggerate a parameter, or remove notation entirely.
- **Assumption reversal:** identify the standard visualization, reverse one assumption (direction, dimensionality, continuity, or notation), and use the reversal to expose a hidden relationship.

Keep the learning objective and mathematical truth fixed while varying the metaphor.
