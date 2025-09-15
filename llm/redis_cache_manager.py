# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis pour RAG
Optimise les performances en cachant embeddings, résultats de recherche et réponses
CORRECTION POINT 4 : Protection OOM et quotas LRU
"""

import json
import hashlib
import logging
import time
import os
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
    """Gestionnaire de cache Redis pour optimiser les performances RAG - AVEC PROTECTION OOM"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client = None
        self.enabled = REDIS_AVAILABLE
        
        # CORRECTION POINT 4 : Protection OOM - Limites configurables
        self.MAX_VALUE_BYTES = int(os.getenv("CACHE_MAX_VALUE_BYTES", "2000000"))  # 2MB par défaut
        self.MAX_KEYS_PER_NAMESPACE = int(os.getenv("CACHE_MAX_KEYS_PER_NS", "1000"))  # 1000 clés par namespace
        
        # TTL configurables par type de cache
        self.ttl_config = {
            "embeddings": 7200,      # 2h - embeddings stables
            "search_results": 1800,   # 30min - résultats recherche
            "responses": 900,         # 15min - réponses générées
            "intent_results": 3600,   # 1h - résultats d'analyse d'intention
            "verification": 1800      # 30min - résultats de vérification
        }
        
        # Statistiques de protection
        self.protection_stats = {
            "oversized_rejects": 0,
            "lru_purges": 0,
            "namespace_limits_hit": 0
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
            logger.info(f"Cache Redis initialisé - Limites: {self.MAX_VALUE_BYTES/1024/1024:.1f}MB par valeur, {self.MAX_KEYS_PER_NAMESPACE} clés/namespace")
            
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
    
    async def _check_size_and_namespace_quota(self, namespace: str, serialized_data: bytes) -> bool:
        """CORRECTION POINT 4 : Vérification taille + quota namespace avec purge LRU"""
        data_size = len(serialized_data)
        
        # 1. Vérification taille maximale
        if data_size > self.MAX_VALUE_BYTES:
            self.protection_stats["oversized_rejects"] += 1
            logger.warning(f"Valeur rejetée (trop large): {data_size} bytes > {self.MAX_VALUE_BYTES} bytes")
            return False
        
        # 2. Vérification quota namespace avec purge LRU si nécessaire
        try:
            # Compter les clés actuelles pour ce namespace
            key_count = 0
            pattern = f"intelia_rag:{namespace}:*"
            async for _ in self.client.scan_iter(match=pattern):
                key_count += 1
            
            # Si on dépasse le quota, déclencher purge LRU
            if key_count >= self.MAX_KEYS_PER_NAMESPACE:
                self.protection_stats["namespace_limits_hit"] += 1
                logger.info(f"Quota namespace {namespace} atteint ({key_count}/{self.MAX_KEYS_PER_NAMESPACE}) - Purge LRU")
                
                # Purger la moitié des clés les plus anciennes
                purged_count = await self._purge_namespace_lru(namespace, key_count // 2)
                self.protection_stats["lru_purges"] += purged_count
                
                if purged_count == 0:
                    logger.warning(f"Échec purge LRU namespace {namespace}")
                    return False
        
        except Exception as e:
            logger.warning(f"Erreur vérification quota namespace {namespace}: {e}")
            # En cas d'erreur, permettre l'écriture (fail-open)
            return True
        
        return True
    
    async def _purge_namespace_lru(self, namespace: str, target_purge_count: int) -> int:
        """Purge LRU pour un namespace - Retourne le nombre de clés supprimées"""
        try:
            keys_with_ttl = []
            pattern = f"intelia_rag:{namespace}:*"
            
            # Collecter toutes les clés avec leur TTL restant
            async for key in self.client.scan_iter(match=pattern):
                ttl = await self.client.ttl(key)
                keys_with_ttl.append((key, ttl))
            
            if not keys_with_ttl:
                return 0
            
            # Trier par TTL restant (les plus anciens = TTL le plus faible)
            # TTL = -1 signifie pas d'expiration, TTL = -2 signifie clé n'existe pas
            keys_with_ttl.sort(key=lambda x: x[1] if x[1] >= 0 else float('inf'))
            
            # Sélectionner les clés à supprimer
            keys_to_delete = [key for key, _ in keys_with_ttl[:target_purge_count]]
            
            if keys_to_delete:
                deleted_count = await self.client.delete(*keys_to_delete)
                logger.info(f"Purge LRU namespace {namespace}: {deleted_count} clés supprimées")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Erreur purge LRU namespace {namespace}: {e}")
            return 0
    
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
        """Met en cache un embedding - AVEC PROTECTION OOM"""
        if not self.enabled or not self.client:
            return
        
        try:
            # Sérialisation et compression
            serialized = pickle.dumps(embedding)
            compressed = zlib.compress(serialized)
            
            # CORRECTION POINT 4 : Vérification taille et quota
            if not await self._check_size_and_namespace_quota("embedding", compressed):
                return
            
            key = self._generate_key("embedding", text)
            await self.client.setex(
                key, 
                self.ttl_config["embeddings"], 
                compressed
            )
            logger.debug(f"Cache set: embedding pour {len(text)} chars ({len(compressed)} bytes)")
            
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
        """Met en cache des résultats de recherche - AVEC PROTECTION OOM"""
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
            
            # Sérialiser les résultats (limiter la taille pour éviter OOM)
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
            
            # CORRECTION POINT 4 : Vérification taille et quota
            if not await self._check_size_and_namespace_quota("search", compressed):
                return
            
            key = self._generate_key("search", cache_data)
            await self.client.setex(
                key,
                self.ttl_config["search_results"],
                compressed
            )
            logger.debug(f"Cache set: {len(results)} résultats de recherche ({len(compressed)} bytes)")
            
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
        """Met en cache une réponse générée - AVEC PROTECTION OOM"""
        if not self.enabled or not self.client:
            return
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            response_bytes = response.encode('utf-8')
            
            # CORRECTION POINT 4 : Vérification taille et quota
            if not await self._check_size_and_namespace_quota("response", response_bytes):
                return
            
            key = self._generate_key("response", cache_data)
            await self.client.setex(
                key,
                self.ttl_config["responses"],
                response_bytes
            )
            logger.debug(f"Cache set: réponse générée ({len(response_bytes)} bytes)")
            
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
        """Met en cache un résultat d'analyse d'intention - AVEC PROTECTION OOM"""
        if not self.enabled or not self.client:
            return
        
        try:
            # Convertir en dict si nécessaire
            if hasattr(intent_result, '__dict__'):
                data = intent_result.__dict__
            else:
                data = intent_result
            
            serialized = pickle.dumps(data)
            compressed = zlib.compress(serialized)
            
            # CORRECTION POINT 4 : Vérification taille et quota
            if not await self._check_size_and_namespace_quota("intent", compressed):
                return
            
            key = self._generate_key("intent", query)
            await self.client.setex(
                key,
                self.ttl_config["intent_results"],
                compressed
            )
            logger.debug(f"Cache set: analyse d'intention ({len(compressed)} bytes)")
            
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
        """Récupère les statistiques du cache - AVEC STATS PROTECTION"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = await self.client.info("memory")
            
            # Compter les clés par type
            type_counts = {}
            total_size_estimates = {}
            
            for cache_type in ["embedding", "search", "response", "intent"]:
                count = 0
                sample_sizes = []
                
                # Échantillonner quelques clés pour estimer la taille
                sample_count = 0
                async for key in self.client.scan_iter(match=f"intelia_rag:{cache_type}:*"):
                    count += 1
                    
                    # Échantillonner les 10 premières pour estimer la taille
                    if sample_count < 10:
                        try:
                            value = await self.client.get(key)
                            if value:
                                sample_sizes.append(len(value))
                            sample_count += 1
                        except:
                            pass
                
                type_counts[cache_type] = count
                
                # Estimation taille totale pour ce type
                if sample_sizes:
                    avg_size = sum(sample_sizes) / len(sample_sizes)
                    total_size_estimates[cache_type] = f"{(avg_size * count / 1024 / 1024):.1f}MB"
                else:
                    total_size_estimates[cache_type] = "0MB"
            
            return {
                "enabled": True,
                "memory_used": info.get("used_memory_human", "N/A"),
                "total_keys": await self.client.dbsize(),
                "type_counts": type_counts,
                "estimated_sizes": total_size_estimates,
                "ttl_config": self.ttl_config,
                "protection_config": {
                    "max_value_bytes": self.MAX_VALUE_BYTES,
                    "max_keys_per_namespace": self.MAX_KEYS_PER_NAMESPACE
                },
                "protection_stats": self.protection_stats
            }
            
        except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def force_namespace_cleanup(self, namespace: str, target_key_count: int = None) -> Dict[str, int]:
        """Force le nettoyage d'un namespace (utile pour maintenance)"""
        if not self.enabled or not self.client:
            return {"error": "cache_disabled"}
        
        try:
            if target_key_count is None:
                target_key_count = self.MAX_KEYS_PER_NAMESPACE // 2
            
            purged = await self._purge_namespace_lru(namespace, target_key_count)
            
            # Recompter après purge
            final_count = 0
            async for _ in self.client.scan_iter(match=f"intelia_rag:{namespace}:*"):
                final_count += 1
            
            return {
                "namespace": namespace,
                "keys_purged": purged,
                "final_key_count": final_count,
                "target_was": target_key_count
            }
            
        except Exception as e:
            logger.error(f"Erreur force cleanup namespace {namespace}: {e}")
            return {"error": str(e)}
    
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
        
        # Mettre en cache (avec protection OOM)
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
            
            # Mettre en cache et ajouter aux résultats (avec protection OOM)
            for idx, embedding in zip(uncached_indices, new_embeddings):
                if embedding:
                    await self.cache_manager.set_embedding(texts[idx], embedding)
                results.append((idx, embedding))
        
        # Trier par index original
        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]