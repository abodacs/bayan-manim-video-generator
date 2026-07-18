# Bayan: Arabic AI-Powered Manim Video Generator

Bayan is an Arabic AI-powered video generator built on top of Manim.

This project targets **Manim Community Edition**. It installs the Community
Edition package as `manim` (version 0.20 or newer), rather than the legacy
`manimlib` package.

## System Requirements

Before running the project, install the system-level dependencies required by Manim for rendering shapes, text, and compiling audio:

- `reshape_arabic_text` reshapes Arabic ligatures and applies the BiDi algorithm
  before rendering.
- `ArabicText` provides a Manim text object with `Noto Sans Arabic` as its
  default font.
- `rtl_glyphs` exposes glyphs in visual right-to-left order for animation.
- `ArabicSanityCheck` renders a small integration scene so Arabic connections,
  direction, and glyph animation can be checked visually.
- A container smoke runner builds a digest-pinned, multi-stage render image,
  runs the Arabic sanity scene without network access, validates its artifacts,
  and saves a video, preview, log, and typed manifest.

### Installation on Ubuntu/Debian

### Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Docker Engine or Docker Desktop for the isolated smoke render
- FFmpeg, Cairo, and Pango, which Manim uses for rendering
- `Noto Sans Arabic` or another font with Arabic glyph coverage
- LaTeX only if you need to render mathematical equations with LaTeX

### 1. Install native dependencies

On Ubuntu or Debian:

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

```bash
uv run manim --version
uv run manim -ql bayan/utils/sanity_check.py ArabicSanityCheck
```

The render should create a video under `media/videos/`. Visually confirm that
Arabic letters are connected, text flows from right to left, and glyphs animate
in the expected order.

### 4. Run the isolated container smoke check

Build the render image and run the same Arabic scene in a container with no
network access:

```bash
uv run python scripts/container_smoke.py
```

The command creates a fresh directory under `artifacts/container-smoke/` for
each run. It does not delete earlier runs. Each run contains `draft.mp4`,
`preview.png`, `render.log`, `smoke_manifest.json`, and the raw Manim output.
The manifest records the image ID, source hashes, resource policy, phase
statuses, and relative output paths. Worker output is capped per phase so a
broken scene cannot fill the host disk.

The worker has no network, runs as a non-root user, mounts the scene read-only,
and writes only to the dedicated run output directory. The Docker CLI itself
receives an allowlisted environment; host application secrets are not passed
to the worker. Use `--skip-build` only when you intentionally want to test an
already-built local image.

If Docker is installed but its daemon is not running, start Docker and run the
command again. If the command fails, read `smoke_manifest.json` and
`render.log` before retrying.

## Development workflow

Run the same checks used by the project’s development tooling:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy bayan
uv run pytest
uv run pre-commit run --all-files
```

If `uv sync` fails in Meson while building `pycairo`, verify that Cairo is
discoverable through `pkg-config`:

```bash
pkg-config --modversion cairo
```

If that command cannot find Cairo, install the native dependencies for your
platform and run `uv sync` again.

## Repository layout

```text
CONTEXT.md                     Canonical domain vocabulary
bayan/
├── renderer/
│   ├── docker.py              Bounded Docker lifecycle and security policy
│   ├── models.py              Typed render settings and manifest models
│   └── smoke.py               Arabic smoke-run orchestration and validation
└── utils/
    ├── arabic_helper.py       Arabic shaping, RTL text, and glyph helpers
    └── sanity_check.py         Render-level Arabic integration scene
Dockerfile                     Pinned container for the Arabic smoke render
scripts/container_smoke.py     Thin CLI for the bounded container smoke run
container/
    ├── pyproject.toml             Render-only dependency declarations
    └── uv.lock                    Locked render dependency graph
docs/
    ├── PROJECT_NORTH_STAR.md       Product direction and success signals
    ├── ARCHITECTURE.md             Target system boundaries
    ├── DOMAIN_MODEL.md             Domain relationships and invariants
    ├── DEVELOPMENT.md              Contributor development loop
    └── agdr/                       Architecture and developer decisions
        ├── AgDR-0001-type-checker.md
        └── AgDR-0002-render-isolation.md
.agents/
└── skills/
    └── manim-video/                Project-scoped Manim video skill
tests/
    ├── test_arabic_helper.py       Arabic shaping and glyph-order tests
    └── test_smoke.py               Package import smoke tests
main.py                         Current application entry-point placeholder
```

The Manim video skill under `.agents/skills/manim-video/` is intentionally
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
the mypy boundary around Manim scenes. The accepted render-isolation boundary is
recorded in [AgDR-0002-render-isolation.md](docs/agdr/AgDR-0002-render-isolation.md).

## Tools Configured
- **Package Manager**: `uv` (PEP 621 & PEP 735)
- **Linter & Formatter**: `ruff`
- **Testing**: `pytest`
