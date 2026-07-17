# Visual Design Principles

## Twelve principles

1. Geometry before algebra when it improves intuition.
2. Opacity creates hierarchy: primary 1.0, context about 0.4, structure about 0.15.
3. One new idea per scene.
4. Keep a concept in a stable screen region while explaining it.
5. Color has semantic meaning and stays consistent.
6. Progressive disclosure: simple first, complexity second.
7. Use whitespace as a teaching tool.
8. Prefer one strong focal point over many equal-weight objects.
9. Show relationships with motion, arrows, or alignment—not paragraphs.
10. Preserve contrast and readable font sizes.
11. Use camera motion only to reveal structure or scale.
12. End each beat with enough stillness for the viewer to think.

## Layout templates

- **FULL_CENTER:** title or single object; generous margins.
- **LEFT_RIGHT:** intuition on the left, formal representation on the right.
- **TOP_BOTTOM:** object or graph above, explanation/legend below.
- **GRID:** small repeated items; reveal one row or column at a time.
- **PROGRESSIVE:** start with one object and add only the next necessary object.
- **ANNOTATED_DIAGRAM:** stable central object with one temporary annotation.

## Palette

Example palettes:

| Palette | Background | Primary | Secondary | Accent |
|---|---|---|---|---|
| Classic academic | `#1C1C1C` | `#58C4DD` | `#83C167` | `#FFFF00` |
| Warm academic | `#2D2B55` | `#FF6B6B` | `#FFD93D` | `#6BCB77` |
| Neutral technical | `#1A1A2E` | `#EAEAEA` | `#888888` | `#FFFFFF` |

Assign colors to concepts, not to random objects. Check contrast against the actual background and avoid dim colors for primary text.

## Typography

Use installed proportional fonts with Pango/Cairo; monospace is not a requirement. Validate the chosen font on the render worker. Use a readable hierarchy such as title 44–52, heading 32–40, body 26–32, label 20–26, then adjust for language and frame density. Keep Arabic in a font with tested glyph coverage.

Use `MathTex` for proper mathematical typesetting when LaTeX is available. Use `Text`/`MarkupText` for prose and simple Unicode symbols.

## Visual QA

Ask: Where should the eye go? What is context? What changed? Can the viewer identify the point without reading every label? If everything is equally bright, the hierarchy is missing. If the frame contains more than three or four competing ideas, split it.
