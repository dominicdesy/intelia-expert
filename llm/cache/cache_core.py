# -*- coding: utf-8 -*-
"""
cache_core.py - Module central du cache Redis robuste
Version corrigée: Configuration simplifiée, gestion mémoire stable, monitoring amélioré
CORRIGÉ: Ajout protection_stats manquant et cohérence des attributs
"""

import os
import time
import logging
import asyncio
import pickle
import zlib
from typing import TYPE_CHECKING
from utils.types import Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from core.base import InitializableMixin

# Redis imports avec gestion d'erreurs
try:
    import redis.asyncio as redis

    # CORRECTION: Suppression de l'import hiredis non utilisé
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# Type-only import for annotations
if TYPE_CHECKING:
    from redis.asyncio import Redis as RedisType
else:
    if REDIS_AVAILABLE:
        from redis.asyncio import Redis as RedisType
    else:
        RedisType = None

logger = logging.getLogger(__name__)


class CacheStatus(Enum):
    """États du cache"""

    DISABLED = "disabled"
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


@dataclass
class CacheConfig:
    """Configuration du cache avec valeurs par défaut saines"""

    # Connexion Redis
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 3600  # 1 heure

    # Limites de sécurité (valeurs plus conservatrices)
    max_value_bytes: int = 100_000  # 100KB par valeur (réduit de 200KB)
    max_keys_per_namespace: int = 1000  # Réduit de 2000
    total_memory_limit_mb: int = 100  # Réduit de 150MB

    # Seuils d'alerte (plus précoces)
    warning_threshold_mb: int = 70  # 70% de la limite
    purge_threshold_mb: int = 85  # 85% de la limite

    # Gestion automatique
    enable_auto_purge: bool = True
    enable_compression: bool = False  # Désactivé par défaut pour simplifier
    purge_ratio: float = 0.3  # Purge 30% en cas de surcharge

    # Monitoring
    stats_log_interval: int = 300  # 5 minutes (réduit de 10)
    health_check_interval: int = 60  # 1 minute

    # TTL spécialisés
    ttl_embeddings: int = 7200  # 2 heures
    ttl_search_results: int = 1800  # 30 minutes
    ttl_responses: int = 3600  # 1 heure
    ttl_intent_results: int = 3600  # 1 heure

    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Crée une configuration à partir des variables d'environnement"""
        return cls(
            redis_url=os.getenv("REDIS_URL", cls.redis_url),
            default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", cls.default_ttl)),
            max_value_bytes=int(
                os.getenv("CACHE_MAX_VALUE_BYTES", cls.max_value_bytes)
            ),
            max_keys_per_namespace=int(
                os.getenv("CACHE_MAX_KEYS_PER_NS", cls.max_keys_per_namespace)
            ),
            total_memory_limit_mb=int(
                os.getenv("CACHE_TOTAL_MEMORY_LIMIT_MB", cls.total_memory_limit_mb)
            ),
            warning_threshold_mb=int(
                os.getenv("CACHE_WARNING_THRESHOLD_MB", cls.warning_threshold_mb)
            ),
            purge_threshold_mb=int(
                os.getenv("CACHE_PURGE_THRESHOLD_MB", cls.purge_threshold_mb)
            ),
            enable_auto_purge=os.getenv("CACHE_ENABLE_AUTO_PURGE", "true").lower()
            == "true",
            enable_compression=os.getenv("CACHE_ENABLE_COMPRESSION", "false").lower()
            == "true",
            stats_log_interval=int(
                os.getenv("CACHE_STATS_LOG_INTERVAL", cls.stats_log_interval)
            ),
        )


@dataclass
class CacheStats:
    """Statistiques du cache"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    memory_usage_mb: float = 0.0
    key_count: int = 0
    avg_value_size: float = 0.0
    last_update: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Taux de réussite du cache"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def memory_usage_percent(self) -> float:
        """Pourcentage d'utilisation mémoire"""
        # Sera calculé avec la limite configurée
        return 0.0


