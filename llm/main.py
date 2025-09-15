# -*- coding: utf-8 -*-
"""
main.py - Intelia Expert Backend avec RAG Enhanced + Cache Sémantique Intelligent
Version corrigée: Validation stricte, gestion d'erreurs robuste, monitoring avancé
NOUVELLES FONCTIONNALITÉS CORRIGÉES:
- Validation stricte des dépendances au démarrage
- Gestion d'erreurs explicite (plus de fallbacks silencieux)
- Health checks robustes avec connectivity tests
- Cache sémantique optimisé et stable
- Configuration robuste avec fallbacks explicites
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

# Import du système de dépendances corrigé
from imports_and_dependencies import (
    dependency_manager, 
    require_critical_dependencies,
    get_full_status_report,
    quick_connectivity_check,
    OPENAI_AVAILABLE,
    WEAVIATE_AVAILABLE
)

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# Validation critique au démarrage
if not OPENAI_AVAILABLE:
    raise RuntimeError("OpenAI non disponible - dépendance critique manquante")

if not WEAVIATE_AVAILABLE:
    raise RuntimeError("Weaviate non disponible - dépendance critique manquante")

# Variables globales pour les services
rag_engine_enhanced = None
agent_rag_engine = None
cache_core = None

# Configuration d'application
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Validation configuration critique
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")

# Paramètres système
STREAM_CHUNK_LEN = int(os.environ.get("STREAM_CHUNK_LEN", "400"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "10000"))
MAX_TENANTS = int(os.getenv("MAX_TENANTS", "200"))
TENANT_TTL = int(os.getenv("TENANT_TTL_SEC", "86400"))

# Configuration CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://expert.intelia.com").split(",")

# Paramètres fonctionnalités
ENABLE_RESPONSE_STREAMING = os.getenv("ENABLE_RESPONSE_STREAMING", "true").lower() == "true"
ENABLE_METRICS_LOGGING = os.getenv("ENABLE_METRICS_LOGGING", "true").lower() == "true"
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "6"))

# Paramètres RAG Enhanced
USE_AGENT_RAG = os.getenv("USE_AGENT_RAG", "false").lower() == "true"
PREFER_ENHANCED_RAG = os.getenv("PREFER_ENHANCED_RAG", "true").lower() == "true"

# Paramètres debug et monitoring
ENABLE_SEMANTIC_DEBUG = os.getenv("ENABLE_SEMANTIC_DEBUG", "true").lower() == "true"
ENABLE_STARTUP_VALIDATION = os.getenv("ENABLE_STARTUP_VALIDATION", "true").lower() == "true"
ENABLE_HEALTH_MONITORING = os.getenv("ENABLE_HEALTH_MONITORING", "true").lower() == "true"
STARTUP_TIMEOUT = int(os.getenv("STARTUP_TIMEOUT", "30"))

# Paramètres langue
LANG_DETECTION_MIN_LENGTH = int(os.getenv("LANG_DETECTION_MIN_LENGTH", "20"))

logger.info(f"Mode RAG Enhanced: Cache Sémantique Intelligent + Validation Stricte v3.0")

class StartupValidationError(Exception):
    """Exception pour les erreurs de validation au démarrage"""
    pass

class SystemHealthMonitor:
    """Moniteur de santé système robuste"""
    
    def __init__(self):
        self.startup_time = time.time()
        self.last_health_check = 0.0
        self.health_status = "initializing"
        self.component_status = {}
        self.validation_report = {}
    
    async def validate_startup_requirements(self) -> Dict[str, Any]:
        """Valide tous les prérequis au démarrage avec gestion d'erreurs stricte"""
        validation_report = {
            "timestamp": time.time(),
            "startup_duration": 0.0,
            "critical_dependencies": {},
            "service_connectivity": {},
            "configuration_validation": {},
            "overall_status": "unknown",
            "errors": [],
            "warnings": []
        }
        
        start_time = time.time()
        
        try:
            # 1. Validation des dépendances critiques
            logger.info("Validation des dépendances critiques...")
            
            try:
                require_critical_dependencies()
                dependency_status = get_full_status_report()
                validation_report["critical_dependencies"] = dependency_status
                
                if not dependency_status["critical_dependencies_ok"]:
                    raise StartupValidationError(
                        f"Dépendances critiques manquantes: {dependency_status['critical_missing']}"
                    )
                
                logger.info("✅ Dépendances critiques validées")
                
            except Exception as e:
                validation_report["errors"].append(f"Dépendances critiques: {e}")
                raise StartupValidationError(f"Validation dépendances échouée: {e}")
            
            # 2. Validation de la configuration OpenAI
            logger.info("Validation configuration OpenAI...")
            
            if not OPENAI_API_KEY:
                raise StartupValidationError("OPENAI_API_KEY non configurée")
            
            try:
                from openai import AsyncOpenAI
                test_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                
                # Test simple avec timeout
                await asyncio.wait_for(
                    test_client.models.list(),
                    timeout=10.0
                )
                validation_report["configuration_validation"]["openai"] = "ok"
                logger.info("✅ Configuration OpenAI validée")
                
            except Exception as e:
                validation_report["errors"].append(f"OpenAI: {e}")
                raise StartupValidationError(f"Configuration OpenAI invalide: {e}")
            
            # 3. Initialisation des services principaux
            logger.info("Initialisation des services...")
            
            service_errors = await self._initialize_core_services()
            if service_errors:
                validation_report["errors"].extend(service_errors)
                raise StartupValidationError(f"Échec initialisation services: {service_errors}")
            
            # 4. Tests de connectivité
            logger.info("Tests de connectivité...")
            
            connectivity_status = await self._test_service_connectivity()
            validation_report["service_connectivity"] = connectivity_status
            
            # Vérification connectivité critique
            if not connectivity_status.get("weaviate", False):
                validation_report["warnings"].append("Weaviate non accessible - mode dégradé")
            
            if not connectivity_status.get("redis", False):
                validation_report["warnings"].append("Redis non accessible - cache désactivé")
            
            # 5. Validation finale
            validation_report["startup_duration"] = time.time() - start_time
            
            if validation_report["errors"]:
                validation_report["overall_status"] = "failed"
                self.health_status = "critical"
            elif validation_report["warnings"]:
                validation_report["overall_status"] = "degraded"
                self.health_status = "warning"
            else:
                validation_report["overall_status"] = "healthy"
                self.health_status = "healthy"
            
            logger.info(f"Validation startup terminée: {validation_report['overall_status']} "
                       f"({validation_report['startup_duration']:.2f}s)")
            
            self.validation_report = validation_report
            return validation_report
            
        except StartupValidationError:
            validation_report["startup_duration"] = time.time() - start_time
            validation_report["overall_status"] = "failed"
            self.health_status = "critical"
            self.validation_report = validation_report
            raise
        except Exception as e:
            validation_report["errors"].append(f"Erreur validation inattendue: {e}")
            validation_report["startup_duration"] = time.time() - start_time
            validation_report["overall_status"] = "failed"
            self.health_status = "critical"
            self.validation_report = validation_report
            raise StartupValidationError(f"Validation startup échouée: {e}")
    
    async def _initialize_core_services(self) -> list[str]:
        """Initialise les services principaux avec gestion d'erreurs stricte"""
        errors = []
        
        global rag_engine_enhanced, agent_rag_engine, cache_core
        
        try:
            # Cache Core (optionnel mais recommandé)
            logger.info("  Initialisation Cache Core...")
            try:
                from cache_core import create_cache_core
                cache_core = create_cache_core()
                if cache_core.enabled:
                    success = await cache_core.initialize()
                    if not success:
                        logger.warning("Cache Core désactivé")
                        cache_core = None
                else:
                    logger.info("Cache Core désactivé par configuration")
                    cache_core = None
            except Exception as e:
                logger.warning(f"Cache Core non disponible: {e}")
                cache_core = None
            
            # RAG Engine Enhanced (critique)
            logger.info("  Initialisation RAG Engine...")
            try:
                # Import avec validation
                try:
                    from rag_engine import create_rag_engine, RAGSource, RAGResult
                except ImportError as e:
                    errors.append(f"Module RAG Engine non disponible: {e}")
                    return errors
                
                # Création des clients OpenAI
                from openai import OpenAI, AsyncOpenAI
                openai_sync = OpenAI(api_key=OPENAI_API_KEY)
                openai_async = AsyncOpenAI(api_key=OPENAI_API_KEY)
                
                # Créer le RAG engine
                rag_engine_enhanced = create_rag_engine(openai_async)
                
                if not rag_engine_enhanced or not getattr(rag_engine_enhanced, 'is_initialized', False):
                    errors.append("RAG Engine non initialisé correctement")
                else:
                    logger.info("✅ RAG Engine initialisé")
                    
                    # Log des optimisations disponibles
                    try:
                        status = rag_engine_enhanced.get_status()
                        optimizations = status.get("optimizations", {})
                        
                        logger.info(f"   - Cache Redis: {optimizations.get('external_cache_enabled', False)}")
                        logger.info(f"   - Cache sémantique: {optimizations.get('semantic_cache_enabled', False)}")
                        logger.info(f"   - Recherche hybride: {optimizations.get('hybrid_search_enabled', False)}")
                        logger.info(f"   - Guardrails: {optimizations.get('guardrails_level', 'unknown')}")
                        
                    except Exception as e:
                        logger.warning(f"Impossible de récupérer le status RAG: {e}")
                    
            except Exception as e:
                errors.append(f"RAG Engine: {e}")
            
            # Agent RAG (optionnel)
            if USE_AGENT_RAG:
                logger.info("  Initialisation Agent RAG...")
                try:
                    from agent_rag_extension import create_agent_rag_engine
                    agent_rag_engine = create_agent_rag_engine()
                    logger.info("✅ Agent RAG disponible")
                except ImportError:
                    logger.info("Agent RAG non disponible (optionnel)")
                    agent_rag_engine = None
                except Exception as e:
                    logger.warning(f"Agent RAG erreur: {e}")
                    agent_rag_engine = None
            
        except Exception as e:
            errors.append(f"Erreur initialisation services: {e}")
        
        return errors
    
    async def _test_service_connectivity(self) -> Dict[str, bool]:
        """Teste la connectivité aux services externes avec timeout"""
        
        # Clients pour tests
        redis_client = cache_core.client if cache_core and getattr(cache_core, 'initialized', False) else None
        weaviate_client = getattr(rag_engine_enhanced, 'weaviate_client', None) if rag_engine_enhanced else None
        
        try:
            connectivity = await asyncio.wait_for(
                quick_connectivity_check(redis_client, weaviate_client),
                timeout=10.0
            )
            return connectivity
        except asyncio.TimeoutError:
            logger.error("Timeout test connectivité")
            return {"redis": False, "weaviate": False}
        except Exception as e:
            logger.error(f"Erreur test connectivité: {e}")
            return {"redis": False, "weaviate": False}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Retourne l'état de santé actuel du système"""
        self.last_health_check = time.time()
        
        # Stats système
        uptime = time.time() - self.startup_time
        
        # Statut des composants
        component_status = {}
        
        if rag_engine_enhanced:
            try:
                rag_status = rag_engine_enhanced.get_status()
                component_status["rag_engine"] = {
                    "status": "healthy" if rag_status.get("initialized") else "degraded",
                    "details": rag_status
                }
            except Exception as e:
                component_status["rag_engine"] = {"status": "error", "error": str(e)}
        else:
            component_status["rag_engine"] = {"status": "missing"}
        
        if cache_core:
            try:
                cache_stats = await cache_core.get_cache_stats()
                component_status["cache"] = {
                    "status": cache_stats.get("status", "unknown"),
                    "details": cache_stats
                }
            except Exception as e:
                component_status["cache"] = {"status": "error", "error": str(e)}
        else:
            component_status["cache"] = {"status": "disabled"}
        
        # Statut global
        component_statuses = [comp.get("status") for comp in component_status.values()]
        
        if "error" in component_statuses or "missing" in component_statuses:
            overall_status = "degraded"
        elif "degraded" in component_statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "overall_status": overall_status,
            "uptime_seconds": uptime,
            "last_check": self.last_health_check,
            "components": component_status,
            "dependencies": get_full_status_report(),
            "startup_validation": self.validation_report,
            "system": {
                "startup_time": self.startup_time,
                "base_path": BASE_PATH,
                "version": "enhanced_v3.0_corrected"
            }
        }

