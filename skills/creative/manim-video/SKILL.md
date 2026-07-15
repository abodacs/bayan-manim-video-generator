---
name: manim-video
description: Generate Manim videos; use for educational animations.
version: 1.0.0
platforms: [linux, macos, windows]
author: "Abdullah Mohammed (@abodacs); Hermes Agent"
---

# Manim Video Skill

Generate grounded educational videos with Manim Community Edition, direct Python scene generation, secure rendering, and visual review. This skill owns planning, code, rendering, and critique; it does not require a JSON-to-Manim compiler, backend queue, or audio pipeline for the first local slice.

## When to Use

Use for mathematical explainers, Arabic RTL animations, algorithm visualizations, paper explainers, architecture diagrams, data stories, and debugging or reviewing Manim scenes.

## Prerequisites

- Manim Community Edition 0.20.1 or newer, with Cairo/Pango and validated fonts.
- FFmpeg for render inspection and scene stitching.
- LaTeX only when using `MathTex`, `Tex`, `Matrix`, or numbered axes; use the no-LaTeX reference otherwise.
- The repository’s Arabic helper and smoke scene for Arabic output.

## How to Run

Follow the project’s render command for a low-quality draft first, inspect stills and logs, then render production quality only after the review gates pass. Load targeted guidance from [references/index.md](references/index.md) instead of loading every reference into context.

## Quick Reference

- The canonical generated artifact is Manim Python. Treat it as untrusted input.
- Security: no network, no Docker socket, no host secrets, non-root execution, read-only root, output-only writes, and bounded CPU/memory/process/time/output limits.
- Story: geometry before algebra, one conceptual point per scene, consistent semantic colors, and a deliberate pause after every reveal.
- Layout: use safe-frame checks, proportional fonts, and `Group(*self.mobjects)` for mixed-mobject cleanup.
- Camera: subclass `MovingCameraScene` whenever using `self.camera.frame`.

```python
class ZoomScene(MovingCameraScene):
    def construct(self):
        target = Circle()
        self.add(target)
        self.play(self.camera.frame.animate.scale(0.6).move_to(target), run_time=1.5)
        self.wait(1.5)
```

## Procedure

1. Plan the audience, misconception, hook, aha moment, narrative arc, scene list, palette, typography, and duration.
2. Write one focused, independently renderable scene per conceptual point.
3. Validate generated Python against the import/API policy before execution. Ground equations and claims in supplied or authoritative sources.
4. Render a low-quality draft, extract key stills, and inspect overlap, clipping, Arabic shaping, pacing, and contrast.
5. Run separate planner, code-review, render-debug, visual-critique, and math-check passes.
6. Allow at most two autonomous repair cycles. Include the exact traceback and failing scene in each repair request.
7. If compilation errors or incorrect math remain, stop mutation and create a human-in-the-loop review packet with the prompt, plan, code, logs, stills, sources, and attempted fixes.

## Pitfalls

- `DecimalNumber` and `Integer` use LaTeX-backed `MathTex` by default in Manim CE 0.20.1; do not classify them as automatically LaTeX-free.
- `VGroup` is for compatible `VMobject` children; use `Group` for mixed mobjects and scene cleanup.
- Use raw strings for LaTeX and do not pass `aligned_edge=None` on affected Manim versions.
- Do not animate a mobject before it is created or added. Do not let generated code access files, processes, sockets, or dynamic imports.
- Visual QA does not prove mathematical correctness; independently check units, assumptions, invariants, and known examples.

## Verification

- Run `scripts/run_tests.sh tests/skills/test_manim_video_skill.py -q` or the repository-equivalent test command.
- Confirm the reference inventory and frontmatter validation test pass without network access.
- Re-run the Arabic smoke scene and a low-quality render after any scene or dependency change.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Manim code compilation errors | Use a bounded multi-agent self-debugging loop; fall back to a human-in-the-loop review queue. |
| LLM hallucinations or incorrect math | Use grounding, system constraints, independent fact-checking, and deterministic spot checks. |
| Malicious generated code | Apply static policy validation and execute only inside the hardened sandbox. |
| Overlap, clipping, or unreadable visuals | Inspect stills, enforce safe spacing, limit simultaneous elements, and require visual QA. |
| Missing LaTeX, fonts, or FFmpeg | Detect capabilities before rendering and use an explicit fallback or blocked status. |
