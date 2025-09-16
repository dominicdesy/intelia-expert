# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis principal (refactorisé)
Point d'entrée principal pour le cache Redis avec fonctionnalités modulaires
CORRIGÉ: Imports relatifs remplacés par imports absolus
CORRIGÉ: Gestion d'erreurs robuste pour modules manquants
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# CORRECTION: Imports absolus au lieu d'imports relatifs pour éviter l'erreur
# "attempted relative import with no known parent package"
try:
    from cache_core import RedisCacheCore
except ImportError as e:
    logger.error(f"Impossible d'importer cache_core: {e}")
    raise ImportError("Module cache_core requis non trouvé")

try:
    from cache_semantic import SemanticCacheManager
except ImportError as e:
    logger.error(f"Impossible d'importer cache_semantic: {e}")
    raise ImportError("Module cache_semantic requis non trouvé")

try:
    from cache_stats import CacheStatsManager
except ImportError as e:
    logger.error(f"Impossible d'importer cache_stats: {e}")
    raise ImportError("Module cache_stats requis non trouvé")

class RAGCacheManager:
    """
    Gestionnaire de cache Redis principal - Interface unifiée
    Délègue les fonctionnalités aux modules spécialisés
    CORRIGÉ: Gestion d'erreurs robuste pour l'initialisation
    """
    
    def __init__(self, redis_url: str = None, default_ttl: int = None):
        """Initialise le gestionnaire de cache avec modules spécialisés"""
        try:
            # Initialiser les modules
            self.core = RedisCacheCore(redis_url, default_ttl)
            self.semantic = SemanticCacheManager(self.core)
            self.stats = CacheStatsManager(self.core)
            
            # Exposer les propriétés importantes pour compatibilité
            self.enabled = self.core.enabled
            self.client = None  # Sera défini lors de l'initialisation
            self.initialized = False
            
            logger.info("RAGCacheManager modules initialises avec succes")
            
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
            logger.warning("RAGCacheManager en mode degrade - initialisation impossible")
            return False
            
        try:
            success = await self.core.initialize()
            if success:
                self.client = self.core.client
                self.initialized = self.core.initialized
                logger.info("RAGCacheManager connexion Redis etablie")
            else:
                logger.warning("RAGCacheManager connexion Redis echouee")
            return success
            
        except Exception as e:
            logger.error(f"Erreur initialisation connexion Redis: {e}")
            return False
    
    def _is_initialized(self) -> bool:
        """Vérifie l'état d'initialisation"""
        if not self.core:
            return False
        return self.core._is_initialized()
    
    # ===== MÉTHODES EMBEDDINGS =====
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding avec cache sémantique intelligent"""
        if not self.semantic:
            return None
        try:
            return await self.semantic.get_embedding(text)
        except Exception as e:
            logger.warning(f"Erreur get_embedding: {e}")
            return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding"""
        if not self.semantic:
            return
        try:
            await self.semantic.set_embedding(text, embedding)
        except Exception as e:
            logger.warning(f"Erreur set_embedding: {e}")
    
    # ===== MÉTHODES RÉPONSES =====
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse avec cascade strict → fallback → simple"""
        if not self.semantic:
            return None
        try:
            return await self.semantic.get_response(query, context_hash, language)
        except Exception as e:
            logger.warning(f"Erreur get_response: {e}")
            return None
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """Met en cache une réponse"""
        if not self.semantic:
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
        if not self.core:
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
        if not self.core:
            return
        try:
            await self.core.set_search_results(query_vector, where_filter, top_k, results)
        except Exception as e:
            logger.warning(f"Erreur set_search_results: {e}")
    
    # ===== MÉTHODES INTENTIONS =====
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention"""
        if not self.semantic:
            return None
        try:
            return await self.semantic.get_intent_result(query)
        except Exception as e:
            logger.warning(f"Erreur get_intent_result: {e}")
            return None
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        if not self.semantic:
            return
        try:
            await self.semantic.set_intent_result(query, intent_result)
        except Exception as e:
            logger.warning(f"Erreur set_intent_result: {e}")
    
    # ===== MÉTHODES UTILITAIRES =====
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte pour le cache"""
        if not self.core:
            # Fallback simple si core non disponible
            import hashlib
            import json
            content = json.dumps([doc.get('content', '')[:100] for doc in documents], sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()[:16]
        
        try:
            return self.core.generate_context_hash(documents)
        except Exception as e:
            logger.warning(f"Erreur generate_context_hash: {e}")
            # Fallback
            import hashlib
            import json
            content = json.dumps([doc.get('content', '')[:100] for doc in documents], sort_keys=True)
            return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def invalidate_pattern(self, pattern: str):
        """Invalide les clés correspondant à un pattern"""
        if not self.core:
            return
        try:
            await self.core.invalidate_pattern(pattern)
        except Exception as e:
            logger.warning(f"Erreur invalidate_pattern: {e}")
    
    # ===== STATISTIQUES =====
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques complètes"""
        if not self.stats:
            return {
                "enabled": False,
                "initialized": False,
                "error": "Module stats non disponible"
            }
        try:
            return await self.stats.get_cache_stats()
        except Exception as e:
            logger.warning(f"Erreur get_cache_stats: {e}")
            return {
                "enabled": self.enabled,
                "initialized": self.initialized,
                "error": str(e)
            }
    
    async def debug_semantic_extraction(self, query: str) -> Dict[str, Any]:
        """Debug de l'extraction sémantique"""
        if not self.semantic:
            return {"error": "Module semantic non disponible"}
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
                await self.core.close()
                logger.info("RAGCacheManager connexion fermee")
            except Exception as e:
                logger.warning(f"Erreur fermeture cache: {e}")
        
        self.client = None
        self.initialized = False

# CORRECTION: Factory function avec gestion d'erreurs robuste
def create_rag_cache_manager(redis_url: str = None, default_ttl: int = None) -> Optional[RAGCacheManager]:
    """
    Factory pour créer une instance RAGCacheManager avec gestion d'erreurs
    
    Args:
        redis_url: URL Redis (optionnel)
        default_ttl: TTL par défaut (optionnel)
    
    Returns:
        RAGCacheManager ou None si échec
    """
    try:
        return RAGCacheManager(redis_url, default_ttl)
    except Exception as e:
        logger.error(f"Impossible de creer RAGCacheManager: {e}")
        return None

# Export pour compatibilité
__all__ = [
    'RAGCacheManager',
    'create_rag_cache_manager'
]