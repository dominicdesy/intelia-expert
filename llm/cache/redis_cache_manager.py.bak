# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis principal (refactorisé)
Point d'entrée principal pour le cache Redis avec fonctionnalités modulaires
CORRIGÉ: Classes stub renommées pour éviter les conflits de nommage
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# CORRECTION CRITIQUE: Imports relatifs pour modules du package cache
try:
    from .cache_core import RedisCacheCore, CacheConfig

    CACHE_CORE_AVAILABLE = True
    logger.debug("Cache core importé avec succès")
except ImportError as e:
    logger.error(f"Cache core module not available: {e}")
    CACHE_CORE_AVAILABLE = False
    # Lever l'erreur explicite au lieu d'un stub silencieux
    raise ImportError("Cache core requires redis package and proper setup") from e

try:
    from .cache_semantic import SemanticCacheManager

    SEMANTIC_AVAILABLE = True
    logger.debug("Semantic cache importé avec succès")
except ImportError as e:
    logger.warning(f"Semantic cache module not available: {e}")
    SEMANTIC_AVAILABLE = False

    # CORRECTION: Classe stub renommée pour éviter le conflit de nommage
    class SemanticCacheManagerStub:
        """Stub pour SemanticCacheManager quand les dépendances ne sont pas disponibles"""

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(
                "SemanticCacheManager not available - install required dependencies or check module imports"
            )


try:
    from .cache_stats import CacheStatsManager

    STATS_AVAILABLE = True
    logger.debug("Cache stats importé avec succès")
except ImportError as e:
    logger.warning(f"Cache stats module not available: {e}")
    STATS_AVAILABLE = False

    # CORRECTION: Classe stub renommée pour éviter le conflit de nommage
    class CacheStatsManagerStub:
        """Stub pour CacheStatsManager quand les dépendances ne sont pas disponibles"""

        def __init__(self, *args, **kwargs):
            raise NotImplementedError(
                "CacheStatsManager not available - install required dependencies or check module imports"
            )


