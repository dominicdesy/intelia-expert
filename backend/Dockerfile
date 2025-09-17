# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

# Répertoire de travail
WORKDIR /app

# Variables d'env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ build-essential wget \
 && rm -rf /var/lib/apt/lists/*

# Copier requirements
COPY backend/requirements.txt /app/requirements.txt

# Installer requirements
RUN python -m pip install --upgrade pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

# Copier le code
COPY backend/ /app/

# Créer dossiers nécessaires (si utilisés par ton code)
RUN mkdir -p /app/rag_index/global /app/rag_index/broiler /app/rag_index/layer /app/logs /app/data

# Exposer le port attendu
EXPOSE 8080

# Healthcheck → teste que le serveur FastAPI répond bien
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 CMD \
  wget -qO- http://127.0.0.1:8080/health || exit 1

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
