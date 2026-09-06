# Exercises — Lesson 04

1. **Write the plan first.** Pick "the area of a circle". Write a `plan.md`
   following the template in the README: arc, palette with color meanings, and
   a beat table with `run_time` and wait for every beat. Only then write the
   scene. Note what the plan caught before any code existed.
2. **Apply the one-sentence test.** Describe `scene.py`'s `PlannedArc` in one
   sentence. Now merge beats 2 and 3 into a single `play` call, render, and try
   again — feel where the sentence breaks.
3. **Retime a reveal.** In `scene.py`, change the caption beat to
   `run_time=3.0` with `self.wait(0.2)`. Render. Confirm the rule: a fast
   reveal with a hold beats a slow reveal without one. Restore the original.
4. **Swap the transition.** In `example-practical.py`, make `CarryForward`
   keep *both* the term and the note. Render. Decide which elements the next
   scene actually builds on — carry those, fade the rest.
5. **Run the self-critique.** Take your exercise-1 scene and ask the six
   questions from the README. Cut half the text. If a label is not pulling
   its weight, drop it and re-render.
