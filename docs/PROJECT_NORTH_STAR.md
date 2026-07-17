# Project North Star

**Status:** Proposed — assumption-led strategy

## North-star statement

Bayan should let an Arabic-speaking educator turn a clear lesson explanation
into a reviewable, visually coherent Manim video without hand-solving Arabic
right-to-left rendering or trusting opaque generated code.

## Product promise

For every supported lesson, Bayan should provide:

- Arabic text that preserves meaning, shaping, and reading direction.
- Visual explanations that are clear enough to review before delivery.
- Reproducible renders with inspectable inputs, configuration, and artifacts.
- A safe boundary around any model-generated or otherwise executable scene code.
- A workflow that supports human correction instead of requiring blind trust.

## Primary user

The primary user is an educator or educational content author who understands
the lesson but should not need to become a Manim, Arabic typography, or video
rendering specialist.

Engineers are an important secondary audience: the system must remain easy to
debug, extend, and operate as the generation pipeline grows.

## Working product strategy

This strategy is a working hypothesis. The repository contains no educator
interviews, usage analytics, or observed workflow evidence yet, so the user
opportunities below must be validated before the product direction is treated
as settled.

### Bounded first-slice outcome

An Arabic-speaking educator should be able to submit one structured lesson
segment and receive a reviewable, reproducible video artifact with an
inspectable scene plan and Arabic validation result. The business outcome this
serves—such as reducing authoring and review time—has not been measured yet and
remains an open strategy decision.

### Unvalidated opportunities by journey moment

- **Lesson setup:** “I can describe a focused lesson segment without learning
  Manim or Arabic typography.”
- **Plan review:** “I can inspect what the system intends to teach before
  executable scene code is trusted.”
- **Render diagnosis:** “I can tell whether an Arabic, visual, content, or
  safety check failed and what to fix.”
- **Acceptance:** “I can correct or reject a result instead of publishing on
  blind trust.”

### Priority solution bets and cheap tests

1. **A deterministic scene-plan contract and known-good generator.** The risky
   assumption is that a platform-neutral plan is understandable enough for an
   educator to review. Test it by hand-authoring plans for three lesson
   segments and asking educators to predict and critique the intended visuals.
2. **An isolated render worker with a reproducibility manifest and validation
   results.** The risky assumption is that clear diagnostics and a safe
   execution boundary make failures recoverable for a non-specialist. Test it
   with one successful render and one intentionally failing render, then check
   whether a reviewer can identify the failure stage and reproduce the attempt.
3. **Arabic-first rendering and validation as a release gate.** The risky
   assumption is that shaping, RTL order, and mixed-script behavior are common
   enough failure points to justify first-class treatment. Test it against a
   small Arabic-heavy sample set that includes mixed Arabic, Latin, and numbers.

Model-assisted generation, a public CLI/API, queues, persistence, audio, and
autonomous publishing are deferred until the deterministic single-job slice
proves that the reviewable artifact is valuable and trustworthy.

## Principles

1. **Arabic correctness is a product requirement.** RTL layout, glyph shaping,
   and animation order are part of the content experience, not cosmetic fixes.
2. **Use a structured intermediate representation.** Keep lesson intent and
   scene plans independent from Manim-specific code.
3. **Make execution safe by default.** Treat generated scene code as untrusted
   input and isolate it from the application host.
4. **Prefer reviewable output.** Expose the scene plan, render configuration,
   validation results, and artifacts needed for a human to make a decision.
5. **Earn automation incrementally.** A deterministic, testable vertical slice
   comes before a broad autonomous generation system.

## Definition of progress

### Foundation — current

- Arabic shaping and RTL glyph helpers exist.
- A Manim sanity scene provides a visual rendering check.
- Focused unit tests cover the Arabic helper and repository comment policy.
- Python packaging, linting, typing, and unit-test tooling are configured.

### First useful vertical slice

- Accept one structured lesson segment.
- Produce one platform-neutral scene plan.
- Render one deterministic scene in an isolated worker.
- Emit a video artifact and the metadata needed to reproduce the job.
- Validate Arabic rendering and expose a clear pass/fail result.

### Later capability

- Add model-assisted scene planning behind the same scene-plan contract.
- Add richer visual and mathematical validation.
- Support multi-segment lessons and review workflows.
- Add operational concerns such as queues, persistence, and provider policies
  only when the single-job workflow proves stable.

## Non-goals for the first slice

- Fully autonomous publishing without human review.
- Executing generated code inside the application process.
- Supporting every Manim feature before the core scene contract is stable.
- Introducing a multi-provider abstraction before one reliable provider path is
  understood.

## Success signals

The North Star is moving in the right direction when:

- A new contributor can install the project and render the Arabic sanity scene
  from the README.
- An educator can inspect what the system intended to show before accepting a
  render.
- A failed render identifies its job, inputs, and failure stage.
- Arabic correctness remains covered by both render-level checks and focused
  automated tests as new capabilities are added.
