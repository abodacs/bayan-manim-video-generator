# 04 — Scene planning and the plan file

> **Objective.** Write a `plan.md` — arc, scenes, palette, beats, timing —
> **before** code, so every scene carries exactly one concept.
>
> **Misconception it kills.** *"Planning slows you down."* A plan file prevents
> rework: it forces one concept per scene, visible beats, and deliberate pauses
> before you write a line of animation code.
>
> **Prerequisites.** [03 — Animations & rate functions](../03-animations-rate-functions/index.html).
>
> **Source reference.** `scene-planning.md`.

## Plan first, then code

Every lesson in this course ships a `plan.md` next to its `scene.py`. The plan
states the arc, the scene breakdown (one sentence per scene), the palette, and
a beat table — animation, `run_time`, wait. Code is then transcription, not
composition: you spend your attention on motion, not on structure.

A plan catches the expensive mistakes while they are still cheap:

- a scene trying to carry two concepts,
- a reveal with no reading time after it,
- colors that drift between scenes,
- an arc with no payoff.

## Pick an arc

| Arc | Beats | Use when |
|---|---|---|
| **Build-up** | seed → perturb → generalise → apply | extending something familiar |
| **Mystery** | question → explore → discover → exploit → reflect | a puzzle or paradox |
| **Zoom-out** | narrow view → context → origin → implication | situating a known result |

Build-up is the default: *simple → broken → fixed → payoff*.

## One concept per scene

A scene must be describable in **one sentence**. If it cannot, split it.
Production videos are several focused scenes, not one long scene with many
internal stages. Typical scene length is **30–90 s**; a 10-minute video is
usually **8–14 scenes**.

## Time every beat

The pause **after** a reveal matters more than the animation. A fast reveal
with a two-second hold beats a slow reveal with no time to think.

| Beat | run_time | Wait after |
|---|---:|---:|
| Title/intro appear | 1.5 s | 1.0 s |
| Simple object creation | 0.5–0.8 s | 0.5 s |
| Complex diagram build | 1.0–1.5 s | 1.0 s |
| Formula reveal | 2.0–3.0 s | 2.0 s |
| Key insight / "aha" | 1.5 s | 2.5 s |
| Transform/morph | 1.5–2.0 s | 0.5 s |
| FadeOut cleanup | 0.5 s | 0.2 s |

## Transitions

- **Clean break** (default when changing topics):

  ```python
  self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)
  self.wait(0.3)
  ```

- **Carry-forward** — keep one or two key elements when the next scene builds
  on them; fade everything else.
- **Transform bridge** — transform the previous result into the next scene's
  starting object when the relationship itself is the point.
- **Camera-driven** — zoom toward the detail the next idea lives in (subclass
  `MovingCameraScene` whenever `self.camera.frame` is touched).

## Consistency: constants, not vibes

Define shared constants at the top of every scene file — the same ones across
the whole video:

```python
BG = "#1C1C1C"
PRIMARY = "#58C4DD"   # the thing being explained
SECONDARY = "#83C167" # supporting structure
ACCENT = "#FFFF00"    # the key result / focus
```

Give colors **meanings** and keep them. Establish hierarchy with opacity:
primary `1.0`, context `0.4`, scaffolding `0.15`. Keep at most three or four
competing elements on screen.

## One practical + one production example

- **`example-practical.py` — `CleanBreak` and `CarryForward`.** Two short
  scenes: the default transition, then the carry-forward that keeps one
  element. Render both; feel the difference in continuity.
- **`example-production.py` — `OpacityLayers`.** The checklist applied end to
  end: constants, opacity layering, subcaptions, a ≥ 2.0 s thinking pause, and
  a clean exit.

## Self-critique (before any code)

1. Can I describe each scene in one sentence?
2. What does the viewer *feel* at each point — curious, surprised, satisfied?
3. Where is the payoff? Does every scene have a reveal?
4. Am I showing the geometry before the algebra?
5. Can I remove half the text?

## Verification step

1. Render `scene.py`. Check the beat table in `plan.md` against what you see:
   every reveal followed by its pause; the caption beat held ~2.5 s.
2. Render `example-practical.py` twice (`CleanBreak`, then `CarryForward`).
   The first leaves nothing behind; the second carries the circled term
   forward.
