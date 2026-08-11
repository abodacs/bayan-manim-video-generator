# Exercises — Lesson 03

1. **Swap create for fade.** In `scene.py`, replace `Create(circle)` with
   `FadeIn(circle)`. Render. Note how "reveal without drawing" feels different.
2. **Feel the rates.** In `example-practical.py`, change the smooth dot to
   `rate_func=linear` and the linear dot to `rate_func=smooth`. Confirm they
   swap behaviours.
3. **Add a `Write`.** Replace one `FadeIn` with `Write(text_obj)` and render.
   `Write` is the right choice for text you want to feel "written on".
4. **Emphasis without model change.** After a reveal, add
   `self.play(Indicate(square), run_time=0.6)` then `self.wait(1.0)`. `Indicate`
   draws attention without altering the scene's state.
5. **Stagger a sequence.** Replace three separate `Create` calls with one
   `LaggedStart(Create(a), Create(b), Create(c), lag_ratio=0.2)`.
