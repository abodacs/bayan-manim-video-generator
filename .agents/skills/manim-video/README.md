# Manim Video Skill

Portable `SKILL.md` instructions for Codex and Claude Code agents working on
educational and Arabic RTL Manim videos.

The skill is intentionally tool-agnostic: keep this directory as the source of
truth, then install or copy it into the agent’s local skill directory:

- Codex: `$CODEX_HOME/skills/manim-video/`
- Claude Code: `.claude/skills/manim-video/`

The workflow requires direct generated Manim Python, secure isolated rendering,
bounded self-debugging, grounded math validation, and visual review. It does
not require the deferred backend queue or audio pipeline for the first local
vertical slice.

Reference material is progressively disclosed through
[`references/index.md`](references/index.md), which routes agents to the 15
topic-specific Manim references without loading them all into context at once.
