# -*- coding: utf-8 -*-
"""
config.py - Configuration centralisée avec support multilingue
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
config.py - Configuration centralisée avec support multilingue
OptimisÉ pour Digital Ocean App Platform
Version multilingue: Support 13 langues + service traduction hybride
Updated: 2025-10-24 - Image storage + TTS voice responses
"""

import os

# ===== CONFIGURATION CORE =====
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
EXTERNAL_CACHE_AVAILABLE = (
    os.getenv("EXTERNAL_CACHE_AVAILABLE", "true").lower() == "true"
)

# ===== API KEYS =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ===== LANGSMITH CONFIGURATION =====
LANGSMITH_ENABLED = os.getenv("LANGSMITH_ENABLED", "true").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "intelia-aviculture")
LANGSMITH_ENVIRONMENT = os.getenv("LANGSMITH_ENVIRONMENT", "production")

# Validation LangSmith
if LANGSMITH_ENABLED and not LANGSMITH_API_KEY:
    import logging

    logging.getLogger(__name__).warning(
        "LangSmith activé mais LANGSMITH_API_KEY manquante"
    )

# ===== NOUVEAU: CONFIGURATION MULTILINGUE =====
# Langues supportées (12 langues ISO 639-1) - Seulement celles avec dictionnaires
SUPPORTED_LANGUAGES = {
    # "ar",  # Arabe - dictionnaire manquant
    "de",  # Allemand
    "en",  # Anglais
    "es",  # Espagnol
    "fr",  # Français
    "hi",  # Hindi
    "id",  # Indonésien
    "it",  # Italien
    # "ja",  # Japonais - dictionnaire manquant
    "nl",  # Néerlandais
    "pl",  # Polonais
    "pt",  # Portugais
    "th",  # Thaï
    # "tr",  # Turc - dictionnaire manquant
    # "vi",  # Vietnamien - dictionnaire manquant
    "zh",  # Chinois
}
DEFAULT_LANGUAGE = "fr"
FALLBACK_LANGUAGE = "en"

# Dictionnaire universel
UNIVERSAL_DICT_PATH = os.getenv("UNIVERSAL_DICT_PATH", "config")

# Google Translation API
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
ENABLE_GOOGLE_TRANSLATE_FALLBACK = (
    os.getenv("ENABLE_GOOGLE_TRANSLATE_FALLBACK", "false").lower() == "true"
)
TRANSLATION_CONFIDENCE_THRESHOLD = float(
    os.getenv("TRANSLATION_CONFIDENCE_THRESHOLD", "0.7")
)
GOOGLE_TRANSLATE_MAX_RETRIES = int(os.getenv("GOOGLE_TRANSLATE_MAX_RETRIES", "3"))
GOOGLE_TRANSLATE_TIMEOUT = int(os.getenv("GOOGLE_TRANSLATE_TIMEOUT", "10"))

# Language detection configuration (using fasttext-langdetect + langdetect)
LANG_DETECTION_MIN_LENGTH = int(os.getenv("LANG_DETECTION_MIN_LENGTH", "15"))
LANG_DETECTION_CONFIDENCE_THRESHOLD = float(
    os.getenv("LANG_DETECTION_CONFIDENCE_THRESHOLD", "0.8")
)

# Cache traductions multilingues
TRANSLATION_CACHE_SIZE = int(os.getenv("TRANSLATION_CACHE_SIZE", "10000"))
TRANSLATION_CACHE_TTL = int(os.getenv("TRANSLATION_CACHE_TTL", "86400"))  # 24h
MULTILINGUAL_CACHE_ENABLED = (
    os.getenv("MULTILINGUAL_CACHE_ENABLED", "true").lower() == "true"
)

# Debug et monitoring multilingue
TRANSLATION_DEBUG = os.getenv("TRANSLATION_DEBUG", "false").lower() == "true"
ENABLE_TRANSLATION_METRICS = (
    os.getenv("ENABLE_TRANSLATION_METRICS", "true").lower() == "true"
)

