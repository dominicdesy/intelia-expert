# -*- coding: utf-8 -*-
"""
config.py - Configuration centralisée avec support LangSmith et RRF Intelligent
Optimisé pour Digital Ocean App Platform
Version corrigée: Ajout ENTITY_CONTEXTS manquant pour le système RAG
CORRIGÉ: Suppression du doublon ENABLE_API_DIAGNOSTICS
CORRECTION: Ajout des constantes manquantes identifiées
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

# Paramètres RRF
RRF_CACHE_SIZE = int(os.getenv("RRF_CACHE_SIZE", "1000"))
RRF_BASE_K = int(os.getenv("RRF_BASE_K", "60"))

# ===== RAG CONFIGURATION =====
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "15"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.55"))
RAG_VERIFICATION_ENABLED = os.getenv("RAG_VERIFICATION_ENABLED", "true").lower() == "true"
RAG_VERIFICATION_SMART = os.getenv("RAG_VERIFICATION_SMART", "true").lower() == "true"
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "8"))

# Recherche hybride
HYBRID_SEARCH_ENABLED = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
DEFAULT_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.6"))

# ===== CACHE CONFIGURATION =====
CACHE_TOTAL_MEMORY_LIMIT_MB = int(os.getenv("CACHE_TOTAL_MEMORY_LIMIT_MB", "150"))
CACHE_VALUE_MAX_SIZE_KB = int(os.getenv("CACHE_VALUE_MAX_SIZE_KB", "200"))
CACHE_ENABLE_COMPRESSION = os.getenv("CACHE_ENABLE_COMPRESSION", "true").lower() == "true"

# Cache sémantique
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true"
SEMANTIC_CACHE_SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_SIMILARITY_THRESHOLD", "0.92"))

# ===== GUARDRAILS ET SÉCURITÉ =====
GUARDRAILS_LEVEL = os.getenv("GUARDRAILS_LEVEL", "strict")
GUARDRAILS_AVAILABLE = True  # Toujours disponible en mode basique

# OOD Detection
OOD_MIN_SCORE = float(os.getenv("OOD_MIN_SCORE", "0.4"))
OOD_STRICT_SCORE = float(os.getenv("OOD_STRICT_SCORE", "0.7"))

# ===== ENRICHISSEMENTS ET FONCTIONNALITÉS =====
ENTITY_ENRICHMENT_ENABLED = os.getenv("ENTITY_ENRICHMENT_ENABLED", "true").lower() == "true"
# CORRECTION: Une seule définition de ENABLE_API_DIAGNOSTICS
ENABLE_API_DIAGNOSTICS = os.getenv("ENABLE_API_DIAGNOSTICS", "false").lower() == "true"

# ===== CONSTANTES MANQUANTES AJOUTÉES =====
BASE_PATH = os.getenv("BASE_PATH", "")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") != "*" else ["*"]
STARTUP_TIMEOUT = int(os.getenv("STARTUP_TIMEOUT", "30"))
TENANT_TTL = int(os.getenv("TENANT_TTL", "3600"))
MAX_TENANTS = int(os.getenv("MAX_TENANTS", "100"))
STREAM_CHUNK_LEN = int(os.getenv("STREAM_CHUNK_LEN", "8"))
ENABLE_METRICS_LOGGING = os.getenv("ENABLE_METRICS_LOGGING", "true").lower() == "true"

# ===== ENTITY_CONTEXTS - CONFIGURATION MANQUANTE CRITIQUE =====
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
        "hy-line": "lignée ponte polyvalente, bonne adaptabilité"
    },
    "species": {
        "broiler": "poulet de chair, objectifs: poids vif, FCR, rendement carcasse",
        "layer": "poule pondeuse, objectifs: intensité de ponte, qualité œuf, persistance",
        "breeder": "reproducteur, objectifs: fertilité, éclosabilité, viabilité descendance",
        "pullet": "poulette, phase d'élevage avant la ponte",
        "chick": "poussin, phase critique des premiers jours"
    },
    "phase": {
        "starter": "phase démarrage (0-10j), croissance critique, thermorégulation",
        "grower": "phase croissance (11-24j), développement squelettique et musculaire", 
        "finisher": "phase finition (25j+), optimisation du poids final et FCR",
        "laying": "phase ponte, maintien de la production et qualité œuf",
        "breeding": "phase reproduction, optimisation fertilité et éclosabilité"
    },
    "site_type": {
        "broiler_farm": "élevage poulets de chair, focus performance et conversion",
        "layer_farm": "élevage pondeuses, focus production œufs",
        "rearing_farm": "élevage poulettes, préparation à la ponte",
        "breeding_farm": "élevage reproducteurs, focus fertilité",
        "hatchery": "couvoir, incubation et éclosion",
        "feed_mill": "usine d'aliments, nutrition animale"
    },
    "environment": {
        "tunnel": "ventilation tunnel, contrôle précis température et humidité",
        "natural": "ventilation naturelle, dépendante des conditions extérieures",
        "mechanical": "ventilation mécanique, contrôle intermédiaire"
    }
}

# ===== DÉTECTION DE LANGUE - VARIABLES MANQUANTES AJOUTÉES =====
LANG_DETECTION_MIN_LENGTH = int(os.getenv("LANG_DETECTION_MIN_LENGTH", "20"))

# Mots indicateurs français
FRENCH_HINTS = [
    "est", "sont", "était", "sera", "avec", "dans", "pour", "que", "qui", "quoi", 
    "comment", "pourquoi", "quand", "où", "combien", "quelle", "quel", "quels", 
    "quelles", "celui", "celle", "ceux", "celles", "cette", "ces", "mon", "ma", 
    "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", "votre", 
    "vos", "leur", "leurs", "le", "la", "les", "un", "une", "des", "du", "de",
    "au", "aux", "sur", "sous", "entre", "vers", "pendant", "depuis", "avant",
    "après", "chez", "sans", "très", "plus", "moins", "aussi", "encore", "déjà",
    "jamais", "toujours", "souvent", "parfois", "hier", "aujourd", "demain",
    "matin", "soir", "nuit", "jour", "semaine", "mois", "année", "temps"
]

# Mots indicateurs anglais
ENGLISH_HINTS = [
    "the", "and", "that", "have", "for", "not", "with", "you", "this", "but",
    "his", "from", "they", "she", "her", "been", "than", "its", "who", "did",
    "what", "when", "where", "why", "how", "which", "would", "could", "should",
    "will", "can", "may", "might", "must", "shall", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "among", "under",
    "over", "very", "more", "most", "less", "much", "many", "some", "any",
    "all", "both", "each", "every", "other", "another", "such", "only", "own",
    "same", "few", "little", "long", "good", "new", "first", "last", "next",
    "old", "great", "small", "large", "right", "left", "high", "low", "here",
    "there", "now", "then", "today", "tomorrow", "yesterday", "morning", "evening"
]

# Caractères spéciaux français
FRENCH_CHARS = ["à", "â", "ä", "ç", "é", "è", "ê", "ë", "î", "ï", "ô", "ö", "ù", "û", "ü", "ÿ", "ñ"]

# Mots techniques aviculture (français)
AVICULTURE_FRENCH_TERMS = [
    "poule", "poulet", "poussin", "coq", "volaille", "ponte", "œuf", "œufs",
    "alimentation", "mangeoire", "abreuvoir", "poulailler", "perchoir", "pondoir",
    "poussinière", "élevage", "couveuse", "incubation", "éclosion", "vaccin",
    "vermifuge", "parasites", "maladies", "aviaires", "stress", "picage",
    "plumage", "mue", "croissance", "reproduction", "fertilité", "ponte",
    "coquille", "blanc", "jaune", "vitellus", "albumen", "chalaze"
]

# ===== DOMAINES KEYWORDS POUR OOD =====
DOMAIN_KEYWORDS = [
    # Aviculture core
    "poule", "poulet", "poussin", "coq", "volaille", "ponte", "œuf", "œufs",
    "chicken", "hen", "rooster", "chick", "poultry", "egg", "eggs", "laying",
    
    # Élevage et soins
    "alimentation", "mangeoire", "abreuvoir", "poulailler", "perchoir", "pondoir",
    "feeding", "feeder", "waterer", "coop", "roost", "nest", "housing",
    
    # Santé et maladies
    "maladie", "vaccin", "vermifuge", "parasites", "stress", "picage", "plumage",
    "disease", "vaccine", "dewormer", "parasites", "stress", "pecking", "feather",
    
    # Production
    "ponte", "production", "œufs", "incubation", "éclosion", "couveuse",
    "laying", "production", "eggs", "incubation", "hatching", "incubator",
    
    # Nutrition
    "protéine", "calcium", "grain", "maïs", "blé", "soja", "vitamines",
    "protein", "calcium", "grain", "corn", "wheat", "soy", "vitamins"
]

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
    
    if not (0.0 <= RAG_CONFIDENCE_THRESHOLD <= 1.0):
        errors.append("RAG_CONFIDENCE_THRESHOLD doit être entre 0.0 et 1.0")
    
    if not (0.0 <= SEMANTIC_CACHE_SIMILARITY_THRESHOLD <= 1.0):
        errors.append("SEMANTIC_CACHE_SIMILARITY_THRESHOLD doit être entre 0.0 et 1.0")
    
    # Validation guardrails - CORRECTION PRINCIPALE
    if GUARDRAILS_LEVEL not in ["strict", "moderate", "permissive"]:
        errors.append("GUARDRAILS_LEVEL doit être: strict, moderate, ou permissive")
    
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
        "entity_contexts": {
            "lines_count": len(ENTITY_CONTEXTS["line"]),
            "species_count": len(ENTITY_CONTEXTS["species"]),
            "phases_count": len(ENTITY_CONTEXTS["phase"]),
            "site_types_count": len(ENTITY_CONTEXTS["site_type"]),
            "environments_count": len(ENTITY_CONTEXTS["environment"])
        },
        "language_detection": {
            "min_length": LANG_DETECTION_MIN_LENGTH,
            "french_hints_count": len(FRENCH_HINTS),
            "english_hints_count": len(ENGLISH_HINTS),
            "french_chars_count": len(FRENCH_CHARS),
            "aviculture_terms_count": len(AVICULTURE_FRENCH_TERMS)
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
    "LANGSMITH_ENABLED", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "LANGSMITH_ENVIRONMENT",
    # RRF Intelligent
    "ENABLE_INTELLIGENT_RRF", "RRF_LEARNING_MODE", "RRF_GENETIC_BOOST", "RRF_DEBUG_MODE",
    "RRF_CACHE_SIZE", "RRF_BASE_K",
    # RAG Config
    "RAG_SIMILARITY_TOP_K", "RAG_CONFIDENCE_THRESHOLD", "RAG_VERIFICATION_ENABLED",
    "RAG_VERIFICATION_SMART", "HYBRID_SEARCH_ENABLED", "DEFAULT_ALPHA", "MAX_CONVERSATION_CONTEXT",
    # Cache
    "CACHE_TOTAL_MEMORY_LIMIT_MB", "CACHE_VALUE_MAX_SIZE_KB", "CACHE_ENABLE_COMPRESSION",
    "ENABLE_SEMANTIC_CACHE", "SEMANTIC_CACHE_SIMILARITY_THRESHOLD",
    # Guardrails
    "GUARDRAILS_LEVEL", "GUARDRAILS_AVAILABLE", "OOD_MIN_SCORE", "OOD_STRICT_SCORE",
    # Features
    "ENTITY_ENRICHMENT_ENABLED", "ENABLE_API_DIAGNOSTICS",
    # CONSTANTES MANQUANTES AJOUTÉES
    "BASE_PATH", "ALLOWED_ORIGINS", "STARTUP_TIMEOUT", 
    "TENANT_TTL", "MAX_TENANTS", "STREAM_CHUNK_LEN", "ENABLE_METRICS_LOGGING",
    # ENTITY_CONTEXTS - AJOUT CRITIQUE
    "ENTITY_CONTEXTS",
    # Language Detection
    "LANG_DETECTION_MIN_LENGTH", "FRENCH_HINTS", "ENGLISH_HINTS", "FRENCH_CHARS",
    "AVICULTURE_FRENCH_TERMS", "DOMAIN_KEYWORDS",
    # Performance
    "ENABLE_PERFORMANCE_MONITORING", "METRICS_EXPORT_INTERVAL",
    # Digital Ocean
    "DO_APP_NAME", "DO_APP_TIER",
    # Fonctions
    "validate_config", "get_config_status"
]