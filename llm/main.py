# -*- coding: utf-8 -*-
"""
main.py - Intelia Expert Backend avec RAG Enhanced + LangSmith + RRF Intelligent
Version corrigée: Validation stricte, gestion d'erreurs robuste, monitoring avancé
NOUVELLES FONCTIONNALITÉS AJOUTÉES:
- Intégration LangSmith pour monitoring LLM
- Support RRF Intelligent avec métriques
- Variables d'environnement Digital Ocean
- Health checks enrichis avec nouveau statut
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

# === NOUVEAU: Imports configuration enrichie ===
from config import (
    # Core
    RAG_ENABLED, CACHE_ENABLED, OPENAI_API_KEY, WEAVIATE_URL, REDIS_URL,
    # LangSmith
    LANGSMITH_ENABLED, LANGSMITH_API_KEY, LANGSMITH_PROJECT,
    # RRF Intelligent
    ENABLE_INTELLIGENT_RRF, RRF_LEARNING_MODE, RRF_GENETIC_BOOST,
    # Autres
    MAX_CONVERSATION_CONTEXT, HYBRID_SEARCH_ENABLED,
    validate_config, get_config_status
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

# === NOUVEAU: Validation configuration enrichie ===
config_valid, config_errors = validate_config()
if not config_valid:
    logger.error(f"Configuration invalide: {config_errors}")
    # En production, on peut continuer avec warnings
    for error in config_errors:
        logger.warning(f"Config: {error}")

# Variables globales pour les services
rag_engine_enhanced = None
agent_rag_engine = None
cache_core = None

# Configuration d'application
BASE_PATH = os.environ.get("BASE_PATH", "/llm").rstrip("/")

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

# Paramètres RAG Enhanced
USE_AGENT_RAG = os.getenv("USE_AGENT_RAG", "false").lower() == "true"
PREFER_ENHANCED_RAG = os.getenv("PREFER_ENHANCED_RAG", "true").lower() == "true"

# Paramètres debug et monitoring
ENABLE_SEMANTIC_DEBUG = os.getenv("ENABLE_SEMANTIC_DEBUG", "true").lower() == "true"
ENABLE_STARTUP_VALIDATION = os.getenv("ENABLE_STARTUP_VALIDATION", "true").lower() == "true"
ENABLE_HEALTH_MONITORING = os.getenv("ENABLE_HEALTH_MONITORING", "true").lower() == "true"
STARTUP_TIMEOUT = int(os.getenv("STARTUP_TIMEOUT", "30"))

# === NOUVEAU: Paramètres Digital Ocean ===
DO_APP_NAME = os.getenv("DO_APP_NAME", "intelia-expert")
DO_APP_TIER = os.getenv("DO_APP_TIER", "basic")

# Paramètres langue
LANG_DETECTION_MIN_LENGTH = int(os.getenv("LANG_DETECTION_MIN_LENGTH", "20"))

logger.info(f"Mode RAG Enhanced: LangSmith + RRF Intelligent v4.0")
logger.info(f"Configuration: LangSmith={LANGSMITH_ENABLED}, RRF={ENABLE_INTELLIGENT_RRF}")

class StartupValidationError(Exception):
    """Exception pour les erreurs de validation au démarrage"""
    pass

class SystemHealthMonitor:
    """Moniteur de santé système robuste avec LangSmith et RRF"""
    
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
            "langsmith_validation": {},
            "rrf_validation": {},
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
            
            # === NOUVEAU: 3. Validation LangSmith ===
            logger.info("Validation configuration LangSmith...")
            
            if LANGSMITH_ENABLED:
                if not LANGSMITH_API_KEY:
                    validation_report["warnings"].append("LangSmith activé mais API key manquante")
                    validation_report["langsmith_validation"]["status"] = "disabled"
                else:
                    try:
                        # Test basique LangSmith
                        validation_report["langsmith_validation"] = {
                            "enabled": True,
                            "api_key_present": bool(LANGSMITH_API_KEY),
                            "project": LANGSMITH_PROJECT,
                            "status": "configured"
                        }
                        logger.info("✅ LangSmith configuré")
                    except Exception as e:
                        validation_report["warnings"].append(f"LangSmith: {e}")
                        validation_report["langsmith_validation"]["status"] = "error"
            else:
                validation_report["langsmith_validation"]["status"] = "disabled"
            
            # === NOUVEAU: 4. Validation RRF Intelligent ===
            logger.info("Validation RRF Intelligent...")
            
            if ENABLE_INTELLIGENT_RRF:
                validation_report["rrf_validation"] = {
                    "enabled": True,
                    "learning_mode": RRF_LEARNING_MODE,
                    "genetic_boost": RRF_GENETIC_BOOST,
                    "redis_required": True,
                    "status": "configured"
                }
                logger.info("✅ RRF Intelligent configuré")
            else:
                validation_report["rrf_validation"]["status"] = "disabled"
            
            # 5. Initialisation des services principaux
            logger.info("Initialisation des services...")
            
            service_errors = await self._initialize_core_services()
            if service_errors:
                validation_report["errors"].extend(service_errors)
                raise StartupValidationError(f"Échec initialisation services: {service_errors}")
            
            # 6. Tests de connectivité
            logger.info("Tests de connectivité...")
            
            connectivity_status = await self._test_service_connectivity()
            validation_report["service_connectivity"] = connectivity_status
            
            # Vérification connectivité critique
            if not connectivity_status.get("weaviate", False):
                validation_report["warnings"].append("Weaviate non accessible - mode dégradé")
            
            if not connectivity_status.get("redis", False):
                validation_report["warnings"].append("Redis non accessible - cache désactivé")
                if ENABLE_INTELLIGENT_RRF:
                    validation_report["warnings"].append("RRF Intelligent désactivé (Redis requis)")
            
            # 7. Validation finale
            validation_report["startup_duration"] = time.time() - start_time
            
            if validation_report["errors"]:
                validation_report["overall_status"] = "failed"
            elif validation_report["warnings"]:
                validation_report["overall_status"] = "degraded"
            else:
                validation_report["overall_status"] = "healthy"
            
            self.validation_report = validation_report
            return validation_report
            
        except StartupValidationError:
            validation_report["startup_duration"] = time.time() - start_time
            validation_report["overall_status"] = "failed"
            self.validation_report = validation_report
            raise
        except Exception as e:
            validation_report["errors"].append(f"Erreur validation inattendue: {e}")
            validation_report["startup_duration"] = time.time() - start_time
            validation_report["overall_status"] = "failed"
            self.validation_report = validation_report
            raise StartupValidationError(f"Validation échouée: {e}")
    
    async def _initialize_core_services(self) -> list:
        """Initialise les services principaux avec support LangSmith + RRF"""
        global rag_engine_enhanced, agent_rag_engine, cache_core
        errors = []
        
        try:
            # Cache Core
            logger.info("  Initialisation Cache Core...")
            try:
                from cache_core import create_cache_core
                cache_core = create_cache_core()
                await cache_core.initialize()
                
                if cache_core.initialized:
                    logger.info("✅ Cache Core initialisé")
                else:
                    logger.warning("⚠️ Cache Core en mode dégradé")
                    
            except Exception as e:
                errors.append(f"Cache Core: {e}")
                logger.warning(f"Cache Core erreur: {e}")
            
            # RAG Engine Enhanced avec LangSmith + RRF
            logger.info("  Initialisation RAG Engine Enhanced...")
            try:
                from rag_engine import InteliaRAGEngine
                rag_engine_enhanced = InteliaRAGEngine()
                await rag_engine_enhanced.initialize()
                
                if rag_engine_enhanced.is_initialized:
                    logger.info("✅ RAG Engine Enhanced initialisé")
                    
                    # Vérifier intégrations
                    status = rag_engine_enhanced.get_status()
                    
                    # Log statut LangSmith
                    langsmith_status = status.get("langsmith", {})
                    if langsmith_status.get("enabled"):
                        logger.info(f"✅ LangSmith actif - Projet: {langsmith_status.get('project')}")
                    
                    # Log statut RRF Intelligent
                    rrf_status = status.get("intelligent_rrf", {})
                    if rrf_status.get("enabled"):
                        logger.info(f"✅ RRF Intelligent actif - Learning: {rrf_status.get('learning_mode')}")
                    
                    # Log optimisations activées
                    optimizations = status.get("optimizations", {})
                    logger.info(f"Optimisations: Cache={optimizations.get('external_cache_enabled', False)}")
                    logger.info(f"   - Hybrid Search: {optimizations.get('hybrid_search_enabled', False)}")
                    logger.info(f"   - LangSmith: {optimizations.get('langsmith_enabled', False)}")
                    logger.info(f"   - RRF Intelligent: {optimizations.get('intelligent_rrf_enabled', False)}")
                        
                else:
                    logger.warning("⚠️ RAG Engine en mode dégradé")
                    
            except Exception as e:
                errors.append(f"RAG Engine: {e}")
                logger.error(f"RAG Engine erreur: {e}")
            
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
            logger.warning("Timeout test connectivité")
            return {"redis": False, "weaviate": False, "timeout": True}
        except Exception as e:
            logger.error(f"Erreur test connectivité: {e}")
            return {"redis": False, "weaviate": False, "error": str(e)}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Health check enrichi avec LangSmith et RRF"""
        current_time = time.time()
        
        # Statut global
        global_status = {
            "overall_status": "healthy",
            "timestamp": current_time,
            "uptime_seconds": current_time - self.startup_time,
            "startup_validation": self.validation_report,
            "services": {},
            "integrations": {},
            "warnings": []
        }
        
        try:
            # === NOUVEAU: Statut services enrichi ===
            
            # RAG Engine
            if rag_engine_enhanced and rag_engine_enhanced.is_initialized:
                rag_status = rag_engine_enhanced.get_status()
                global_status["services"]["rag_engine"] = {
                    "status": "healthy" if not rag_engine_enhanced.degraded_mode else "degraded",
                    "approach": rag_status.get("approach", "unknown"),
                    "optimizations": rag_status.get("optimizations", {}),
                    "metrics": rag_status.get("optimization_stats", {})
                }
                
                # === NOUVEAU: Intégrations spécialisées ===
                
                # LangSmith
                langsmith_info = rag_status.get("langsmith", {})
                global_status["integrations"]["langsmith"] = {
                    "available": langsmith_info.get("available", False),
                    "enabled": langsmith_info.get("enabled", False),
                    "configured": langsmith_info.get("configured", False),
                    "project": langsmith_info.get("project", ""),
                    "traces_count": langsmith_info.get("traces_count", 0),
                    "errors_count": langsmith_info.get("errors_count", 0)
                }
                
                if langsmith_info.get("enabled") and not langsmith_info.get("configured"):
                    global_status["warnings"].append("LangSmith activé mais non configuré")
                
                # RRF Intelligent
                rrf_info = rag_status.get("intelligent_rrf", {})
                global_status["integrations"]["intelligent_rrf"] = {
                    "available": rrf_info.get("available", False),
                    "enabled": rrf_info.get("enabled", False),
                    "configured": rrf_info.get("configured", False),
                    "learning_mode": rrf_info.get("learning_mode", False),
                    "usage_count": rrf_info.get("usage_count", 0),
                    "performance_stats": rrf_info.get("performance_stats", {})
                }
                
                if rrf_info.get("enabled") and not rrf_info.get("configured"):
                    global_status["warnings"].append("RRF Intelligent activé mais non configuré")
                
            else:
                global_status["services"]["rag_engine"] = {"status": "error", "reason": "not_initialized"}
                global_status["overall_status"] = "degraded"
            
            # Cache
            if cache_core and getattr(cache_core, 'initialized', False):
                cache_status = cache_core.get_health_status() if hasattr(cache_core, 'get_health_status') else {"status": "unknown"}
                global_status["services"]["cache"] = cache_status
            else:
                global_status["services"]["cache"] = {"status": "disabled"}
            
            # Agent RAG
            if agent_rag_engine:
                global_status["services"]["agent_rag"] = {"status": "available"}
            else:
                global_status["services"]["agent_rag"] = {"status": "disabled"}
            
            # === NOUVEAU: Configuration et environnement ===
            config_status = get_config_status()
            global_status["configuration"] = config_status
            
            # Digital Ocean info
            global_status["environment"] = {
                "platform": "digital_ocean",
                "app_name": DO_APP_NAME,
                "app_tier": DO_APP_TIER,
                "base_path": BASE_PATH
            }
            
            # Déterminer statut global final
            if global_status["warnings"]:
                if global_status["overall_status"] == "healthy":
                    global_status["overall_status"] = "healthy_with_warnings"
            
            return global_status
            
        except Exception as e:
            logger.error(f"Erreur health check: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": current_time
            }