# ===== RRF INTELLIGENT CONFIGURATION =====
# PHASE 1 OPTIMIZATION: RRF Intelligent activé pour améliorer Faithfulness
ENABLE_INTELLIGENT_RRF = os.getenv("ENABLE_INTELLIGENT_RRF", "true").lower() == "true"
RRF_LEARNING_MODE = os.getenv("RRF_LEARNING_MODE", "true").lower() == "true"
RRF_GENETIC_BOOST = os.getenv("RRF_GENETIC_BOOST", "true").lower() == "true"
RRF_DEBUG_MODE = os.getenv("RRF_DEBUG_MODE", "false").lower() == "true"

# Paramètres RRF
RRF_CACHE_SIZE = int(os.getenv("RRF_CACHE_SIZE", "1000"))
RRF_BASE_K = int(os.getenv("RRF_BASE_K", "60"))

# ===== RAG CONFIGURATION =====
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "15"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.55"))
RAG_VERIFICATION_ENABLED = (
    os.getenv("RAG_VERIFICATION_ENABLED", "true").lower() == "true"
)
RAG_VERIFICATION_SMART = os.getenv("RAG_VERIFICATION_SMART", "true").lower() == "true"
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "8"))

# Recherche hybride
HYBRID_SEARCH_ENABLED = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
DEFAULT_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.6"))

# ===== EXTERNAL SOURCES CONFIGURATION =====
# Query-driven document ingestion from external scientific sources
ENABLE_EXTERNAL_SOURCES = os.getenv("ENABLE_EXTERNAL_SOURCES", "true").lower() == "true"
EXTERNAL_SEARCH_THRESHOLD = float(os.getenv("EXTERNAL_SEARCH_THRESHOLD", "0.7"))
EXTERNAL_SOURCES_LOG_DIR = os.getenv("EXTERNAL_SOURCES_LOG_DIR", "/app/logs/external_sources")

# External sources settings
EXTERNAL_SOURCES_ENABLED_BY_DEFAULT = True  # Auto-enable if Weaviate available
EXTERNAL_SOURCES_PARALLEL_SEARCH = True  # Search all sources simultaneously
EXTERNAL_SOURCES_MAX_RESULTS_PER_SOURCE = int(os.getenv("EXTERNAL_SOURCES_MAX_RESULTS_PER_SOURCE", "5"))
EXTERNAL_SOURCES_MIN_YEAR = int(os.getenv("EXTERNAL_SOURCES_MIN_YEAR", "2015"))

# Individual source toggles
ENABLE_SEMANTIC_SCHOLAR = os.getenv("ENABLE_SEMANTIC_SCHOLAR", "true").lower() == "true"
ENABLE_PUBMED = os.getenv("ENABLE_PUBMED", "true").lower() == "true"
ENABLE_EUROPE_PMC = os.getenv("ENABLE_EUROPE_PMC", "true").lower() == "true"
ENABLE_FAO = os.getenv("ENABLE_FAO", "false").lower() == "true"  # Placeholder only

# Optional API keys
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY")  # Optional: increases rate limit

# ===== CACHE CONFIGURATION =====
CACHE_TOTAL_MEMORY_LIMIT_MB = int(os.getenv("CACHE_TOTAL_MEMORY_LIMIT_MB", "150"))
CACHE_VALUE_MAX_SIZE_KB = int(os.getenv("CACHE_VALUE_MAX_SIZE_KB", "200"))
CACHE_ENABLE_COMPRESSION = (
    os.getenv("CACHE_ENABLE_COMPRESSION", "true").lower() == "true"
)

# Cache sémantique
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true"
SEMANTIC_CACHE_SIMILARITY_THRESHOLD = float(
    os.getenv("SEMANTIC_CACHE_SIMILARITY_THRESHOLD", "0.92")
)

# ===== GUARDRAILS ET SÉCURITÉ =====
GUARDRAILS_LEVEL = os.getenv("GUARDRAILS_LEVEL", "strict")
GUARDRAILS_AVAILABLE = True  # Toujours disponible en mode basique

