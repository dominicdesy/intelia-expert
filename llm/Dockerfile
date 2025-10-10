# Stage 1: Builder optimisé avec cache des layers
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Installation des outils de build (Layer mis en cache)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# OPTIMISATION CLÉE: Copier requirements.txt AVANT le code source
# Ce layer sera mis en cache tant que requirements.txt ne change pas
COPY requirements.txt .

# Installation GROUPÉE de toutes les dépendances (Layer mis en cache)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --target=/opt/venv "typing-extensions>=4.12.0" \
    && pip install --no-cache-dir --target=/opt/venv \
       torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --target=/opt/venv -r requirements.txt \
    && pip install --no-cache-dir --target=/opt/venv --upgrade "typing-extensions>=4.12.0"

# Stage 2: Runtime minimal (inchangé)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copie des dépendances installées (Layer mis en cache)
COPY --from=builder /opt/venv /opt/venv

# OPTIMISATION: Copier le code source EN DERNIER
# Seul ce layer sera reconstruit quand vous modifiez votre code
COPY . .

# Nettoyage final
RUN find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} +

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]