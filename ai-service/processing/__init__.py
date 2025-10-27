# -*- coding: utf-8 -*-
"""
Processing module - Traitement des intentions et entités
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Processing module - Traitement des intentions et entités
CORRIGÉ: Imports modulaires selon nouvelle architecture
NOTE: EntityExtractor a été déplacé vers core.entity_extractor
"""

# CORRECTION: Import des types d'abord pour éviter les dépendances circulaires
from .intent_types import (
    IntentType,
    IntentResult,
    IntentValidationResult,
    ConfigurationValidator,
    ValidationResult,
    DEFAULT_INTENTS_CONFIG,
    IntentCategory,
    EntityType,
    create_configuration_validator,
)

# CORRECTION: Imports conditionnels des classes principales pour éviter les erreurs de démarrage
try:
    from .intent_processor import IntentProcessor
except ImportError as e:
    IntentProcessor = None
    import logging

    logging.getLogger(__name__).warning(f"IntentProcessor non disponible: {e}")

# SUPPRIMÉ: EntityExtractor est maintenant dans core.entity_extractor
# L'import depuis processing.entity_extractor générait un warning inutile
# Utilisez: from core.entity_extractor import EntityExtractor

try:
    from .intent_classifier import IntentClassifier
except ImportError as e:
    IntentClassifier = None
    import logging

    logging.getLogger(__name__).warning(f"IntentClassifier non disponible: {e}")

try:
    from .query_expander import QueryExpander
except ImportError as e:
    QueryExpander = None
    import logging

    logging.getLogger(__name__).warning(f"QueryExpander non disponible: {e}")

try:
    from .vocabulary_extractor import PoultryVocabularyExtractor as VocabularyExtractor
except ImportError as e:
    VocabularyExtractor = None
    import logging

    logging.getLogger(__name__).warning(f"VocabularyExtractor non disponible: {e}")

# Export public - tous les éléments disponibles
__all__ = [
    # Types de base (toujours disponibles)
    "IntentType",
    "IntentResult",
    "IntentValidationResult",
    "ConfigurationValidator",
    "ValidationResult",
    "DEFAULT_INTENTS_CONFIG",
    "IntentCategory",
    "EntityType",
    "create_configuration_validator",
    # Classes de traitement (peuvent être None si import échoue)
    "IntentProcessor",
    # EntityExtractor retiré - utiliser core.entity_extractor
    "IntentClassifier",
    "QueryExpander",
    "VocabularyExtractor",
]


# Fonction utilitaire pour diagnostiquer les composants disponibles
def get_processing_status():
    """Retourne le statut des composants du module processing"""
    return {
        "types_available": True,
        "intent_processor_available": IntentProcessor is not None,
        # entity_extractor n'est plus dans processing
        "intent_classifier_available": IntentClassifier is not None,
        "query_expander_available": QueryExpander is not None,
        "vocabulary_extractor_available": VocabularyExtractor is not None,
        "configuration_validator_available": True,
    }
