# app/api/v1/logging_cache.py
# -*- coding: utf-8 -*-
"""
🚀 SYSTÈME DE CACHE INTELLIGENT POUR ANALYTICS
⚡ Cache avec TTL, nettoyage automatique et statistiques
"""
import os
import logging
import threading
from typing import Dict, Any, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 🔧 Configuration du cache
_analytics_cache: Dict[str, tuple] = {}
_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = int(os.getenv("ANALYTICS_CACHE_TTL", "300"))  # 5 minutes par défaut


def get_cached_or_compute(cache_key: str, compute_func: Callable, ttl_seconds: int = None) -> Any:
    """Cache intelligent avec TTL pour optimiser les requêtes lourdes"""
    if ttl_seconds is None:
        ttl_seconds = CACHE_TTL_SECONDS
    
    with _cache_lock:
        cached_item = _analytics_cache.get(cache_key)
        
        if cached_item:
            cached_time, cached_data = cached_item
            if datetime.now() - cached_time < timedelta(seconds=ttl_seconds):
                logger.info(f"✅ Cache HIT pour {cache_key}")
                return cached_data
            else:
                logger.info(f"⏰ Cache EXPIRED pour {cache_key}")
        
        # Recalculer
        logger.info(f"🔄 Cache MISS - Calcul pour {cache_key}")
        fresh_data = compute_func()
        _analytics_cache[cache_key] = (datetime.now(), fresh_data)
        return fresh_data


def clear_analytics_cache(pattern: str = None) -> None:
    """Nettoie le cache (utile après modifications)"""
    with _cache_lock:
        if pattern:
            keys_to_remove = [k for k in _analytics_cache.keys() if pattern in k]
            for k in keys_to_remove:
                del _analytics_cache[k]
            logger.info(f"🧹 Cache nettoyé: {len(keys_to_remove)} entrées supprimées")
        else:
            _analytics_cache.clear()
            logger.info("🧹 Cache complètement nettoyé")


def get_cache_stats() -> Dict[str, Any]:
    """Statistiques du cache pour monitoring"""
    with _cache_lock:
        total_entries = len(_analytics_cache)
        expired_entries = 0
        now = datetime.now()
        
        for cached_time, _ in _analytics_cache.values():
            if now - cached_time > timedelta(seconds=CACHE_TTL_SECONDS):
                expired_entries += 1
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "cache_ttl_seconds": CACHE_TTL_SECONDS
        }


def cleanup_expired_cache() -> int:
    """Nettoie les entrées expirées du cache"""
    with _cache_lock:
        now = datetime.now()
        expired_keys = []
        
        for key, (cached_time, _) in _analytics_cache.items():
            if now - cached_time > timedelta(seconds=CACHE_TTL_SECONDS):
                expired_keys.append(key)
        
        for key in expired_keys:
            del _analytics_cache[key]
        
        if expired_keys:
            logger.info(f"🧹 Nettoyage automatique: {len(expired_keys)} entrées expirées supprimées")
        
        return len(expired_keys)


def get_cache_memory_usage() -> Dict[str, Any]:
    """🆕 NOUVEAU - Statistiques d'usage mémoire du cache"""
    import sys
    
    with _cache_lock:
        total_size = 0
        entry_sizes = {}
        
        for key, (cached_time, cached_data) in _analytics_cache.items():
            entry_size = sys.getsizeof(cached_data) + sys.getsizeof(cached_time) + sys.getsizeof(key)
            entry_sizes[key] = entry_size
            total_size += entry_size
        
        return {
            "total_memory_bytes": total_size,
            "total_memory_mb": round(total_size / (1024 * 1024), 2),
            "entries_count": len(_analytics_cache),
            "avg_entry_size_bytes": round(total_size / len(_analytics_cache)) if _analytics_cache else 0,
            "largest_entries": sorted(entry_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
        }