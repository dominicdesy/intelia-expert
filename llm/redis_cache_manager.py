# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis principal (refactorisé)
Point d'entrée principal pour le cache Redis avec fonctionnalités modulaires
CORRIGÉ: Arguments constructeur RedisCacheCore selon signature réelle
CORRIGÉ: Utilisation des variables d'environnement correctes
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# CORRECTION: Imports absolus avec fallbacks robustes
try:
    from cache_core import RedisCacheCore, CacheConfig
    CACHE_CORE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Impossible d'importer cache_core: {e}")
    CACHE_CORE_AVAILABLE = False
    # Stub pour éviter les crashes
    class RedisCacheCore:
        def __init__(self, *args, **kwargs):
            self.enabled = False
            self.initialized = False
            self.client = None
    class CacheConfig:
        @classmethod
        def from_env(cls):
            return cls()

try:
    from cache_semantic import SemanticCacheManager
    SEMANTIC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Module cache_semantic non disponible: {e}")
    SEMANTIC_AVAILABLE = False
    class SemanticCacheManager:
        def __init__(self, *args, **kwargs):
            pass

try:
    from cache_stats import CacheStatsManager
    STATS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Module cache_stats non disponible: {e}")
    STATS_AVAILABLE = False
    class CacheStatsManager:
        def __init__(self, *args, **kwargs):
            pass

