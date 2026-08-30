# Multi-stage build: reduce final image size
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY api/ ./api/
COPY core/ ./core/
COPY scripts/ ./scripts/
COPY static/ ./static/
COPY requirements.txt .

# Database migrations must ship in the image (SPEC-A03 / F-05): without these
# run_migrations() raises and the container would otherwise start with no DB.
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create data directory tree. Real parquet/model data is NOT baked into the
# image — it is bind-mounted from ../data via docker-compose.yml.
RUN mkdir -p data/raw/parquet data/models backtest_results

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV EXECUTION_MODE=paper
ENV TRADING_ENABLED=false

# Health check — stdlib only (`requests` is not in requirements.txt). Non-2xx
# raises → non-zero exit → container marked unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Expose ports
EXPOSE 8000 8001

# Default command: the API (no scheduled jobs — SPEC-A02). The `worker` service
# in docker-compose.yml overrides this with `python scripts/run_pipeline.py`,
# which is the single owner of the pipeline scheduler.
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
