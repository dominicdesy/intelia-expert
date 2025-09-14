FROM python:3.11-slim

# Réglages Python/pip pour des builds stables et rapides
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ONLY_BINARY=:all: \ 
    PIP_NO_BINARY=langdetect \ 
    LANG=C.UTF-8

WORKDIR /app

# Outils pip à jour (meilleure résolution de wheels)
RUN pip install --upgrade pip setuptools wheel

# Copie des dépendances d'abord pour profiter du cache Docker
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install -r requirements.txt

# Copie du code de l'application
COPY . .

# Variables d'environnement de l'app
ENV BASE_PATH=/llm
ENV LANGUAGE_FILE=/app/languages.json
ENV INTENTS_FILE=/app/intents.json

EXPOSE 8080

# Healthcheck (optionnel) : vérifie que le port répond
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python - <<'PY'
import socket,sys
s=socket.socket(); s.settimeout(2)
try:
    s.connect(('127.0.0.1',8080)); s.close(); sys.exit(0)
except Exception:
    sys.exit(1)
PY

# SSE/streaming : 1 worker conseillé, keep-alive un peu plus long
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "30", "--proxy-headers"]
