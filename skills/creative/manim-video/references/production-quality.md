# Production Quality Checklist

Use this after the plan and again after the first low-quality render.

## Pre-code

- [ ] Audience, prerequisite knowledge, misconception, and aha moment are explicit.
- [ ] Narration is written and visual beats are marked.
- [ ] Each scene has one conceptual point, a purpose, layout, elements, timing, and exit.
- [ ] Palette colors have semantic meanings and remain consistent.
- [ ] Font availability, Arabic support, LaTeX, FFmpeg, and asset requirements are known.

## Text and layout

- [ ] Use a validated proportional font; do not require monospace.
- [ ] Keep important text inside a safe margin; check bounding boxes after `next_to` and `move_to`.
- [ ] Use `buff >= 0.5` near frame edges and avoid `aligned_edge=None` on affected Manim versions.
- [ ] Plan a safe frame budget before placement; clamp or reposition objects that leave it.
- [ ] Use explicit stage transitions instead of piling more than four vertical layers into one scene.
- [ ] Reduce font size or split the scene when text is dense.
- [ ] Use a legend for three or more narrow labeled regions.
- [ ] Never place a second label on top of an old label without a deliberate transform.
- [ ] Arabic is checked in rendered frames using the project helper and Noto Sans Arabic.

## Visual hierarchy

- Primary elements: opacity 1.0.
- Context: opacity about 0.3–0.5.
- Structural guides: opacity about 0.15.
- No more than three or four active elements should compete for attention.
- Color identifies concepts, not arbitrary objects.
- Use whitespace; if a frame needs more than four vertical layers, split it.

## Motion

- [ ] Animation variety follows meaning, not novelty.
- [ ] Every reveal has reading time; the key reveal has the longest pause.
- [ ] Camera motion has a pedagogical purpose.
- [ ] Objects are created/added before property animation.
- [ ] Scene cleanup uses `Group` for mixed mobjects.

## Post-render

- [ ] Inspect the title, densest frame, every key reveal, transitions, and final frame.
- [ ] Check clipping, overlap, accidental persistence, contrast, and visual hierarchy.
- [ ] Compare visuals against narration and the plan.
- [ ] Run independent math/fact validation; visual polish is not correctness evidence.
- [ ] Preserve the command, logs, stills, validation results, and final artifact.

## External craft references

For visual craft rather than API syntax, study [3Blue1Brown’s scene source](https://github.com/3b1b/videos), [Manim School](https://manim.school/), [Academy of Manim](https://www.youtube.com/c/AcademyofManim), and [ManiBench](https://github.com/nabin2004/ManiBench). Treat external examples as inspiration; still validate every API against the installed Manim version.
