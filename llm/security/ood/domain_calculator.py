# -*- coding: utf-8 -*-
"""
domain_calculator.py - Domain relevance calculation logic

This module handles all domain-related calculations including relevance scoring,
blocked term detection, universal pattern recognition, context boosting, and
adaptive threshold selection.
"""

import logging
import re
from utils.types import Dict, List, Set
from .models import DomainRelevance, DomainScore

logger = logging.getLogger(__name__)


# Weight multipliers for domain relevance levels
WEIGHT_MULTIPLIERS = {
    DomainRelevance.HIGH: 1.0,
    DomainRelevance.MEDIUM: 0.6,
    DomainRelevance.LOW: 0.3,
    DomainRelevance.GENERIC: 0.1,
}


class DomainCalculator:
    """
    Calculator for domain relevance analysis.

    This class is responsible for calculating domain relevance scores,
    detecting blocked terms, recognizing universal patterns, applying
    context boosters, and selecting adaptive thresholds.

    Attributes:
        domain_vocabulary: Hierarchical vocabulary mapping relevance levels to term sets
        blocked_terms: Dictionary of blocked terms by category
        adaptive_thresholds: Threshold values for different query types
    """

    def __init__(
        self,
        domain_vocabulary: Dict[DomainRelevance, Set[str]],
        blocked_terms: Dict[str, List[str]],
        adaptive_thresholds: Dict[str, float] = None,
    ):
        """
        Initialize the domain calculator.

        Args:
            domain_vocabulary: Hierarchical vocabulary for domain classification
            blocked_terms: Dictionary of blocked terms by category
            adaptive_thresholds: Optional custom thresholds for query types
        """
        self.domain_vocabulary = domain_vocabulary
        self.blocked_terms = blocked_terms

        # Default adaptive thresholds
        self.adaptive_thresholds = adaptive_thresholds or {
            "technical_query": 0.10,
            "numeric_query": 0.15,
            "standard_query": 0.20,
            "generic_query": 0.30,
            "suspicious_query": 0.50,
        }

    def calculate_domain_relevance(
        self, words: List[str], context_analysis: Dict, language: str
    ) -> DomainScore:
        """
        Calculate domain relevance score for a query.

        Analyzes words against the domain vocabulary hierarchy and calculates
        a weighted relevance score with contextual adjustments.

        Args:
            words: Tokenized and normalized query words
            context_analysis: Context analysis result from ContextAnalyzer
            language: Language code of the query

        Returns:
            DomainScore with detailed scoring information
        """
        domain_words = []
        relevance_scores = {level: 0 for level in DomainRelevance}

        # Analyze word by word against vocabulary
        for word in words:
            word_clean = word.strip().lower()
            if len(word_clean) < 2:
                continue

            for level, vocabulary in self.domain_vocabulary.items():
                if word_clean in vocabulary:
                    domain_words.append(word_clean)
                    relevance_scores[level] += 1
                    break

        # Calculate weighted score
        weighted_score = sum(
            count * WEIGHT_MULTIPLIERS.get(level, 0.1)
            for level, count in relevance_scores.items()
            if level != DomainRelevance.BLOCKED
        )

        significant_words = [w for w in words if len(w.strip()) >= 2]
        base_score = weighted_score / len(significant_words) if significant_words else 0

        # Determine overall relevance level
        if relevance_scores[DomainRelevance.HIGH] >= 2:
            overall_relevance = DomainRelevance.HIGH
        elif (
            relevance_scores[DomainRelevance.HIGH] >= 1
            or relevance_scores[DomainRelevance.MEDIUM] >= 2
        ):
            overall_relevance = DomainRelevance.MEDIUM
        elif (
            sum(
                relevance_scores[level]
                for level in [
                    DomainRelevance.HIGH,
                    DomainRelevance.MEDIUM,
                    DomainRelevance.LOW,
                ]
            )
            >= 1
        ):
            overall_relevance = DomainRelevance.LOW
        else:
            overall_relevance = DomainRelevance.GENERIC

        # Contextual bonus
        context_bonus = 0.0
        if context_analysis["type"] == "technical_query":
            context_bonus += 0.15
        if len(context_analysis.get("technical_indicators", [])) >= 1:
            context_bonus += 0.1

        final_score = min(1.0, base_score + context_bonus)

        confidence_boosters = {
            "context_bonus": context_bonus,
            "high_relevance_words": relevance_scores[DomainRelevance.HIGH],
            "medium_relevance_words": relevance_scores[DomainRelevance.MEDIUM],
            "technical_indicators": len(
                context_analysis.get("technical_indicators", [])
            ),
        }

        reasoning = (
            f"Mots domaine: {len(domain_words)}/{len(significant_words)} | "
            f"Niveau: {overall_relevance.value} | Score: {final_score:.3f}"
        )

        return DomainScore(
            final_score=final_score,
            relevance_level=overall_relevance,
            domain_words=domain_words,
            blocked_terms=[],
            confidence_boosters=confidence_boosters,
            threshold_applied=0.0,
            reasoning=reasoning,
            original_language=language,
        )

    def detect_blocked_terms(self, query: str, words: List[str]) -> Dict:
        """
        Detect blocked/inappropriate terms in the query.

        Scans the query for terms from the blocked terms dictionary across
        all categories.

        Args:
            query: The query string (normalized)
            words: Tokenized query words

        Returns:
            Dictionary with blocking information:
                - is_blocked: Whether query should be blocked
                - blocked_terms: List of detected blocked terms
                - block_score: Ratio of blocked terms to total words
        """
        blocked_found = []
        for category, terms in self.blocked_terms.items():
            for term in terms:
                if term.lower() in query:
                    blocked_found.append(term)

        is_blocked = len(blocked_found) >= 2

        return {
            "is_blocked": is_blocked,
            "blocked_terms": blocked_found,
            "block_score": len(blocked_found) / max(len(words), 1),
        }

    def detect_universal_patterns(self, query: str, language: str) -> float:
        """
        Detect universal poultry patterns for non-Latin languages.

        Recognizes technical terms and patterns that are universal across
        languages (brand names, numerical patterns, etc.).

        Args:
            query: The query string
            language: Language code

        Returns:
            Universal pattern score (0.0 to 1.0)
        """
        score = 0.0

        # Universal brands (same spelling across languages)
        universal_brands = ["cobb", "ross", "hubbard", "isa", "lohmann"]
        brand_matches = sum(
            1 for brand in universal_brands if brand.lower() in query.lower()
        )
        score += brand_matches * 0.4

        # Numbers with units (universal patterns)
        weight_patterns = [
            r"\d+\s*(?:g|kg|gram|kilogram|公斤|克|किलो|ग्राम)",
            r"\d+\s*(?:day|jour|วัน|天|दिन|hari)",
            r"\d+\s*%",
        ]

        for pattern in weight_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 0.15

        # Language-specific technical terms
        if language == "hi":
            hindi_terms = ["मुर्गी", "चिकन", "कॉब", "रॉस", "वजन", "दिन", "अंडा"]
            hindi_matches = sum(1 for term in hindi_terms if term in query)
            score += hindi_matches * 0.3

        elif language == "zh":
            chinese_terms = ["鸡", "鸡肉", "肉鸡", "蛋鸡", "科宝", "罗斯", "体重", "天"]
            chinese_matches = sum(1 for term in chinese_terms if term in query)
            score += chinese_matches * 0.3

        elif language == "th":
            thai_terms = ["ไก่", "เนื้อไก่", "คอบบ์", "รอสส์", "น้ำหนัก", "วัน", "ไข่"]
            thai_matches = sum(1 for term in thai_terms if term in query)
            score += thai_matches * 0.3

        return min(1.0, score)

    def apply_context_boosters(
        self, base_score: float, context_analysis: Dict, intent_result=None
    ) -> float:
        """
        Apply contextual boosters to the base domain score.

        Enhances the score based on technical indicators, query type,
        and intent confidence.

        Args:
            base_score: Base domain relevance score
            context_analysis: Context analysis result
            intent_result: Optional intent detection result

        Returns:
            Boosted score (capped at 0.98)
        """
        boosted_score = base_score

        if context_analysis["type"] == "technical_query":
            boosted_score += 0.15

        technical_count = len(context_analysis.get("technical_indicators", []))
        if technical_count >= 2:
            boosted_score += 0.1
        elif technical_count == 1:
            boosted_score += 0.05

        if context_analysis.get("intent_confidence", 0.0) > 0.8:
            boosted_score += 0.1

        return min(0.98, boosted_score)

    def select_adaptive_threshold(
        self, context_analysis: Dict, domain_analysis: DomainScore
    ) -> float:
        """
        Select an adaptive threshold based on query context.

        Dynamically adjusts the acceptance threshold based on the type
        and specificity of the query.

        Args:
            context_analysis: Context analysis result
            domain_analysis: Domain relevance analysis result

        Returns:
            Adaptive threshold value (0.05 to 0.6)
        """
        base_threshold = self.adaptive_thresholds.get(
            context_analysis["type"], self.adaptive_thresholds["standard_query"]
        )

        # Adjustments based on context
        if (
            context_analysis.get("specificity_level") == "low"
            and domain_analysis.relevance_level == DomainRelevance.GENERIC
        ):
            base_threshold += 0.1

        if len(context_analysis.get("technical_indicators", [])) >= 2:
            base_threshold -= 0.05

        return max(0.05, min(0.6, base_threshold))
