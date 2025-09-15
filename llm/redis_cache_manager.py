# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis principal (refactorisé)
Point d'entrée principal pour le cache Redis avec fonctionnalités modulaires
"""

import logging
from typing import Dict, List, Optional, Any
from .cache_core import RedisCacheCore
from .cache_semantic import SemanticCacheManager
from .cache_stats import CacheStatsManager

logger = logging.getLogger(__name__)

class RAGCacheManager:
    """
    Gestionnaire de cache Redis principal - Interface unifiée
    Délègue les fonctionnalités aux modules spécialisés
    """
    
    def __init__(self, redis_url: str = None, default_ttl: int = None):
        """Initialise le gestionnaire de cache avec modules spécialisés"""
        # Initialiser les modules
        self.core = RedisCacheCore(redis_url, default_ttl)
        self.semantic = SemanticCacheManager(self.core)
        self.stats = CacheStatsManager(self.core)
        
        # Exposer les propriétés importantes pour compatibilité
        self.enabled = self.core.enabled
        self.client = None  # Sera défini lors de l'initialisation
        self.initialized = False
    
    async def initialize(self):
        """Initialise la connexion Redis"""
        success = await self.core.initialize()
        if success:
            self.client = self.core.client
            self.initialized = self.core.initialized
        return success
    
    def _is_initialized(self) -> bool:
        """Vérifie l'état d'initialisation"""
        return self.core._is_initialized()
    
    # ===== MÉTHODES EMBEDDINGS =====
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding avec cache sémantique intelligent"""
        return await self.semantic.get_embedding(text)
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding"""
        await self.semantic.set_embedding(text, embedding)
    
    # ===== MÉTHODES RÉPONSES =====
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse avec cascade strict → fallback → simple"""
        return await self.semantic.get_response(query, context_hash, language)
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """Met en cache une réponse"""
        await self.semantic.set_response(query, context_hash, response, language)
    
    # ===== MÉTHODES RECHERCHE =====
    async def get_search_results(self, query_vector: List[float], 
                               where_filter: Dict = None, 
                               top_k: int = 10) -> Optional[List[Dict]]:
        """Récupère des résultats de recherche depuis le cache"""
        return await self.core.get_search_results(query_vector, where_filter, top_k)
    
    async def set_search_results(self, query_vector: List[float], 
                               where_filter: Dict, top_k: int, 
                               results: List[Dict]):
        """Met en cache des résultats de recherche"""
        await self.core.set_search_results(query_vector, where_filter, top_k, results)
    
    # ===== MÉTHODES INTENTIONS =====
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention"""
        return await self.semantic.get_intent_result(query)
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        await self.semantic.set_intent_result(query, intent_result)
    
    # ===== MÉTHODES UTILITAIRES =====
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte pour le cache"""
        return self.core.generate_context_hash(documents)
    
    async def invalidate_pattern(self, pattern: str):
        """Invalide les clés correspondant à un pattern"""
        await self.core.invalidate_pattern(pattern)
    
    # ===== STATISTIQUES =====
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques complètes"""
        return await self.stats.get_cache_stats()
    
    async def debug_semantic_extraction(self, query: str) -> Dict[str, Any]:
        """Debug de l'extraction sémantique"""
        return await self.semantic.debug_semantic_extraction(query)
    
    # ===== FERMETURE =====
    async def close(self):
        """Ferme la connexion Redis proprement"""
        await self.core.close()
        self.client = None
        self.initialized = False