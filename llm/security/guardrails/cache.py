# -*- coding: utf-8 -*-
"""
cache.py - Cache management for guardrails verification
"""

import hashlib
import logging
from utils.types import Dict, List, Optional, Any
from .models import GuardrailResult, VerificationLevel

logger = logging.getLogger(__name__)


class GuardrailCache:
    """Simple in-memory cache for guardrail verification results"""

    def __init__(self, max_size: int = 1000):
        """
        Initialize cache

        Args:
            max_size: Maximum number of entries (default 1000)
        """
        self._cache: Dict[str, GuardrailResult] = {}
        self._max_size = max_size

    def generate_key(
        self,
        query: str,
        response: str,
        context_docs: List[Dict],
        verification_level: VerificationLevel,
    ) -> Optional[str]:
        """
        Generate unique cache key

        Args:
            query: User query
            response: LLM response
            context_docs: Context documents
            verification_level: Verification level

        Returns:
            Cache key or None if generation fails
        """
        try:
            content_hash = hashlib.md5(
                f"{query}|{response}|{len(context_docs)}|{verification_level.value}".encode(),
                usedforsecurity=False
            ).hexdigest()
            return f"guardrail_{content_hash}"
        except Exception as e:
            logger.warning(f"Failed to generate cache key: {e}")
            return None

    def get(self, cache_key: str) -> Optional[GuardrailResult]:
        """
        Get result from cache

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None
        """
        if not cache_key:
            return None
        return self._cache.get(cache_key)

    def store(self, cache_key: str, result: GuardrailResult) -> None:
        """
        Store result in cache with size management

        Args:
            cache_key: Cache key
            result: Guardrail result to cache
        """
        if not cache_key:
            return

        # Simple LRU-like eviction: remove 20% oldest entries when full
        if len(self._cache) >= self._max_size:
            keys_to_remove = list(self._cache.keys())[: self._max_size // 5]
            for key in keys_to_remove:
                del self._cache[key]

        self._cache[cache_key] = result

    def clear(self) -> int:
        """
        Clear all cache entries

        Returns:
            Number of entries removed
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        return {
            "cache_enabled": True,
            "entries_count": len(self._cache),
            "max_size": self._max_size,
            "utilization": (
                len(self._cache) / self._max_size if self._max_size > 0 else 0
            ),
        }


__all__ = ["GuardrailCache"]
