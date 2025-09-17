FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Installation en une seule couche + nettoyage immédiat
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev postgresql-dev \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        fastapi==0.104.1 \
        uvicorn[standard]==0.24.0 \
        python-multipart==0.0.6 \
        pydantic==2.5.0 \
        psycopg2-binary \
        asyncpg \
        supabase==2.9.1 \
        httpx \
        openai==1.51.0 \
        requests==2.31.0 \
        aiohttp \
        python-dotenv==1.0.0 \
        psutil==5.9.5 \
        typing-extensions \
        tenacity \
        toml==0.10.2 \
    && apk del .build-deps \
    && rm -rf /root/.cache /tmp/* /var/tmp/*

# Copie SÉLECTIVE - seulement les fichiers Python essentiels
COPY *.py ./
COPY config/ ./config/
COPY core/ ./core/
COPY api/ ./api/

# Nettoyage agressif final
RUN find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} + \
    && find . -name "*.pyo" -delete

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]env==1.0.0 \
        psutil==5.9.5 \
        typing-extensions \
        tenacity \
        toml==0.10.2 \
    && apk del .build-deps \
    && rm -rf /root/.cache /tmp/* /var/tmp/*

# Copie du code seulement
COPY app/ ./app/
COPY *.py ./

EXPOSE 8080

# Healthcheck simple
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]