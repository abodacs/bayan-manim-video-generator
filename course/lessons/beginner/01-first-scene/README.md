# 01 — Install Manim and render your first Scene

> **Objective.** Install Manim Community Edition (≥ 0.20.1) and render a first
> scene from the command line.
>
> **Misconception it kills.** *“Manim is a GUI video editor.”* It is not. Manim
> is a **Python library**: you write a `Scene` class in a `.py` file and render
> it headlessly to a video file. There is no timeline, no drag-and-drop.
>
> **Prerequisites.** None — this is the entry point.
>
> **Source reference.** `rendering.md`, `mobjects.md`.

## What Manim actually is

Manim Community Edition (Manim CE) takes Python code and produces an `.mp4`.
A **Scene** is one renderable unit with a `construct(self)` method. Inside it you
build **mobjects** (the visible objects), drive them with `self.play(...)`, and
hold frames with `self.wait(...)`. The canonical artifact is the Python file
itself — treat it as code you review, not a black box.

This course never renders video for you. Every `scene.py` is real, runnable
Manim that **you** render locally.

## Install (one-time)

```bash
pip install "manim>=0.20.1"     # Manim Community Edition
manim --version                 # confirm it is on your PATH
ffmpeg -version                 # Manim needs FFmpeg to write video
```

Manim also needs Cairo and Pango for text/graphics. On most systems `pip
install manim` pulls prebuilt wheels that bundle them; if a build fails, install
`cairo` and `pango` via your system package manager first. See
[`rendering.md`](.agents/skills/manim-video/references/rendering.md).

> LaTeX is **only** needed for `MathTex`/`Tex`/`Matrix`, numbered axes, and
> `DecimalNumber`/`Integer`. This first scene uses none of those, so you do not
> need a LaTeX installation yet.

## The annotated minimal scene

This is `scene.py`. Read it top to bottom — every line is intentional:

```python
from manim import *

BG = "#1C1C1C"  # named constant, not a magic hex scattered through the file


class HelloManim(Scene):
    """Write a title, draw a circle, pause after each reveal, then clean up."""

    def construct(self):
        self.camera.background_color = BG

        title = Text("Hello, Manim", font_size=56)
        circle = Circle(radius=1.2, color=BLUE)

        # Reveal the title, then HOLD so the viewer can read it.
        self.play(Write(title), run_time=1.5)
        self.wait(1.0)

        # Lift the title to make room, then create the circle.
        self.play(title.animate.to_edge(UP), run_time=0.8)
        self.play(Create(circle), run_time=1.0)
        self.wait(1.5)

        # Clean exit: fade every on-screen mobject together.
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.6)
```

Annotated beats:

- `self.play(Write(title), run_time=1.5)` — one **animation** over 1.5 s.
- `self.wait(1.0)` — the **pause after the reveal**. This is not optional padding;
  it is how the viewer gets reading time. A fast reveal + a long hold beats a
  slow reveal with no hold.
- `title.animate.to_edge(UP)` — the `.animate` syntax chains a coherent state
  change. The mobject must already be on screen.
- `Create(circle)` — a *creation* animation; this is what puts `circle` on screen.
- `Group(*self.mobjects)` — groups **all** on-screen mobjects (possibly mixed
  types) so they fade out together. Use `Group`, not `VGroup`, for scene cleanup.

## Render it

```bash
manim -ql scene.py HelloManim      # low-quality draft (fast)  -> media/videos/...
manim -qh scene.py HelloManim      # production quality, only after review
manim -ql --format=png -s scene.py HelloManim   # a single still preview
```

Always give the explicit scene name (`HelloManim`). Avoid the interactive scene
chooser in automation. The output lands under `media/videos/scene/.../*.mp4`.

## One practical + one production example

- **`example-practical.py` — `TitleCard`.** A title card you will rebuild often:
  fade in a title and subtitle, hold, fade out. The smallest useful scene.
- **`example-production.py` — `ConventionsDemo`.** Same idea, but obeys **every**
  convention the rest of the course enforces: named semantic colours, opacity
  layering (primary `1.0` / context `~0.4` / structure `~0.15`), a pause after
  every reveal, a subcaption per beat, and `Group(*self.mobjects)` cleanup.

## Pitfalls and how to detect them

| Pitfall | Symptom | Detection |
|---|---|---|
| Animating a mobject before it is on screen | Nothing changes, or an error | The property animation must follow a `Create`/`add`; creation animations (`Create`, `Write`, `FadeIn`) are what add the object. |
| No `self.wait()` after a reveal | Video feels frantic, unreadable | Every reveal needs a hold; key reveals ≥ 1.5 s. |
| Forgetting `run_time` on important beats | Default timing feels arbitrary | Set `run_time` explicitly for every `play`. |
| Mixing `VGroup`/`Group` for cleanup | Error if non-`VMobject` children present | Cleanup the whole scene with `Group(*self.mobjects)`. |

## Verification step

1. `manim --version` prints ≥ 0.20.1.
2. `manim -ql scene.py HelloManim` writes a file under `media/videos/`.
3. Open the `.mp4`: you should see the title write on, the circle appear, holds
   between beats, and a clean fade-out. If any beat has no pause, re-render after
   adding `self.wait(...)`.

When you can do the three steps above, take the quiz.
