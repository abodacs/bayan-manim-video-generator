# Bayan

Bayan is an Arabic-first video-generation toolkit built on [Manim Community
Edition](https://www.manim.community/). It is designed to turn educational
content into clear, maintainable explainer videos with reliable Arabic
shaping, right-to-left layout, and reproducible rendering.

> **Project status:** early-stage foundation. The repository currently provides
> Arabic text utilities, a Manim rendering sanity check, and development tooling.
> The end-to-end AI generation pipeline is not implemented yet.

Bayan uses the Community Edition package named `manim` (version 0.20 or newer),
not the legacy `manimlib` package.

## What works today

- `reshape_arabic_text` reshapes Arabic ligatures and applies the BiDi algorithm
  before rendering.
- `ArabicText` provides a Manim text object with `Noto Sans Arabic` as its
  default font.
- `rtl_glyphs` exposes glyphs in visual right-to-left order for animation.
- `ArabicSanityCheck` renders a small integration scene so Arabic connections,
  direction, and glyph animation can be checked visually.

## Quick start

### Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- FFmpeg, Cairo, and Pango, which Manim uses for rendering
- `Noto Sans Arabic` or another font with Arabic glyph coverage
- LaTeX only if you need to render mathematical equations with LaTeX

### 1. Install native dependencies

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y \
  ffmpeg build-essential pkg-config python3-dev \
  libcairo2-dev libpango1.0-dev fonts-noto-core
```

On Windows with Chocolatey:

```powershell
choco install ffmpeg pango cairo -y
```

On other platforms, install the equivalent FFmpeg, Cairo, Pango, and Arabic-font
packages before installing the Python dependencies.

### 2. Install the Python environment

Install `uv` if it is not already available:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then create the project environment and install the versions locked in
`uv.lock`:

```bash
uv sync
```

You do not need to activate `.venv` manually; `uv run` uses the project
environment automatically.

### 3. Verify the installation

Check the Manim edition and render the Arabic sanity scene:

```bash
uv run manim --version
uv run manim -ql bayan/utils/sanity_check.py ArabicSanityCheck
```

The render should create a video under `media/videos/`. Visually confirm that
Arabic letters are connected, text flows from right to left, and glyphs animate
in the expected order.

## Development workflow

Run the same checks used by the project’s development tooling:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy bayan
uv run pytest
uv run pre-commit run --all-files
```

Install the commit and push hooks once per clone:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

The type checker runs in strict mode for ordinary package code. Manim scene
files are excluded because the dynamic `from manim import *` API does not
provide a useful static typing boundary. Keep non-rendering logic in typed
modules and keep scenes thin.

If `uv sync` fails while building `pycairo`, check that Cairo is visible to
`pkg-config`:

```bash
pkg-config --modversion cairo
```

If that command cannot find Cairo, install the native dependencies for your
platform and run `uv sync` again.

## Repository layout

```text
CONTEXT.md                     Canonical domain vocabulary
bayan/
└── utils/
    ├── arabic_helper.py       Arabic shaping, RTL text, and glyph helpers
    └── sanity_check.py         Render-level Arabic integration scene
docs/
    ├── PROJECT_NORTH_STAR.md       Product direction and success signals
    ├── ARCHITECTURE.md             Target system boundaries
    ├── DOMAIN_MODEL.md             Domain relationships and invariants
    ├── DEVELOPMENT.md              Contributor development loop
    └── agdr/                       Architecture and developer decisions
        ├── AgDR-0001-type-checker.md
        └── AgDR-0002-render-isolation.md
skills/
└── creative/
    └── manim-video/                Project-scoped Manim video skill
tests/
    ├── test_arabic_helper.py       Arabic shaping and glyph-order tests
    └── test_smoke.py               Package import smoke tests
main.py                         Current application entry-point placeholder
```

The Manim video skill under `skills/creative/manim-video/` is intentionally
project-scoped and versioned with this repository. Keep it available to
contributors working on Bayan; it should not be replaced by a global skill
installation.

## Architecture direction

The repository is intentionally small today. As the product grows, keep the
workflow separated into explicit boundaries:

1. **Content domain** — structured lessons, scene plans, and render metadata.
2. **Generation** — deterministic or model-assisted production of a constrained
   scene representation.
3. **Rendering** — isolated execution of Manim scenes and collection of output
   artifacts.
4. **Validation** — Arabic RTL checks, visual smoke checks, mathematical or
   content validation, and safety checks for generated code.
5. **Interfaces** — a CLI or API that composes the workflow without owning the
   domain rules.

The key architectural rule is to keep domain logic independent of Manim. Scene
files should be thin rendering adapters, while generated code should run in an
isolated process rather than inside the application host.

See the detailed [architecture](docs/ARCHITECTURE.md), [domain model](docs/DOMAIN_MODEL.md),
and [project North Star](docs/PROJECT_NORTH_STAR.md) for the proposed direction.

## Design and engineering decisions

The `docs/agdr/` directory records decisions that affect the project’s
architecture and development workflow. Start with
[`AgDR-0001-type-checker.md`](docs/agdr/AgDR-0001-type-checker.md) to understand
the mypy boundary around Manim scenes. The proposed render-isolation boundary is
recorded in [AgDR-0002-render-isolation.md](docs/agdr/AgDR-0002-render-isolation.md).

Contributor workflow is documented in
[DEVELOPMENT.md](docs/DEVELOPMENT.md).