# OOD Detection
OOD_MIN_SCORE = float(os.getenv("OOD_MIN_SCORE", "0.4"))
OOD_STRICT_SCORE = float(os.getenv("OOD_STRICT_SCORE", "0.7"))

# ===== ENRICHISSEMENTS ET FONCTIONNALITÉS =====
ENTITY_ENRICHMENT_ENABLED = (
    os.getenv("ENTITY_ENRICHMENT_ENABLED", "true").lower() == "true"
)
ENABLE_API_DIAGNOSTICS = os.getenv("ENABLE_API_DIAGNOSTICS", "false").lower() == "true"

# ===== CONSTANTES SYSTÈME =====
BASE_PATH = os.getenv("BASE_PATH", "")
ALLOWED_ORIGINS = (
    os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if os.getenv("ALLOWED_ORIGINS") != "*"
    else ["*"]
)
STARTUP_TIMEOUT = int(os.getenv("STARTUP_TIMEOUT", "30"))
TENANT_TTL = int(os.getenv("TENANT_TTL", "3600"))
MAX_TENANTS = int(os.getenv("MAX_TENANTS", "100"))
STREAM_CHUNK_LEN = int(os.getenv("STREAM_CHUNK_LEN", "8"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "16384"))  # 16KB par défaut
ENABLE_METRICS_LOGGING = os.getenv("ENABLE_METRICS_LOGGING", "true").lower() == "true"

# ===== ENTITY_CONTEXTS - CONFIGURATION CRITIQUE =====
ENTITY_CONTEXTS = {
    "line": {
        "ross 308": "lignée à croissance rapide, optimisée pour le rendement carcasse et FCR",
        "ross 708": "lignée à croissance très rapide, développée pour l'efficacité maximale",
        "ross": "lignée à croissance rapide, optimisée pour le rendement carcasse",
        "cobb 500": "lignée équilibrée performance/robustesse, bonne conversion alimentaire",
        "cobb 700": "lignée haute performance, optimisée pour les conditions difficiles",
        "cobb 400": "lignée rustique, adaptée aux conditions d'élevage extensives",
        "cobb": "lignée équilibrée performance/robustesse, bonne conversion alimentaire",
        "hubbard classic": "lignée rustique, adaptée à l'élevage extensif et labels qualité",
        "hubbard flex": "lignée polyvalente, bon compromis croissance/robustesse",
        "hubbard": "lignée rustique, adaptée à l'élevage extensif et labels qualité",
        "isa brown": "lignée ponte brune, excellente production d'œufs colorés",
        "isa white": "lignée ponte blanche, optimisée pour l'efficacité alimentaire",
        "isa": "lignée ponte, optimisée pour la production d'œufs",
        "lohmann brown": "lignée ponte brune, excellence en persistance de ponte",
        "lohmann white": "lignée ponte blanche, très bonne conversion alimentaire",
        "lohmann": "lignée ponte, excellence en persistance de ponte",
        "hy-line brown": "lignée ponte brune, robustesse et adaptabilité",
        "hy-line white": "lignée ponte blanche, production intensive",
        "hy-line": "lignée ponte polyvalente, bonne adaptabilité",
    },
    "species": {
        "broiler": "poulet de chair, objectifs: poids vif, FCR, rendement carcasse",
        "layer": "poule pondeuse, objectifs: intensité de ponte, qualité œuf, persistance",
        "breeder": "reproducteur, objectifs: fertilité, éclosabilité, viabilité descendance",
        "pullet": "poulette, phase d'élevage avant la ponte",
        "chick": "poussin, phase critique des premiers jours",
    },
    "phase": {
        "starter": "phase démarrage (0-10j), croissance critique, thermorégulation",
        "grower": "phase croissance (11-24j), développement squelettique et musculaire",
        "finisher": "phase finition (25j+), optimisation du poids final et FCR",
        "laying": "phase ponte, maintien de la production et qualité œuf",
        "breeding": "phase reproduction, optimisation fertilité et éclosabilité",
    },
    "site_type": {
        "broiler_farm": "élevage poulets de chair, focus performance et conversion",
        "layer_farm": "élevage pondeuses, focus production œufs",
        "rearing_farm": "élevage poulettes, préparation à la ponte",
        "breeding_farm": "élevage reproducteurs, focus fertilité",
        "hatchery": "couvoir, incubation et éclosion",
        "feed_mill": "usine d'aliments, nutrition animale",
    },
    "environment": {
        "tunnel": "ventilation tunnel, contrôle précis température et humidité",
        "natural": "ventilation naturelle, dépendante des conditions extérieures",
        "mechanical": "ventilation mécanique, contrôle intermédiaire",
    },
}

