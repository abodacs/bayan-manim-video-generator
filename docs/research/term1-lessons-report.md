# Term-1 lesson set — generation report

**Status:** First real-generation round (Grade-6, Term 1)
**Date:** 2026-09-06
**Scope:** One generated lesson per Term-1 unit from the curriculum
inventory (#86): Numbers (GCF), Integers (comparing integers), Algebra
(evaluating expressions), Equations (one-step equations). This report is
the factual input to the teacher review round (#89).

## Generation settings (reproducibility)

- Model: `gemini-3.6-flash` via the Gemini OpenAI-compatible endpoint
  (the configured OpenAI-key account had no credits left; the failures
  below document the switch). Plans were requested through structured
  output; scenes through the minimal-fix code prompt.
- Quality: `draft` (pipeline default); profile `msa-western` (all four
  Term-1 units; no digit-note deviations in this term).
- Container: the standard `bayan/manim-smoke:0.20.1` image, no network,
  default resource policy (AgDR-0002).
- Pipeline at commit `feature/87-golden-prompt-set` (stop_after was not
  used; these are full renders).

## Per-lesson results (successful runs)

| run id | unit (#86) | topic | prompt | profile | model | tokens (prompt/completion) | cost estimate (USD) | repairs | outcome | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20260906T1406Z-41f75d2a` | Numbers | GCF | شرح القاسم المشترك الأكبر للعددين ١٢ و ١٨ | msa-western | gemini-3.6-flash | 1215 / 924 | 0.0000 | 2 | succeeded | repairs: `arabic_layout` (raw `Text` swapped to `ArabicText`), then `text_overflow` (edge-clipped layout reworked) — review `preview.png` closely |
| `20260906T1409Z-c84700dc` | Integers | Comparing integers | شرح مقارنة العددين -٥ و -٢ على خط الأعداد | msa-western | gemini-3.6-flash | 1114 / 1299 | 0.0000 | 1 | succeeded | repair: `render_crash` (first scene crashed the worker; the fix re-animated the comparison) |
| `20260906T1412Z-c9563700` | Algebra | Evaluating an expression | شرح إيجاد قيمة ٢س + ١ عندما س = ٤ | msa-western | gemini-3.6-flash | 1134 / 1152 | 0.0000 | 0 | succeeded | clean first pass through gates, render, and all four critic checks |
| `20260906T1415Z-2ec55b70` | Equations | One-step equation | شرح حل المعادلة س + ٣ = ١٠ | msa-western | gemini-3.6-flash | 1073 / 673 | 0.0000 | 0 | succeeded | clean first pass; all four critic checks passed |

All four successful runs passed every critic check (render artifacts,
duration bounds, overflow heuristic, beat coverage).

## Failed attempts (documented, not hidden)

| run id | unit | prompt | model | outcome | failure record |
| --- | --- | --- | --- | --- | --- |
| `20260906T1358Z-41f75d2a` | Numbers | GCF | (none reached) | failed | Upstream: the configured OpenAI-key account returned `insufficient_quota` ("no credits remaining") on every planning attempt. |
| `20260906T1358Z-ba8e31e5` | Numbers | GCF | gemini-flash-latest | failed | Plan and code stages produced output, but the code failed its gates and the repair round hit Gemini free-tier `429` (`RESOURCE_EXHAUSTED`, 5 requests/minute). |
| `20260906T1401Z-41f75d2a` | Numbers | GCF | gemini-flash-latest | failed | Same 429 shape during repair. |
| `20260906T1403Z-c84700dc` | Integers | Comparing integers | gemini-flash-latest | failed | Planning exhausted: `GenerateRequestsPerDayPerProjectPerModel-FreeTier` cap (20 requests/day for that model id). |
| `20260906T1405Z-41f75d2a` | Numbers | GCF | gemini-2.5-flash | failed | Provider returned 404: the model is no longer available to new accounts. |

These are upstream availability failures, not pipeline defects: in every
case the pipeline recorded attempts, degrading cleanly (typed records,
non-zero exit, no tracebacks) — which is itself a working demonstration
of BDD scenario #73 (offline/failed-provider fail-fast).

## Totals

| metric | value |
| --- | --- |
| lessons succeeded | 4 of 4 Term-1 units |
| failed attempts (documented above) | 5 |
| tokens, successful lessons (prompt + completion) | 4536 + 4048 = 8584 |
| tokens, failed attempts (partial calls) | 318 + 524 = 842 |
| cost estimate, successful lessons (recorded) | 0.0000 USD × 4 |
| repairs used, successful lessons | 3 (2 + 1 + 0 + 0) |

Cost note: the recorded estimates are `0.0000` because the pricing
constants table (#75) carries GPT prices only; `gemini-3.6-flash` pricing
was not published in a form this pipeline could pin at generation time.
Token counts above are the auditable quantity; extending
`bayan/pipeline/pricing.py` with the Gemini prices converts them to USD
without re-running anything.

## Notes for the teacher review round

- The GCF lesson consumed both repair attempts (`arabic_layout` then
  `text_overflow`); its preview should be reviewed first — the overflow
  repair reworked a layout that had been clipped at the frame edge.
- The Integers lesson needed a `render_crash` repair; check that the
  number-line comparison it renders actually shows -5 < -2 and not just
  the two numbers.
- Every repaired scene is preserved in `records/07-repair.json`
  (`code_after` per attempt) alongside the final `scene.py`; reviewers
  can diff what the model changed.
- Digit usage in all four scenes is Western, matching the locked
  `msa-western` profile decision.
- Artifacts live locally under `runs/<run id>/` (`draft.mp4`,
  `preview.png`, `records/`); they are intentionally not committed.
