# -*- coding: utf-8 -*-
"""
query_decomposer.py - Query Decomposer for Complex Multi-Criteria Questions
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
query_decomposer.py - Query Decomposer for Complex Multi-Criteria Questions

Handles decomposition of complex queries into simpler sub-queries for better processing.

Example:
    Input: "Impact nutrition, température ET densité sur FCR mâles Ross 308 selon climat"

    Decomposition:
    1. "Impact nutrition sur FCR Ross 308 mâles"
    2. "Impact température sur FCR Ross 308 mâles"
    3. "Impact densité sur FCR Ross 308 mâles"
    4. Aggregation: "Synthèse impact nutrition, température, densité sur FCR Ross 308 mâles selon climat"

Version: 1.0 (Phase 3)
"""

import logging
import re
from dataclasses import dataclass
from utils.types import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SubQuery:
    """Represents a sub-query extracted from complex query"""

    query: str
    context: Dict[str, Any]
    priority: int = 1  # Execution priority (1=highest)


@dataclass
class DecompositionResult:
    """Result of query decomposition"""

    is_complex: bool
    original_query: str
    sub_queries: List[SubQuery]
    aggregation_strategy: str  # 'combine', 'compare', 'synthesize'


class QueryDecomposer:
    """
    Decomposes complex multi-criteria queries into simpler sub-queries

    Features:
    - Detects complexity patterns (AND, OR, multi-factors)
    - Extracts individual criteria/factors
    - Generates executable sub-queries
    - Provides aggregation strategy

    Example:
        >>> decomposer = QueryDecomposer()
        >>> result = decomposer.decompose("Impact nutrition et température sur FCR Ross 308")
        >>> print(len(result.sub_queries))  # 2 sub-queries
    """

    def __init__(self):
        """Initialize Query Decomposer"""

        # Complexity indicators
        self.complexity_patterns = [
            # Multi-factor patterns
            r"\b(et|and)\b.*\b(et|and)\b",  # "A et B et C"
            r"\b(ou|or)\b.*\b(ou|or)\b",  # "A ou B ou C"
            r",.*,",  # "A, B, C"
            # Impact/influence patterns
            r"impact.*\b(et|and|,)\b",  # "Impact A et B sur..."
            r"effet.*\b(et|and|,)\b",  # "Effet A et B sur..."
            r"influence.*\b(et|and|,)\b",  # "Influence A et B sur..."
            # Comparison with multiple criteria
            r"compar.*\b(et|and)\b.*\b(et|and)\b",
            # Multi-question patterns
            r"\?.*\?",  # Multiple questions
        ]

        # Factor extraction patterns
        self.factor_patterns = {
            "nutrition": r"\b(nutrition|aliment|feed|ration)\b",
            "temperature": r"\b(temp[ée]rature|climat|thermique)\b",
            "density": r"\b(densit[ée]|occupation|espace)\b",
            "lighting": r"\b([ée]clairage|lumi[èe]re|photoperiod)\b",
            "ventilation": r"\b(ventilation|a[ée]ration|air)\b",
            "humidity": r"\b(humidit[ée]|hygrom[ée]trie)\b",
            "age": r"\b([âa]ge|jour|day|semaine|week)\b",
            "sex": r"\b(m[âa]le|femelle|male|female|sexe)\b",
            "breed": r"\b(race|souche|breed|ross|cobb|hubbard)\b",
        }

        # Conjunctions and separators
        self.conjunctions = ["et", "and", "ou", "or", ",", ";"]

    def detect_complexity(self, query: str) -> bool:
        """
        Detect if query is complex and needs decomposition

        Args:
            query: User query

        Returns:
            True if query is complex (multi-criteria)
        """
        query_lower = query.lower()

        # Check complexity patterns
        for pattern in self.complexity_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Complexity detected: pattern '{pattern}'")
                return True

        # Check multiple factors mentioned
        factors_found = sum(
            1
            for pattern in self.factor_patterns.values()
            if re.search(pattern, query_lower)
        )

        if factors_found >= 3:
            logger.debug(f"Complexity detected: {factors_found} factors found")
            return True

        return False

    def extract_factors(self, query: str) -> List[str]:
        """
        Extract individual factors/criteria from query

        Args:
            query: User query

        Returns:
            List of factor names found in query
        """
        query_lower = query.lower()
        factors = []

        for factor_name, pattern in self.factor_patterns.items():
            if re.search(pattern, query_lower):
                factors.append(factor_name)

        logger.debug(f"Factors extracted: {factors}")
        return factors

    def extract_multi_factors_explicit(self, query: str) -> List[str]:
        """
        Extract explicitly listed factors (e.g., "nutrition, température et densité")

        Args:
            query: User query

        Returns:
            List of factor phrases
        """
        query_lower = query.lower()

        # Pattern: "A, B et C" or "A and B and C"
        # Look for segments between conjunctions

        # First, try to find the list portion
        # Common patterns: "impact ... sur" or "effet ... sur"
        impact_match = re.search(
            r"(impact|effet|influence)\s+(?:de\s+|d\')?(.+?)\s+sur", query_lower
        )

        if impact_match:
            factors_text = impact_match.group(2)

            # Split by conjunctions
            # Replace conjunctions with delimiter
            for conj in [" et ", " and ", " ou ", " or "]:
                factors_text = factors_text.replace(conj, "|")
            factors_text = factors_text.replace(",", "|")

            # Split and clean
            factors = [f.strip() for f in factors_text.split("|") if f.strip()]

            logger.debug(f"Explicit factors extracted: {factors}")
            return factors

        return []

    def decompose(self, query: str) -> DecompositionResult:
        """
        Decompose complex query into sub-queries

        Args:
            query: Complex user query

        Returns:
            DecompositionResult with sub-queries and aggregation strategy
        """
        # Check if decomposition needed
        if not self.detect_complexity(query):
            logger.info("Query is not complex, no decomposition needed")
            return DecompositionResult(
                is_complex=False,
                original_query=query,
                sub_queries=[SubQuery(query=query, context={}, priority=1)],
                aggregation_strategy="none",
            )

        logger.info(f"Decomposing complex query: '{query}'")

        # Extract factors
        explicit_factors = self.extract_multi_factors_explicit(query)
        detected_factors = self.extract_factors(query)

        # Use explicit if available, otherwise detected
        factors = explicit_factors if explicit_factors else detected_factors

        if not factors:
            logger.warning("No factors extracted, treating as simple query")
            return DecompositionResult(
                is_complex=False,
                original_query=query,
                sub_queries=[SubQuery(query=query, context={}, priority=1)],
                aggregation_strategy="none",
            )

        # Extract base question (what is being asked)
        base_question = self._extract_base_question(query)

        # Generate sub-queries for each factor
        sub_queries = []
        for idx, factor in enumerate(factors):
            sub_query_text = self._generate_subquery(query, factor, base_question)
            sub_queries.append(
                SubQuery(
                    query=sub_query_text,
                    context={"factor": factor, "index": idx},
                    priority=1,
                )
            )

        # Determine aggregation strategy
        aggregation = self._determine_aggregation_strategy(query, factors)

        logger.info(
            f"Decomposed into {len(sub_queries)} sub-queries, strategy: {aggregation}"
        )

        return DecompositionResult(
            is_complex=True,
            original_query=query,
            sub_queries=sub_queries,
            aggregation_strategy=aggregation,
        )

    def _extract_base_question(self, query: str) -> Dict[str, Any]:
        """
        Extract the base question components (metric, target, etc.)

        Args:
            query: Original query

        Returns:
            Dict with base question components
        """
        base = {}
        query_lower = query.lower()

        # Extract metric being asked about
        metrics = {
            "fcr": r"\b(fcr|icg|conversion|indice)\b",
            "weight": r"\b(poids|weight|masse)\b",
            "gain": r"\b(gain|croissance|growth)\b",
            "mortality": r"\b(mortalit[ée]|mortality|survie)\b",
            "production": r"\b(production|ponte|egg)\b",
        }

        for metric, pattern in metrics.items():
            if re.search(pattern, query_lower):
                base["metric"] = metric
                break

        # Extract target (breed, age, sex)
        breed_match = re.search(r"\b(ross|cobb|hubbard)\s*\d+", query_lower)
        if breed_match:
            base["breed"] = breed_match.group(0)

        age_match = re.search(r"(\d+)\s*(jour|day|j)", query_lower)
        if age_match:
            base["age"] = age_match.group(1)

        sex_match = re.search(r"\b(m[âa]les?|femelles?|males?|females?)\b", query_lower)
        if sex_match:
            base["sex"] = sex_match.group(0)

        return base

    def _generate_subquery(
        self, original_query: str, factor: str, base: Dict[str, Any]
    ) -> str:
        """
        Generate a sub-query for a single factor

        Args:
            original_query: Original complex query
            factor: Factor to focus on
            base: Base question components

        Returns:
            Generated sub-query text
        """
        # Build sub-query from components
        parts = []

        # Question word
        if "impact" in original_query.lower():
            parts.append(f"Impact {factor}")
        elif "effet" in original_query.lower():
            parts.append(f"Effet {factor}")
        else:
            parts.append(f"Impact {factor}")

        # Metric
        if base.get("metric"):
            parts.append(f"sur {base['metric']}")

        # Target
        if base.get("breed"):
            parts.append(base["breed"])
        if base.get("sex"):
            parts.append(base["sex"])
        if base.get("age"):
            parts.append(f"{base['age']} jours")

        sub_query = " ".join(parts)
        logger.debug(f"Generated sub-query: '{sub_query}' for factor '{factor}'")

        return sub_query

    def _determine_aggregation_strategy(self, query: str, factors: List[str]) -> str:
        """
        Determine how to aggregate results from sub-queries

        Args:
            query: Original query
            factors: List of factors

        Returns:
            Aggregation strategy: 'combine', 'compare', 'synthesize'
        """
        query_lower = query.lower()

        # Check for comparison indicators
        if re.search(r"\b(compar|versus|vs|diff[ée]rence)\b", query_lower):
            return "compare"

        # Check for synthesis indicators
        if re.search(r"\b(synth[èe]se|global|ensemble|overall)\b", query_lower):
            return "synthesize"

        # Default: combine results
        return "combine"

    def execute_subqueries(
        self, sub_queries: List[SubQuery], query_executor_fn
    ) -> List[Dict[str, Any]]:
        """
        Execute all sub-queries and collect results

        Args:
            sub_queries: List of sub-queries to execute
            query_executor_fn: Function to execute a single query
                              Should accept (query: str) and return Dict[str, Any]

        Returns:
            List of results, one per sub-query
        """
        results = []

        logger.info(f"Executing {len(sub_queries)} sub-queries")

        for idx, sub_query in enumerate(sub_queries):
            try:
                logger.debug(
                    f"Executing sub-query {idx+1}/{len(sub_queries)}: '{sub_query.query}'"
                )

                # Execute sub-query
                result = query_executor_fn(sub_query.query)

                # Attach context
                result["sub_query_context"] = sub_query.context
                result["sub_query_index"] = idx

                results.append(result)

                logger.debug(f"Sub-query {idx+1} executed successfully")

            except Exception as e:
                logger.error(f"Error executing sub-query {idx+1}: {e}")
                results.append(
                    {
                        "error": str(e),
                        "sub_query": sub_query.query,
                        "sub_query_context": sub_query.context,
                        "sub_query_index": idx,
                    }
                )

        logger.info(
            f"Executed {len(results)} sub-queries ({len([r for r in results if 'error' not in r])} successful)"
        )

        return results

    def aggregate_results(
        self, results: List[Dict[str, Any]], strategy: str, original_query: str
    ) -> Dict[str, Any]:
        """
        Aggregate results from sub-queries into final answer

        Args:
            results: List of results from sub-queries
            strategy: Aggregation strategy ('combine', 'compare', 'synthesize')
            original_query: Original complex query

        Returns:
            Aggregated result
        """
        logger.info(f"Aggregating {len(results)} results with strategy '{strategy}'")

        # Filter out errors
        valid_results = [r for r in results if "error" not in r]

        if not valid_results:
            logger.error("No valid results to aggregate")
            return {
                "error": "All sub-queries failed",
                "sub_results": results,
                "strategy": strategy,
            }

        if strategy == "combine":
            return self._aggregate_combine(valid_results, original_query)
        elif strategy == "compare":
            return self._aggregate_compare(valid_results, original_query)
        elif strategy == "synthesize":
            return self._aggregate_synthesize(valid_results, original_query)
        else:
            # Default: simple combination
            return self._aggregate_combine(valid_results, original_query)

    def _aggregate_combine(
        self, results: List[Dict[str, Any]], original_query: str
    ) -> Dict[str, Any]:
        """Combine results by listing each factor's impact"""
        combined = {
            "aggregation_type": "combine",
            "original_query": original_query,
            "sub_results": results,
            "summary": [],
        }

        for result in results:
            factor = result.get("sub_query_context", {}).get("factor", "unknown")
            combined["summary"].append(
                {
                    "factor": factor,
                    "result": result.get("answer", result.get("content", "N/A")),
                }
            )

        logger.debug(f"Combined {len(results)} results")
        return combined

    def _aggregate_compare(
        self, results: List[Dict[str, Any]], original_query: str
    ) -> Dict[str, Any]:
        """Compare results to show differences/similarities"""
        comparison = {
            "aggregation_type": "compare",
            "original_query": original_query,
            "sub_results": results,
            "comparisons": [],
        }

        # Compare pairs of results
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                factor_a = (
                    results[i].get("sub_query_context", {}).get("factor", f"Factor {i}")
                )
                factor_b = (
                    results[j].get("sub_query_context", {}).get("factor", f"Factor {j}")
                )

                comparison["comparisons"].append(
                    {
                        "factor_a": factor_a,
                        "factor_b": factor_b,
                        "result_a": results[i].get(
                            "answer", results[i].get("content", "N/A")
                        ),
                        "result_b": results[j].get(
                            "answer", results[j].get("content", "N/A")
                        ),
                    }
                )

        logger.debug(f"Compared {len(comparison['comparisons'])} pairs")
        return comparison

    def _aggregate_synthesize(
        self, results: List[Dict[str, Any]], original_query: str
    ) -> Dict[str, Any]:
        """Synthesize results into unified answer"""
        synthesis = {
            "aggregation_type": "synthesize",
            "original_query": original_query,
            "sub_results": results,
            "synthesis_parts": [],
        }

        # Extract key insights from each result
        for result in results:
            factor = result.get("sub_query_context", {}).get("factor", "unknown")
            answer = result.get("answer", result.get("content", "N/A"))

            synthesis["synthesis_parts"].append({"factor": factor, "insight": answer})

        # Placeholder for LLM-based synthesis (Phase 3.x)
        synthesis["needs_llm_synthesis"] = True

        logger.debug(f"Synthesized {len(results)} results")
        return synthesis


# Singleton instance
_decomposer_instance: Optional[QueryDecomposer] = None


def get_query_decomposer() -> QueryDecomposer:
    """
    Get singleton instance of QueryDecomposer

    Returns:
        QueryDecomposer instance
    """
    global _decomposer_instance
    if _decomposer_instance is None:
        _decomposer_instance = QueryDecomposer()
        logger.debug("QueryDecomposer singleton initialized")
    return _decomposer_instance


__all__ = ["QueryDecomposer", "SubQuery", "DecompositionResult", "get_query_decomposer"]
