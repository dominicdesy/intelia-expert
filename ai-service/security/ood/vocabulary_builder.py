# -*- coding: utf-8 -*-
"""
vocabulary_builder.py - Domain vocabulary construction for OOD detection
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
vocabulary_builder.py - Domain vocabulary construction for OOD detection

This module contains the VocabularyBuilder class responsible for building
the hierarchical domain vocabulary used in out-of-domain detection.
Supports both service-based (from translation service) and fallback
vocabulary construction methods.
"""

import logging
from utils.types import Dict, Set
from .models import DomainRelevance
from .config import (
    FALLBACK_HIGH_PRIORITY_TERMS,
    FALLBACK_MEDIUM_PRIORITY_TERMS,
    GENERIC_QUERY_WORDS,
)

# Import DOMAIN_KEYWORDS from main config
from config.config import DOMAIN_KEYWORDS

logger = logging.getLogger(__name__)


class VocabularyBuilder:
    """
    Static utility class for building domain vocabularies.

    This class provides methods to construct hierarchical domain vocabularies
    from either a translation service (preferred) or from fallback configurations.
    The vocabulary is organized into relevance levels (HIGH, MEDIUM, LOW, GENERIC)
    for more nuanced domain detection.
    """

    @staticmethod
    def build_from_service(
        translation_service,
        supported_languages: list,
        domain_keywords: list = None,
    ) -> Dict[DomainRelevance, Set[str]]:
        """
        Build domain vocabulary from translation service.

        Constructs a multilingual domain vocabulary by:
        1. Starting with base keywords from DOMAIN_KEYWORDS config
        2. Extending with terms from the translation service's domain dictionaries
        3. Organizing terms into relevance levels (HIGH, MEDIUM, LOW, GENERIC)

        Args:
            translation_service: Translation service instance with get_domain_terms method
            supported_languages: List of ISO language codes to retrieve terms for
            domain_keywords: Optional list of base keywords (defaults to DOMAIN_KEYWORDS)

        Returns:
            Dict mapping DomainRelevance levels to sets of terms

        Example:
            >>> vocabulary = VocabularyBuilder.build_from_service(
            ...     translation_service,
            ...     ["fr", "en", "es"],
            ...     DOMAIN_KEYWORDS
            ... )
            >>> len(vocabulary[DomainRelevance.HIGH])
            150  # Number of high-priority terms
        """
        if domain_keywords is None:
            domain_keywords = DOMAIN_KEYWORDS

        vocabulary = {level: set() for level in DomainRelevance}

        # ===== Step 1: Build base vocabulary from DOMAIN_KEYWORDS =====

        # First 20 keywords are high priority
        high_priority_base = set()
        for keyword in domain_keywords[:20]:
            high_priority_base.add(keyword.lower())

        # Next 20 keywords are medium priority
        medium_priority_base = set()
        for keyword in domain_keywords[20:40]:
            medium_priority_base.add(keyword.lower())

        # Remaining keywords are low priority
        low_priority_base = set()
        for keyword in domain_keywords[40:]:
            low_priority_base.add(keyword.lower())

        # ===== Step 2: Extend via translation service =====

        if translation_service:
            try:
                # Define domain categories to retrieve
                aviculture_domains = [
                    "genetic_lines",
                    "performance_metrics",
                    "equipment_types",
                    "health_symptoms",
                    "feeding_systems",
                    "housing_types",
                ]

                # Retrieve terms for each domain in each supported language
                for domain in aviculture_domains:
                    for lang in supported_languages:
                        # Get domain-specific terms from translation service
                        if hasattr(translation_service, "get_domain_terms"):
                            terms = translation_service.get_domain_terms(domain, lang)
                        else:
                            # Fallback if method not available
                            terms = []

                        # Classify terms by domain category
                        if domain in ["genetic_lines", "performance_metrics"]:
                            # Technical domains = high priority
                            high_priority_base.update(term.lower() for term in terms)
                        elif domain in ["equipment_types", "health_symptoms"]:
                            # Specialized domains = medium priority
                            medium_priority_base.update(term.lower() for term in terms)
                        else:
                            # General domains = low priority
                            low_priority_base.update(term.lower() for term in terms)

                logger.debug(
                    f"Vocabulary extended via service: "
                    f"{len(high_priority_base)} high, "
                    f"{len(medium_priority_base)} medium, "
                    f"{len(low_priority_base)} low"
                )

            except Exception as e:
                logger.debug(f"Error extending vocabulary via translation service: {e}")
                # Continue with base vocabulary

        # ===== Step 3: Build final vocabulary structure =====

        vocabulary[DomainRelevance.HIGH] = high_priority_base
        vocabulary[DomainRelevance.MEDIUM] = medium_priority_base
        vocabulary[DomainRelevance.LOW] = low_priority_base

        # Generic terms (question words, common terms across languages)
        vocabulary[DomainRelevance.GENERIC] = GENERIC_QUERY_WORDS.copy()

        return vocabulary

    @staticmethod
    def build_fallback(domain_keywords: list = None) -> Dict[DomainRelevance, Set[str]]:
        """
        Build fallback domain vocabulary without translation service.

        Used when translation service is unavailable. Constructs a multilingual
        vocabulary using hardcoded fallback terms from configuration plus
        base keywords.

        Args:
            domain_keywords: Optional list of base keywords (defaults to DOMAIN_KEYWORDS)

        Returns:
            Dict mapping DomainRelevance levels to sets of terms

        Example:
            >>> vocabulary = VocabularyBuilder.build_fallback(DOMAIN_KEYWORDS)
            >>> "ross" in vocabulary[DomainRelevance.HIGH]
            True
            >>> "feed" in vocabulary[DomainRelevance.MEDIUM]
            True
        """
        if domain_keywords is None:
            domain_keywords = DOMAIN_KEYWORDS

        vocabulary = {level: set() for level in DomainRelevance}

        logger.debug(
            "Translation service unavailable, using extended fallback vocabulary"
        )

        # ===== Step 1: Build base from DOMAIN_KEYWORDS =====

        high_priority_base = set()
        for keyword in domain_keywords[:20]:  # First 20 = high priority
            high_priority_base.add(keyword.lower())

        medium_priority_base = set()
        for keyword in domain_keywords[20:40]:  # Next 20 = medium priority
            medium_priority_base.add(keyword.lower())

        low_priority_base = set()
        for keyword in domain_keywords[40:]:  # Rest = low priority
            low_priority_base.add(keyword.lower())

        # ===== Step 2: Add multilingual fallback terms =====

        # Add predefined high-priority multilingual terms
        high_priority_base.update(FALLBACK_HIGH_PRIORITY_TERMS)

        # Add predefined medium-priority multilingual terms
        medium_priority_base.update(FALLBACK_MEDIUM_PRIORITY_TERMS)

        # ===== Step 3: Build final vocabulary structure =====

        vocabulary[DomainRelevance.HIGH] = high_priority_base
        vocabulary[DomainRelevance.MEDIUM] = medium_priority_base
        vocabulary[DomainRelevance.LOW] = low_priority_base

        # Generic terms (question words, common terms)
        vocabulary[DomainRelevance.GENERIC] = GENERIC_QUERY_WORDS.copy()

        logger.debug(
            f"Fallback vocabulary built: "
            f"{len(high_priority_base)} high, "
            f"{len(medium_priority_base)} medium, "
            f"{len(low_priority_base)} low priority terms"
        )

        return vocabulary