# Instance globale du moniteur
health_monitor = SystemHealthMonitor()

# Helpers OpenAI
def get_openai_sync():
    """Factory pour client OpenAI synchrone"""
    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI non disponible")
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)

def get_openai_async():
    """Factory pour client OpenAI asynchrone"""
    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI non disponible")
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=OPENAI_API_KEY)

# Chargement des messages multilingues avec validation
def _load_language_messages(path: str) -> Dict[str, str]:
    try:
        if not os.path.exists(path):
            logger.warning(f"Fichier langue non trouvé: {path}")
            return _get_default_messages()
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            logger.error(f"Format invalide dans {path}")
            return _get_default_messages()
        
        return {(k.lower() if isinstance(k, str) else k): v for k, v in data.items()}
    except Exception as e:
        logger.error(f"Erreur chargement {path}: {e}")
        return _get_default_messages()

def _get_default_messages() -> Dict[str, str]:
    """Messages par défaut si fichier de langue non disponible"""
    return {
        "default": "Intelia Expert is a poultry-focused application. Questions outside this domain cannot be processed.",
        "fr": "Intelia Expert est une application spécialisée en aviculture. Les questions hors de ce domaine ne peuvent pas être traitées.",
        "en": "Intelia Expert is a poultry-focused application. Questions outside this domain cannot be processed.",
        "es": "Intelia Expert es una aplicación especializada en avicultura. No se pueden procesar preguntas fuera de este dominio.",
        "de": "Intelia Expert ist eine auf Geflügelhaltung spezialisierte Anwendung. Fragen außerhalb dieses Bereichs können nicht bearbeitet werden."
    }

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANGUAGE_FILE = os.path.join(BASE_DIR, "languages.json")
OUT_OF_DOMAIN_MESSAGES = _load_language_messages(LANGUAGE_FILE)

