# -*- coding: utf-8 -*-
"""
Processing module - Traitement des intentions et entités
CORRIGÉ: Imports modulaires selon nouvelle architecture
"""

# CORRECTION: Supprimer IntentResult et IntentType de cette ligne car ils sont importés depuis intent_types
from .intent_processor import IntentProcessor
from .entity_extractor import EntityExtractor

# CORRECTION: Import explicite au lieu du star import dangereux
from .intent_types import (
    IntentType,
    IntentResult,
    IntentValidationResult,
    ConfigurationValidator,
    ValidationResult,
    DEFAULT_INTENTS_CONFIG,
    IntentCategory,
    EntityType,
)

try:
    from .intent_classifier import IntentClassifier
except ImportError:
    IntentClassifier = None

try:
    from .query_expander import QueryExpander
except ImportError:
    QueryExpander = None

try:
    from .vocabulary_extractor import PoultryVocabularyExtractor as VocabularyExtractor
except ImportError:
    VocabularyExtractor = None

__all__ = [
    "IntentProcessor",
    "IntentResult",
    "IntentType",
    "EntityExtractor",
    "IntentClassifier",
    "QueryExpander",
    "VocabularyExtractor",
    "IntentValidationResult",
    "ConfigurationValidator",
    "ValidationResult",
    "DEFAULT_INTENTS_CONFIG",
    "IntentCategory",
    "EntityType",
]
