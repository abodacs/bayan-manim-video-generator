<!--
Context Is The Work. The diff shows WHAT changed; this body carries WHAT we meant,
WHAT constrained us, and HOW we know it's correct. Optimize for 3 reader modes:
30s intent → 3–7min reviewer guidance → deep-dive provenance. Don't paste the agent
transcript — serialize the plot points. See CONTRIBUTING.md → "Pull requests".
-->

## Goal
<!-- The outcome we're producing — not the mechanism. Why now? -->

## Non-goals
<!-- What we're explicitly NOT doing — data model? API/partner contract? refactors? -->

## Constraints / invariants
<!-- What would make this change wrong even if tests pass? Document boundaries,
Arabic rendering requirements, safety constraints, or domain vocabulary. -->

## Approach
<!-- The shape of the solution, in 2–4 lines. -->

## What changed (walkthrough)
<!-- Where should a reviewer look first? The plot points, in order. -->

## Verification
<!-- How do we KNOW this works? Commands run + outcomes. -->

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run mypy bayan`
- [ ] `uv run pytest`
- [ ] `uv run pre-commit run --all-files`
- [ ] Arabic sanity render or other manual checks, when relevant:

## Risks & rollback
<!-- How does this fail in prod, and how do we undo it? Feature flag %? Migration? DLQ? -->

<details>
<summary>Context manifest (audit / archaeology)</summary>

- **Prompt summary (not transcript):**
- **Repo anchors used:**
- **Decision points:**
- **Tools invoked:**

</details>

## Checklist

**General**

- [ ] I read `AGENTS.md` and relevant docs/agdr decision records
- [ ] Canonical terms from `CONTEXT.md` are used correctly
- [ ] No new AgDR is required, or an AgDR was added for the decision
- [ ] Docs updated (if needed)