class RAGCacheManager:
    """
    Gestionnaire de cache Redis principal - Interface unifiée
    Délègue les fonctionnalités aux modules spécialisés
    """

    def __init__(self, redis_url: str = None, default_ttl: int = None):
        """
        Initialise le gestionnaire de cache avec modules spécialisés
        """
        if not CACHE_CORE_AVAILABLE:
            raise ImportError(
                "Cannot initialize RAGCacheManager: Redis dependencies not available"
            )

        try:
            # Créer la configuration depuis l'environnement
            config = CacheConfig.from_env()

            # Optionnellement override avec les paramètres fournis
            if redis_url:
                config.redis_url = redis_url
            if default_ttl:
                config.default_ttl = default_ttl

            # Initialiser le core avec la configuration
            self.core = RedisCacheCore(config)

            # Modules optionnels - avec gestion d'erreurs explicites et classes stub corrigées
            try:
                if SEMANTIC_AVAILABLE:
                    self.semantic = SemanticCacheManager(self.core)
                else:
                    logger.warning(
                        "Semantic cache module not available - related features disabled"
                    )
                    # CORRECTION: Utiliser None au lieu de la classe stub
                    self.semantic = None
            except Exception as e:
                logger.error(f"Failed to initialize semantic cache: {e}")
                self.semantic = None

            try:
                if STATS_AVAILABLE:
                    self.stats = CacheStatsManager(self.core)
                else:
                    logger.warning(
                        "Stats cache module not available - statistics disabled"
                    )
                    # CORRECTION: Utiliser None au lieu de la classe stub
                    self.stats = None
            except Exception as e:
                logger.error(f"Failed to initialize stats cache: {e}")
                self.stats = None

            # Exposer les propriétés importantes pour compatibilité
            self.enabled = getattr(self.core, "enabled", False)
            self.client = None  # Sera défini lors de l'initialisation
            self.initialized = False

            logger.info("RAGCacheManager modules initialisés avec succès")

        except Exception as e:
            logger.error(f"Erreur initialisation RAGCacheManager: {e}")
            raise RuntimeError(f"Failed to initialize RAGCacheManager: {e}") from e

    async def initialize(self):
        """Initialise la connexion Redis"""
        if not self.core:
            logger.error(
                "RAGCacheManager core not available - initialization impossible"
            )
            return False

        try:
            success = await self.core.initialize()
            if success:
                self.client = self.core.client
                self.initialized = self.core.initialized
                self.enabled = self.core.enabled
                logger.info("RAGCacheManager connexion Redis établie")
            else:
                logger.warning("RAGCacheManager connexion Redis échouée")
            return success

        except Exception as e:
            logger.error(f"Erreur initialisation connexion Redis: {e}")
            return False

    def _is_operational(self) -> bool:
        """Vérifie l'état opérationnel"""
        if not self.core:
            return False
        # Accès direct à la méthode _is_operational si elle existe
        if hasattr(self.core, "_is_operational"):
            return self.core._is_operational()
        # Fallback sur les attributs de base
        return (
            getattr(self.core, "initialized", False)
            and getattr(self.core, "client", None) is not None
            and getattr(self.core, "enabled", False)
        )

    # ===== MÉTHODES EMBEDDINGS =====
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding avec cache sémantique intelligent"""
        if not self.semantic:
            logger.debug("Semantic cache not available for get_embedding")
            return None
        try:
            return await self.semantic.get_embedding(text)
        except Exception as e:
            logger.warning(f"Erreur get_embedding: {e}")
            return None

    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding"""
        if not self.semantic:
            logger.debug("Semantic cache not available for set_embedding")
            return
        try:
            await self.semantic.set_embedding(text, embedding)
        except Exception as e:
            logger.warning(f"Erreur set_embedding: {e}")

    # ===== MÉTHODES RÉPONSES =====
    async def get_response(
        self, query: str, context_hash: str, language: str = "fr"
    ) -> Optional[str]:
        """Récupère une réponse avec cascade strict → fallback → simple"""
        if not self.semantic:
            logger.debug("Semantic cache not available for get_response")
            return None
        try:
            return await self.semantic.get_response(query, context_hash, language)
        except Exception as e:
            logger.warning(f"Erreur get_response: {e}")
            return None

    async def set_response(
        self, query: str, context_hash: str, response: str, language: str = "fr"
    ):
        """Met en cache une réponse"""
        if not self.semantic:
            logger.debug("Semantic cache not available for set_response")
            return
        try:
            await self.semantic.set_response(query, context_hash, response, language)
        except Exception as e:
            logger.warning(f"Erreur set_response: {e}")

    # ===== MÉTHODES RECHERCHE =====
    async def get_search_results(
        self, query_vector: List[float], where_filter: Dict = None, top_k: int = 10
    ) -> Optional[List[Dict]]:
        """Récupère des résultats de recherche depuis le cache"""
        if not self.core:
            logger.debug("Core cache not available for get_search_results")
            return None
        try:
            logger.debug(
                "get_search_results: Méthode non encore implémentée dans cache_core"
            )
            return None
        except Exception as e:
            logger.warning(f"Erreur get_search_results: {e}")
            return None

    async def set_search_results(
        self,
        query_vector: List[float],
        where_filter: Dict,
        top_k: int,
        results: List[Dict],
    ):
        """Met en cache des résultats de recherche"""
        if not self.core:
            logger.debug("Core cache not available for set_search_results")
            return
        try:
            logger.debug(
                "set_search_results: Méthode non encore implémentée dans cache_core"
            )
            return
        except Exception as e:
            logger.warning(f"Erreur set_search_results: {e}")

    # ===== MÉTHODES INTENTIONS =====
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention"""
        if not self.semantic:
            logger.debug("Semantic cache not available for get_intent_result")
            return None
        try:
            return await self.semantic.get_intent_result(query)
        except Exception as e:
            logger.warning(f"Erreur get_intent_result: {e}")
            return None

    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        if not self.semantic:
            logger.debug("Semantic cache not available for set_intent_result")
            return
        try:
            await self.semantic.set_intent_result(query, intent_result)
        except Exception as e:
            logger.warning(f"Erreur set_intent_result: {e}")

    # ===== MÉTHODES UTILITAIRES =====
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte pour le cache"""
        import hashlib
        import json

        try:
            content = json.dumps(
                [doc.get("content", "")[:100] for doc in documents], sort_keys=True
            )
            return hashlib.md5(content.encode()).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Erreur generate_context_hash: {e}")
            return hashlib.md5(str(len(documents)).encode()).hexdigest()[:16]

    async def invalidate_pattern(self, pattern: str, namespace: str = "default"):
        """Invalide les clés correspondant à un pattern"""
        if not self.core:
            logger.debug("Core cache not available for invalidate_pattern")
            return
        try:
            await self.core.invalidate_pattern(pattern, namespace)
        except Exception as e:
            logger.warning(f"Erreur invalidate_pattern: {e}")

    # ===== STATISTIQUES =====
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques complètes"""
        base_stats = {
            "enabled": self.enabled,
            "initialized": self.initialized,
            "core_available": CACHE_CORE_AVAILABLE,
            "semantic_available": SEMANTIC_AVAILABLE,
            "stats_available": STATS_AVAILABLE,
            "operational": self._is_operational(),
        }

        if not self.stats:
            logger.debug("Stats module not available")
            return {**base_stats, "note": "Statistics module not available"}
        try:
            stats_data = await self.stats.get_cache_stats()
            return {**base_stats, **stats_data}
        except Exception as e:
            logger.warning(f"Erreur get_cache_stats: {e}")
            return {**base_stats, "error": str(e)}

    async def debug_semantic_extraction(self, query: str) -> Dict[str, Any]:
        """Debug de l'extraction sémantique"""
        if not self.semantic:
            return {
                "error": "Semantic module not available",
                "semantic_available": SEMANTIC_AVAILABLE,
            }
        try:
            return await self.semantic.debug_semantic_extraction(query)
        except Exception as e:
            logger.warning(f"Erreur debug_semantic_extraction: {e}")
            return {"error": str(e)}

    # ===== FERMETURE =====
    async def close(self):
        """Ferme la connexion Redis proprement"""
        if self.core:
            try:
                await self.core.cleanup()
                logger.info("RAGCacheManager connexion fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture cache: {e}")

        self.client = None
        self.initialized = False


# Factory function avec gestion d'erreurs explicite
def create_rag_cache_manager(
    redis_url: str = None, default_ttl: int = None
) -> RAGCacheManager:
    """
    Factory pour créer une instance RAGCacheManager avec gestion d'erreurs explicite

    Args:
        redis_url: URL Redis (optionnel, utilise REDIS_URL par défaut)
        default_ttl: TTL par défaut (optionnel, utilise CACHE_DEFAULT_TTL par défaut)

    Returns:
        RAGCacheManager: Instance configurée

    Raises:
        ImportError: Si les dépendances Redis ne sont pas disponibles
        RuntimeError: Si l'initialisation échoue
    """
    if not CACHE_CORE_AVAILABLE:
        raise ImportError(
            "Cannot create RAGCacheManager: Redis dependencies not available"
        )

    try:
        return RAGCacheManager(redis_url, default_ttl)
    except Exception as e:
        logger.error(f"Impossible de créer RAGCacheManager: {e}")
        raise RuntimeError(f"Failed to create RAGCacheManager: {e}") from e


# Export pour compatibilité
__all__ = ["RAGCacheManager", "create_rag_cache_manager"]
