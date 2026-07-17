# Scene Planning Reference

## Narrative Arc Structures

These structures reflect common patterns in 3Blue1Brown-style mathematical explanations.

### The “Build-Up” Arc

The most common structure for Grant’s explanations:

1. **Seed** — Show a simple, familiar case that activates prior knowledge.
2. **Perturb** — Change one parameter and show what happens.
3. **Generalize** — Reveal the pattern that connects all cases.
4. **Apply** — Use the pattern to solve something that was previously difficult or impossible.

This maps to: *simple → broken → fixed → payoff*.

### The “Mystery” Arc

1. **Question** — Pose a puzzle or apparent paradox.
2. **Explore** — Try the obvious approach and let it fail.
3. **Discover** — Stumble onto the key insight.
4. **Exploit** — Use the insight to solve the puzzle.
5. **Reflect** — Generalize: what else does this explain?

### The “Zoom Out” Arc

1. **Narrow view** — Show a specific result or formula.
2. **Context** — Place it in a larger framework.
3. **Origin** — Explain how it was discovered or derived.
4. **Implication** — Show what the result unlocks.

## Scene Granularity

A scene should contain **exactly one conceptual point**. If it cannot be described in one sentence, split it. A scene should make one idea visible, understandable, or surprising—not carry an entire subsection of the explanation.

Production videos generally benefit from several focused scenes rather than one long scene with many internal stages. Each scene should normally be a separate `.py` file in `active_projects/<video_name>/`; one script with several scene classes is acceptable for a small prototype. Separate scene files improve iteration, camera setup, and narrative rearrangement.

Typical scene length is **30–90 seconds**. As a reference point, ManiBench analyses reported:

- Colliding Blocks: 16 scenes, 2,193 lines — approximately 137 lines per scene.
- Gradient Descent: 16 scenes, 8,598 lines — approximately 537 lines per scene.
- Convolution: 13 scenes, 3,309 lines — approximately 254 lines per scene.
- Eigenvectors: 13 scenes, 5,120 lines — approximately 394 lines per scene.

## Scene Transitions

### Clean Break

Use this by default when changing topics:

```python
self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)
self.wait(0.3)
```

### Carry-Forward

Keep one or two key elements from the previous scene when the next scene builds directly on them. Fade everything else so the viewer can see what is being carried forward.

### Transform Bridge

Transform the previous result into the next scene’s starting object when the relationship itself is useful to show.

### Camera-Driven Transition

Use a zoom or pan when the next idea is contained inside the current visual:

```python
# Zoom into a detail, then fade to the next scene
self.play(self.camera.frame.animate.scale(0.3).move_to(target))
self.wait(0.5)
self.play(FadeOut(Group(*self.mobjects)))
```

The camera may reset after the cut if the next scene needs a fresh framing.

## Timing Patterns

| Context | Animation (`run_time`) | Wait after | Why |
|---|---:|---:|---|
| Title/intro appear | 1.5s | 1.0s | Gives the viewer time to read the premise. |
| Simple object creation | 0.5–0.8s | 0.5s | Lets the shape appear and register. |
| Complex diagram build | 1.0–1.5s | 1.0s | Gives the viewer time to parse the structure. |
| Formula reveal | 2.0–3.0s | 2.0s | Gives the viewer time to read the formula. |
| Key insight / “aha” | 1.5s | 2.5s | The longest pause lets the insight sink in. |
| Transform/morph | 1.5–2.0s | 0.5s | Keeps the relationship legible without stalling. |
| FadeIn label | 0.5–0.8s | 0.3s | Adds a quick annotation without distracting from the main idea. |
| FadeOut cleanup | 0.5s | 0.2s | Keeps the transition clean and decisive. |

The pause **after** the reveal is more important than the animation itself. A fast animation with a two-second hold beats a slow animation with no time to think. Give every reveal a deliberate pause, especially the key insight.

## Cross-Scene Consistency

Define shared constants at the top of each scene file, or import them from a shared project module:

```python
BG = "#1C1C1C"
PRIMARY = "#58C4DD"
SECONDARY = "#83C167"
ACCENT = "#FFFF00"

TITLE_SIZE = 48
BODY_SIZE = 30
LABEL_SIZE = 24

FAST = 0.8
NORMAL = 1.5
SLOW = 2.5
```

