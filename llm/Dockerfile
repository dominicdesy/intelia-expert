FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .   # ← depuis le contexte ./llm, cela place main.py + intents.json + languages.json dans /app
ENV BASE_PATH=/llm
# facultatif mais explicite :
ENV LANGUAGE_FILE=/app/languages.json
ENV INTENTS_FILE=/app/intents.json
EXPOSE 8080
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8080"]
