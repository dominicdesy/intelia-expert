# -*- coding: utf-8 -*-
"""
main.py - Intelia Expert Backend avec RAG Enhanced intégré
Version optimisée préservant votre intelligence métier avec RAG Enhanced
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

# Import du RAG Engine Enhanced (remplace l'ancien import)
from rag_engine import InteliaRAGEngine, create_rag_engine, RAGSource, RAGResult

# Tentative d'import Agent RAG (optionnel)
try:
    from agent_rag_extension import InteliaAgentRAG, create_agent_rag_engine, AgentResult, QueryComplexity
    AGENT_RAG_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("Agent RAG disponible")
except ImportError as e:
    AGENT_RAG_AVAILABLE = False
    # Fallback types pour compatibilité
    class QueryComplexity:
        SIMPLE = "simple"
        COMPLEX = "complex"
    class AgentResult:
        pass

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DetectorFactory.seed = 0
load_dotenv()

# Variables globales - MODIFIÉ pour RAG Enhanced
rag_engine_enhanced = None  # Nouvelle instance RAG Enhanced
agent_rag_engine = None     # Agent RAG optionnel

# Configuration (préservée de votre version originale)
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Paramètres système améliorés
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "10000"))
MAX_TENANTS = int(os.getenv("MAX_TENANTS", "200"))
TENANT_TTL = int(os.getenv("TENANT_TTL_SEC", "86400"))

# Configuration CORS (préservée)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://expert.intelia.com").split(",")

# Nouveaux paramètres pour fonctionnalités améliorées
ENABLE_RESPONSE_STREAMING = os.getenv("ENABLE_RESPONSE_STREAMING", "true").lower() == "true"
ENABLE_METRICS_LOGGING = os.getenv("ENABLE_METRICS_LOGGING", "true").lower() == "true"
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "3"))

# Nouveaux paramètres RAG Enhanced
USE_AGENT_RAG = os.getenv("USE_AGENT_RAG", "false").lower() == "true"  # Désactivé par défaut
PREFER_ENHANCED_RAG = os.getenv("PREFER_ENHANCED_RAG", "true").lower() == "true"

# Validation configuration
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")

logger.info(f"Mode RAG Enhanced: Cache Redis + Recherche Hybride + Guardrails")

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

# Mémoire de conversation simplifiée (préservée avec améliorations mineures)
class TenantMemory(OrderedDict):
    """Cache LRU avec TTL pour la mémoire de conversation - Version améliorée"""
    
    def set(self, tenant_id: str, item: list):
        now = time.time()
        self[tenant_id] = {"data": item, "ts": now, "last_query": ""}
        self.move_to_end(tenant_id)
        
        # Purge TTL
        expired_keys = [k for k, v in self.items() if now - v["ts"] > TENANT_TTL]
        for k in expired_keys:
            del self[k]
            logger.debug(f"Tenant {k} expiré (TTL)")
        
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
    
    def update_last_query(self, tenant_id: str, query: str):
        """Met à jour la dernière requête pour un tenant"""
        if tenant_id in self:
            self[tenant_id]["last_query"] = query

conversation_memory = TenantMemory()

def add_to_conversation_memory(tenant_id: str, question: str, answer: str, source: str = "rag_enhanced"):
    """Ajoute un échange à la mémoire de conversation - Version améliorée"""
    tenant_data = conversation_memory.get(tenant_id, {"data": []})
    history = tenant_data["data"]
    
    history.append({
        "question": question, 
        "answer": answer, 
        "timestamp": time.time(),
        "answer_source": source  # Traçabilité améliorée
    })
    
    # Limiter selon la configuration
    if len(history) > MAX_CONVERSATION_CONTEXT:
        history = history[-MAX_CONVERSATION_CONTEXT:]
    
    conversation_memory.set(tenant_id, history)
    conversation_memory.update_last_query(tenant_id, question)

# Classe de métriques pour monitoring amélioré - ÉTENDUE pour RAG Enhanced
class MetricsCollector:
    """Collecteur de métriques pour monitoring des performances"""
    
    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "rag_enhanced_queries": 0,
            "agent_queries": 0,
            "simple_queries": 0,
            "complex_queries": 0,
            "rag_standard_queries": 0,
            "ood_filtered": 0,
            "fallback_queries": 0,
            "verified_responses": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "hybrid_searches": 0,
            "guardrail_violations": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0,
        }
        self.recent_processing_times = []
        self.recent_confidences = []
        self.max_recent_samples = 100
    
    def record_query(self, result, source_type: str = "unknown"):
        """Enregistre les métriques d'une requête - Compatible Enhanced RAG + Agent"""
        if not ENABLE_METRICS_LOGGING:
            return
        
        self.metrics["total_queries"] += 1
        
        # Gestion selon le type de source
        if source_type == "rag_enhanced":
            self.metrics["rag_enhanced_queries"] += 1
            
        elif source_type == "agent_rag":
            self.metrics["agent_queries"] += 1
            if hasattr(result, 'complexity'):
                if result.complexity == QueryComplexity.SIMPLE:
                    self.metrics["simple_queries"] += 1
                else:
                    self.metrics["complex_queries"] += 1
        
        # Traitement selon le type de résultat
        if hasattr(result, 'source'):
            if result.source == RAGSource.RAG_KNOWLEDGE:
                self.metrics["rag_standard_queries"] += 1
            elif result.source == RAGSource.RAG_VERIFIED:
                self.metrics["rag_standard_queries"] += 1
                self.metrics["verified_responses"] += 1
            elif result.source == RAGSource.OOD_FILTERED:
                self.metrics["ood_filtered"] += 1
            else:
                self.metrics["fallback_queries"] += 1
        
        # Métriques des optimisations
        if hasattr(result, 'metadata') and result.metadata:
            opt_stats = result.metadata.get("optimization_stats", {})
            self.metrics["cache_hits"] += opt_stats.get("cache_hits", 0)
            self.metrics["cache_misses"] += opt_stats.get("cache_misses", 0)
            self.metrics["hybrid_searches"] += opt_stats.get("hybrid_searches", 0)
            self.metrics["guardrail_violations"] += opt_stats.get("guardrail_violations", 0)
        
        # Temps de traitement
        processing_time = getattr(result, 'processing_time', 0)
        if processing_time > 0:
            self.recent_processing_times.append(processing_time)
            if len(self.recent_processing_times) > self.max_recent_samples:
                self.recent_processing_times.pop(0)
            
            self.metrics["avg_processing_time"] = (
                sum(self.recent_processing_times) / len(self.recent_processing_times)
            )
        
        # Confiance
        confidence = getattr(result, 'confidence', 0)
        if confidence > 0:
            self.recent_confidences.append(confidence)
            if len(self.recent_confidences) > self.max_recent_samples:
                self.recent_confidences.pop(0)
            
            self.metrics["avg_confidence"] = (
                sum(self.recent_confidences) / len(self.recent_confidences)
            )
    
    def get_metrics(self) -> Dict:
        """Retourne les métriques actuelles"""
        total_queries = max(1, self.metrics["total_queries"])
        
        return {
            **self.metrics,
            "success_rate": (
                (self.metrics["rag_enhanced_queries"] + self.metrics["verified_responses"] + self.metrics["agent_queries"]) / total_queries
            ),
            "enhanced_rag_usage_rate": self.metrics["rag_enhanced_queries"] / total_queries,
            "agent_usage_rate": self.metrics["agent_queries"] / total_queries,
            "cache_hit_rate": (
                self.metrics["cache_hits"] / max(1, self.metrics["cache_hits"] + self.metrics["cache_misses"])
            ),
            "hybrid_search_rate": self.metrics["hybrid_searches"] / total_queries,
            "guardrail_violation_rate": self.metrics["guardrail_violations"] / total_queries
        }

