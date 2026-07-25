# AI Code Review

You are reviewing a pull request for **Bayan** — an Arabic-first AI-powered Manim
video generator (Python 3.11+, `uv`, Manim Community Edition, mypy strict, ruff,
pytest). The repo's central invariant: model output and generated scene code are
**untrusted**, executed only in an isolated render worker; Arabic shaping, RTL
direction, and glyph animation must be visually correct.

Follow this process exactly. Output only the final report template.

## Step 1: Establish the diff

```bash
git fetch origin main --depth=100
git merge-base origin/main HEAD | xargs git diff --stat
git merge-base origin/main HEAD | xargs git diff
git log --oneline origin/main..HEAD
```

If `origin/main` is unavailable, fall back to `git merge-base HEAD` against the
default branch and note the fallback in the report.

## Step 2: Measure change size

Count total code lines changed (added + removed):

- **S** (1–100): proceed normally
- **M** (101–300): proceed if one logical change
- **L** (301–700): flag for splitting
- **XL** (700+): block — "This change is too large for reliable review (N lines). Split before requesting review."

## Step 3: Read context

Read the intent and the boundaries the change must respect:

- PR description, linked issues, commit messages (Conventional Commits). If none, warn: "No linked spec/issue found — correctness judged from code intent only."
- `AGENTS.md` — PR/commit rules; English-only comments; Arabic in string literals.
- `CONTEXT.md` — canonical terms (Lesson, Lesson segment, Scene plan, Scene, Render job, Artifact, Validation result, Review). Flag synonym drift.
- `docs/ARCHITECTURE.md` — system boundaries and trust model.
- `docs/DEVELOPMENT.md` — dev loop and test strategy.
- `docs/agdr/` — any decision this change touches or contradicts.

## Step 4: Analyze blast radius

No external graph tools are available. Use the repo directly:

1. Grep/Glob for callers and importers of changed public symbols.
2. For `bayan/renderer/` or security changes, confirm the worker trust boundary is preserved: no network, no app secrets, read-only root, `--cap-drop=ALL`, `no-new-privileges`, bounded CPU/memory/PIDs, `noexec` tmpfs, allowlisted env, read-only source mount, explicit output mount, `docker rm --force` on every exit path.
3. Check no change executes or imports generated/Manim scene code into the host.

Record: changed symbols/files, direct callers, affected stage
(content → generation → rendering → validation → interface), test coverage, and
whether a render/visual check is required.

## Step 5: Review tests and validation first

For each test file: name describes behavior; tests behavior not implementation;
happy path + Arabic/edge cases; meaningful assertions. Behavior that needs native
rendering — Arabic shaping, RTL order, glyph order, frame composition, animation
order — cannot be replaced by unit tests. Flag missing checks:

```bash
uv run manim -ql bayan/utils/sanity_check.py ArabicSanityCheck
python3 scripts/container_smoke.py --output /tmp/bayan-review-smoke
```

Flag untested changed code by criticality: P0 boundary/security/Arabic correctness,
P1 domain rules, P2 helpers, INFO render-only scenes.

## Step 6: Score each changed file across 8 axes (0–4)

**1 — Correctness**: spec match; edge cases (empty, boundary, mixed scripts,
diacritics); error paths; off-by-one; return-type consistency; structured failures
that name the stage and relevant inputs.

**2 — Trust boundary & safety** (highest weight): generated/Manim scene code stays
untrusted data; never executed or imported in the host; isolated worker preserves
no-network / no-secrets / read-only-root / cap-drop / no-new-privileges / bounded
CPU-memory-PIDs / noexec-tmpfs / allowlisted-env / read-only-source-mount /
explicit-output-mount / forced cleanup; no command or path injection into Docker or
subprocess args; paths resolved and validated before mounting.

**3 — Arabic & i18n correctness**: `reshape_arabic_text` reshaping + BiDi applied
before render; RTL visual glyph order correct; `Noto Sans Arabic` coverage assumed;
ligatures and diacritics preserved; Latin/digits handled correctly; visual vs
logical order respected.

**4 — Architecture boundaries**: content domain has no Manim/model-SDK/storage
imports; renderer exposes a small serializable request/result interface and does
not leak Manim CLI details; Manim scenes stay thin (composition/animation only);
deterministic and model-assisted generators share one contract; explicit data
between stages; CLI does not own domain rules or execute generated code; the
`sanity_check.py` exclusion from mypy/ruff star-import noise is intentional
(AgDR-0001) — do not relocate logic into it.

**5 — Types & static checks**: `bayan/` (excl. `sanity_check.py`) passes mypy
**strict** — explicit types, `from __future__ import annotations`, no `Any`
leakage; ruff (E/F/I/UP/B/SIM/C4) clean; Python comments English-only (Arabic only
in string literals, enforced by `scripts/check_python_comments.py`).

