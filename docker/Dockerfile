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

# Create data directory
RUN mkdir -p data/raw/parquet data/models backtest_results

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV EXECUTION_MODE=paper
ENV TRADING_ENABLED=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose ports
EXPOSE 8000 8001

# Run Uvicorn with 4 workers
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
