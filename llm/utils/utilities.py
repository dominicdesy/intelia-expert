# -*- coding: utf-8 -*-
"""
utilities.py - Point d'entrée principal des utilitaires - VERSION MODULAIRE
Refactorisé pour éviter un seul gros fichier tout en conservant la compatibilité
"""

import logging

# ============================================================================
# IMPORTS DES MODULES REFACTORISÉS
# ============================================================================

# Classes de données et sérialisation
from utils.data_classes import (
    ValidationReport,
    ProcessingResult,
    safe_serialize_for_json,
)

# Détection de langue - CORRIGÉ
from utils.language_detection import (
    LanguageDetectionResult,
    detect_language_enhanced,
    is_supported_language,
    normalize_language_code,
    FASTTEXT_LANGDETECT_AVAILABLE,
    LANGDETECT_AVAILABLE,
    UNIDECODE_AVAILABLE,
)

# Traduction et messages
from utils.translation_utils import (
    get_universal_translation,
    get_out_of_domain_message,
    get_system_message,
    get_aviculture_response,
)

# Métriques
from utils.metrics_collector import (
    METRICS,
    MetricsCollector,
    get_all_metrics_json,
)

# Traitement d'intentions
from utils.intent_processing import (
    validate_intent_result,
    build_where_filter,
    create_intent_processor,
    process_query_with_intents,
    validate_intents_config,
    IntentProcessorFactory,
)

# Utilitaires de texte
from utils.text_utilities import (
    safe_get_attribute,
    safe_dict_get,
    sse_event,
    smart_chunk_text,
)

# Données de test et configuration
from utils.test_data import (
    COMPREHENSIVE_TEST_QUERIES,
    setup_logging,
)

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# ALIAS POUR COMPATIBILITÉ APRÈS TOUS LES IMPORTS
# ============================================================================

# CORRECTION: Alias pour compatibilité avec le code existant
FASTTEXT_AVAILABLE = FASTTEXT_LANGDETECT_AVAILABLE
FAST_LANGDETECT_AVAILABLE = LANGDETECT_AVAILABLE

# ============================================================================
# EXPORTS - MAINTIEN DE LA COMPATIBILITÉ
# ============================================================================

__all__ = [
    # FLAGS D'IMPORT
    "FASTTEXT_AVAILABLE",
    "FAST_LANGDETECT_AVAILABLE",
    "UNIDECODE_AVAILABLE",
    # Classes de données multilingues
    "LanguageDetectionResult",
    "ValidationReport",
    "ProcessingResult",
    # Détection langue multilingue
    "detect_language_enhanced",
    # Support langues
    "is_supported_language",
    "normalize_language_code",
    "get_universal_translation",
    # Messages multilingues - MODIFIÉ
    "get_out_of_domain_message",
    "get_system_message",  # NOUVEAU
    "get_aviculture_response",
    # CORRECTION CRITIQUE: Ajout fonction manquante
    "validate_intent_result",
    # Métriques
    "METRICS",
    "MetricsCollector",
    "get_all_metrics_json",
    # Weaviate - MODIFIÉ avec support DISABLE_WHERE_FILTER
    "build_where_filter",
    # Intent processing
    "create_intent_processor",
    "process_query_with_intents",
    "validate_intents_config",
    "IntentProcessorFactory",
    # Utilitaires
    "safe_serialize_for_json",
    "safe_get_attribute",
    "safe_dict_get",
    "sse_event",
    "smart_chunk_text",
    "setup_logging",
    # Données test
    "COMPREHENSIVE_TEST_QUERIES",
]
