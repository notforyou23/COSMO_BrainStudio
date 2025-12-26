# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.12.8
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
FROM base AS builder
ARG POETRY_VERSION=1.8.3

# System build deps for reproducible wheels where needed.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc curl git \
 && rm -rf /var/lib/apt/lists/*

# Create an isolated venv and install Poetry (pinned) into it.
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN pip install --upgrade pip setuptools wheel \
 && pip install "poetry==${POETRY_VERSION}" \
 && poetry --version

WORKDIR /app

# Install only from lockfile (no source code yet) for better caching.
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-interaction --no-ansi --sync --no-root

# Now copy the project and install the package itself (still locked).
COPY . .
RUN poetry install --only main --no-interaction --no-ansi --sync
FROM base AS runtime

# Create a non-root user for safer, more deterministic runs.
RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

USER app

# Default command is test-friendly for CI; override in docker run as needed.
CMD ["python", "-m", "pytest", "-q"]
