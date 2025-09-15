# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis pour RAG - OPTIMISÉ
Optimise les performances en cachant embeddings, résultats de recherche et réponses
CORRECTIONS APPLIQUÉES:
- Normalisation intelligente des requêtes pour améliorer les cache hits
- TTL prolongés pour contenu stable avicole
- Cache sémantique basé sur mots-clés métier
- Logs détaillés pour monitoring
"""

import json
import hashlib
import logging
import time
import os
import re
from typing import Dict, List, Optional, Any, Tuple, Set
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
    """Gestionnaire de cache Redis optimisé pour maximiser les hits - Version améliorée"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client = None
        self.enabled = REDIS_AVAILABLE
        
        # Protection OOM - Limites configurables
        self.MAX_VALUE_BYTES = int(os.getenv("CACHE_MAX_VALUE_BYTES", "2000000"))  # 2MB
        self.MAX_KEYS_PER_NAMESPACE = int(os.getenv("CACHE_MAX_KEYS_PER_NS", "1000"))  # 1000 clés
        
        # TTL optimisés pour contenu avicole stable
        self.ttl_config = {
            "embeddings": 86400,     # 24h - embeddings très stables
            "search_results": 7200,   # 2h - résultats recherche
            "responses": 3600,        # 1h - réponses générées (augmenté de 15min à 1h)
            "intent_results": 7200,   # 2h - analyses d'intention
            "verification": 3600,     # 1h - vérifications
            "normalized": 10800       # 3h - cache normalisé
        }
        
        # Vocabulaire avicole pour normalisation sémantique
        self.poultry_keywords = {
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann',  # Lignées
            'fcr', 'poids', 'weight', 'gain', 'croissance', 'growth',  # Métriques
            'poulet', 'chicken', 'poule', 'broiler', 'layer',  # Types
            'starter', 'grower', 'finisher', 'ponte', 'laying',  # Phases
            'temperature', 'ventilation', 'eau', 'water', 'aliment', 'feed',  # Environnement
            'mortalité', 'mortality', 'vaccination', 'maladie'  # Santé
        }
        
        # Mots vides à ignorer pour la normalisation
        self.stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 
            'que', 'qui', 'est', 'sont', 'pour', 'avec', 'dans', 'sur',
            'the', 'a', 'an', 'and', 'or', 'is', 'are', 'for', 'with', 'in', 'on',
            'quel', 'quelle', 'quels', 'what', 'how', 'comment', 'combien'
        }
        
        # Statistiques de protection et cache
        self.protection_stats = {
            "oversized_rejects": 0,
            "lru_purges": 0,
            "namespace_limits_hit": 0
        }
        
        self.cache_stats = {
            "normalized_hits": 0,
            "semantic_hits": 0,
            "exact_hits": 0,
            "total_requests": 0
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
            logger.info(f"Cache Redis optimisé initialisé - Limites: {self.MAX_VALUE_BYTES/1024/1024:.1f}MB/valeur, {self.MAX_KEYS_PER_NAMESPACE} clés/namespace")
            logger.info(f"TTL optimisés: réponses {self.ttl_config['responses']}s, recherches {self.ttl_config['search_results']}s")
            
        except Exception as e:
            logger.warning(f"Erreur connexion Redis: {e} - cache désactivé")
            self.enabled = False
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour maximiser les cache hits"""
        if not text:
            return ""
        
        # Conversion en minuscules et suppression espaces multiples
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        
        # Suppression ponctuation finale
        normalized = re.sub(r'[?!.]+$', '', normalized)
        
        # Normalisation des variations courantes
        normalized = re.sub(r'\bà\b', 'a', normalized)  # "à 35 jours" -> "a 35 jours"
        normalized = re.sub(r'\bjours?\b', 'j', normalized)  # "jours" -> "j"
        normalized = re.sub(r'\bsemaines?\b', 'sem', normalized)  # "semaines" -> "sem"
        
        # Normalisation des lignées
        normalized = re.sub(r'\bross\s*308\b', 'ross308', normalized)
        normalized = re.sub(r'\bcobb\s*500\b', 'cobb500', normalized)
        
        return normalized
    
    def _extract_semantic_keywords(self, text: str) -> Set[str]:
        """Extrait les mots-clés sémantiques pour cache intelligent"""
        words = set(re.findall(r'\b\w+\b', text.lower()))
        
        # Filtrer les mots vides
        meaningful_words = words - self.stopwords
        
        # Identifier les mots-clés avicoles
        poultry_words = meaningful_words & self.poultry_keywords
        
        # Ajouter les nombres (âges, poids, etc.)
        numbers = set(re.findall(r'\b\d+\b', text))
        
        return poultry_words | numbers
    
    def _generate_key(self, prefix: str, data: Any, use_semantic: bool = True) -> str:
        """Génère une clé de cache optimisée avec normalisation"""
        if isinstance(data, str):
            if use_semantic and prefix in ["response", "intent"]:
                # Cache sémantique pour réponses et intentions
                keywords = self._extract_semantic_keywords(data)
                if keywords:
                    semantic_signature = '|'.join(sorted(keywords))
                    hash_obj = hashlib.md5(semantic_signature.encode('utf-8'))
                    return f"intelia_rag:{prefix}:semantic:{hash_obj.hexdigest()}"
            
            # Cache normalisé pour tout le reste
            content = self._normalize_text(data)
        elif isinstance(data, dict):
            # Normaliser les dictionnaires contenant des requêtes
            normalized_dict = data.copy()
            if "query" in normalized_dict:
                normalized_dict["query"] = self._normalize_text(normalized_dict["query"])
            content = json.dumps(normalized_dict, sort_keys=True)
        else:
            content = str(data)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        cache_type = "normalized" if isinstance(data, str) else "exact"
        return f"intelia_rag:{prefix}:{cache_type}:{hash_obj.hexdigest()}"
    
    def _generate_fallback_keys(self, primary_key: str, original_data: Any) -> List[str]:
        """Génère des clés de fallback pour améliorer les hits"""
        fallback_keys = []
        
        if isinstance(original_data, str):
            # Essayer sans normalisation complète
            simple_normalized = re.sub(r'\s+', ' ', original_data.lower().strip())
            if simple_normalized != self._normalize_text(original_data):
                simple_hash = hashlib.md5(simple_normalized.encode()).hexdigest()
                fallback_keys.append(f"intelia_rag:response:simple:{simple_hash}")
        
        return fallback_keys
    
    async def _check_size_and_namespace_quota(self, namespace: str, serialized_data: bytes) -> bool:
        """Vérification taille + quota namespace avec purge LRU"""
        data_size = len(serialized_data)
        
        # 1. Vérification taille maximale
        if data_size > self.MAX_VALUE_BYTES:
            self.protection_stats["oversized_rejects"] += 1
            logger.warning(f"Valeur rejetée (trop large): {data_size} bytes > {self.MAX_VALUE_BYTES} bytes")
            return False
        
        # 2. Vérification quota namespace avec purge LRU si nécessaire
        try:
            key_count = 0
            pattern = f"intelia_rag:{namespace}:*"
            async for _ in self.client.scan_iter(match=pattern):
                key_count += 1
            
            if key_count >= self.MAX_KEYS_PER_NAMESPACE:
                self.protection_stats["namespace_limits_hit"] += 1
                logger.info(f"Quota namespace {namespace} atteint ({key_count}/{self.MAX_KEYS_PER_NAMESPACE}) - Purge LRU")
                
                purged_count = await self._purge_namespace_lru(namespace, key_count // 2)
                self.protection_stats["lru_purges"] += purged_count
                
                if purged_count == 0:
                    logger.warning(f"Échec purge LRU namespace {namespace}")
                    return False
        
        except Exception as e:
            logger.warning(f"Erreur vérification quota namespace {namespace}: {e}")
            return True  # fail-open
        
        return True
    
    async def _purge_namespace_lru(self, namespace: str, target_purge_count: int) -> int:
        """Purge LRU pour un namespace"""
        try:
            keys_with_ttl = []
            pattern = f"intelia_rag:{namespace}:*"
            
            async for key in self.client.scan_iter(match=pattern):
                ttl = await self.client.ttl(key)
                keys_with_ttl.append((key, ttl))
            
            if not keys_with_ttl:
                return 0
            
            # Trier par TTL restant (les plus anciens = TTL le plus faible)
            keys_with_ttl.sort(key=lambda x: x[1] if x[1] >= 0 else float('inf'))
            
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
        """Récupère un embedding depuis le cache avec fallback intelligent"""
        if not self.enabled or not self.client:
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            # Essayer d'abord la clé normalisée
            key = self._generate_key("embedding", text, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = zlib.decompress(cached)
                embedding = pickle.loads(decompressed)
                self.cache_stats["normalized_hits"] += 1
                logger.debug(f"Cache HIT (normalisé): embedding pour '{text[:30]}...'")
                return embedding
            
            # Essayer les clés de fallback
            fallback_keys = self._generate_fallback_keys(key, text)
            for fallback_key in fallback_keys:
                cached = await self.client.get(fallback_key)
                if cached:
                    decompressed = zlib.decompress(cached)
                    embedding = pickle.loads(decompressed)
                    self.cache_stats["exact_hits"] += 1
                    logger.debug(f"Cache HIT (fallback): embedding pour '{text[:30]}...'")
                    return embedding
            
            logger.debug(f"Cache MISS: embedding pour '{text[:30]}...'")
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache embedding: {e}")
        
        return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding avec clés multiples"""
        if not self.enabled or not self.client:
            return
        
        try:
            serialized = pickle.dumps(embedding)
            compressed = zlib.compress(serialized)
            
            if not await self._check_size_and_namespace_quota("embedding", compressed):
                return
            
            # Stocker avec clé normalisée
            key = self._generate_key("embedding", text, use_semantic=False)
            await self.client.setex(
                key, 
                self.ttl_config["embeddings"], 
                compressed
            )
            
            # Stocker aussi avec clés de fallback pour améliorer les hits futurs
            fallback_keys = self._generate_fallback_keys(key, text)
            for fallback_key in fallback_keys:
                try:
                    await self.client.setex(
                        fallback_key,
                        self.ttl_config["embeddings"] // 2,  # TTL plus court pour fallback
                        compressed
                    )
                except:
                    pass  # Ignorer erreurs fallback
            
            logger.debug(f"Cache SET: embedding pour '{text[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache embedding: {e}")
    
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse générée depuis le cache avec recherche intelligente"""
        if not self.enabled or not self.client:
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            # 1. Essayer cache sémantique d'abord
            semantic_key = self._generate_key("response", query, use_semantic=True)
            cached = await self.client.get(semantic_key)
            
            if cached:
                response = cached.decode('utf-8')
                self.cache_stats["semantic_hits"] += 1
                logger.info(f"Cache HIT (sémantique): '{query[:30]}...'")
                return response
            
            # 2. Essayer cache normalisé
            normalized_key = self._generate_key("response", cache_data, use_semantic=False)
            cached = await self.client.get(normalized_key)
            
            if cached:
                response = cached.decode('utf-8')
                self.cache_stats["normalized_hits"] += 1
                logger.info(f"Cache HIT (normalisé): '{query[:30]}...'")
                return response
            
            # 3. Essayer clés de fallback
            fallback_keys = self._generate_fallback_keys(normalized_key, query)
            for fallback_key in fallback_keys:
                cached = await self.client.get(fallback_key)
                if cached:
                    response = cached.decode('utf-8')
                    self.cache_stats["exact_hits"] += 1
                    logger.info(f"Cache HIT (fallback): '{query[:30]}...'")
                    return response
            
            logger.info(f"Cache MISS: '{query[:30]}...' (keywords: {self._extract_semantic_keywords(query)})")
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache réponse: {e}")
        
        return None
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """Met en cache une réponse générée avec clés multiples"""
        if not self.enabled or not self.client:
            return
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            response_bytes = response.encode('utf-8')
            
            if not await self._check_size_and_namespace_quota("response", response_bytes):
                return
            
            # Stocker avec cache sémantique (prioritaire)
            keywords = self._extract_semantic_keywords(query)
            if keywords:
                semantic_key = self._generate_key("response", query, use_semantic=True)
                await self.client.setex(
                    semantic_key,
                    self.ttl_config["responses"],
                    response_bytes
                )
                logger.debug(f"Cache SET (sémantique): '{query[:30]}...' -> keywords: {keywords}")
            
            # Stocker aussi avec cache normalisé
            normalized_key = self._generate_key("response", cache_data, use_semantic=False)
            await self.client.setex(
                normalized_key,
                self.ttl_config["responses"],
                response_bytes
            )
            
            logger.debug(f"Cache SET: réponse '{query[:30]}...' ({len(response_bytes)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache réponse: {e}")
    
    async def get_search_results(self, query_vector: List[float], 
                               where_filter: Dict = None, 
                               top_k: int = 10) -> Optional[List[Dict]]:
        """Récupère des résultats de recherche depuis le cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            cache_data = {
                "vector_hash": hashlib.md5(
                    str(query_vector[:10]).encode()
                ).hexdigest(),
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            key = self._generate_key("search", cache_data, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = zlib.decompress(cached)
                results = pickle.loads(decompressed)
                logger.debug("Cache HIT: résultats de recherche")
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
            
            # Limiter la taille pour éviter OOM
            limited_results = [
                {
                    "content": r.get("content", "")[:500],
                    "metadata": r.get("metadata", {}),
                    "score": r.get("score", 0.0)
                }
                for r in results[:top_k]
            ]
            
            serialized = pickle.dumps(limited_results)
            compressed = zlib.compress(serialized)
            
            if not await self._check_size_and_namespace_quota("search", compressed):
                return
            
            key = self._generate_key("search", cache_data, use_semantic=False)
            await self.client.setex(
                key,
                self.ttl_config["search_results"],
                compressed
            )
            logger.debug(f"Cache SET: {len(results)} résultats de recherche ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache recherche: {e}")
    
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention depuis le cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            # Utiliser cache sémantique pour intentions
            key = self._generate_key("intent", query, use_semantic=True)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = zlib.decompress(cached)
                intent_result = pickle.loads(decompressed)
                logger.debug(f"Cache HIT: analyse d'intention pour '{query[:30]}...'")
                return intent_result
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache intention: {e}")
        
        return None
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        if not self.enabled or not self.client:
            return
        
        try:
            if hasattr(intent_result, '__dict__'):
                data = intent_result.__dict__
            else:
                data = intent_result
            
            serialized = pickle.dumps(data)
            compressed = zlib.compress(serialized)
            
            if not await self._check_size_and_namespace_quota("intent", compressed):
                return
            
            key = self._generate_key("intent", query, use_semantic=True)
            await self.client.setex(
                key,
                self.ttl_config["intent_results"],
                compressed
            )
            logger.debug(f"Cache SET: analyse d'intention '{query[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache intention: {e}")
    
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte optimisé pour le cache"""
        try:
            # Simplifier le hash pour augmenter les hits
            content_summary = []
            for doc in documents[:3]:  # Réduire de 5 à 3 docs
                summary = {
                    "source": doc.get("source", ""),
                    "genetic_line": doc.get("genetic_line", doc.get("geneticLine", "")),
                    "content_words": len(doc.get("content", "").split()),
                    "score_rounded": round(doc.get("score", 0.0), 1)  # Arrondir à 1 décimale au lieu de 3
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
        """Récupère les statistiques du cache avec détails optimisation"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = await self.client.info("memory")
            
            # Compter les clés par type
            type_counts = {}
            cache_type_counts = {"semantic": 0, "normalized": 0, "exact": 0}
            
            for cache_type in ["embedding", "search", "response", "intent"]:
                count = 0
                async for key in self.client.scan_iter(match=f"intelia_rag:{cache_type}:*"):
                    count += 1
                    # Analyser le type de cache
                    if ":semantic:" in key:
                        cache_type_counts["semantic"] += 1
                    elif ":normalized:" in key:
                        cache_type_counts["normalized"] += 1
                    else:
                        cache_type_counts["exact"] += 1
                
                type_counts[cache_type] = count
            
            # Calculer le taux de hit
            total_requests = max(1, self.cache_stats["total_requests"])
            total_hits = (self.cache_stats["semantic_hits"] + 
                         self.cache_stats["normalized_hits"] + 
                         self.cache_stats["exact_hits"])
            hit_rate = total_hits / total_requests
            
            return {
                "enabled": True,
                "memory_used": info.get("used_memory_human", "N/A"),
                "total_keys": await self.client.dbsize(),
                "type_counts": type_counts,
                "cache_type_distribution": cache_type_counts,
                "hit_statistics": {
                    "total_requests": total_requests,
                    "semantic_hits": self.cache_stats["semantic_hits"],
                    "normalized_hits": self.cache_stats["normalized_hits"],
                    "exact_hits": self.cache_stats["exact_hits"],
                    "hit_rate": round(hit_rate, 3),
                    "semantic_hit_rate": round(self.cache_stats["semantic_hits"] / total_requests, 3),
                    "normalized_hit_rate": round(self.cache_stats["normalized_hits"] / total_requests, 3)
                },
                "ttl_config": self.ttl_config,
                "optimization_features": {
                    "semantic_cache": True,
                    "text_normalization": True,
                    "fallback_keys": True,
                    "poultry_keywords": len(self.poultry_keywords),
                    "stopwords": len(self.stopwords)
                },
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
        """Force le nettoyage d'un namespace"""
        if not self.enabled or not self.client:
            return {"error": "cache_disabled"}
        
        try:
            if target_key_count is None:
                target_key_count = self.MAX_KEYS_PER_NAMESPACE // 2
            
            purged = await self._purge_namespace_lru(namespace, target_key_count)
            
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
                # Afficher les stats finales
                stats = await self.get_cache_stats()
                if "hit_statistics" in stats:
                    hit_stats = stats["hit_statistics"]
                    logger.info(f"Stats cache finales - Hit rate: {hit_stats['hit_rate']:.1%}, "
                              f"Semantic: {hit_stats['semantic_hits']}, "
                              f"Normalized: {hit_stats['normalized_hits']}, "
                              f"Exact: {hit_stats['exact_hits']}")
                
                await self.client.close()
                logger.info("Connexion Redis fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture Redis: {e}")


# Classe wrapper pour intégration facile dans RAG Engine
class CachedOpenAIEmbedder:
    """Wrapper pour OpenAI Embedder avec cache Redis optimisé"""
    
    def __init__(self, original_embedder, cache_manager: RAGCacheManager):
        self.original_embedder = original_embedder
        self.cache_manager = cache_manager
    
    async def embed_query(self, text: str) -> List[float]:
        """Embedding avec cache optimisé"""
        # Essayer le cache d'abord
        cached_embedding = await self.cache_manager.get_embedding(text)
        if cached_embedding:
            return cached_embedding
        
        # Générer si pas en cache
        embedding = await self.original_embedder.embed_query(text)
        
        # Mettre en cache avec clés multiples
        if embedding:
            await self.cache_manager.set_embedding(text, embedding)
        
        return embedding
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embedding batch avec cache optimisé"""
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