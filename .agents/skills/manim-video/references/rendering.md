# Rendering Reference

## Prerequisites

Check the exact worker environment before rendering:

```bash
python --version
manim --version
ffmpeg -version
latex --version       # only if using MathTex/Tex/numbered axes
```

Manim may need Cairo, Pango, fonts, and system build tools. On macOS, install `pkg-config` and Cairo before installing Manim when the package build requests them. In the project’s supported environments, run the Arabic sanity scene before accepting generated output.

## Quality presets

```bash
manim -ql script.py SceneName       # fast draft
manim -qm script.py SceneName       # medium review
manim -qh script.py SceneName       # production candidate
manim -ql --format=png -s script.py SceneName  # still preview
```

Render individual scenes while debugging. Use `-qh` only after low-quality frames pass visual and semantic review. Avoid commands that open an interactive scene chooser in automation; provide explicit scene names.

## Output and stitching

Keep per-scene outputs, logs, and the final artifact separate. Stitch only scenes that have passed individually:

```bash
ffmpeg -y -f concat -safe 0 -i concat.txt -c copy final.mp4
```

Use absolute, controlled paths in the concat manifest. Do not allow generated code to create arbitrary output paths.

## Optional audio

Audio is deferred from the first local vertical slice. When enabled, generate or validate narration after the visual cut is stable, measure each clip, then mux with FFmpeg. Keep the silent visual artifact available for debugging.

## Aspect ratios and configuration

Choose the target aspect ratio before layout. Do not reuse a 16:9 layout unchanged for portrait output. Put stable render settings in `manim.cfg` or an explicit command, and record them in the review packet.

## Render workflow

`plan.md -> draft scenes -> still review -> low-quality motion review -> repair -> production render -> stitch -> optional audio -> final QA`.
