# app/api/v1/stats_cache.py
"""
VERSION SIMPLE ET DIRECTE - CACHE EN MÉMOIRE
Évite les complexités SQL et utilise un cache en mémoire simple
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class StatisticsCache:
    def __init__(self, dsn: str = None):
        # Cache en mémoire simple
        self._cache = {}
        self._timestamps = {}
        self.max_entries = 100

        logger.debug("StatisticsCache VERSION SIMPLE V1.0 initialisé")
        logger.debug("Cache en mémoire activé (max 100 entrées)")
        logger.debug("Cette version évite les problèmes SQL du cache")

    def set_cache(
        self, key: str, data: Any, ttl_hours: int = 12, source: str = "computed"
    ) -> bool:
        """Stocke dans le cache mémoire"""
        try:
            # Nettoyer si trop d'entrées
            if len(self._cache) >= self.max_entries:
                self._cleanup_expired()

            expires_at = datetime.now() + timedelta(hours=ttl_hours)

            self._cache[key] = {
                "data": data,
                "expires_at": expires_at,
                "source": source,
                "created_at": datetime.now(),
            }
            self._timestamps[key] = datetime.now()

            logger.info(f"Cache SET: {key} (TTL: {ttl_hours}h)")
            return True

        except Exception as e:
            logger.error(f"Erreur set cache {key}: {e}")
            return False

    def get_cache(
        self, key: str, include_expired: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Récupère du cache mémoire"""
        try:
            if key not in self._cache:
                return None

            cached_item = self._cache[key]
            is_expired = datetime.now() > cached_item["expires_at"]

            if is_expired and not include_expired:
                # Supprimer l'entrée expirée
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                return None

            logger.info(f"Cache {'HIT' if not is_expired else 'EXPIRED'}: {key}")

            return {
                "data": cached_item["data"],
                "cached_at": cached_item["created_at"].isoformat(),
                "expires_at": cached_item["expires_at"].isoformat(),
                "source": cached_item["source"],
                "is_expired": is_expired,
            }

        except Exception as e:
            logger.error(f"Erreur get cache {key}: {e}")
            return None

    def invalidate_cache(self, pattern: str = None, key: str = None) -> int:
        """Invalide le cache"""
        try:
            deleted_count = 0

            if key:
                if key in self._cache:
                    self._cache.pop(key)
                    self._timestamps.pop(key, None)
                    deleted_count = 1
            elif pattern:
                # Supprimer par pattern
                keys_to_delete = [
                    k for k in self._cache.keys() if pattern.replace("*", "") in k
                ]
                for k in keys_to_delete:
                    self._cache.pop(k, None)
                    self._timestamps.pop(k, None)
                    deleted_count += 1
            else:
                # Supprimer les expirés
                deleted_count = self._cleanup_expired()

            logger.info(f"Cache invalidé: {deleted_count} entrées supprimées")
            return deleted_count

        except Exception as e:
            logger.error(f"Erreur invalidation cache: {e}")
            return 0

    def delete_cache(self, key: str) -> bool:
        """Alias pour compatibilité"""
        return self.invalidate_cache(key=key) > 0

    def _cleanup_expired(self) -> int:
        """Nettoie les entrées expirées"""
        now = datetime.now()
        expired_keys = []

        for key, item in self._cache.items():
            if now > item["expires_at"]:
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

        return len(expired_keys)

    def set_dashboard_snapshot(
        self, stats: Dict[str, Any], period_hours: int = 24
    ) -> bool:
        """Stocke snapshot dashboard"""
        return self.set_cache(
            "dashboard:snapshot", stats, ttl_hours=period_hours, source="dashboard"
        )

    def get_dashboard_snapshot(self) -> Optional[Dict[str, Any]]:
        """Récupère snapshot dashboard"""
        cached = self.get_cache("dashboard:snapshot")
        return cached["data"] if cached else None

    def cleanup_expired_cache(self) -> int:
        """Nettoyage manuel"""
        return self._cleanup_expired()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Stats du cache"""
        now = datetime.now()
        expired_count = sum(
            1 for item in self._cache.values() if now > item["expires_at"]
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": len(self._cache) - expired_count,
            "expired_entries": expired_count,
            "max_entries": self.max_entries,
            "cache_type": "memory_based",
            "timestamp": now.isoformat(),
        }


# Singleton
_stats_cache_instance = None


def get_stats_cache() -> StatisticsCache:
    global _stats_cache_instance
    if _stats_cache_instance is None:
        _stats_cache_instance = StatisticsCache()
    return _stats_cache_instance


def force_cache_refresh() -> Dict[str, Any]:
    """Force refresh du cache"""
    cache = get_stats_cache()
    cleaned = cache.cleanup_expired_cache()

    return {
        "status": "success",
        "entries_cleaned": cleaned,
        "timestamp": datetime.now().isoformat(),
    }
