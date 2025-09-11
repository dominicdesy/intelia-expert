NON_AGRI_TERMS = [
    # Médias / Divertissement (FR/EN/DE/ES/IT/NL/PL/PT)
    "cinéma", "film", "films", "séries", "serie", "séries tv", "netflix", "hollywood", "bollywood", "disney",
    "pixar", "musique", "concert", "rap", "pop", "rock", "jazz", "opéra", "orchestre", "télévision", "télé",
    "emission", "émission", "jeux vidéo", "gaming", "playstation", "xbox", "nintendo", "fortnite", "minecraft",
    "kino", "filme", "musik", "konzert", "fernsehen", "videospiele", "spiele",  # DE
    "cine", "música", "televisión", "videojuegos", "juegos",  # ES
    "cinema", "musica", "televisione", "videogiochi", "giochi",  # IT
    "bioscoop", "muziek", "televisie", "videospellen", "spellen",  # NL
    "kino", "muzyka", "telewizja", "gry wideo", "gry",  # PL
    "cinema", "música", "televisão", "videojogos", "jogos",  # PT
    
    # Sports
    "football", "soccer", "nba", "nfl", "nhl", "hockey", "mlb", "tennis", "golf", "cyclisme",
    "tour de france", "formule 1", "f1", "boxe", "ufc", "olympiques",
    "fußball", "sport", "olympia", "bundesliga",  # DE
    "fútbol", "deporte", "olimpiadas",# -*- coding: utf-8 -*-
#
# main.py — Intelia LLM backend (FastAPI + SSE)
# Python 3.11+
#

import os
import re
import json
import asyncio
import time
import logging
import uuid
from typing import Any, Dict, AsyncGenerator, Optional

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from langdetect import detect, DetectorFactory

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DetectorFactory.seed = 0
load_dotenv()

# -----------------------------------------------------------------------------
# Env config
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")
POLL_INTERVAL_SEC = float(os.environ.get("POLL_INTERVAL_SEC", "0.6"))
ASSISTANT_TIMEOUT = int(os.getenv("ASSISTANT_TIMEOUT_SEC", "30"))
ASSISTANT_MAX_POLLS = int(os.getenv("ASSISTANT_MAX_POLLS", "200"))
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))
DEBUG_GUARD = os.getenv("DEBUG_GUARD", "0") == "1"
HYBRID_MODE = os.getenv("HYBRID_MODE", "1") == "1"
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o")
FALLBACK_TEMPERATURE = float(os.getenv("FALLBACK_TEMPERATURE", "0.7"))
FALLBACK_MAX_COMPLETION_TOKENS = int(
    os.getenv("FALLBACK_MAX_COMPLETION_TOKENS", os.getenv("FALLBACK_MAX_TOKENS", "600"))
)

LANGUAGE_FILE = os.getenv("LANGUAGE_FILE", os.path.join(BASE_DIR, "languages.json"))

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
if not ASSISTANT_ID:
    raise RuntimeError("ASSISTANT_ID is required")

