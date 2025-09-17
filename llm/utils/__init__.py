# -*- coding: utf-8 -*-
"""
Utils module - Utilitaires et fonctions helpers
VERSION CORRIGÃ‰E POUR STRUCTURE MODULAIRE
"""

from .utilities import (
    METRICS,
    detect_language_enhanced,
    build_where_filter,
    create_intent_processor,
    process_query_with_intents,
    validate_intents_config
)

try:
    # CORRECTION MAJEURE : Import depuis le chemin modulaire
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
        REDIS_AVAILABLE
    )
    DEPENDENCIES_MANAGER_AVAILABLE = True
except ImportError:
    DEPENDENCIES_MANAGER_AVAILABLE = False
    dependency_manager = None

__all__ = [
    "METRICS",
    "detect_language_enhanced",
    "build_where_filter", 
    "create_intent_processor",
    "process_query_with_intents",
    "validate_intents_config",
    "dependency_manager",
    "get_openai_sync",
    "get_openai_async",
    "get_dependencies_status",
    "get_full_status_report",
    "quick_connectivity_check",
    "require_critical_dependencies",
    "OPENAI_AVAILABLE",
    "WEAVIATE_AVAILABLE", 
    "REDIS_AVAILABLE",
    "DEPENDENCIES_MANAGER_AVAILABLE"
]