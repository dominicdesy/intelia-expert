FROM python:3.11-slim

WORKDIR /app

# (reco) pip récent pour éviter des résolutions bancales
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

ENV BASE_PATH=/llm
ENV LANGUAGE_FILE=/app/languages.json
ENV INTENTS_FILE=/app/intents.json

EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
