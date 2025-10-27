# -*- coding: utf-8 -*-
"""
adaptive_length.py - Adaptive Response Length Calculator
Version: 1.4.1
Last modified: 2025-10-27
Migrated from ai-service to llm service
"""
"""
Dynamically determines optimal max_tokens based on query complexity.

Simple question → Simple answer (300-500 tokens)
Complex question → Detailed answer (800-1500 tokens)
"""

import logging
import re
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels"""

    VERY_SIMPLE = "very_simple"  # 200-400 tokens
    SIMPLE = "simple"  # 400-600 tokens
    MODERATE = "moderate"  # 600-900 tokens
    COMPLEX = "complex"  # 900-1200 tokens
    VERY_COMPLEX = "very_complex"  # 1200-1500 tokens


class AdaptiveResponseLength:
    """
    Calculates optimal max_tokens based on query complexity

    Complexity factors:
    1. Query length (words)
    2. Number of entities
    3. Query type (comparative, temporal, etc.)
    4. Number of context documents
    5. Presence of lists/comparisons/steps
    6. Domain complexity

    Usage:
        calculator = AdaptiveResponseLength()

        max_tokens = calculator.calculate_max_tokens(
            query="Quel poids pour Ross 308 ?",
            entities={"breed": "Ross 308"},
            query_type="standard",
            context_docs=[...],
            domain="production"
        )

        # Returns: 400 (simple query)
    """

    def __init__(self):
        """Initialize adaptive length calculator"""

        # Token ranges per complexity level
        self.token_ranges = {
            QueryComplexity.VERY_SIMPLE: (200, 400),
            QueryComplexity.SIMPLE: (400, 600),
            QueryComplexity.MODERATE: (600, 900),
            QueryComplexity.COMPLEX: (900, 1200),
            QueryComplexity.VERY_COMPLEX: (1200, 1500),
        }

        # Keywords that indicate need for longer response
        self.complexity_keywords = {
            "comparative": [
                "comparer",
                "compare",
                "différence",
                "difference",
                "versus",
                "vs",
                "meilleur",
                "best",
                "entre",
                "between",
            ],
            "procedural": [
                "comment",
                "how",
                "étapes",
                "steps",
                "procédure",
                "procedure",
                "protocole",
                "protocol",
                "processus",
                "process",
            ],
            "explanatory": [
                "pourquoi",
                "why",
                "expliquer",
                "explain",
                "raison",
                "reason",
                "causes",
                "consequences",
            ],
            "listing": [
                "liste",
                "list",
                "tous",
                "all",
                "quels",
                "which",
                "exemples",
                "examples",
            ],
            "analytical": [
                "analyser",
                "analyze",
                "évaluer",
                "evaluate",
                "diagnostic",
                "diagnosis",
                "optimiser",
                "optimize",
            ],
        }

        logger.info("✅ AdaptiveResponseLength initialized")

    def calculate_max_tokens(
        self,
        query: str,
        entities: Optional[Dict[str, Any]] = None,
        query_type: Optional[str] = None,
        context_docs: Optional[List[Dict]] = None,
        domain: Optional[str] = None,
        **kwargs,
    ) -> int:
        """
        Calculate optimal max_tokens for this query

        Args:
            query: User query
            entities: Extracted entities
            query_type: Query type (standard, comparative, temporal)
            context_docs: Retrieved context documents
            domain: Query domain

        Returns:
            Optimal max_tokens (200-1500)
        """

        # Calculate complexity score
        complexity = self._assess_complexity(
            query, entities, query_type, context_docs, domain
        )

        # Get token range for complexity level
        min_tokens, max_tokens = self.token_ranges[complexity]

        # Fine-tune within range based on specific factors
        final_tokens = self._fine_tune_tokens(
            query, entities, query_type, context_docs, min_tokens, max_tokens
        )

        logger.info(
            f"📏 Adaptive length: {final_tokens} tokens "
            f"(complexity={complexity.value}, query_len={len(query.split())} words)"
        )

        return final_tokens

    def _assess_complexity(
        self,
        query: str,
        entities: Optional[Dict[str, Any]],
        query_type: Optional[str],
        context_docs: Optional[List[Dict]],
        domain: Optional[str],
    ) -> QueryComplexity:
        """
        Assess overall query complexity

        Returns:
            QueryComplexity enum
        """

        score = 0
        factors = []

        # Factor 1: Query length (0-3 points)
        words = query.split()
        query_length = len(words)
        if query_length <= 5:
            score += 0
            factors.append(f"very_short={query_length}w")
        elif query_length <= 10:
            score += 1
            factors.append(f"short={query_length}w")
        elif query_length <= 20:
            score += 2
            factors.append(f"medium={query_length}w")
        else:
            score += 3
            factors.append(f"long={query_length}w")

        # Factor 2: Number of entities (0-2 points)
        entity_count = len(entities) if entities else 0
        if entity_count == 0:
            score += 1  # No entities = might be complex question
        elif entity_count == 1:
            score += 0  # Single entity = very simple
        elif entity_count == 2:
            score += 1  # Two entities = simple
            factors.append(f"entities={entity_count}")
        elif entity_count <= 4:
            score += 2  # Moderate
            factors.append(f"entities={entity_count}")
        else:
            score += 3  # Many entities = complex query
            factors.append(f"many_entities={entity_count}")

        # Factor 3: Query type (0-3 points)
        if query_type in ["comparative", "comparison"]:
            score += 3
            factors.append("comparative")
        elif query_type in ["temporal", "trend"]:
            score += 2
            factors.append("temporal")
        elif query_type in ["calculation", "optimization"]:
            score += 2
            factors.append("calculation")
        elif query_type in ["standard", "factual"]:
            score += 0

        # Factor 4: Context richness (0-2 points)
        doc_count = len(context_docs) if context_docs else 0
        if doc_count >= 5:
            score += 2  # Many docs = need synthesis
            factors.append(f"many_docs={doc_count}")
        elif doc_count >= 3:
            score += 1
        else:
            score += 0

        # Factor 5: Complexity keywords (0-3 points)
        keyword_score, keyword_types = self._check_complexity_keywords(query)
        score += keyword_score
        if keyword_types:
            factors.append(f"keywords={'+'.join(keyword_types)}")

        # Factor 6: Domain complexity (0-2 points)
        if domain in ["health", "santé", "veterinary"]:
            score += 2  # Health queries need detailed answers
            factors.append("health_domain")
        elif domain in ["nutrition", "genetics"]:
            score += 1
            factors.append("complex_domain")

        # Factor 7: Question marks (multiple questions)
        question_count = query.count("?")
        if question_count > 1:
            score += 2
            factors.append(f"multi_question={question_count}")

        # Factor 8: Lists/enumerations expected
        if self._expects_list(query):
            score += 2
            factors.append("expects_list")

        # Map score to complexity level
        # Score range: 0-22
        if score <= 1:
            complexity = QueryComplexity.VERY_SIMPLE
        elif score <= 4:
            complexity = QueryComplexity.SIMPLE
        elif score <= 8:
            complexity = QueryComplexity.MODERATE
        elif score <= 13:
            complexity = QueryComplexity.COMPLEX
        else:
            complexity = QueryComplexity.VERY_COMPLEX

        logger.debug(
            f"Complexity assessment: score={score}, level={complexity.value}, "
            f"factors=[{', '.join(factors)}]"
        )

        return complexity

    def _check_complexity_keywords(self, query: str) -> tuple[int, List[str]]:
        """
        Check for complexity keywords in query

        Returns:
            (score, keyword_types) tuple
        """
        query_lower = query.lower()
        score = 0
        found_types = []

        for keyword_type, keywords in self.complexity_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    if keyword_type not in found_types:
                        found_types.append(keyword_type)
                        score += 1
                    break

        # Cap at 3 points
        return min(score, 3), found_types

    def _expects_list(self, query: str) -> bool:
        """Check if query expects a list response"""

        list_indicators = [
            r"\bliste\b",
            r"\blist\b",
            r"\btous les\b",
            r"\ball\b",
            r"\bquels sont\b",
            r"\bwhat are\b",
            r"\bénumér",
            r"\benumer",
            r"\bexemples\b",
            r"\bexamples\b",
            r"\btypes de\b",
            r"\btypes of\b",
        ]

        query_lower = query.lower()
        for pattern in list_indicators:
            if re.search(pattern, query_lower):
                return True

        return False

    def _fine_tune_tokens(
        self,
        query: str,
        entities: Optional[Dict[str, Any]],
        query_type: Optional[str],
        context_docs: Optional[List[Dict]],
        min_tokens: int,
        max_tokens: int,
    ) -> int:
        """
        Fine-tune tokens within the range

        Returns:
            Final token count
        """

        # Start at midpoint
        tokens = (min_tokens + max_tokens) // 2

        # Adjust based on specific factors

        # If very short query (1-3 words), reduce
        if len(query.split()) <= 3:
            tokens = min_tokens + (max_tokens - min_tokens) // 4

        # If many context docs, increase (need synthesis)
        if context_docs and len(context_docs) >= 4:
            tokens = min_tokens + int((max_tokens - min_tokens) * 0.75)

        # If comparative query, increase significantly
        if query_type in ["comparative", "comparison"]:
            tokens = min_tokens + int((max_tokens - min_tokens) * 0.9)

        # If health domain and many entities, max out
        if entities and len(entities) >= 3:
            domain_keywords = ["symptôme", "maladie", "diagnostic", "traitement"]
            if any(kw in query.lower() for kw in domain_keywords):
                tokens = max_tokens

        # Ensure within bounds
        tokens = max(min_tokens, min(tokens, max_tokens))

        return tokens

    def get_complexity_info(
        self,
        query: str,
        entities: Optional[Dict[str, Any]] = None,
        query_type: Optional[str] = None,
        context_docs: Optional[List[Dict]] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed complexity analysis (for debugging/monitoring)

        Returns:
            {
                "complexity": "moderate",
                "max_tokens": 750,
                "token_range": (600, 900),
                "factors": {
                    "query_length": 12,
                    "entity_count": 3,
                    "query_type": "standard",
                    "doc_count": 4,
                    "keywords": ["procedural"],
                    "domain": "health"
                }
            }
        """

        complexity = self._assess_complexity(
            query, entities, query_type, context_docs, domain
        )
        token_range = self.token_ranges[complexity]
        max_tokens = self.calculate_max_tokens(
            query, entities, query_type, context_docs, domain
        )

        keyword_score, keyword_types = self._check_complexity_keywords(query)

        return {
            "complexity": complexity.value,
            "max_tokens": max_tokens,
            "token_range": token_range,
            "factors": {
                "query_length": len(query.split()),
                "entity_count": len(entities) if entities else 0,
                "query_type": query_type or "unknown",
                "doc_count": len(context_docs) if context_docs else 0,
                "keywords": keyword_types,
                "domain": domain or "unknown",
                "expects_list": self._expects_list(query),
            },
        }


# Singleton instance
_adaptive_length_instance = None


def get_adaptive_length() -> AdaptiveResponseLength:
    """Get or create AdaptiveResponseLength singleton"""
    global _adaptive_length_instance

    if _adaptive_length_instance is None:
        _adaptive_length_instance = AdaptiveResponseLength()

    return _adaptive_length_instance
