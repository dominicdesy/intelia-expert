# -*- coding: utf-8 -*-
"""
models.py - Domain relevance models for OOD detection

This module contains the data models used for representing domain relevance
scores and levels in the out-of-domain detection system.
"""

from dataclasses import dataclass
from enum import Enum
from utils.types import Dict, List, Optional
from utils.mixins import SerializableMixin


class DomainRelevance(Enum):
    """
    Enumeration of domain relevance levels for poultry domain classification.

    Levels represent the degree to which a query relates to the poultry domain:
    - HIGH: Strong poultry domain relevance (e.g., specific genetic lines, technical metrics)
    - MEDIUM: Moderate poultry relevance (e.g., general farming terms, equipment)
    - LOW: Weak poultry relevance (e.g., tangentially related terms)
    - GENERIC: Generic terms without specific domain relevance
    - BLOCKED: Explicitly blocked/inappropriate content
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    GENERIC = "generic"
    BLOCKED = "blocked"


@dataclass
class DomainScore(SerializableMixin):
    """
    Detailed domain scoring result with multilingual context.

    This dataclass encapsulates all information about a query's domain relevance
    including the calculated score, detected domain words, blocked terms, and
    reasoning behind the classification.

    Attributes:
        final_score: Final calculated relevance score (0.0 to 1.0)
        relevance_level: Categorical relevance level (DomainRelevance enum)
        domain_words: List of domain-specific words found in the query
        blocked_terms: List of blocked/inappropriate terms detected
        confidence_boosters: Dict of factors that boosted confidence
        threshold_applied: The threshold value used for decision
        reasoning: Human-readable explanation of the scoring decision
        translation_used: Whether translation was used in analysis
        original_language: Original language of the query (ISO code)
        translated_query: Translated version of query if translation was used
    """

    final_score: float
    relevance_level: DomainRelevance
    domain_words: List[str]
    blocked_terms: List[str]
    confidence_boosters: Dict[str, float]
    threshold_applied: float
    reasoning: str
    translation_used: bool = False
    original_language: str = "fr"
    translated_query: Optional[str] = None
