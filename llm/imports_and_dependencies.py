# -*- coding: utf-8 -*-
"""
imports_and_dependencies.py - Gestion centralisée des imports conditionnels
"""

import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

def require(cond: bool, name: str) -> None:
    """
    Loggue un warning bloquant quand une fonctionnalité critique est absente.
    N'élève pas d'exception à l'import, mais rend le statut visible au boot.
    """
    if not cond:
        logger.warning("⚠️ Required dependency or feature is unavailable: %s", name)

# === IMPORTS CONDITIONNELS ===
try:
    import weaviate
    weaviate_version = getattr(weaviate, '__version__', '4.0.0')
    if weaviate_version.startswith('4.'):
        try:
            import weaviate.classes as wvc
            import weaviate.classes.query as wvc_query
            WEAVIATE_V4 = True
        except ImportError:
            wvc = None
            wvc_query = None
            WEAVIATE_V4 = False
    else:
        WEAVIATE_V4 = False
        wvc = None
        wvc_query = None
    WEAVIATE_AVAILABLE = True
    logger.info(f"Weaviate {weaviate_version} détecté (V4: {WEAVIATE_V4})")
except ImportError as e:
    WEAVIATE_AVAILABLE = False
    WEAVIATE_V4 = False
    wvc = None
    wvc_query = None
    weaviate = None
    logger.error(f"Weaviate non disponible: {e}")

try:
    from openai import AsyncOpenAI, OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    logger.error(f"OpenAI non disponible: {e}")

try:
    import redis.asyncio as redis
    import hiredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    logger.warning("Redis non disponible - cache désactivé")

try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    logger.warning("VoyageAI non disponible")

try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("SentenceTransformers non disponible")

try:
    from unidecode import unidecode
    UNIDECODE_AVAILABLE = True
except ImportError:
    UNIDECODE_AVAILABLE = False
    logger.warning("Unidecode non disponible")

try:
    from intent_processor import create_intent_processor, IntentType, IntentResult
    INTENT_PROCESSOR_AVAILABLE = True
except ImportError as e:
    INTENT_PROCESSOR_AVAILABLE = False
    logger.warning(f"Intent processor non disponible: {e}")
    
    class IntentType:
        METRIC_QUERY = "metric_query"
        OUT_OF_DOMAIN = "out_of_domain"
    
    class IntentResult:
        def __init__(self):
            self.intent_type = IntentType.METRIC_QUERY
            self.confidence = 0.8
            self.detected_entities = {}
            self.expanded_query = ""
            self.metadata = {}
            self.confidence_breakdown = {}

try:
    from advanced_guardrails import create_response_guardrails, VerificationLevel, GuardrailResult
    GUARDRAILS_AVAILABLE = True
except ImportError as e:
    GUARDRAILS_AVAILABLE = False
    logger.warning(f"Advanced guardrails non disponible: {e}")
    
    class VerificationLevel:
        MINIMAL = "minimal"
        STANDARD = "standard"
        STRICT = "strict"
        CRITICAL = "critical"
    
    class GuardrailResult:
        def __init__(self):
            self.is_valid = True
            self.confidence = 0.8
            self.violations = []
            self.warnings = []
            self.evidence_support = 0.8
            self.hallucination_risk = 0.2
            self.correction_suggestions = []
            self.metadata = {}

# IMPORT DU CACHE EXTERNE OPTIMISÉ
try:
    from redis_cache_manager import RAGCacheManager
    EXTERNAL_CACHE_AVAILABLE = True
    logger.info("Cache Redis externe importé avec succès")
except ImportError as e:
    EXTERNAL_CACHE_AVAILABLE = False
    logger.warning(f"Cache Redis externe non disponible: {e}")
    
    class RAGCacheManager:
        def __init__(self, *args, **kwargs):
            self.enabled = False
            self.ENABLE_SEMANTIC_CACHE = False
        
        async def initialize(self):
            pass
        
        async def get_embedding(self, text: str):
            return None
        
        async def set_embedding(self, text: str, embedding: list):
            pass
        
        async def get_response(self, query: str, context_hash: str, language: str = "fr"):
            return None
        
        async def set_response(self, query: str, context_hash: str, response: str, language: str = "fr"):
            pass
        
        def generate_context_hash(self, documents: list) -> str:
            return "fallback_hash"
        
        async def get_cache_stats(self):
            return {"enabled": False, "semantic_enhancements": {}}
        
        async def debug_semantic_extraction(self, query: str):
            return {"extracted_keywords": [], "cache_keys": {}}
        
        def _normalize_text(self, text: str) -> str:
            return text.lower()
        
        async def cleanup(self):
            pass

def quick_connectivity_check(redis_client=None, weaviate_client=None) -> Dict[str, bool]:
    """
    Vérifie rapidement la connectivité aux services externes.
    Retourne un dictionnaire avec le statut de chaque service.
    """
    ok = {"redis": False, "weaviate": False}
    
    # Test Redis
    try:
        if redis_client and REDIS_AVAILABLE:
            # Pour redis.asyncio, utiliser ping() de manière synchrone si possible
            # Sinon, on assume que le client est disponible
            if hasattr(redis_client, 'ping'):
                redis_client.ping()
            ok["redis"] = True
    except Exception as e:
        logger.debug(f"Redis connectivity check failed: {e}")
        pass
    
    # Test Weaviate
    try:
        if weaviate_client and WEAVIATE_AVAILABLE:
            if WEAVIATE_V4:
                # Weaviate v4
                weaviate_client.is_ready()
            else:
                # Weaviate v3 ou antérieur
                weaviate_client.is_ready()
            ok["weaviate"] = True
    except Exception as e:
        logger.debug(f"Weaviate connectivity check failed: {e}")
        pass
    
    return ok

# Fonction pour obtenir les informations sur les dépendances
def get_dependencies_status():
    """Retourne le statut de toutes les dépendances"""
    status = {
        "openai": OPENAI_AVAILABLE,
        "weaviate": WEAVIATE_AVAILABLE,
        "weaviate_v4": WEAVIATE_V4,
        "weaviate_version": weaviate_version if WEAVIATE_AVAILABLE else "N/A",
        "redis": REDIS_AVAILABLE,
        "external_cache": EXTERNAL_CACHE_AVAILABLE,
        "voyage": VOYAGE_AVAILABLE,
        "sentence_transformers": SENTENCE_TRANSFORMERS_AVAILABLE,
        "unidecode": UNIDECODE_AVAILABLE,
        "intent_processor": INTENT_PROCESSOR_AVAILABLE,
        "guardrails": GUARDRAILS_AVAILABLE
    }
    
    # Vérifications des dépendances critiques
    require(OPENAI_AVAILABLE, "OpenAI API client")
    require(WEAVIATE_AVAILABLE, "Weaviate vector database")
    require(REDIS_AVAILABLE or not EXTERNAL_CACHE_AVAILABLE, "Redis cache (if external cache enabled)")
    
    return status