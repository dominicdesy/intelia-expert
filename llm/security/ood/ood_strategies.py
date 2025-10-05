# -*- coding: utf-8 -*-
"""
ood_strategies.py - OOD calculation strategies

This module contains the OODStrategy class that implements the four main
strategies for calculating out-of-domain (OOD) scores:
1. Direct calculation for French/English
2. Translation-based calculation for Latin languages
3. Non-Latin script calculation
4. Fallback calculation

Each strategy returns a tuple: (is_in_domain, score, details)
"""

import logging
import re
from utils.types import Dict, Tuple, Optional
from utils.utilities import METRICS

from .models import DomainScore
from .config import LANGUAGE_ADJUSTMENTS, FALLBACK_UNIVERSAL_TERMS
from .query_normalizer import QueryNormalizer
from .context_analyzer import ContextAnalyzer
from .domain_calculator import DomainCalculator
from .translation_handler import TranslationHandler

logger = logging.getLogger(__name__)


class OODStrategy:
    """
    OOD calculation strategies orchestrator.

    This class implements the four main strategies for calculating out-of-domain
    scores based on the query language and context:

    1. Direct calculation: For French/English queries (no translation needed)
    2. Translation-based: For Latin languages (Spanish, German, etc.)
    3. Non-Latin script: For Hindi, Chinese, Thai, Arabic
    4. Fallback: When other methods fail or service unavailable

    Attributes:
        domain_calculator: Calculator for domain relevance analysis
        translation_handler: Handler for translation service
        language_adjustments: Language-specific threshold adjustments
    """

    def __init__(
        self,
        domain_calculator: DomainCalculator,
        translation_handler: TranslationHandler,
        language_adjustments: Dict[str, float] = None,
    ):
        """
        Initialize the OOD strategy orchestrator.

        Args:
            domain_calculator: Domain calculator instance for relevance analysis
            translation_handler: Translation handler for query translation
            language_adjustments: Optional custom language adjustments (default: from config)
        """
        self.domain_calculator = domain_calculator
        self.translation_handler = translation_handler
        self.language_adjustments = language_adjustments or LANGUAGE_ADJUSTMENTS

    def calculate_direct(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Direct OOD calculation for French/English (no translation needed).

        This is the primary strategy for French and English queries. It performs
        full analysis without translation overhead:
        1. Normalize query
        2. Analyze context
        3. Calculate domain relevance
        4. Detect blocked terms
        5. Apply context boosters
        6. Select adaptive threshold
        7. Make final decision

        Args:
            query: User query string
            intent_result: Optional intent detection result
            language: Language code ("fr" or "en")

        Returns:
            Tuple of (is_in_domain, score, details):
                - is_in_domain: Boolean decision
                - score: Boosted domain score
                - details: Dictionary with comprehensive scoring details

        Example:
            >>> strategy = OODStrategy(domain_calc, translation_handler)
            >>> is_in_domain, score, details = strategy.calculate_direct(
            ...     "Quel est le meilleur FCR pour Ross 308?",
            ...     None,
            ...     "fr"
            ... )
            >>> is_in_domain
            True
            >>> details["method"]
            'direct'
        """
        # Step 1: Normalize query
        normalized_query = QueryNormalizer.normalize_query(query, language)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query", "language": language}

        # Step 2: Analyze context
        context_analysis = ContextAnalyzer.analyze_query_context(
            normalized_query, words, intent_result
        )

        # Step 3: Calculate domain relevance
        domain_analysis = self.domain_calculator.calculate_domain_relevance(
            words, context_analysis, language
        )

        # Step 4: Detect blocked terms
        blocked_analysis = self.domain_calculator.detect_blocked_terms(
            normalized_query, words
        )

        # Step 5: Apply context boosters
        boosted_score = self.domain_calculator.apply_context_boosters(
            domain_analysis.final_score, context_analysis, intent_result
        )

        # Step 6: Select adaptive threshold
        base_threshold = self.domain_calculator.select_adaptive_threshold(
            context_analysis, domain_analysis
        )
        adjusted_threshold = base_threshold * self.language_adjustments.get(
            language, 1.0
        )

        # Step 7: Make final decision
        is_in_domain = (
            boosted_score > adjusted_threshold and not blocked_analysis["is_blocked"]
        )

        # Step 8: Log decision and update metrics
        self._log_ood_decision(
            query,
            domain_analysis,
            boosted_score,
            adjusted_threshold,
            is_in_domain,
            language,
        )
        self._update_ood_metrics(domain_analysis, adjusted_threshold, is_in_domain)

        # Step 9: Build detailed response
        score_details = {
            "vocab_score": domain_analysis.final_score,
            "boosted_score": boosted_score,
            "threshold_used": adjusted_threshold,
            "base_threshold": base_threshold,
            "language_adjustment": self.language_adjustments.get(language, 1.0),
            "domain_words_found": len(domain_analysis.domain_words),
            "blocked_terms_found": len(domain_analysis.blocked_terms),
            "context_type": context_analysis["type"],
            "relevance_level": domain_analysis.relevance_level.value,
            "reasoning": domain_analysis.reasoning,
            "language": language,
            "translation_used": False,
            "method": "direct",
        }

        return is_in_domain, boosted_score, score_details

    def calculate_with_translation(
        self, query: str, intent_result=None, language: str = "es"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        OOD calculation with translation for Latin languages.

        This strategy is used for Latin-script languages other than French/English
        (Spanish, German, Italian, Portuguese, etc.). It translates the query to
        French and then applies direct analysis:
        1. Check translation service availability
        2. Translate query to French
        3. Perform direct analysis on translated query
        4. Apply translation confidence penalty to threshold
        5. Make final decision with translation context

        Args:
            query: User query string
            intent_result: Optional intent detection result
            language: Source language code (e.g., "es", "de", "it")

        Returns:
            Tuple of (is_in_domain, score, details):
                - is_in_domain: Boolean decision
                - score: Boosted domain score
                - details: Dictionary including translation metadata

        Note:
            Falls back to calculate_fallback() if translation service unavailable
        """
        # Check translation service availability
        if not self.translation_handler.is_available():
            logger.debug(
                f"Service traduction indisponible, utilisation fallback pour langue {language}"
            )
            return self.calculate_fallback(query, intent_result, language)

        try:
            # Translate query to French
            translation_result = self.translation_handler.translate_query(
                query, "fr", source_lang=language, domain="general_poultry"
            )

            translated_query = translation_result.text
            translation_confidence = translation_result.confidence

            logger.debug(
                f"Traduction [{language}→fr]: '{query[:30]}...' → '{translated_query[:30]}...' "
                f"(confiance: {translation_confidence:.2f})"
            )

            # Perform direct analysis on translated query
            is_in_domain, score, details = self.calculate_direct(
                translated_query, intent_result, "fr"
            )

            # Apply translation confidence penalty to threshold
            # Lower confidence = higher threshold (more strict)
            translation_penalty = 1.0 - (0.3 * (1.0 - translation_confidence))
            adjusted_threshold = details["threshold_used"] * translation_penalty
            is_in_domain = score > adjusted_threshold

            # Enrich details with translation metadata
            details.update(
                {
                    "original_language": language,
                    "original_query": query,
                    "translated_query": translated_query,
                    "translation_used": True,
                    "translation_confidence": translation_confidence,
                    "translation_penalty": translation_penalty,
                    "final_threshold": adjusted_threshold,
                    "translation_source": translation_result.source,
                    "method": "translation",
                }
            )

            # Log with translation context
            self._log_ood_decision(
                query,
                None,
                score,
                adjusted_threshold,
                is_in_domain,
                language,
                translated_query,
            )

            return is_in_domain, score, details

        except Exception as e:
            logger.debug(f"Erreur traduction {language}: {e}, utilisation fallback")
            return self.calculate_fallback(query, intent_result, language)

    def calculate_non_latin(
        self, query: str, intent_result=None, language: str = "hi"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        OOD calculation for non-Latin scripts (Hindi, Chinese, Thai, Arabic).

        This strategy handles queries in non-Latin scripts with a hybrid approach:
        1. First detect universal patterns (brand names, numbers with units)
        2. If universal patterns detected with high score, accept immediately
        3. Otherwise attempt translation if service available
        4. Fall back to permissive analysis if translation fails

        Universal patterns include:
        - Brand names (Cobb, Ross, Hubbard)
        - Numerical patterns with units (kg, days, %)
        - Language-specific poultry terms

        Args:
            query: User query string in non-Latin script
            intent_result: Optional intent detection result
            language: Language code ("hi", "zh", "th", "ar", etc.)

        Returns:
            Tuple of (is_in_domain, score, details):
                - is_in_domain: Boolean decision
                - score: Universal pattern or domain score
                - details: Dictionary with method used and reasoning
        """
        # Step 1: Detect universal patterns first
        universal_score = self.domain_calculator.detect_universal_patterns(
            query, language
        )

        if universal_score > 0.3:
            # High universal pattern score = likely poultry-related
            logger.debug(
                f"Patterns universels détectés [{language}]: score {universal_score:.2f}"
            )
            return (
                True,
                universal_score,
                {
                    "language": language,
                    "method": "universal_patterns",
                    "universal_score": universal_score,
                    "reasoning": f"Patterns aviculture universels détectés (score: {universal_score:.2f})",
                    "translation_used": False,
                },
            )

        # Step 2: Try translation if service available
        if self.translation_handler.is_available():
            try:
                return self.calculate_with_translation(query, intent_result, language)
            except Exception as e:
                logger.debug(f"Traduction échouée pour {language}: {e}")

        # Step 3: Fallback to permissive analysis
        return self.calculate_fallback(query, intent_result, language)

    def calculate_fallback(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Fallback OOD calculation with multilingual vocabulary.

        This is the most permissive strategy, used when:
        - Translation service is unavailable
        - Other strategies fail
        - Non-Latin script with no universal patterns

        Uses a multilingual vocabulary of universal terms and patterns:
        - Genetic line names (Ross, Cobb, Hubbard, etc.)
        - Universal metrics (FCR, ADG, etc.)
        - Multilingual poultry terms (chicken, poulet, pollo, 鸡, etc.)
        - Numerical patterns with units

        Args:
            query: User query string
            intent_result: Optional intent detection result (unused in fallback)
            language: Language code for threshold adjustment

        Returns:
            Tuple of (is_in_domain, score, details):
                - is_in_domain: Boolean decision (permissive)
                - score: Match score based on universal terms
                - details: Dictionary with matched terms and reasoning

        Note:
            This method is intentionally permissive to avoid false negatives
            when translation or full analysis is not available.
        """
        logger.debug(f"OOD Fallback [{language}]: '{query[:30]}...'")

        # Basic analysis with extended multilingual vocabulary
        query_lower = query.lower()
        domain_score = 0.0
        matched_terms = []

        # Search for universal terms
        for term in FALLBACK_UNIVERSAL_TERMS:
            if term in query_lower:
                domain_score += 0.3
                matched_terms.append(term)

        # Boost for numerical values (likely technical)
        # Age patterns: 35j, 35 days, 35 días, 35 天, etc.
        if re.search(r"\b\d+\s*(?:j|day|días?|jours?|天|يوم)\b", query_lower):
            domain_score += 0.4
            matched_terms.append("age_numeric")

        # Weight patterns: 2.5kg, 2500g, etc.
        if re.search(r"\b\d+\.?\d*\s*(?:kg|g|lb|%)\b", query_lower):
            domain_score += 0.3
            matched_terms.append("weight_numeric")

        # Determine adjusted threshold by language
        # More permissive for non-Latin scripts
        base_threshold = 0.30 if language in ["hi", "zh", "th", "ar"] else 0.20
        language_adjustment = self.language_adjustments.get(language, 0.80)
        adjusted_threshold = base_threshold * language_adjustment

        is_in_domain = domain_score >= adjusted_threshold

        details = {
            "method": "fallback",
            "language": language,
            "score": domain_score,
            "threshold_used": adjusted_threshold,
            "base_threshold": base_threshold,
            "language_adjustment": language_adjustment,
            "matched_terms": matched_terms,
            "term_count": len(matched_terms),
            "translation_used": False,
            "fallback_reason": "translation_service_unavailable",
        }

        # Log decision
        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"
        logger.info(
            f"OOD Fallback [{language}]: '{query[:30]}...' | "
            f"Score: {domain_score:.3f} | {decision}"
        )

        return is_in_domain, domain_score, details

    # ===== HELPER METHODS =====

    def _log_ood_decision(
        self,
        query: str,
        domain_analysis: Optional[DomainScore],
        score: float,
        threshold: float,
        is_in_domain: bool,
        language: str,
        translated_query: str = None,
    ) -> None:
        """
        Log OOD decision with multilingual support.

        Logs the OOD decision in a consistent format, including translation
        information if applicable.

        Args:
            query: Original query string
            domain_analysis: Domain analysis result (can be None for translation cases)
            score: Final calculated score
            threshold: Threshold used for decision
            is_in_domain: Boolean decision result
            language: Query language code
            translated_query: Optional translated query (for translation method)

        Note:
            Uses logger.debug() to avoid cluttering production logs.
        """
        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"

        if translated_query:
            # Log with translation information
            logger.debug(
                f"OOD {decision} [{language}]: '{query[:30]}...' → '{translated_query[:30]}...' | "
                f"Score: {score:.3f} vs {threshold:.3f}"
            )
        else:
            # Log without translation
            logger.debug(
                f"OOD {decision} [{language}]: '{query[:40]}...' | "
                f"Score: {score:.3f} vs {threshold:.3f}"
            )

    def _update_ood_metrics(
        self,
        domain_analysis: Optional[DomainScore],
        threshold: float,
        is_in_domain: bool,
    ) -> None:
        """
        Update OOD metrics for monitoring.

        Reports OOD decisions to the global metrics system for monitoring
        and analytics purposes.

        Args:
            domain_analysis: Domain analysis result (can be None)
            threshold: Threshold used for decision
            is_in_domain: Boolean decision result

        Note:
            Gracefully handles errors to prevent metrics from breaking detection.
        """
        try:
            if is_in_domain:
                score_value = domain_analysis.final_score if domain_analysis else 0.5
                relevance = (
                    domain_analysis.relevance_level.value
                    if domain_analysis
                    else "unknown"
                )
                METRICS.ood_accepted(score_value, relevance)
            else:
                score_value = domain_analysis.final_score if domain_analysis else 0.0
                METRICS.ood_filtered(score_value, "threshold_not_met")
        except Exception as e:
            logger.warning(f"Erreur MAJ métriques OOD: {e}")
