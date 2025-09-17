# -*- coding: utf-8 -*-
"""
Cache module - Système de cache Redis avec gestion sémantique
"""

from .cache_core import (
    RedisCacheCore,
    CacheConfig,
    CacheStats,
    CacheStatus,
    create_cache_core,
)
from .redis_cache_manager import RAGCacheManager

try:
    from .cache_semantic import SemanticCacheManager
except ImportError:
    SemanticCacheManager = None

try:
    from .cache_stats import CacheStatsManager
except ImportError:
    CacheStatsManager = None

__all__ = [
    "RedisCacheCore",
    "CacheConfig",
    "CacheStats",
    "CacheStatus",
    "create_cache_core",
    "RAGCacheManager",
    "SemanticCacheManager",
    "CacheStatsManager",
]
