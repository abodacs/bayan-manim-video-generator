# Bayan: Arabic AI-Powered Manim Video Generator

Bayan is an Arabic AI-powered video generator built on top of Manim.

## System Requirements
Before running the project, you must install the following system-level dependencies required by Manim for rendering shapes, text, and compiling audio:
- **FFmpeg**: Required for video and audio rendering.
- **Pango**: Required for text rendering and layout.
- **Cairo**: Required for vector graphics rendering.
- **LaTeX (Optional)**: Required if you want to render mathematical equations.

> **Install these before `uv sync`.** Manim's `pycairo` / `manimpango` build
> steps need the Cairo and Pango development headers, so `uv sync` fails
> without them.

### Installation on Windows (via Chocolatey):
```powershell
choco install ffmpeg pango cairo -y
```

### Installation on Linux (Debian/Ubuntu):
```bash
sudo apt-get install -y libcairo2-dev libpango1.0-dev libpangocairo-1.0-0 ffmpeg
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
- **Linter & Formatter**: `ruff` (`uv run ruff check .`, `uv run ruff format .`)
- **Type Checker**: `mypy` (`uv run mypy bayan` — strict; Manim scenes excluded)
- **Testing**: `pytest` with coverage (`uv run pytest`, reports `--cov=bayan`)
- **CI**: `.github/workflows/ci.yml` — ruff, mypy, and pytest run on every push and pull request