**6 — Tests & validation evidence**: unit tests for deterministic helpers and
domain rules; smoke tests for clean imports; render checks for native/Arabic
behavior; validation reports **evidence, not just a boolean**; the coverage gate is
intentionally permissive — do not penalize, but flag uncovered boundary/security/
Arabic logic.

**7 — Reproducibility & isolation hygiene**: typed manifests with phase status,
bounded diagnostics, source hashes, image metadata, relative artifact paths; atomic
writes (tmp file → `replace`); deterministic container names; bounded logs/output;
explicit timeouts on every phase; cleanup on every exit path.

**8 — Readability & conventions**: descriptive names; canonical CONTEXT.md terms;
no deep nesting or oversized functions; no dead code; Conventional Commits and
branch prefix (`feature/` `fix/` `docs/` `chore/` `refactor/`) correct; PR created
via the GitHub REST API per `AGENTS.md`.

Render/scene-only or docs-only changes: score axes 1, 4, 8 only; mark the rest N/A.

## Step 7: Compute risk

Sum scores (0–32). Apply modifiers:

- −4 touches the render/security boundary or executes/generated code
- −3 changes Arabic shaping, BiDi, or glyph ordering
- −2 >20 direct dependents
- −2 changed boundary/security/Arabic code with no test or visual check
- −1 size L or XL
- −1 crosses 3+ stages/modules

Clamp at 0. Classify:

| Score   | Risk      | Action                      |
| ------- | ---------- | --------------------------- |
| 28–32   | LOW        | Approve                     |
| 22–27   | MODERATE   | Approve with suggestions    |
| 16–21   | ELEVATED   | Request changes             |
| 10–15   | HIGH       | Request changes + re-review |
| 0–9     | CRITICAL   | Block, escalate             |

Any P0/P1 finding or untested boundary/Arabic change: add a note recommending human
plus visual review.

## Step 8: Classify findings

| Severity      | Meaning                                                        | Blocks?    |
| ------------- | -------------------------------------------------------------- | ---------- |
| P0 BLOCKER    | Trust-boundary breach, untrusted code in host, Arabic regression, crash, broken func | Yes        |
| P1 MUST-FIX   | Missing critical test/check, wrong boundary, bug risk          | Yes        |
| P2 SHOULD-FIX | Suboptimal but functional                                      | No (defer) |
| P3 NIT        | Style, naming, minor optimization                             | No         |

Every P0/P1 must include: axis, `file:line`, description, concrete fix.

## Step 9: Report

Output ONLY this template, filled in. No preamble, no closing summary.

```
## Code Review: [PR ref / branch name]

### Context
- **Spec/Issue**: [link or "none found"]
- **Change size**: [S/M/L/XL] ([N] lines)
- **Risk level**: [LOW/MODERATE/ELEVATED/HIGH/CRITICAL] ([score]/32)
- **Stages touched**: [content/generation/rendering/validation/interface]

### Blast Radius
- Changed: [N] symbols in [M] files
- Direct callers (d=1): [count/list]
- Boundary / Arabic impact: [yes/no — detail]
- Test/visual coverage: [N]/[M] changed functions have tests; sanity render needed? [yes/no]

### Axis Scores

| #         | Axis                          | Score   | Key Finding |
| --------- | ----------------------------- | ------- | ----------- |
| 1         | Correctness                   | /4      |             |
| 2         | Trust boundary & safety       | /4      |             |
| 3         | Arabic & i18n correctness     | /4      |             |
| 4         | Architecture boundaries       | /4      |             |
| 5         | Types & static checks         | /4      |             |
| 6         | Tests & validation evidence   | /4      |             |
| 7         | Reproducibility & isolation   | /4      |             |
| 8         | Readability & conventions     | /4      |             |
| **Total** |                               | **/32** |             |

### Findings

#### P0 — Blockers
[list or "None."]

#### P1 — Must Fix
[list or "None."]

#### P2 — Should Fix
[list or "None."]

#### P3 — Nits
[list or "None."]

### Untested / Unverified
[boundary/security/Arabic logic lacking a test or visual check, or "All covered."]

### What's Done Well
- [specific positive]

### Verdict
**[APPROVE / REQUEST CHANGES / BLOCK — ESCALATE]**

[1–2 sentence rationale]
```

## Step 10: Self-check

Before outputting verify:

- Every finding has `file:line`; every P0/P1 a concrete fix.
- Scores are consistent with findings (no 4/4 on an axis with a P1 there).
- Blast radius is honest ("could not be determined" if so).
- Boundary and Arabic claims reference the specific code.
- At least one item in "What's Done Well".
