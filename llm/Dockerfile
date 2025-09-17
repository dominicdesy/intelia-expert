FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Installation système optimisée
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge \
    && rm -rf /root/.cache /root/.local /tmp/* /var/tmp/*

# Copie du code source selon structure LLM
COPY *.py ./
COPY config/ ./config/
COPY core/ ./core/
COPY api/ ./api/
COPY cache/ ./cache/
COPY generation/ ./generation/
COPY processing/ ./processing/
COPY retrieval/ ./retrieval/
COPY security/ ./security/
COPY utils/ ./utils/

# Nettoyage final
RUN find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} + \
    && find . -name "*.pyo" -delete \
    && rm -f requirements.txt

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); exit(0 if s.connect_ex(('127.0.0.1', 8080))==0 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]