# Educator study plan

**Status:** Plan — awaiting fieldwork
**Mode:** JTBD interviews + a plan-legibility probe
**Feeds:** issue #32 (its deliverable), then `/layers-user-needs`, `/layers-domain`

## Why this study

`PRODUCT_DIRECTION.md` rests on zero observation (`PROJECT_NORTH_STAR.md`
lines 32–35). Three assumptions are load-bearing and untested: that teachers
think in "aha" terms, that their real workflow has a gap a video fills, and that
a low-tech teacher can read and direct a storyboard board. This study tests all
three cheaply, in one session per educator.

## Learning goal

1. **Workflow & trigger.** The last time a textbook explanation was not enough to
   get a concept across — what did the teacher do? What did they start from, what
   did they reach for, where did it break? (Artifacts in hand + workarounds are
   the strongest need signal.)
2. **Value test.** When a visual explanation *works* for their students, what
   makes it work — a moment of insight, or covering the steps / curriculum / exam
   prep? (Tests whether "aha-moment video" matches their value model.)
3. **Thesis test (probe).** Can a teacher predict what a hand-authored storyboard
   teaches, spot what is wrong, and direct a correction before render?

## Who to recruit

- 6–8 educators (qualitative saturation). Math or physics, any grade, teaching
  bilingual Arabic/English students in Egypt.
- **Low-tech:** not animation or video specialists; in the last term they either
  made, or wanted but failed to make, a visual or digital explanation.
- Each session opens on a **real recent lesson or artifact**, not a hypothetical.

## Method

JTBD interview about a real past experience (~40 min) + a 5-minute storyboard
probe at the close. Record with consent; one note-taker if possible.

### Interview guide

- **Opening:** "Tell me about the last time you had to explain a math/physics
  concept and the usual explanation wasn't enough." Insist on a real one; refuse
  the hypothetical.
- **Timeline:** What triggered it? What did you start from (textbook page,
  worksheet, your own notes)? What did you try, in order? Where did it fall short?
- **Motivations / anxieties:** What did you hope students would *get*? What
  worried you — the explanation, or producing anything visual?
- **Value probe:** "Show me one visual or explanation that landed with students.
  What made it work?" Listen for *insight* language vs *coverage/steps* language.
- **Journey moments** (lesson setup → plan review → render diagnosis →
  acceptance): probe each lightly.
- **Close + probe:** hand them
  [`probe-storyboard-circle-area.md`](probe-storyboard-circle-area.md). "What will
  this teach? What's missing or wrong? What would you change before it rendered?"

### Probe protocol

Show the 3-card sequence and ask: (a) **predict** — what does this teach?
(b) **critique** — what's missing or wrong? (c) **direct** — what would you
change? (d) **trust** — would you accept this for your students? Optionally show
the flawed variant (slicing with no rearrangement) and ask what is missing —
tests whether they notice the insight never lands.

## Synthesis

One observation per note, tagged to the question it answers (**W** / **V** /
**T**). Raw quotes over summaries. Every note marked **observed / inferred /
assumed** — an *observed* claim with no quotable evidence is really *inferred*.
Listen for nouns and natural language → candidate domain objects for
`/layers-domain`.

## Candidate job stories (all ASSUMED — to test, not cite)

- *When [a concept is hard for students to grasp from the textbook alone], I want
  to [produce a short visual that makes the insight click], so I can [get through
  the lesson without losing them].*
- *When [I'm asked to turn a lesson into a video but I'm not an animation
  specialist], I want to [see and correct what it will show before it renders],
  so I can [trust it without becoming an expert].*
- *When [my explanation didn't land], I want to [know whether the math, the
  Arabic, or the visual was the problem], so I can [fix the right thing].*

Refine these at `/layers-user-needs` once Q1–Q2 have evidence.

## Decisions this study must capture (per #32)

1. **Blocking-vs-advisory checklist** — which checks should block a render and
   which need human review. Feeds #36. Working hypothesis: math/symbol
   correctness and Arabic shaping are blocking; pedagogical effectiveness,
   dialect, and pacing are advisory. Confirm or overturn with evidence.
2. **What teachers include in a natural request vs leave out** — feeds the
   prompt-vocabulary decision (`PRODUCT_DIRECTION.md` open decision #1).
3. **Provider/privacy** — already recorded for the model-assisted phase: GLM cloud
   (Zhipu/Z.ai), counsel-accepted, deferred to phase 2; the first-slice
   validation uses no provider. Confirm with educators whether sending their
   lesson content to a cloud model is *acceptable to them* (their comfort, not
   legality — legality is settled).

## Named gaps this study will not close

- **Student-viewer reception** — teachers are a proxy for whether the aha lands
  with bilingual Egyptian *students*.
- **Dialect preference at scale** — MSA vs Egyptian, beyond anecdote.
- **Longitudinal use** — whether a teacher returns after the first video.

## Output

A short decision note under `docs/research/` (this file, completed after
fieldwork) + an explicit list of unanswered questions. **No guesses** to fill
gaps.
