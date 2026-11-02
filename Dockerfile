# =============================================================================
# RegulaRAG — Dockerfile
# =============================================================================
# Multi-stage build for the Python backend application.
# Stage 1: builder — installs dependencies with uv.
# Stage 2: runtime  — minimal image without build tools.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: builder
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first (Docker layer caching)
COPY pyproject.toml ./
COPY src/ ./src/

# Install runtime dependencies into /app/.venv (no dev/test extras)
RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python -e "."

# ---------------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --from=builder /app/src ./src

# Copy configs and any static assets
COPY configs/ ./configs/

# Ensure the virtualenv Python is used
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src"

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["python", "-m", "uvicorn", "regularag.main:app", "--host", "0.0.0.0", "--port", "8000"]

