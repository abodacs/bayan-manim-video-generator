FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        build-essential \
        ffmpeg \
        fontconfig \
        fonts-noto-core \
        libcairo2-dev \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libpango1.0-dev \
        pkg-config \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.16 /uv /uvx /usr/local/bin/

WORKDIR /workspace
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project \
    && rm -rf /root/.cache

RUN useradd --create-home --home-dir /home/bayan --shell /usr/sbin/nologin --uid 10001 bayan

ENV PATH=/workspace/.venv/bin:$PATH \
    HOME=/tmp/home \
    XDG_CACHE_HOME=/tmp/cache

USER bayan

CMD ["manim", "--version"]
