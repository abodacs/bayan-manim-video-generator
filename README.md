# Bayan: Arabic AI-Powered Manim Video Generator

Bayan is an Arabic AI-powered video generator built on top of Manim.

This project targets **Manim Community Edition**. It installs the Community
Edition package as `manim` (version 0.20 or newer), rather than the legacy
`manimlib` package.

## System Requirements

Before running the project, install the system-level dependencies required by Manim for rendering shapes, text, and compiling audio:

- **FFmpeg**: Required for video and audio rendering.
- **Pango**: Required for text rendering and layout.
- **Cairo**: Required for vector graphics rendering.
- **LaTeX (Optional)**: Required if you want to render mathematical equations.

### Installation on Ubuntu/Debian

The Cairo and Pango development packages are required because `pycairo` and
`manimpango` may be compiled from source during `uv sync`:

```bash
sudo apt update
sudo apt install -y ffmpeg build-essential pkg-config python3-dev \
  libcairo2-dev libpango1.0-dev fonts-noto-core
```

The sanity scene uses `Noto Sans Arabic` for predictable Arabic glyph coverage.
The `fonts-noto-core` package provides it on Ubuntu/Debian.

### Installation on Windows (via Chocolatey):
```powershell
choco install ffmpeg pango cairo -y
```

### Installation on Linux (Debian/Ubuntu):
```bash
sudo apt-get install -y libcairo2-dev libpango1.0-dev libpangocairo-1.0-0 ffmpeg
```

## Setup & Development

If this is your first time using the project, follow these steps in order. You
do not need to activate a virtual environment manually: `uv run` uses the
project's `.venv` automatically.

1. **Install `uv`** (skip this step if `uv --version` already works):

   **macOS/Linux**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   **Windows PowerShell**:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   Close and reopen your terminal after installing `uv`, then check it:
   ```bash
   uv --version
   ```

2. **Install the Python dependencies** and create the project environment:
   ```bash
   uv sync
   ```
   This creates `.venv` and installs the versions recorded in `uv.lock`.

3. **Confirm the Manim edition and version**:
   ```bash
   uv run manim --version
   # Manim Community v0.20.1 (or newer)
   ```

4. **Run the Arabic rendering check**:
   ```bash
   uv run manim -ql bayan/utils/sanity_check.py ArabicSanityCheck
   ```
   The `-ql` option means “quick, low quality,” so this check finishes faster
   than a final render. A successful run creates a video under `media/videos/`.

5. **Run the tests** (optional):
   ```bash
   uv run pytest
   ```

### Troubleshooting `pycairo` build errors

If `uv sync` fails in Meson while building `pycairo`, verify that Cairo is
discoverable through `pkg-config`:

```bash
pkg-config --modversion cairo
```

If the command reports that the package cannot be found, install the Ubuntu/Debian
system requirements above and run `uv sync` again.

## Tools Configured
- **Package Manager**: `uv` (PEP 621 & PEP 735)
- **Linter & Formatter**: `ruff` (`uv run ruff check .`, `uv run ruff format .`)
- **Type Checker**: `mypy` (`uv run mypy bayan` — strict; Manim scenes excluded)
- **Testing**: `pytest` with coverage (`uv run pytest`, reports `--cov=bayan`)
- **CI**: `.github/workflows/ci.yml` — ruff, mypy, and pytest run on every push and pull request
