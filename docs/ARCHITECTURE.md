# Architecture

**Status:** Target architecture for the early product phase

The repository is currently a small Python package with Arabic text utilities,
one Manim sanity scene, and development tooling. This document describes the
boundaries that future product code should grow into; it is not a claim that
all of these components exist today.

## System shape

~~~text
Lesson
  -> Lesson segment
  -> Scene plan                platform-neutral intent
  -> Scene generation          deterministic or model-assisted
  -> Render job
  -> Isolated Manim worker     executable scene code
  -> Artifacts
  -> Validation and review
~~~

The application should pass explicit, serializable data between these stages.
The Manim worker should not need to know how a lesson was authored, and the
lesson domain should not import Manim.

## Boundaries

### Content domain

Owns lessons, lesson segments, scene plans, and the rules that describe what a
visual explanation is meant to communicate. It must remain independent of
Manim, model SDKs, and storage details.

### Generation

Turns a scene plan into a constrained scene representation. A deterministic
generator and a model-assisted generator should implement the same contract;
the rest of the system should not depend on a particular model provider.

Generated content must be treated as data until it passes the checks required
to become executable scene code.

### Rendering

Owns the render job lifecycle, invokes Manim, captures logs, and records output
artifacts. It should expose a small request/result interface rather than leak
Manim’s command-line details into the content domain.

### Validation

Owns checks that are meaningful at different levels:

- **Content:** the scene represents the intended lesson segment.
- **Language:** Arabic shaping, RTL order, and font availability are correct.
- **Visual:** the scene renders, fits the frame, and remains legible.
- **Mathematical:** equations and transformations are valid when applicable.
- **Safety:** generated code stays within the permitted execution boundary.

Validation results should be attached to the render job and its artifacts so a
reviewer can understand both what passed and what failed.

### Interface

The CLI or future API composes the workflow, reports progress, and returns
artifacts. It should not own domain rules or execute generated scene code
directly.

## Trust boundaries

The application host is trusted orchestration code. Model output and generated
scene code are untrusted input. The renderer therefore needs a separate worker
boundary with, at minimum:

- no network access by default;
- no access to application secrets;
- an isolated temporary workspace;
- an explicit output location for artifacts;
- time and resource limits; and
- structured success and failure results.

The exact mechanism—container, sandboxed subprocess, or another worker runtime—
is an implementation decision. The boundary itself is not optional.

## Current implementation map

- `bayan/utils/arabic_helper.py` contains the current Arabic text and glyph
  helpers.
- `bayan/utils/sanity_check.py` is the current render-level integration scene.
- `tests/` contains focused helper tests and package smoke tests.
- `main.py` is still an application entry-point placeholder.
- `docs/agdr/` records decisions that explain development and architecture
  constraints.

## First vertical slice

The first end-to-end slice should be deliberately narrow:

1. Build one typed scene plan without a model dependency.
2. Convert it into one known-good Manim scene.
3. Execute that scene in the isolated worker boundary.
4. Collect a video artifact, logs, and a reproducibility manifest.
5. Run Arabic and render validation before marking the job reviewable.

This slice proves the boundaries before adding provider integrations, queues, or
multi-lesson orchestration.