# -----------------------------------------------------------------------------
# Load messages (languages.json)
# -----------------------------------------------------------------------------
def _load_language_messages(path: str) -> Dict[str, str]:
    """
    languages.json structure:
    {
      "default": "...",
      "fr": "...",
      "en": "...",
      ...
    }
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "default" not in data or not isinstance(data["default"], str):
            raise ValueError("languages.json must include a 'default' string.")
        return {(k.lower() if isinstance(k, str) else k): v for k, v in data.items()}
    except Exception as e:
        logger.error(f"Unable to load {path}: {e}")
        return {
            "default": "Intelia Expert is a poultry-focused application. Questions outside this domain cannot be processed."
        }

OUT_OF_DOMAIN_MESSAGES = _load_language_messages(LANGUAGE_FILE)

logger.info(f"LANGUAGE_FILE={LANGUAGE_FILE} exists={os.path.exists(LANGUAGE_FILE)}")
logger.info(f"FALLBACK_MODEL={FALLBACK_MODEL}")

def get_out_of_domain_message(lang: str) -> str:
    if not lang:
        return OUT_OF_DOMAIN_MESSAGES.get("default")
    code = (lang or "").lower()
    msg = OUT_OF_DOMAIN_MESSAGES.get(code)
    if msg:
        return msg
    short = code.split("-")[0]
    return OUT_OF_DOMAIN_MESSAGES.get(short, OUT_OF_DOMAIN_MESSAGES["default"])

# -----------------------------------------------------------------------------
# OpenAI client
# -----------------------------------------------------------------------------
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    test_models = client.models.list()
    logger.info(f"OpenAI client initialized successfully. Available models: {len(test_models.data)}")
except Exception as e:
    logger.error(f"Erreur initialisation OpenAI client: {e}")
    raise RuntimeError(f"Impossible d'initialiser le client OpenAI: {e}")

# -----------------------------------------------------------------------------
# FastAPI
# -----------------------------------------------------------------------------
app = FastAPI(title="Intelia LLM Backend", debug=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
router = APIRouter()

# -----------------------------------------------------------------------------
# SSE helpers
# -----------------------------------------------------------------------------
def sse_event(obj: Dict[str, Any]) -> bytes:
    try:
        data = json.dumps(obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        return b"data: {\"type\":\"error\",\"message\":\"Erreur formatage\"}\n\n"

def send_event(obj: Dict[str, Any]) -> bytes:
    if "type" not in obj:
        obj = {"type": "final", "answer": "Désolé, une erreur de format interne est survenue."}
    if obj.get("type") == "final" and not obj.get("answer"):
        obj["answer"] = "Désolé, aucune réponse n'a pu être générée."
    return sse_event(obj)

# -----------------------------------------------------------------------------
# Language detection
# -----------------------------------------------------------------------------
def parse_accept_language(header: Optional[str]) -> Optional[str]:
    if not header:
        return None
    try:
        first = header.split(",")[0].strip()
        code = first.split(";")[0].split("-")[0].lower()
        if 2 <= len(code) <= 3:
            return code
    except Exception:
        pass
    return None

def guess_lang_from_text(text: str) -> Optional[str]:
    try:
        detected = detect(text)
        # Normaliser les codes de langue
        if detected in ['de', 'ger']:
            return 'de'
        elif detected in ['fr', 'fra']:
            return 'fr'
        elif detected in ['en', 'eng']:
            return 'en'
        elif detected in ['es', 'spa']:
            return 'es'
        else:
            return detected
    except Exception:
        # Fallback basique si langdetect échoue
        text_lower = text.lower()
        if any(word in text_lower for word in ['was', 'ist', 'wie', 'wo', 'wann', 'warum', 'kryptowährung', 'deutschland']):
            return 'de'
        elif any(word in text_lower for word in ['what', 'is', 'how', 'where', 'when', 'why', 'cryptocurrency']):
            return 'en'
        elif any(word in text_lower for word in ['qué', 'es', 'cómo', 'dónde', 'cuándo', 'por qué']):
            return 'es'
        elif any(word in text_lower for word in ['qu\'est', 'comment', 'où', 'quand', 'pourquoi', 'cryptomonnaie']):
            return 'fr'
        return None

# -----------------------------------------------------------------------------
# Text helpers
# -----------------------------------------------------------------------------
CITATION_PATTERN = re.compile(r"【[^【】]*】")

def clean_text(txt: str) -> str:
    if not txt:
        return txt
    cleaned = CITATION_PATTERN.sub("", txt)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

# -----------------------------------------------------------------------------
# Domain guard (permissif: bloque évidents hors-agri)
# -----------------------------------------------------------------------------
NON_AGRI_TERMS = [
    "cinéma", "film", "films", "séries", "serie", "séries tv", "netflix", "hollywood", "bollywood", "disney",
    "pixar", "musique", "concert", "rap", "pop", "rock", "jazz", "opéra", "orchestre", "télévision", "télé",
    "emission", "émission", "jeux vidéo", "gaming", "playstation", "xbox", "nintendo", "fortnite", "minecraft",
    "football", "soccer", "nba", "nfl", "nhl", "hockey", "mlb", "tennis", "golf", "cyclisme",
    "tour de france", "formule 1", "f1", "boxe", "ufc", "olympiques",
    "élections", "elections", "président", "premier ministre", "parlement", "guerre", "otan", "onu",
    "bourse", "actions", "nasdaq", "wall street",
    "crypto", "cryptomonnaie", "cryptomonnaies", "cryptocurrency", "cryptocurrencies",
    "blockchain", "bitcoin", "ethereum",
    "iphone", "android", "samsung", "apple", "google", "microsoft",
    "cancer", "diabète", "covid", "hôpital", "clinique",
    "mode", "vêtements", "voyage", "vacances",
    "astronomie", "physique quantique", "spacex",
    "religion", "église", "astrologie", "horoscope",
]
NON_AGRI_PAT = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in NON_AGRI_TERMS) + r")\b", re.IGNORECASE)

def guard_debug(reason: str, text: str):
    if DEBUG_GUARD:
        logger.info(f"[GUARD] {reason} :: {text[:160]!r}")

def is_agri_question(text: str) -> bool:
    if not text:
        return True
    blocked = NON_AGRI_PAT.search(text) is not None
    if blocked:
        guard_debug("blocked_non_agri_match", text)
    return not blocked

# -----------------------------------------------------------------------------
# Chat Completions helpers
# -----------------------------------------------------------------------------
def _chat_args(messages, max_completion_tokens, stream=False, temperature=None):
    args = dict(messages=messages, max_completion_tokens=max_completion_tokens, stream=stream)
    force_temp = os.getenv("FORCE_TEMPERATURE_PARAM", "0") == "1"
    if force_temp and temperature is not None:
        args["temperature"] = float(temperature)
    return args

def create_chat_completion_safe(client, model, messages, max_completion_tokens, stream=False, temperature=None):
    try:
        kwargs = _chat_args(messages, max_completion_tokens, stream=stream, temperature=temperature)
        return client.chat.completions.create(model=model, **kwargs)
    except Exception as e:
        emsg = str(e)
        if ("Unsupported value: 'temperature'" in emsg) or ("does not support" in emsg and "temperature" in emsg):
            kwargs = _chat_args(messages, max_completion_tokens, stream=stream, temperature=None)
            return client.chat.completions.create(model=model, **kwargs)
        raise

# -----------------------------------------------------------------------------
# Data-only (Assistant v2)
# -----------------------------------------------------------------------------
def run_data_only_assistant(client: OpenAI, assistant_id: str, user_text: str, lang: str) -> str:
    reminder = (
        f"INSTRUCTIONS STRICTES:\n"
        f"1. RÉPONDS EXCLUSIVEMENT à partir des documents du Vector Store\n"
        f"2. Si l'information est totalement absente, réponds: \"Hors base: information absente de la connaissance Intelia.\"\n"
        f"3. TOUJOURS répondre dans la langue de la question: {lang}\n\n"
        f"Question utilisateur: {user_text}"
    )
    
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id, 
            role="user", 
            content=reminder
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id, 
            assistant_id=assistant_id
        )
        
        timeout = time.time() + ASSISTANT_TIMEOUT
        polls = 0
        
        while time.time() < timeout and polls < ASSISTANT_MAX_POLLS:
            r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if r.status in ("completed", "failed", "cancelled", "expired"):
                break
            time.sleep(POLL_INTERVAL_SEC)
            polls += 1
        
        logger.info(f"[ASSISTANT] Status: {r.status} après {polls} polls")
        
        if r.status != "completed":
            logger.error(f"Assistant run failed with status: {r.status}")
            return "Hors base: information absente de la connaissance Intelia."
        
        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        msgs_data = msgs.data
        
        if len(msgs_data) == 1:
            latest = msgs_data[0] if msgs_data[0].role == "assistant" else None
        else:
            latest = next(
                (m for m in sorted(msgs_data, key=lambda x: x.created_at, reverse=True) if m.role == "assistant"),
                None
            )
        
        if latest:
            for c in latest.content:
                if getattr(c, "type", "") == "text":
                    txt = clean_text((c.text.value or "").strip())
                    if txt:
                        logger.info(f"[ASSISTANT] Réponse: {txt[:100]}...")
                        return txt
        
        return "Hors base: information absente de la connaissance Intelia."
        
    except Exception as e:
        logger.error(f"Erreur assistant data-only: {e}")
        return "Hors base: information absente de la connaissance Intelia."

# -----------------------------------------------------------------------------
# Fallback general (stream)
# -----------------------------------------------------------------------------
async def stream_fallback_general(client: OpenAI, text: str):
    system = (
        "Tu es un assistant spécialisé en agriculture et aviculture. "
        "Tu remponds UNIQUEMENT aux questions dans ce domaine. "
        "Si la question sort du cadre, refuse poliment. "
        "Réponds dans la MÊME langue que la question de l'utilisateur. "
        "Sois précis et technique quand approprié."
    )
    try:
        stream = create_chat_completion_safe(
            client,
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
            max_completion_tokens=FALLBACK_MAX_COMPLETION_TOKENS,
            stream=True,
            temperature=FALLBACK_TEMPERATURE
        )
        final_buf = []
        for event in stream:
            if hasattr(event, "choices") and event.choices:
                delta = event.choices[0].delta
                if delta and getattr(delta, "content", None):
                    chunk = clean_text(delta.content)
                    final_buf.append(chunk)
                    yield send_event({"type": "delta", "text": chunk})
        final_text = clean_text("".join(final_buf).strip())
        if not final_text:
            final_text = "Désolé, aucune réponse n'a pu être générée. Pouvez-vous reformuler ou préciser votre question ?"
        yield send_event({"type": "final", "answer": final_text})
    except Exception as e:
        if "must be verified to stream" in str(e).lower() or "param': 'stream'" in str(e).lower():
            resp = create_chat_completion_safe(
                client, model=FALLBACK_MODEL,
                messages=[{"role":"system","content":system},{"role":"user","content":text}],
                max_completion_tokens=FALLBACK_MAX_COMPLETION_TOKENS, stream=False, temperature=FALLBACK_TEMPERATURE
            )
            final_text = clean_text(resp.choices[0].message.content or "") or "Désolé, aucune réponse n'a pu être générée."
            yield send_event({"type":"final","answer":final_text})
            return
        logger.error(f"Erreur fallback streaming: {e}")
        yield send_event({"type": "final", "answer": "Désolé, une erreur est survenue et la réponse n'a pas pu être générée."})

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.get("/health")
def health():
    return {
        "ok": True,
        "assistant_id": ASSISTANT_ID,
        "guard_mode": "permissive_non_agri",
        "debug_guard": DEBUG_GUARD,
        "hybrid_mode": HYBRID_MODE,
        "language_file": LANGUAGE_FILE,
        "blocked_terms_file": BLOCKED_TERMS_FILE,
        "fallback_model": FALLBACK_MODEL,
        "languages_loaded": list(OUT_OF_DOMAIN_MESSAGES.keys())[:10] + (["…"] if len(OUT_OF_DOMAIN_MESSAGES) > 10 else []),
        "blocked_terms_count": len(BLOCKED_TERMS),
        "blocked_terms_sample": BLOCKED_TERMS[:10]
    }

@router.post("/chat/stream")
async def chat_stream(request: Request):
    """
    JSON attendu: { "tenant_id": "ten_123", "message": "...", "allow_fallback": true }
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erreur parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="invalid_json")

    tenant_id = (payload.get("tenant_id") or "").strip()
    message = (payload.get("message") or "").strip()
    allow_fallback = bool(payload.get("allow_fallback", True))

    if not tenant_id or not message:
        raise HTTPException(status_code=400, detail="missing_fields")
    if len(message) > 10000:
        raise HTTPException(status_code=400, detail="message_too_long")
    if len(message) < 2:
        raise HTTPException(status_code=400, detail="message_too_short")
    if "\x00" in message:
        raise HTTPException(status_code=400, detail="message_invalid_chars")

    # Langue = celle de la question (prioritaire). Accept-Language en secours.
    accept_lang = request.headers.get("accept-language")
    lang = guess_lang_from_text(message) or parse_accept_language(accept_lang) or "fr"
    lang = (lang or "fr")[:5].split("-")[0].lower()

    request_id = str(uuid.uuid4())
    logger.info(f"[REQ {request_id}] tenant={tenant_id}, lang={lang}, message='{message[:50]}...'")

    async def event_source() -> AsyncGenerator[bytes, None]:
        sent_final = False
        try:
            # 1) Garde-fou: hors-domaine => message fixe depuis languages.json
            if not is_agri_question(message):
                answer = clean_text(get_out_of_domain_message(lang))
                yield send_event({"type": "final", "answer": answer})
                sent_final = True
                return

            _client = client

            # 2) Tentative data-only (Assistant v2)
            text = await asyncio.to_thread(run_data_only_assistant, _client, ASSISTANT_ID, message, lang)
            text = clean_text(text)
            logger.info(f"[REQ {request_id}] Assistant response: {text[:100]}...")

            # 3) Fallback GPT si hors base
            if text.lower().startswith("hors base"):
                if HYBRID_MODE and allow_fallback:
                    logger.info(f"[REQ {request_id}] Basculement vers fallback GPT")
                    async for sse in stream_fallback_general(_client, message):
                        yield sse
                    sent_final = True
                    return
                else:
                    yield send_event({"type": "final", "answer": text})
                    sent_final = True
                    return

            # 4) Réponse data-only (stream simulé)
            if not text:
                text = "Désolé, aucune réponse n'a pu être générée."
                
            for i in range(0, len(text), STREAM_CHUNK_LEN):
                chunk = clean_text(text[i:i + STREAM_CHUNK_LEN])
                if chunk:
                    yield send_event({"type": "delta", "text": chunk})
                    await asyncio.sleep(0.02)
                    
            final_answer = text
            yield send_event({"type": "final", "answer": final_answer})
            sent_final = True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[REQ {request_id}] Erreur dans event_source: {e}")
            if not sent_final:
                yield send_event({"type": "final", "answer": "Désolé, une erreur est survenue et la réponse n'a pas pu être générée."})
                sent_final = True
            else:
                yield send_event({"type": "error", "message": f"Erreur interne: {str(e)}"})

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
    }
    return StreamingResponse(event_source(), headers=headers)

# -----------------------------------------------------------------------------
# Mount router & misc
# -----------------------------------------------------------------------------
app.include_router(router, prefix=BASE_PATH)

@app.get("/")
def root():
    return JSONResponse({"service": "intelia-llm", "sse": f"{BASE_PATH}/chat/stream", "version": "simplified"})

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée: {exc}")
    return JSONResponse(status_code=500, content={"detail": f"Erreur interne du serveur: {str(exc)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)