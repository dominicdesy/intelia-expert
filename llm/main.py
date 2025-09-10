#
# main.py — Intelia LLM backend (FastAPI + SSE)
#
# Python 3.11+
#

import os
import json
import time
from typing import Any, Dict, Generator

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError

# Charge .env si présent (utile en local)
load_dotenv()

# -------- Config via variables d'environnement --------
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")  # ex: "/llm" ou ""
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")  # asst_... (créé avec tes fichiers)
# Optionnel: timeouts
POLL_INTERVAL_SEC = float(os.environ.get("POLL_INTERVAL_SEC", "0.6"))
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------- App & CORS --------
app = FastAPI(title="Intelia LLM Backend")
# CORS permissif par défaut; restreins origin en prod si besoin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

router = APIRouter()


def sse_event(obj: Dict[str, Any]) -> bytes:
    """Encode un event SSE (Server-Sent Events)."""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8")


@router.get("/health")
def health():
    return {"ok": True, "assistant_id": ASSISTANT_ID}


@router.post("/chat/stream")
async def chat_stream(req: Request):
    """
    Body attendu (JSON):
      { "tenant_id": "ten_123", "lang": "fr", "message": "..." }

    Réponse: flux SSE
      data: {"type":"delta","text":"..."}
      ...
      data: {"type":"final","answer":"..."}

    Notes:
      - Pas de citations envoyées au frontend (mode simple).
      - Utilise Assistants v2 pour fiabilité avec Vector Store.
    """
    try:
        payload = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    tenant_id = (payload.get("tenant_id") or "").strip()
    lang = (payload.get("lang") or "fr").strip()
    message = (payload.get("message") or "").strip()

    if not tenant_id or not message:
        raise HTTPException(status_code=400, detail="missing_fields")

    def run() -> Generator[bytes, None, None]:
        try:
            # 1) Thread
            thread = client.beta.threads.create()

            # 2) Message utilisateur + rappel "data-only"
            reminder = (
                "RÉPONDS EXCLUSIVEMENT à partir des documents du Vector Store. "
                "Si l'information est absente, réponds exactement: "
                "\"Hors base: information absente de la connaissance Intelia.\""
            )
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"{message}\n\nLangue: {lang}.\n{reminder}",
            )

            # 3) Lancer le run (assistant déjà relié au Vector Store)
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID,
            )

            # 4) Poll & envoie un petit delta pour signaler l'activité
            spinner_sent = False
            while True:
                r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                if r.status in ("completed", "failed", "cancelled", "expired"):
                    break
                if not spinner_sent:
                    yield sse_event({"type": "delta", "text": "…"})
                    spinner_sent = True
                time.sleep(POLL_INTERVAL_SEC)

            if r.status != "completed":
                yield sse_event({"type": "final", "answer": "Désolé, la génération a échoué."})
                return

            # 5) Récupère le dernier message assistant
            msgs = client.beta.threads.messages.list(thread_id=thread.id)
            answer = ""
            for m in msgs.data:
                if m.role == "assistant":
                    for c in m.content:
                        if getattr(c, "type", "") == "text":
                            answer = c.text.value or ""
                            break
                    if answer:
                        break

            # 6) Stream en plusieurs petits deltas pour l'UX
            if answer:
                for i in range(0, len(answer), STREAM_CHUNK_LEN):
                    yield sse_event({"type": "delta", "text": answer[i : i + STREAM_CHUNK_LEN]})
                    time.sleep(0.02)

            yield sse_event({"type": "final", "answer": answer})

        except BadRequestError as e:
            # Erreur API OpenAI
            yield sse_event({"type": "final", "answer": f"Erreur LLM: {e}"} )
        except Exception as e:
            # Autre erreur (réseau, etc.)
            yield sse_event({"type": "final", "answer": "Erreur interne. Réessayez."})

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
    }
    return StreamingResponse(run(), headers=headers)


# Monte toutes les routes sous BASE_PATH (ex: /llm)
app.include_router(router, prefix=BASE_PATH)


@app.get("/")
def root():
    # Petit ping pour vérifier le service
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream"})


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"
