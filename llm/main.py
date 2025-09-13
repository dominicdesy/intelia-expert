# -*- coding: utf-8 -*-
"""
main.py - Intelia Expert Backend amélioré avec Agent RAG
Version optimisée préservant votre intelligence métier avec Agent RAG intelligent
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

# Import de votre RAG Engine amélioré
from rag_engine import create_rag_engine, process_question_with_rag, RAGSource, RAGResult

# Import de l'Agent RAG (nouveau)
try:
    from agent_rag_extension import InteliaAgentRAG, create_agent_rag_engine, AgentResult, QueryComplexity
    AGENT_RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Agent RAG non disponible: {e}")
    AGENT_RAG_AVAILABLE = False
    # Fallback types
    class QueryComplexity:
        SIMPLE = "simple"
    class AgentResult:
        pass

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DetectorFactory.seed = 0
load_dotenv()

# Variables globales - modification pour Agent RAG
agent_rag_engine = None  # Remplace rag_engine

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

# Validation configuration
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")

logger.info(f"Mode Agent RAG Enhanced: Intelligence multi-requêtes avec synthèse")

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

def add_to_conversation_memory(tenant_id: str, question: str, answer: str):
    """Ajoute un échange à la mémoire de conversation - Version améliorée"""
    tenant_data = conversation_memory.get(tenant_id, {"data": []})
    history = tenant_data["data"]
    
    history.append({
        "question": question, 
        "answer": answer, 
        "timestamp": time.time(),
        "answer_source": "agent_rag"  # Traçabilité améliorée
    })
    
    # Limiter selon la configuration
    if len(history) > MAX_CONVERSATION_CONTEXT:
        history = history[-MAX_CONVERSATION_CONTEXT:]
    
    conversation_memory.set(tenant_id, history)
    conversation_memory.update_last_query(tenant_id, question)

# Classe de métriques pour monitoring amélioré
class MetricsCollector:
    """Collecteur de métriques pour monitoring des performances"""
    
    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "agent_queries": 0,
            "simple_queries": 0,
            "complex_queries": 0,
            "rag_queries": 0,
            "ood_filtered": 0,
            "fallback_queries": 0,
            "verified_responses": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0,
            "synthesis_success_rate": 0.0
        }
        self.recent_processing_times = []
        self.recent_confidences = []
        self.max_recent_samples = 100
    
    def record_query(self, result):
        """Enregistre les métriques d'une requête - compatible Agent et RAG"""
        if not ENABLE_METRICS_LOGGING:
            return
        
        self.metrics["total_queries"] += 1
        
        # Gestion Agent Result
        if isinstance(result, AgentResult):
            self.metrics["agent_queries"] += 1
            if result.complexity == QueryComplexity.SIMPLE:
                self.metrics["simple_queries"] += 1
            else:
                self.metrics["complex_queries"] += 1
                
            processing_time = result.processing_time
            confidence = result.confidence
            
        # Gestion RAG Result standard
        elif hasattr(result, 'source') and hasattr(result, 'confidence'):
            if result.source == RAGSource.RAG_KNOWLEDGE:
                self.metrics["rag_queries"] += 1
            elif result.source == RAGSource.RAG_VERIFIED:
                self.metrics["rag_queries"] += 1
                self.metrics["verified_responses"] += 1
            elif result.source == RAGSource.OOD_FILTERED:
                self.metrics["ood_filtered"] += 1
            else:
                self.metrics["fallback_queries"] += 1
                
            processing_time = result.processing_time
            confidence = result.confidence
        else:
            return  # Format non reconnu
        
        # Temps de traitement
        if processing_time > 0:
            self.recent_processing_times.append(processing_time)
            if len(self.recent_processing_times) > self.max_recent_samples:
                self.recent_processing_times.pop(0)
            
            self.metrics["avg_processing_time"] = (
                sum(self.recent_processing_times) / len(self.recent_processing_times)
            )
        
        # Confiance
        if confidence > 0:
            self.recent_confidences.append(confidence)
            if len(self.recent_confidences) > self.max_recent_samples:
                self.recent_confidences.pop(0)
            
            self.metrics["avg_confidence"] = (
                sum(self.recent_confidences) / len(self.recent_confidences)
            )
    
    def get_metrics(self) -> Dict:
        """Retourne les métriques actuelles"""
        return {
            **self.metrics,
            "success_rate": (
                (self.metrics["rag_queries"] + self.metrics["verified_responses"] + self.metrics["agent_queries"]) / 
                max(1, self.metrics["total_queries"])
            ),
            "agent_usage_rate": self.metrics["agent_queries"] / max(1, self.metrics["total_queries"]),
            "complexity_rate": self.metrics["complex_queries"] / max(1, self.metrics["agent_queries"]) if self.metrics["agent_queries"] > 0 else 0.0
        }