# ===== DOMAINES KEYWORDS POUR OOD (MULTILINGUE) =====
DOMAIN_KEYWORDS = [
    # Français - Aviculture core
    "poule",
    "poulet",
    "poussin",
    "coq",
    "volaille",
    "ponte",
    "œuf",
    "œufs",
    # Anglais - Aviculture core
    "chicken",
    "hen",
    "rooster",
    "chick",
    "poultry",
    "egg",
    "eggs",
    "laying",
    # Français - Équipements
    "mangeoire",
    "abreuvoir",
    "poulailler",
    "perchoir",
    "pondoir",
    # Anglais - Équipements
    "feeder",
    "waterer",
    "coop",
    "roost",
    "nest",
    "housing",
    # Français - Santé
    "maladie",
    "vaccin",
    "vermifuge",
    "parasites",
    "stress",
    "picage",
    "plumage",
    # Anglais - Santé
    "disease",
    "vaccine",
    "dewormer",
    "parasites",
    "stress",
    "pecking",
    "feather",
    # Français - Production
    "production",
    "incubation",
    "éclosion",
    "couveuse",
    # Anglais - Production
    "production",
    "incubation",
    "hatching",
    "incubator",
    # Français - Nutrition
    "protéine",
    "calcium",
    "grain",
    "maïs",
    "blé",
    "soja",
    "vitamines",
    # Anglais - Nutrition
    "protein",
    "calcium",
    "grain",
    "corn",
    "wheat",
    "soy",
    "vitamins",
]

# ===== LOGGING =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ===== PERFORMANCE MONITORING =====
ENABLE_PERFORMANCE_MONITORING = (
    os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
)
METRICS_EXPORT_INTERVAL = int(os.getenv("METRICS_EXPORT_INTERVAL", "60"))

# ===== DIGITAL OCEAN SPECIFIC =====
DO_APP_NAME = os.getenv("DO_APP_NAME", "intelia-expert")
DO_APP_TIER = os.getenv("DO_APP_TIER", "basic")

# Configuration dynamique selon l'environnement DO
if DO_APP_TIER == "professional":
    RAG_SIMILARITY_TOP_K = 135  # INCREASED: Was 120, now 135 (sweet spot: performance vs latency)
    RRF_CACHE_SIZE = 2000
elif DO_APP_TIER == "basic":
    RAG_SIMILARITY_TOP_K = 135  # INCREASED: Was 120, now 135 (sweet spot: performance vs latency)
    RRF_CACHE_SIZE = 500


