# Bayan domain context

This glossary defines the canonical terms for Bayan’s educational video
workflow. Use these terms consistently in product discussions, documentation,
and future APIs.

## Content

**Lesson**:
A coherent educational explanation that Bayan helps an author turn into a
video.
_Avoid_: prompt, script, video

**Lesson segment**:
A bounded part of a lesson with one learning objective and a focused visual
explanation.
_Avoid_: slide, scene

**Scene plan**:
A platform-neutral description of how a lesson segment should be visualized,
including its content, ordering, and transitions.
_Avoid_: Manim scene, generated code

## Rendering

**Scene**:
A visual sequence produced from a scene plan for inclusion in the final video.
_Avoid_: scene plan, slide

**Render job**:
A request to produce one or more artifacts from a scene and its declared input
configuration.
_Avoid_: render, build

**Artifact**:
A durable output of a render job, such as a video, preview image, metadata, or
diagnostic record.
_Avoid_: file, output

## Quality

**Validation result**:
A recorded assessment of whether an artifact satisfies a defined linguistic,
visual, mathematical, content, or safety check.
_Avoid_: test result

**Review**:
A human or automated decision about whether a validated artifact is suitable
for delivery.
_Avoid_: validation
