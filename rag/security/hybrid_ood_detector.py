# -*- coding: utf-8 -*-
"""
hybrid_ood_detector.py - Hybrid OOD Detection (LLM + Weaviate)
Version: 1.0.0
Last modified: 2025-10-30

Combines LLM classification with Weaviate content search for robust,
auto-adaptive out-of-domain detection.

Key Features:
- Fast path: LLM for clear YES/NO decisions (<100ms)
- Fallback: Weaviate search for uncertain cases
- Auto-discovery: New products/topics become IN-DOMAIN when docs are ingested
- Configurable thresholds for fine-tuning

Architecture:
1. LLM Classifier (fast, opinionated)
   - Clear YES → Accept immediately (fast path)
   - Clear NO (no poultry keywords) → Reject immediately
   - UNCERTAIN → Check Weaviate

2. Weaviate Search (fallback for uncertain cases)
   - Hybrid search (vector + keyword)
   - If relevant docs found (score > threshold) → IN-DOMAIN
   - If no relevant docs → OUT-OF-DOMAIN

Benefits:
✅ Auto-adaptive: New products discovered automatically
✅ Fast: Most queries use LLM fast path (<100ms)
✅ Robust: Weaviate catches edge cases
✅ Zero maintenance: No need to update product lists
"""

import logging
from typing import Tuple, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OODDecision:
    """Result of OOD detection"""

    is_in_domain: bool
    confidence: float
    method: str  # "llm_fast_accept", "llm_fast_reject", "weaviate_found", "weaviate_not_found"
    details: Dict[str, Any]


