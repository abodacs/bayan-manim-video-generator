# Domain model

This document describes the conceptual model behind Bayan’s video workflow.
The canonical vocabulary is maintained in the root
[`CONTEXT.md`](../CONTEXT.md); use those terms in code and documentation.

## Core model

~~~text
Lesson
  -> ordered Lesson segments
  -> Scene plans
  -> Scenes
  -> Render jobs
  -> Artifacts
  -> Validation results
  -> Review decision
~~~

The model keeps educational intent separate from the executable representation
used by Manim. A scene plan is the handoff between the content domain and the
generation boundary.

### Lesson

A coherent educational explanation. A lesson may contain multiple ordered
lesson segments, each with its own learning objective and visual focus.

### Lesson segment

A bounded unit of a lesson that can be planned and reviewed independently. It
should be small enough that a reviewer can explain what the resulting visuals
are meant to teach.

### Scene plan

A platform-neutral description of the segment’s visual intent: content,
sequence, transitions, timing, and any domain-specific constraints. It is the
source of truth for what should be shown; generated Manim code is not.

### Scene

A visual sequence produced from a scene plan. A scene may be authored
deterministically or generated with model assistance, but it must still be
traceable to the plan that requested it.

### Render job

A bounded request to turn a scene into artifacts. A job records the scene-plan
identity, scene identity, renderer configuration, tool versions, and lifecycle
result needed to explain or reproduce the attempt.

### Artifact

A durable output of a render job. The first slice should at least distinguish
the rendered video, diagnostic logs, and a manifest describing the inputs and
configuration used for the job.

### Validation result

A named check with a pass, fail, or not-applicable outcome and enough evidence
to explain the result. Validation should be composable: Arabic language checks
should not need to know how mathematical checks are implemented.

### Review decision

A decision that an artifact is suitable for delivery, needs correction, or is
rejected. Validation informs review but does not replace it when the product
requires human approval.

## Invariants

- Every render job points to an explicit scene and its originating scene plan.
- A scene plan does not depend on Manim classes or model-provider response
  formats.
- Generated scene code is not accepted as a deliverable without the required
  validation results.
- Every artifact can be traced back to the render job that produced it.
- Failed jobs retain their failure stage and diagnostics rather than collapsing
  into an opaque error.

## Lifecycle sketches

~~~text
Lesson:     draft -> planned -> ready for generation
Render job: requested -> running -> succeeded | failed
Artifact:   produced -> validated -> accepted | needs correction | rejected
~~~

These states describe domain intent, not a required persistence technology.
They should become explicit in a typed contract before a queue or database is
introduced.

## Open questions

- Does one scene plan always produce one scene, or can it produce an ordered
  scene sequence?
- Which validation checks are blocking, and which are advisory?
- When should narration and audio become part of the artifact contract?
- What is the smallest review experience that lets an educator correct a scene
  plan without editing generated code?
