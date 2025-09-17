# -*- coding: utf-8 -*-
"""
Utils module - Utilitaires et fonctions helpers
VERSION CORRIGÉE POUR STRUCTURE MODULAIRE - Import circulaire résolu
"""

# ÉTAPE 1: Importer utilities en premier (contient METRICS)
from .utilities import (
    METRICS,
    detect_language_enhanced,
    build_where_filter,
    create_intent_processor,
    process_query_with_intents,
    validate_intents_config,
)

# ÉTAPE 2: Importer imports_and_dependencies après utilities
try:
    from .imports_and_dependencies import (
        dependency_manager,
        get_openai_sync,
        get_openai_async,
        get_dependencies_status,
        get_full_status_report,
        quick_connectivity_check,
        require_critical_dependencies,
        OPENAI_AVAILABLE,
        WEAVIATE_AVAILABLE,
        REDIS_AVAILABLE,
        UNIDECODE_AVAILABLE,  # AJOUT CRITIQUE
        VOYAGEAI_AVAILABLE,
        SENTENCE_TRANSFORMERS_AVAILABLE,
        TRANSFORMERS_AVAILABLE,
        LANGDETECT_AVAILABLE,
        LANGSMITH_AVAILABLE,
    )
    DEPENDENCIES_MANAGER_AVAILABLE = True
except ImportError as e:
    # Log l'erreur pour debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Erreur import imports_and_dependencies: {e}")
    
    DEPENDENCIES_MANAGER_AVAILABLE = False
    dependency_manager = None
    # Définir les fallbacks
    OPENAI_AVAILABLE = False
    WEAVIATE_AVAILABLE = False
    REDIS_AVAILABLE = False
    UNIDECODE_AVAILABLE = False
    VOYAGEAI_AVAILABLE = False
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    TRANSFORMERS_AVAILABLE = False
    LANGDETECT_AVAILABLE = False
    LANGSMITH_AVAILABLE = False

__all__ = [
    # Utilities - toujours disponible
    "METRICS",
    "detect_language_enhanced",
    "build_where_filter",
    "create_intent_processor",
    "process_query_with_intents",
    "validate_intents_config",
    
    # Dependencies manager - peut être None
    "dependency_manager",
    "get_openai_sync",
    "get_openai_async",
    "get_dependencies_status",
    "get_full_status_report",
    "quick_connectivity_check",
    "require_critical_dependencies",
    
    # Variables de statut
    "OPENAI_AVAILABLE",
    "WEAVIATE_AVAILABLE",
    "REDIS_AVAILABLE",
    "UNIDECODE_AVAILABLE",  # AJOUT CRITIQUE
    "VOYAGEAI_AVAILABLE",
    "SENTENCE_TRANSFORMERS_AVAILABLE", 
    "TRANSFORMERS_AVAILABLE",
    "LANGDETECT_AVAILABLE",
    "LANGSMITH_AVAILABLE",
    "DEPENDENCIES_MANAGER_AVAILABLE",
]