# Application image for the API and worker (M6+).
# Multi-stage: install with uv, then run as a non-root user.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# uv for fast, reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Dependency layer (cached until pyproject/lock change).
COPY pyproject.toml uv.lock* ./
RUN uv sync --extra api --extra worker --no-dev --no-install-project

# Application code.
COPY . .
RUN uv sync --extra api --extra worker --no-dev

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Default command runs the API; the worker service overrides it in docker-compose.
CMD ["uv", "run", "uvicorn", "ai_eval.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
