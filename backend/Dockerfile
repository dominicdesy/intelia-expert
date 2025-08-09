# ---- Builder stage -----------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# build deps for some wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage -----------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# runtime deps: curl for healthcheck, libgomp1 for faiss/sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy python from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# copy app code
COPY app/ ./app/
COPY rag/ ./rag/
COPY rag_index/ ./rag_index/

# RAG index envs (adaptées à ton arbo)
ENV RAG_INDEX_DIR=/app/rag_index \
    RAG_INDEX_BROILER=/app/rag_index/broiler \
    RAG_INDEX_LAYER=/app/rag_index/layer \
    RAG_INDEX_GLOBAL=/app/rag_index/global

# permissions
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE $PORT

# healthcheck -> tes routes santé sont exposées via /api/v1/health
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:$PORT/api/v1/health || exit 1

# start API
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
