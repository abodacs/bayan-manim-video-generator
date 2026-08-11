# Product Direction

**Status:** Proposed — post-POC product direction

> This document captures the product Bayan is becoming after the
> [POC](PROJECT_NORTH_STAR.md) proved its foundations. The repository as it
> stands is a proof of concept; this is where the product goes next.

## Product

Bayan turns a low-tech teacher's lesson intent into a short, *aha-moment*
mathematics or physics video for bilingual (Arabic/English) Egyptian students —
with correctness and pedagogy guaranteed by construction, not by trusting
generated code.

## Primary users

- **Author:** a teacher who understands the lesson but is not a Manim, Arabic
  typography, or video specialist, and writes natural-language prompts. The
  system must not require them to read code or scene-plan JSON.
- **Viewer:** an Arabic/English bilingual student. Mixed Arabic, Latin, and
  numerals is the default on screen, not an edge case.
- **Engineer:** the system stays debuggable and extensible as it grows.

## Core thesis

The product is a **storyboard wall**, not a prompt-to-video pipeline. Before any
final render, the teacher sees the whole video as reviewable cards and directs
it with sentences while changes are cheap. This is pre-production, automated —
the pattern popularized by HyperFrames (HeyGen), adapted below for mathematics
and physics.

The wall resolves the load-bearing tensions the POC surfaced:

- **Ambiguity** is resolved by the teacher directing the plan cards, not by a
  model guessing (a wrong guess on math/physics teaches a misconception).
- **Reviewability** means watching and correcting a board, not reading a
  `scene_plan.json`.
- **Correctness and pedagogy** come from the template, by construction: each
  card maps to a hand-crafted, math-verified *aha-capsule* template with
  validated parameter slots. Generated code is never trusted as a deliverable.

## The storyboard flow (adapted from HyperFrames)

The board fills in three passes, each more expensive than the last, each waiting
for the teacher's sign-off before the next begins:

1. **Plan.** The whole video lands as cards — one per beat: title, what
   happens, how long. **For Bayan, each card also states the *insight move*** —
   the animation that produces the aha (rings unrolling, vectors sliding
   tip-to-tail). The insight must be reviewable here, at the cheapest moment,
   because in this domain the motion *is* the pedagogy.
2. **Sketch.** Every card shows the real layout with the real words placed where
   they will live. **For Bayan this is a real low-quality Manim render per
   card** (the renderer already emits a preview), not a wireframe mock — more
   truthful than a sketch, at low cost.
3. **Build.** The final render lands on the layouts and insight moves already
   approved. The teacher directs with sentence-comments on individual cards;
   only the commented card changes.

The board is plain files (`STORYBOARD.md` + a small sidecar JSON),
git-checkable, editable by hand. Prose fields (titles, narration) are freely
editable; **math and parameter slots are validated, never free-form** — that is
what keeps "correctness by construction" honest.

## How it relates to the POC

The current repository proved:

- Arabic shaping, RTL order, and mixed-script rendering are correct and tested.
- A deterministic scene can render inside an isolated, network-free container
  (AgDR-0002) with inspectable artifacts.
- The plan → template → render spine is buildable.

**Carry forward:** the Arabic helper, the isolation boundary and container
worker, the renderer/preview pipeline, and the discovery that the reviewable
artifact is the product.

**Redesign for the product:**

| POC artifact | Becomes |
|---|---|
| `scene_plan.json` | Storyboard cards (`STORYBOARD.md` + sidecar) |
| Validation review packet (#36) | The board's review/approve flow |
| Fixed template catalogue (#35) | A living set of approved *recipes* |
| FakeProvider | A constrained-vocabulary mapper (or removed) |

**Recipes = the catalogue.** Each approved aha board freezes into a reusable
recipe. The template catalogue is no longer "ship six hand-authored demos"; it
*grows* from approved, pedagogically-verified boards. That accumulation is the
real product loop.

## Principles

1. **Arabic correctness is a product requirement.** RTL layout, shaping, and
   animation order are part of the content, not cosmetic.
2. **The aha lives in the motion.** For math/physics, the animation is the
   pedagogy; the insight move is a first-class, reviewable part of every card.
3. **Correctness and pedagogy by construction.** They come from verified
   templates with validated slots — never from trusted generated code or
   free-form edits to math.
4. **Direct, don't gamble.** Feedback happens on the board, while it is cheap.
   The final render only starts on a plan the teacher has approved.
5. **Plain files, nothing trapped in a UI.** The board is text a team can read,
   edit, version, and check in.

## Deferred until the storyboard proves valuable

Consistent with the North Star, the following wait until the reviewable board is
proven valuable and trustworthy with real teachers: model-assisted free-form
prompt parsing, audio and narrating avatars, autonomous end-to-end publishing,
queues, and persistence. Pulling any of these in early repeats the scope creep
the POC already corrected once.

## Open decisions

- **Prompt vocabulary.** Truly free-form ambiguous prompts require a model to
  resolve (un-skips the provider); "natural but constrained" prompts need no
  model but require a curated vocabulary. This single choice shapes the mapper,
  the catalogue, and what "ambiguous" means.
- **MSA vs Egyptian dialect** for on-screen text, and the bilingual mixing
  policy per subject (physics terms are often English even in Arabic schools).

## Relation to prior work: Code2Video

[Code2Video](https://github.com/showlab/Code2Video) is a prompt→code→video
teaching-video agent (Planner / Coder / Critic). It is the closest existing
system to Bayan, and the product's position toward it is deliberate: **extend
its tactics, do not align with its thesis.**

Code2Video *is* the prompt-to-Python wrapper this product explicitly rejects —
it generates Manim code from a prompt and trusts it enough to render on the
host. Bayan replaces that core with the storyboard wall and correctness by
construction. What survives from Code2Video is the craft around generation.

**Extend (borrow the pattern, not the code):**

- **Typed agents, not a god-class.** Code2Video's tri-agent is, in code, methods
  on one class driven by a CLI. Bayan keeps small typed services invoked by the
  CLI, each writing an inspectable record to the run directory.
- **Classify-then-fix repair.** Parse a failure into type + category +
  plain-English suggestion + scope, fix the minimal snippet, and run cheap gates
  (syntax check, import-only dry run) before any render. Bayan caps this at two
  attempts and applies it only to the *build* pass.
- **Anchored, structured findings.** Code2Video's critic returns
  `{problem, solution}` tied to a location. Bayan generalizes this into the
  per-card directing mechanism: comment on one card, only that card changes.
- **Plan → scene → artifact decomposition.** Outline/storyboard → Lesson/plan;
  per-section code → Scene; merged MP4 → Artifact.

**Reject (each violates a product safety or pedagogy principle):**

- Running generated Manim on the host with full filesystem and network and only a
  timeout → Bayan renders only approved templates inside an isolated container.
- Downloading assets at generation time → Bayan uses local assets with provenance.
- Printing provider keys → Bayan never does.
- Loose retry counts and day-one parallelism → Bayan stays serial, capped.
- A mandatory VLM critic → for math/physics, correctness is by construction, not
  by visual inspection; the VLM stays optional and deferred.

## Reference

- HyperFrames / HeyGen, "Storyboard" (Day 17) — the pre-production-wall pattern
  this direction adapts. Docs: <https://hyperframes.heygen.com>
- [Code2Video](https://github.com/showlab/Code2Video) — prompt→code→video agent;
  tactics extended, core thesis rejected (see above).
