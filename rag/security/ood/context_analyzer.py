# -*- coding: utf-8 -*-
"""
context_analyzer.py - Query context analysis for OOD detection
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
context_analyzer.py - Query context analysis for OOD detection

This module contains the ContextAnalyzer class responsible for analyzing
the context of user queries to classify query types and detect technical
indicators that influence domain relevance scoring.
"""

import logging
import re
from utils.types import Dict, List
from .config import TECHNICAL_PATTERNS

logger = logging.getLogger(__name__)


class ContextAnalyzer:
    """
    Static utility class for analyzing query context.

    Provides methods to detect technical indicators, classify query types,
    and determine specificity levels. This contextual information is used
    to apply adaptive thresholds and boost domain relevance scores.
    """

    @staticmethod
    def analyze_query_context(query: str, words: List[str], intent_result=None) -> Dict:
        """
        Perform comprehensive context analysis on a query.

        Analyzes the query to determine:
        - Query type (technical, standard, generic)
        - Technical indicators present (metrics, measurements, genetic lines)
        - Specificity level (very_high, high, medium, low)
        - Intent confidence (if intent_result provided)

        Args:
            query: Normalized query string
            words: List of words from the query (tokenized)
            intent_result: Optional intent detection result with confidence and entities

        Returns:
            Dict containing:
                - type: str - Query classification ("technical_query", "standard_query", etc.)
                - technical_indicators: List[Dict] - Detected technical patterns
                - numeric_indicators: List[Dict] - Detected numeric patterns (legacy)
                - specificity_level: str - Level of query specificity
                - intent_confidence: float - Confidence from intent detection (0.0 if unavailable)

        Example:
            >>> context = ContextAnalyzer.analyze_query_context(
            ...     "ross 308 at 35 days weight",
            ...     ["ross", "308", "at", "35", "days", "weight"],
            ...     None
            ... )
            >>> context["type"]
            'technical_query'
            >>> len(context["technical_indicators"])
            2  # genetic_line and age_specification
        """
        context = {
            "type": "standard_query",
            "technical_indicators": [],
            "numeric_indicators": [],  # For backward compatibility
            "specificity_level": "medium",
            "intent_confidence": 0.0,
        }

        # ===== Step 1: Detect technical indicators =====

        technical_indicators = ContextAnalyzer._detect_technical_indicators(query)
        context["technical_indicators"] = technical_indicators

        # Also populate numeric_indicators for backward compatibility
        # (Extract only numeric-type indicators)
        context["numeric_indicators"] = [
            ind
            for ind in technical_indicators
            if ind["type"]
            in ["age_specification", "weight_measure", "percentage_value"]
        ]

        # ===== Step 2: Classify query type =====

        if len(technical_indicators) >= 2:
            # Multiple technical indicators = technical query
            context["type"] = "technical_query"
            context["specificity_level"] = "high"
        elif len(technical_indicators) == 1:
            # Single technical indicator = borderline technical
            context["type"] = "standard_query"
            context["specificity_level"] = "medium"
        else:
            # No technical indicators = standard or generic
            context["type"] = "standard_query"
            context["specificity_level"] = "medium"

        # ===== Step 3: Analyze intent result if available =====

        if intent_result:
            try:
                # Extract intent confidence
                if hasattr(intent_result, "confidence"):
                    context["intent_confidence"] = float(intent_result.confidence)

                # Check for detected entities (further boost specificity)
                if hasattr(intent_result, "detected_entities"):
                    entities = intent_result.detected_entities
                    if isinstance(entities, dict) and len(entities) >= 2:
                        # Multiple entities detected = very specific query
                        context["type"] = "technical_query"
                        context["specificity_level"] = "very_high"

            except Exception as e:
                logger.debug(f"Error analyzing intent result: {e}")

        return context

    @staticmethod
    def _detect_technical_indicators(query: str) -> List[Dict]:
        """
        Detect technical indicators in the query using pattern matching.

        Scans the query for technical patterns defined in TECHNICAL_PATTERNS
        configuration, including:
        - Conversion metrics (FCR, IC, etc.)
        - Genetic line names (Ross, Cobb, Hubbard, etc.)
        - Age specifications with units (days, weeks)
        - Weight measurements with units (g, kg)
        - Percentage values

        Args:
            query: Normalized query string

        Returns:
            List of dicts, each containing:
                - type: str - Type of indicator (e.g., "genetic_line")
                - matches: List[str] - Matched strings
                - count: int - Number of matches

        Example:
            >>> indicators = ContextAnalyzer._detect_technical_indicators(
            ...     "cobb 500 at 42 days has 2.5 kg weight"
            ... )
            >>> len(indicators)
            3  # genetic_line, age_specification, weight_measure
            >>> indicators[0]["type"]
            'genetic_line'
            >>> indicators[0]["matches"]
            ['cobb 500']
        """
        technical_indicators = []

        for pattern, indicator_type in TECHNICAL_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                technical_indicators.append(
                    {
                        "type": indicator_type,
                        "matches": matches,
                        "count": len(matches),
                    }
                )

        return technical_indicators
