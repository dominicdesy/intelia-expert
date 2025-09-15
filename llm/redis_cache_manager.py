# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis pour RAG
Optimise les performances en cachant embeddings, résultats de recherche et réponses
"""

import json
import hashlib
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
import pickle
import zlib

# Redis imports
try:
    import redis.asyncio as redis
    import hiredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

class RAGCacheManager:
    """Gestionnaire de cache Redis pour optimiser les performances RAG"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client = None
        self.enabled = REDIS_AVAILABLE
        
        # TTL configurables par type de cache
        self.ttl_config = {
            "embeddings": 7200,      # 2h - embeddings stables
            "search_results": 1800,   # 30min - résultats recherche
            "responses": 900,         # 15min - réponses générées
            "intent_results": 3600,   # 1h - résultats d'analyse d'intention
            "verification": 1800      # 30min - résultats de vérification
        }
    
    async def initialize(self):
        """Initialise la connexion Redis"""
        if not self.enabled:
            logger.warning("Redis non disponible - cache désactivé")
            return
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # Pour gérer pickle
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test de connexion
            await self.client.ping()
            logger.info("Cache Redis initialisé")
            
        except Exception as e:
            logger.warning(f"Erreur connexion Redis: {e} - cache désactivé")
            self.enabled = False
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """Génère une clé de cache basée sur le hash du contenu"""
        if isinstance(data, str):
            content = data
        elif isinstance(data, dict):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"intelia_rag:{prefix}:{hash_obj.hexdigest()}"
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding depuis le cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            key = self._generate_key("embedding", text)
            cached = await self.client.get(key)
            
            if cached:
                # Décompression et désérialisation
                decompressed = zlib.decompress(cached)
                embedding = pickle.loads(decompressed)
                logger.debug(f"Cache hit: embedding pour {len(text)} chars")
                return embedding
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache embedding: {e}")
        
        return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding"""
        if not self.enabled or not self.client:
            return
        
        try:
            key = self._generate_key("embedding", text)
            
            # Compression pour réduire l'espace
            serialized = pickle.dumps(embedding)
            compressed = zlib.compress(serialized)
            
            await self.client.setex(
                key, 
                self.ttl_config["embeddings"], 
                compressed
            )
            logger.debug(f"Cache set: embedding pour {len(text)} chars")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache embedding: {e}")
    
    async def get_search_results(self, query_vector: List[float], 
                               where_filter: Dict = None, 
                               top_k: int = 10) -> Optional[List[Dict]]:
        """Récupère des résultats de recherche depuis le cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            # Créer une clé basée sur le vecteur + filtres
            cache_data = {
                "vector_hash": hashlib.md5(
                    str(query_vector[:10]).encode()  # Hash partiel pour performance
                ).hexdigest(),
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            key = self._generate_key("search", cache_data)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = zlib.decompress(cached)
                results = pickle.loads(decompressed)
                logger.debug("Cache hit: résultats de recherche")
                return results
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache recherche: {e}")
        
        return None
    
    async def set_search_results(self, query_vector: List[float], 
                               where_filter: Dict, top_k: int, 
                               results: List[Dict]):
        """Met en cache des résultats de recherche"""
        if not self.enabled or not self.client:
            return
        
        try:
            cache_data = {
                "vector_hash": hashlib.md5(
                    str(query_vector[:10]).encode()
                ).hexdigest(),
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            key = self._generate_key("search", cache_data)
            
            # Sérialiser les résultats (limiter la taille)
            limited_results = [
                {
                    "content": r.get("content", "")[:500],  # Limiter le contenu
                    "metadata": r.get("metadata", {}),
                    "score": r.get("score", 0.0)
                }
                for r in results[:top_k]
            ]
            
            serialized = pickle.dumps(limited_results)
            compressed = zlib.compress(serialized)
            
            await self.client.setex(
                key,
                self.ttl_config["search_results"],
                compressed
            )
            logger.debug(f"Cache set: {len(results)} résultats de recherche")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache recherche: {e}")
    
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse générée depuis le cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            key = self._generate_key("response", cache_data)
            cached = await self.client.get(key)
            
            if cached:
                response = cached.decode('utf-8')
                logger.debug("Cache hit: réponse générée")
                return response
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache réponse: {e}")
        
        return None
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """Met en cache une réponse générée"""
        if not self.enabled or not self.client:
            return
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            key = self._generate_key("response", cache_data)
            
            await self.client.setex(
                key,
                self.ttl_config["responses"],
                response.encode('utf-8')
            )
            logger.debug("Cache set: réponse générée")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache réponse: {e}")
    
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention depuis le cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            key = self._generate_key("intent", query)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = zlib.decompress(cached)
                intent_result = pickle.loads(decompressed)
                logger.debug("Cache hit: analyse d'intention")
                return intent_result
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache intention: {e}")
        
        return None
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        if not self.enabled or not self.client:
            return
        
        try:
            key = self._generate_key("intent", query)
            
            # Convertir en dict si nécessaire
            if hasattr(intent_result, '__dict__'):
                data = intent_result.__dict__
            else:
                data = intent_result
            
            serialized = pickle.dumps(data)
            compressed = zlib.compress(serialized)
            
            await self.client.setex(
                key,
                self.ttl_config["intent_results"],
                compressed
            )
            logger.debug("Cache set: analyse d'intention")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache intention: {e}")
    
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte pour le cache des réponses"""
        try:
            # Créer un hash basé sur le contenu des documents
            content_summary = []
            for doc in documents[:5]:  # Limiter à 5 docs
                summary = {
                    "title": doc.get("title", ""),
                    "source": doc.get("source", ""),
                    "content_length": len(doc.get("content", "")),
                    "score": round(doc.get("score", 0.0), 3)
                }
                content_summary.append(summary)
            
            return hashlib.md5(
                json.dumps(content_summary, sort_keys=True).encode()
            ).hexdigest()
            
        except Exception as e:
            logger.warning(f"Erreur génération hash contexte: {e}")
            return "fallback_hash"
    
    async def invalidate_pattern(self, pattern: str):
        """Invalide les clés correspondant à un pattern"""
        if not self.enabled or not self.client:
            return
        
        try:
            keys = []
            async for key in self.client.scan_iter(match=f"intelia_rag:{pattern}:*"):
                keys.append(key)
            
            if keys:
                await self.client.delete(*keys)
                logger.info(f"Invalidé {len(keys)} clés pour pattern {pattern}")
                
        except Exception as e:
            logger.warning(f"Erreur invalidation pattern: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques du cache"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = await self.client.info("memory")
            
            # Compter les clés par type
            type_counts = {}
            for cache_type in ["embedding", "search", "response", "intent"]:
                count = 0
                async for _ in self.client.scan_iter(match=f"intelia_rag:{cache_type}:*"):
                    count += 1
                type_counts[cache_type] = count
            
            return {
                "enabled": True,
                "memory_used": info.get("used_memory_human", "N/A"),
                "total_keys": await self.client.dbsize(),
                "type_counts": type_counts,
                "ttl_config": self.ttl_config
            }
            
        except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def cleanup(self):
        """Nettoie les ressources Redis"""
        if self.client:
            try:
                await self.client.close()
                logger.info("Connexion Redis fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture Redis: {e}")


# Classe wrapper pour intégration facile dans RAG Engine
class CachedOpenAIEmbedder:
    """Wrapper pour OpenAI Embedder avec cache Redis"""
    
    def __init__(self, original_embedder, cache_manager: RAGCacheManager):
        self.original_embedder = original_embedder
        self.cache_manager = cache_manager
    
    async def embed_query(self, text: str) -> List[float]:
        """Embedding avec cache"""
        # Essayer le cache d'abord
        cached_embedding = await self.cache_manager.get_embedding(text)
        if cached_embedding:
            return cached_embedding
        
        # Générer si pas en cache
        embedding = await self.original_embedder.embed_query(text)
        
        # Mettre en cache
        if embedding:
            await self.cache_manager.set_embedding(text, embedding)
        
        return embedding
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embedding batch avec cache"""
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # Vérifier le cache pour chaque texte
        for i, text in enumerate(texts):
            cached = await self.cache_manager.get_embedding(text)
            if cached:
                results.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Générer les embeddings manquants
        if uncached_texts:
            new_embeddings = await self.original_embedder.embed_documents(uncached_texts)
            
            # Mettre en cache et ajouter aux résultats
            for idx, embedding in zip(uncached_indices, new_embeddings):
                if embedding:
                    await self.cache_manager.set_embedding(texts[idx], embedding)
                results.append((idx, embedding))
        
        # Trier par index original
        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]