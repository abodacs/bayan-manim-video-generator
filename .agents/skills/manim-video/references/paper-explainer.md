# Paper Explainer Workflow

A paper optimizes for completeness and proof; a video optimizes for understanding and retention. Do not read the paper aloud with decorative pictures. Extract the core insight and make the “why” visually obvious.

## Before code

Record:

- target audience and prerequisites;
- the paper’s central claim and what evidence supports it;
- the problem and why existing approaches fail;
- the one mechanism or insight worth remembering;
- what can be omitted without changing the claim;
- source locations for every equation, number, and comparison.

## Five-minute structure

1. Hook: a question, surprising result, or concrete failure.
2. Problem: what is difficult and why it matters.
3. Intuition: a geometric or procedural model.
4. Mechanism: the paper’s contribution, introduced one idea at a time.
5. Evidence: a restrained comparison or result.
6. Limitations and takeaway.

Use one focused scene per conceptual point. For a Transformer-like paper, introduce the information bottleneck before revealing Q/K/V; for a systems paper, build the data path before showing the full architecture.

## Grounded equations

Show a complete equation dimmed, then highlight terms in the order the viewer needs them. Define symbols in plain language. Validate that the animation’s simplification preserves the paper’s stated assumptions.

## Architecture and results

Build systems left-to-right or top-to-bottom: component, connection, data flow, then scale. For charts, reveal the baseline before the result and preserve units, axes, sample sizes, and rounding. Never imply causation from a visual comparison that the paper does not support.

## Review gates

- An independent reviewer can state the paper’s claim from the video.
- Every nontrivial claim has a source or is marked illustrative.
- The animation distinguishes intuition, formal definition, result, and limitation.
- The final scene does not overclaim generality.
