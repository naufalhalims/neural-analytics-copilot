# Multi-stage production container untuk Neural Analytics Copilot
# Zero GPU dependency, optimized DuckDB vectorized pushdown
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Salin dependencies dari stage builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Salin direktori aplikasi dan data
COPY engines/ ./engines/
COPY templates/ ./templates/
COPY static/ ./static/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY app.py .
COPY requirements.txt .

# Dedicated Vault terisolasi di dalam container
COPY vault/ ./vault/

EXPOSE 8508

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8508/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8508"]