Assign colors to concepts and preserve those meanings across scenes. Use opacity to establish hierarchy:

- Primary concept: opacity `1.0`.
- Context or supporting information: opacity `0.4`.
- Background structure or scaffolding: opacity `0.15`.

## Scene Checklist

- [ ] Background color is set: `self.camera.background_color = BG`.
- [ ] Scene has exactly one conceptual point that can be described in one sentence.
- [ ] Purpose and audience prerequisite are clear.
- [ ] Layout and safe-frame budget are specified.
- [ ] Visual elements and animation beats are listed.
- [ ] Subcaptions are added for every animation: `self.add_subcaption(...)`.
- [ ] There is a `self.wait()` after every reveal, especially key reveals; key pauses are at least 1.5 seconds.
- [ ] At least one `self.wait(2.0)` gives the viewer time to think.
- [ ] Text near an edge uses `buff >= 0.5`.
- [ ] Text does not overlap other text or important visual elements.
- [ ] Color constants are used instead of hardcoded colors.
- [ ] Opacity layering is applied: primary `1.0`, context `0.4`, structure `0.15`.
- [ ] No more than three or four competing active elements are visible at once.
- [ ] Narration or subtitle text is included when enabled.
- [ ] Scene has a clean exit or an intentional carry-forward.
- [ ] Cleanup uses `Group(*self.mobjects)`, not `VGroup(*self.mobjects)`, for the full scene group.

## Duration Estimation

| Content | Typical duration |
|---|---:|
| Title card | 3–5s |
| Concept introduction | 10–20s |
| Formula reveal | 15–25s |
| Algorithm or process step | 5–10s each |
| Data comparison | 10–15s |
| “Aha moment” | 15–30s |
| Conclusion or summary | 5–10s |

A 10-minute video should usually have **8–14 scenes**, depending on how dense the mathematics is.

## Planning Template

```markdown
# [Video Title]

## Overview
- **Topic**: [Core concept]
- **Hook**: [Opening question]
- **Aha moment**: [Key insight]
- **Target audience**: [Prerequisites]
- **Length**: [seconds/minutes]
- **Resolution**: 480p (draft) / 1080p (final)
- **Arc**: build-up / mystery / zoom-out
- **Grounding sources**: [Books, papers, references, or datasets]

## Color Palette
- Background: #XXXXXX
- Primary: #XXXXXX -- [purpose]
- Secondary: #XXXXXX -- [purpose]
- Accent: #XXXXXX -- [purpose]
- Semantic color meanings: [What each color represents throughout the video]

## Scene Breakdown
Total: N scenes, ~X seconds each, ~Y minutes total

### Scene 1: [Name] (~Ns)
**One-sentence description**: [Exactly one conceptual point]
**Purpose/prerequisites**: [Why this scene exists and what the viewer needs to know]
**Layout**: [FULL_CENTER / LEFT_RIGHT / GRID / ZOOM_IN]
**Safe-frame budget**: [Where content may extend and where it must not]

#### Visual elements
- [Mobject: type, position, color, opacity, semantic role]

#### Animation sequence
1. [Animation] -- [what it reveals] (~Ns)
2. [Animation] -- [what it reveals] (~Ns)

#### Narration/subtitles
[Narration or subtitle text, if enabled]

#### Key pause
[Reveal] → wait(Ns) → [next beat]

### Scene 2: [Name] (~Ns)
...
```

## Self-Critique Questions

After planning, but before writing code, ask:

1. **One sentence per scene?** — If I cannot describe a scene in one sentence, is it trying to do too much?
2. **What does the viewer feel at each point?** — Curious, surprised, or satisfied? If any scene evokes confusion or boredom, how should it be reworked?
3. **Where is the payoff?** — Does every scene have an aha or reveal? If a scene only presents information, should it be cut or merged?
4. **Am I showing the geometry before the algebra?** — Is visual intuition presented before the formula?
5. **Is there a MovingCamera opportunity?** — Would a zoom or pan make the explanation feel more guided?
6. **Can I remove half the text?** — If a label is not pulling its weight, can it be dropped?
