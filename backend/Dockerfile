FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Installation optimisée en une seule couche + nettoyage immédiat
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && pip install --no-cache-dir --upgrade pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Installation des dépendances Python sans cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge \
    && rm -rf /root/.cache /root/.local

# Copie SÉLECTIVE du code source - STRUCTURE BACKEND
COPY *.py ./
COPY app/ ./app/

# Nettoyage agressif de tous les fichiers temporaires
RUN find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} + \
    && find . -name "*.pyo" -delete \
    && find . -name "*.dist-info" -type d -exec rm -rf {} + \
    && find . -name "test*" -type d -exec rm -rf {} + \
    && rm -rf /tmp/* /var/tmp/* requirements.txt

EXPOSE 8080

# Healthcheck ultra-léger sans imports lourds
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); exit(0 if s.connect_ex(('127.0.0.1', 8080))==0 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]