# ===== VALIDATION CONFIGURATION =====
def validate_config() -> tuple[bool, list[str]]:
    """Valide la configuration et retourne (is_valid, errors)"""
    errors = []

    # Validation clés critiques
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY manquante")

    if LANGSMITH_ENABLED and not LANGSMITH_API_KEY:
        errors.append("LangSmith activé mais LANGSMITH_API_KEY manquante")

    # Validation multilingue
    if ENABLE_GOOGLE_TRANSLATE_FALLBACK and not GOOGLE_TRANSLATE_API_KEY:
        errors.append("Google Translate activé mais GOOGLE_TRANSLATE_API_KEY manquante")

    if not UNIVERSAL_DICT_PATH:
        errors.append("UNIVERSAL_DICT_PATH manquant")

    # Validation valeurs numériques
    if RAG_SIMILARITY_TOP_K <= 0:
        errors.append("RAG_SIMILARITY_TOP_K doit être > 0")

    if not (0.0 <= DEFAULT_ALPHA <= 1.0):
        errors.append("HYBRID_ALPHA doit être entre 0.0 et 1.0")

    if not (0.0 <= RAG_CONFIDENCE_THRESHOLD <= 1.0):
        errors.append("RAG_CONFIDENCE_THRESHOLD doit être entre 0.0 et 1.0")

    if not (0.0 <= SEMANTIC_CACHE_SIMILARITY_THRESHOLD <= 1.0):
        errors.append("SEMANTIC_CACHE_SIMILARITY_THRESHOLD doit être entre 0.0 et 1.0")

    if not (0.0 <= TRANSLATION_CONFIDENCE_THRESHOLD <= 1.0):
        errors.append("TRANSLATION_CONFIDENCE_THRESHOLD doit être entre 0.0 et 1.0")

    if not (0.0 <= LANG_DETECTION_CONFIDENCE_THRESHOLD <= 1.0):
        errors.append("LANG_DETECTION_CONFIDENCE_THRESHOLD doit être entre 0.0 et 1.0")

    # Validation guardrails
    if GUARDRAILS_LEVEL not in ["strict", "moderate", "permissive"]:
        errors.append("GUARDRAILS_LEVEL doit être: strict, moderate, ou permissive")

    return len(errors) == 0, errors


def validate_language_code(lang_code: str) -> bool:
    """Valide qu'un code langue est supporté"""
    return lang_code in SUPPORTED_LANGUAGES


def get_supported_languages_info() -> dict:
    """Retourne les informations sur les langues supportées"""
    return {
        "count": len(SUPPORTED_LANGUAGES),
        "languages": list(SUPPORTED_LANGUAGES),
        "default": DEFAULT_LANGUAGE,
        "fallback": FALLBACK_LANGUAGE,
        "google_translate_enabled": ENABLE_GOOGLE_TRANSLATE_FALLBACK,
        "fasttext_langdetect_enabled": True,  # Using fasttext-langdetect package
    }


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
            "project": LANGSMITH_PROJECT,
        },
        "multilingual": {
            "enabled": True,
            "supported_languages": list(SUPPORTED_LANGUAGES),
            "google_translate": {
                "enabled": ENABLE_GOOGLE_TRANSLATE_FALLBACK,
                "configured": bool(GOOGLE_TRANSLATE_API_KEY),
                "confidence_threshold": TRANSLATION_CONFIDENCE_THRESHOLD,
            },
            "language_detection": {
                "library": "fasttext-langdetect",
                "fallback": "langdetect",
                "min_length": LANG_DETECTION_MIN_LENGTH,
                "confidence_threshold": LANG_DETECTION_CONFIDENCE_THRESHOLD,
            },
            "cache": {
                "enabled": MULTILINGUAL_CACHE_ENABLED,
                "size": TRANSLATION_CACHE_SIZE,
                "ttl_hours": TRANSLATION_CACHE_TTL // 3600,
            },
        },
        "rrf_intelligent": {
            "enabled": ENABLE_INTELLIGENT_RRF,
            "learning_mode": RRF_LEARNING_MODE,
            "genetic_boost": RRF_GENETIC_BOOST,
            "debug_mode": RRF_DEBUG_MODE,
        },
        "entity_contexts": {
            "lines_count": len(ENTITY_CONTEXTS["line"]),
            "species_count": len(ENTITY_CONTEXTS["species"]),
            "phases_count": len(ENTITY_CONTEXTS["phase"]),
            "site_types_count": len(ENTITY_CONTEXTS["site_type"]),
            "environments_count": len(ENTITY_CONTEXTS["environment"]),
        },
        "environment": {
            "do_app_name": DO_APP_NAME,
            "do_app_tier": DO_APP_TIER,
            "cache_enabled": CACHE_ENABLED,
            "rag_enabled": RAG_ENABLED,
        },
    }


