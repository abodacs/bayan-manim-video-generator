# Exercises — Lesson 01

Do these locally after rendering `scene.py`. They build fluency, not new theory.

1. **Change the text.** Replace `"Hello, Manim"` with your name. Re-render at
   `-ql`. Confirm the new title appears and still has a pause after it.
2. **Swap the shape.** Replace `Circle(...)` with `Square(side_length=2.0,
   color=GREEN)`. Render. Confirm the square draws and the title still lifts out
   of the way.
3. **Add a second beat.** After the circle appears, transform it into a different
   mobject, e.g. `self.play(Transform(circle, Square()), run_time=1.0)` followed
   by `self.wait(1.0)`. (You will learn `Transform` formally in Lesson 03.)
4. **Drop the pauses on purpose.** Remove both `self.wait(...)` calls and render.
   Observe how unreadable it becomes — this is why the hold after a reveal is a
   rule, not a style choice.
5. **Render a still.** Run the `--format=png -s` command. Inspect the single
   frame. This is your fastest feedback loop while learning layout.

> Stuck? Re-read the “Annotated minimal scene” in `README.md`, then ask the agent.
