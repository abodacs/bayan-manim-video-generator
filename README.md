# Bayan: Arabic AI-Powered Manim Video Generator

Bayan is an Arabic AI-powered video generator built on top of Manim.

## System Requirements
Before running the project, you must install the following system-level dependencies required by Manim for rendering shapes, text, and compiling audio:
- **FFmpeg**: Required for video and audio rendering.
- **Pango**: Required for text rendering and layout.
- **Cairo**: Required for vector graphics rendering.
- **LaTeX (Optional)**: Required if you want to render mathematical equations.

### Installation on Windows (via Chocolatey):
```powershell
choco install ffmpeg pango cairo -y
```

## Setup & Development

1. **Install dependencies and create virtual environment** (using `uv`):
   ```bash
   uv sync
   ```

2. **Verify environment setup** (Run sanity check scene):
   ```bash
   uv run manim -ql bayan/utils/sanity_check.py SanityCheckScene
   ```

## Tools Configured
- **Package Manager**: `uv` (PEP 621 & PEP 735)
- **Linter & Formatter**: `ruff`
- **Testing**: `pytest`