metrics_collector = MetricsCollector()

# Wrapper de compatibilité pour RAG standard (nouveau)
class AgentCompatibilityWrapper:
    """Wrapper pour compatibilité avec RAG standard"""
    def __init__(self, rag_engine):
        self.rag_engine = rag_engine
        self.is_agent = False
    
    async def process_query_agent(self, query: str, language: str = "fr", tenant_id: str = "") -> AgentResult:
        """Simule l'interface agent avec RAG standard"""
        rag_result = await self.rag_engine.process_query(query, language, tenant_id)
        
        # Créer un AgentResult simple pour compatibilité
        agent_result = type('AgentResult', (), {
            'final_answer': rag_result.answer or "Aucune réponse trouvée",
            'confidence': rag_result.confidence,
            'sub_results': [rag_result],
            'synthesis_method': "standard_rag_fallback",
            'processing_time': rag_result.processing_time,
            'complexity': QueryComplexity.SIMPLE,
            'decomposition_used': False,
            'agent_decisions': ["Fallback vers RAG standard"]
        })()
        
        return agent_result
    
    def get_agent_status(self):
        base_status = self.rag_engine.get_status() if hasattr(self.rag_engine, 'get_status') else {}
        return {**base_status, "agent_enabled": False, "fallback_mode": True}
    
    # Déléguer les autres méthodes
    async def process_query(self, *args, **kwargs):
        return await self.rag_engine.process_query(*args, **kwargs)
    
    def get_status(self):
        return self.rag_engine.get_status() if hasattr(self.rag_engine, 'get_status') else {}
    
    async def cleanup(self):
        if hasattr(self.rag_engine, 'cleanup'):
            await self.rag_engine.cleanup()

# Helpers de streaming améliorés
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

# Initialisation RAG - MODIFICATION MAJEURE POUR AGENT RAG
async def initialize_rag_engine():
    """Initialise le RAG engine avec Agent RAG ou fallback standard"""
    global agent_rag_engine
    if agent_rag_engine is not None:
        return agent_rag_engine
    
    # Essayer d'initialiser Agent RAG d'abord
    if AGENT_RAG_AVAILABLE:
        try:
            logger.info("Initialisation de l'Agent RAG Enhanced...")
            agent_rag_engine = await create_agent_rag_engine(openai_client)
            agent_status = agent_rag_engine.get_agent_status()
            logger.info(f"Agent RAG Enhanced initialisé: {agent_status.get('agent_features', [])}")
            return agent_rag_engine
        except Exception as e:
            logger.error(f"Erreur initialisation Agent RAG: {e}")
            logger.info("Tentative de fallback vers RAG standard...")
    
    # Fallback vers RAG standard
    try:
        logger.info("Initialisation du RAG Engine standard...")
        standard_rag = await create_rag_engine(openai_client)
        # Wrapper pour compatibilité
        agent_rag_engine = AgentCompatibilityWrapper(standard_rag)
        logger.info("RAG standard initialisé avec wrapper de compatibilité")
        return agent_rag_engine
    except Exception as e:
        logger.error(f"Erreur initialisation RAG standard: {e}")
        return None

# Fonctions de streaming spécialisées (nouvelles)
async def _stream_simple_response(agent_result, language: str, tenant_id: str):
    """Streaming pour réponses simples"""
    async def generate():
        try:
            yield sse_event({"type": "start", "complexity": "simple"})
            
            # Chunking intelligent de la réponse
            chunks = smart_chunk_text(agent_result.final_answer, STREAM_CHUNK_LEN)
            
            for chunk in chunks:
                yield sse_event({
                    "type": "chunk", 
                    "content": chunk,
                    "confidence": agent_result.confidence
                })
                await asyncio.sleep(0.01)  # Smooth streaming
            
            yield sse_event({
                "type": "end",
                "total_time": agent_result.processing_time,
                "confidence": agent_result.confidence
            })
            
            # Enregistrer dans la mémoire
            add_to_conversation_memory(tenant_id, "question", agent_result.final_answer)
            
        except Exception as e:
            logger.error(f"Erreur streaming simple: {e}")
            yield sse_event({"type": "error", "message": str(e)})
    
    return StreamingResponse(generate(), media_type="text/plain")

