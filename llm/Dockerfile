FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ONLY_BINARY=:all: \
    LANG=C.UTF-8

WORKDIR /app

# Outils pip à jour (meilleure résolution de wheels)
RUN pip install --upgrade pip setuptools wheel

# Copie requirements d'abord pour le cache
COPY requirements.txt .

# Dépendances Python
RUN pip install -r requirements.txt

# Code de l'application
COPY . .

# Tes variables d'env
ENV BASE_PATH=/llm
ENV LANGUAGE_FILE=/app/languages.json
ENV INTENTS_FILE=/app/intents.json

EXPOSE 8080

# Healthcheck basique (optionnel)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',8080)); s.close()"

# ⚠️ SSE/Streaming: garder 1 worker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "30", "--proxy-headers"]
