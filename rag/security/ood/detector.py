# -*- coding: utf-8 -*-
"""
detector.py - Main OOD Detector Orchestrator
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
detector.py - Main OOD Detector Orchestrator

This module contains the main OODDetector class which orchestrates all
OOD detection components. It is a simple coordinator that delegates to
specialized modules for vocabulary building, translation, normalization,
context analysis, and domain calculation.
"""

import logging
import os
import json
from utils.types import Dict, List, Tuple, Optional

# Import configuration
from config.config import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

# Import utilities
from utils.utilities import detect_language_enhanced, METRICS

# Import OOD modules
from .models import DomainScore
from .config import (
    ADAPTIVE_THRESHOLDS,
    LANGUAGE_ADJUSTMENTS,
    FALLBACK_BLOCKED_TERMS,
)
from .translation_handler import TranslationHandler
from .vocabulary_builder import VocabularyBuilder
from .domain_calculator import DomainCalculator
from .query_normalizer import QueryNormalizer
from .context_analyzer import ContextAnalyzer

logger = logging.getLogger(__name__)


class OODDetector:
    """
    Main orchestrator for Out-Of-Domain detection.

    This class coordinates all OOD detection components and provides
    the main public API for multilingual OOD detection.

    Public Methods:
        - calculate_ood_score_multilingual(): Main entry point with language detection
        - calculate_ood_score(): Legacy entry point for backward compatibility
        - get_detector_stats(): Return detector statistics
        - test_query_analysis(): Test and diagnose queries
    """

    def __init__(self, blocked_terms_path: str = None):
        """
        Initialize the OOD detector with all components.

        Args:
            blocked_terms_path: Optional path to blocked terms JSON file
        """
        # Load blocked terms
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)

        # Initialize translation handler
        self.translation_handler = TranslationHandler(
            supported_languages=SUPPORTED_LANGUAGES
        )

        # Initialize vocabulary builder and build vocabulary
        if self.translation_handler.is_available():
            self.domain_vocabulary = VocabularyBuilder.build_from_service(
                translation_service=self.translation_handler.service,
                supported_languages=SUPPORTED_LANGUAGES,
            )
        else:
            self.domain_vocabulary = VocabularyBuilder.build_fallback()

        # Initialize domain calculator
        self.domain_calculator = DomainCalculator(
            domain_vocabulary=self.domain_vocabulary,
            blocked_terms=self.blocked_terms,
            adaptive_thresholds=ADAPTIVE_THRESHOLDS,
        )

        # Store configuration
        self.supported_languages = SUPPORTED_LANGUAGES
        self.default_language = DEFAULT_LANGUAGE
        self.language_adjustments = LANGUAGE_ADJUSTMENTS

        logger.debug(
            f"OODDetector initialized with {len(self.supported_languages)} languages"
        )

    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """
        Load blocked terms from JSON file with fallback.

        Args:
            path: Optional path to blocked terms file

        Returns:
            Dictionary of blocked terms by category
        """
        if path is None:
            possible_paths = [
                os.getenv("BLOCKED_TERMS_FILE", ""),
                "/app/config/blocked_terms.json",
                "config/blocked_terms.json",
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "config",
                    "blocked_terms.json",
                ),
            ]
        else:
            possible_paths = [path]

        for attempt_path in possible_paths:
            if not attempt_path or not os.path.exists(attempt_path):
                continue
            try:
                with open(attempt_path, "r", encoding="utf-8") as f:
                    blocked_terms = json.load(f)
                logger.info(f"Termes bloqués chargés depuis: {attempt_path}")
                return blocked_terms
            except Exception as e:
                logger.warning(f"Erreur lecture {attempt_path}: {e}")
                continue

        # Fallback to default blocked terms
        logger.warning(
            f"Utilisation des termes bloqués fallback: {len(FALLBACK_BLOCKED_TERMS)} catégories"
        )
        return FALLBACK_BLOCKED_TERMS

    # ===== PUBLIC METHODS =====

    def calculate_ood_score_multilingual(
        self, query: str, intent_result=None, language: str = None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Main entry point for multilingual OOD detection.

        Automatically detects the language if not provided and routes to
        the appropriate OOD calculation strategy.

        Args:
            query: The user query to analyze
            intent_result: Optional intent detection result
            language: Optional language code (auto-detected if None)

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        # Automatic language detection if needed
        if language is None:
            detection_result = detect_language_enhanced(query)
            language = detection_result.language
            logger.debug(
                f"Langue détectée automatiquement: {language} "
                f"(confiance: {detection_result.confidence:.2f})"
            )

        # Validate supported language
        actual_language = (
            language.language if hasattr(language, "language") else language
        )
        if actual_language not in self.supported_languages:
            logger.warning(
                f"Langue non supportée: {actual_language}, "
                f"utilisation fallback {self.default_language}"
            )
            language = self.default_language
        else:
            language = actual_language

        # Route to appropriate strategy
        return self._calculate_ood_score_for_language(query, intent_result, language)

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Legacy entry point for OOD detection.

        Provided for backward compatibility. Uses the default language.

        Args:
            query: The user query to analyze
            intent_result: Optional intent detection result

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        return self.calculate_ood_score_multilingual(
            query, intent_result, self.default_language
        )

    def get_detector_stats(self) -> Dict:
        """
        Get detector statistics.

        Returns:
            Dictionary with detector statistics including vocabulary size,
            blocked terms count, configuration, and service status
        """
        vocab_stats = {
            level.value: len(terms) for level, terms in self.domain_vocabulary.items()
        }
        blocked_stats = {
            category: len(terms) for category, terms in self.blocked_terms.items()
        }

        return {
            "version": "multilingual_v2.1_refactored",
            "vocabulary_stats": vocab_stats,
            "blocked_terms_stats": blocked_stats,
            "adaptive_thresholds": ADAPTIVE_THRESHOLDS.copy(),
            "language_adjustments": self.language_adjustments.copy(),
            "supported_languages": list(self.supported_languages),
            "translation_service_available": self.translation_handler.is_available(),
            "translation_service_healthy": self.translation_handler.is_healthy(),
            "total_domain_terms": sum(
                len(terms) for terms in self.domain_vocabulary.values()
            ),
            "integration_features": [
                "universal_translation_service_with_fallback",
                "dynamic_vocabulary_from_dict",
                "language_specific_analysis",
                "unicode_script_preservation",
                "adaptive_thresholds_by_language",
                "robust_error_handling",
            ],
        }

    def test_query_analysis(self, query: str, language: str = None) -> Dict:
        """
        Test and diagnose a query.

        Provides detailed analysis of how a query is processed for debugging
        and diagnostic purposes.

        Args:
            query: The query to test
            language: Optional language code (auto-detected if None)

        Returns:
            Dictionary with detailed analysis results
        """
        is_in_domain, score, details = self.calculate_ood_score_multilingual(
            query, None, language
        )

        return {
            "original_query": query,
            "detected_language": details.get("language", "unknown"),
            "final_score": score,
            "is_in_domain": is_in_domain,
            "decision": "ACCEPTED" if is_in_domain else "REJECTED",
            "method": details.get("method", "unknown"),
            "translation_used": details.get("translation_used", False),
            "details": details,
        }

    # ===== PRIVATE METHODS =====

    def _calculate_ood_score_for_language(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Calculate OOD score using language-specific strategy.

        Routes the query to the appropriate calculation strategy based on
        the detected language.

        Args:
            query: The user query
            intent_result: Optional intent detection result
            language: Language code

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        try:
            # Strategy selection based on language
            if language in ["fr", "en"]:
                # Main languages: direct processing (optimized)
                return self._calculate_ood_direct(query, intent_result, language)

            elif language in ["es", "de", "it", "pt", "nl", "pl", "id"]:
                # Latin/European languages: translation via service
                return self._calculate_ood_with_translation(
                    query, intent_result, language
                )

            else:
                # Non-Latin scripts: adapted analysis + fallback
                return self._calculate_ood_non_latin(query, intent_result, language)

        except Exception as e:
            logger.error(f"Erreur calcul OOD pour langue {language}: {e}")
            return self._calculate_ood_fallback(query, intent_result, language)

    def _calculate_ood_direct(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Direct OOD calculation for French/English (no translation needed).

        Args:
            query: The user query
            intent_result: Optional intent detection result
            language: Language code ('fr' or 'en')

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        # Normalization adapted to language
        normalized_query = QueryNormalizer.normalize_query(query, language)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query", "language": language}

        # Context analysis
        context_analysis = ContextAnalyzer.analyze_query_context(
            normalized_query, words, intent_result
        )

        # Domain analysis
        domain_analysis = self.domain_calculator.calculate_domain_relevance(
            words, context_analysis, language
        )

        # Blocked terms detection
        blocked_analysis = self.domain_calculator.detect_blocked_terms(
            normalized_query, words
        )

        # Apply context boosters
        boosted_score = self.domain_calculator.apply_context_boosters(
            domain_analysis.final_score, context_analysis, intent_result
        )

        # Select adaptive threshold
        base_threshold = self.domain_calculator.select_adaptive_threshold(
            context_analysis, domain_analysis
        )
        adjusted_threshold = base_threshold * self.language_adjustments.get(
            language, 1.0
        )

        # Final decision
        is_in_domain = (
            boosted_score > adjusted_threshold and not blocked_analysis["is_blocked"]
        )

        # Logging and metrics
        self._log_ood_decision(
            query,
            domain_analysis,
            boosted_score,
            adjusted_threshold,
            is_in_domain,
            language,
        )
        self._update_ood_metrics(domain_analysis, adjusted_threshold, is_in_domain)

        # Build detailed response
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

    def _calculate_ood_with_translation(
        self, query: str, intent_result=None, language: str = "es"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        OOD calculation with translation for Latin/European languages.

        Args:
            query: The user query
            intent_result: Optional intent detection result
            language: Language code

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        if not self.translation_handler.is_available():
            logger.debug(
                f"Service traduction indisponible, utilisation fallback pour langue {language}"
            )
            return self._calculate_ood_fallback(query, intent_result, language)

        try:
            # Translate to French via universal service
            translation_result = self.translation_handler.translate_query(
                query, "fr", source_lang=language, domain="general_poultry"
            )

            translated_query = translation_result.text
            translation_confidence = translation_result.confidence

            logger.debug(
                f"Traduction [{language}→fr]: '{query[:30]}...' → "
                f"'{translated_query[:30]}...' (confiance: {translation_confidence:.2f})"
            )

            # OOD analysis on translated version
            is_in_domain, score, details = self._calculate_ood_direct(
                translated_query, intent_result, "fr"
            )

            # Adjust threshold for translations
            translation_penalty = 1.0 - (0.3 * (1.0 - translation_confidence))
            adjusted_threshold = details["threshold_used"] * translation_penalty
            is_in_domain = score > adjusted_threshold

            # Enrich details
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
            return self._calculate_ood_fallback(query, intent_result, language)

    def _calculate_ood_non_latin(
        self, query: str, intent_result=None, language: str = "hi"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        OOD calculation for non-Latin script languages (Hindi, Chinese, Thai).

        Args:
            query: The user query
            intent_result: Optional intent detection result
            language: Language code

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        # Detect universal patterns first
        universal_score = self.domain_calculator.detect_universal_patterns(
            query, language
        )

        if universal_score > 0.3:
            # High score on universal patterns = probably poultry
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

        # Otherwise, try translation if service available
        if self.translation_handler.is_available():
            try:
                return self._calculate_ood_with_translation(
                    query, intent_result, language
                )
            except Exception as e:
                logger.debug(f"Traduction échouée pour {language}: {e}")

        # Fallback: permissive analysis
        return self._calculate_ood_fallback(query, intent_result, language)

    def _calculate_ood_fallback(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Fallback OOD calculation with extended multilingual vocabulary.

        Used when translation service is unavailable or other strategies fail.

        Args:
            query: The user query
            intent_result: Optional intent detection result
            language: Language code

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        import re
        from .config import FALLBACK_UNIVERSAL_TERMS

        logger.debug(f"OOD Fallback [{language}]: '{query[:30]}...'")

        # Basic analysis with extended multilingual vocabulary
        query_lower = query.lower()
        domain_score = 0.0
        matched_terms = []

        # Search for relevant terms
        for term in FALLBACK_UNIVERSAL_TERMS:
            if term in query_lower:
                domain_score += 0.3
                matched_terms.append(term)

        # Boost for numeric values (probably technical)
        if re.search(r"\b\d+\s*(?:j|day|días?|jours?|天|يوم)\b", query_lower):
            domain_score += 0.4
            matched_terms.append("age_numeric")

        if re.search(r"\b\d+\.?\d*\s*(?:kg|g|lb|%)\b", query_lower):
            domain_score += 0.3
            matched_terms.append("weight_numeric")

        # Determine adjusted threshold by language
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

    # ===== LOGGING AND METRICS =====

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

        Args:
            query: Original query
            domain_analysis: Domain analysis result
            score: Final score
            threshold: Threshold used
            is_in_domain: Decision result
            language: Language code
            translated_query: Optional translated query
        """
        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"

        if translated_query:
            logger.debug(
                f"OOD {decision} [{language}]: '{query[:30]}...' → "
                f"'{translated_query[:30]}...' | Score: {score:.3f} vs {threshold:.3f}"
            )
        else:
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
        Update OOD metrics.

        Args:
            domain_analysis: Domain analysis result
            threshold: Threshold used
            is_in_domain: Decision result
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
