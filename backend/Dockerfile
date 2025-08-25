# ---- Simple working Dockerfile ----
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/backend

# Copy and install requirements (single step to avoid dependency conflicts)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY rag/ ./rag/
COPY rag_index/ ./rag_index/

# RAG index environment variables
ENV RAG_INDEX_DIR=/workspace/backend/rag_index \
    RAG_INDEX_BROILER=/workspace/backend/rag_index/broiler \
    RAG_INDEX_LAYER=/workspace/backend/rag_index/layer \
    RAG_INDEX_GLOBAL=/workspace/backend/rag_index/global

# Set permissions
RUN chown -R appuser:appuser /workspace/backend
USER appuser

EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:$PORT/api/v1/health || exit 1

# Start API
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]