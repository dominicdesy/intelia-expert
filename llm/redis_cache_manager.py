# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis optimisé pour performance
Version corrigée pour éliminer les goulots d'étranglement et overhead
CORRECTIONS APPLIQUÉES: Désactivation cache sémantique + compression + optimisations
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
    """Gestionnaire de cache Redis optimisé pour performance maximale"""
    
    def __init__(self, redis_url: str = None, default_ttl: int = None):
        # Configuration Redis
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = default_ttl or int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
        self.client = None
        self.enabled = REDIS_AVAILABLE and os.getenv("CACHE_ENABLED", "true").lower() == "true"
        
        # === LIMITES MÉMOIRE OPTIMISÉES ===
        self.MAX_VALUE_BYTES = int(os.getenv("CACHE_MAX_VALUE_BYTES", "200000"))  # Réduit de 500KB à 200KB
        self.MAX_KEYS_PER_NAMESPACE = int(os.getenv("CACHE_MAX_KEYS_PER_NS", "2000"))  # Réduit de 5000 à 2000
        self.TOTAL_MEMORY_LIMIT_MB = int(os.getenv("CACHE_TOTAL_MEMORY_LIMIT_MB", "150"))  # Réduit de 200MB à 150MB
        
        # === SEUILS D'ALERTE OPTIMISÉS ===
        self.WARNING_THRESHOLD_MB = int(os.getenv("CACHE_WARNING_THRESHOLD_MB", "120"))  # 120 MB
        self.PURGE_THRESHOLD_MB = int(os.getenv("CACHE_PURGE_THRESHOLD_MB", "130"))  # 130 MB
        self.STATS_LOG_INTERVAL = int(os.getenv("CACHE_STATS_LOG_INTERVAL", "600"))  # 10 min au lieu de 5
        
        # === TTL OPTIMISÉS POUR PERFORMANCE ===
        self.ttl_config = {
            "embeddings": int(os.getenv("CACHE_TTL_EMBEDDINGS", "3600")),      # 1h au lieu de 24h
            "search_results": int(os.getenv("CACHE_TTL_SEARCHES", "1800")),    # 30min au lieu de 2h
            "responses": int(os.getenv("CACHE_TTL_RESPONSES", "1800")),        # 30min au lieu de 1h
            "intent_results": int(os.getenv("CACHE_TTL_INTENTS", "3600")),     # 1h au lieu de 2h
            "verification": int(os.getenv("CACHE_TTL_VERIFICATION", "1800")),  # 30min
            "normalized": int(os.getenv("CACHE_TTL_NORMALIZED", "3600"))       # 1h au lieu de 3h
        }
        
        # === OPTIMISATIONS DÉSACTIVÉES POUR PERFORMANCE ===
        # CORRECTION: Désactiver les fonctionnalités lourdes par défaut
        self.ENABLE_COMPRESSION = os.getenv("CACHE_ENABLE_COMPRESSION", "false").lower() == "true"  # Désactivé
        self.ENABLE_SEMANTIC_CACHE = os.getenv("CACHE_ENABLE_SEMANTIC", "false").lower() == "true"  # Désactivé
        self.ENABLE_FALLBACK_KEYS = os.getenv("CACHE_ENABLE_FALLBACK", "false").lower() == "true"  # Désactivé
        self.MAX_SEARCH_CONTENT_LENGTH = int(os.getenv("CACHE_MAX_SEARCH_CONTENT", "300"))  # Réduit de 500 à 300
        
        # === PURGE CONFIGURABLES ===
        self.LRU_PURGE_RATIO = float(os.getenv("CACHE_LRU_PURGE_RATIO", "0.4"))  # Purge 40% en LRU (plus agressif)
        self.ENABLE_AUTO_PURGE = os.getenv("CACHE_ENABLE_AUTO_PURGE", "true").lower() == "true"
        
        # Vocabulaire avicole simplifié (seulement si sémantique activé)
        self.poultry_keywords = {
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann',  # Lignées
            'fcr', 'poids', 'weight', 'gain', 'croissance',  # Métriques principales
            'poulet', 'chicken', 'poule', 'broiler', 'layer',  # Types
            'starter', 'grower', 'finisher', 'ponte'  # Phases principales
        } if self.ENABLE_SEMANTIC_CACHE else set()
        
        # Mots vides réduits (seulement si fallback activé)
        self.stopwords = {
            'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'que', 'est', 'pour',
            'the', 'a', 'and', 'or', 'is', 'are', 'for', 'with', 'in', 'on'
        } if self.ENABLE_FALLBACK_KEYS else set()
        
        # Statistiques simplifiées
        self.protection_stats = {
            "oversized_rejects": 0,
            "lru_purges": 0,
            "namespace_limits_hit": 0,
            "memory_warnings": 0,
            "auto_purges": 0
        }
        
        self.cache_stats = {
            "exact_hits": 0,
            "total_requests": 0,
            "saved_operations": 0  # Remplace compression_savings_bytes
        }
        
        # Dernière vérification mémoire
        self.last_memory_check = 0
        self.last_stats_log = 0
    
    async def initialize(self):
        """Initialise la connexion Redis avec configuration optimisée"""
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
                decode_responses=False,  # Pour gérer pickle
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=60  # Réduit la fréquence de health check
            )
            
            # Test de connexion
            await self.client.ping()
            
            # Log de la configuration optimisée
            logger.info("Cache Redis initialisé avec configuration OPTIMISÉE:")
            logger.info(f"  - Limite valeur: {self.MAX_VALUE_BYTES/1024:.0f} KB (optimisé)")
            logger.info(f"  - Limite clés/namespace: {self.MAX_KEYS_PER_NAMESPACE} (optimisé)")
            logger.info(f"  - Limite mémoire totale: {self.TOTAL_MEMORY_LIMIT_MB} MB (optimisé)")
            logger.info(f"  - TTL embeddings: {self.ttl_config['embeddings']}s ({self.ttl_config['embeddings']//60}min)")
            logger.info(f"  - TTL réponses: {self.ttl_config['responses']}s ({self.ttl_config['responses']//60}min)")
            logger.info(f"  - Compression: {self.ENABLE_COMPRESSION} (DÉSACTIVÉ pour performance)")
            logger.info(f"  - Cache sémantique: {self.ENABLE_SEMANTIC_CACHE} (DÉSACTIVÉ pour performance)")
            logger.info(f"  - Clés fallback: {self.ENABLE_FALLBACK_KEYS} (DÉSACTIVÉ pour performance)")
            logger.info(f"  - Auto-purge: {self.ENABLE_AUTO_PURGE}")
            
        except Exception as e:
            logger.warning(f"Erreur connexion Redis: {e} - cache désactivé")
            self.enabled = False
    
    def _normalize_text(self, text: str) -> str:
        """Normalisation TEXT LÉGÈRE pour maximiser cache hits sans overhead"""
        if not text:
            return ""
        
        # Normalisation minimale seulement
        normalized = text.lower().strip()
        
        # Suppression espaces multiples et ponctuation finale uniquement
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[?!.]+$', '', normalized)
        
        # Normalisation spécifique aviculture (uniquement les patterns les plus fréquents)
        normalized = re.sub(r'\bjours?\b', 'j', normalized)  # "jours" -> "j"
        normalized = re.sub(r'\bross\s*308\b', 'ross308', normalized)
        normalized = re.sub(r'\bcobb\s*500\b', 'cobb500', normalized)
        
        return normalized
    
    def _generate_key(self, prefix: str, data: Any, use_semantic: bool = False) -> str:
        """Génère une clé de cache SIMPLE et RAPIDE"""
        if isinstance(data, str):
            # CORRECTION: Cache sémantique désactivé par défaut pour performance
            if use_semantic and self.ENABLE_SEMANTIC_CACHE and prefix in ["response", "intent"]:
                # Cache sémantique (seulement si explicitement activé)
                keywords = self._extract_semantic_keywords_fast(data)
                if keywords:
                    semantic_signature = '|'.join(sorted(keywords))
                    hash_obj = hashlib.md5(semantic_signature.encode('utf-8'))
                    return f"intelia_rag:{prefix}:semantic:{hash_obj.hexdigest()}"
            
            # Cache normalisé standard (rapide)
            content = self._normalize_text(data)
        elif isinstance(data, dict):
            # Normaliser les dictionnaires contenant des requêtes
            normalized_dict = data.copy()
            if "query" in normalized_dict:
                normalized_dict["query"] = self._normalize_text(normalized_dict["query"])
            content = json.dumps(normalized_dict, sort_keys=True, separators=(',', ':'))  # Compact JSON
        else:
            content = str(data)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"intelia_rag:{prefix}:simple:{hash_obj.hexdigest()}"
    
    def _extract_semantic_keywords_fast(self, text: str) -> Set[str]:
        """Extraction RAPIDE de keywords sémantiques (seulement si activé)"""
        if not self.ENABLE_SEMANTIC_CACHE or not self.poultry_keywords:
            return set()
        
        words = set(re.findall(r'\b\w+\b', text.lower()))
        
        # Identifier uniquement les mots-clés avicoles principaux
        poultry_words = words & self.poultry_keywords
        
        # Ajouter les nombres (âges, poids, etc.) - pattern simple
        numbers = set(re.findall(r'\b\d+\b', text))
        
        return poultry_words | numbers
    
    def _generate_fallback_keys(self, primary_key: str, original_data: Any) -> List[str]:
        """Génère des clés de fallback SEULEMENT si activé"""
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
            return used_memory / (1024 * 1024)  # Convertir en MB
        except:
            return 0.0
    
    async def _check_memory_limits(self) -> bool:
        """Vérification mémoire OPTIMISÉE - moins fréquente"""
        now = time.time()
        
        # Vérifier seulement toutes les 60 secondes pour réduire overhead
        if now - self.last_memory_check < 60:
            return True
        
        self.last_memory_check = now
        
        try:
            memory_usage_mb = await self._get_memory_usage_mb()
            
            # Log périodique des stats (moins fréquent)
            if now - self.last_stats_log > self.STATS_LOG_INTERVAL:
                self.last_stats_log = now
                logger.info(f"Cache Redis: {memory_usage_mb:.1f}MB utilisés / {self.TOTAL_MEMORY_LIMIT_MB}MB limite")
            
            # Alerte si approche de la limite
            if memory_usage_mb > self.WARNING_THRESHOLD_MB:
                self.protection_stats["memory_warnings"] += 1
                logger.warning(f"Cache Redis proche de la limite: {memory_usage_mb:.1f}MB / {self.TOTAL_MEMORY_LIMIT_MB}MB")
            
            # Purge forcée si dépassement
            if memory_usage_mb > self.PURGE_THRESHOLD_MB and self.ENABLE_AUTO_PURGE:
                self.protection_stats["auto_purges"] += 1
                logger.warning(f"Purge automatique déclenchée: {memory_usage_mb:.1f}MB > {self.PURGE_THRESHOLD_MB}MB")
                
                # Purger tous les namespaces de manière plus agressive
                for namespace in ["response", "search", "intent", "embedding"]:
                    await self._purge_namespace_lru(namespace, int(self.MAX_KEYS_PER_NAMESPACE * self.LRU_PURGE_RATIO))
                
                return True
            
            # Rejeter si dépassement critique
            if memory_usage_mb > self.TOTAL_MEMORY_LIMIT_MB:
                logger.error(f"Cache Redis saturé: {memory_usage_mb:.1f}MB > {self.TOTAL_MEMORY_LIMIT_MB}MB - Rejet de la nouvelle entrée")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur vérification mémoire Redis: {e}")
            return True  # fail-open
    
    async def _check_size_and_namespace_quota(self, namespace: str, serialized_data: bytes) -> bool:
        """Vérification taille + quota OPTIMISÉE"""
        data_size = len(serialized_data)
        
        # 1. Vérification taille maximale par valeur
        if data_size > self.MAX_VALUE_BYTES:
            self.protection_stats["oversized_rejects"] += 1
            logger.warning(f"Valeur rejetée (trop large): {data_size/1024:.1f}KB > {self.MAX_VALUE_BYTES/1024:.1f}KB")
            return False
        
        # 2. Vérification limites mémoire globales (moins fréquente)
        if not await self._check_memory_limits():
            return False
        
        # 3. Vérification quota namespace SIMPLIFIÉE
        try:
            # Compter les clés de manière approximative pour éviter scan complet
            key_count = 0
            pattern = f"intelia_rag:{namespace}:*"
            
            # Utiliser SCAN avec LIMIT pour éviter de bloquer Redis
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                key_count += len(keys)
                scan_count += 1
                
                # Limiter le scan pour éviter overhead
                if scan_count > 10:  # Max 1000 clés scannées
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
            return True  # fail-open
        
        return True
    
    async def _purge_namespace_lru(self, namespace: str, target_purge_count: int) -> int:
        """Purge LRU OPTIMISÉE pour un namespace"""
        try:
            keys_to_delete = []
            pattern = f"intelia_rag:{namespace}:*"
            
            # Utiliser SCAN avec COUNT pour éviter de bloquer Redis
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=50)
                
                # Pour chaque batch de clés, récupérer les TTL
                if keys:
                    pipeline = self.client.pipeline()
                    for key in keys:
                        pipeline.ttl(key)
                    ttls = await pipeline.execute()
                    
                    # Ajouter les clés avec leur TTL
                    for key, ttl in zip(keys, ttls):
                        keys_to_delete.append((key, ttl if ttl >= 0 else 0))
                
                scan_count += 1
                # Limiter le scan pour éviter overhead
                if scan_count > 5 or len(keys_to_delete) >= target_purge_count * 2:
                    break
            
            if not keys_to_delete:
                return 0
            
            # Trier par TTL restant (les plus anciens = TTL le plus faible)
            keys_to_delete.sort(key=lambda x: x[1])
            
            # Prendre seulement les clés à supprimer
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
        """Compression SEULEMENT si activée (désactivée par défaut)"""
        if not self.ENABLE_COMPRESSION:
            return data
        
        try:
            compressed = zlib.compress(data, level=1)  # Compression rapide si activée
            savings = len(data) - len(compressed)
            self.cache_stats["saved_operations"] += 1
            return compressed
        except:
            return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Décompression SEULEMENT si activée"""
        if not self.ENABLE_COMPRESSION:
            return data
        
        try:
            return zlib.decompress(data)
        except:
            return data
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding depuis le cache OPTIMISÉ"""
        if not self.enabled or not self.client:
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            # CORRECTION: Utiliser seulement la clé simple et rapide
            key = self._generate_key("embedding", text, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
                embedding = pickle.loads(decompressed)
                self.cache_stats["exact_hits"] += 1
                logger.debug(f"Cache HIT: embedding pour '{text[:30]}...'")
                return embedding
            
            # PAS de fallback keys pour éviter overhead - seulement si explicitement activé
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
        """Met en cache un embedding OPTIMISÉ"""
        if not self.enabled or not self.client:
            return
        
        try:
            serialized = pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
            if not await self._check_size_and_namespace_quota("embedding", compressed):
                return
            
            # Stocker seulement avec clé principale (pas de fallback pour éviter overhead)
            key = self._generate_key("embedding", text, use_semantic=False)
            await self.client.setex(
                key, 
                self.ttl_config["embeddings"], 
                compressed
            )
            
            logger.debug(f"Cache SET: embedding pour '{text[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache embedding: {e}")
    
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse générée depuis le cache OPTIMISÉ"""
        if not self.enabled or not self.client:
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            # CORRECTION: Essayer d'abord cache simple et rapide
            key = self._generate_key("response", cache_data, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                response = cached.decode('utf-8')
                self.cache_stats["exact_hits"] += 1
                logger.info(f"Cache HIT: '{query[:30]}...'")
                return response
            
            # Cache sémantique SEULEMENT si activé
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("response", query, use_semantic=True)
                cached = await self.client.get(semantic_key)
                
                if cached:
                    response = cached.decode('utf-8')
                    self.cache_stats["exact_hits"] += 1
                    logger.info(f"Cache HIT (sémantique): '{query[:30]}...'")
                    return response
            
            logger.info(f"Cache MISS: '{query[:30]}...'")
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache réponse: {e}")
        
        return None
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """Met en cache une réponse générée OPTIMISÉ"""
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
            
            # Cache sémantique SEULEMENT si activé
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_fast(query)
                if keywords:
                    semantic_key = self._generate_key("response", query, use_semantic=True)
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
        """Récupère des résultats de recherche depuis le cache OPTIMISÉ"""
        if not self.enabled or not self.client:
            return None
        
        try:
            # Hash simplifié pour performance
            vector_hash = hashlib.md5(str(query_vector[:5]).encode()).hexdigest()  # Seulement 5 premiers éléments
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
        """Met en cache des résultats de recherche OPTIMISÉ"""
        if not self.enabled or not self.client:
            return
        
        try:
            # Hash simplifié pour performance
            vector_hash = hashlib.md5(str(query_vector[:5]).encode()).hexdigest()
            cache_data = {
                "vector_hash": vector_hash,
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            # Limiter la taille de manière plus agressive
            limited_results = [
                {
                    "content": r.get("content", "")[:self.MAX_SEARCH_CONTENT_LENGTH],
                    "metadata": {
                        "title": r.get("metadata", {}).get("title", ""),
                        "source": r.get("metadata", {}).get("source", "")
                    },
                    "score": round(r.get("score", 0.0), 3)  # Arrondir les scores
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
        """Récupère un résultat d'analyse d'intention depuis le cache OPTIMISÉ"""
        if not self.enabled or not self.client:
            return None
        
        try:
            # Cache simple pour intentions
            key = self._generate_key("intent", query, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
                intent_result = pickle.loads(decompressed)
                logger.debug(f"Cache HIT: analyse d'intention pour '{query[:30]}...'")
                return intent_result
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache intention: {e}")
        
        return None
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention OPTIMISÉ"""
        if not self.enabled or not self.client:
            return
        
        try:
            if hasattr(intent_result, '__dict__'):
                # Simplifier les données stockées
                data = {
                    "intent_type": getattr(intent_result, 'intent_type', 'unknown'),
                    "confidence": round(getattr(intent_result, 'confidence', 0.0), 3),
                    "detected_entities": getattr(intent_result, 'detected_entities', {}),
                    "expanded_query": getattr(intent_result, 'expanded_query', "")[:200]  # Limiter taille
                }
            else:
                data = intent_result
            
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
            if not await self._check_size_and_namespace_quota("intent", compressed):
                return
            
            key = self._generate_key("intent", query, use_semantic=False)
            await self.client.setex(
                key,
                self.ttl_config["intent_results"],
                compressed
            )
            logger.debug(f"Cache SET: analyse d'intention '{query[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache intention: {e}")
    
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte OPTIMISÉ pour le cache"""
        try:
            # Hash encore plus simple pour maximiser les hits
            content_summary = []
            for doc in documents[:2]:  # Seulement 2 docs au lieu de 3
                summary = {
                    "source": doc.get("source", "")[:50],  # Limiter la taille
                    "score_rounded": round(doc.get("score", 0.0), 1)  # Arrondir à 1 décimale
                }
                content_summary.append(summary)
            
            return hashlib.md5(
                json.dumps(content_summary, sort_keys=True, separators=(',', ':')).encode()
            ).hexdigest()
            
        except Exception as e:
            logger.warning(f"Erreur génération hash contexte: {e}")
            return "fallback_hash"
    
    async def invalidate_pattern(self, pattern: str):
        """Invalide les clés correspondant à un pattern OPTIMISÉ"""
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
                if scan_count > 10:  # Limiter les scans
                    break
            
            if keys:
                # Supprimer par batches pour éviter de bloquer Redis
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
        """Récupère les statistiques du cache OPTIMISÉES"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = await self.client.info("memory")
            memory_usage_mb = await self._get_memory_usage_mb()
            
            # Compter les clés de manière approximative pour éviter overhead
            total_keys = await self.client.dbsize()
            
            # Stats simplifiées
            type_counts = {}
            for cache_type in ["embedding", "search", "response", "intent"]:
                # Approximation rapide au lieu de scan complet
                type_counts[cache_type] = "approx"
            
            # Calculer le taux de hit simplifié
            total_requests = max(1, self.cache_stats["total_requests"])
            hit_rate = self.cache_stats["exact_hits"] / total_requests
            
            return {
                "enabled": True,
                "approach": "optimized_for_performance",
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
                    "hit_rate": round(hit_rate, 3)
                },
                "configuration": {
                    "max_value_kb": round(self.MAX_VALUE_BYTES / 1024, 1),
                    "ttl_config_minutes": {k: round(v/60, 1) for k, v in self.ttl_config.items()},
                    "compression_enabled": self.ENABLE_COMPRESSION,
                    "semantic_cache_enabled": self.ENABLE_SEMANTIC_CACHE,
                    "fallback_keys_enabled": self.ENABLE_FALLBACK_KEYS,
                    "auto_purge_enabled": self.ENABLE_AUTO_PURGE,
                    "performance_optimized": True
                },
                "protection_stats": self.protection_stats,
                "performance": {
                    "saved_operations": self.cache_stats["saved_operations"],
                    "optimizations_disabled": {
                        "compression": not self.ENABLE_COMPRESSION,
                        "semantic_cache": not self.ENABLE_SEMANTIC_CACHE,
                        "fallback_keys": not self.ENABLE_FALLBACK_KEYS
                    }
                }
            }
            
        except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def force_namespace_cleanup(self, namespace: str, target_key_count: int = None) -> Dict[str, int]:
        """Force le nettoyage d'un namespace OPTIMISÉ"""
        if not self.enabled or not self.client:
            return {"error": "cache_disabled"}
        
        try:
            if target_key_count is None:
                target_key_count = int(self.MAX_KEYS_PER_NAMESPACE * self.LRU_PURGE_RATIO)
            
            purged = await self._purge_namespace_lru(namespace, target_key_count)
            
            # Compter approximativement les clés restantes
            final_count = 0
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=f"intelia_rag:{namespace}:*", count=100)
                final_count += len(keys)
                scan_count += 1
                if scan_count > 5:  # Limiter pour éviter overhead
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
        """Nettoie les ressources Redis OPTIMISÉ"""
        if self.client:
            try:
                # Afficher les stats finales simplifiées
                stats = await self.get_cache_stats()
                if "hit_statistics" in stats:
                    hit_stats = stats["hit_statistics"]
                    memory_stats = stats.get("memory", {})
                    logger.info(f"Stats cache finales - Hit rate: {hit_stats['hit_rate']:.1%}, "
                              f"Mémoire: {memory_stats.get('used_mb', 0):.1f}MB, "
                              f"Performance optimisée: {stats['performance']['optimizations_disabled']}")
                
                await self.client.close()
                logger.info("Connexion Redis fermée (optimisée)")
            except Exception as e:
                logger.warning(f"Erreur fermeture Redis: {e}")


# Classe wrapper pour intégration facile dans RAG Engine (optimisée)
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
        
        # Mettre en cache de manière optimisée
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