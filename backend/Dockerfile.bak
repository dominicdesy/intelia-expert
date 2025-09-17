# syntax=docker/dockerfile:1.7
FROM python:3.11-slim
WORKDIR /workspace/backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ build-essential \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
COPY . .
RUN mkdir -p rag_index/global rag_index/broiler rag_index/layer logs data
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]