# ===== EXPORTATION POUR COMPATIBILITÉ =====
__all__ = [
    # Core
    "RAG_ENABLED",
    "CACHE_ENABLED",
    "EXTERNAL_CACHE_AVAILABLE",
    # API Keys
    "OPENAI_API_KEY",
    "WEAVIATE_URL",
    "REDIS_URL",
    # LangSmith
    "LANGSMITH_ENABLED",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGSMITH_ENVIRONMENT",
    # Multilingue - NOUVEAU
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "FALLBACK_LANGUAGE",
    "UNIVERSAL_DICT_PATH",
    "GOOGLE_TRANSLATE_API_KEY",
    "ENABLE_GOOGLE_TRANSLATE_FALLBACK",
    "TRANSLATION_CONFIDENCE_THRESHOLD",
    "GOOGLE_TRANSLATE_MAX_RETRIES",
    "GOOGLE_TRANSLATE_TIMEOUT",
    "LANG_DETECTION_MIN_LENGTH",
    "LANG_DETECTION_CONFIDENCE_THRESHOLD",
    "TRANSLATION_CACHE_SIZE",
    "TRANSLATION_CACHE_TTL",
    "MULTILINGUAL_CACHE_ENABLED",
    "TRANSLATION_DEBUG",
    "ENABLE_TRANSLATION_METRICS",
    # RRF Intelligent
    "ENABLE_INTELLIGENT_RRF",
    "RRF_LEARNING_MODE",
    "RRF_GENETIC_BOOST",
    "RRF_DEBUG_MODE",
    "RRF_CACHE_SIZE",
    "RRF_BASE_K",
    # RAG Config
    "RAG_SIMILARITY_TOP_K",
    "RAG_CONFIDENCE_THRESHOLD",
    "RAG_VERIFICATION_ENABLED",
    "RAG_VERIFICATION_SMART",
    "HYBRID_SEARCH_ENABLED",
    "DEFAULT_ALPHA",
    "MAX_CONVERSATION_CONTEXT",
    # External Sources
    "ENABLE_EXTERNAL_SOURCES",
    "EXTERNAL_SEARCH_THRESHOLD",
    "EXTERNAL_SOURCES_LOG_DIR",
    "EXTERNAL_SOURCES_ENABLED_BY_DEFAULT",
    "EXTERNAL_SOURCES_PARALLEL_SEARCH",
    "EXTERNAL_SOURCES_MAX_RESULTS_PER_SOURCE",
    "EXTERNAL_SOURCES_MIN_YEAR",
    "ENABLE_SEMANTIC_SCHOLAR",
    "ENABLE_PUBMED",
    "ENABLE_EUROPE_PMC",
    "ENABLE_FAO",
    "PUBMED_API_KEY",
    # Cache
    "CACHE_TOTAL_MEMORY_LIMIT_MB",
    "CACHE_VALUE_MAX_SIZE_KB",
    "CACHE_ENABLE_COMPRESSION",
    "ENABLE_SEMANTIC_CACHE",
    "SEMANTIC_CACHE_SIMILARITY_THRESHOLD",
    # Guardrails
    "GUARDRAILS_LEVEL",
    "GUARDRAILS_AVAILABLE",
    "OOD_MIN_SCORE",
    "OOD_STRICT_SCORE",
    # Features
    "ENTITY_ENRICHMENT_ENABLED",
    "ENABLE_API_DIAGNOSTICS",
    # Constantes système
    "BASE_PATH",
    "ALLOWED_ORIGINS",
    "STARTUP_TIMEOUT",
    "TENANT_TTL",
    "MAX_TENANTS",
    "STREAM_CHUNK_LEN",
    "MAX_REQUEST_SIZE",
    "ENABLE_METRICS_LOGGING",
    # Entity contexts
    "ENTITY_CONTEXTS",
    # Domain keywords
    "DOMAIN_KEYWORDS",
    # Performance
    "ENABLE_PERFORMANCE_MONITORING",
    "METRICS_EXPORT_INTERVAL",
    # Digital Ocean
    "DO_APP_NAME",
    "DO_APP_TIER",
    # Fonctions
    "validate_config",
    "get_config_status",
    "validate_language_code",
    "get_supported_languages_info",
]
