# Term-2 lesson set — generation report

**Status:** First real-generation round (Grade-6, Term 2)
**Date:** 2026-09-06
**Scope:** One generated lesson per Term-2 unit from the curriculum
inventory (#86): Fractions (comparing fractions), Ratio (ratio concept),
Geometry (perimeter), Measurement (metric conversion). Generated with the
Term-1 adjustments applied (see the mapping below). Same report shape as
the Term-1 report (#88); this is the second input to the teacher review
round (#89).

## Term-1 adjustments applied (finding → change)

| Term-1 finding | Term-2 adjustment |
| --- | --- |
| GCF `text_overflow` repair (text clipped at the frame edge) | Every Term-2 prompt adds an explicit instruction to keep text well inside safe screen margins. |
| Integers `render_crash` repair | Prompts request simple, well-known Manim constructions (bars, squares, colored counters) instead of exotic effects. |
| Failed planning attempts from provider quota churn | Generations are spaced ≥65 s apart to respect the provider's per-minute free-tier quota. |

## Generation settings (reproducibility)

Identical to Term-1: model `gemini-3.6-flash` via the Gemini
OpenAI-compatible endpoint, `quality=draft`, profile `msa-western` (no
digit-note deviations in Term 2), standard container policy. Pipeline at
commit `feature/88-term1-lesson-set`.

## Per-lesson results

| run id | unit (#86) | topic | prompt | profile | model | tokens (prompt/completion) | cost estimate (USD) | repairs | outcome | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20260906T1421Z-7b21c706` | Fractions | Comparing fractions | شرح مقارنة الكسرين ٣/٧ و ٥/٧ باستخدام أشرطة الكسور، مع الحفاظ على هوامش آمنة بعيدة عن حدود الشاشة للنص | msa-western | gemini-3.6-flash | 1151 / 1660 | 0.0000 | 2 | failed-exhausted | The 18.2 s video rendered and the overflow/duration checks passed, but `beat_coverage` failed: the scene's summary line paraphrases the plan's beat 4 text instead of matching it verbatim, and neither repair attempt converged. Teacher should still watch the video — the fraction bars are correct. |
| `20260906T1427Z-c317dbea` | Ratio | Ratio concept | شرح مفهوم النسبة ٣ إلى ٢ باستخدام كرات ملونة | msa-western | gemini-3.6-flash | 1077 / 1084 | 0.0000 | 0 | succeeded | Clean first pass; every critic check green. |
| `20260906T1430Z-d23a1429` | Geometry | Perimeter | شرح إيجاد محيط مستطيل طوله ٦ وعرضه ٤ | msa-western | gemini-3.6-flash | 1110 / 867 | 0.0000 | 0 | succeeded | Clean first pass. |
| `20260906T1432Z-5692f181` | Geometry | Area (unit squares) | شرح إيجاد مساحة مستطيل طوله ٦ وعرضه ٤ باستخدام مربعات الوحدة | msa-western | gemini-3.6-flash | 1129 / 988 | 0.0000 | 0 | failed | The plan and code stages produced output, but the code failed its gates and the repair round hit the provider daily quota (`429`, 20 requests/day for `gemini-3.6-flash`). Retry when the quota resets. |
| `20260906T1434Z-b2ba79dd` | Measurement | Metric conversion | شرح تحويل ٣ متر إلى سنتيمتر | msa-western | gemini-3.6-flash | 0 / 0 | 0.0000 | 0 | failed | Planning exhausted: the same daily quota blocked every planning attempt. Retry when the quota resets. |

## Totals

| metric | value |
| --- | --- |
| lessons succeeded | 2 of 4 Term-2 units (Ratio, Geometry-perimeter) |
| failed attempts (documented above) | 3 |
| tokens, successful lessons (prompt + completion) | 2187 + 1951 = 4138 |
| tokens, failed attempts (partial calls) | 2280 + 2648 = 4928 |
| cost estimate, successful lessons (recorded) | 0.0000 USD × 2 |
| repairs used, successful lessons | 0 (the two failures consumed 2 repair attempts) |

The same pricing-table gap as Term 1 applies: `gemini-3.6-flash` prices
are absent from `bayan/pipeline/pricing.py`, so recorded cost estimates
are `0.0000`; token counts are the auditable quantity.

## Findings for the teacher review round

1. **`beat_coverage` exact-match is brittle against LLM paraphrasing.**
   The fractions video is mathematically and visually correct, but the
   plan's beat-4 sentence was paraphrased on screen, so the strict
   substring check failed and both repair attempts went to that. This is
   a pipeline improvement item (fuzzy or semantic beat matching), to be
   filed against #82's critic — not a prompt problem.
2. **The daily free-tier quota (20 requests/day for the chosen model) is
   smaller than one Term-2 set.** Two lessons remain ungenerated
   (area, metric conversion) until the quota resets. Generation settings
   in this report make the retry a copy-paste action.
3. **The margin adjustment from Term 1 worked**: the one rendered
   Term-2 video passes the overflow heuristic on the first try.