class HybridOODDetector:
    """
    Hybrid OOD detector combining LLM classification with Weaviate content search

    Decision Flow:
    1. LLM Classification (fast, ~100ms)
       - If confident YES → Accept (fast path)
       - If confident NO + no poultry keywords → Reject (fast path)
       - If uncertain → Check Weaviate

    2. Weaviate Search (fallback, ~200ms)
       - Hybrid search for relevant documents
       - If found (score > threshold) → Accept
       - If not found → Reject

    Configuration Parameters:
        llm_high_confidence_threshold: Minimum confidence to skip Weaviate (default: 0.9)
        weaviate_score_threshold: Minimum doc score to accept as IN-DOMAIN (default: 0.7)
        weaviate_top_k: Number of documents to retrieve (default: 5)
        weaviate_alpha: Balance between vector/keyword (0=vector, 1=keyword) (default: 0.5)
    """

    def __init__(
        self,
        llm_detector,
        weaviate_client,
        llm_high_confidence_threshold: float = 0.9,
        weaviate_score_threshold: float = 0.7,
        weaviate_top_k: int = 5,
        weaviate_alpha: float = 0.5,
    ):
        """
        Initialize hybrid OOD detector

        Args:
            llm_detector: LLMOODDetector instance
            weaviate_client: WeaviateManager instance for content search
            llm_high_confidence_threshold: LLM confidence to skip Weaviate check
            weaviate_score_threshold: Minimum Weaviate score for IN-DOMAIN
            weaviate_top_k: Number of documents to retrieve from Weaviate
            weaviate_alpha: Hybrid search balance (0=pure vector, 1=pure keyword)
        """
        self.llm_detector = llm_detector
        self.weaviate_client = weaviate_client
        self.llm_high_confidence_threshold = llm_high_confidence_threshold
        self.weaviate_score_threshold = weaviate_score_threshold
        self.weaviate_top_k = weaviate_top_k
        self.weaviate_alpha = weaviate_alpha

        # Keywords that indicate poultry context
        self.poultry_keywords = [
            "chicken",
            "broiler",
            "layer",
            "poultry",
            "poulet",
            "volaille",
            "egg",
            "hen",
            "rooster",
            "chick",
            "duck",
            "turkey",
            "quail",
            "avian",
            "aviculture",
            "fcr",
            "feed conversion",
            "hatchery",
            "coccidiosis",
            "newcastle",
            "vaccine",
            "mortality",
        ]

        logger.info(
            f"✅ HybridOODDetector initialized (LLM threshold={llm_high_confidence_threshold}, "
            f"Weaviate threshold={weaviate_score_threshold})"
        )

    def is_in_domain(
        self, query: str, intent_result: Optional[Dict] = None, language: str = "fr"
    ) -> Tuple[bool, float, Dict]:
        """
        Determine if query is in-domain using hybrid approach

        Args:
            query: User query
            intent_result: Intent detection result (optional, for compatibility)
            language: Query language

        Returns:
            Tuple (is_in_domain, confidence, details):
                - is_in_domain: True if in poultry domain
                - confidence: 0.0-1.0 confidence score
                - details: Dict with method, scores, etc.
        """
        logger.info(f"🔍 Hybrid OOD detection for: '{query[:60]}...' (lang={language})")

        # ═══════════════════════════════════════════════════════════
        # STEP 1: LLM Classification (Fast Path)
        # ═══════════════════════════════════════════════════════════

        try:
            llm_is_in_domain, llm_confidence, llm_details = (
                self.llm_detector.is_in_domain(query, intent_result, language)
            )
        except Exception as e:
            logger.error(f"❌ LLM OOD detection failed: {e}")
            # Fallback to Weaviate on LLM failure
            llm_is_in_domain = None
            llm_confidence = 0.0
            llm_details = {"error": str(e)}

        # Fast path: LLM is confident YES
        if (
            llm_is_in_domain is True
            and llm_confidence >= self.llm_high_confidence_threshold
        ):
            logger.info(
                f"✅ FAST ACCEPT (LLM confident YES): confidence={llm_confidence:.2f}"
            )
            return (
                True,
                llm_confidence,
                {
                    "method": "llm_fast_accept",
                    "llm_confidence": llm_confidence,
                    "llm_details": llm_details,
                    "weaviate_checked": False,
                },
            )

        # Fast reject: LLM says NO and query has no poultry keywords
        if llm_is_in_domain is False and not self._has_poultry_keywords(query):
            logger.warning(
                f"⛔ FAST REJECT (LLM NO + no poultry keywords): '{query[:60]}...'"
            )
            return (
                False,
                0.0,
                {
                    "method": "llm_fast_reject",
                    "llm_confidence": llm_confidence,
                    "llm_details": llm_details,
                    "weaviate_checked": False,
                },
            )

        # ═══════════════════════════════════════════════════════════
        # STEP 2: Weaviate Content Search (Fallback for Uncertain Cases)
        # ═══════════════════════════════════════════════════════════

        logger.info(
            f"🔎 LLM uncertain or has poultry keywords → checking Weaviate content..."
        )

        try:
            # Perform hybrid search in Weaviate
            search_results = self._search_weaviate(query, language)

            if not search_results:
                logger.warning(
                    f"⛔ OUT-OF-DOMAIN (Weaviate): No relevant documents found for '{query[:60]}...'"
                )
                return (
                    False,
                    0.0,
                    {
                        "method": "weaviate_not_found",
                        "llm_confidence": llm_confidence,
                        "llm_details": llm_details,
                        "weaviate_checked": True,
                        "weaviate_results_count": 0,
                        "weaviate_max_score": 0.0,
                    },
                )

            # Get max score from results
            max_score = max(result.get("score", 0.0) for result in search_results)
            result_count = len(search_results)

            logger.info(
                f"📚 Weaviate found {result_count} documents (max_score={max_score:.3f})"
            )

            # Check if max score exceeds threshold
            if max_score >= self.weaviate_score_threshold:
                logger.info(
                    f"✅ IN-DOMAIN (Weaviate): Found relevant content (score={max_score:.3f} >= {self.weaviate_score_threshold})"
                )
                return (
                    True,
                    max_score,
                    {
                        "method": "weaviate_found",
                        "llm_confidence": llm_confidence,
                        "llm_details": llm_details,
                        "weaviate_checked": True,
                        "weaviate_results_count": result_count,
                        "weaviate_max_score": max_score,
                        "weaviate_top_docs": [
                            {
                                "title": r.get("title", "N/A"),
                                "score": r.get("score", 0.0),
                            }
                            for r in search_results[:3]
                        ],
                    },
                )
            else:
                logger.warning(
                    f"⛔ OUT-OF-DOMAIN (Weaviate): Max score {max_score:.3f} < threshold {self.weaviate_score_threshold}"
                )
                return (
                    False,
                    max_score,
                    {
                        "method": "weaviate_low_score",
                        "llm_confidence": llm_confidence,
                        "llm_details": llm_details,
                        "weaviate_checked": True,
                        "weaviate_results_count": result_count,
                        "weaviate_max_score": max_score,
                    },
                )

        except Exception as e:
            logger.error(f"❌ Weaviate OOD check failed: {e}")
            # Fallback: If Weaviate fails but LLM said YES, accept
            # If both fail or LLM said NO, reject
            fallback_decision = llm_is_in_domain is True
            logger.warning(
                f"⚠️ Fallback decision: {'ACCEPT' if fallback_decision else 'REJECT'} (based on LLM)"
            )
            return (
                fallback_decision,
                llm_confidence if fallback_decision else 0.0,
                {
                    "method": "weaviate_error_fallback",
                    "llm_confidence": llm_confidence,
                    "llm_details": llm_details,
                    "weaviate_checked": True,
                    "weaviate_error": str(e),
                },
            )

    def _has_poultry_keywords(self, query: str) -> bool:
        """
        Check if query contains poultry-related keywords

        Args:
            query: User query

        Returns:
            True if query contains poultry keywords
        """
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in self.poultry_keywords)

    def _search_weaviate(self, query: str, language: str) -> list:
        """
        Search Weaviate for relevant documents

        Args:
            query: Search query
            language: Query language

        Returns:
            List of search results with scores
        """
        try:
            # Get collection name from environment or use default
            collection_name = "InteliaKnowledge"

            # Perform hybrid search
            results = self.weaviate_client.hybrid_search(
                collection_name=collection_name,
                query_text=query,
                limit=self.weaviate_top_k,
                alpha=self.weaviate_alpha,
                return_properties=[
                    "title",
                    "content",
                    "document_type",
                    "visibility_level",
                ],
            )

            # Convert to list of dicts with scores
            formatted_results = []
            for result in results:
                # Extract score from result object
                # Weaviate returns score in different ways depending on search type
                score = 0.0
                if hasattr(result, "metadata"):
                    score = getattr(result.metadata, "score", 0.0)
                elif isinstance(result, dict):
                    score = result.get("_additional", {}).get("score", 0.0)

                formatted_results.append(
                    {
                        "score": score,
                        "title": (
                            result.properties.get("title", "N/A")
                            if hasattr(result, "properties")
                            else result.get("title", "N/A")
                        ),
                        "content": (
                            result.properties.get("content", "")
                            if hasattr(result, "properties")
                            else result.get("content", "")
                        ),
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"❌ Weaviate search error: {e}")
            return []

    def calculate_ood_score_multilingual(
        self, query: str, intent_result: Optional[Dict] = None, language: str = "fr"
    ) -> Tuple[bool, float, Dict]:
        """
        Alias for compatibility with old API

        Calls is_in_domain() internally
        """
        return self.is_in_domain(query, intent_result, language)

    def clear_cache(self):
        """Clear LLM cache"""
        if hasattr(self.llm_detector, "clear_cache"):
            self.llm_detector.clear_cache()
            logger.info("🗑️ Hybrid OOD detector cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about OOD detection"""
        stats = {
            "llm_high_confidence_threshold": self.llm_high_confidence_threshold,
            "weaviate_score_threshold": self.weaviate_score_threshold,
            "weaviate_top_k": self.weaviate_top_k,
            "weaviate_alpha": self.weaviate_alpha,
        }

        if hasattr(self.llm_detector, "get_cache_size"):
            stats["llm_cache_size"] = self.llm_detector.get_cache_size()

        return stats


# Factory function for creating hybrid detector
def create_hybrid_ood_detector(
    llm_detector,
    weaviate_client,
    llm_high_confidence_threshold: float = 0.9,
    weaviate_score_threshold: float = 0.7,
    weaviate_top_k: int = 5,
    weaviate_alpha: float = 0.5,
) -> HybridOODDetector:
    """
    Create a HybridOODDetector instance

    Args:
        llm_detector: LLMOODDetector instance
        weaviate_client: WeaviateManager instance
        llm_high_confidence_threshold: LLM confidence threshold for fast path
        weaviate_score_threshold: Weaviate score threshold for IN-DOMAIN
        weaviate_top_k: Number of documents to retrieve
        weaviate_alpha: Hybrid search balance

    Returns:
        HybridOODDetector instance
    """
    return HybridOODDetector(
        llm_detector=llm_detector,
        weaviate_client=weaviate_client,
        llm_high_confidence_threshold=llm_high_confidence_threshold,
        weaviate_score_threshold=weaviate_score_threshold,
        weaviate_top_k=weaviate_top_k,
        weaviate_alpha=weaviate_alpha,
    )
