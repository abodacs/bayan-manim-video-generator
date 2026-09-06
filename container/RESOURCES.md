# Resources

High-trust sources grounding this course. The **primary source of truth** is the local skill; external
links are for craft, API verification, and inspiration.

## Primary (local, authoritative)
- `.agents/skills/manim-video/SKILL.md` — security, story, layout, camera, LaTeX policy.
- `.agents/skills/manim-video/references/index.md` — progressive-disclosure router.
- `.agents/skills/manim-video/references/*.md` — all 16 topical references (see lesson→reference map in `course/`).
- `bayan/utils/arabic_helper.py` — `ArabicText`, `reshape_arabic_text`, `rtl_glyphs` (RTL shaping via `arabic_reshaper` + `python-bidi`, font `Noto Sans Arabic`).
- `templates/*.py` — production Manim scenes in this repo (sine curve, grid transform, electric field, pendulum, etc.) used as worked examples.

## Official API & docs (verify against installed version)
- Manim Community docs — https://docs.manim.community/en/stable/ (API reference, examples, `manim.cfg`).
- Manim CE GitHub — https://github.com/ManimCommunity/manim/ (release notes, issue tracker for version-specific bugs).
- `manim --version` and the installed package source are the final arbiter for API behavior on 0.20.1+.

## Craft & inspiration (validate every API before copying)
- 3Blue1Brown scene source — https://github.com/3b1b/videos (narrative arc, pacing, semantic color).
- Manim School — https://manim.school/
- Academy of Manim (YouTube) — https://www.youtube.com/c/AcademyofManim
- ManiBench — https://github.com/nabin2004/ManiBench (scene-length statistics cited in scene-planning.md).

## Skill provenance
- Hermes Manim skill (MIT) — https://github.com/NousResearch/hermes-agent/tree/main/skills/creative/manim-video ; PR #23970. The local references are adapted from this, with corrections.

## Tooling for local rendering (student-run, not at build)
- FFmpeg — https://ffmpeg.org/ (scene stitching, optional audio mux).
- LaTeX (TeX Live / MiKTeX) — only required for `MathTex`/`Tex`/`Matrix`/numbered axes/`DecimalNumber`/`Integer`.
- Cairo + Pango — Manim's text/render backend; verify fonts on the actual render worker.
