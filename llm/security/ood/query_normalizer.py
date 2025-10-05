# -*- coding: utf-8 -*-
"""
query_normalizer.py - Query normalization for OOD detection

This module contains the QueryNormalizer class responsible for normalizing
user queries before domain analysis. Handles different normalization strategies
for Latin and non-Latin scripts to preserve Unicode integrity where needed.
"""

import logging
import re
from .config import ACRONYM_EXPANSIONS, NON_LATIN_SCRIPT_LANGUAGES

# Import unidecode utility
from utils.imports_and_dependencies import UNIDECODE_AVAILABLE

if UNIDECODE_AVAILABLE:
    from unidecode import unidecode

logger = logging.getLogger(__name__)


class QueryNormalizer:
    """
    Static utility class for normalizing user queries.

    Provides language-aware normalization that:
    - Preserves Unicode characters for non-Latin scripts (Hindi, Thai, Chinese, etc.)
    - Applies transliteration for Latin scripts (French, English, Spanish, etc.)
    - Expands common acronyms
    - Cleans and standardizes whitespace
    """

    @staticmethod
    def normalize_query(query: str, language: str) -> str:
        """
        Normalize query based on language and script type.

        This is the main entry point for query normalization. It routes to
        appropriate normalization strategies based on the query's language:
        - Non-Latin scripts: Preserve Unicode, minimal normalization
        - Latin scripts: Apply full normalization with transliteration

        Args:
            query: Original user query string
            language: ISO language code (e.g., "fr", "en", "hi", "zh")

        Returns:
            Normalized query string suitable for domain analysis

        Example:
            >>> QueryNormalizer.normalize_query("Quel est le meilleur FCR?", "fr")
            'quel est le meilleur feed conversion ratio'

            >>> QueryNormalizer.normalize_query("मुर्गी का वजन?", "hi")
            'मुर्गी का वजन'
        """
        if not query:
            return ""

        # Route to appropriate normalization strategy
        if language in NON_LATIN_SCRIPT_LANGUAGES:
            return QueryNormalizer._normalize_non_latin(query, language)
        else:
            return QueryNormalizer._normalize_latin(query, language)

    @staticmethod
    def _normalize_latin(query: str, language: str) -> str:
        """
        Normalize query for Latin scripts (French, English, Spanish, etc.).

        Applies comprehensive normalization:
        1. Convert to lowercase
        2. Transliterate accented characters (if unidecode available)
        3. Remove special characters (keep alphanumeric, spaces, basic punctuation)
        4. Normalize whitespace
        5. Expand acronyms

        Args:
            query: Query string in a Latin-script language
            language: ISO language code

        Returns:
            Fully normalized query string

        Example:
            >>> QueryNormalizer._normalize_latin("Quelle température idéale?", "fr")
            'quelle temperature ideale'
        """
        # Step 1: Convert to lowercase
        normalized = query.lower()

        # Step 2: Transliterate accented characters
        if UNIDECODE_AVAILABLE:
            normalized = unidecode(normalized)
        else:
            # If unidecode not available, just use lowercase
            logger.debug("unidecode not available, skipping transliteration")

        # Step 3: Remove special characters (keep word chars, spaces, digits, basic punctuation)
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)

        # Step 4: Normalize whitespace (collapse multiple spaces)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Step 5: Expand acronyms
        for acronym, expansion in ACRONYM_EXPANSIONS.items():
            # Use word boundary to match whole acronyms only
            normalized = re.sub(rf"\b{acronym}\b", expansion, normalized)

        return normalized

    @staticmethod
    def _normalize_non_latin(query: str, language: str) -> str:
        """
        Normalize query for non-Latin scripts (Hindi, Thai, Chinese, Arabic, etc.).

        Applies minimal normalization to preserve script integrity:
        1. Convert to lowercase (for languages that support it)
        2. Remove special characters (but preserve Unicode script characters)
        3. Normalize whitespace

        Does NOT apply:
        - Transliteration (would destroy the script)
        - Acronym expansion (may not be relevant)

        Args:
            query: Query string in a non-Latin script language
            language: ISO language code (e.g., "hi", "th", "zh", "ar")

        Returns:
            Minimally normalized query with preserved Unicode

        Example:
            >>> QueryNormalizer._normalize_non_latin("मुर्गी का वजन कितना?", "hi")
            'मुर्गी का वजन कितना'

            >>> QueryNormalizer._normalize_non_latin("鸡的体重是多少？", "zh")
            '鸡的体重是多少'
        """
        # Step 1: Convert to lowercase (works for some non-Latin scripts)
        normalized = query.lower()

        # Step 2: Remove special characters but preserve Unicode word characters
        # The \w in Python regex includes Unicode letters, so this preserves scripts
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)

        # Step 3: Normalize whitespace (collapse multiple spaces)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Note: No transliteration, no acronym expansion for non-Latin scripts

        return normalized