async def _stream_agent_response(agent_result, language: str, tenant_id: str):
    """Streaming pour réponses complexes avec détails agent"""
    async def generate():
        try:
            yield sse_event({
                "type": "agent_start", 
                "complexity": agent_result.complexity,
                "decomposition_used": agent_result.decomposition_used,
                "sub_queries_count": len(agent_result.sub_results)
            })
            
            # Optionnel: Montrer les décisions de l'agent
            if hasattr(agent_result, 'agent_decisions') and agent_result.agent_decisions:
                yield sse_event({
                    "type": "agent_thinking",
                    "decisions": agent_result.agent_decisions[:3]  # Premières 3 décisions
                })
            
            # Stream de la réponse finale
            chunks = smart_chunk_text(agent_result.final_answer, STREAM_CHUNK_LEN)
            
            for i, chunk in enumerate(chunks):
                yield sse_event({
                    "type": "chunk", 
                    "content": chunk,
                    "confidence": agent_result.confidence,
                    "chunk_index": i
                })
                await asyncio.sleep(0.02)  # Slightly slower for complex responses
            
            yield sse_event({
                "type": "agent_end",
                "total_time": agent_result.processing_time,
                "confidence": agent_result.confidence,
                "synthesis_method": getattr(agent_result, 'synthesis_method', 'unknown'),
                "sources_used": len(agent_result.sub_results)
            })
            
            # Enregistrer dans la mémoire
            add_to_conversation_memory(tenant_id, "question", agent_result.final_answer)
            
        except Exception as e:
            logger.error(f"Erreur streaming agent: {e}")
            yield sse_event({"type": "error", "message": str(e)})
    
    return StreamingResponse(generate(), media_type="text/plain")

# Gestionnaires de cycle de vie - MODIFIÉS
async def startup_event():
    """Démarrage de l'application amélioré"""
    logger.info("🚀 Démarrage Intelia Expert - Version Enhanced Agent RAG")
    await initialize_rag_engine()

async def shutdown_event():
    """Arrêt de l'application amélioré"""
    global agent_rag_engine
    try:
        logger.info("🔄 Arrêt de l'application...")
        if agent_rag_engine and hasattr(agent_rag_engine, 'cleanup'):
            await agent_rag_engine.cleanup()
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
    title="Intelia Expert - Agent RAG Backend", 
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
    """Health check avec status Agent RAG détaillé"""
    global agent_rag_engine
    
    memory_stats = {
        "total_tenants": len(conversation_memory),
        "total_exchanges": sum(len(v["data"]) for v in conversation_memory.values()),
        "memory_usage_mb": len(str(conversation_memory)) / (1024 * 1024)
    }
    
    if agent_rag_engine:
        agent_status = agent_rag_engine.get_agent_status()
        return {
            "ok": True,
            "version": "enhanced_agent_rag_v3.0",
            "agent_enabled": agent_status.get("agent_enabled", False),
            "fallback_mode": agent_status.get("fallback_mode", False),
            "rag_status": agent_status,
            "memory_stats": memory_stats,
            "agent_features": agent_status.get("agent_features", []),
            "agent_stats": agent_status.get("agent_stats", {}),
            "performance_metrics": metrics_collector.get_metrics()
        }
    else:
        return {
            "ok": False,
            "version": "enhanced_agent_rag_v3.0",
            "error": "Agent RAG non initialisé",
            "memory_stats": memory_stats,
            "performance_metrics": metrics_collector.get_metrics()
        }

# Route CHAT principale - MODIFICATION MAJEURE
@router.post(f"{BASE_PATH}/chat")
async def chat(request: Request):
    """Chat endpoint avec Agent RAG intelligent"""
    global agent_rag_engine
    
    if not agent_rag_engine:
        raise HTTPException(status_code=503, detail="RAG Engine non disponible")
    
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
        
        # Utiliser l'Agent RAG si disponible
        if hasattr(agent_rag_engine, 'process_query_agent'):
            agent_result = await agent_rag_engine.process_query_agent(message, language, tenant_id)
            
            # Enregistrer les métriques
            metrics_collector.record_query(agent_result)
            
            # Traitement selon le type de complexité
            if hasattr(agent_result, 'complexity') and agent_result.complexity == QueryComplexity.SIMPLE:
                return await _stream_simple_response(agent_result, language, tenant_id)
            else:
                return await _stream_agent_response(agent_result, language, tenant_id)
        else:
            # Fallback vers traitement standard si pas d'agent
            rag_result = await agent_rag_engine.process_query(message, language, tenant_id)
            
            # Enregistrer les métriques
            metrics_collector.record_query(rag_result)
            
            # Créer un AgentResult simulé pour compatibilité
            simulated_agent_result = type('AgentResult', (), {
                'final_answer': rag_result.answer or get_out_of_domain_message(language),
                'confidence': rag_result.confidence,
                'processing_time': rag_result.processing_time,
                'complexity': QueryComplexity.SIMPLE
            })()
            
            return await _stream_simple_response(simulated_agent_result, language, tenant_id)
            
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

# Inclure le router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)