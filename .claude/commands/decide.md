# /decide — Technical Decision Gate

Forces structured decision-making and records an auditable Agent Decision
Record (AgDR) in the format this repo already uses under `docs/agdr/`
(see `AgDR-0001-type-checker.md` and `AgDR-0002-render-isolation.md`).

## Trigger

```
/decide "what you're deciding"
/decide how to validate Arabic glyph order without visual review
/decide whether to add a render-job queue now
/decide which worker boundary to use for hostile multi-tenant rendering
```

## Process

### 1. Parse decision topic

Extract the topic from input. If unclear, ask:

```
What technical decision do you need to make?
```

### 2. Gather context

Identify only decision-relevant context:

- What problem are we solving, and which Bayan stage does it touch (content / generation / rendering / validation / interface)?
- What constraints exist (trust boundary, Arabic correctness, mypy strict, no Manim in the content domain)?
- What is already in the codebase or an existing AgDR?

### 3. List options

Present 2–4 options in a table:

```markdown
| Option   | Pros | Cons |
| -------- | ---- | ---- |
| Option A | ...  | ...  |
| Option B | ...  | ...  |
```

### 4. Make the decision

State the chosen option with a justification ("because" clause).

### 5. Pick the next AgDR number

```bash
ls docs/agdr/AgDR-*.md 2>/dev/null | sort -V | tail -1 | grep -oP 'AgDR-\K\d+'
# Increment by 1, zero-pad to 4 digits (e.g. 0002 -> 0003), or start at 0001.
```

### 6. Create the AgDR file

Write `docs/agdr/AgDR-{NNNN}-{slug}.md`, matching the repo's existing format:

```markdown
# {short title}

**Status:** {Accepted | Proposed | Superseded by AgDR-NNNN} for {scope}

> In the context of {context}, facing {concern}, I decided {decision} to achieve {goal}, accepting {tradeoff}.

## Context
{Decision-relevant context only — 2–4 bullets.}

## Options Considered
| Option | Pros | Cons |
| ------ | ---- | ---- |
| ...    | ...  | ...  |

## Decision
Chosen: **{option}**, because {justification}.

## Consequences
- {consequence 1}
- {consequence 2}

## Not decided yet
{Optional — deferred concerns, e.g. queue, remote store, multi-tenant sandbox.}
```

Rules:

- Slug: lowercase, hyphens, ≤50 chars, from the title.
- Cross-link related records: `(see AgDR-0002-render-isolation.md)`.
- Status line and "Not decided yet" are optional; the Y-statement and options table are required.

### 7. Return the decision

Output so work can continue:

```
Decision: {chosen option}

AgDR-{NNNN} created at docs/agdr/AgDR-{NNNN}-{slug}.md

Proceeding with: {brief action}
```

## When to use

Use `/decide` for a hard-to-reverse choice or a change to an established boundary
(per `CONTRIBUTING.md`), for example:

- Choosing a render-worker boundary, sandbox, or job queue.
- Deciding how to validate Arabic shaping, RTL order, or glyph correctness.
- Picking a model/generation contract or dependency boundary.
- Changing the type-checking, testing, or reproducibility strategy.

Do not create an AgDR for a small, easily reversible change.

## Rules

1. **Always create an AgDR** — no decision without a record.
2. **Minimal context** — only what influenced the decision.
3. **Y-statement required** — one-line summary at the top.
4. **Options table required** — at least two options compared.
5. **Justification required** — the "because" clause is mandatory.
6. **Slug from the title** — lowercase, hyphens, ≤50 chars.
