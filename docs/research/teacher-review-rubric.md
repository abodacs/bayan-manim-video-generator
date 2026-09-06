# Teacher review rubric

**Status:** Fixed rubric for the Bayan MVP review rounds (#89)
**Date:** 2026-09-06
**Scope:** Every generated video is scored on three dimensions, each on a
1–5 scale with written anchors. A video passes a dimension at 3 or higher;
the video passes overall when all three dimensions pass. Reviewers quote
findings verbatim in the review files; scores without findings are not
accepted rows.

## Dimension 1 — Mathematical correctness

Does the video state and show only mathematically true statements, and
does the final result match the prompt's example numbers?

| score | anchor |
| --- | --- |
| 5 | Every statement is correct; the worked result matches the prompt's example numbers exactly; notation follows textbook conventions. |
| 4 | Correct throughout with one cosmetic slip (e.g. a label reads "المجموع" where "الناتج" fits better); no wrong math. |
| 3 | Correct result, but one imprecise intermediate step (e.g. a skipped explanation of a sign). |
| 2 | One incorrect statement or a wrong final result that a viewer could memorize. |
| 1 | Multiple incorrect statements, or the video teaches a false rule. |

Pass threshold: **3**.

## Dimension 2 — Pedagogy

Does the sequence of beats teach the concept in a watchable order, and
does every visual actually support the learning objective?

| score | anchor |
| --- | --- |
| 5 | Beats build from concrete to abstract in a self-evident order; every animation supports the objective; the video needs no narration to follow. |
| 4 | Clear order with one beat that adds little; still followable alone. |
| 3 | Understandable, but one beat is redundant or out of order; a viewer must re-watch once. |
| 2 | The order confuses the concept, or half the animations are decorative. |
| 1 | No discernible teaching order; the video cannot be followed. |

Pass threshold: **3**.

## Dimension 3 — Arabic quality

Is the on-screen Arabic correctly shaped, right-to-left, readable, and
idiomatic for an Egyptian grade-6 classroom?

| score | anchor |
| --- | --- |
| 5 | Perfectly shaped and connected RTL text, natural phrasing, nothing clipped; digits match the chosen profile. |
| 4 | Correct and readable with one phrasing a native teacher would reword; shaping and RTL are right. |
| 3 | Readable but noticeably stiff or mixed-dialect; no shaping or direction defects. |
| 2 | A shaping/direction defect (disconnected letters, reversed order) or clipped text that hurts readability. |
| 1 | Unreadable Arabic, or the wrong language renders. |

Pass threshold: **3**.

## Overall pass rule

A lesson **passes** when all three dimensions are 3 or higher. A lesson
**fails** if any dimension is below 3. Per-unit and per-term pass rates
are the share of passing lessons; the MVP declaration (#68) requires the
recorded pass rate, not a target — a missed threshold is recorded as a
gap, never rounded up.

## Reviewer procedure

1. Watch `runs/<run id>/draft.mp4` once without pausing.
2. Re-watch pausing per beat; check the final frame against the prompt's
   example numbers.
3. Score the three dimensions; write findings verbatim (Arabic findings
   are quoted as-is); note the exact timestamp of any defect.
4. One row per lesson in the round's review file
   (`teacher-review-term1.md`, `teacher-review-final.md`).