class RAGCacheManager:
    """
    Gestionnaire de cache Redis principal - Interface unifiée
    Délègue les fonctionnalités aux modules spécialisés
    CORRIGÉ: Constructeur compatible avec RedisCacheCore(config: Optional[CacheConfig])
    """
    
    def __init__(self, redis_url: str = None, default_ttl: int = None):
        """
        Initialise le gestionnaire de cache avec modules spécialisés
        
        CORRECTION MAJEURE: RedisCacheCore ne prend qu'un seul argument (config)
        selon la signature: __init__(self, config: Optional[CacheConfig] = None)
        """
        try:
            # CORRECTION: Utiliser la configuration depuis les variables d'environnement
            # Au lieu de passer redis_url et default_ttl directement
            
            if CACHE_CORE_AVAILABLE:
                # Créer la configuration depuis l'environnement
                config = CacheConfig.from_env()
                
                # Optionnellement override avec les paramètres fournis
                if redis_url:
                    config.redis_url = redis_url
                if default_ttl:
                    config.default_ttl = default_ttl
                
                # CORRECTION: Un seul argument au lieu de deux
                self.core = RedisCacheCore(config)
            else:
                self.core = RedisCacheCore()  # Version stub
            
            # Modules optionnels
            if SEMANTIC_AVAILABLE:
                self.semantic = SemanticCacheManager(self.core)
            else:
                self.semantic = SemanticCacheManager()  # Stub
                
            if STATS_AVAILABLE:
                self.stats = CacheStatsManager(self.core)
            else:
                self.stats = CacheStatsManager()  # Stub
            
            # Exposer les propriétés importantes pour compatibilité
            self.enabled = getattr(self.core, 'enabled', False)
            self.client = None  # Sera défini lors de l'initialisation
            self.initialized = False
            
            logger.info("RAGCacheManager modules initialisés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur initialisation RAGCacheManager: {e}")
            # Mode dégradé : créer des stubs pour éviter les crashes
            self.core = None
            self.semantic = None
            self.stats = None
            self.enabled = False
            self.client = None
            self.initialized = False
            raise
    
    async def initialize(self):
        """Initialise la connexion Redis"""
        if not self.core:
            logger.warning("RAGCacheManager en mode dégradé - initialisation impossible")
            return False
            
        try:
            success = await self.core.initialize()
            if success:
                self.client = self.core.client
                self.initialized = self.core.initialized
                logger.info("RAGCacheManager connexion Redis établie")
            else:
                logger.warning("RAGCacheManager connexion Redis échouée")
            return success
            
        except Exception as e:
            logger.error(f"Erreur initialisation connexion Redis: {e}")
            return False
    
    def _is_initialized(self) -> bool:
        """Vérifie l'état d'initialisation"""
        if not self.core:
            return False
        return getattr(self.core, '_is_initialized', lambda: False)()
    
    # ===== MÉTHODES EMBEDDINGS =====
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding avec cache sémantique intelligent"""
        if not self.semantic or not SEMANTIC_AVAILABLE:
            return None
        try:
            return await self.semantic.get_embedding(text)
        except Exception as e:
            logger.warning(f"Erreur get_embedding: {e}")
            return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding"""
        if not self.semantic or not SEMANTIC_AVAILABLE:
            return
        try:
            await self.semantic.set_embedding(text, embedding)
        except Exception as e:
            logger.warning(f"Erreur set_embedding: {e}")
    
    # ===== MÉTHODES RÉPONSES =====
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse avec cascade strict → fallback → simple"""
        if not self.semantic or not SEMANTIC_AVAILABLE:
            return None
        try:
            return await self.semantic.get_response(query, context_hash, language)
        except Exception as e:
            logger.warning(f"Erreur get_response: {e}")
            return None
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """Met en cache une réponse"""
        if not self.semantic or not SEMANTIC_AVAILABLE:
            return
        try:
            await self.semantic.set_response(query, context_hash, response, language)
        except Exception as e:
            logger.warning(f"Erreur set_response: {e}")
    
    # ===== MÉTHODES RECHERCHE =====
    async def get_search_results(self, query_vector: List[float], 
                               where_filter: Dict = None, 
                               top_k: int = 10) -> Optional[List[Dict]]:
        """Récupère des résultats de recherche depuis le cache"""
        if not self.core or not CACHE_CORE_AVAILABLE:
            return None
        try:
            return await self.core.get_search_results(query_vector, where_filter, top_k)
        except Exception as e:
            logger.warning(f"Erreur get_search_results: {e}")
            return None
    
    async def set_search_results(self, query_vector: List[float], 
                               where_filter: Dict, top_k: int, 
                               results: List[Dict]):
        """Met en cache des résultats de recherche"""
        if not self.core or not CACHE_CORE_AVAILABLE:
            return
        try:
            await self.core.set_search_results(query_vector, where_filter, top_k, results)
        except Exception as e:
            logger.warning(f"Erreur set_search_results: {e}")
    
    # ===== MÉTHODES INTENTIONS =====
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention"""
        if not self.semantic or not SEMANTIC_AVAILABLE:
            return None
        try:
            return await self.semantic.get_intent_result(query)
        except Exception as e:
            logger.warning(f"Erreur get_intent_result: {e}")
            return None
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        if not self.semantic or not SEMANTIC_AVAILABLE:
            return
        try:
            await self.semantic.set_intent_result(query, intent_result)
        except Exception as e:
            logger.warning(f"Erreur set_intent_result: {e}")
    
    # ===== MÉTHODES UTILITAIRES =====
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte pour le cache"""
        if self.core and CACHE_CORE_AVAILABLE:
            try:
                return self.core.generate_context_hash(documents)
            except Exception as e:
                logger.warning(f"Erreur generate_context_hash: {e}")
        
        # Fallback simple
        import hashlib
        import json
        try:
            content = json.dumps([doc.get('content', '')[:100] for doc in documents], sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Erreur fallback hash: {e}")
            return hashlib.md5(str(len(documents)).encode()).hexdigest()[:16]
    
    async def invalidate_pattern(self, pattern: str):
        """Invalide les clés correspondant à un pattern"""
        if not self.core or not CACHE_CORE_AVAILABLE:
            return
        try:
            await self.core.invalidate_pattern(pattern)
        except Exception as e:
            logger.warning(f"Erreur invalidate_pattern: {e}")
    
    # ===== STATISTIQUES =====
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques complètes"""
        if not self.stats or not STATS_AVAILABLE:
            return {
                "enabled": self.enabled,
                "initialized": self.initialized,
                "error": "Module stats non disponible",
                "core_available": CACHE_CORE_AVAILABLE,
                "semantic_available": SEMANTIC_AVAILABLE,
                "stats_available": STATS_AVAILABLE
            }
        try:
            return await self.stats.get_cache_stats()
        except Exception as e:
            logger.warning(f"Erreur get_cache_stats: {e}")
            return {
                "enabled": self.enabled,
                "initialized": self.initialized,
                "error": str(e),
                "core_available": CACHE_CORE_AVAILABLE,
                "semantic_available": SEMANTIC_AVAILABLE,
                "stats_available": STATS_AVAILABLE
            }
    
    async def debug_semantic_extraction(self, query: str) -> Dict[str, Any]:
        """Debug de l'extraction sémantique"""
        if not self.semantic or not SEMANTIC_AVAILABLE:
            return {
                "error": "Module semantic non disponible",
                "semantic_available": SEMANTIC_AVAILABLE
            }
        try:
            return await self.semantic.debug_semantic_extraction(query)
        except Exception as e:
            logger.warning(f"Erreur debug_semantic_extraction: {e}")
            return {"error": str(e)}
    
    # ===== FERMETURE =====
    async def close(self):
        """Ferme la connexion Redis proprement"""
        if self.core and CACHE_CORE_AVAILABLE:
            try:
                await self.core.close()
                logger.info("RAGCacheManager connexion fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture cache: {e}")
        
        self.client = None
        self.initialized = False

# Factory function avec gestion d'erreurs robuste
def create_rag_cache_manager(redis_url: str = None, default_ttl: int = None) -> Optional[RAGCacheManager]:
    """
    Factory pour créer une instance RAGCacheManager avec gestion d'erreurs
    
    Args:
        redis_url: URL Redis (optionnel, utilise REDIS_URL par défaut)
        default_ttl: TTL par défaut (optionnel, utilise CACHE_DEFAULT_TTL par défaut)
    
    Returns:
        RAGCacheManager ou None si échec
    """
    try:
        return RAGCacheManager(redis_url, default_ttl)
    except Exception as e:
        logger.error(f"Impossible de créer RAGCacheManager: {e}")
        return None

# Export pour compatibilité
__all__ = [
    'RAGCacheManager',
    'create_rag_cache_manager'
]