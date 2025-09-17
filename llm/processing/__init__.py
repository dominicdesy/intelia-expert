# -*- coding: utf-8 -*-
"""
Processing module - Traitement des intentions et entités
CORRIGÉ: Imports modulaires selon nouvelle architecture
"""

from .intent_processor import IntentProcessor, IntentResult, IntentType
from .entity_extractor import EntityExtractor
from .intent_types import *

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
    "VocabularyExtractor"
]