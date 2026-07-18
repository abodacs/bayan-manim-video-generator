ARG PYTHON_BASE=python:3.11-slim-bookworm@sha256:b18992999dbe963a45a8a4da40ac2b1975be1a776d939d098c647482bcad5cba
ARG UV_BASE=ghcr.io/astral-sh/uv:0.8.16@sha256:f228383e3aca00ab1a54feaaceb8ea1ba646b96d3ee92dc20f5e8e3dcb159c9f
ARG DEBIAN_SNAPSHOT=20260713T000000Z

FROM ${UV_BASE} AS uv

FROM ${PYTHON_BASE} AS builder
ARG DEBIAN_SNAPSHOT

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace

RUN sed -i \
        -e "s|http://deb.debian.org/debian-security|http://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}|" \
        -e "s|http://deb.debian.org/debian|http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}|" \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install --no-install-recommends --yes \
        build-essential \
        libcairo2-dev \
        libgdk-pixbuf-2.0-dev \
        libglib2.0-dev \
        libpango1.0-dev \
        pkg-config \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /workspace
COPY container/pyproject.toml container/uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project \
    && rm -rf /root/.cache

FROM ${PYTHON_BASE} AS runtime
ARG DEBIAN_SNAPSHOT

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace

RUN sed -i \
        -e "s|http://deb.debian.org/debian-security|http://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}|" \
        -e "s|http://deb.debian.org/debian|http://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}|" \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install --no-install-recommends --yes \
        ffmpeg \
        fontconfig \
        fonts-noto-core \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY --from=builder /workspace/.venv /workspace/.venv

RUN useradd --create-home --home-dir /home/bayan --shell /usr/sbin/nologin --uid 10001 bayan

ENV PATH=/workspace/.venv/bin:$PATH \
    HOME=/tmp/home \
    XDG_CACHE_HOME=/tmp/cache

USER bayan

CMD ["manim", "--version"]
