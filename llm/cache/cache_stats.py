# -*- coding: utf-8 -*-
"""
cache_stats.py - Module de gestion des statistiques du cache
Collecte et présentation des métriques de performance
CORRIGÉ: Utilisation de self.core.config au lieu d'attributs directs inexistants
"""

import logging
from utils.types import Dict, Any

logger = logging.getLogger(__name__)


class CacheStatsManager:
    """Gestionnaire des statistiques et métriques du cache"""

    def __init__(self, core_cache):
        self.core = core_cache

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques complètes avec métriques fallback sémantique"""
        if not self.core._is_initialized():
            return {"enabled": False, "initialized": False}

        try:
            info = await self.core.client.info("memory")
            # CORRECTION: Utiliser la méthode existante au lieu d'une méthode inexistante
            memory_usage_mb = self.core.stats.memory_usage_mb
            total_keys = await self.core.client.dbsize()

            # Récupérer les stats depuis le module sémantique
            semantic_module = None
            for attr_name in dir(self.core):
                attr = getattr(self.core, attr_name)
                if hasattr(attr, "cache_stats") and hasattr(
                    attr, "_extract_semantic_keywords_strict"
                ):
                    semantic_module = attr
                    break

            if semantic_module:
                cache_stats = semantic_module.cache_stats
            else:
                # Fallback si le module sémantique n'est pas trouvé
                cache_stats = {
                    "exact_hits": 0,
                    "semantic_hits": 0,
                    "semantic_fallback_hits": 0,
                    "fallback_hits": 0,
                    "total_requests": 0,
                    "saved_operations": 0,
                    "alias_normalizations": 0,
                    "keyword_extractions": 0,
                    "semantic_false_positives_avoided": 0,
                    "init_attempts": 0,
                }

            # Calculer les taux de hit avec fallback sémantique
            total_requests = max(1, cache_stats["total_requests"])
            exact_hit_rate = cache_stats["exact_hits"] / total_requests
            semantic_hit_rate = cache_stats["semantic_hits"] / total_requests
            semantic_fallback_hit_rate = (
                cache_stats["semantic_fallback_hits"] / total_requests
            )
            fallback_hit_rate = cache_stats["fallback_hits"] / total_requests

            total_hit_rate = (
                cache_stats["exact_hits"]
                + cache_stats["semantic_hits"]
                + cache_stats["semantic_fallback_hits"]
                + cache_stats["fallback_hits"]
            ) / total_requests

            return {
                "enabled": True,
                "initialized": self.core.is_initialized,
                "approach": "enhanced_semantic_cache_with_strict_validation_and_fallback_v3.0_modular",
                "memory": {
                    "used_mb": round(memory_usage_mb, 2),
                    "used_human": info.get("used_memory_human", "N/A"),
                    # CORRECTION: Utiliser self.core.config au lieu d'attributs directs
                    "limit_mb": self.core.config.total_memory_limit_mb,
                    "usage_percent": round(
                        (memory_usage_mb / self.core.config.total_memory_limit_mb)
                        * 100,
                        1,
                    ),
                },
                "keys": {
                    "total": total_keys,
                    # CORRECTION: Utiliser self.core.config au lieu d'attributs directs
                    "max_per_namespace": self.core.config.max_keys_per_namespace,
                },
                "hit_statistics": {
                    "total_requests": total_requests,
                    "exact_hits": cache_stats["exact_hits"],
                    "semantic_hits": cache_stats["semantic_hits"],
                    "semantic_fallback_hits": cache_stats["semantic_fallback_hits"],
                    "fallback_hits": cache_stats["fallback_hits"],
                    "exact_hit_rate": round(exact_hit_rate, 3),
                    "semantic_hit_rate": round(semantic_hit_rate, 3),
                    "semantic_fallback_hit_rate": round(semantic_fallback_hit_rate, 3),
                    "fallback_hit_rate": round(fallback_hit_rate, 3),
                    "total_hit_rate": round(total_hit_rate, 3),
                    "last_hit_type": (
                        getattr(semantic_module, "hit_type_last", None)
                        if semantic_module
                        else None
                    ),
                },
                "semantic_validation": {
                    "min_keywords_required": (
                        getattr(semantic_module, "SEMANTIC_MIN_KEYWORDS", 2)
                        if semantic_module
                        else 2
                    ),
                    "context_required": (
                        getattr(semantic_module, "SEMANTIC_CONTEXT_REQUIRED", True)
                        if semantic_module
                        else True
                    ),
                    "rejections": self.core.protection_stats.get(
                        "semantic_rejections", 0
                    ),
                    "false_positives_avoided": cache_stats[
                        "semantic_false_positives_avoided"
                    ],
                    "fallback_enabled": (
                        getattr(semantic_module, "ENABLE_SEMANTIC_FALLBACK", False)
                        if semantic_module
                        else False
                    ),
                    "extended_patterns": (
                        len(getattr(semantic_module, "extended_line_patterns", {}))
                        if semantic_module
                        else 0
                    ),
                },
                "configuration": {
                    # CORRECTION: Utiliser self.core.config au lieu d'attributs directs
                    "max_value_kb": round(self.core.config.max_value_bytes / 1024, 1),
                    "ttl_config_minutes": {
                        k: round(v / 60, 1) for k, v in self.core.ttl_config.items()
                    },
                    "compression_enabled": self.core.config.enable_compression,
                    "semantic_cache_enabled": (
                        getattr(semantic_module, "ENABLE_SEMANTIC_CACHE", False)
                        if semantic_module
                        else False
                    ),
                    "semantic_fallback_enabled": (
                        getattr(semantic_module, "ENABLE_SEMANTIC_FALLBACK", False)
                        if semantic_module
                        else False
                    ),
                    "fallback_keys_enabled": (
                        getattr(semantic_module, "ENABLE_FALLBACK_KEYS", False)
                        if semantic_module
                        else False
                    ),
                    "auto_purge_enabled": self.core.config.enable_auto_purge,
                },
                "semantic_enhancements": {
                    "aliases_categories": (
                        len(getattr(semantic_module, "aliases", {}))
                        if semantic_module
                        else 0
                    ),
                    "vocabulary_size": (
                        len(getattr(semantic_module, "poultry_keywords", set()))
                        if semantic_module
                        else 0
                    ),
                    "alias_normalizations": cache_stats["alias_normalizations"],
                    "keyword_extractions": cache_stats["keyword_extractions"],
                    "stopwords_count": (
                        len(getattr(semantic_module, "stopwords", set()))
                        if semantic_module
                        else 0
                    ),
                    "extended_line_patterns": (
                        len(getattr(semantic_module, "extended_line_patterns", {}))
                        if semantic_module
                        else 0
                    ),
                },
                "protection_stats": self.core.protection_stats,
                "performance": {
                    "saved_operations": cache_stats["saved_operations"],
                    "init_attempts": cache_stats["init_attempts"],
                    "features_enabled": {
                        # CORRECTION: Utiliser self.core.config au lieu d'attributs directs
                        "compression": self.core.config.enable_compression,
                        "semantic_cache": (
                            getattr(semantic_module, "ENABLE_SEMANTIC_CACHE", False)
                            if semantic_module
                            else False
                        ),
                        "semantic_fallback": (
                            getattr(semantic_module, "ENABLE_SEMANTIC_FALLBACK", False)
                            if semantic_module
                            else False
                        ),
                        "fallback_keys": (
                            getattr(semantic_module, "ENABLE_FALLBACK_KEYS", False)
                            if semantic_module
                            else False
                        ),
                        "intelligent_aliases": (
                            bool(getattr(semantic_module, "aliases", {}))
                            if semantic_module
                            else False
                        ),
                        "strict_semantic_validation": True,
                        "extended_normalization": True,
                        "modular_architecture": True,
                    },
                },
                "architecture": {
                    "modules": ["core", "semantic", "stats"],
                    "version": "3.0_modular",
                    "refactored": True,
                    "maintainability": "high",
                },
            }

        except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {
                "enabled": True,
                "initialized": self.core.is_initialized,
                "error": str(e),
            }
