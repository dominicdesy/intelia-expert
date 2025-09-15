# -*- coding: utf-8 -*-
"""
config.py - Configuration centralisée avec support LangSmith et RRF Intelligent
Optimisé pour Digital Ocean App Platform
"""

import os
from typing import Optional

# ===== CONFIGURATION CORE =====
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
EXTERNAL_CACHE_AVAILABLE = os.getenv("EXTERNAL_CACHE_AVAILABLE", "true").lower() == "true"

# ===== API KEYS =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ===== NOUVEAU: LANGSMITH CONFIGURATION =====
LANGSMITH_ENABLED = os.getenv("LANGSMITH_ENABLED", "true").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "intelia-aviculture")
LANGSMITH_ENVIRONMENT = os.getenv("LANGSMITH_ENVIRONMENT", "production")

# Validation LangSmith
if LANGSMITH_ENABLED and not LANGSMITH_API_KEY:
    import logging
    logging.getLogger(__name__).warning("LangSmith activé mais LANGSMITH_API_KEY manquante")

# ===== NOUVEAU: RRF INTELLIGENT CONFIGURATION =====
ENABLE_INTELLIGENT_RRF = os.getenv("ENABLE_INTELLIGENT_RRF", "false").lower() == "true"
RRF_LEARNING_MODE = os.getenv("RRF_LEARNING_MODE", "true").lower() == "true"
RRF_GENETIC_BOOST = os.getenv("RRF_GENETIC_BOOST", "true").lower() == "true"
RRF_DEBUG_MODE = os.getenv("RRF_DEBUG_MODE", "false").lower() == "true"

# Paramètres RRF tunables
RRF_BASE_K = int(os.getenv("RRF_BASE_K", "60"))
RRF_GENETIC_BOOST_FACTOR = float(os.getenv("RRF_GENETIC_BOOST_FACTOR", "1.3"))
RRF_LEARNING_DECAY = float(os.getenv("RRF_LEARNING_DECAY", "0.95"))
RRF_CACHE_SIZE = int(os.getenv("RRF_CACHE_SIZE", "1000"))

# ===== CONFIGURATION RAG =====
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "15"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.1"))
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "8"))
RAG_VERIFICATION_ENABLED = os.getenv("RAG_VERIFICATION_ENABLED", "true").lower() == "true"
RAG_VERIFICATION_SMART = os.getenv("RAG_VERIFICATION_SMART", "true").lower() == "true"

# ===== HYBRID SEARCH =====
HYBRID_SEARCH_ENABLED = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
DEFAULT_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.6"))

# ===== OOD DETECTION =====
OOD_MIN_SCORE = float(os.getenv("OOD_MIN_SCORE", "0.3"))
OOD_STRICT_SCORE = float(os.getenv("OOD_STRICT_SCORE", "0.6"))

# ===== GUARDRAILS =====
GUARDRAILS_AVAILABLE = os.getenv("GUARDRAILS_AVAILABLE", "true").lower() == "true"
GUARDRAILS_LEVEL = os.getenv("GUARDRAILS_LEVEL", "standard")

# ===== ENTITY ENRICHMENT =====
ENTITY_ENRICHMENT_ENABLED = os.getenv("ENTITY_ENRICHMENT_ENABLED", "true").lower() == "true"

# ===== API DIAGNOSTICS =====
ENABLE_API_DIAGNOSTICS = os.getenv("ENABLE_API_DIAGNOSTICS", "true").lower() == "true"

# ===== CONVERSATION MEMORY =====
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "6"))

# ===== LANGUAGE DETECTION =====
LANG_DETECTION_MIN_LENGTH = int(os.getenv("LANG_DETECTION_MIN_LENGTH", "20"))

# ===== LOGGING =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ===== PERFORMANCE MONITORING =====
ENABLE_PERFORMANCE_MONITORING = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
METRICS_EXPORT_INTERVAL = int(os.getenv("METRICS_EXPORT_INTERVAL", "60"))

# ===== DIGITAL OCEAN SPECIFIC =====
# Ces variables sont automatiquement disponibles sur DO App Platform
DO_APP_NAME = os.getenv("DO_APP_NAME", "intelia-expert")
DO_APP_TIER = os.getenv("DO_APP_TIER", "basic")

# Configuration dynamique selon l'environnement DO
if DO_APP_TIER == "professional":
    # Configuration optimisée pour tier professionnel
    RAG_SIMILARITY_TOP_K = 20
    RRF_CACHE_SIZE = 2000
    ENABLE_INTELLIGENT_RRF = True
elif DO_APP_TIER == "basic":
    # Configuration conservatrice pour tier basic
    RAG_SIMILARITY_TOP_K = 12
    RRF_CACHE_SIZE = 500
    ENABLE_INTELLIGENT_RRF = False

# ===== VALIDATION CONFIGURATION =====
def validate_config() -> tuple[bool, list[str]]:
    """Valide la configuration et retourne (is_valid, errors)"""
    errors = []
    
    # Validation clés critiques
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY manquante")
    
    if LANGSMITH_ENABLED and not LANGSMITH_API_KEY:
        errors.append("LangSmith activé mais LANGSMITH_API_KEY manquante")
    
    # Validation valeurs numériques
    if RAG_SIMILARITY_TOP_K <= 0:
        errors.append("RAG_SIMILARITY_TOP_K doit être > 0")
    
    if not (0.0 <= DEFAULT_ALPHA <= 1.0):
        errors.append("HYBRID_ALPHA doit être entre 0.0 et 1.0")
    
    return len(errors) == 0, errors

# ===== STATUS REPORTING =====
def get_config_status() -> dict:
    """Retourne le statut de la configuration"""
    is_valid, errors = validate_config()
    
    return {
        "valid": is_valid,
        "errors": errors,
        "langsmith": {
            "enabled": LANGSMITH_ENABLED,
            "configured": bool(LANGSMITH_API_KEY),
            "project": LANGSMITH_PROJECT
        },
        "rrf_intelligent": {
            "enabled": ENABLE_INTELLIGENT_RRF,
            "learning_mode": RRF_LEARNING_MODE,
            "genetic_boost": RRF_GENETIC_BOOST,
            "debug_mode": RRF_DEBUG_MODE
        },
        "environment": {
            "do_app_name": DO_APP_NAME,
            "do_app_tier": DO_APP_TIER,
            "cache_enabled": CACHE_ENABLED,
            "rag_enabled": RAG_ENABLED
        }
    }

# ===== EXPORTATION POUR COMPATIBILITÉ =====
__all__ = [
    # Core
    "RAG_ENABLED", "CACHE_ENABLED", "EXTERNAL_CACHE_AVAILABLE",
    # API Keys
    "OPENAI_API_KEY", "WEAVIATE_URL", "REDIS_URL",
    # LangSmith
    "LANGSMITH_ENABLED", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT",
    # RRF Intelligent
    "ENABLE_INTELLIGENT_RRF", "RRF_LEARNING_MODE", "RRF_GENETIC_BOOST",
    # RAG Config
    "RAG_SIMILARITY_TOP_K", "RAG_CONFIDENCE_THRESHOLD", "HYBRID_SEARCH_ENABLED",
    # Fonctions
    "validate_config", "get_config_status"
]