metrics_collector = MetricsCollector()

# Helpers de streaming (préservés, légèrement optimisés)
def sse_event(obj: Dict[str, Any]) -> bytes:
    """Formatage SSE amélioré avec gestion d'erreurs robuste"""
    try:
        data = json.dumps(obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        error_obj = {"type": "error", "message": "Erreur formatage données"}
        data = json.dumps(error_obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")

def smart_chunk_text(text: str, max_chunk_size: int = 400) -> list:
    """Découpe intelligente du texte pour streaming - Version améliorée"""
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []
    
    chunks = []
    remaining_text = text
    
    while remaining_text:
        if len(remaining_text) <= max_chunk_size:
            chunks.append(remaining_text)
            break
        
        # Recherche de points de coupure optimaux
        cut_point = max_chunk_size
        
        # Préférer les points après ponctuation
        for i in range(max_chunk_size, max(max_chunk_size // 2, 0), -1):
            if i < len(remaining_text) and remaining_text[i] in '.!?':
                cut_point = i + 1
                break
        
        # Sinon, couper aux espaces
        if cut_point == max_chunk_size:
            while cut_point > 0 and remaining_text[cut_point] != ' ':
                cut_point -= 1
        
        # Fallback: couper à la taille max
        if cut_point == 0:
            cut_point = min(max_chunk_size, len(remaining_text))
        
        chunk = remaining_text[:cut_point].strip()
        if chunk:
            chunks.append(chunk)
        
        remaining_text = remaining_text[cut_point:].strip()
    
    return [chunk for chunk in chunks if chunk.strip()]

# Détection de langue (votre logique préservée)
def guess_lang_from_text(text: str) -> Optional[str]:
    """Détection automatique de la langue - Version améliorée"""
    try:
        detected = detect(text)
        lang_mapping = {
            'de': 'de', 'ger': 'de',
            'fr': 'fr', 'fra': 'fr', 
            'en': 'en', 'eng': 'en',
            'es': 'es', 'spa': 'es',
            'it': 'it', 'ita': 'it',
            'nl': 'nl', 'nld': 'nl',
            'pl': 'pl', 'pol': 'pl',
            'pt': 'pt', 'por': 'pt'
        }
        return lang_mapping.get(detected, detected)
    except Exception:
        # Fallback par mots-clés amélioré
        text_lower = text.lower()
        
        # Patterns linguistiques spécifiques
        lang_patterns = {
            'fr': ['poulet', 'aviculture', 'qu\'est', 'comment', 'quelle', 'combien'],
            'en': ['chicken', 'poultry', 'what', 'how', 'which', 'where'],
            'es': ['pollo', 'avicultura', 'qué', 'cómo', 'cuál', 'dónde'],
            'de': ['huhn', 'geflügel', 'was', 'wie', 'welche', 'wo']
        }
        
        for lang, patterns in lang_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return lang
        
        return 'fr'  # Défaut français

# Générateur de prompts spécialisés amélioré (préservé)
async def generate_specialized_response(query: str, language: str = "fr", intent_result = None) -> str:
    """Génération de réponse avec prompts spécialisés selon l'intention"""
    
    # Prompt de base selon la langue
    system_prompts = {
        'fr': "Tu es un assistant spécialisé en aviculture. Réponds uniquement aux questions dans ce domaine avec précision et expertise.",
        'en': "You are a poultry specialist assistant. Only answer questions in this domain with precision and expertise.",
        'es': "Eres un asistente especializado en avicultura. Solo responde preguntas de este dominio con precisión y experiencia.",
        'de': "Du bist ein auf Geflügelhaltung spezialisierter Assistent. Beantworte nur Fragen in diesem Bereich mit Präzision und Expertise."
    }
    
    system_message = system_prompts.get(language, system_prompts['fr'])
    
    # Enrichissement du prompt selon l'intention détectée
    if intent_result and hasattr(intent_result, 'intent_type'):
        if hasattr(intent_result.intent_type, 'value'):
            intent_value = intent_result.intent_type.value
        else:
            intent_value = str(intent_result.intent_type)
        
        if "metric" in intent_value:
            system_message += " Fournis des données précises avec les unités appropriées et les références standards de l'industrie."
        elif "environment" in intent_value:
            system_message += " Concentre-toi sur les paramètres techniques d'ambiance et de climat d'élevage."
        elif "diagnosis" in intent_value:
            system_message += " Utilise une approche méthodique de diagnostic différentiel et considère l'épidémiologie."
        elif "economics" in intent_value:
            system_message += " Fournis des analyses de coûts détaillées et des calculs de rentabilité."
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ],
            max_tokens=600,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erreur génération spécialisée: {e}")
        return "Désolé, une erreur est survenue lors de la génération de la réponse."

# Initialisation RAG - MODIFIÉ pour RAG Enhanced
async def initialize_rag_engines():
    """Initialise les engines RAG (Enhanced + optionnel Agent)"""
    global rag_engine_enhanced, agent_rag_engine
    
    if rag_engine_enhanced is not None:
        return rag_engine_enhanced
    
    # 1. Initialiser RAG Enhanced (prioritaire)
    if PREFER_ENHANCED_RAG:
        try:
            logger.info("🚀 Initialisation RAG Engine Enhanced...")
            
            # Créer client OpenAI async pour RAG Enhanced
            from openai import AsyncOpenAI
            async_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            
            rag_engine_enhanced = await create_rag_engine(async_openai_client)
            
            status = rag_engine_enhanced.get_status()
            optimizations = status.get("optimizations", {})
            
            logger.info(f"✅ RAG Enhanced initialisé:")
            logger.info(f"   - Cache: {optimizations.get('cache_enabled', False)}")
            logger.info(f"   - Recherche hybride: {optimizations.get('hybrid_search_enabled', False)}")
            logger.info(f"   - Enrichissement entités: {optimizations.get('entity_enrichment_enabled', False)}")
            logger.info(f"   - Guardrails: {optimizations.get('guardrails_level', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation RAG Enhanced: {e}")
            rag_engine_enhanced = None
    
    # 2. CORRECTION POINT 2 : Référence OpenAI correcte pour Agent RAG
    if USE_AGENT_RAG and AGENT_RAG_AVAILABLE:
        try:
            logger.info("🤖 Initialisation Agent RAG...")
            # CORRECTION : Utiliser async_openai_client au lieu de openai_client
            from openai import AsyncOpenAI
            async_openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            agent_rag_engine = await create_agent_rag_engine(async_openai_client)
            agent_status = agent_rag_engine.get_agent_status()
            logger.info(f"✅ Agent RAG initialisé: {agent_status.get('agent_features', [])}")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Agent RAG: {e}")
            agent_rag_engine = None
    
    return rag_engine_enhanced

# Fonctions de streaming spécialisées - ADAPTÉES pour RAG Enhanced
async def _stream_enhanced_rag_response(rag_result: RAGResult, language: str, tenant_id: str):
    """Streaming pour réponses RAG Enhanced avec métadonnées"""
    async def generate():
        try:
            # Informations sur les optimisations utilisées
            metadata = rag_result.metadata or {}
            optimizations = metadata.get("optimizations_enabled", {})
            
            yield sse_event({
                "type": "enhanced_start", 
                "source": rag_result.source.value if rag_result.source else "unknown",
                "optimizations": optimizations,
                "confidence": rag_result.confidence,
                "processing_time": rag_result.processing_time
            })
            
            # Optionnel: Montrer les optimisations utilisées
            if optimizations.get("redis_cache") or optimizations.get("hybrid_search"):
                yield sse_event({
                    "type": "optimization_info",
                    "cache_used": optimizations.get("redis_cache", False),
                    "hybrid_search": optimizations.get("hybrid_search", False),
                    "entity_enrichment": optimizations.get("entity_enrichment", False)
                })
            
            # Stream de la réponse
            if rag_result.answer:
                chunks = smart_chunk_text(rag_result.answer, STREAM_CHUNK_LEN)
                
                for i, chunk in enumerate(chunks):
                    yield sse_event({
                        "type": "chunk", 
                        "content": chunk,
                        "confidence": rag_result.confidence,
                        "chunk_index": i
                    })
                    await asyncio.sleep(0.01)  # Smooth streaming
            
            # Informations finales
            yield sse_event({
                "type": "enhanced_end",
                "total_time": rag_result.processing_time,
                "confidence": rag_result.confidence,
                "documents_used": len(rag_result.context_docs),
                "verification_status": rag_result.verification_status,
                "source": rag_result.source.value if rag_result.source else "unknown"
            })
            
            # Enregistrer dans la mémoire
            if rag_result.answer:
                add_to_conversation_memory(tenant_id, "question", rag_result.answer, "rag_enhanced")
            
        except Exception as e:
            logger.error(f"Erreur streaming enhanced RAG: {e}")
            yield sse_event({"type": "error", "message": str(e)})
    
    return StreamingResponse(generate(), media_type="text/plain")

async def _stream_agent_response(agent_result, language: str, tenant_id: str):
    """Streaming pour réponses Agent RAG (préservé)"""
    async def generate():
        try:
            yield sse_event({
                "type": "agent_start", 
                "complexity": getattr(agent_result, 'complexity', 'unknown'),
                "decomposition_used": getattr(agent_result, 'decomposition_used', False),
                "sub_queries_count": len(getattr(agent_result, 'sub_results', []))
            })
            
            # Optionnel: Montrer les décisions de l'agent
            if hasattr(agent_result, 'agent_decisions') and agent_result.agent_decisions:
                yield sse_event({
                    "type": "agent_thinking",
                    "decisions": agent_result.agent_decisions[:3]  # Premières 3 décisions
                })
            
            # Stream de la réponse finale
            answer = getattr(agent_result, 'final_answer', '')
            if answer:
                chunks = smart_chunk_text(answer, STREAM_CHUNK_LEN)
                
                for i, chunk in enumerate(chunks):
                    yield sse_event({
                        "type": "chunk", 
                        "content": chunk,
                        "confidence": getattr(agent_result, 'confidence', 0.5),
                        "chunk_index": i
                    })
                    await asyncio.sleep(0.02)  # Slightly slower for complex responses
            
            yield sse_event({
                "type": "agent_end",
                "total_time": getattr(agent_result, 'processing_time', 0),
                "confidence": getattr(agent_result, 'confidence', 0.5),
                "synthesis_method": getattr(agent_result, 'synthesis_method', 'unknown'),
                "sources_used": len(getattr(agent_result, 'sub_results', []))
            })
            
            # Enregistrer dans la mémoire
            if answer:
                add_to_conversation_memory(tenant_id, "question", answer, "agent_rag")
            
        except Exception as e:
            logger.error(f"Erreur streaming agent: {e}")
            yield sse_event({"type": "error", "message": str(e)})
    
    return StreamingResponse(generate(), media_type="text/plain")

# Gestionnaires de cycle de vie - MODIFIÉS
async def startup_event():
    """Démarrage de l'application amélioré"""
    logger.info("🚀 Démarrage Intelia Expert - Version RAG Enhanced")
    await initialize_rag_engines()

async def shutdown_event():
    """Arrêt de l'application amélioré"""
    global rag_engine_enhanced, agent_rag_engine
    try:
        logger.info("🔄 Arrêt de l'application...")
        
        if rag_engine_enhanced and hasattr(rag_engine_enhanced, 'cleanup'):
            await rag_engine_enhanced.cleanup()
        
        if agent_rag_engine and hasattr(agent_rag_engine, 'cleanup'):
            await agent_rag_engine.cleanup()
        
        rag_engine_enhanced = None
        agent_rag_engine = None
        conversation_memory.clear()
        
        logger.info("🛑 Arrêt propre terminé")
    except Exception as e:
        logger.error(f"⚠️ Erreur lors du nettoyage: {e}")

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()

app = FastAPI(
    title="Intelia Expert - RAG Enhanced Backend", 
    debug=False, 
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

router = APIRouter()

# Routes améliorées
@router.get("/health")
def health():
    """Health check avec status RAG Enhanced détaillé"""
    global rag_engine_enhanced, agent_rag_engine
    
    memory_stats = {
        "total_tenants": len(conversation_memory),
        "total_exchanges": sum(len(v["data"]) for v in conversation_memory.values()),
        "memory_usage_mb": len(str(conversation_memory)) / (1024 * 1024)
    }
    
    health_data = {
        "ok": True,
        "version": "rag_enhanced_v2.0",
        "memory_stats": memory_stats,
        "performance_metrics": metrics_collector.get_metrics()
    }
    
    # Status RAG Enhanced
    if rag_engine_enhanced:
        try:
            rag_status = rag_engine_enhanced.get_status()
            health_data.update({
                "rag_enhanced_enabled": True,
                "rag_enhanced_status": rag_status,
                "optimizations": rag_status.get("optimizations", {}),
                "components": rag_status.get("components", {}),
                "degraded_mode": rag_status.get("degraded_mode", False)
            })
        except Exception as e:
            health_data.update({
                "rag_enhanced_enabled": False,
                "rag_enhanced_error": str(e)
            })
    else:
        health_data.update({
            "rag_enhanced_enabled": False,
            "rag_enhanced_status": "not_initialized"
        })
    
    # Status Agent RAG (optionnel)
    if agent_rag_engine:
        try:
            agent_status = agent_rag_engine.get_agent_status()
            health_data.update({
                "agent_rag_enabled": True,
                "agent_rag_status": agent_status
            })
        except Exception as e:
            health_data.update({
                "agent_rag_enabled": False,
                "agent_rag_error": str(e)
            })
    else:
        health_data["agent_rag_enabled"] = False
    
    return health_data

# Route CHAT principale - MODIFICATION MAJEURE POUR RAG ENHANCED
@router.post(f"{BASE_PATH}/chat")
async def chat(request: Request):
    """Chat endpoint avec RAG Enhanced intelligent"""
    global rag_engine_enhanced, agent_rag_engine
    
    if not rag_engine_enhanced:
        raise HTTPException(status_code=503, detail="RAG Engine Enhanced non disponible")
    
    try:
        body = await request.json()
        message = body.get("message", "").strip()
        language = body.get("language", "").strip() or guess_lang_from_text(message)
        tenant_id = body.get("tenant_id", str(uuid.uuid4())[:8])
        
        if not message:
            raise HTTPException(status_code=400, detail="Message vide")
        
        if len(message) > MAX_REQUEST_SIZE:
            raise HTTPException(status_code=413, detail=f"Message trop long (max {MAX_REQUEST_SIZE})")
        
        # Vérification du message hors-domaine d'abord
        if len(message.split()) < 3:  # Messages trop courts
            out_of_domain_msg = get_out_of_domain_message(language)
            
            async def simple_response():
                yield sse_event({"type": "start", "reason": "too_short"})
                yield sse_event({"type": "chunk", "content": out_of_domain_msg})
                yield sse_event({"type": "end", "confidence": 0.9})
            
            return StreamingResponse(simple_response(), media_type="text/plain")
        
        # Stratégie de traitement intelligente
        # 1. Essayer Agent RAG si disponible et activé
        if USE_AGENT_RAG and agent_rag_engine and hasattr(agent_rag_engine, 'process_query_agent'):
            try:
                agent_result = await agent_rag_engine.process_query_agent(message, language, tenant_id)
                metrics_collector.record_query(agent_result, "agent_rag")
                return await _stream_agent_response(agent_result, language, tenant_id)
            except Exception as e:
                logger.warning(f"Erreur Agent RAG, fallback vers RAG Enhanced: {e}")
        
        # 2. Utiliser RAG Enhanced (principal)
        rag_result = await rag_engine_enhanced.process_query(message, language, tenant_id)
        metrics_collector.record_query(rag_result, "rag_enhanced")
        
        # Traitement selon le type de résultat
        if rag_result.source == RAGSource.OOD_FILTERED:
            # Message hors domaine
            async def ood_response():
                yield sse_event({"type": "start", "reason": "out_of_domain"})
                yield sse_event({"type": "chunk", "content": rag_result.answer})
                yield sse_event({"type": "end", "confidence": rag_result.confidence})
            
            return StreamingResponse(ood_response(), media_type="text/plain")
        
        elif rag_result.source == RAGSource.FALLBACK_NEEDED:
            # Fallback vers génération spécialisée
            try:
                specialized_answer = await generate_specialized_response(message, language, rag_result.intent_result)
                
                async def fallback_response():
                    yield sse_event({"type": "start", "reason": "fallback_specialized"})
                    chunks = smart_chunk_text(specialized_answer, STREAM_CHUNK_LEN)
                    for chunk in chunks:
                        yield sse_event({"type": "chunk", "content": chunk})
                        await asyncio.sleep(0.05)
                    yield sse_event({"type": "end", "confidence": 0.6})
                
                add_to_conversation_memory(tenant_id, message, specialized_answer, "specialized_fallback")
                return StreamingResponse(fallback_response(), media_type="text/plain")
                
            except Exception as e:
                logger.error(f"Erreur fallback spécialisé: {e}")
                out_of_domain_msg = get_out_of_domain_message(language)
                
                async def error_response():
                    yield sse_event({"type": "start", "reason": "error_fallback"})
                    yield sse_event({"type": "chunk", "content": out_of_domain_msg})
                    yield sse_event({"type": "end", "confidence": 0.3})
                
                return StreamingResponse(error_response(), media_type="text/plain")
        
        elif rag_result.source == RAGSource.ERROR:
            raise HTTPException(status_code=500, detail="Erreur traitement RAG Enhanced")
        
        else:
            # Réponse RAG Enhanced normale
            return await _stream_enhanced_rag_response(rag_result, language, tenant_id)
            
    except Exception as e:
        logger.error(f"Erreur chat endpoint: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur traitement: {str(e)}"}
        )

# Route OOD pour compatibilité (préservée)
@router.post(f"{BASE_PATH}/ood")
async def ood_endpoint(request: Request):
    """Point de terminaison pour messages hors domaine"""
    try:
        body = await request.json()
        language = body.get("language", "fr")
        message = get_out_of_domain_message(language)
        
        async def ood_response():
            yield sse_event({"type": "start", "reason": "out_of_domain"})
            
            chunks = smart_chunk_text(message, STREAM_CHUNK_LEN)
            for chunk in chunks:
                yield sse_event({"type": "chunk", "content": chunk})
                await asyncio.sleep(0.05)
            
            yield sse_event({"type": "end", "confidence": 1.0})
        
        return StreamingResponse(ood_response(), media_type="text/plain")
        
    except Exception as e:
        logger.error(f"Erreur OOD endpoint: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Nouvelles routes pour RAG Enhanced
@router.get(f"{BASE_PATH}/rag/status")
async def rag_status():
    """Status détaillé du RAG Enhanced"""
    if not rag_engine_enhanced:
        return {"error": "RAG Engine Enhanced non initialisé"}
    
    try:
        return rag_engine_enhanced.get_status()
    except Exception as e:
        return {"error": str(e)}

@router.post(f"{BASE_PATH}/rag/cache/clear")
async def clear_cache():
    """Vider le cache Redis (utile pour développement)"""
    if not rag_engine_enhanced or not hasattr(rag_engine_enhanced, 'cache_manager'):
        raise HTTPException(status_code=404, detail="Cache non disponible")
    
    try:
        cache_manager = rag_engine_enhanced.cache_manager
        if cache_manager and hasattr(cache_manager, 'invalidate_pattern'):
            await cache_manager.invalidate_pattern("*")
            return {"status": "cache_cleared"}
        else:
            raise HTTPException(status_code=404, detail="Cache manager non configuré")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(f"{BASE_PATH}/metrics")
async def get_metrics():
    """Endpoint pour récupérer les métriques de performance"""
    try:
        return {
            "application_metrics": metrics_collector.get_metrics(),
            "system_metrics": {
                "conversation_memory": {
                    "tenants": len(conversation_memory),
                    "total_exchanges": sum(len(v["data"]) for v in conversation_memory.values())
                }
            },
            "rag_enhanced_metrics": rag_engine_enhanced.get_status().get("metrics", {}) if rag_engine_enhanced else {}
        }
    except Exception as e:
        return {"error": str(e)}

# Inclure le router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)