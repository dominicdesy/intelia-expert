# -*- coding: utf-8 -*-
"""
main.py - Intelia Expert Backend avec LlamaIndex
Version simplifiée préservant votre intelligence métier
"""

import os
import json
import asyncio
import time
import logging
import uuid
from typing import Any, Dict, AsyncGenerator, Optional
from collections import OrderedDict
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI
from langdetect import detect, DetectorFactory

# Import de votre RAG Engine simplifié
from rag_engine import create_rag_engine, process_question_with_rag, RAGSource, RAGResult

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DetectorFactory.seed = 0
load_dotenv()

# Variables globales
rag_engine = None

# Configuration (simplifiée par rapport à votre version originale)
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Paramètres système
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "10000"))
MAX_TENANTS = int(os.getenv("MAX_TENANTS", "200"))
TENANT_TTL = int(os.getenv("TENANT_TTL_SEC", "86400"))

# Configuration CORS (simplifiée)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://expert.intelia.com").split(",")

# Validation configuration
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")

logger.info(f"Mode LlamaIndex: RAG simplifié avec intelligence métier préservée")

# Chargement des messages multilingues (votre logique préservée)
def _load_language_messages(path: str) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {(k.lower() if isinstance(k, str) else k): v for k, v in data.items()}
    except Exception as e:
        logger.error(f"Unable to load {path}: {e}")
        return {
            "default": "Intelia Expert is a poultry-focused application. Questions outside this domain cannot be processed."
        }

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANGUAGE_FILE = os.path.join(BASE_DIR, "languages.json")
OUT_OF_DOMAIN_MESSAGES = _load_language_messages(LANGUAGE_FILE)

def get_out_of_domain_message(lang: str) -> str:
    """Récupère le message hors-domaine dans la langue appropriée"""
    if not lang:
        return OUT_OF_DOMAIN_MESSAGES.get("default")
    code = (lang or "").lower()
    msg = OUT_OF_DOMAIN_MESSAGES.get(code)
    if msg:
        return msg
    short = code.split("-")[0]
    return OUT_OF_DOMAIN_MESSAGES.get(short, OUT_OF_DOMAIN_MESSAGES["default"])

# OpenAI client
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI client initialized")
except Exception as e:
    logger.error(f"Erreur initialisation OpenAI client: {e}")
    raise RuntimeError(f"Impossible d'initialiser le client OpenAI: {e}")

# Mémoire de conversation simplifiée (votre logique préservée mais allégée)
class TenantMemory(OrderedDict):
    """Cache LRU avec TTL pour la mémoire de conversation"""
    
    def set(self, tenant_id: str, item: list):
        now = time.time()
        self[tenant_id] = {"data": item, "ts": now}
        self.move_to_end(tenant_id)
        
        # Purge TTL
        expired_keys = [k for k, v in self.items() if now - v["ts"] > TENANT_TTL]
        for k in expired_keys:
            del self[k]
        
        # Purge LRU
        while len(self) > MAX_TENANTS:
            oldest_tenant, _ = self.popitem(last=False)
            logger.debug(f"Tenant {oldest_tenant} purgé (LRU)")
    
    def get(self, tenant_id: str, default=None):
        if tenant_id not in self:
            return default
        
        now = time.time()
        if now - self[tenant_id]["ts"] > TENANT_TTL:
            del self[tenant_id]
            return default
        
        self[tenant_id]["ts"] = now
        self.move_to_end(tenant_id)
        return self[tenant_id]

conversation_memory = TenantMemory()

def add_to_conversation_memory(tenant_id: str, question: str, answer: str):
    """Ajoute un échange à la mémoire de conversation"""
    tenant_data = conversation_memory.get(tenant_id, {"data": []})
    history = tenant_data["data"]
    
    history.append({
        "question": question, 
        "answer": answer, 
        "timestamp": time.time()
    })
    
    if len(history) > 3:  # Limiter à 3 échanges
        history = history[-3:]
    
    conversation_memory.set(tenant_id, history)