health_monitor = SystemHealthMonitor()

# Clients OpenAI globaux avec validation
try:
    from imports_and_dependencies import get_openai_sync, get_openai_async
    openai_client_sync = get_openai_sync()
    openai_client_async = get_openai_async()
    logger.info("Clients OpenAI (sync + async) initialisés")
except Exception as e:
    logger.error(f"Erreur initialisation clients OpenAI: {e}")
    raise RuntimeError(f"Impossible d'initialiser les clients OpenAI: {e}")

# Mémoire de conversation (existante)
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

# === NOUVEAU: Collecteur de métriques enrichi ===
class MetricsCollector:
    """Collecteur de métriques avec support LangSmith et RRF"""
    
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
            # === NOUVEAU: Métriques LangSmith ===
            "langsmith_traces": 0,
            "langsmith_errors": 0,
            "hallucination_alerts": 0,
            # === NOUVEAU: Métriques RRF Intelligent ===
            "intelligent_rrf_queries": 0,
            "genetic_boosts_applied": 0,
            "rrf_learning_updates": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0,
        }
        self.recent_processing_times = []
        self.recent_confidences = []
        self.latency_percentiles = {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        self.max_recent_samples = 100
    
    def record_query(self, result, source_type: str = "unknown", endpoint_time: float = 0.0):
        """Enregistre les métriques avec support LangSmith et RRF"""
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
            
            # === NOUVEAU: Métriques LangSmith et RRF ===
            if hasattr(result, 'metadata') and result.metadata:
                try:
                    metadata = result.metadata
                    
                    # LangSmith
                    if metadata.get("langsmith", {}).get("traced"):
                        self.metrics["langsmith_traces"] += 1
                    
                    if metadata.get("alerts_aviculture"):
                        self.metrics["hallucination_alerts"] += 1
                    
                    # RRF Intelligent
                    if metadata.get("intelligent_rrf", {}).get("used"):
                        self.metrics["intelligent_rrf_queries"] += 1
                    
                    opt_stats = metadata.get("optimization_stats", {})
                    self.metrics["cache_hits"] += opt_stats.get("cache_hits", 0)
                    self.metrics["cache_misses"] += opt_stats.get("cache_misses", 0)
                    self.metrics["semantic_cache_hits"] += opt_stats.get("semantic_cache_hits", 0)
                    self.metrics["hybrid_searches"] += opt_stats.get("hybrid_searches", 0)
                    self.metrics["genetic_boosts_applied"] += opt_stats.get("genetic_boosts_applied", 0)
                    self.metrics["rrf_learning_updates"] += opt_stats.get("rrf_learning_updates", 0)
                    
                except Exception as e:
                    logger.debug(f"Erreur traitement métriques metadata: {e}")
            
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
        """Retourne les métriques enrichies avec protection contre les erreurs"""
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
                "latency_percentiles": self.latency_percentiles,
                # === NOUVEAU: Taux spécialisés ===
                "langsmith_usage_rate": self.metrics["langsmith_traces"] / total_queries,
                "rrf_intelligent_usage_rate": self.metrics["intelligent_rrf_queries"] / total_queries,
                "hallucination_alert_rate": self.metrics["hallucination_alerts"] / total_queries
            }
        except Exception as e:
            logger.error(f"Erreur calcul métriques: {e}")
            return self.metrics

