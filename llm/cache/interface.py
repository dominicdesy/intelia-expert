# -*- coding: utf-8 -*-
"""
Standard cache interface for all cache modules

This module defines the common interface that all cache implementations
should follow, enabling consistent behavior across:
- cache/cache_semantic.py
- cache/cache_core.py
- cache/redis_cache_manager.py

Usage:
    from cache.interface import CacheInterface, CacheStats

    class MyCache(CacheInterface):
        async def get_embedding(self, text: str):
            # implementation
"""

from abc import ABC, abstractmethod
from utils.types import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class CacheStats:
    """
    Standard cache statistics structure

    All cache implementations should return stats in this format
    """

    total_requests: int = 0
    hits: int = 0
    misses: int = 0
    errors: int = 0
    hit_rate: float = 0.0

    # Extended stats (optional)
    exact_hits: int = 0
    semantic_hits: int = 0
    fallback_hits: int = 0
    saved_operations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_requests": self.total_requests,
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "hit_rate": self.hit_rate,
            "exact_hits": self.exact_hits,
            "semantic_hits": self.semantic_hits,
            "fallback_hits": self.fallback_hits,
            "saved_operations": self.saved_operations,
        }


class CacheInterface(ABC):
    """
    Standard cache interface

    All cache implementations should inherit from this interface
    to ensure consistent behavior across the codebase.
    """

    # =========================================================================
    # EMBEDDING CACHE
    # =========================================================================

    @abstractmethod
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding for text

        Args:
            text: Input text to get embedding for

        Returns:
            Embedding vector or None if not cached
        """
        pass

    @abstractmethod
    async def set_embedding(self, text: str, embedding: List[float], **kwargs) -> bool:
        """
        Cache embedding for text

        Args:
            text: Input text
            embedding: Embedding vector to cache
            **kwargs: Additional cache parameters (ttl, etc.)

        Returns:
            True if cached successfully
        """
        pass

    # =========================================================================
    # RESPONSE CACHE
    # =========================================================================

    @abstractmethod
    async def get_response(
        self, query: str, context_hash: str, language: str = "fr"
    ) -> Optional[str]:
        """
        Retrieve cached response for query

        Args:
            query: User query
            context_hash: Hash of the context used
            language: Query language

        Returns:
            Cached response or None if not found
        """
        pass

    @abstractmethod
    async def set_response(
        self,
        query: str,
        context_hash: str,
        response: str,
        language: str = "fr",
        **kwargs,
    ) -> bool:
        """
        Cache response for query

        Args:
            query: User query
            context_hash: Hash of the context used
            response: Generated response to cache
            language: Query language
            **kwargs: Additional cache parameters (ttl, metadata, etc.)

        Returns:
            True if cached successfully
        """
        pass

    # =========================================================================
    # GENERAL CACHE OPERATIONS
    # =========================================================================

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Generic cache get operation

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Generic cache set operation

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)

        Returns:
            True if cached successfully
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key to delete

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all cache entries

        Returns:
            True if cleared successfully
        """
        pass

    # =========================================================================
    # STATISTICS
    # =========================================================================

    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Should return a dict compatible with CacheStats dataclass

        Returns:
            Dictionary with cache statistics
        """
        pass

    def get_cache_stats_object(self) -> CacheStats:
        """
        Get cache statistics as CacheStats object

        Returns:
            CacheStats instance
        """
        stats = self.get_cache_stats()
        return CacheStats(**stats)


class AsyncCacheInterface(CacheInterface):
    """
    Async-only cache interface

    For caches that only support async operations.
    All methods are already async in the base interface.
    """

    pass


class SyncCacheInterface(ABC):
    """
    Synchronous cache interface

    For caches that provide synchronous operations.
    """

    @abstractmethod
    def get_embedding_sync(self, text: str) -> Optional[List[float]]:
        """Synchronous embedding retrieval"""
        pass

    @abstractmethod
    def set_embedding_sync(self, text: str, embedding: List[float]) -> bool:
        """Synchronous embedding storage"""
        pass

    @abstractmethod
    def get_sync(self, key: str) -> Optional[Any]:
        """Synchronous cache get"""
        pass

    @abstractmethod
    def set_sync(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Synchronous cache set"""
        pass


__all__ = [
    "CacheInterface",
    "AsyncCacheInterface",
    "SyncCacheInterface",
    "CacheStats",
]
