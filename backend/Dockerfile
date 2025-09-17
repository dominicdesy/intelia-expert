FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copie du code source
COPY . .

# Port d'exposition
EXPOSE 8080

# Healthcheck simple - utilise la route health de votre API
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health', timeout=5)" || exit 1

# Commande de démarrage - pointe vers app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]