metrics_collector = MetricsCollector()

# Helpers de streaming et fonctions utilitaires (inchangées)
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
                if i < len(remaining_text) and remaining_text[i] in '.!?:':
                    cut_point = i + 1
                    break
            
            # Sinon, couper sur un espace
            if cut_point == max_chunk_size:
                for i in range(max_chunk_size, max(max_chunk_size // 2, 0), -1):
                    if i < len(remaining_text) and remaining_text[i] == ' ':
                        cut_point = i
                        break
            
            chunks.append(remaining_text[:cut_point])
            remaining_text = remaining_text[cut_point:].lstrip()
        
        return chunks
        
    except Exception as e:
        logger.error(f"Erreur découpe texte: {e}")
        return [text[:max_chunk_size]] if text else []

def get_out_of_domain_message(lang: Optional[str] = None) -> str:
    """Messages out of domain multilingue"""
    OUT_OF_DOMAIN_MESSAGES = {
        "fr": "Désolé, cette question sort du domaine avicole. Pose-moi une question sur l'aviculture, l'élevage de volailles, la nutrition, la santé des oiseaux, ou les performances.",
        "en": "Sorry, this question is outside the poultry domain. Ask me about poultry farming, bird nutrition, health, or performance.",
        "es": "Lo siento, esta pregunta está fuera del dominio avícola. Pregúntame sobre avicultura, nutrición, salud o rendimiento de aves.",
        "default": "Questions outside poultry domain not supported. Ask about poultry farming, nutrition, health, or performance."
    }
    
    code = (lang or "").lower()
    msg = OUT_OF_DOMAIN_MESSAGES.get(code)
    if msg:
        return msg
    
    short = code.split("-")[0]
    return OUT_OF_DOMAIN_MESSAGES.get(short, OUT_OF_DOMAIN_MESSAGES.get("default", "Questions outside domain not supported."))

def detect_language(text: str, min_length: int = None) -> str:
    """Détection de langue avec fallback pattern"""
    min_length = min_length or LANG_DETECTION_MIN_LENGTH
    
    if len(text) < min_length:
        return 'fr'  # Défaut français pour textes courts
    
    try:
        # Tentative avec langdetect si disponible
        try:
            from langdetect import detect
            detected = detect(text)
            
            # Mapping normalisé
            lang_mapping = {
                'de': 'de',
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

# Gestion du cycle de vie de l'application (mise à jour avec nouveau monitoring)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie avec validation stricte et monitoring enrichi"""
    
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
                
                # Log statut des intégrations
                langsmith_status = validation_result.get("langsmith_validation", {})
                if langsmith_status.get("status") == "configured":
                    logger.info(f"🧠 LangSmith actif - Projet: {langsmith_status.get('project')}")
                
                rrf_status = validation_result.get("rrf_validation", {})
                if rrf_status.get("status") == "configured":
                    logger.info(f"⚡ RRF Intelligent actif - Learning: {rrf_status.get('learning_mode')}")
        
        else:
            logger.info("Validation startup désactivée")
            # Initialisation minimale
            await health_monitor._initialize_core_services()
        
        # Application prête
        logger.info(f"API disponible sur {BASE_PATH}")
        logger.info(f"Environment: DO App={DO_APP_NAME}, Tier={DO_APP_TIER}")
        
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
    description="API RAG Enhanced avec LangSmith et RRF Intelligent",
    version="4.0.0-langsmith-rrf",
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
    """Health check complet avec détails LangSmith et RRF"""
    try:
        health_status = await health_monitor.get_health_status()
        
        # Code de statut HTTP selon l'état
        if health_status["overall_status"] in ["healthy", "healthy_with_warnings"]:
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
    """Endpoint pour récupérer les métriques de performance enrichies"""
    try:
        base_metrics = {
            "application_metrics": metrics_collector.get_metrics(),
            "system_metrics": {
                "conversation_memory": {
                    "tenants": len(conversation_memory),
                    "max_tenants": MAX_TENANTS,
                    "ttl_seconds": TENANT_TTL
                }
            }
        }
        
        # === NOUVEAU: Métriques RAG Engine enrichies ===
        if rag_engine_enhanced and rag_engine_enhanced.is_initialized:
            rag_status = rag_engine_enhanced.get_status()
            
            base_metrics["rag_engine"] = {
                "approach": rag_status.get("approach", "unknown"),
                "optimizations": rag_status.get("optimizations", {}),
                "langsmith": rag_status.get("langsmith", {}),
                "intelligent_rrf": rag_status.get("intelligent_rrf", {}),
                "optimization_stats": rag_status.get("optimization_stats", {}),
                "weaviate_capabilities": rag_status.get("api_capabilities", {})
            }
        
        # Cache stats externe
        if cache_core and getattr(cache_core, 'initialized', False):
            cache_stats = cache_core.get_stats() if hasattr(cache_core, 'get_stats') else {}
            base_metrics["cache"] = cache_stats
        
        return base_metrics
        
    except Exception as e:
        logger.error(f"Erreur récupération métriques: {e}")
        return {"error": str(e), "timestamp": time.time()}

# === NOUVEAU: Endpoint configuration ===
@router.get(f"{BASE_PATH}/status/configuration")
async def configuration_status():
    """Statut détaillé de la configuration"""
    try:
        config_status = get_config_status()
        
        # Enrichir avec informations runtime
        config_status["runtime"] = {
            "environment_variables": {
                "langsmith_enabled": LANGSMITH_ENABLED,
                "rrf_enabled": ENABLE_INTELLIGENT_RRF,
                "cache_enabled": CACHE_ENABLED,
                "rag_enabled": RAG_ENABLED
            },
            "digital_ocean": {
                "app_name": DO_APP_NAME,
                "app_tier": DO_APP_TIER,
                "base_path": BASE_PATH
            }
        }
        
        return config_status
        
    except Exception as e:
        return {"error": str(e)}

# Inclusion du router dans l'app
app.include_router(router)

# Démarrage de l'application
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Démarrage serveur sur {host}:{port}")
    logger.info(f"LangSmith: {LANGSMITH_ENABLED}, RRF: {ENABLE_INTELLIGENT_RRF}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Désactivé en production
        log_level="info"
    )