# Dockerfile pour le service RAG
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source RAG
COPY . .

# Créer un utilisateur non-root
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Exposer le port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande de démarrage
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]