def get_out_of_domain_message(lang: str) -> str:
    """Récupère le message hors-domaine dans la langue appropriée"""
    if not lang:
        return OUT_OF_DOMAIN_MESSAGES.get("default", "Questions outside domain not supported.")
    
    code = (lang or "").lower()
    msg = OUT_OF_DOMAIN_MESSAGES.get(code)
    if msg:
        return msg
    
    short = code.split("-")[0]
    return OUT_OF_DOMAIN_MESSAGES.get(short, OUT_OF_DOMAIN_MESSAGES.get("default", "Questions outside domain not supported."))

# Clients OpenAI globaux avec validation
try:
    openai_client_sync = get_openai_sync()
    openai_client_async = get_openai_async()
    logger.info("Clients OpenAI (sync + async) initialisés")
except Exception as e:
    logger.error(f"Erreur initialisation clients OpenAI: {e}")
    raise RuntimeError(f"Impossible d'initialiser les clients OpenAI: {e}")

# Mémoire de conversation avec validation
class TenantMemory(OrderedDict):
    """Cache LRU avec TTL pour la mémoire de conversation - Version robuste"""
    
    def set(self, tenant_id: str, item: list):
        if not tenant_id or not isinstance(item, list):
            logger.warning(f"Paramètres invalides pour TenantMemory.set: {tenant_id}, {type(item)}")
            return
        
        now = time.time()
        self[tenant_id] = {"data": item, "ts": now, "last_query": ""}
        self.move_to_end(tenant_id)
        
        # Purge TTL
        try:
            expired_keys = [k for k, v in self.items() if now - v.get("ts", 0) > TENANT_TTL]
            for k in expired_keys:
                del self[k]
                logger.debug(f"Tenant {k} expiré (TTL)")
        except Exception as e:
            logger.warning(f"Erreur purge TTL: {e}")
        
        # Purge LRU
        try:
            while len(self) > MAX_TENANTS:
                oldest_tenant, _ = self.popitem(last=False)
                logger.debug(f"Tenant {oldest_tenant} purgé (LRU)")
        except Exception as e:
            logger.warning(f"Erreur purge LRU: {e}")
    
    def get(self, tenant_id: str, default=None):
        if not tenant_id or tenant_id not in self:
            return default
        
        try:
            now = time.time()
            if now - self[tenant_id].get("ts", 0) > TENANT_TTL:
                del self[tenant_id]
                return default
            
            self[tenant_id]["ts"] = now
            self.move_to_end(tenant_id)
            return self[tenant_id]
        except Exception as e:
            logger.warning(f"Erreur récupération tenant {tenant_id}: {e}")
            return default
    
    def update_last_query(self, tenant_id: str, query: str):
        """Met à jour la dernière requête pour un tenant"""
        if tenant_id in self and isinstance(query, str):
            try:
                self[tenant_id]["last_query"] = query[:500]  # Limiter la taille
            except Exception as e:
                logger.warning(f"Erreur mise à jour last_query: {e}")

