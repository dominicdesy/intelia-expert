# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis optimisé pour performance
Version corrigée avec support complet des variables d'environnement
CORRECTIONS APPLIQUÉES: Configuration dynamique via variables d'environnement
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
    """Gestionnaire de cache Redis optimisé avec configuration via variables d'environnement"""
    
    def __init__(self, redis_url: str = None, default_ttl: int = None):
        # Configuration Redis de base
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = default_ttl or int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
        self.client = None
        self.enabled = REDIS_AVAILABLE and os.getenv("CACHE_ENABLED", "true").lower() == "true"
        
        # Limites mémoire depuis variables d'environnement
        self.MAX_VALUE_BYTES = int(os.getenv("CACHE_MAX_VALUE_BYTES", "200000"))
        self.MAX_KEYS_PER_NAMESPACE = int(os.getenv("CACHE_MAX_KEYS_PER_NS", "2000"))
        self.TOTAL_MEMORY_LIMIT_MB = int(os.getenv("CACHE_TOTAL_MEMORY_LIMIT_MB", "150"))
        
        # Seuils d'alerte depuis variables d'environnement
        self.WARNING_THRESHOLD_MB = int(os.getenv("CACHE_WARNING_THRESHOLD_MB", "120"))
        self.PURGE_THRESHOLD_MB = int(os.getenv("CACHE_PURGE_THRESHOLD_MB", "130"))
        self.STATS_LOG_INTERVAL = int(os.getenv("CACHE_STATS_LOG_INTERVAL", "600"))
        
        # TTL configurables via variables d'environnement
        self.ttl_config = {
            "embeddings": int(os.getenv("CACHE_TTL_EMBEDDINGS", "3600")),
            "search_results": int(os.getenv("CACHE_TTL_SEARCHES", "1800")),
            "responses": int(os.getenv("CACHE_TTL_RESPONSES", "1800")),
            "intent_results": int(os.getenv("CACHE_TTL_INTENTS", "3600")),
            "verification": int(os.getenv("CACHE_TTL_VERIFICATION", "1800")),
            "normalized": int(os.getenv("CACHE_TTL_NORMALIZED", "3600"))
        }
        
        # Fonctionnalités configurables via variables d'environnement
        self.ENABLE_COMPRESSION = os.getenv("CACHE_ENABLE_COMPRESSION", "false").lower() == "true"
        self.ENABLE_SEMANTIC_CACHE = os.getenv("CACHE_ENABLE_SEMANTIC", "false").lower() == "true"
        self.ENABLE_FALLBACK_KEYS = os.getenv("CACHE_ENABLE_FALLBACK", "false").lower() == "true"
        self.MAX_SEARCH_CONTENT_LENGTH = int(os.getenv("CACHE_MAX_SEARCH_CONTENT", "300"))
        
        # Configuration purge depuis variables d'environnement
        self.LRU_PURGE_RATIO = float(os.getenv("CACHE_LRU_PURGE_RATIO", "0.4"))
        self.ENABLE_AUTO_PURGE = os.getenv("CACHE_ENABLE_AUTO_PURGE", "true").lower() == "true"
        
        # Vocabulaire avicole (activé seulement si cache sémantique activé)
        self.poultry_keywords = {
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann',
            'fcr', 'poids', 'weight', 'gain', 'croissance',
            'poulet', 'chicken', 'poule', 'broiler', 'layer',
            'starter', 'grower', 'finisher', 'ponte',
            'indice', 'conversion', '308', '500', '35', '21', '7'
        } if self.ENABLE_SEMANTIC_CACHE else set()
        
        # Mots vides (activés seulement si fallback activé)
        self.stopwords = {
            'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'que', 'est', 'pour',
            'the', 'a', 'and', 'or', 'is', 'are', 'for', 'with', 'in', 'on'
        } if self.ENABLE_FALLBACK_KEYS else set()
        
        # Statistiques
        self.protection_stats = {
            "oversized_rejects": 0,
            "lru_purges": 0,
            "namespace_limits_hit": 0,
            "memory_warnings": 0,
            "auto_purges": 0
        }
        
        self.cache_stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "total_requests": 0,
            "saved_operations": 0
        }
        
        # Monitoring
        self.last_memory_check = 0
        self.last_stats_log = 0
    
    async def initialize(self):
        """Initialise la connexion Redis avec affichage de la configuration réelle"""
        if not self.enabled:
            logger.warning("Cache Redis désactivé via CACHE_ENABLED=false")
            return
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis non disponible - cache désactivé")
            self.enabled = False
            return
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=60
            )
            
            # Test de connexion
            await self.client.ping()
            
            # Log de la configuration réelle depuis les variables d'environnement
            logger.info("Cache Redis initialisé avec configuration:")
            logger.info(f"  - Limite valeur: {self.MAX_VALUE_BYTES/1024:.0f} KB")
            logger.info(f"  - Limite clés/namespace: {self.MAX_KEYS_PER_NAMESPACE}")
            logger.info(f"  - Limite mémoire totale: {self.TOTAL_MEMORY_LIMIT_MB} MB")
            logger.info(f"  - TTL embeddings: {self.ttl_config['embeddings']}s ({self.ttl_config['embeddings']//60}min)")
            logger.info(f"  - TTL réponses: {self.ttl_config['responses']}s ({self.ttl_config['responses']//60}min)")
            logger.info(f"  - Compression: {self.ENABLE_COMPRESSION}")
            logger.info(f"  - Cache sémantique: {self.ENABLE_SEMANTIC_CACHE}")
            logger.info(f"  - Clés fallback: {self.ENABLE_FALLBACK_KEYS}")
            logger.info(f"  - Auto-purge: {self.ENABLE_AUTO_PURGE}")
            logger.info(f"  - Vocabulaire avicole: {len(self.poultry_keywords)} mots-clés")
            
        except Exception as e:
            logger.warning(f"Erreur connexion Redis: {e} - cache désactivé")
            self.enabled = False
    
    def _normalize_text(self, text: str) -> str:
        """Normalisation de texte pour maximiser les cache hits"""
        if not text:
            return ""
        
        # Normalisation de base
        normalized = text.lower().strip()
        
        # Suppression espaces multiples et ponctuation finale
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[?!.]+$', '', normalized)
        
        # Normalisation spécifique aviculture
        normalized = re.sub(r'\bjours?\b', 'j', normalized)
        normalized = re.sub(r'\bross\s*308\b', 'ross308', normalized)
        normalized = re.sub(r'\bcobb\s*500\b', 'cobb500', normalized)
        normalized = re.sub(r'\bindice\s+conversion\b', 'fcr', normalized)
        normalized = re.sub(r'\bà\s+(\d+)\s*j\b', r'\1j', normalized)
        
        return normalized
    
    def _generate_key(self, prefix: str, data: Any, use_semantic: bool = False) -> str:
        """Génère une clé de cache (simple ou sémantique selon configuration)"""
        if isinstance(data, str):
            # Essayer d'abord le cache sémantique si activé
            if use_semantic and self.ENABLE_SEMANTIC_CACHE and prefix in ["response", "intent"]:
                keywords = self._extract_semantic_keywords_fast(data)
                if keywords:
                    semantic_signature = '|'.join(sorted(keywords))
                    hash_obj = hashlib.md5(semantic_signature.encode('utf-8'))
                    return f"intelia_rag:{prefix}:semantic:{hash_obj.hexdigest()}"
            
            # Cache normalisé standard
            content = self._normalize_text(data)
        elif isinstance(data, dict):
            # Normaliser les dictionnaires contenant des requêtes
            normalized_dict = data.copy()
            if "query" in normalized_dict:
                normalized_dict["query"] = self._normalize_text(normalized_dict["query"])
            content = json.dumps(normalized_dict, sort_keys=True, separators=(',', ':'))
        else:
            content = str(data)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"intelia_rag:{prefix}:simple:{hash_obj.hexdigest()}"
    
    def _extract_semantic_keywords_fast(self, text: str) -> Set[str]:
        """Extraction rapide de keywords sémantiques (si activé)"""
        if not self.ENABLE_SEMANTIC_CACHE or not self.poultry_keywords:
            return set()
        
        words = set(re.findall(r'\b\w+\b', text.lower()))
        
        # Identifier les mots-clés avicoles
        poultry_words = words & self.poultry_keywords
        
        # Ajouter les nombres (âges, poids, etc.)
        numbers = set(re.findall(r'\b\d+\b', text))
        
        return poultry_words | numbers
    
    def _generate_fallback_keys(self, primary_key: str, original_data: Any) -> List[str]:
        """Génère des clés de fallback si activé"""
        if not self.ENABLE_FALLBACK_KEYS:
            return []
        
        fallback_keys = []
        
        if isinstance(original_data, str):
            # Version simple sans normalisation complète
            simple_normalized = re.sub(r'\s+', ' ', original_data.lower().strip())
            if simple_normalized != self._normalize_text(original_data):
                simple_hash = hashlib.md5(simple_normalized.encode()).hexdigest()
                fallback_keys.append(f"intelia_rag:response:fallback:{simple_hash}")
        
        return fallback_keys
    
    async def _get_memory_usage_mb(self) -> float:
        """Récupère l'usage mémoire Redis en MB"""
        try:
            info = await self.client.info("memory")
            used_memory = info.get("used_memory", 0)
            return used_memory / (1024 * 1024)
        except:
            return 0.0
    
    async def _check_memory_limits(self) -> bool:
        """Vérification mémoire avec fréquence configurable"""
        now = time.time()
        
        # Vérifier selon la fréquence configurée
        if now - self.last_memory_check < 60:
            return True
        
        self.last_memory_check = now
        
        try:
            memory_usage_mb = await self._get_memory_usage_mb()
            
            # Log périodique selon l'intervalle configuré
            if now - self.last_stats_log > self.STATS_LOG_INTERVAL:
                self.last_stats_log = now
                logger.info(f"Cache Redis: {memory_usage_mb:.1f}MB utilisés / {self.TOTAL_MEMORY_LIMIT_MB}MB limite")
            
            # Alertes selon seuils configurés
            if memory_usage_mb > self.WARNING_THRESHOLD_MB:
                self.protection_stats["memory_warnings"] += 1
                logger.warning(f"Cache Redis proche de la limite: {memory_usage_mb:.1f}MB / {self.TOTAL_MEMORY_LIMIT_MB}MB")
            
            # Purge automatique selon seuil configuré
            if memory_usage_mb > self.PURGE_THRESHOLD_MB and self.ENABLE_AUTO_PURGE:
                self.protection_stats["auto_purges"] += 1
                logger.warning(f"Purge automatique déclenchée: {memory_usage_mb:.1f}MB > {self.PURGE_THRESHOLD_MB}MB")
                
                for namespace in ["response", "search", "intent", "embedding"]:
                    await self._purge_namespace_lru(namespace, int(self.MAX_KEYS_PER_NAMESPACE * self.LRU_PURGE_RATIO))
                
                return True
            
            # Rejet si dépassement critique
            if memory_usage_mb > self.TOTAL_MEMORY_LIMIT_MB:
                logger.error(f"Cache Redis saturé: {memory_usage_mb:.1f}MB > {self.TOTAL_MEMORY_LIMIT_MB}MB")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur vérification mémoire Redis: {e}")
            return True
    
    async def _check_size_and_namespace_quota(self, namespace: str, serialized_data: bytes) -> bool:
        """Vérification taille et quota selon configuration"""
        data_size = len(serialized_data)
        
        # Vérification taille maximale configurée
        if data_size > self.MAX_VALUE_BYTES:
            self.protection_stats["oversized_rejects"] += 1
            logger.warning(f"Valeur rejetée (trop large): {data_size/1024:.1f}KB > {self.MAX_VALUE_BYTES/1024:.1f}KB")
            return False
        
        if not await self._check_memory_limits():
            return False
        
        # Vérification quota namespace configuré
        try:
            key_count = 0
            pattern = f"intelia_rag:{namespace}:*"
            
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                key_count += len(keys)
                scan_count += 1
                
                if scan_count > 10:
                    break
            
            if key_count >= self.MAX_KEYS_PER_NAMESPACE:
                self.protection_stats["namespace_limits_hit"] += 1
                logger.info(f"Quota namespace {namespace} atteint ({key_count}/{self.MAX_KEYS_PER_NAMESPACE}) - Purge LRU")
                
                purge_count = int(self.MAX_KEYS_PER_NAMESPACE * self.LRU_PURGE_RATIO)
                purged_count = await self._purge_namespace_lru(namespace, purge_count)
                self.protection_stats["lru_purges"] += purged_count
                
                if purged_count == 0:
                    logger.warning(f"Échec purge LRU namespace {namespace}")
                    return False
        
        except Exception as e:
            logger.warning(f"Erreur vérification quota namespace {namespace}: {e}")
            return True
        
        return True
    
    async def _purge_namespace_lru(self, namespace: str, target_purge_count: int) -> int:
        """Purge LRU avec ratio configuré"""
        try:
            keys_to_delete = []
            pattern = f"intelia_rag:{namespace}:*"
            
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=50)
                
                if keys:
                    pipeline = self.client.pipeline()
                    for key in keys:
                        pipeline.ttl(key)
                    ttls = await pipeline.execute()
                    
                    for key, ttl in zip(keys, ttls):
                        keys_to_delete.append((key, ttl if ttl >= 0 else 0))
                
                scan_count += 1
                if scan_count > 5 or len(keys_to_delete) >= target_purge_count * 2:
                    break
            
            if not keys_to_delete:
                return 0
            
            keys_to_delete.sort(key=lambda x: x[1])
            final_keys = [key for key, _ in keys_to_delete[:target_purge_count]]
            
            if final_keys:
                deleted_count = await self.client.delete(*final_keys)
                logger.info(f"Purge LRU namespace {namespace}: {deleted_count} clés supprimées")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Erreur purge LRU namespace {namespace}: {e}")
            return 0
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compression selon configuration"""
        if not self.ENABLE_COMPRESSION:
            return data
        
        try:
            compressed = zlib.compress(data, level=1)
            self.cache_stats["saved_operations"] += 1
            return compressed
        except:
            return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Décompression selon configuration"""
        if not self.ENABLE_COMPRESSION:
            return data
        
        try:
            return zlib.decompress(data)
        except:
            return data
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding avec cache sémantique optionnel"""
        if not self.enabled or not self.client:
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            # Essayer d'abord cache simple
            key = self._generate_key("embedding", text, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
                embedding = pickle.loads(decompressed)
                self.cache_stats["exact_hits"] += 1
                logger.debug(f"Cache HIT: embedding pour '{text[:30]}...'")
                return embedding
            
            # Essayer cache sémantique si activé
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("embedding", text, use_semantic=True)
                cached = await self.client.get(semantic_key)
                
                if cached:
                    decompressed = self._decompress_data(cached)
                    embedding = pickle.loads(decompressed)
                    self.cache_stats["semantic_hits"] += 1
                    logger.debug(f"Cache HIT (sémantique): embedding pour '{text[:30]}...'")
                    return embedding
            
            # Fallback keys si activé
            if self.ENABLE_FALLBACK_KEYS:
                fallback_keys = self._generate_fallback_keys(key, text)
                for fallback_key in fallback_keys:
                    cached = await self.client.get(fallback_key)
                    if cached:
                        decompressed = self._decompress_data(cached)
                        embedding = pickle.loads(decompressed)
                        self.cache_stats["exact_hits"] += 1
                        logger.debug(f"Cache HIT (fallback): embedding pour '{text[:30]}...'")
                        return embedding
            
            logger.debug(f"Cache MISS: embedding pour '{text[:30]}...'")
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache embedding: {e}")
        
        return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding avec stockage sémantique optionnel"""
        if not self.enabled or not self.client:
            return
        
        try:
            serialized = pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
            if not await self._check_size_and_namespace_quota("embedding", compressed):
                return
            
            # Stocker avec clé principale
            key = self._generate_key("embedding", text, use_semantic=False)
            await self.client.setex(
                key, 
                self.ttl_config["embeddings"], 
                compressed
            )
            
            # Stocker aussi avec clé sémantique si activé
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("embedding", text, use_semantic=True)
                if semantic_key != key:  # Éviter duplication
                    await self.client.setex(
                        semantic_key,
                        self.ttl_config["embeddings"],
                        compressed
                    )
            
            logger.debug(f"Cache SET: embedding pour '{text[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache embedding: {e}")
    
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse avec cache sémantique avancé"""
        if not self.enabled or not self.client:
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            # Essayer cache exact
            key = self._generate_key("response", cache_data, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                response = cached.decode('utf-8')
                self.cache_stats["exact_hits"] += 1
                logger.info(f"Cache HIT: '{query[:30]}...'")
                return response
            
            # Essayer cache sémantique si activé
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("response", query, use_semantic=True)
                cached = await self.client.get(semantic_key)
                
                if cached:
                    response = cached.decode('utf-8')
                    self.cache_stats["semantic_hits"] += 1
                    logger.info(f"Cache HIT (sémantique): '{query[:30]}...'")
                    return response
            
            logger.info(f"Cache MISS: '{query[:30]}...'")
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache réponse: {e}")
        
        return None
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """Met en cache une réponse avec support sémantique"""
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
            
            # Stocker avec cache principal
            key = self._generate_key("response", cache_data, use_semantic=False)
            await self.client.setex(
                key,
                self.ttl_config["responses"],
                response_bytes
            )
            
            # Stocker aussi avec cache sémantique si activé
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_fast(query)
                if keywords:
                    semantic_key = self._generate_key("response", query, use_semantic=True)
                    if semantic_key != key:  # Éviter duplication
                        await self.client.setex(
                            semantic_key,
                            self.ttl_config["responses"],
                            response_bytes
                        )
                        logger.debug(f"Cache SET (sémantique): '{query[:30]}...' -> keywords: {keywords}")
            
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
            vector_hash = hashlib.md5(str(query_vector[:5]).encode()).hexdigest()
            cache_data = {
                "vector_hash": vector_hash,
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            key = self._generate_key("search", cache_data, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
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
            vector_hash = hashlib.md5(str(query_vector[:5]).encode()).hexdigest()
            cache_data = {
                "vector_hash": vector_hash,
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            limited_results = [
                {
                    "content": r.get("content", "")[:self.MAX_SEARCH_CONTENT_LENGTH],
                    "metadata": {
                        "title": r.get("metadata", {}).get("title", ""),
                        "source": r.get("metadata", {}).get("source", "")
                    },
                    "score": round(r.get("score", 0.0), 3)
                }
                for r in results[:top_k]
            ]
            
            serialized = pickle.dumps(limited_results, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
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
        """Récupère un résultat d'analyse d'intention avec cache sémantique"""
        if not self.enabled or not self.client:
            return None
        
        try:
            # Cache simple
            key = self._generate_key("intent", query, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
                intent_result = pickle.loads(decompressed)
                logger.debug(f"Cache HIT: analyse d'intention pour '{query[:30]}...'")
                return intent_result
            
            # Cache sémantique si activé
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("intent", query, use_semantic=True)
                cached = await self.client.get(semantic_key)
                
                if cached:
                    decompressed = self._decompress_data(cached)
                    intent_result = pickle.loads(decompressed)
                    logger.debug(f"Cache HIT (sémantique): intention pour '{query[:30]}...'")
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
                data = {
                    "intent_type": getattr(intent_result, 'intent_type', 'unknown'),
                    "confidence": round(getattr(intent_result, 'confidence', 0.0), 3),
                    "detected_entities": getattr(intent_result, 'detected_entities', {}),
                    "expanded_query": getattr(intent_result, 'expanded_query', "")[:200]
                }
            else:
                data = intent_result
            
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
            if not await self._check_size_and_namespace_quota("intent", compressed):
                return
            
            # Stocker cache principal
            key = self._generate_key("intent", query, use_semantic=False)
            await self.client.setex(
                key,
                self.ttl_config["intent_results"],
                compressed
            )
            
            # Stocker cache sémantique si activé
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("intent", query, use_semantic=True)
                if semantic_key != key:
                    await self.client.setex(
                        semantic_key,
                        self.ttl_config["intent_results"],
                        compressed
                    )
            
            logger.debug(f"Cache SET: analyse d'intention '{query[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache intention: {e}")
    
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte pour le cache"""
        try:
            content_summary = []
            for doc in documents[:2]:
                summary = {
                    "source": doc.get("source", "")[:50],
                    "score_rounded": round(doc.get("score", 0.0), 1)
                }
                content_summary.append(summary)
            
            return hashlib.md5(
                json.dumps(content_summary, sort_keys=True, separators=(',', ':')).encode()
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
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, batch_keys = await self.client.scan(cursor, match=f"intelia_rag:{pattern}:*", count=100)
                keys.extend(batch_keys)
                scan_count += 1
                if scan_count > 10:
                    break
            
            if keys:
                batch_size = 50
                deleted_total = 0
                for i in range(0, len(keys), batch_size):
                    batch = keys[i:i + batch_size]
                    deleted = await self.client.delete(*batch)
                    deleted_total += deleted
                
                logger.info(f"Invalidé {deleted_total} clés pour pattern {pattern}")
                
        except Exception as e:
            logger.warning(f"Erreur invalidation pattern: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques complètes du cache"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = await self.client.info("memory")
            memory_usage_mb = await self._get_memory_usage_mb()
            total_keys = await self.client.dbsize()
            
            # Calculer les taux de hit
            total_requests = max(1, self.cache_stats["total_requests"])
            exact_hit_rate = self.cache_stats["exact_hits"] / total_requests
            semantic_hit_rate = self.cache_stats["semantic_hits"] / total_requests
            total_hit_rate = (self.cache_stats["exact_hits"] + self.cache_stats["semantic_hits"]) / total_requests
            
            return {
                "enabled": True,
                "approach": "configurable_via_environment_variables",
                "memory": {
                    "used_mb": round(memory_usage_mb, 2),
                    "used_human": info.get("used_memory_human", "N/A"),
                    "limit_mb": self.TOTAL_MEMORY_LIMIT_MB,
                    "usage_percent": round((memory_usage_mb / self.TOTAL_MEMORY_LIMIT_MB) * 100, 1)
                },
                "keys": {
                    "total": total_keys,
                    "max_per_namespace": self.MAX_KEYS_PER_NAMESPACE
                },
                "hit_statistics": {
                    "total_requests": total_requests,
                    "exact_hits": self.cache_stats["exact_hits"],
                    "semantic_hits": self.cache_stats["semantic_hits"],
                    "exact_hit_rate": round(exact_hit_rate, 3),
                    "semantic_hit_rate": round(semantic_hit_rate, 3),
                    "total_hit_rate": round(total_hit_rate, 3)
                },
                "configuration": {
                    "max_value_kb": round(self.MAX_VALUE_BYTES / 1024, 1),
                    "ttl_config_minutes": {k: round(v/60, 1) for k, v in self.ttl_config.items()},
                    "compression_enabled": self.ENABLE_COMPRESSION,
                    "semantic_cache_enabled": self.ENABLE_SEMANTIC_CACHE,
                    "fallback_keys_enabled": self.ENABLE_FALLBACK_KEYS,
                    "auto_purge_enabled": self.ENABLE_AUTO_PURGE,
                    "semantic_keywords_count": len(self.poultry_keywords)
                },
                "protection_stats": self.protection_stats,
                "performance": {
                    "saved_operations": self.cache_stats["saved_operations"],
                    "features_enabled": {
                        "compression": self.ENABLE_COMPRESSION,
                        "semantic_cache": self.ENABLE_SEMANTIC_CACHE,
                        "fallback_keys": self.ENABLE_FALLBACK_KEYS
                    }
                }
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
                target_key_count = int(self.MAX_KEYS_PER_NAMESPACE * self.LRU_PURGE_RATIO)
            
            purged = await self._purge_namespace_lru(namespace, target_key_count)
            
            final_count = 0
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=f"intelia_rag:{namespace}:*", count=100)
                final_count += len(keys)
                scan_count += 1
                if scan_count > 5:
                    final_count = f"~{final_count}+"
                    break
            
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
                stats = await self.get_cache_stats()
                if "hit_statistics" in stats:
                    hit_stats = stats["hit_statistics"]
                    memory_stats = stats.get("memory", {})
                    logger.info(f"Stats cache finales - Hit rate total: {hit_stats['total_hit_rate']:.1%}, "
                              f"Sémantique: {hit_stats['semantic_hit_rate']:.1%}, "
                              f"Mémoire: {memory_stats.get('used_mb', 0):.1f}MB")
                
                await self.client.close()
                logger.info("Connexion Redis fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture Redis: {e}")


# Classe wrapper pour intégration dans RAG Engine
class CachedOpenAIEmbedder:
    """Wrapper pour OpenAI Embedder avec cache Redis configuré"""
    
    def __init__(self, original_embedder, cache_manager: RAGCacheManager):
        self.original_embedder = original_embedder
        self.cache_manager = cache_manager
    
    async def embed_query(self, text: str) -> List[float]:
        """Embedding avec cache (simple et sémantique selon configuration)"""
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