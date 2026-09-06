# Teacher review round — Term 1

**Status:** Awaiting teacher scores (this file is prepared; only the
Score and Findings columns are filled by the human reviewer)
**Date prepared:** 2026-09-06
**Rubric:** `docs/research/teacher-review-rubric.md` (math correctness,
pedagogy, Arabic quality; 1–5 each; pass at 3; overall pass = all three
pass)
**Videos:** `runs/<run id>/draft.mp4` (rendered locally, not committed)

## Term-1 lessons to review

| run id | unit (#86) | topic | prompt | repairs | score: math | score: pedagogy | score: Arabic | findings (verbatim) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20260906T1406Z-41f75d2a` | Numbers | GCF | شرح القاسم المشترك الأكبر للعددين ١٢ و ١٨ | 2 (`arabic_layout`, then `text_overflow`) | | | | |
| `20260906T1409Z-c84700dc` | Integers | Comparing integers | شرح مقارنة العددين -٥ و -٢ على خط الأعداد | 1 (`render_crash`) | | | | |
| `20260906T1412Z-c9563700` | Algebra | Evaluating an expression | شرح إيجاد قيمة ٢س + ١ عندما س = ٤ | 0 | | | | |
| `20260906T1415Z-2ec55b70` | Equations | One-step equation | شرح حل المعادلة س + ٣ = ١٠ | 0 | | | | |

## Reviewer notes

- The GCF preview deserves the closest look: its second repair was for
  the `text_overflow` heuristic (content had reached the frame edge).
- The Integers video's first scene crashed the worker; the repaired
  scene re-animated the comparison. Verify -5 < -2 is actually shown.
- Term-1 pass rate feeds the MVP declaration; record it here when the
  round completes: pass rate = ___ of 4.