conversation_memory = TenantMemory()

def add_to_conversation_memory(tenant_id: str, question: str, answer: str, source: str = "rag_enhanced"):
    """Ajoute un échange à la mémoire de conversation avec validation"""
    if not tenant_id or not question or not answer:
        logger.warning("Paramètres invalides pour add_to_conversation_memory")
        return
    
    try:
        tenant_data = conversation_memory.get(tenant_id, {"data": []})
        history = tenant_data.get("data", [])
        
        history.append({
            "question": question[:1000],  # Limiter la taille
            "answer": answer[:2000],      # Limiter la taille
            "timestamp": time.time(),
            "answer_source": source
        })
        
        # Limiter selon la configuration
        if len(history) > MAX_CONVERSATION_CONTEXT:
            history = history[-MAX_CONVERSATION_CONTEXT:]
        
        conversation_memory.set(tenant_id, history)
        conversation_memory.update_last_query(tenant_id, question)
    except Exception as e:
        logger.error(f"Erreur ajout conversation memory: {e}")

# Collecteur de métriques robuste
class MetricsCollector:
    """Collecteur de métriques avec protection contre les erreurs"""
    
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
            "errors": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0,
        }
        self.recent_processing_times = []
        self.recent_confidences = []
        self.latency_percentiles = {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        self.max_recent_samples = 100
    
    def record_query(self, result, source_type: str = "unknown", endpoint_time: float = 0.0):
        """Enregistre les métriques avec protection contre les erreurs"""
        if not ENABLE_METRICS_LOGGING:
            return
        
        try:
            self.metrics["total_queries"] += 1
            
            # Gestion selon le type de source
            if source_type == "rag_enhanced":
                self.metrics["rag_enhanced_queries"] += 1
            elif source_type == "agent_rag":
                self.metrics["agent_queries"] += 1
            elif source_type == "error":
                self.metrics["errors"] += 1
            
            # Traitement selon le type de résultat
            if hasattr(result, 'source'):
                try:
                    source_value = result.source.value if hasattr(result.source, 'value') else str(result.source)
                    if "rag" in source_value.lower():
                        self.metrics["rag_standard_queries"] += 1
                    elif "ood" in source_value.lower():
                        self.metrics["ood_filtered"] += 1
                    else:
                        self.metrics["fallback_queries"] += 1
                except:
                    self.metrics["fallback_queries"] += 1
            
            # Métriques cache et performance
            if hasattr(result, 'metadata') and result.metadata:
                try:
                    opt_stats = result.metadata.get("optimization_stats", {})
                    self.metrics["cache_hits"] += opt_stats.get("cache_hits", 0)
                    self.metrics["cache_misses"] += opt_stats.get("cache_misses", 0)
                    self.metrics["semantic_cache_hits"] += opt_stats.get("semantic_cache_hits", 0)
                    self.metrics["hybrid_searches"] += opt_stats.get("hybrid_searches", 0)
                except:
                    pass
            
            # Calcul des métriques temporelles
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
                if len(self.recent_processing_times) >= 10:
                    try:
                        sorted_times = sorted(self.recent_processing_times)
                        n = len(sorted_times)
                        self.latency_percentiles["p50"] = sorted_times[int(n * 0.5)]
                        self.latency_percentiles["p95"] = sorted_times[int(n * 0.95)]
                        self.latency_percentiles["p99"] = sorted_times[int(n * 0.99)]
                    except:
                        pass
            
            # Confiance
            confidence = getattr(result, 'confidence', 0)
            if confidence > 0:
                self.recent_confidences.append(confidence)
                if len(self.recent_confidences) > self.max_recent_samples:
                    self.recent_confidences.pop(0)
                
                self.metrics["avg_confidence"] = (
                    sum(self.recent_confidences) / len(self.recent_confidences)
                )
        
        except Exception as e:
            logger.warning(f"Erreur enregistrement métriques: {e}")
            self.metrics["errors"] = self.metrics.get("errors", 0) + 1
    
    def get_metrics(self) -> Dict:
        """Retourne les métriques avec protection contre les erreurs"""
        try:
            total_queries = max(1, self.metrics["total_queries"])
            total_cache_requests = max(1, self.metrics["cache_hits"] + self.metrics["cache_misses"])
            
            return {
                **self.metrics,
                "success_rate": (
                    (self.metrics["rag_enhanced_queries"] + self.metrics["verified_responses"] + self.metrics["agent_queries"]) / total_queries
                ),
                "enhanced_rag_usage_rate": self.metrics["rag_enhanced_queries"] / total_queries,
                "cache_hit_rate": self.metrics["cache_hits"] / total_cache_requests,
                "semantic_cache_hit_rate": self.metrics["semantic_cache_hits"] / total_cache_requests,
                "error_rate": self.metrics["errors"] / total_queries,
                "latency_percentiles": self.latency_percentiles
            }
        except Exception as e:
            logger.error(f"Erreur calcul métriques: {e}")
            return self.metrics

metrics_collector = MetricsCollector()

# Helpers de streaming robustes
def sse_event(obj: Dict[str, Any]) -> bytes:
    """Formatage SSE avec gestion d'erreurs robuste"""
    try:
        data = json.dumps(obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        error_obj = {"type": "error", "message": "Erreur formatage données"}
        data = json.dumps(error_obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")

def smart_chunk_text(text: str, max_chunk_size: int = None) -> list:
    """Découpe intelligente du texte avec validation"""
    if not isinstance(text, str):
        return []
    
    max_chunk_size = max_chunk_size or STREAM_CHUNK_LEN
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []
    
    try:
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
    
    except Exception as e:
        logger.error(f"Erreur découpe texte: {e}")
        return [text[:max_chunk_size]] if text else []

# Détection de langue robuste
def guess_lang_from_text(text: str) -> Optional[str]:
    """Détection automatique de la langue avec fallbacks robustes"""
    if not isinstance(text, str) or not text.strip():
        return 'fr'  # Défaut français
    
    try:
        text = text.strip()
        
        # Pour les textes courts, utiliser patterns
        if len(text) < LANG_DETECTION_MIN_LENGTH:
            text_lower = text.lower()
            
            quick_patterns = {
                'fr': ['fcr', 'poulet', 'ross', 'cobb', 'jours', 'jour', 'kg', 'poids', 'conversion', 'qu', 'comment'],
                'en': ['fcr', 'chicken', 'broiler', 'days', 'day', 'weight', 'feed', 'conversion', 'what', 'how'],
                'es': ['fcr', 'pollo', 'días', 'día', 'peso', 'conversión', 'alimento', 'qué', 'cómo'],
                'de': ['fcr', 'huhn', 'tage', 'tag', 'gewicht', 'futter', 'was', 'wie']
            }
            
            for lang, patterns in quick_patterns.items():
                if any(pattern in text_lower for pattern in patterns):
                    logger.debug(f"Détection rapide: {lang} pour '{text[:20]}...'")
                    return lang
            
            return 'fr'  # Fallback français pour textes courts
        
        # Pour les textes plus longs, utiliser langdetect si disponible
        try:
            from langdetect import detect
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
            logger.debug(f"Détection: {result} pour '{text[:30]}...'")
            return result
            
        except ImportError:
            logger.debug("langdetect non disponible, utilisation patterns")
        except Exception as e:
            logger.debug(f"Erreur langdetect: {e}, fallback patterns")
        
        # Fallback par patterns étendus
        text_lower = text.lower()
        
        lang_patterns = {
            'fr': ['poulet', 'aviculture', 'qu\'est', 'comment', 'quelle', 'combien'],
            'en': ['chicken', 'poultry', 'what', 'how', 'which', 'where'],
            'es': ['pollo', 'avicultura', 'qué', 'cómo', 'cuál', 'dónde'],
            'de': ['huhn', 'geflügel', 'was', 'wie', 'welche', 'wo']
        }
        
        for lang, patterns in lang_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                logger.debug(f"Fallback pattern: {lang} pour '{text[:20]}...'")
                return lang
        
        return 'fr'  # Défaut français final
        
    except Exception as e:
        logger.warning(f"Erreur détection langue pour '{text[:50]}...': {e}")
        return 'fr'  # Défaut français en cas d'erreur

# Gestion du cycle de vie de l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie avec validation stricte"""
    
    logger.info("Démarrage Intelia Expert Backend...")
    
    try:
        if ENABLE_STARTUP_VALIDATION:
            # Validation complète au démarrage
            validation_result = await asyncio.wait_for(
                health_monitor.validate_startup_requirements(),
                timeout=STARTUP_TIMEOUT
            )
            
            if validation_result["overall_status"] == "failed":
                logger.error("Validation startup échouée - Arrêt de l'application")
                raise RuntimeError(f"Startup validation failed: {validation_result['errors']}")
            
            elif validation_result["overall_status"] == "degraded":
                logger.warning("Application démarrée en mode dégradé")
                logger.warning(f"Warnings: {validation_result['warnings']}")
            
            else:
                logger.info("Application démarrée avec succès")
        
        else:
            logger.info("Validation startup désactivée")
            # Initialisation minimale
            await health_monitor._initialize_core_services()
        
        # Application prête
        logger.info(f"API disponible sur {BASE_PATH}")
        
        yield
        
    except asyncio.TimeoutError:
        logger.error(f"Timeout startup après {STARTUP_TIMEOUT}s")
        raise RuntimeError("Startup timeout")
    
    except Exception as e:
        logger.error(f"Erreur critique au démarrage: {e}")
        raise
    
    finally:
        # Nettoyage
        logger.info("Nettoyage des ressources...")
        
        try:
            global rag_engine_enhanced, agent_rag_engine, cache_core
            
            if cache_core and hasattr(cache_core, 'cleanup'):
                await cache_core.cleanup()
            
            if rag_engine_enhanced and hasattr(rag_engine_enhanced, 'cleanup'):
                await rag_engine_enhanced.cleanup()
            
            if agent_rag_engine and hasattr(agent_rag_engine, 'cleanup'):
                await agent_rag_engine.cleanup()
            
            # Fermer les clients OpenAI
            if hasattr(openai_client_async, 'http_client'):
                await openai_client_async.http_client.aclose()
            
            # Nettoyer les variables globales
            rag_engine_enhanced = None
            agent_rag_engine = None
            cache_core = None
            conversation_memory.clear()
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
        
        logger.info("Application arrêtée")

# Création de l'application FastAPI
app = FastAPI(
    title="Intelia Expert Backend",
    description="API RAG Enhanced avec validation stricte et cache sémantique",
    version="3.0.0-corrected",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Router principal
router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check complet avec détails des composants"""
    try:
        health_status = await health_monitor.get_health_status()
        
        # Code de statut HTTP selon l'état
        if health_status["overall_status"] == "healthy":
            status_code = 200
        elif health_status["overall_status"] == "degraded":
            status_code = 200  # Toujours 200 mais avec warnings
        else:
            status_code = 503  # Service Unavailable
        
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "overall_status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
        )

@router.get(f"{BASE_PATH}/status/dependencies")
async def dependencies_status():
    """Statut détaillé des dépendances"""
    try:
        return get_full_status_report()
    except Exception as e:
        return {"error": str(e)}

@router.get(f"{BASE_PATH}/status/connectivity")
async def connectivity_status():
    """Test de connectivité aux services externes"""
    try:
        redis_client = cache_core.client if cache_core and getattr(cache_core, 'initialized', False) else None
        weaviate_client = getattr(rag_engine_enhanced, 'weaviate_client', None) if rag_engine_enhanced else None
        
        connectivity = await quick_connectivity_check(redis_client, weaviate_client)
        
        return {
            "timestamp": time.time(),
            "services": connectivity,
            "overall": all(connectivity.values())
        }
        
    except Exception as e:
        return {"error": str(e), "overall": False}

@router.get(f"{BASE_PATH}/metrics")
async def get_metrics():
    """Endpoint pour récupérer les métriques de performance"""
    try:
        base_metrics = {
            "application_metrics": metrics_collector.get_metrics(),
            "system_metrics": {
                "conversation_memory": {
                    "tenants": len(conversation_memory),
                    "total_exchanges": sum(len(v.get("data", [])) for v in conversation_memory.values())
                }
            }
        }
        
        # Ajouter métriques cache si disponible
        if rag_engine_enhanced and hasattr(rag_engine_enhanced, 'cache_manager') and rag_engine_enhanced.cache_manager:
            try:
                cache_stats = await rag_engine_enhanced.cache_manager.get_cache_stats()
                base_metrics["cache_metrics"] = cache_stats
            except Exception as e:
                base_metrics["cache_metrics"] = {"error": str(e)}
        
        return base_metrics
    except Exception as e:
        return {"error": str(e)}

# Route CHAT principale avec validation stricte
@router.post(f"{BASE_PATH}/chat")
async def chat(request: Request):
    """Chat endpoint avec validation stricte et gestion d'erreurs robuste"""
    total_start_time = time.time()
    
    if not rag_engine_enhanced:
        metrics_collector.record_query({"source": "error"}, "error", time.time() - total_start_time)
        raise HTTPException(status_code=503, detail="RAG Engine Enhanced non disponible")
    
    try:
        # Validation de la requête
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"JSON invalide: {e}")
        
        message = body.get("message", "").strip()
        language = body.get("language", "").strip()
        tenant_id = body.get("tenant_id", str(uuid.uuid4())[:8])
        
        # Validations
        if not message:
            raise HTTPException(status_code=400, detail="Message vide")
        
        if len(message) > MAX_REQUEST_SIZE:
            raise HTTPException(status_code=413, detail=f"Message trop long (max {MAX_REQUEST_SIZE})")
        
        # Détection de langue si non fournie
        if not language:
            language = guess_lang_from_text(message)
        
        # Validation tenant_id
        if not tenant_id or len(tenant_id) > 50:
            tenant_id = str(uuid.uuid4())[:8]
        
        # Messages trop courts -> réponse OOD
        if len(message.split()) < 3:
            out_of_domain_msg = get_out_of_domain_message(language)
            
            async def simple_response():
                yield sse_event({"type": "start", "reason": "too_short"})
                yield sse_event({"type": "chunk", "content": out_of_domain_msg})
                yield sse_event({"type": "end", "confidence": 0.9})
            
            metrics_collector.record_query({"source": "ood"}, "ood", time.time() - total_start_time)
            return StreamingResponse(simple_response(), media_type="text/plain")
        
        # Traitement principal avec RAG Enhanced
        try:
            rag_result = await rag_engine_enhanced.process_query(message, language, tenant_id)
        except Exception as e:
            logger.error(f"Erreur traitement RAG: {e}")
            metrics_collector.record_query({"source": "error"}, "error", time.time() - total_start_time)
            raise HTTPException(status_code=500, detail=f"Erreur traitement: {str(e)}")
        
        # Enregistrer métriques
        total_processing_time = time.time() - total_start_time
        metrics_collector.record_query(rag_result, "rag_enhanced", total_processing_time)
        
        # Streaming de la réponse
        async def generate_response():
            try:
                # Informations de début
                metadata = getattr(rag_result, 'metadata', {}) or {}
                yield sse_event({
                    "type": "start", 
                    "source": getattr(rag_result, 'source', 'unknown'),
                    "confidence": getattr(rag_result, 'confidence', 0.5),
                    "processing_time": getattr(rag_result, 'processing_time', 0)
                })
                
                # Contenu de la réponse
                answer = getattr(rag_result, 'answer', '')
                if answer:
                    chunks = smart_chunk_text(answer, STREAM_CHUNK_LEN)
                    
                    for i, chunk in enumerate(chunks):
                        yield sse_event({
                            "type": "chunk", 
                            "content": chunk,
                            "chunk_index": i
                        })
                        await asyncio.sleep(0.01)  # Streaming fluide
                
                # Informations finales
                yield sse_event({
                    "type": "end",
                    "total_time": total_processing_time,
                    "confidence": getattr(rag_result, 'confidence', 0.5),
                    "documents_used": len(getattr(rag_result, 'context_docs', []))
                })
                
                # Enregistrer en mémoire
                if answer and hasattr(rag_result, 'source'):
                    add_to_conversation_memory(tenant_id, message, answer, "rag_enhanced")
                
            except Exception as e:
                logger.error(f"Erreur streaming: {e}")
                yield sse_event({"type": "error", "message": str(e)})
        
        return StreamingResponse(generate_response(), media_type="text/plain")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur chat endpoint: {e}")
        metrics_collector.record_query({"source": "error"}, "error", time.time() - total_start_time)
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur traitement: {str(e)}"}
        )

# Route OOD pour compatibilité
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

# Inclusion du router
app.include_router(router)

# Point d'entrée pour le développement
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Démarrage serveur de développement sur {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Désactivé en production
        log_level="info"
    )