# Production Checklists

## Planning checklist

- [ ] State the target audience and prerequisites.
- [ ] Name the misconception or question the video resolves.
- [ ] Define the hook and the single aha moment.
- [ ] Choose a narrative arc: discovery, problem/solution, comparison, or build-up.
- [ ] Split the story into focused scenes; do not cram unrelated concepts into one scene.
- [ ] For every scene, record its purpose, layout, visual elements, animation sequence, subtitle/narration, and approximate duration.
- [ ] Choose a shared background, primary, secondary, and accent palette.
- [ ] Identify whether LaTeX, Arabic fonts, FFmpeg, or other optional capabilities are required.

## Code checklist

- [ ] One independently renderable `Scene` class per focused concept.
- [ ] Shared constants define colors, font choices, sizes, and normal/fast/slow timings.
- [ ] `self.camera.background_color` is set intentionally in every scene.
- [ ] Text uses a validated proportional font; Arabic uses the project’s RTL helper path.
- [ ] Every reveal has enough `self.wait()` time for comprehension.
- [ ] Edge text uses adequate buffer; labels do not overlap axes, arrows, or equations.
- [ ] Mobjects are added before they are animated.
- [ ] Scene cleanup uses `Group` when the collection can contain non-VMobjects.
- [ ] LaTeX strings are raw strings and are only used when the capability check passes.

## Grounding and math checklist

- [ ] List every nontrivial claim, equation, unit, and numerical constant in the plan.
- [ ] Attach each claim to user-provided or authoritative grounding where applicable.
- [ ] Ask an independent reviewer to challenge definitions, assumptions, signs, units, and edge cases.
- [ ] Run deterministic checks: substitute known values, verify dimensions, test invariants, and compare a known example.
- [ ] Mark illustrative simplifications explicitly; do not present them as universal facts.
- [ ] Fail or queue review when the fact checker is uncertain; visual polish is not evidence of mathematical correctness.

## Render and review checklist

- [ ] Run the repository’s dependency and Arabic smoke checks.
- [ ] Render each scene at low quality before a production render.
- [ ] Extract stills around the first reveal, densest layout, transition, and final frame.
- [ ] Check for clipping, overlap, unreadable text, accidental persistence, and inconsistent visual language.
- [ ] Check that camera movement supports the explanation rather than adding spectacle.
- [ ] Stitch scenes only after individual scenes pass.
- [ ] Add audio only after the visual cut is stable; audio is optional in the first vertical slice.

## Self-debugging loop

Use distinct review passes, whether implemented as subagents or sequential roles:

1. **Planner/grounding reviewer:** verifies the story, claims, equations, and scene contract.
2. **Code reviewer:** checks imports, Manim API usage, object lifecycle, and sandbox policy.
3. **Render debugger:** classifies the traceback as dependency, syntax, API, layout, or resource failure.
4. **Visual critic:** inspects stills and identifies overlap, clipping, pacing, and hierarchy issues.
5. **Math checker:** independently validates equations, units, examples, and stated conclusions.

Allow at most two autonomous repair cycles. Each cycle must produce a concrete code diff and a new low-quality render. If the same failure persists, write `review_packet.md` with the prompt, plan, script, command, traceback, stills, validation findings, and attempted fixes, then stop automatic mutation.

## Capability fallbacks

| Capability | Preferred path | Fallback |
|---|---|---|
| LaTeX | `MathTex`, `Tex`, and LaTeX-backed axes | `Text`, Unicode math glyphs, manual labels, or a clear blocked status |
| Arabic text | `ArabicText` with `Noto Sans Arabic` and RTL smoke test | Stop and report missing font/render support |
| Camera motion | `MovingCamera` for meaningful zoom/pan | Static camera with stronger framing |
| Audio | Add voiceover after visual lock | Deliver silent MP4 plus narration metadata |

## Influences

- [Hermes Manim video skill](https://github.com/NousResearch/hermes-agent/tree/main/skills/creative/manim-video)
- [Hermes issue #23969](https://github.com/NousResearch/hermes-agent/issues/23969)
- [Hermes PR #23970](https://github.com/NousResearch/hermes-agent/pull/23970)