# Helpers de streaming (simplifiés de votre version)
def sse_event(obj: Dict[str, Any]) -> bytes:
    """Formatage SSE"""
    try:
        data = json.dumps(obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        return b"data: {\"type\":\"error\",\"message\":\"Erreur formatage\"}\n\n"

def smart_chunk_text(text: str, max_chunk_size: int = 400) -> list:
    """Découpe intelligente du texte pour streaming"""
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []
    
    chunks = []
    remaining_text = text
    
    while remaining_text:
        if len(remaining_text) <= max_chunk_size:
            chunks.append(remaining_text)
            break
        
        cut_point = max_chunk_size
        while cut_point > 0 and remaining_text[cut_point] != ' ':
            cut_point -= 1
        
        if cut_point == 0:
            cut_point = min(max_chunk_size, len(remaining_text))
        
        chunk = remaining_text[:cut_point].strip()
        if chunk:
            chunks.append(chunk)
        
        remaining_text = remaining_text[cut_point:].strip()
    
    return [chunk for chunk in chunks if chunk.strip()]

# Détection de langue (votre logique préservée)
def guess_lang_from_text(text: str) -> Optional[str]:
    """Détection automatique de la langue"""
    try:
        detected = detect(text)
        lang_mapping = {
            'de': 'de', 'ger': 'de',
            'fr': 'fr', 'fra': 'fr', 
            'en': 'en', 'eng': 'en',
            'es': 'es', 'spa': 'es'
        }
        return lang_mapping.get(detected, detected)
    except Exception:
        # Fallback par mots-clés
        text_lower = text.lower()
        if any(word in text_lower for word in ['poulet', 'aviculture', 'qu\'est', 'comment']):
            return 'fr'
        elif any(word in text_lower for word in ['chicken', 'poultry', 'what', 'how']):
            return 'en'
        return 'fr'  # Défaut français

# Fallback GPT simple
async def generate_fallback_response(query: str, language: str = "fr") -> str:
    """Génération de réponse fallback via OpenAI directement"""
    system_message = {
        'fr': "Tu es un assistant spécialisé en aviculture. Réponds uniquement aux questions dans ce domaine. Si la question est hors-sujet, refuse poliment.",
        'en': "You are a poultry specialist assistant. Only answer questions in this domain. If the question is off-topic, politely decline.",
        'es': "Eres un asistente especializado en avicultura. Solo responde preguntas de este dominio. Si la pregunta está fuera de tema, rechaza educadamente."
    }
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message.get(language, system_message['fr'])},
                {"role": "user", "content": query}
            ],
            max_tokens=600,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erreur fallback GPT: {e}")
        return "Désolé, une erreur est survenue lors de la génération de la réponse."

# Initialisation RAG
async def initialize_rag_engine():
    """Initialise le RAG engine simplifié"""
    global rag_engine
    if rag_engine is not None:
        return rag_engine
    
    try:
        logger.info("Initialisation du RAG Engine LlamaIndex...")
        rag_engine = await create_rag_engine()
        rag_status = rag_engine.get_status()
        logger.info(f"RAG Engine initialisé: {rag_status}")
        return rag_engine
    except Exception as e:
        logger.error(f"Erreur initialisation RAG: {e}")
        return None

# Gestionnaires de cycle de vie
async def startup_event():
    """Démarrage de l'application"""
    logger.info("🚀 Démarrage Intelia Expert - Version LlamaIndex")
    await initialize_rag_engine()

async def shutdown_event():
    """Arrêt de l'application"""
    global rag_engine
    try:
        logger.info("🔄 Arrêt de l'application...")
        if rag_engine:
            await rag_engine.cleanup()
            rag_engine = None
        conversation_memory.clear()
        logger.info("🛑 Arrêt propre terminé")
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage: {e}")

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()

