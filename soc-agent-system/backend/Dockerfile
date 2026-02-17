# =============================================================================
# SOC Agent System — Backend Dockerfile
# =============================================================================
# Multi-stage build for Python FastAPI application
# Stage 1: Install dependencies
# Stage 2: Runtime with minimal footprint
# =============================================================================

# Stage 1: Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application source code
COPY src/ .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

