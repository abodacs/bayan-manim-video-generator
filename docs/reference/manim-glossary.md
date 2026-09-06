# Manim CE Glossary

The shared Manim vocabulary for this repository. Adhere to these terms in docs, templates, and authored lessons.

| Term | Meaning |
|---|---|
| **Manim CE** | Manim Community Edition, the community-maintained fork. Target ≥ 0.20.1. |
| **Mobject** | "Mathematical object" — anything visible on screen (shapes, text, graphs). Base class `Mobject`. |
| **VMobject** | Vector mobject — a `Mobject` made of bezier curves; supports fill/stroke. Most primitives. |
| **Scene** | In Manim, a renderable unit: one `Scene` subclass with a `construct(self)` method. In Bayan's domain model, a *scene* is the visual sequence produced from a scene plan (see `CONTEXT.md`). |
| **construct** | The method Manim calls to build a scene: create mobjects, `play`, `wait`. |
| **play** | `self.play(animation, run_time=…)` — animates one beat. |
| **wait** | `self.wait(seconds)` — holds the frame; the *pause after a reveal*. |
| **run_time** | Duration in seconds of an animation. Set explicitly for important beats. |
| **rate function** | Maps progress 0→1 to eased progress (`smooth`, `linear`, `there_and_back`, `rush_into`). |
| **Animation** | Object passed to `play`: `Create`, `Write`, `FadeIn`, `FadeOut`, `Transform`, `Indicate`, … |
| **Transform** | Morph one mobject's points/look into another's. `ReplacementTransform` replaces the source. |
| **`.animate`** | Chained method syntax for a coherent state change: `obj.animate.shift(RIGHT).set_color(RED)`. |
| **VGroup** | Group of **compatible `VMobject` children** for joint transform/styling. |
| **Group** | Group of **mixed** `Mobject` types (e.g. shapes + `Text`). Used for scene cleanup. |
| **updater** | Per-frame function keeping a relationship true (label follows moving dot). |
| **ValueTracker** | An invisible mobject holding a scalar you animate; drives `always_redraw` dependents. |
| **always_redraw** | Rebuilds a dependent mobject every frame from current tracker values. |
| **MovingCameraScene** | Scene base class required whenever you animate `self.camera.frame` (zoom/pan). |
| **ThreeDScene** | Scene with a movable 3D camera (`set_camera_orientation(phi, theta)`); use only when depth matters. |
| **LinearTransformationScene** | Specialized scene for linear-algebra transforms on a coordinate grid. |
| **MathTex / Tex** | LaTeX-backed text. `MathTex` for math mode; always **raw strings** (`r"…"`). |
| **Text / MarkupText / Paragraph** | Non-LaTeX text (Pango). `MarkupText` for inline styling. |
| **DecimalNumber / Integer** | Live counters — **LaTeX-backed by default** (`mob_class=MathTex`) in 0.20.1. |
| **Axes / NumberPlane** | Coordinate systems. `include_numbers=True` needs LaTeX; `False` + manual labels avoids it. |
| **c2p** | "coords to point" — `axes.c2p(x, y)` converts data coords to a screen point. |
| **Brace / SurroundingRectangle / Angle** | Decorations: span label, highlight box, geometric angle. |
| **buff** | Buffer/spacing distance. Use `buff >= 0.5` near frame edges. |
| **safe frame** | The on-screen region content must stay inside; checked via bounding boxes. |
| **opacity layering** | Hierarchy by opacity: primary 1.0, context ~0.4, structure ~0.15. |
| **semantic color** | A color bound to a *concept* (e.g. yellow = "the result"), reused consistently. |
| **plan.md** | The pre-code planning document: arc, scenes, palette, beats, timing, grounding sources. |
| **HITL packet** | Human-in-the-loop review packet (prompt, plan, code, error, sources, attempted fixes) — emitted after ≤ 2 failed repair cycles. |
| **grounding** | Attaching every nontrivial claim/equation/number to an authoritative source. |
| **-ql / -qm / -qh** | Manim quality presets: low (draft), medium (review), high (production). |
| **RTL** | Right-to-left text direction (Arabic). Requires shaping (`arabic_reshaper`) + BiDi (`python-bidi`). |