class RedisCacheCore(InitializableMixin):
    """Module central robuste pour la gestion du cache Redis"""

    def __init__(self, config: Optional[CacheConfig] = None):
        super().__init__()
        self.config = config or CacheConfig.from_env()
        self.client: Optional[RedisType] = None
        self.status = CacheStatus.DISABLED
        self.stats = CacheStats()
        self.enabled = (
            REDIS_AVAILABLE and os.getenv("CACHE_ENABLED", "true").lower() == "true"
        )

        # CORRECTION: Ajout protection_stats manquant
        self.protection_stats = {
            "semantic_rejections": 0,
            "oversized_values": 0,
            "memory_limit_hits": 0,
            "namespace_limit_hits": 0,
        }

        # Monitoring interne
        self.last_health_check = 0.0
        self.last_stats_log = 0.0
        self.last_memory_check = 0.0

        # Protection contre les erreurs en cascade
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.error_backoff_until = 0.0

        # Namespaces pour organisation
        self.namespaces = {
            "embeddings": "emb:",
            "searches": "search:",
            "responses": "resp:",
            "intents": "intent:",
            "normalized": "norm:",
            "semantic": "sem:",
        }

        # CORRECTION: TTL config pour compatibilité
        self.ttl_config = {
            "embeddings": self.config.ttl_embeddings,
            "search_results": self.config.ttl_search_results,
            "responses": self.config.ttl_responses,
            "intent_results": self.config.ttl_intent_results,
            "semantic_fallback": self.config.ttl_responses,  # Fallback semantic utilise le même TTL que responses
        }

        logger.info(f"RedisCacheCore configuré: {self._get_config_summary()}")

    def _get_config_summary(self) -> str:
        """Résumé de la configuration"""
        return (
            f"limite={self.config.total_memory_limit_mb}MB, "
            f"max_value={self.config.max_value_bytes//1024}KB, "
            f"compression={self.config.enable_compression}"
        )

    async def initialize(self) -> bool:
        """Initialise la connexion Redis avec validation robuste"""
        if not self.enabled:
            logger.info("Cache Redis désactivé via configuration")
            self.status = CacheStatus.DISABLED
            return False

        if not REDIS_AVAILABLE:
            logger.warning("Redis non disponible - cache désactivé")
            self.status = CacheStatus.DISABLED
            self.enabled = False
            return False

        self.status = CacheStatus.INITIALIZING

        try:
            # Configuration de connexion robuste
            self.client = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=False,  # Gestion manuelle pour compression
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=self.config.health_check_interval,
                socket_connect_timeout=5,
                socket_timeout=3,
                retry_on_timeout=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
            )

            # Test de connexion avec timeout
            await asyncio.wait_for(self.client.ping(), timeout=3.0)

            # Vérification des capacités Redis
            await self._verify_redis_capabilities()

            # Initialisation des statistiques
            await self._initialize_stats()

            self.status = CacheStatus.HEALTHY
            self.consecutive_errors = 0

            logger.info(f"Cache Redis initialisé avec succès: {self.config.redis_url}")
            logger.info(f"Configuration: {self._get_config_summary()}")

            await super().initialize()
            return True

        except asyncio.TimeoutError:
            logger.error("Timeout connexion Redis - cache désactivé")
            self.status = CacheStatus.ERROR
            self._disable_cache()
            return False
        except Exception as e:
            logger.error(f"Erreur initialisation Redis: {e} - cache désactivé")
            self.status = CacheStatus.ERROR
            self._disable_cache()
            return False

    async def _verify_redis_capabilities(self):
        """Vérifie les capacités Redis requises"""
        try:
            # Test des commandes de base
            await self.client.set("test:capability", "ok", ex=1)
            await self.client.get("test:capability")
            await self.client.delete("test:capability")

            # Test de la commande INFO pour les statistiques
            info = await self.client.info("memory")
            if "used_memory" not in info:
                logger.warning("Statistiques mémoire Redis non disponibles")

        except Exception as e:
            raise RuntimeError(f"Redis ne supporte pas les opérations requises: {e}")

    async def _initialize_stats(self):
        """Initialise les statistiques du cache"""
        try:
            # Récupération des stats initiales
            await self._update_memory_stats()
            self.stats.last_update = time.time()
            self.last_health_check = time.time()

        except Exception as e:
            logger.warning(f"Impossible d'initialiser les statistiques: {e}")

    def _disable_cache(self):
        """Désactive le cache en cas d'erreur"""
        self.enabled = False
        self.is_initialized = False
        if self.client:
            try:
                asyncio.create_task(self.client.close())
            # CORRECTION: Remplacer bare except par Exception
            except Exception:
                pass
            self.client = None

    # CORRECTION: Méthode _is_operational pour compatibilité
    def _is_operational(self) -> bool:
        """Vérifie si le cache est opérationnel"""
        if not (self.enabled and self.is_initialized and self.client):
            return False

        # Vérification du backoff en cas d'erreurs
        if time.time() < self.error_backoff_until:
            return False

        return self.status in [CacheStatus.HEALTHY, CacheStatus.WARNING]

    # CORRECTION: Alias pour compatibilité
    def _is_initialized(self) -> bool:
        """Alias pour _is_operational pour compatibilité"""
        return self._is_operational()

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Récupère une valeur du cache avec gestion d'erreurs robuste"""
        if not self._is_operational():
            return None

        full_key = self._build_key(key, namespace)

        try:
            # Vérification de la limite de taille de clé
            if len(full_key.encode()) > 512:  # Limite Redis
                logger.warning(f"Clé trop longue ignorée: {len(full_key)} bytes")
                return None

            raw_value = await asyncio.wait_for(self.client.get(full_key), timeout=1.0)

            if raw_value is None:
                self.stats.misses += 1
                return None

            # Décompression si activée
            value = (
                self._decompress_value(raw_value)
                if self.config.enable_compression
                else raw_value
            )

            # Désérialisation
            result = pickle.loads(value)

            self.stats.hits += 1
            self._reset_error_backoff()

            return result

        except asyncio.TimeoutError:
            logger.warning(f"Timeout récupération cache: {full_key}")
            self.stats.errors += 1
            return None
        except Exception as e:
            self._handle_cache_error(f"Erreur get {full_key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
    ) -> bool:
        """Stocke une valeur dans le cache avec validation"""
        if not self._is_operational():
            return False

        full_key = self._build_key(key, namespace)

        try:
            # Sérialisation
            serialized = pickle.dumps(value)

            # Vérification de la taille
            if len(serialized) > self.config.max_value_bytes:
                logger.warning(
                    f"Valeur trop grande ignorée: {len(serialized)} bytes > {self.config.max_value_bytes}"
                )
                self.protection_stats["oversized_values"] += 1
                return False

            # Compression si activée
            final_value = (
                self._compress_value(serialized)
                if self.config.enable_compression
                else serialized
            )

            # TTL selon le namespace
            effective_ttl = ttl or self._get_namespace_ttl(namespace)

            # Vérification de l'espace disponible
            if not await self._check_memory_limits():
                logger.warning("Limite mémoire atteinte - stockage refusé")
                self.protection_stats["memory_limit_hits"] += 1
                return False

            # Stockage avec timeout
            success = await asyncio.wait_for(
                self.client.set(full_key, final_value, ex=effective_ttl), timeout=1.0
            )

            if success:
                self.stats.sets += 1
                self._reset_error_backoff()

                # Monitoring des namespaces
                await self._monitor_namespace_limits(namespace)

            return bool(success)

        except asyncio.TimeoutError:
            logger.warning(f"Timeout stockage cache: {full_key}")
            self.stats.errors += 1
            return False
        except Exception as e:
            self._handle_cache_error(f"Erreur set {full_key}: {e}")
            return False

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Supprime une clé du cache"""
        if not self._is_operational():
            return False

        full_key = self._build_key(key, namespace)

        try:
            result = await asyncio.wait_for(self.client.delete(full_key), timeout=1.0)

            if result > 0:
                self.stats.deletes += 1
                self._reset_error_backoff()

            return result > 0

        except Exception as e:
            self._handle_cache_error(f"Erreur delete {full_key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str, namespace: str = "default") -> int:
        """Invalide les clés correspondant à un pattern"""
        if not self._is_operational():
            return 0

        full_pattern = self._build_key(pattern, namespace)

        try:
            # Recherche des clés
            keys = await asyncio.wait_for(self.client.keys(full_pattern), timeout=5.0)

            if not keys:
                return 0

            # Suppression par batch
            deleted = 0
            batch_size = 100

            for i in range(0, len(keys), batch_size):
                batch = keys[i : i + batch_size]
                deleted += await self.client.delete(*batch)

            self.stats.deletes += deleted
            logger.info(f"Pattern {full_pattern}: {deleted} clés supprimées")

            return deleted

        except Exception as e:
            self._handle_cache_error(f"Erreur invalidation pattern {full_pattern}: {e}")
            return 0

    # CORRECTION: Méthodes de compression pour compatibilité semantic
    def _compress_data(self, data: bytes) -> bytes:
        """Compresse des données - alias pour _compress_value"""
        return self._compress_value(data)

    def _decompress_data(self, data: bytes) -> bytes:
        """Décompresse des données - alias pour _decompress_value"""
        return self._decompress_value(data)

    # CORRECTION: Méthode de vérification size/namespace quota pour semantic
    async def _check_size_and_namespace_quota(
        self, namespace: str, data: bytes
    ) -> bool:
        """Vérifie les quotas de taille et namespace"""
        # Vérification taille
        if len(data) > self.config.max_value_bytes:
            self.protection_stats["oversized_values"] += 1
            return False

        # Vérification mémoire globale
        if not await self._check_memory_limits():
            self.protection_stats["memory_limit_hits"] += 1
            return False

        # Vérification namespace (optionnelle, on vérifie dans monitor_namespace_limits)
        return True

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques complètes du cache"""
        if not self.is_initialized:
            return {"enabled": False, "status": self.status.value}

        try:
            # Mise à jour des stats mémoire
            await self._update_memory_stats()

            # Stats Redis
            redis_info = await self.client.info("memory")

            # Stats par namespace
            namespace_stats = await self._get_namespace_stats()

            return {
                "enabled": self.enabled,
                "status": self.status.value,
                "operational": self._is_operational(),
                "stats": asdict(self.stats),
                "config": {
                    "total_memory_limit_mb": self.config.total_memory_limit_mb,
                    "max_value_bytes": self.config.max_value_bytes,
                    "compression_enabled": self.config.enable_compression,
                    "auto_purge_enabled": self.config.enable_auto_purge,
                },
                "redis_info": {
                    "used_memory": redis_info.get("used_memory", 0),
                    "used_memory_human": redis_info.get("used_memory_human", "0B"),
                    "connected_clients": redis_info.get("connected_clients", 0),
                },
                "namespaces": namespace_stats,
                "health": {
                    "consecutive_errors": self.consecutive_errors,
                    "error_backoff_until": self.error_backoff_until,
                    "last_health_check": self.last_health_check,
                },
                "protection_stats": self.protection_stats,
            }

        except Exception as e:
            logger.error(f"Erreur récupération stats: {e}")
            return {"enabled": self.enabled, "status": "error", "error": str(e)}

    def _build_key(self, key: str, namespace: str) -> str:
        """Construit une clé complète avec namespace"""
        prefix = self.namespaces.get(namespace, f"{namespace}:")
        return f"{prefix}{key}"

    def _get_namespace_ttl(self, namespace: str) -> int:
        """Retourne le TTL par défaut pour un namespace"""
        ttl_map = {
            "embeddings": self.config.ttl_embeddings,
            "searches": self.config.ttl_search_results,
            "responses": self.config.ttl_responses,
            "intents": self.config.ttl_intent_results,
        }
        return ttl_map.get(namespace, self.config.default_ttl)

    def _compress_value(self, value: bytes) -> bytes:
        """Compresse une valeur"""
        return zlib.compress(value, level=1)  # Compression rapide

    def _decompress_value(self, value: bytes) -> bytes:
        """Décompresse une valeur"""
        return zlib.decompress(value)

    def _handle_cache_error(self, error_msg: str):
        """Gestion centralisée des erreurs de cache"""
        self.stats.errors += 1
        self.consecutive_errors += 1

        logger.warning(error_msg)

        # Politique de backoff exponentiel
        if self.consecutive_errors >= self.max_consecutive_errors:
            backoff_seconds = min(
                300, 2 ** (self.consecutive_errors - self.max_consecutive_errors)
            )
            self.error_backoff_until = time.time() + backoff_seconds
            self.status = CacheStatus.CRITICAL

            logger.error(
                f"Cache en backoff pour {backoff_seconds}s après {self.consecutive_errors} erreurs"
            )

    def _reset_error_backoff(self):
        """Remet à zéro le compteur d'erreurs"""
        if self.consecutive_errors > 0:
            self.consecutive_errors = 0
            self.error_backoff_until = 0.0
            if self.status == CacheStatus.CRITICAL:
                self.status = CacheStatus.HEALTHY

    async def _check_memory_limits(self) -> bool:
        """Vérifie les limites mémoire et déclenche le nettoyage si nécessaire"""
        try:
            await self._update_memory_stats()

            usage_percent = (
                self.stats.memory_usage_mb / self.config.total_memory_limit_mb
            ) * 100

            if (
                usage_percent
                > (self.config.purge_threshold_mb / self.config.total_memory_limit_mb)
                * 100
            ):
                if self.config.enable_auto_purge:
                    await self._auto_purge_cache()
                return False
            elif (
                usage_percent
                > (self.config.warning_threshold_mb / self.config.total_memory_limit_mb)
                * 100
            ):
                self.status = CacheStatus.WARNING
            else:
                self.status = CacheStatus.HEALTHY

            return True

        except Exception as e:
            logger.error(f"Erreur vérification mémoire: {e}")
            return True  # Autorise en cas d'erreur pour éviter le blocage

    async def _update_memory_stats(self):
        """Met à jour les statistiques mémoire"""
        try:
            info = await self.client.info("memory")
            used_memory_bytes = info.get("used_memory", 0)
            self.stats.memory_usage_mb = used_memory_bytes / (1024 * 1024)

            # Estimation du nombre de clés
            keyspace_info = await self.client.info("keyspace")
            total_keys = sum(
                int(db_info.split("keys=")[1].split(",")[0])
                for db_info in keyspace_info.values()
                if isinstance(db_info, str) and "keys=" in db_info
            )
            self.stats.key_count = total_keys

            # Calcul de la taille moyenne des valeurs
            if total_keys > 0:
                self.stats.avg_value_size = (
                    (used_memory_bytes / total_keys) if total_keys > 0 else 0
                )

            self.last_memory_check = time.time()

        except Exception as e:
            logger.warning(f"Impossible de mettre à jour les stats mémoire: {e}")

    async def _auto_purge_cache(self):
        """Purge automatique du cache en cas de surcharge"""
        logger.warning("Déclenchement purge automatique du cache")

        try:
            # Purge par ordre de priorité (TTL le plus court d'abord)
            namespaces_by_priority = [
                "searches",
                "responses",
                "intents",
                "normalized",
                "embeddings",
            ]

            for namespace in namespaces_by_priority:
                keys_deleted = await self._purge_namespace(
                    namespace, self.config.purge_ratio
                )
                if keys_deleted > 0:
                    logger.info(f"Purge {namespace}: {keys_deleted} clés supprimées")

                # Vérification si suffisant
                await self._update_memory_stats()
                usage_percent = (
                    self.stats.memory_usage_mb / self.config.total_memory_limit_mb
                ) * 100

                if usage_percent < self.config.warning_threshold_mb:
                    break

        except Exception as e:
            logger.error(f"Erreur purge automatique: {e}")

    async def _purge_namespace(self, namespace: str, ratio: float) -> int:
        """Purge un pourcentage des clés d'un namespace"""
        try:
            pattern = self.namespaces.get(namespace, f"{namespace}:") + "*"
            keys = await self.client.keys(pattern)

            if not keys:
                return 0

            # Suppression d'un pourcentage des clés (les plus anciennes en priorité)
            keys_to_delete = int(len(keys) * ratio)
            if keys_to_delete == 0:
                return 0

            # Simple: prendre les premières clés (Redis keys() n'est pas ordonné mais suffisant)
            selected_keys = keys[:keys_to_delete]

            return await self.client.delete(*selected_keys)

        except Exception as e:
            logger.error(f"Erreur purge namespace {namespace}: {e}")
            return 0

    async def _monitor_namespace_limits(self, namespace: str):
        """Surveille les limites par namespace"""
        try:
            pattern = self.namespaces.get(namespace, f"{namespace}:") + "*"
            keys = await self.client.keys(pattern)

            if len(keys) > self.config.max_keys_per_namespace:
                logger.warning(
                    f"Namespace {namespace} dépasse la limite: {len(keys)} clés"
                )
                self.protection_stats["namespace_limit_hits"] += 1
                # Purge ciblée du namespace
                await self._purge_namespace(namespace, 0.2)  # Purge 20%

        except Exception as e:
            logger.warning(f"Erreur monitoring namespace {namespace}: {e}")

    async def _get_namespace_stats(self) -> Dict[str, Dict[str, Any]]:
        """Statistiques par namespace"""
        stats = {}

        for namespace, prefix in self.namespaces.items():
            try:
                pattern = prefix + "*"
                keys = await self.client.keys(pattern)

                stats[namespace] = {
                    "key_count": len(keys),
                    "limit": self.config.max_keys_per_namespace,
                    "usage_percent": (len(keys) / self.config.max_keys_per_namespace)
                    * 100,
                    "ttl": self._get_namespace_ttl(namespace),
                }

            except Exception as e:
                stats[namespace] = {"error": str(e)}

        return stats

    async def cleanup(self):
        """Nettoyage des ressources"""
        if self.client:
            try:
                await self.client.close()
                logger.info("Connexion Redis fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture Redis: {e}")
            finally:
                self.client = None
                self.status = CacheStatus.DISABLED

        await super().close()


# Factory function pour créer une instance de cache
def create_cache_core(config: Optional[CacheConfig] = None) -> RedisCacheCore:
    """
    Crée une instance de cache core avec configuration

    Args:
        config: Configuration optionnelle, sinon utilise les variables d'environnement

    Returns:
        RedisCacheCore: Instance configurée
    """
    return RedisCacheCore(config)


# Export des classes principales
__all__ = [
    "RedisCacheCore",
    "CacheConfig",
    "CacheStats",
    "CacheStatus",
    "create_cache_core",
]
