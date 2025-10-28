"""
Model Router - Intelligent Model Selection for Speed/Quality Trade-off

This module provides intelligent routing between different LLM models:
- Llama 3.2 3B: Fast model for simple queries (2500ms)
- Llama 3.1 8B: Accurate model for complex queries (4500ms)

Routing Strategy:
1. Simple queries → Always 3B (fast)
2. Complex queries → Always 8B (accurate)
3. Medium queries → A/B test (configurable ratio)

Expected Impact:
- 60% queries → 3B: Average latency 3300ms (-27%)
- 40% queries → 8B: Maintains quality on complex queries
- Cost reduction: -30%
"""

import hashlib
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ModelSize(Enum):
    """Available model sizes"""
    SMALL = "3b"   # Llama 3.2 3B - Fast
    LARGE = "8b"   # Llama 3.1 8B - Accurate


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"      # Factual, single-answer queries
    MEDIUM = "medium"      # Standard queries with context
    COMPLEX = "complex"    # Multi-step reasoning, comparisons


class ModelRouter:
    """
    Intelligent model routing based on query complexity

    Routing Rules:
    - Simple (40-50% queries): Always 3B (2500ms, quality: 95%)
    - Medium (40-50% queries): A/B test 3B/8B (tunable ratio)
    - Complex (5-10% queries): Always 8B (4500ms, quality: 100%)
    """

    # Model configurations
    MODELS = {
        ModelSize.SMALL: {
            "name": "meta-llama/Llama-3.2-3B-Instruct",
            "avg_latency_ms": 2500,
            "quality_score": 0.92,
            "cost_per_1k_tokens": 0.0001,
            "max_tokens": 128000,
            "best_for": ["simple factual", "single metric", "straightforward context"]
        },
        ModelSize.LARGE: {
            "name": "meta-llama/Llama-3.1-8B-Instruct",
            "avg_latency_ms": 4500,
            "quality_score": 1.0,
            "cost_per_1k_tokens": 0.0002,
            "max_tokens": 128000,
            "best_for": ["complex reasoning", "comparisons", "nuanced questions"]
        }
    }

    def __init__(
        self,
        ab_test_ratio: float = 0.5,
        enable_routing: bool = True,
        default_model: ModelSize = ModelSize.LARGE
    ):
        """
        Initialize model router

        Args:
            ab_test_ratio: Ratio of medium queries to route to 3B (0.0 = all 8B, 1.0 = all 3B)
            enable_routing: Enable intelligent routing (False = always use default)
            default_model: Default model if routing disabled
        """
        self.ab_test_ratio = ab_test_ratio
        self.enable_routing = enable_routing
        self.default_model = default_model

        # Statistics tracking
        self.stats = {
            ModelSize.SMALL: {"count": 0, "total_ms": 0},
            ModelSize.LARGE: {"count": 0, "total_ms": 0}
        }

        logger.info(
            f"🧭 ModelRouter initialized: "
            f"routing={'enabled' if enable_routing else 'disabled'}, "
            f"ab_ratio={ab_test_ratio}"
        )

    def determine_complexity(
        self,
        query: str,
        query_type: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        context_docs: Optional[list] = None
    ) -> QueryComplexity:
        """
        Determine query complexity based on multiple signals

        Simple queries:
        - Single metric lookup (breed + age + metric)
        - Factual questions with clear answer
        - Query type: genetics_performance, metric_query (single value)
        - Examples: "Weight of Ross 308 at 21 days?"

        Medium queries:
        - Standard questions with context
        - Query types: nutrition_query, health_diagnosis, farm_management
        - Multiple entities but straightforward
        - Examples: "How to improve FCR for Ross 308?"

        Complex queries:
        - Comparisons (multiple breeds, ages, metrics)
        - Multi-step reasoning
        - Ambiguous or open-ended questions
        - Query type: comparative, diagnostic_synthesis
        - Examples: "Compare Ross 308 vs Cobb 500 at 21, 28, 35 days"

        Args:
            query: User query text
            query_type: Classified query type
            entities: Extracted entities (breed, age, etc.)
            context_docs: Retrieved context documents

        Returns:
            QueryComplexity enum
        """
        query_lower = query.lower()

        # === COMPLEX QUERIES ===
        complex_indicators = [
            "compare", "comparison", "vs", "versus", "difference between",
            "which is better", "pros and cons", "advantages disadvantages",
            "multiple", "several", "various", "different"
        ]

        if any(indicator in query_lower for indicator in complex_indicators):
            logger.debug(f"🔴 COMPLEX: Comparison/multi-entity detected")
            return QueryComplexity.COMPLEX

        # Check for multiple values in entities (comparison)
        if entities:
            for key, value in entities.items():
                if isinstance(value, str) and ',' in value:
                    # Multiple breeds/ages = comparison
                    logger.debug(f"🔴 COMPLEX: Multiple entities in {key}: {value}")
                    return QueryComplexity.COMPLEX

        # Query type based complexity
        complex_query_types = [
            "comparative",
            "diagnostic_synthesis",
            "multi_metric_synthesis"
        ]

        if query_type in complex_query_types:
            logger.debug(f"🔴 COMPLEX: Query type = {query_type}")
            return QueryComplexity.COMPLEX

        # === SIMPLE QUERIES ===
        simple_query_types = [
            "genetics_performance",
            "metric_query"
        ]

        # Check for simple metric lookup pattern
        has_breed = entities and entities.get("breed")
        has_age = entities and entities.get("age_days")
        has_metric = entities and entities.get("metric_type")

        if query_type in simple_query_types and has_breed and has_age:
            logger.debug(f"🟢 SIMPLE: Single metric lookup (breed={has_breed}, age={has_age})")
            return QueryComplexity.SIMPLE

        # Short factual questions
        if len(query.split()) <= 10 and ('?' in query or 'what' in query_lower or 'how much' in query_lower):
            logger.debug(f"🟢 SIMPLE: Short factual question ({len(query.split())} words)")
            return QueryComplexity.SIMPLE

        # === MEDIUM (DEFAULT) ===
        logger.debug(f"🟡 MEDIUM: Standard query")
        return QueryComplexity.MEDIUM

    def select_model(
        self,
        complexity: QueryComplexity,
        query: str,
        query_hash: Optional[str] = None
    ) -> ModelSize:
        """
        Select optimal model based on complexity

        Routing Rules:
        - SIMPLE → Always 3B (fast, high quality for simple tasks)
        - COMPLEX → Always 8B (accurate, handles complexity)
        - MEDIUM → A/B test based on ab_test_ratio

        Args:
            complexity: Determined query complexity
            query: User query (for logging)
            query_hash: Optional hash for consistent A/B assignment

        Returns:
            ModelSize enum (SMALL or LARGE)
        """
        if not self.enable_routing:
            logger.debug(f"🔀 Routing disabled, using default: {self.default_model.value}")
            return self.default_model

        # Simple queries → Always fast model
        if complexity == QueryComplexity.SIMPLE:
            logger.info(f"🟢 ROUTE → 3B (SIMPLE): '{query[:60]}...'")
            return ModelSize.SMALL

        # Complex queries → Always accurate model
        if complexity == QueryComplexity.COMPLEX:
            logger.info(f"🔴 ROUTE → 8B (COMPLEX): '{query[:60]}...'")
            return ModelSize.LARGE

        # Medium queries → A/B test
        # Use consistent hashing for same query to always get same model
        if query_hash is None:
            query_hash = hashlib.md5(query.encode()).hexdigest()

        # Convert hash to 0.0-1.0 range
        hash_value = int(query_hash[:8], 16) / 0xFFFFFFFF

        if hash_value < self.ab_test_ratio:
            logger.info(f"🟡 ROUTE → 3B (MEDIUM A/B: {hash_value:.2f} < {self.ab_test_ratio}): '{query[:60]}...'")
            return ModelSize.SMALL
        else:
            logger.info(f"🟡 ROUTE → 8B (MEDIUM A/B: {hash_value:.2f} >= {self.ab_test_ratio}): '{query[:60]}...'")
            return ModelSize.LARGE

    def get_model_name(self, model_size: ModelSize) -> str:
        """Get HuggingFace model ID for given size"""
        return self.MODELS[model_size]["name"]

    def get_model_info(self, model_size: ModelSize) -> Dict[str, Any]:
        """Get complete model information"""
        return self.MODELS[model_size].copy()

    def record_usage(self, model_size: ModelSize, latency_ms: int):
        """Record model usage for statistics"""
        self.stats[model_size]["count"] += 1
        self.stats[model_size]["total_ms"] += latency_ms

    def get_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics

        Returns:
            Dictionary with routing stats and performance metrics
        """
        total_requests = sum(s["count"] for s in self.stats.values())

        if total_requests == 0:
            return {
                "total_requests": 0,
                "model_distribution": {},
                "average_latency_ms": 0,
                "estimated_cost_savings": 0
            }

        # Calculate distributions
        small_count = self.stats[ModelSize.SMALL]["count"]
        large_count = self.stats[ModelSize.LARGE]["count"]

        small_ratio = small_count / total_requests if total_requests > 0 else 0
        large_ratio = large_count / total_requests if total_requests > 0 else 0

        # Calculate average latencies
        small_avg = (
            self.stats[ModelSize.SMALL]["total_ms"] / small_count
            if small_count > 0 else 0
        )
        large_avg = (
            self.stats[ModelSize.LARGE]["total_ms"] / large_count
            if large_count > 0 else 0
        )

        # Weighted average latency
        weighted_avg = (
            small_avg * small_ratio +
            large_avg * large_ratio
        )

        # Baseline (all 8B)
        baseline_latency = 4500

        # Cost savings calculation
        baseline_cost = total_requests * self.MODELS[ModelSize.LARGE]["cost_per_1k_tokens"]
        actual_cost = (
            small_count * self.MODELS[ModelSize.SMALL]["cost_per_1k_tokens"] +
            large_count * self.MODELS[ModelSize.LARGE]["cost_per_1k_tokens"]
        )
        cost_savings_pct = ((baseline_cost - actual_cost) / baseline_cost * 100) if baseline_cost > 0 else 0

        return {
            "total_requests": total_requests,
            "model_distribution": {
                "3b": {
                    "count": small_count,
                    "percentage": round(small_ratio * 100, 1),
                    "avg_latency_ms": round(small_avg, 0)
                },
                "8b": {
                    "count": large_count,
                    "percentage": round(large_ratio * 100, 1),
                    "avg_latency_ms": round(large_avg, 0)
                }
            },
            "average_latency_ms": round(weighted_avg, 0),
            "baseline_latency_ms": baseline_latency,
            "latency_improvement_pct": round((baseline_latency - weighted_avg) / baseline_latency * 100, 1),
            "estimated_cost_savings_pct": round(cost_savings_pct, 1),
            "ab_test_ratio": self.ab_test_ratio,
            "routing_enabled": self.enable_routing
        }

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            ModelSize.SMALL: {"count": 0, "total_ms": 0},
            ModelSize.LARGE: {"count": 0, "total_ms": 0}
        }
        logger.info("📊 ModelRouter stats reset")


# Singleton instance
_model_router: Optional[ModelRouter] = None


def get_model_router(
    ab_test_ratio: float = 0.5,
    enable_routing: bool = True,
    default_model: ModelSize = ModelSize.LARGE
) -> ModelRouter:
    """
    Get singleton instance of model router

    Args:
        ab_test_ratio: Ratio for A/B testing medium queries (only used on first call)
        enable_routing: Enable intelligent routing (only used on first call)
        default_model: Default model if routing disabled (only used on first call)

    Returns:
        ModelRouter instance
    """
    global _model_router

    if _model_router is None:
        _model_router = ModelRouter(
            ab_test_ratio=ab_test_ratio,
            enable_routing=enable_routing,
            default_model=default_model
        )

    return _model_router
