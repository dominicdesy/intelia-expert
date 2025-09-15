# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Enhanced avec Cache Redis, Recherche Hybride et Guardrails
Version Production Intégrée pour Intelia Expert Aviculture
"""

import os
import asyncio
import logging
import time
import json
import re
import statistics
import hashlib
import pickle
import zlib
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import numpy as np
import httpx
import anyio

# Configuration logging
logger = logging.getLogger(__name__)

# === IMPORTS CONDITIONNELS ===
try:
    import weaviate
    weaviate_version = getattr(weaviate, '__version__', '4.0.0')
    if weaviate_version.startswith('4.'):
        try:
            import weaviate.classes as wvc
            WEAVIATE_V4 = True
        except ImportError:
            wvc = None
            WEAVIATE_V4 = False
    else:
        WEAVIATE_V4 = False
        wvc = None
    WEAVIATE_AVAILABLE = True
    logger.info(f"Weaviate {weaviate_version} détecté (V4: {WEAVIATE_V4})")
except ImportError as e:
    WEAVIATE_AVAILABLE = False
    WEAVIATE_V4 = False
    wvc = None
    weaviate = None
    logger.error(f"Weaviate non disponible: {e}")

try:
    from openai import AsyncOpenAI, OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    logger.error(f"OpenAI non disponible: {e}")

try:
    import redis.asyncio as redis
    import hiredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    logger.warning("Redis non disponible - cache désactivé")

try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    logger.warning("VoyageAI non disponible")

try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("SentenceTransformers non disponible")

try:
    from unidecode import unidecode
    UNIDECODE_AVAILABLE = True
except ImportError:
    UNIDECODE_AVAILABLE = False
    logger.warning("Unidecode non disponible")

try:
    from intent_processor import create_intent_processor, IntentType, IntentResult
    INTENT_PROCESSOR_AVAILABLE = True
except ImportError as e:
    INTENT_PROCESSOR_AVAILABLE = False
    logger.warning(f"Intent processor non disponible: {e}")
    
    class IntentType:
        METRIC_QUERY = "metric_query"
        OUT_OF_DOMAIN = "out_of_domain"
    
    class IntentResult:
        def __init__(self):
            self.intent_type = IntentType.METRIC_QUERY
            self.confidence = 0.8
            self.detected_entities = {}
            self.expanded_query = ""
            self.metadata = {}

# CORRECTION POINT 1 : Import des guardrails depuis le module dédié
try:
    from advanced_guardrails import create_response_guardrails, VerificationLevel, GuardrailResult
    GUARDRAILS_AVAILABLE = True
except ImportError as e:
    GUARDRAILS_AVAILABLE = False
    logger.warning(f"Advanced guardrails non disponible: {e}")
    
    # Fallback minimal
    class VerificationLevel:
        MINIMAL = "minimal"
        STANDARD = "standard"
        STRICT = "strict"
        CRITICAL = "critical"
    
    class GuardrailResult:
        def __init__(self):
            self.is_valid = True
            self.confidence = 0.8
            self.violations = []
            self.warnings = []
            self.evidence_support = 0.8
            self.hallucination_risk = 0.2
            self.correction_suggestions = []
            self.metadata = {}

# === CONFIGURATION ===
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Paramètres RAG optimisés
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "15"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.55"))
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "8"))
RAG_VERIFICATION_ENABLED = os.getenv("RAG_VERIFICATION_ENABLED", "true").lower() == "true"
RAG_VERIFICATION_SMART = os.getenv("RAG_VERIFICATION_SMART", "true").lower() == "true"
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "1500"))

# CORRECTION POINT 3 : Seuil OOD configurable et plus strict
OOD_MIN_SCORE = float(os.getenv("OOD_MIN_SCORE", "0.3"))

# Nouvelles configurations
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
HYBRID_SEARCH_ENABLED = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
GUARDRAILS_LEVEL = os.getenv("GUARDRAILS_LEVEL", "standard")
ENTITY_ENRICHMENT_ENABLED = os.getenv("ENTITY_ENRICHMENT_ENABLED", "true").lower() == "true"

# === UTILITAIRES ===
class MetricsCollector:
    """Collecteur de métriques in-process amélioré"""
    def __init__(self):
        self.counters = defaultdict(int)
        self.last_100_lat = []
        self.cache_stats = defaultdict(int)
        self.search_stats = defaultdict(int)

    def inc(self, key: str, n: int = 1): 
        self.counters[key] += n
    
    def observe_latency(self, sec: float):
        self.last_100_lat.append(sec)
        if len(self.last_100_lat) > 100: 
            self.last_100_lat = self.last_100_lat[-100:]

    def cache_hit(self, cache_type: str):
        self.cache_stats[f"{cache_type}_hits"] += 1
    
    def cache_miss(self, cache_type: str):
        self.cache_stats[f"{cache_type}_misses"] += 1

    def snapshot(self):
        p50 = statistics.median(self.last_100_lat) if self.last_100_lat else 0.0
        p95 = (sorted(self.last_100_lat)[int(0.95*len(self.last_100_lat))-1]
               if len(self.last_100_lat) >= 20 else p50)
        return {
            "counters": dict(self.counters),
            "cache_stats": dict(self.cache_stats),
            "search_stats": dict(self.search_stats),
            "p50_latency_sec": round(p50, 3),
            "p95_latency_sec": round(p95, 3),
            "samples": len(self.last_100_lat)
        }

METRICS = MetricsCollector()

# Détection de langue légère
_FRENCH_HINTS = {" le ", " la ", " les ", " des ", " un ", " une ", " et ", " ou ", " que ", " est ", " avec ", " pour ", " d'", " l'", " j'", " au ", " aux ", " du "}
_ENGLISH_HINTS = {" the ", " and ", " or ", " is ", " are ", " with ", " for ", " a ", " an ", " of "}

def detect_language_light(text: str, default: str = "fr") -> str:
    s = f" {text.lower()} "
    fr = sum(1 for w in _FRENCH_HINTS if w in s)
    en = sum(1 for w in _ENGLISH_HINTS if w in s)
    if fr > en + 1: return "fr"
    if en > fr + 1: return "en"
    if any(ch in s for ch in ["é", "è", "ê", "à", "ù", "ç"]): return "fr"
    return default

# === ENUMS ET DATACLASSES ===
class RAGSource(Enum):
    RAG_KNOWLEDGE = "rag_knowledge"
    RAG_VERIFIED = "rag_verified"
    OOD_FILTERED = "ood_filtered" 
    FALLBACK_NEEDED = "fallback_needed"
    ERROR = "error"

@dataclass
class RAGResult:
    source: RAGSource
    answer: Optional[str] = None
    confidence: float = 0.0
    context_docs: List[Dict] = None
    processing_time: float = 0.0
    metadata: Dict = None
    verification_status: Optional[Dict] = None
    intent_result: Optional[IntentResult] = None
    
    def __post_init__(self):
        if self.context_docs is None:
            self.context_docs = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Document:
    content: str
    metadata: Dict = None
    score: float = 0.0
    original_distance: Optional[float] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

# === GESTIONNAIRE DE CACHE REDIS ===
class RAGCacheManager:
    """Gestionnaire de cache Redis optimisé"""
    
    def __init__(self, redis_url: str = REDIS_URL, default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client = None
        self.enabled = REDIS_AVAILABLE and CACHE_ENABLED
        
        # CORRECTION POINT 4 : Protection OOM
        self.MAX_VALUE_BYTES = int(os.getenv("CACHE_MAX_VALUE_BYTES", "2000000"))  # 2MB
        self.MAX_KEYS_PER_NAMESPACE = int(os.getenv("CACHE_MAX_KEYS_PER_NS", "1000"))
        
        self.ttl_config = {
            "embeddings": 7200,
            "search_results": 1800,
            "responses": 900,
            "intent_results": 3600,
            "verification": 1800
        }
    
    async def initialize(self):
        if not self.enabled:
            logger.warning("Redis cache désactivé")
            return
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                socket_keepalive=True,
                health_check_interval=30
            )
            await self.client.ping()
            logger.info("Cache Redis initialisé")
        except Exception as e:
            logger.warning(f"Erreur connexion Redis: {e} - cache désactivé")
            self.enabled = False
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        if isinstance(data, str):
            content = data
        elif isinstance(data, dict):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"intelia_rag:{prefix}:{hash_obj.hexdigest()}"
    
    async def _check_size_and_purge(self, namespace: str, data_size: int) -> bool:
        """CORRECTION POINT 4 : Vérification taille et purge LRU"""
        if data_size > self.MAX_VALUE_BYTES:
            logger.warning(f"Valeur trop large pour cache: {data_size} bytes (max: {self.MAX_VALUE_BYTES})")
            return False
        
        # Purge LRU par namespace si nécessaire
        try:
            count = 0
            async for _ in self.client.scan_iter(match=f"intelia_rag:{namespace}:*"):
                count += 1
            
            if count >= self.MAX_KEYS_PER_NAMESPACE:
                logger.info(f"Purge LRU namespace {namespace}: {count} clés")
                await self._purge_namespace_lru(namespace, count // 2)  # Supprimer la moitié
        except Exception as e:
            logger.warning(f"Erreur purge LRU: {e}")
        
        return True
    
    async def _purge_namespace_lru(self, namespace: str, to_delete: int):
        """Purge LRU pour un namespace"""
        try:
            keys_with_ttl = []
            async for key in self.client.scan_iter(match=f"intelia_rag:{namespace}:*"):
                ttl = await self.client.ttl(key)
                keys_with_ttl.append((key, ttl))
            
            # Trier par TTL (les plus anciens d'abord)
            keys_with_ttl.sort(key=lambda x: x[1])
            keys_to_delete = [key for key, _ in keys_with_ttl[:to_delete]]
            
            if keys_to_delete:
                await self.client.delete(*keys_to_delete)
                logger.info(f"Supprimé {len(keys_to_delete)} clés du namespace {namespace}")
                
        except Exception as e:
            logger.warning(f"Erreur purge LRU détaillée: {e}")
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        if not self.enabled or not self.client:
            return None
        
        try:
            key = self._generate_key("embedding", text)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = zlib.decompress(cached)
                embedding = pickle.loads(decompressed)
                METRICS.cache_hit("embedding")
                return embedding
        except Exception as e:
            logger.warning(f"Erreur lecture cache embedding: {e}")
        
        METRICS.cache_miss("embedding")
        return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        if not self.enabled or not self.client:
            return
        
        try:
            serialized = pickle.dumps(embedding)
            compressed = zlib.compress(serialized)
            
            # CORRECTION POINT 4 : Vérification taille
            if not await self._check_size_and_purge("embedding", len(compressed)):
                return
            
            key = self._generate_key("embedding", text)
            await self.client.setex(key, self.ttl_config["embeddings"], compressed)
        except Exception as e:
            logger.warning(f"Erreur écriture cache embedding: {e}")
    
    async def get_response(self, query: str, context_hash: str, language: str = "fr") -> Optional[str]:
        if not self.enabled or not self.client:
            return None
        
        try:
            cache_data = {"query": query, "context_hash": context_hash, "language": language}
            key = self._generate_key("response", cache_data)
            cached = await self.client.get(key)
            
            if cached:
                response = cached.decode('utf-8')
                METRICS.cache_hit("response")
                return response
        except Exception as e:
            logger.warning(f"Erreur lecture cache réponse: {e}")
        
        METRICS.cache_miss("response")
        return None
    
    async def set_response(self, query: str, context_hash: str, response: str, language: str = "fr"):
        if not self.enabled or not self.client:
            return
        
        try:
            response_bytes = response.encode('utf-8')
            
            # CORRECTION POINT 4 : Vérification taille
            if not await self._check_size_and_purge("response", len(response_bytes)):
                return
            
            cache_data = {"query": query, "context_hash": context_hash, "language": language}
            key = self._generate_key("response", cache_data)
            await self.client.setex(key, self.ttl_config["responses"], response_bytes)
        except Exception as e:
            logger.warning(f"Erreur écriture cache réponse: {e}")
    
    def generate_context_hash(self, documents: List[Dict]) -> str:
        try:
            content_summary = []
            for doc in documents[:5]:
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
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques du cache"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = await self.client.info("memory")
            
            # Compter les clés par type
            type_counts = {}
            for cache_type in ["embeddings", "search_results", "responses", "intent_results", "verification"]:
                count = 0
                async for _ in self.client.scan_iter(match=f"intelia_rag:{cache_type}:*"):
                    count += 1
                type_counts[cache_type] = count
            
            return {
                "enabled": True,
                "memory_used": info.get("used_memory_human", "N/A"),
                "total_keys": await self.client.dbsize(),
                "type_counts": type_counts,
                "ttl_config": self.ttl_config,
                "max_value_bytes": self.MAX_VALUE_BYTES,
                "max_keys_per_namespace": self.MAX_KEYS_PER_NAMESPACE
            }
            
        except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {"enabled": True, "error": str(e)}
    
    async def cleanup(self):
        if self.client:
            try:
                await self.client.close()
                logger.info("Connexion Redis fermée")
            except Exception as e:
                logger.warning(f"Erreur fermeture Redis: {e}")

# === EMBEDDER AVEC CACHE ===
class OpenAIEmbedder:
    """Embedder OpenAI avec cache Redis intégré"""
    
    def __init__(self, client: AsyncOpenAI, cache_manager: RAGCacheManager = None, 
                 model: str = "text-embedding-3-small"):
        self.client = client
        self.cache_manager = cache_manager
        self.model = model
        
    async def embed_query(self, text: str) -> List[float]:
        # Vérifier le cache
        if self.cache_manager:
            cached_embedding = await self.cache_manager.get_embedding(text)
            if cached_embedding:
                return cached_embedding
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            
            # Mettre en cache
            if self.cache_manager:
                await self.cache_manager.set_embedding(text, embedding)
            
            return embedding
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            return []
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # Vérifier le cache pour chaque texte
        if self.cache_manager:
            for i, text in enumerate(texts):
                cached = await self.cache_manager.get_embedding(text)
                if cached:
                    results.append((i, cached))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
        
        # Générer les embeddings manquants
        if uncached_texts:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=uncached_texts,
                    encoding_format="float"
                )
                new_embeddings = [item.embedding for item in response.data]
                
                # Ajouter aux résultats et mettre en cache
                for idx, embedding in zip(uncached_indices, new_embeddings):
                    if self.cache_manager:
                        await self.cache_manager.set_embedding(texts[idx], embedding)
                    results.append((idx, embedding))
            except Exception as e:
                logger.error(f"Erreur embeddings batch: {e}")
                return []
        
        # Trier par index original
        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]

# === RETRIEVER HYBRIDE ===
def _to_v4_filter(where_dict):
    """Convertit dict where v3 vers Filter v4"""
    if not where_dict or not WEAVIATE_V4 or not wvc:
        return where_dict
    
    try:
        if "path" in where_dict:
            property_name = where_dict["path"][-1] if isinstance(where_dict["path"], list) else where_dict["path"]
            operator = where_dict.get("operator", "Equal")
            value = where_dict.get("valueText", where_dict.get("valueString", ""))
            
            if operator == "Like":
                return wvc.query.Filter.by_property(property_name).like(value)
            elif operator == "Equal":
                return wvc.query.Filter.by_property(property_name).equal(value)
            else:
                return wvc.query.Filter.by_property(property_name).equal(value)
        
        operator = where_dict.get("operator", "And").lower()
        operands = [_to_v4_filter(o) for o in where_dict.get("operands", [])]
        
        if operator == "and" and len(operands) >= 2:
            result = operands[0]
            for op in operands[1:]:
                result = result & op
            return result
        elif operator == "or" and len(operands) >= 2:
            result = operands[0]
            for op in operands[1:]:
                result = result | op
            return result
        else:
            return operands[0] if operands else None
            
    except Exception as e:
        logger.warning(f"Erreur conversion filter v4: {e}")
        return None

class HybridWeaviateRetriever:
    """Retriever hybride optimisé avec cache et fallbacks"""
    
    def __init__(self, client, collection_name: str = "InteliaKnowledge"):
        self.client = client
        self.collection_name = collection_name
        self.is_v4 = WEAVIATE_V4
        
        self.fusion_config = {
            "vector_weight": 0.7,
            "bm25_weight": 0.3,
            "rrf_k": 60,
            "min_score_threshold": 0.1,
            "diversity_threshold": 0.8
        }
        
    async def adaptive_search(self, query_vector: List[float], query_text: str,
                            top_k: int = 15, where_filter: Dict = None) -> List[Document]:
        """Recherche adaptative qui ajuste alpha selon la requête"""
        try:
            alpha = self._analyze_query_for_alpha(query_text)
            
            if HYBRID_SEARCH_ENABLED and self.is_v4:
                documents = await self._hybrid_search_v4(
                    query_vector, query_text, top_k, where_filter, alpha
                )
                METRICS.search_stats["hybrid_native"] += 1
            else:
                # Fallback recherche vectorielle + BM25 manuel
                documents = await self._hybrid_search_fallback(
                    query_vector, query_text, top_k, where_filter, alpha
                )
                METRICS.search_stats["hybrid_manual"] += 1
            
            # Retry sans age_band si nécessaire
            if not documents and where_filter and "age_band" in json.dumps(where_filter):
                logger.info("Retry recherche sans critère age_band")
                where_filter_no_age = self._remove_age_band_filter(where_filter)
                documents = await self._hybrid_search_v4(
                    query_vector, query_text, top_k, where_filter_no_age, alpha
                ) if self.is_v4 else await self._vector_search_fallback(
                    query_vector, top_k, where_filter_no_age
                )
                
                for doc in documents:
                    doc.metadata["age_band_fallback_used"] = True
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche adaptative: {e}")
            return await self._vector_search_fallback(query_vector, top_k, where_filter)
    
    def _analyze_query_for_alpha(self, query_text: str) -> float:
        """Analyse la requête pour déterminer l'alpha optimal"""
        query_lower = query_text.lower()
        
        # Requêtes spécifiques -> favoriser BM25
        if any(pattern in query_lower for pattern in [
            "ross", "cobb", "hubbard", "isa", "lohmann",
            "fcr", "pv", "gmd",
            "j0", "j7", "j21", "j35"
        ]):
            return 0.3
        
        # Requêtes numériques -> équilibré vers BM25
        if re.search(r'\d+\s*(g|kg|%|jour|j)', query_lower):
            return 0.4
        
        # Requêtes conceptuelles -> favoriser vectoriel
        if any(concept in query_lower for concept in [
            "comment", "pourquoi", "expliquer", "différence",
            "améliorer", "optimiser", "problème", "solution"
        ]):
            return 0.8
        
        return 0.7  # Par défaut
    
    async def _hybrid_search_v4(self, query_vector: List[float], query_text: str,
                               top_k: int, where_filter: Dict, alpha: float) -> List[Document]:
        """Recherche hybride native Weaviate v4"""
        try:
            def _sync_hybrid_search():
                collection = self.client.collections.get(self.collection_name)
                
                search_params = {
                    "query": query_text,
                    "vector": query_vector,
                    "alpha": alpha,
                    "limit": top_k,
                    "return_metadata": ["score"]
                }
                
                if where_filter:
                    v4_filter = _to_v4_filter(where_filter)
                    if v4_filter:
                        search_params["where"] = v4_filter
                
                return collection.query.hybrid(**search_params)
            
            response = await anyio.to_thread.run_sync(_sync_hybrid_search)
            
            documents = []
            for obj in response.objects:
                hybrid_score = float(getattr(obj.metadata, "score", 0.0))
                
                doc = Document(
                    content=obj.properties.get("content", ""),
                    metadata={
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "hybrid_used": True,
                        "alpha": alpha
                    },
                    score=hybrid_score
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche hybride v4: {e}")
            raise
    
    async def _hybrid_search_fallback(self, query_vector: List[float], query_text: str,
                                    top_k: int, where_filter: Dict, alpha: float) -> List[Document]:
        """Recherche hybride manuelle pour v3 ou fallback"""
        try:
            # Recherche vectorielle et BM25 en parallèle
            vector_docs = await self._vector_search_v3(query_vector, top_k * 2, where_filter)
            bm25_docs = await self._bm25_search_fallback(query_text, top_k, where_filter)
            
            # Fusion avec RRF
            fused_docs = self._fuse_results_rrf(vector_docs, bm25_docs, alpha, top_k)
            return fused_docs
            
        except Exception as e:
            logger.error(f"Erreur recherche hybride fallback: {e}")
            return await self._vector_search_fallback(query_vector, top_k, where_filter)
    
    def _fuse_results_rrf(self, vector_docs: List[Document], bm25_docs: List[Document],
                         alpha: float, top_k: int) -> List[Document]:
        """Fusion avec Reciprocal Rank Fusion"""
        all_docs = {}
        
        # Indexer documents vectoriels
        for i, doc in enumerate(vector_docs):
            content_key = doc.content[:100]
            if content_key not in all_docs:
                all_docs[content_key] = {
                    "doc": doc,
                    "vector_rank": i + 1,
                    "vector_score": doc.score,
                    "bm25_rank": None,
                    "bm25_score": 0.0
                }
        
        # Indexer documents BM25
        for i, doc in enumerate(bm25_docs):
            content_key = doc.content[:100]
            if content_key in all_docs:
                all_docs[content_key]["bm25_rank"] = i + 1
                all_docs[content_key]["bm25_score"] = doc.score
            else:
                all_docs[content_key] = {
                    "doc": doc,
                    "vector_rank": None,
                    "vector_score": 0.0,
                    "bm25_rank": i + 1,
                    "bm25_score": doc.score
                }
        
        # Calcul score RRF
        fused_docs = []
        for content_key, data in all_docs.items():
            doc = data["doc"]
            
            rrf_score = 0.0
            if data["vector_rank"]:
                rrf_score += alpha / (self.fusion_config["rrf_k"] + data["vector_rank"])
            if data["bm25_rank"]:
                rrf_score += (1 - alpha) / (self.fusion_config["rrf_k"] + data["bm25_rank"])
            
            if rrf_score >= self.fusion_config["min_score_threshold"]:
                doc.score = rrf_score * 10  # Normaliser
                doc.metadata.update({
                    "hybrid_used": True,
                    "fusion_method": "rrf",
                    "alpha": alpha,
                    "vector_rank": data["vector_rank"],
                    "bm25_rank": data["bm25_rank"]
                })
                fused_docs.append(doc)
        
        fused_docs.sort(key=lambda x: x.score, reverse=True)
        return fused_docs[:top_k]
    
    async def _vector_search_v3(self, query_vector: List[float], top_k: int, 
                              where_filter: Dict) -> List[Document]:
        """Recherche vectorielle Weaviate v3"""
        try:
            def _sync_search():
                query_builder = (
                    self.client.query
                    .get(self.collection_name, ["content", "title", "source", "geneticLine", "species", "phase", "age_band"])
                    .with_near_vector({"vector": query_vector})
                    .with_limit(top_k)
                    .with_additional(["score", "distance", "certainty"])
                )
                
                if where_filter:
                    query_builder = query_builder.with_where(where_filter)
                
                return query_builder.do()
            
            result = await anyio.to_thread.run_sync(_sync_search)
            
            documents = []
            objects = result.get("data", {}).get("Get", {}).get(self.collection_name, [])
            
            for obj in objects:
                additional = obj.get("_additional", {})
                score = additional.get("score", additional.get("certainty", 0.0))
                
                doc = Document(
                    content=obj.get("content", ""),
                    metadata={
                        "title": obj.get("title", ""),
                        "source": obj.get("source", ""),
                        "geneticLine": obj.get("geneticLine", ""),
                        "species": obj.get("species", ""),
                        "phase": obj.get("phase", ""),
                        "age_band": obj.get("age_band", ""),
                    },
                    score=float(score) if score else 0.0,
                    original_distance=additional.get("distance")
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle v3: {e}")
            return []
    
    async def _bm25_search_fallback(self, query_text: str, top_k: int, 
                                  where_filter: Dict) -> List[Document]:
        """Recherche BM25 de fallback"""
        if not self.is_v4:
            return []
        
        try:
            def _sync_bm25():
                collection = self.client.collections.get(self.collection_name)
                params = {
                    "query": query_text,
                    "limit": top_k,
                    "return_metadata": ["score"]
                }
                if where_filter:
                    v4_filter = _to_v4_filter(where_filter)
                    if v4_filter:
                        params["where"] = v4_filter
                return collection.query.bm25(**params)
            
            response = await anyio.to_thread.run_sync(_sync_bm25)
            
            documents = []
            for obj in response.objects:
                score = float(getattr(obj.metadata, "score", 0.0))
                
                doc = Document(
                    content=obj.properties.get("content", ""),
                    metadata={
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "bm25_used": True
                    },
                    score=score
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur BM25 fallback: {e}")
            return []
    
    async def _vector_search_fallback(self, query_vector: List[float], top_k: int, 
                                    where_filter: Dict) -> List[Document]:
        """Recherche vectorielle simple de fallback"""
        return await self._vector_search_v3(query_vector, top_k, where_filter)
    
    def _remove_age_band_filter(self, where_filter: Dict) -> Dict:
        """Retire le critère age_band du filtre"""
        if not where_filter:
            return None
        
        try:
            if "path" in where_filter:
                path = where_filter["path"]
                if (isinstance(path, list) and "age_band" in path) or path == "age_band":
                    return None
                return where_filter
            
            if "operands" in where_filter:
                new_operands = []
                for operand in where_filter["operands"]:
                    filtered_operand = self._remove_age_band_filter(operand)
                    if filtered_operand:
                        new_operands.append(filtered_operand)
                
                if not new_operands:
                    return None
                elif len(new_operands) == 1:
                    return new_operands[0]
                else:
                    return {
                        "operator": where_filter["operator"],
                        "operands": new_operands
                    }
            
            return where_filter
            
        except Exception as e:
            logger.warning(f"Erreur suppression age_band filter: {e}")
            return None

# === GÉNÉRATEUR DE RÉPONSES ENRICHI ===
class EnhancedResponseGenerator:
    """Générateur avec enrichissement d'entités et cache"""
    
    def __init__(self, client, cache_manager: RAGCacheManager = None):
        self.client = client
        self.cache_manager = cache_manager
        
        self.entity_contexts = {
            "line": {
                "ross": "lignée à croissance rapide, optimisée pour le rendement carcasse",
                "cobb": "lignée équilibrée performance/robustesse, bonne conversion alimentaire", 
                "hubbard": "lignée rustique, adaptée à l'élevage extensif et labels qualité",
                "isa": "lignée ponte, optimisée pour la production d'œufs",
                "lohmann": "lignée ponte, excellence en persistance de ponte"
            },
            "species": {
                "broiler": "poulet de chair, objectifs: poids vif, FCR, rendement carcasse",
                "layer": "poule pondeuse, objectifs: intensité de ponte, qualité œuf, persistance",
                "breeder": "reproducteur, objectifs: fertilité, éclosabilité, viabilité descendance"
            },
            "phase": {
                "starter": "phase démarrage (0-10j), croissance critique, thermorégulation",
                "grower": "phase croissance (11-24j), développement squelettique et musculaire", 
                "finisher": "phase finition (25j+), optimisation du poids final et FCR",
                "laying": "phase ponte, maintien de la production et qualité œuf",
                "breeding": "phase reproduction, optimisation fertilité et éclosabilité"
            }
        }
    
    async def generate_response(self, query: str, context_docs: List[Document], 
                              conversation_context: str = "", language: str = "fr",
                              intent_result=None) -> str:
        """Génère une réponse enrichie avec cache"""
        try:
            # Vérifier le cache
            if self.cache_manager:
                context_hash = self.cache_manager.generate_context_hash(
                    [self._doc_to_dict(doc) for doc in context_docs]
                )
                cached_response = await self.cache_manager.get_response(
                    query, context_hash, language
                )
                if cached_response:
                    METRICS.cache_hit("response")
                    return cached_response
                METRICS.cache_miss("response")
            
            # Construire enrichissement
            enrichment = self._build_entity_enrichment(intent_result) if intent_result else None
            
            # Générer le prompt enrichi
            system_prompt, user_prompt = self._build_enhanced_prompt(
                query, context_docs, enrichment, conversation_context, language
            )
            
            # Génération
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=900
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # Mettre en cache
            if self.cache_manager:
                context_hash = self.cache_manager.generate_context_hash(
                    [self._doc_to_dict(doc) for doc in context_docs]
                )
                await self.cache_manager.set_response(
                    query, context_hash, generated_response, language
                )
            
            return generated_response
            
        except Exception as e:
            logger.error(f"Erreur génération réponse enrichie: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."
    
    def _doc_to_dict(self, doc: Document) -> Dict:
        """Convertit Document en dict pour cache"""
        return {
            "content": doc.content,
            "title": doc.metadata.get("title", ""),
            "source": doc.metadata.get("source", ""),
            "score": doc.score
        }
    
    def _build_entity_enrichment(self, intent_result):
        """Construit l'enrichissement basé sur les entités"""
        try:
            entities = getattr(intent_result, 'detected_entities', {})
            entity_contexts = []
            
            if "line" in entities:
                line = entities["line"].lower()
                if line in self.entity_contexts["line"]:
                    entity_contexts.append(f"Lignée {entities['line']}: {self.entity_contexts['line'][line]}")
            
            if "species" in entities:
                species = entities["species"].lower()
                if species in self.entity_contexts["species"]:
                    entity_contexts.append(f"Type {entities['species']}: {self.entity_contexts['species'][species]}")
            
            if "phase" in entities:
                phase = entities["phase"].lower()
                if phase in self.entity_contexts["phase"]:
                    entity_contexts.append(f"Phase {entities['phase']}: {self.entity_contexts['phase'][phase]}")
            
            return "; ".join(entity_contexts) if entity_contexts else ""
            
        except Exception as e:
            logger.warning(f"Erreur construction enrichissement: {e}")
            return ""
    
    def _build_enhanced_prompt(self, query: str, context_docs: List[Document], 
                              enrichment: str, conversation_context: str, 
                              language: str) -> Tuple[str, str]:
        """Construit un prompt enrichi"""
        
        context_text = "\n\n".join([
            f"Document {i+1} ({doc.metadata.get('geneticLine', 'N/A')} - {doc.metadata.get('species', 'N/A')}):\n{doc.content[:1000]}"
            for i, doc in enumerate(context_docs[:5])
        ])
        
        system_prompt = f"""Tu es un expert en aviculture spécialisé dans l'accompagnement technique des éleveurs.

CONTEXTE MÉTIER DÉTECTÉ:
{enrichment or 'Contexte général aviculture'}

DIRECTIVES DE RÉPONSE:
1. Base ta réponse UNIQUEMENT sur les documents fournis
2. Intègre le contexte métier détecté dans ta réponse
3. Adapte le niveau technique au contexte (éleveur professionnel)
4. Fournis des valeurs chiffrées quand disponibles
5. Mentionne les spécificités de lignée/phase si pertinentes

RÈGLE LINGUISTIQUE: Réponds STRICTEMENT en {language}

Si les documents ne contiennent pas l'information demandée, dis-le clairement."""

        limited_context = conversation_context[:MAX_CONVERSATION_CONTEXT] if conversation_context else ""
        
        user_prompt = f"""CONTEXTE CONVERSATIONNEL:
{limited_context}

DOCUMENTS TECHNIQUES (avec métadonnées):
{context_text}

QUESTION ORIGINALE:
{query}

RÉPONSE TECHNIQUE (intégrant le contexte métier détecté):"""

        return system_prompt, user_prompt

# === DÉTECTEUR HORS DOMAINE ===
class EnhancedOODDetector:
    """Détecteur hors-domaine amélioré"""
    
    def __init__(self, blocked_terms_path: str = None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_keywords = {
            'poulet', 'poule', 'aviculture', 'élevage', 'volaille', 'poids', 'fcr',
            'aliment', 'vaccination', 'maladie', 'production', 'croissance', 'nutrition',
            'chicken', 'poultry', 'broiler', 'layer', 'feed', 'weight', 'growth',
            'température', 'ventilation', 'eau', 'water', 'temperature', 'incubation',
            'couvoir', 'hatchery', 'biosécurité', 'mortalité', 'mortality', 'performance',
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann', 'ponte', 'eggs', 'laying'
        }
        

    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes bloqués depuis le fichier configuré"""
        if path is None:
            # CORRECTION: Utiliser la variable d'environnement de Digital Ocean
            path = os.getenv("BLOCKED_TERMS_FILE", "/app/blocked_terms.json")
            if not os.path.exists(path):
                # Fallback pour développement local
                base_dir = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(base_dir, "blocked_terms.json")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                blocked_terms = json.load(f)
            
            logger.info(f"Loaded {len(blocked_terms)} blocked term categories from {path}")
            return blocked_terms
            
        except Exception as e:
            logger.warning(f"Erreur chargement blocked_terms depuis {path}: {e}")
            # Fallback avec termes de base en cas d'erreur
            return {
                "general": ["crypto", "bitcoin", "football", "film", "politique", "news"]
            }
    
    def calculate_ood_score(self, query: str, intent_result=None) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul score OOD avec normalisation - CORRECTION POINT 3: Seuil plus strict"""
        query_lower = (unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower())
        words = query_lower.split()
        
        # Boost entités métier
        entities_boost = 0.0
        if intent_result and hasattr(intent_result, 'detected_entities'):
            business_entities = ['line', 'species', 'age_days', 'weight', 'fcr', 'phase']
            detected_business = [e for e in business_entities if e in intent_result.detected_entities]
            if detected_business:
                entities_boost = 0.3 * len(detected_business)
        
        # Score vocabulaire domaine
        domain_words = [word for word in words if word in self.domain_keywords]
        vocab_score = (len(domain_words) / len(words) if words else 0.0) + entities_boost
        
        # Score termes bloqués
        blocked_score = 0.0
        for category, terms in self.blocked_terms.items():
            category_matches = sum(1 for term in terms if term in query_lower)
            if category_matches > 0:
                blocked_score = max(blocked_score, min(0.7, category_matches / max(2, len(words) // 2)))
        
        # Score final
        if vocab_score > 0.4:
            final_score = max(0.7, vocab_score - blocked_score * 0.3)
        elif entities_boost > 0:
            final_score = 0.6 + entities_boost - blocked_score * 0.2
        elif blocked_score > 0.6:
            final_score = 0.1
        else:
            final_score = (vocab_score * 0.8) - (blocked_score * 0.2)
        
        # CORRECTION POINT 3 : Seuil plus strict
        is_in_domain = final_score > OOD_MIN_SCORE
        
        score_details = {
            "vocab_score": vocab_score,
            "entities_boost": entities_boost,
            "blocked_score": blocked_score,
            "final_score": final_score,
            "threshold_used": OOD_MIN_SCORE
        }
        
        return is_in_domain, final_score, score_details

# === MÉMOIRE CONVERSATIONNELLE ===
class ConversationMemory:
    """Mémoire conversationnelle simple"""
    
    def __init__(self, client):
        self.client = client
        self.memory_store = {}
        self.max_exchanges = 5
    
    async def get_contextual_memory(self, tenant_id: str, current_query: str) -> str:
        """Récupère le contexte conversationnel"""
        if tenant_id not in self.memory_store:
            return ""
        
        history = self.memory_store[tenant_id]
        if not history:
            return ""
        
        # Retourner simplement le dernier échange
        try:
            last_exchange = history[-1]
            return f"Dernier échange - Q: {last_exchange['question'][:100]}... R: {last_exchange['answer'][:200]}..."
        except Exception as e:
            logger.warning(f"Erreur mémoire: {e}")
            return ""
    
    def add_exchange(self, tenant_id: str, question: str, answer: str):
        """Ajoute un échange"""
        if tenant_id not in self.memory_store:
            self.memory_store[tenant_id] = []
        
        self.memory_store[tenant_id].append({
            "question": question,
            "answer": answer,
            "timestamp": time.time()
        })
        
        if len(self.memory_store[tenant_id]) > self.max_exchanges:
            self.memory_store[tenant_id] = self.memory_store[tenant_id][-self.max_exchanges:]

# === UTILITAIRES ===
def build_where_filter(intent_result) -> Dict:
    """Construire where filter par entités"""
    if not intent_result or not hasattr(intent_result, 'detected_entities'):
        return None
    
    entities = intent_result.detected_entities
    where_conditions = []
    
    if "line" in entities:
        where_conditions.append({
            "path": ["geneticLine"],
            "operator": "Like",
            "valueText": f"*{entities['line']}*"
        })
    
    if "species" in entities:
        where_conditions.append({
            "path": ["species"],
            "operator": "Like", 
            "valueText": f"*{entities['species']}*"
        })
    
    if "phase" in entities:
        where_conditions.append({
            "path": ["phase"],
            "operator": "Like",
            "valueText": f"*{entities['phase']}*"
        })
    
    if "age_days" in entities:
        age_days = entities["age_days"]
        if isinstance(age_days, (int, float)):
            if age_days <= 7:
                age_band = "0-7j"
            elif age_days <= 21:
                age_band = "8-21j"
            elif age_days <= 35:
                age_band = "22-35j"
            else:
                age_band = "36j+"
            
            where_conditions.append({
                "path": ["age_band"],
                "operator": "Equal",
                "valueText": age_band
            })
    
    if not where_conditions:
        return None
    
    if len(where_conditions) == 1:
        return where_conditions[0]
    else:
        return {
            "operator": "And",
            "operands": where_conditions
        }

# === RAG ENGINE PRINCIPAL ===
class InteliaRAGEngine:
    """RAG Engine principal avec toutes les optimisations intégrées"""
    
    def __init__(self, openai_client: AsyncOpenAI = None):
        self.openai_client = openai_client or self._build_openai_client()
        
        # Composants principaux
        self.cache_manager = None
        self.embedder = None
        self.retriever = None
        self.generator = None
        self.verifier = None
        self.memory = None
        self.intent_processor = None
        self.ood_detector = None
        self.guardrails = None
        self.weaviate_client = None
        
        # État
        self.is_initialized = False
        self.degraded_mode = False
        
        # Stats optimisation
        self.optimization_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "hybrid_searches": 0,
            "guardrail_violations": 0,
            "entity_enrichments": 0
        }
    
    def _build_openai_client(self) -> AsyncOpenAI:
        """Construit le client OpenAI"""
        try:
            http_client = httpx.AsyncClient(timeout=30.0)
            return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            return AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def initialize(self):
        """Initialisation complète"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation RAG Engine Enhanced")
        
        if not OPENAI_AVAILABLE or not WEAVIATE_AVAILABLE:
            self.degraded_mode = True
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return
        
        try:
            # 1. Cache Redis
            if CACHE_ENABLED and REDIS_AVAILABLE:
                self.cache_manager = RAGCacheManager()
                await self.cache_manager.initialize()
            
            # 2. Connexion Weaviate
            await self._connect_weaviate()
            
            # 3. Composants de base
            self.embedder = OpenAIEmbedder(self.openai_client, self.cache_manager)
            self.memory = ConversationMemory(self.openai_client)
            self.ood_detector = EnhancedOODDetector()
            
            # 4. Retriever hybride
            if self.weaviate_client:
                self.retriever = HybridWeaviateRetriever(self.weaviate_client)
            
            # 5. Générateur enrichi
            if ENTITY_ENRICHMENT_ENABLED:
                self.generator = EnhancedResponseGenerator(self.openai_client, self.cache_manager)
            
            # 6. CORRECTION POINT 1 : Guardrails depuis le module dédié
            if GUARDRAILS_AVAILABLE:
                self.guardrails = create_response_guardrails(self.openai_client, GUARDRAILS_LEVEL)
            
            # 7. Intent processor
            if INTENT_PROCESSOR_AVAILABLE:
                self.intent_processor = create_intent_processor()
            
            self.is_initialized = True
            logger.info("RAG Engine Enhanced initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur initialisation: {e}")
            self.degraded_mode = True
            self.is_initialized = True
    
    async def _connect_weaviate(self):
        """Connexion Weaviate"""
        if WEAVIATE_V4:
            try:
                if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                    self.weaviate_client = weaviate.WeaviateClient(
                        url=WEAVIATE_URL,
                        auth_client_secret=weaviate.AuthApiKey(WEAVIATE_API_KEY),
                        additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                    )
                else:
                    additional_headers = {"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                    
                    if WEAVIATE_API_KEY:
                        self.weaviate_client = weaviate.WeaviateClient(
                            url=WEAVIATE_URL,
                            auth_client_secret=weaviate.AuthApiKey(WEAVIATE_API_KEY),
                            additional_headers=additional_headers
                        )
                    else:
                        self.weaviate_client = weaviate.WeaviateClient(
                            url=WEAVIATE_URL,
                            additional_headers=additional_headers
                        )
                
                def _test_connection():
                    self.weaviate_client.connect()
                    return self.weaviate_client.is_ready()
                
                is_ready = await anyio.to_thread.run_sync(_test_connection)
                
                if not is_ready:
                    raise Exception("Weaviate not ready")
                    
            except Exception as e:
                logger.error(f"Erreur connexion Weaviate v4: {e}")
                raise
        else:
            # Weaviate v3
            if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
                self.weaviate_client = weaviate.Client(
                    url=WEAVIATE_URL,
                    auth_client_secret=auth_config,
                    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            else:
                self.weaviate_client = weaviate.Client(
                    url=WEAVIATE_URL,
                    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            
            def _check_connection():
                return self.weaviate_client.is_ready()
            
            is_ready = await anyio.to_thread.run_sync(_check_connection)
            
            if not is_ready:
                raise Exception("Weaviate not ready")
    
    async def process_query(self, query: str, language: str = "fr", tenant_id: str = "") -> RAGResult:
        """Traitement de requête avec toutes les optimisations"""
        if not RAG_ENABLED:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "rag_disabled"})
        
        if not self.is_initialized:
            await self.initialize()
        
        if self.degraded_mode:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "degraded_mode"})
        
        start_time = time.time()
        METRICS.inc("requests_total")
        
        try:
            # Auto-détection langue
            if not language:
                language = detect_language_light(query, default="fr")
            
            # Intent processing
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
            
            # OOD detection avec seuil corrigé
            if self.ood_detector:
                is_in_domain, domain_score, score_details = self.ood_detector.calculate_ood_score(query, intent_result)
                
                if not is_in_domain:
                    METRICS.inc("requests_ood")
                    METRICS.observe_latency(time.time() - start_time)
                    return RAGResult(
                        source=RAGSource.OOD_FILTERED,
                        answer="Désolé, cette question sort du domaine avicole. Pose-moi une question sur l'aviculture.",
                        confidence=1.0 - domain_score,
                        processing_time=time.time() - start_time,
                        metadata={
                            "domain_score": domain_score,
                            "score_details": score_details,
                            "optimization_stats": self.optimization_stats.copy()
                        },
                        intent_result=intent_result
                    )
            
            # Contexte conversationnel
            conversation_context = ""
            if tenant_id and self.memory:
                try:
                    conversation_context = await self.memory.get_contextual_memory(tenant_id, query)
                except Exception as e:
                    logger.warning(f"Erreur mémoire conversationnelle: {e}")
            
            # Embedding de la requête
            search_query = query
            if intent_result and hasattr(intent_result, 'expanded_query') and intent_result.expanded_query:
                search_query = intent_result.expanded_query
            
            query_vector = await self.embedder.embed_query(search_query)
            if not query_vector:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.ERROR,
                    metadata={"error": "embedding_failed", "optimization_stats": self.optimization_stats.copy()}
                )
            
            # Construire where filter
            where_filter = build_where_filter(intent_result)
            
            # Recherche hybride
            documents = []
            if self.retriever:
                try:
                    documents = await self.retriever.adaptive_search(
                        query_vector, search_query, RAG_SIMILARITY_TOP_K, where_filter
                    )
                    if any(doc.metadata.get("hybrid_used") for doc in documents):
                        self.optimization_stats["hybrid_searches"] += 1
                except Exception as e:
                    logger.error(f"Erreur recherche hybride: {e}")
            
            if not documents:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={
                        "reason": "no_documents_found", 
                        "where_filter_used": where_filter is not None,
                        "optimization_stats": self.optimization_stats.copy()
                    }
                )
            
            # Filtrage par confiance avec seuil dynamique
            effective_threshold = RAG_CONFIDENCE_THRESHOLD
            if documents:
                top1 = max(d.score for d in documents)
                if top1 >= 0.85:
                    effective_threshold = max(RAG_CONFIDENCE_THRESHOLD, 0.60)
                elif any(d.metadata.get("bm25_used") for d in documents) and top1 < 0.70:
                    effective_threshold = min(effective_threshold, 0.50)
            
            filtered_docs = [doc for doc in documents if doc.score >= effective_threshold]
            
            if not filtered_docs:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={
                        "reason": "low_confidence_documents", 
                        "min_score": min(doc.score for doc in documents) if documents else 0,
                        "effective_threshold": effective_threshold,
                        "optimization_stats": self.optimization_stats.copy()
                    }
                )
            
            # Génération de réponse enrichie
            response_text = ""
            if self.generator and ENTITY_ENRICHMENT_ENABLED:
                try:
                    response_text = await self.generator.generate_response(
                        query, filtered_docs, conversation_context, language, intent_result
                    )
                    self.optimization_stats["entity_enrichments"] += 1
                except Exception as e:
                    logger.error(f"Erreur génération enrichie: {e}")
            
            # Fallback génération basique
            if not response_text:
                try:
                    context_text = "\n\n".join([
                        f"Document {i+1}:\n{doc.content[:1000]}"
                        for i, doc in enumerate(filtered_docs[:5])
                    ])
                    
                    system_prompt = f"""Tu es un expert en aviculture. Réponds UNIQUEMENT basé sur les documents fournis.
RÈGLE: Réponds strictement en {language}."""
                    
                    user_prompt = f"""DOCUMENTS:\n{context_text}\n\nQUESTION:\n{query}\n\nRÉPONSE:"""
                    
                    response = await self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=800
                    )
                    
                    response_text = response.choices[0].message.content.strip()
                    
                except Exception as e:
                    logger.error(f"Erreur génération fallback: {e}")
                    response_text = "Désolé, je ne peux pas générer une réponse."
            
            if not response_text or "ne peux pas" in response_text.lower():
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={
                        "reason": "generation_failed",
                        "optimization_stats": self.optimization_stats.copy()
                    }
                )
            
            # Vérification avec guardrails
            verification_result = None
            if self.guardrails:
                try:
                    # Vérification smart: skip si haute confiance
                    do_verify = True
                    if RAG_VERIFICATION_SMART:
                        top_scores = [d.score for d in filtered_docs[:3]]
                        if top_scores and top_scores[0] >= 0.80 and (len(top_scores) <= 1 or np.std(top_scores) <= 0.05):
                            do_verify = False
                    
                    if do_verify:
                        verification_result = await self.guardrails.verify_response(
                            query, response_text, filtered_docs, intent_result
                        )
                        
                        if not verification_result.is_valid:
                            self.optimization_stats["guardrail_violations"] += 1
                            logger.warning(f"Violation guardrails: {verification_result.violations}")
                            
                            # Si violation critique, retourner fallback
                            if verification_result.confidence < 0.3:
                                METRICS.observe_latency(time.time() - start_time)
                                return RAGResult(
                                    source=RAGSource.FALLBACK_NEEDED,
                                    metadata={
                                        "reason": "guardrail_violation",
                                        "violations": verification_result.violations,
                                        "optimization_stats": self.optimization_stats.copy()
                                    }
                                )
                    
                except Exception as e:
                    logger.warning(f"Erreur guardrails: {e}")
            
            # Calcul de confiance finale
            confidence = self._calculate_confidence(filtered_docs, verification_result)
            
            # Source du résultat
            result_source = RAGSource.RAG_KNOWLEDGE
            if verification_result and verification_result.is_valid:
                result_source = RAGSource.RAG_VERIFIED
                confidence = min(confidence * 1.1, 0.95)
            
            # Construire context_docs pour le résultat
            context_docs = []
            for doc in filtered_docs:
                context_docs.append({
                    "title": doc.metadata.get("title", ""),
                    "content": doc.content,
                    "score": doc.score,
                    "source": doc.metadata.get("source", ""),
                    "genetic_line": doc.metadata.get("geneticLine", ""),
                    "species": doc.metadata.get("species", ""),
                    "phase": doc.metadata.get("phase", ""),
                    "age_band": doc.metadata.get("age_band", ""),
                    "hybrid_used": doc.metadata.get("hybrid_used", False),
                    "bm25_used": doc.metadata.get("bm25_used", False),
                    "search_type": getattr(doc, 'search_type', 'unknown')
                })
            
            # Métadonnées complètes
            metadata = {
                "approach": "enhanced_rag_integrated_complete",
                "optimizations_enabled": {
                    "redis_cache": self.cache_manager.enabled if self.cache_manager else False,
                    "hybrid_search": HYBRID_SEARCH_ENABLED,
                    "entity_enrichment": ENTITY_ENRICHMENT_ENABLED,
                    "advanced_guardrails": True
                },
                "weaviate_version": weaviate_version,
                "weaviate_v4": WEAVIATE_V4,
                "documents_found": len(documents) if documents else 0,
                "documents_used": len(filtered_docs),
                "effective_threshold": effective_threshold,
                "query_expanded": search_query != query,
                "conversation_context_used": bool(conversation_context),
                "where_filter_applied": where_filter is not None,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "verification_smart": RAG_VERIFICATION_SMART,
                "language_target": language,
                "language_detected": detect_language_light(query),
                "optimization_stats": self.optimization_stats.copy()
            }
            
            if intent_result:
                metadata.update({
                    "intent_type": getattr(intent_result, 'intent_type', 'unknown'),
                    "detected_entities": getattr(intent_result, 'detected_entities', {})
                })
            
            # Sauvegarde mémoire
            if tenant_id and self.memory:
                try:
                    self.memory.add_exchange(tenant_id, query, response_text)
                except Exception as e:
                    logger.warning(f"Erreur sauvegarde mémoire: {e}")
            
            METRICS.observe_latency(time.time() - start_time)
            
            return RAGResult(
                source=result_source,
                answer=response_text,
                confidence=confidence,
                context_docs=context_docs,
                processing_time=time.time() - start_time,
                metadata=metadata,
                verification_status=verification_result.__dict__ if verification_result else None,
                intent_result=intent_result
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement query: {e}")
            METRICS.observe_latency(time.time() - start_time)
            return RAGResult(
                source=RAGSource.ERROR,
                confidence=0.0,
                processing_time=time.time() - start_time,
                metadata={
                    "error": str(e),
                    "optimization_stats": self.optimization_stats.copy()
                },
                intent_result=intent_result if 'intent_result' in locals() else None
            )
    
    def _calculate_confidence(self, documents: List[Document], verification_result=None) -> float:
        """Calcul de confiance optimisé"""
        if not documents:
            return 0.0
        
        scores = [doc.score for doc in documents if doc.score > 0]
        if not scores:
            return 0.5
        
        avg_score = sum(scores) / len(scores)
        coherence_factor = min(1.2, 1 + (len(scores) - 1) * 0.05)
        
        if len(scores) > 1:
            score_std = np.std(scores)
            distribution_factor = max(0.9, 1 - score_std * 0.5)
        else:
            distribution_factor = 1.0
        
        verification_factor = 1.0
        if verification_result and verification_result.is_valid:
            verification_factor = 1.1
        
        final_confidence = avg_score * coherence_factor * distribution_factor * verification_factor
        return min(0.95, max(0.1, final_confidence))
    
    def get_status(self) -> Dict:
        """Status complet du système"""
        try:
            weaviate_connected = False
            if self.weaviate_client:
                try:
                    def _check():
                        return self.weaviate_client.is_ready()
                    weaviate_connected = _check()
                except:
                    weaviate_connected = False
            
            status = {
                "rag_enabled": RAG_ENABLED,
                "initialized": self.is_initialized,
                "degraded_mode": self.degraded_mode,
                "approach": "enhanced_rag_integrated_complete",
                "optimizations": {
                    "cache_enabled": self.cache_manager.enabled if self.cache_manager else False,
                    "hybrid_search_enabled": HYBRID_SEARCH_ENABLED,
                    "entity_enrichment_enabled": ENTITY_ENRICHMENT_ENABLED,
                    "guardrails_level": GUARDRAILS_LEVEL,
                    "verification_smart": RAG_VERIFICATION_SMART
                },
                "components": {
                    "openai_available": OPENAI_AVAILABLE,
                    "weaviate_available": WEAVIATE_AVAILABLE,
                    "weaviate_version": weaviate_version if WEAVIATE_AVAILABLE else "N/A",
                    "weaviate_v4": WEAVIATE_V4,
                    "weaviate_connected": weaviate_connected,
                    "redis_available": REDIS_AVAILABLE,
                    "voyage_available": VOYAGE_AVAILABLE,
                    "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
                    "intent_processor_available": INTENT_PROCESSOR_AVAILABLE,
                    "guardrails_available": GUARDRAILS_AVAILABLE
                },
                "configuration": {
                    "similarity_top_k": RAG_SIMILARITY_TOP_K,
                    "confidence_threshold": RAG_CONFIDENCE_THRESHOLD,
                    "rerank_top_k": RAG_RERANK_TOP_K,
                    "max_conversation_context": MAX_CONVERSATION_CONTEXT,
                    "ood_min_score": OOD_MIN_SCORE,
                    "redis_url": REDIS_URL,
                    "weaviate_url": WEAVIATE_URL
                },
                "optimization_stats": self.optimization_stats.copy(),
                "metrics": METRICS.snapshot()
            }
            
            # Ajout stats cache si disponible
            if self.cache_manager:
                try:
                    # Utiliser l'event loop existant ou en créer un nouveau
                    try:
                        loop = asyncio.get_running_loop()
                        # Si on est déjà dans un event loop async, créer une tâche
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                lambda: asyncio.run(self.cache_manager.get_cache_stats())
                            )
                            cache_stats = future.result(timeout=5.0)
                    except RuntimeError:
                        # Si pas d'event loop actif, utiliser run_until_complete
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            cache_stats = loop.run_until_complete(self.cache_manager.get_cache_stats())
                        finally:
                            loop.close()
                    
                    status["cache_stats"] = cache_stats
                except Exception as e:
                    logger.warning(f"Erreur récupération stats cache: {e}")
                    status["cache_stats"] = {"error": "unavailable"}
            
            return status
            
        except Exception as e:
            logger.error(f"Erreur get_status: {e}")
            return {
                "error": str(e),
                "rag_enabled": RAG_ENABLED,
                "initialized": False,
                "degraded_mode": True
            }
    
    async def cleanup(self):
        """Nettoyage complet des ressources"""
        try:
            if self.cache_manager:
                await self.cache_manager.cleanup()
            
            if self.weaviate_client and hasattr(self.weaviate_client, 'close'):
                self.weaviate_client.close()
            
            if self.memory:
                self.memory.memory_store.clear()
            
            if hasattr(self.openai_client, 'http_client'):
                await self.openai_client.http_client.aclose()
            
            logger.info("Enhanced RAG Engine nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")


# === FONCTIONS UTILITAIRES POUR COMPATIBILITÉ ===
async def create_rag_engine(openai_client: AsyncOpenAI = None) -> InteliaRAGEngine:
    """Factory pour créer le RAG engine enhanced"""
    try:
        engine = InteliaRAGEngine(openai_client)
        await engine.initialize()
        return engine
    except Exception as e:
        logger.error(f"Erreur création RAG engine: {e}")
        engine = InteliaRAGEngine(openai_client)
        engine.degraded_mode = True
        engine.is_initialized = True
        return engine

async def process_question_with_rag(
    rag_engine: InteliaRAGEngine, 
    question: str, 
    language: str = "fr", 
    tenant_id: str = ""
) -> RAGResult:
    """Interface compatible pour traitement des questions"""
    try:
        return await rag_engine.process_query(question, language, tenant_id)
    except Exception as e:
        logger.error(f"Erreur process_question_with_rag: {e}")
        return RAGResult(
            source=RAGSource.ERROR,
            confidence=0.0,
            metadata={"error": str(e)}
        )