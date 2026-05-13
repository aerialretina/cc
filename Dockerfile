FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --upgrade pip \
 && pip install -e .

COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8080

# Boot script prints a DB diagnostic, runs migrations, then execs uvicorn.
# Idempotent — safe to re-run on every container start.
CMD ["python", "-m", "lip.boot"]
