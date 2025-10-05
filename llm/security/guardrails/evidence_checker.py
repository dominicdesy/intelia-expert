# -*- coding: utf-8 -*-
"""
evidence_checker.py - Evidence checking and support verification for guardrails

This module provides evidence-based verification methods extracted from advanced_guardrails.py
for cleaner code organization and reusability.

Classes:
    EvidenceChecker: Async methods for checking evidence support in responses
"""

import asyncio
import re
import logging
from utils.types import Dict, List, Tuple
from .text_analyzer import TextAnalyzer

logger = logging.getLogger(__name__)


class EvidenceChecker:
    """
    Evidence checking utilities for guardrails verification.

    This class provides async methods for verifying that claims and statements
    in responses are properly supported by source documents.

    Methods:
        _check_evidence_support: Verify documentary support for response claims
        _find_enhanced_claim_support: Find support for specific claims in documents
        _quick_document_overlap: Calculate quick overlap between response and document
    """

    def __init__(self):
        """Initialize the EvidenceChecker."""
        # Evidence indicators for detecting explicit references
        self.evidence_indicators = [
            # Explicit references
            r"selon le document|d'après les données|les résultats montrent",
            r"d'après l'étude|selon l'analyse|les mesures indiquent",
            r"tableau \d+|figure \d+|source\s*:|référence\s*:",
            r"page \d+|section \d+|annexe \d+",
            # Scientific terms
            r"étude de|essai|test|mesure|observation|expérience",
            r"recherche|analyse|évaluation|examen|investigation",
            r"protocole|méthodologie|procédure|standard",
            # Quantitative data with context
            r"les données montrent|les chiffres révèlent|l'analyse démontre",
            r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|semaine|°C|kcal)\s+(?:mesurés?|observés?|enregistrés?)",
        ]

    async def _check_evidence_support(
        self, response: str, context_docs: List[Dict]
    ) -> Tuple[float, Dict]:
        """
        Verify optimized documentary support for response.

        Extracts factual claims from the response and verifies each claim
        against the provided context documents in parallel. Calculates an
        evidence score based on how well claims are supported.

        Args:
            response: The response text to verify
            context_docs: List of context documents with 'content' field

        Returns:
            Tuple containing:
                - evidence_score (float): Score from 0.0 to 1.0 indicating support level
                - details (Dict): Detailed breakdown of evidence analysis including:
                    - total_claims: Number of factual claims extracted
                    - supported_claims: Number of well-supported claims
                    - evidence_indicators: Count of explicit evidence markers
                    - support_distribution: Strong/moderate/weak support counts

        Example:
            >>> checker = EvidenceChecker()
            >>> score, details = await checker._check_evidence_support(
            ...     "Ross 308 atteint 2.5kg en 42 jours",
            ...     [{"content": "Ross 308 broiler weight: 2.5kg at day 42"}]
            ... )
            >>> score > 0.7
            True
        """
        try:
            if not context_docs:
                return 0.1, {"no_documents": True}

            # Enhanced extraction of factual claims
            claims = self._extract_enhanced_factual_claims(response)

            if not claims:
                return 0.5, {"no_factual_claims": True}

            # Parallel verification of support for each claim
            support_tasks = [
                self._find_enhanced_claim_support(claim, context_docs)
                for claim in claims
            ]

            support_scores = await asyncio.gather(
                *support_tasks, return_exceptions=True
            )

            # Calculate evidence score with weighting
            valid_scores = [
                s
                for s in support_scores
                if not isinstance(s, Exception) and s is not None
            ]

            if not valid_scores:
                evidence_score = 0.3
            else:
                # Weighted score: favors well-supported claims
                strong_support = sum(1 for s in valid_scores if s > 0.7)
                moderate_support = sum(1 for s in valid_scores if 0.4 <= s <= 0.7)
                weak_support = sum(1 for s in valid_scores if s < 0.4)

                evidence_score = (
                    strong_support * 1.0 + moderate_support * 0.6 + weak_support * 0.2
                ) / len(valid_scores)

            # Bonus for explicit evidence indicators
            evidence_indicators_found = sum(
                1
                for pattern in self.evidence_indicators
                if re.search(pattern, response.lower(), re.IGNORECASE)
            )

            if evidence_indicators_found > 0:
                evidence_score = min(
                    1.0, evidence_score + 0.1 * evidence_indicators_found
                )

            return evidence_score, {
                "total_claims": len(claims),
                "supported_claims": len([s for s in valid_scores if s > 0.6]),
                "evidence_indicators": evidence_indicators_found,
                "support_distribution": {
                    "strong": strong_support if valid_scores else 0,
                    "moderate": moderate_support if valid_scores else 0,
                    "weak": weak_support if valid_scores else 0,
                },
            }

        except Exception as e:
            logger.warning(f"Erreur vérification evidence: {e}")
            return 0.5, {"error": str(e)}

    async def _find_enhanced_claim_support(
        self, claim: str, context_docs: List[Dict]
    ) -> float:
        """
        Search for enhanced support of a claim with semantic similarity.

        Analyzes each document for support of the given claim using:
        - Lexical similarity (word overlap)
        - Key element matching (numbers, technical terms)
        - Fuzzy matching for variations

        Args:
            claim: The claim text to verify
            context_docs: List of context documents to search

        Returns:
            float: Maximum support score found (0.0 to 1.0), where:
                - 0.9-1.0: Strong direct match found
                - 0.6-0.9: Good lexical and key element overlap
                - 0.3-0.6: Moderate overlap
                - 0.0-0.3: Weak or no support

        Example:
            >>> checker = EvidenceChecker()
            >>> score = await checker._find_enhanced_claim_support(
            ...     "FCR de 1.65 pour Ross 308",
            ...     [{"content": "Ross 308 achieves FCR of 1.65"}]
            ... )
            >>> score > 0.8
            True
        """
        try:
            max_support = 0.0
            claim_words = set(TextAnalyzer._normalize_text(claim).split())

            # Extract key elements from the claim
            key_elements = TextAnalyzer._extract_key_elements(claim)

            for doc in context_docs:
                content = doc.get("content", "")
                if not content:
                    continue

                content_normalized = TextAnalyzer._normalize_text(content)
                content_words = set(content_normalized.split())

                # Basic lexical similarity
                if claim_words and content_words:
                    overlap = len(claim_words.intersection(content_words))
                    lexical_similarity = overlap / len(claim_words)

                    # Bonus for key elements
                    key_matches = sum(
                        1 for key in key_elements if key in content_normalized
                    )
                    key_bonus = (
                        (key_matches / len(key_elements)) * 0.3 if key_elements else 0
                    )

                    similarity = min(1.0, lexical_similarity + key_bonus)
                    max_support = max(max_support, similarity)

                # Check direct presence with variations
                if TextAnalyzer._fuzzy_match(claim, content):
                    max_support = max(max_support, 0.9)

            return min(1.0, max_support)

        except Exception as e:
            logger.warning(f"Erreur recherche support claim: {e}")
            return 0.3

    async def _quick_document_overlap(self, response: str, doc: Dict) -> float:
        """
        Calculate quick overlap between response and a document.

        Performs fast word-based overlap calculation using normalized text
        comparison. Useful for quick filtering or preliminary verification.

        Args:
            response: The response text
            doc: Document dictionary with 'content' field

        Returns:
            float: Overlap ratio (0.0 to 1.0) calculated as:
                intersection_size / min(response_words, content_words)

        Example:
            >>> checker = EvidenceChecker()
            >>> overlap = await checker._quick_document_overlap(
            ...     "Ross 308 performance FCR",
            ...     {"content": "Ross 308 broiler FCR performance data"}
            ... )
            >>> overlap > 0.5
            True
        """
        try:
            content = doc.get("content", "")
            if not content:
                return 0.0

            response_words = set(TextAnalyzer._normalize_text(response).split())
            content_words = set(TextAnalyzer._normalize_text(content).split())

            if not response_words or not content_words:
                return 0.0

            overlap = len(response_words.intersection(content_words))
            return overlap / min(len(response_words), len(content_words))

        except Exception:
            return 0.0

    def _extract_enhanced_factual_claims(self, response: str) -> List[str]:
        """
        Extract enhanced factual claims from response.

        Identifies sentences containing factual information based on patterns
        such as numeric values, metrics, recommendations, classifications,
        genetic lines, and technical parameters.

        Args:
            response: The response text to analyze

        Returns:
            List[str]: List of sentences containing factual claims

        Note:
            This is a helper method used internally by _check_evidence_support.
            Sentences shorter than 15 characters are filtered out.
        """
        claims = []

        # Segment into sentences preserving context
        sentences = re.split(r"(?<=[.!?])\s+", response)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue

            # Patterns to identify factual claims
            factual_patterns = [
                r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|°C|kcal)",  # Numeric values
                r"(?:poids|fcr|mortalité|ponte|croissance)\s+(?:de|est|atteint)",  # Metrics
                r"(?:recommandé|optimal|maximum|minimum|idéal)\s+(?:est|de)",  # Recommendations
                r"(?:lignée|espèce|phase|âge)\s+\w+",  # Classifications
                r"(?:ross|cobb|hubbard|isa)\s*\d*",  # Genetic lines
                r"(?:température|densité|ventilation)\s+(?:de|doit|optimal)",  # Technical parameters
            ]

            for pattern in factual_patterns:
                if re.search(pattern, sentence.lower(), re.IGNORECASE):
                    claims.append(sentence)
                    break

        return claims
