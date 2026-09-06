# Exercises — Lesson 02

1. **Swap the order.** In `scene.py`, change `arrange(RIGHT, ...)` to
   `arrange(DOWN, ...)`. Predict the layout, then render to confirm.
2. **Add a fourth shape.** Add a `RegularPolygon(n=5)` to the `VGroup`. Confirm
   `arrange` re-spaces all four evenly with no manual math.
3. **Nudge with `next_to`.** Place a `Dot` at the centre of the square using
   `dot.move_to(square.get_center())`. Render a still to verify alignment.
4. **Break it on purpose.** Try cleaning up with `VGroup(*self.mobjects)` instead
   of `Group`. If your scene contains only VMobjects it may work — then add a
   `Text` and observe why `Group` is the safe default.
5. **Edge buffer.** Reduce `to_edge(UP, buff=...)` to `0.1` and render. See the
   row touch the frame edge — the reason for `buff >= 0.5`.
