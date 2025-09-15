# -*- coding: utf-8 -*-
"""
Package cache Redis pour Intelia Expert
Architecture modulaire pour maintenabilité optimale
"""

from .redis_cache_manager import RAGCacheManager
from .cache_core import RedisCacheCore
from .cache_semantic import SemanticCacheManager
from .cache_stats import CacheStatsManager

__version__ = "3.0.0-modular"
__all__ = [
    "RAGCacheManager",
    "RedisCacheCore", 
    "SemanticCacheManager",
    "CacheStatsManager"
]