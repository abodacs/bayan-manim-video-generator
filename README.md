# Bayan: Arabic AI-Powered Manim Video Generator

Bayan is an Arabic AI-powered video generator built on top of Manim.

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
sudo apt install -y ffmpeg build-essential pkg-config python3-dev libcairo2-dev libpango1.0-dev
```

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
- **Linter & Formatter**: `ruff`
- **Testing**: `pytest`
