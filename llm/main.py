# -*- coding: utf-8 -*-
"""
main.py - Intelia Expert Backend avec RAG Enhanced + Cache Sémantique Intelligent
Version Enhanced intégrant les aliases d'intents.json pour cache sémantique optimisé
NOUVELLES FONCTIONNALITÉS:
- Cache sémantique basé sur aliases métier
- Debug tools intégrés
- Métriques de performance étendues
- Harmonisation OpenAI Async/Sync
- OPTIMISATIONS v2.3: Initialisation Redis asynchrone, détection langue améliorée, monitoring enrichi
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
from openai import OpenAI, AsyncOpenAI
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
# MODIFIÉ: Augmentation du contexte de conversation
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "6"))  # 3 → 6 pour meilleure désambiguïsation

# Nouveaux paramètres RAG Enhanced
USE_AGENT_RAG = os.getenv("USE_AGENT_RAG", "false").lower() == "true"  # Désactivé par défaut
PREFER_ENHANCED_RAG = os.getenv("PREFER_ENHANCED_RAG", "true").lower() == "true"

# NOUVEAU: Paramètres cache sémantique
ENABLE_SEMANTIC_DEBUG = os.getenv("ENABLE_SEMANTIC_DEBUG", "true").lower() == "true"

# NOUVEAU: Seuil de détection de langue court
LANG_DETECTION_MIN_LENGTH = int(os.getenv("LANG_DETECTION_MIN_LENGTH", "20"))

# Validation configuration
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")

logger.info(f"Mode RAG Enhanced: Cache Sémantique Intelligent + Aliases + Debug Tools v2.3")

# Helpers OpenAI harmonisés
def get_openai_sync() -> OpenAI:
    """Factory pour client OpenAI synchrone"""
    return OpenAI(api_key=OPENAI_API_KEY)

def get_openai_async() -> AsyncOpenAI:
    """Factory pour client OpenAI asynchrone"""
    return AsyncOpenAI(api_key=OPENAI_API_KEY)

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

# OpenAI clients harmonisés
try:
    openai_client_sync = get_openai_sync()
    openai_client_async = get_openai_async()
    logger.info("Clients OpenAI (sync + async) initialisés")
except Exception as e:
    logger.error(f"Erreur initialisation clients OpenAI: {e}")
    raise RuntimeError(f"Impossible d'initialiser les clients OpenAI: {e}")

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

# Classe de métriques pour monitoring amélioré - ÉTENDUE pour Cache Sémantique
class MetricsCollector:
    """Collecteur de métriques pour monitoring des performances - Version Enhanced v2.3"""
    
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
            "semantic_cache_hits": 0,
            "fallback_cache_hits": 0,
            "hybrid_searches": 0,
            "guardrail_violations": 0,
            "api_corrections": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0,
        }
        self.recent_processing_times = []
        self.recent_confidences = []
        # NOUVEAU: Métriques de latence enrichies
        self.latency_percentiles = {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        self.max_recent_samples = 100
        # NOUVEAU: Stockage des temps de traitement endpoint
        self.endpoint_processing_times = []
    
    def record_query(self, result, source_type: str = "unknown", endpoint_time: float = 0.0):
        """Enregistre les métriques d'une requête - Version Enhanced avec cache sémantique"""
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
        
        # NOUVEAU: Métriques cache sémantique depuis RAG Enhanced
        if hasattr(result, 'metadata') and result.metadata:
            opt_stats = result.metadata.get("optimization_stats", {})
            self.metrics["cache_hits"] += opt_stats.get("cache_hits", 0)
            self.metrics["cache_misses"] += opt_stats.get("cache_misses", 0)
            self.metrics["semantic_cache_hits"] += opt_stats.get("semantic_cache_hits", 0)
            self.metrics["fallback_cache_hits"] += opt_stats.get("fallback_cache_hits", 0)
            self.metrics["hybrid_searches"] += opt_stats.get("hybrid_searches", 0)
            self.metrics["guardrail_violations"] += opt_stats.get("guardrail_violations", 0)
            self.metrics["api_corrections"] += opt_stats.get("api_corrections", 0)
        
        # NOUVEAU: Calcul des percentiles de latence
        processing_time = endpoint_time if endpoint_time > 0 else getattr(result, 'processing_time', 0)
        
        if processing_time > 0:
            self.recent_processing_times.append(processing_time)
            if len(self.recent_processing_times) > self.max_recent_samples:
                self.recent_processing_times.pop(0)
            
            # Calcul de la moyenne
            self.metrics["avg_processing_time"] = (
                sum(self.recent_processing_times) / len(self.recent_processing_times)
            )
            
            # Calcul des percentiles
            if len(self.recent_processing_times) >= 10:  # Minimum d'échantillons
                sorted_times = sorted(self.recent_processing_times)
                n = len(sorted_times)
                self.latency_percentiles["p50"] = sorted_times[int(n * 0.5)]
                self.latency_percentiles["p95"] = sorted_times[int(n * 0.95)]
                self.latency_percentiles["p99"] = sorted_times[int(n * 0.99)]
        
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
        """Retourne les métriques actuelles avec cache sémantique"""
        total_queries = max(1, self.metrics["total_queries"])
        total_cache_requests = max(1, self.metrics["cache_hits"] + self.metrics["cache_misses"])
        
        return {
            **self.metrics,
            "success_rate": (
                (self.metrics["rag_enhanced_queries"] + self.metrics["verified_responses"] + self.metrics["agent_queries"]) / total_queries
            ),
            "enhanced_rag_usage_rate": self.metrics["rag_enhanced_queries"] / total_queries,
            "agent_usage_rate": self.metrics["agent_queries"] / total_queries,
            "cache_hit_rate": self.metrics["cache_hits"] / total_cache_requests,
            "semantic_cache_hit_rate": self.metrics["semantic_cache_hits"] / total_cache_requests,
            "fallback_cache_hit_rate": self.metrics["fallback_cache_hits"] / total_cache_requests,
            "hybrid_search_rate": self.metrics["hybrid_searches"] / total_queries,
            "guardrail_violation_rate": self.metrics["guardrail_violations"] / total_queries,
            "api_correction_rate": self.metrics["api_corrections"] / total_queries,
            # NOUVEAU: Percentiles de latence
            "latency_percentiles": self.latency_percentiles
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

# MODIFIÉ: Détection de langue améliorée
def guess_lang_from_text(text: str) -> Optional[str]:
    """Détection automatique de la langue - Version améliorée v2.3"""
    try:
        # NOUVEAU: Pour les textes courts, utiliser détection légère d'abord
        if len(text) < LANG_DETECTION_MIN_LENGTH:
            text_lower = text.lower()
            
            # Patterns linguistiques spécifiques pour textes courts
            quick_patterns = {
                'fr': ['fcr', 'poulet', 'ross', 'cobb', 'jours', 'jour', 'kg', 'poids', 'conversion'],
                'en': ['fcr', 'chicken', 'broiler', 'days', 'day', 'weight', 'feed', 'conversion'],
                'es': ['fcr', 'pollo', 'días', 'día', 'peso', 'conversión', 'alimento'],
                'de': ['fcr', 'huhn', 'tage', 'tag', 'gewicht', 'futter', 'umwandlung']
            }
            
            for lang, patterns in quick_patterns.items():
                if any(pattern in text_lower for pattern in patterns):
                    logger.debug(f"Détection rapide: {lang} pour '{text[:20]}...'")
                    return lang
            
            # Fallback français pour les textes courts non reconnus
            logger.debug(f"Fallback FR pour texte court: '{text[:20]}...'")
            return 'fr'
        
        # Pour les textes plus longs, utiliser langdetect
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
        
        result = lang_mapping.get(detected, detected)
        logger.debug(f"Détection longue: {result} pour '{text[:30]}...'")
        return result
        
    except Exception as e:
        logger.debug(f"Erreur détection langue: {e}, fallback vers patterns")
        
        # Fallback par mots-clés améliorés
        text_lower = text.lower()
        
        # Patterns linguistiques spécifiques étendus
        lang_patterns = {
            'fr': ['poulet', 'aviculture', 'qu\'est', 'comment', 'quelle', 'combien', 'ross', 'cobb', 'fcr'],
            'en': ['chicken', 'poultry', 'what', 'how', 'which', 'where', 'broiler', 'ross', 'cobb'],
            'es': ['pollo', 'avicultura', 'qué', 'cómo', 'cuál', 'dónde', 'broiler', 'ross', 'cobb'],
            'de': ['huhn', 'geflügel', 'was', 'wie', 'welche', 'wo', 'masthuhn', 'ross', 'cobb']
        }
        
        for lang, patterns in lang_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                logger.debug(f"Fallback pattern: {lang} pour '{text[:20]}...'")
                return lang
        
        logger.debug(f"Fallback final FR pour '{text[:20]}...'")
        return 'fr'  # Défaut français

# Générateur de prompts spécialisés amélioré (HARMONISÉ avec AsyncOpenAI)
async def generate_specialized_response(query: str, language: str = "fr", intent_result = None) -> str:
    """Génération de réponse avec prompts spécialisés selon l'intention - Version Async"""
    
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
        # Utiliser le client async global
        response = await openai_client_async.chat.completions.create(
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

# MODIFIÉ: Initialisation RAG avec vérification Redis asynchrone
async def initialize_rag_engines():
    """Initialise les engines RAG (Enhanced + optionnel Agent) avec vérification Redis"""
    global rag_engine_enhanced, agent_rag_engine
    
    if rag_engine_enhanced is not None:
        return rag_engine_enhanced
    
    # 1. Initialiser RAG Enhanced (prioritaire)
    if PREFER_ENHANCED_RAG:
        try:
            logger.info("🚀 Initialisation RAG Engine Enhanced avec Cache Sémantique v2.3...")
            
            # Utiliser le client async pour RAG Enhanced
            rag_engine_enhanced = await create_rag_engine(openai_client_async)
            
            # NOUVEAU: Vérifier explicitement l'initialisation Redis
            if rag_engine_enhanced.cache_manager:
                try:
                    logger.info("🔄 Vérification initialisation Redis...")
                    await rag_engine_enhanced.cache_manager.initialize()
                    
                    # Test de connectivité Redis
                    test_result = await rag_engine_enhanced.cache_manager.get_response("test", "test", "fr")
                    logger.info("✅ Cache Redis initialisé et testé avec succès")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Problème initialisation Redis: {e}")
                    logger.info("🔄 Continuant en mode dégradé sans cache Redis")
            
            status = rag_engine_enhanced.get_status()
            optimizations = status.get("optimizations", {})
            
            logger.info(f"✅ RAG Enhanced initialisé:")
            logger.info(f"   - Cache Redis: {optimizations.get('external_cache_enabled', False)}")
            logger.info(f"   - Cache sémantique: {optimizations.get('semantic_cache_enabled', False)}")
            logger.info(f"   - Recherche hybride: {optimizations.get('hybrid_search_enabled', False)}")
            logger.info(f"   - Enrichissement entités: {optimizations.get('entity_enrichment_enabled', False)}")
            logger.info(f"   - Guardrails: {optimizations.get('guardrails_level', 'unknown')}")
            
            # NOUVEAU: Log des stats cache sémantique
            if rag_engine_enhanced.cache_manager:
                try:
                    cache_stats = await rag_engine_enhanced.cache_manager.get_cache_stats()
                    semantic_info = cache_stats.get("semantic_enhancements", {})
                    logger.info(f"   - Aliases chargés: {semantic_info.get('aliases_categories', 0)} catégories")
                    logger.info(f"   - Vocabulaire sémantique: {semantic_info.get('vocabulary_size', 0)} termes")
                except Exception as e:
                    logger.warning(f"Impossible de récupérer stats cache sémantique: {e}")
            
            # NOUVEAU: Log des capacités API détectées
            api_capabilities = status.get("api_capabilities", {})
            if api_capabilities.get("diagnosed", False):
                logger.info(f"   - API Weaviate diagnostiquée: {api_capabilities}")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation RAG Enhanced: {e}")
            rag_engine_enhanced = None
    
    # 2. Agent RAG optionnel
    if USE_AGENT_RAG and AGENT_RAG_AVAILABLE:
        try:
            logger.info("🤖 Initialisation Agent RAG...")
            agent_rag_engine = await create_agent_rag_engine(openai_client_async)
            agent_status = agent_rag_engine.get_agent_status()
            logger.info(f"✅ Agent RAG initialisé: {agent_status.get('agent_features', [])}")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Agent RAG: {e}")
            agent_rag_engine = None
    
    return rag_engine_enhanced

# Fonctions de streaming spécialisées - ADAPTÉES pour RAG Enhanced avec Cache Sémantique
async def _stream_enhanced_rag_response(rag_result: RAGResult, language: str, tenant_id: str):
    """Streaming pour réponses RAG Enhanced avec métriques cache sémantique"""
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
            
            # NOUVEAU: Afficher les métriques cache sémantique si disponibles et debug activé
            if ENABLE_SEMANTIC_DEBUG and optimizations.get("external_redis_cache") and metadata.get("cache_stats"):
                cache_stats = metadata["cache_stats"]
                yield sse_event({
                    "type": "cache_info",
                    "semantic_hits": cache_stats.get("semantic_hits", 0),
                    "exact_hits": cache_stats.get("exact_hits", 0),
                    "fallback_hits": cache_stats.get("fallback_hits", 0),
                    "keywords_extracted": cache_stats.get("keyword_extractions", 0)
                })
            
            # NOUVEAU: Afficher les capacités API si diagnostiquées
            api_capabilities = metadata.get("api_capabilities", {})
            if ENABLE_SEMANTIC_DEBUG and api_capabilities.get("diagnosed", False):
                yield sse_event({
                    "type": "api_capabilities",
                    "hybrid_with_vector": api_capabilities.get("hybrid_with_vector", False),
                    "hybrid_with_where": api_capabilities.get("hybrid_with_where", False),
                    "near_vector_format": api_capabilities.get("near_vector_format", "unknown"),
                    "corrections_applied": metadata.get("api_corrections_applied", False)
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
            
            # Informations finales avec cache sémantique
            final_data = {
                "type": "enhanced_end",
                "total_time": rag_result.processing_time,
                "confidence": rag_result.confidence,
                "documents_used": len(rag_result.context_docs),
                "verification_status": rag_result.verification_status,
                "source": rag_result.source.value if rag_result.source else "unknown"
            }
            
            # Ajouter stats sémantiques si disponibles
            if metadata.get("semantic_keywords_used"):
                final_data["semantic_keywords"] = metadata["semantic_keywords_used"]
            
            # NOUVEAU: Ajouter explain_score si disponible et debug activé
            if ENABLE_SEMANTIC_DEBUG and rag_result.context_docs:
                explain_scores = []
                for doc in rag_result.context_docs:
                    if isinstance(doc, dict) and doc.get("explain_score"):
                        explain_scores.append({
                            "title": doc.get("title", ""),
                            "explain_score": doc["explain_score"]
                        })
                if explain_scores:
                    final_data["explain_scores"] = explain_scores
            
            yield sse_event(final_data)
            
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
    logger.info("🚀 Démarrage Intelia Expert - Version RAG Enhanced avec Cache Sémantique v2.3")
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
        
        # Fermer les clients OpenAI
        if hasattr(openai_client_async, 'http_client'):
            await openai_client_async.http_client.aclose()
        
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
    title="Intelia Expert - RAG Enhanced Backend avec Cache Sémantique v2.3", 
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

# NOUVEAU: Route status enrichie
@router.get("/health")
async def health():
    """Health check avec status RAG Enhanced et Cache Sémantique détaillé - v2.3"""
    global rag_engine_enhanced, agent_rag_engine
    
    memory_stats = {
        "total_tenants": len(conversation_memory),
        "total_exchanges": sum(len(v["data"]) for v in conversation_memory.values()),
        "memory_usage_mb": len(str(conversation_memory)) / (1024 * 1024)
    }
    
    health_data = {
        "ok": True,
        "version": "rag_enhanced_semantic_v2.3_optimized",
        "memory_stats": memory_stats,
        "performance_metrics": metrics_collector.get_metrics()
    }
    
    # Status RAG Enhanced avec cache sémantique
    if rag_engine_enhanced:
        try:
            rag_status = rag_engine_enhanced.get_status()
            health_data.update({
                "rag_enhanced_enabled": True,
                "rag_enhanced_status": rag_status,
                "optimizations": rag_status.get("optimizations", {}),
                "components": rag_status.get("components", {}),
                "degraded_mode": rag_status.get("degraded_mode", False),
                "api_capabilities": rag_status.get("api_capabilities", {})  # NOUVEAU: capacités API
            })
            
            # NOUVEAU: Stats cache sémantique spécifiques
            if rag_engine_enhanced.cache_manager:
                try:
                    cache_stats = await rag_engine_enhanced.cache_manager.get_cache_stats()
                    health_data["semantic_cache_stats"] = cache_stats.get("semantic_enhancements", {})
                    
                    # NOUVEAU: Intent coverage stats
                    intent_stats = cache_stats.get("intent_coverage_stats", {})
                    if intent_stats:
                        health_data["intent_coverage_stats"] = intent_stats
                        
                except:
                    health_data["semantic_cache_stats"] = {"error": "unavailable"}
                    
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

# NOUVEAU: Route status riche exposée
@router.get("/status")
async def get_rich_status():
    """Status riche avec toutes les métriques et diagnostics"""
    global rag_engine_enhanced, agent_rag_engine
    
    status_data = {
        "timestamp": time.time(),
        "version": "rag_enhanced_semantic_v2.3_optimized",
        "components": {
            "rag_enhanced": rag_engine_enhanced is not None,
            "agent_rag": agent_rag_engine is not None,
            "openai_clients": True,
            "conversation_memory": True
        }
    }
    
    # Métriques de performance avec percentiles
    status_data["performance_metrics"] = metrics_collector.get_metrics()
    
    # Stats RAG Enhanced détaillées
    if rag_engine_enhanced:
        try:
            rag_status = rag_engine_enhanced.get_status()
            status_data["rag_status"] = rag_status
            
            # Capacités Weaviate
            api_capabilities = rag_status.get("api_capabilities", {})
            if api_capabilities.get("diagnosed", False):
                status_data["weaviate_capabilities"] = api_capabilities
            
            # Stats cache sémantique
            if rag_engine_enhanced.cache_manager:
                try:
                    cache_stats = await rag_engine_enhanced.cache_manager.get_cache_stats()
                    status_data["cache_stats"] = cache_stats
                    
                    # Intent coverage
                    intent_stats = cache_stats.get("intent_coverage_stats", {})
                    if intent_stats:
                        status_data["intent_coverage_stats"] = intent_stats
                        
                except Exception as e:
                    status_data["cache_error"] = str(e)
                    
        except Exception as e:
            status_data["rag_error"] = str(e)
    
    # API corrections counter
    if rag_engine_enhanced and hasattr(rag_engine_enhanced, 'get_api_corrections_count'):
        try:
            corrections_count = rag_engine_enhanced.get_api_corrections_count()
            status_data["api_corrections"] = corrections_count
        except:
            pass
    
    return status_data

# Route CHAT principale - MODIFICATION MAJEURE pour Cache Sémantique
@router.post(f"{BASE_PATH}/chat")
async def chat(request: Request):
    """Chat endpoint avec RAG Enhanced + Cache Sémantique Intelligent v2.3"""
    global rag_engine_enhanced, agent_rag_engine
    
    # Mesure du temps total endpoint
    total_start_time = time.time()
    
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
                
                # Enregistrer avec temps endpoint
                total_processing_time = time.time() - total_start_time
                metrics_collector.record_query(agent_result, "agent_rag", total_processing_time)
                
                return await _stream_agent_response(agent_result, language, tenant_id)
            except Exception as e:
                logger.warning(f"Erreur Agent RAG, fallback vers RAG Enhanced: {e}")
        
        # 2. Utiliser RAG Enhanced avec Cache Sémantique (principal)
        rag_result = await rag_engine_enhanced.process_query(message, language, tenant_id)
        
        # Calculer le temps total de l'endpoint
        total_processing_time = time.time() - total_start_time
        metrics_collector.record_query(rag_result, "rag_enhanced", total_processing_time)
        
        # Traitement selon le type de résultat
        if rag_result.source == RAGSource.OOD_FILTERED:
            # Message hors domaine
            async def ood_response():
                yield sse_event({"type": "start", "reason": "out_of_domain"})
                yield sse_event({"type": "chunk", "content": rag_result.answer})
                yield sse_event({"type": "end", "confidence": rag_result.confidence})
            
            return StreamingResponse(ood_response(), media_type="text/plain")
        
        elif rag_result.source == RAGSource.FALLBACK_NEEDED:
            # Fallback vers génération spécialisée (maintenant async)
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
            # Réponse RAG Enhanced normale avec cache sémantique
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

# Nouvelles routes pour RAG Enhanced avec Cache Sémantique
@router.get(f"{BASE_PATH}/rag/status")
async def rag_status():
    """Status détaillé du RAG Enhanced avec cache sémantique"""
    if not rag_engine_enhanced:
        return {"error": "RAG Engine Enhanced non initialisé"}
    
    try:
        status = rag_engine_enhanced.get_status()
        
        # Ajouter stats cache sémantique si disponible
        if rag_engine_enhanced.cache_manager:
            try:
                cache_stats = await rag_engine_enhanced.cache_manager.get_cache_stats()
                status["cache_stats"] = cache_stats
            except Exception as e:
                status["cache_stats_error"] = str(e)
        
        return status
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
            return {"status": "cache_cleared", "timestamp": time.time()}
        else:
            raise HTTPException(status_code=404, detail="Cache manager non configuré")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NOUVELLE ROUTE: Debug cache sémantique
@router.post(f"{BASE_PATH}/debug/semantic-cache")
async def debug_semantic_cache(request: Request):
    """Debug du cache sémantique pour analyser les keywords extraits"""
    if not ENABLE_SEMANTIC_DEBUG:
        raise HTTPException(status_code=403, detail="Debug sémantique désactivé")
        
    if not rag_engine_enhanced or not rag_engine_enhanced.cache_manager:
        raise HTTPException(status_code=404, detail="Cache non disponible")
    
    try:
        body = await request.json()
        test_query = body.get("query", "")
        
        if not test_query:
            raise HTTPException(status_code=400, detail="Query manquante")
        
        cache_manager = rag_engine_enhanced.cache_manager
        debug_results = await cache_manager.debug_semantic_extraction(test_query)
        
        # Ajouter tests de variations
        variations = [
            test_query.replace("ross 308", "ross308"),
            test_query.replace("FCR", "fcr").replace("indice conversion", "fcr"),
            test_query.replace("35 jours", "35j"),
            cache_manager._normalize_text(test_query)
        ]
        
        variation_results = []
        for i, var in enumerate(variations):
            if var != test_query:  # Éviter duplicatas
                var_debug = await cache_manager.debug_semantic_extraction(var)
                variation_results.append({
                    "variation_index": i,
                    "variation": var,
                    "keywords": var_debug.get("extracted_keywords", []),
                    "same_semantic_key": var_debug.get("cache_keys", {}).get("semantic") == debug_results.get("cache_keys", {}).get("semantic")
                })
        
        return {
            "debug_results": debug_results,
            "variation_tests": variation_results,
            "test_summary": {
                "total_variations": len(variation_results),
                "semantic_matches": sum(1 for v in variation_results if v["same_semantic_key"]),
                "keywords_overlap": len(set(debug_results.get("extracted_keywords", [])) & 
                                      set().union(*[set(v["keywords"]) for v in variation_results]))
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur debug: {str(e)}")

@router.get(f"{BASE_PATH}/metrics")
async def get_metrics():
    """Endpoint pour récupérer les métriques de performance avec cache sémantique"""
    try:
        base_metrics = {
            "application_metrics": metrics_collector.get_metrics(),
            "system_metrics": {
                "conversation_memory": {
                    "tenants": len(conversation_memory),
                    "total_exchanges": sum(len(v["data"]) for v in conversation_memory.values())
                }
            }
        }
        
        # Ajouter métriques cache sémantique
        if rag_engine_enhanced and rag_engine_enhanced.cache_manager:
            try:
                cache_stats = await rag_engine_enhanced.cache_manager.get_cache_stats()
                base_metrics["semantic_cache_metrics"] = cache_stats
            except:
                base_metrics["semantic_cache_metrics"] = {"error": "unavailable"}
        
        # Métriques RAG Enhanced
        if rag_engine_enhanced:
            try:
                rag_metrics = rag_engine_enhanced.get_status().get("metrics", {})
                base_metrics["rag_enhanced_metrics"] = rag_metrics
            except:
                base_metrics["rag_enhanced_metrics"] = {"error": "unavailable"}
        
        return base_metrics
    except Exception as e:
        return {"error": str(e)}

# NOUVELLE ROUTE: Test performance cache sémantique
@router.post(f"{BASE_PATH}/test/semantic-performance")
async def test_semantic_performance(request: Request):
    """Test de performance du cache sémantique avec variations de requêtes"""
    if not ENABLE_SEMANTIC_DEBUG:
        raise HTTPException(status_code=403, detail="Tests de performance désactivés")
        
    if not rag_engine_enhanced:
        raise HTTPException(status_code=404, detail="RAG Enhanced non disponible")
    
    try:
        body = await request.json()
        base_query = body.get("base_query", "FCR Ross 308 à 35 jours")
        test_variations = body.get("variations", [
            "quel fcr pour ross308 35j",
            "indice conversion ross 308 35 jours", 
            "fcr optimal ross308 à 35j ?",
            "conversion alimentaire r308 35j"
        ])
        
        results = []
        
        for i, query in enumerate([base_query] + test_variations):
            start_time = time.time()
            
            # Test si la requête est en cache
            cache_hit = False
            if rag_engine_enhanced.cache_manager:
                cached_response = await rag_engine_enhanced.cache_manager.get_response(query, "test_context", "fr")
                cache_hit = cached_response is not None
            
            # Si pas en cache, traiter la requête pour la mettre en cache
            if not cache_hit:
                rag_result = await rag_engine_enhanced.process_query(query, "fr", "test_tenant")
                processing_time = time.time() - start_time
            else:
                processing_time = time.time() - start_time
            
            results.append({
                "query_index": i,
                "query": query,
                "cache_hit": cache_hit,
                "processing_time_ms": round(processing_time * 1000, 2),
                "is_baseline": i == 0
            })
        
        # Calculer statistiques
        baseline_time = results[0]["processing_time_ms"]
        cache_hits = sum(1 for r in results if r["cache_hit"])
        avg_time = sum(r["processing_time_ms"] for r in results) / len(results)
        
        return {
            "performance_test": {
                "baseline_query": base_query,
                "baseline_time_ms": baseline_time,
                "results": results,
                "summary": {
                    "total_queries": len(results),
                    "cache_hits": cache_hits,
                    "cache_hit_rate": cache_hits / len(results),
                    "average_time_ms": round(avg_time, 2),
                    "speedup_factor": round(baseline_time / avg_time, 2) if avg_time > 0 else 0
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur test performance: {str(e)}")

# Inclure le router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)