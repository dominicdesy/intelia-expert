FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8

WORKDIR /app

# Installation des dépendances système pour compiler langdetect
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV BASE_PATH=/llm \
    LANGUAGE_FILE=/app/languages.json \
    INTENTS_FILE=/app/intents.json

EXPOSE 8080

# Healthcheck en one-liner Python
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["python","-c","import socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0) if s.connect_ex(('127.0.0.1',8080))==0 else sys.exit(1)"]

# SSE/streaming: 1 worker + keep-alive un peu plus long
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8080","--timeout-keep-alive","30","--proxy-headers"]