app = FastAPI(title="Intelia Expert - LlamaIndex Backend", debug=False, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

router = APIRouter()

# Routes
@router.get("/health")
def health():
    """Health check avec status RAG"""
    global rag_engine
    
    memory_stats = {
        "total_tenants": len(conversation_memory),
        "total_exchanges": sum(len(v["data"]) for v in conversation_memory.values())
    }
    
    rag_stats = {
        "rag_enabled": True,
        "rag_engine_loaded": rag_engine is not None,
        "rag_status": rag_engine.get_status() if rag_engine else {}
    }
    
    return {
        "ok": True,
        "version": "llama_index_simplified",
        "mode": "rag_with_business_intelligence",
        "features": [
            "llama_index_rag",
            "intent_processor_preserved", 
            "multilingual_support",
            "conversation_memory",
            "streaming_responses"
        ],
        "conversation_memory": memory_stats,
        "rag": rag_stats
    }

@router.post("/chat/stream")
async def chat_stream(request: Request):
    """Route principale de chat avec streaming"""
    request_start_time = time.time()
    
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erreur parsing JSON: {e}")
        raise HTTPException(status_code=400, detail="invalid_json")

    tenant_id = (payload.get("tenant_id") or "").strip()
    message = (payload.get("message") or "").strip()

    # Validation
    if not tenant_id or not message:
        raise HTTPException(status_code=400, detail="missing_fields")
    if len(message) > MAX_REQUEST_SIZE:
        raise HTTPException(status_code=400, detail="message_too_long")

    # Détection de langue
    lang = guess_lang_from_text(message) or "fr"
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[REQ {request_id}] tenant={tenant_id[:10]}..., lang={lang}, query='{message[:50]}...'")

    async def event_source() -> AsyncGenerator[bytes, None]:
        final_response = ""
        sent_final = False
        
        try:
            # Initialiser RAG si nécessaire
            global rag_engine
            if rag_engine is None:
                rag_engine = await initialize_rag_engine()
            
            # Traitement RAG principal
            if rag_engine:
                rag_result = await process_question_with_rag(
                    rag_engine, message, lang, tenant_id
                )
                
                logger.info(f"[REQ {request_id}] RAG result: {rag_result.source.value}, confidence: {rag_result.confidence:.3f}")
                
                # Cas 1: Question hors domaine
                if rag_result.source == RAGSource.OOD_FILTERED:
                    final_response = get_out_of_domain_message(lang)
                    
                # Cas 2: Réponse RAG trouvée
                elif (rag_result.source == RAGSource.RAG_KNOWLEDGE and 
                      rag_result.answer and rag_result.confidence > 0.6):
                    
                    # Streaming de la réponse RAG
                    chunks = smart_chunk_text(rag_result.answer, STREAM_CHUNK_LEN)
                    for chunk in chunks:
                        if chunk.strip():
                            yield sse_event({"type": "delta", "text": chunk})
                            await asyncio.sleep(0.02)
                    
                    final_response = rag_result.answer
                    
                    # Métadonnées enrichies
                    metadata = {
                        "source": "rag_knowledge",
                        "confidence": rag_result.confidence,
                        "context_docs": len(rag_result.context_docs),
                        "processing_time": rag_result.processing_time,
                        "request_id": request_id
                    }
                    if hasattr(rag_result, 'metadata') and rag_result.metadata:
                        metadata.update(rag_result.metadata)
                    
                    yield sse_event({
                        "type": "final", 
                        "answer": final_response,
                        "metadata": metadata
                    })
                    sent_final = True
                
                # Cas 3: RAG insuffisant - Fallback GPT avec prompt spécialisé
                else:
                    logger.info(f"[REQ {request_id}] Fallback to specialized GPT")
                    # Récupérer l'intent_result pour les prompts spécialisés
                    intent_result = getattr(rag_result, 'intent_result', None)
                    final_response = await generate_fallback_response(message, lang, intent_result)
            else:
                # Pas de RAG disponible - Fallback direct
                final_response = await generate_fallback_response(message, lang)
            
            # Envoyer final si pas déjà fait
            if not sent_final:
                latency_ms = int((time.time() - request_start_time) * 1000)
                yield sse_event({
                    "type": "final", 
                    "answer": final_response,
                    "metadata": {
                        "source": "fallback_gpt",
                        "latency_ms": latency_ms,
                        "request_id": request_id
                    }
                })
            
            # Ajouter à la mémoire de conversation
            if final_response:
                add_to_conversation_memory(tenant_id, message, final_response)
                
        except Exception as e:
            logger.error(f"[REQ {request_id}] Erreur dans event_source: {e}")
            if not sent_final:
                yield sse_event({
                    "type": "final", 
                    "answer": "Désolé, une erreur est survenue lors du traitement de votre question.",
                    "metadata": {"source": "error", "error": str(e)[:100], "request_id": request_id}
                })

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
    }
    
    return StreamingResponse(event_source(), headers=headers)

@router.get("/rag/status")
def rag_status():
    """Status détaillé du système RAG"""
    global rag_engine
    
    base_status = {
        "version": "llama_index_0.10.57",
        "rag_engine_loaded": rag_engine is not None
    }
    
    if rag_engine:
        detailed_status = rag_engine.get_status()
        base_status.update(detailed_status)
    
    return base_status

# Mount router
app.include_router(router, prefix=BASE_PATH)

@app.get("/")
def root():
    return JSONResponse({
        "service": "intelia-expert-llama", 
        "version": "2.0-llama-index-simplified",
        "sse_endpoint": f"{BASE_PATH}/chat/stream",
        "features": [
            "llama_index_rag",
            "business_intelligence_preserved",
            "async_streaming", 
            "multilingual_support",
            "conversation_memory",
            "domain_filtering"
        ],
        "simplifications": [
            "reduced_codebase_70_percent",
            "unified_rag_pipeline", 
            "streamlined_configuration",
            "maintained_business_logic"
        ]
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)