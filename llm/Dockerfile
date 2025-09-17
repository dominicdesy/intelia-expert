# Utiliser une image plus légère
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Installation système optimisée en une seule couche
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Installation des dépendances Python avec nettoyage agressif
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache /root/.local /tmp/* /var/tmp/* \
    && find /usr/local -name "*.pyc" -delete \
    && find /usr/local -name "__pycache__" -type d -exec rm -rf {} + \
    && rm requirements.txt

# Copie du code source (les exclusions sont gérées par .dockerignore)
COPY . .

# Nettoyage final agressif
RUN find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} + \
    && find . -name "*.pyo" -delete \
    && find . -name "*.log" -delete \
    && find . -name "*.tmp" -delete \
    && find . -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); exit(0 if s.connect_ex(('127.0.0.1', 8080))==0 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]