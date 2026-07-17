<!--
Context Is The Work. The diff shows WHAT changed; this body carries WHAT we meant,
WHAT constrained us, and HOW we know it's correct. Optimize for 3 reader modes:
30s intent → 3–7min reviewer guidance → deep-dive provenance. Don't paste the agent
transcript — serialize the plot points. See CONTRIBUTING.md → "PR Description Template".
-->

## Goal
<!-- The outcome we're producing — not the mechanism. Why now? -->

## Non-goals
<!-- What we're explicitly NOT doing — data model? API/partner contract? refactors? -->

## Constraints / invariants
<!-- What would make this change wrong even if tests pass? Latency budgets,
no-PII-logging, DDD-layer rules, ubiquitous language, idempotency, ... -->

## Approach
<!-- The shape of the solution, in 2–4 lines. -->

## What changed (walkthrough)
<!-- Where should a reviewer look first? The plot points, in order. -->

## Verification
<!-- How do we KNOW this works? Commands run + outcomes. -->

- [ ] `uv run pytest`
- [ ] `python scripts/validate_ddd.py`
- [ ] Integration / manual checks:

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

- [ ] I read `AGENTS.md` and relevant ADRs
- [ ] Ubiquitous language used correctly
- [ ] No new ADR required, or ADR drafted
- [ ] AgDR created for any technical decisions
- [ ] Docs updated (if needed)

**Backend** (if `backend/**` touched)

- [ ] Tests pass (`uv run pytest`)
- [ ] DDD validation passes (`python scripts/validate_ddd.py`)

**Frontend** (if `frontend/**` touched — run from `frontend/`)

- [ ] Tests pass (`pnpm test`)
- [ ] Lint + types pass (`pnpm lint && pnpm type-check`)
