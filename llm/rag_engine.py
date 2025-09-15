# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Enhanced avec Cache Redis externe optimisé
Version Production Intégrée pour Intelia Expert Aviculture
Version corrigée pour Weaviate 4.16.9 - Septembre 2025
CORRECTIONS APPLIQUÉES: Optimisations cache sémantique + intent processor + diagnostics enrichis
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
            import weaviate.classes.query as wvc_query
            WEAVIATE_V4 = True
        except ImportError:
            wvc = None
            wvc_query = None
            WEAVIATE_V4 = False
    else:
        WEAVIATE_V4 = False
        wvc = None
        wvc_query = None
    WEAVIATE_AVAILABLE = True
    logger.info(f"Weaviate {weaviate_version} détecté (V4: {WEAVIATE_V4})")
except ImportError as e:
    WEAVIATE_AVAILABLE = False
    WEAVIATE_V4 = False
    wvc = None
    wvc_query = None
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
            self.confidence_breakdown = {}

try:
    from advanced_guardrails import create_response_guardrails, VerificationLevel, GuardrailResult
    GUARDRAILS_AVAILABLE = True
except ImportError as e:
    GUARDRAILS_AVAILABLE = False
    logger.warning(f"Advanced guardrails non disponible: {e}")
    
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

# IMPORT DU CACHE EXTERNE OPTIMISÉ
try:
    from redis_cache_manager import RAGCacheManager
    EXTERNAL_CACHE_AVAILABLE = True
    logger.info("Cache Redis externe importé avec succès")
except ImportError as e:
    EXTERNAL_CACHE_AVAILABLE = False
    logger.warning(f"Cache Redis externe non disponible: {e}")
    
    class RAGCacheManager:
        def __init__(self, *args, **kwargs):
            self.enabled = False
            self.ENABLE_SEMANTIC_CACHE = False
        
        async def initialize(self):
            pass
        
        async def get_embedding(self, text: str):
            return None
        
        async def set_embedding(self, text: str, embedding: List[float]):
            pass
        
        async def get_response(self, query: str, context_hash: str, language: str = "fr"):
            return None
        
        async def set_response(self, query: str, context_hash: str, response: str, language: str = "fr"):
            pass
        
        def generate_context_hash(self, documents: List[Dict]) -> str:
            return "fallback_hash"
        
        async def get_cache_stats(self):
            return {"enabled": False, "semantic_enhancements": {}}
        
        async def debug_semantic_extraction(self, query: str):
            return {"extracted_keywords": [], "cache_keys": {}}
        
        def _normalize_text(self, text: str) -> str:
            return text.lower()
        
        async def cleanup(self):
            pass

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

# MODIFICATION: Contexte conversationnel augmenté (3→8 tours)
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "2400"))  # 8 tours * 300 chars en moyenne

# MODIFICATION: Seuil OOD dynamique basé sur l'intent
OOD_MIN_SCORE = float(os.getenv("OOD_MIN_SCORE", "0.3"))
OOD_STRICT_SCORE = float(os.getenv("OOD_STRICT_SCORE", "0.45"))  # Seuil durci pour vocabulaire générique

# Nouvelles configurations
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
HYBRID_SEARCH_ENABLED = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
GUARDRAILS_LEVEL = os.getenv("GUARDRAILS_LEVEL", "standard")
ENTITY_ENRICHMENT_ENABLED = os.getenv("ENTITY_ENRICHMENT_ENABLED", "true").lower() == "true"

# Configuration diagnostics
ENABLE_API_DIAGNOSTICS = os.getenv("ENABLE_API_DIAGNOSTICS", "true").lower() == "true"

# NOUVEAU: Configuration détection de langue optimisée
LANG_DETECTION_MIN_LENGTH = int(os.getenv("LANG_DETECTION_MIN_LENGTH", "20"))

# === UTILITAIRES ===
class MetricsCollector:
    """Collecteur de métriques enrichi avec statistiques intent et cache sémantique"""
    def __init__(self):
        self.counters = defaultdict(int)
        self.last_100_lat = []
        self.cache_stats = defaultdict(int)
        self.search_stats = defaultdict(int)
        # NOUVEAU: Stats intent et cache sémantique
        self.intent_stats = defaultdict(int)
        self.semantic_cache_stats = defaultdict(int)
        self.ood_stats = defaultdict(int)
        self.api_corrections = defaultdict(int)

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
    
    # NOUVEAU: Métriques intent
    def intent_detected(self, intent_type: str, confidence: float):
        self.intent_stats[f"intent_{intent_type}"] += 1
        self.intent_stats["total_intents"] += 1
        self.intent_stats["avg_confidence"] = (
            (self.intent_stats.get("avg_confidence", 0.0) * (self.intent_stats["total_intents"] - 1) + confidence) 
            / self.intent_stats["total_intents"]
        )
    
    # NOUVEAU: Métriques cache sémantique
    def semantic_cache_hit(self, cache_type: str):
        self.semantic_cache_stats[f"semantic_{cache_type}_hits"] += 1
    
    def semantic_fallback_used(self):
        self.semantic_cache_stats["fallback_hits"] += 1
    
    # NOUVEAU: Métriques OOD
    def ood_filtered(self, score: float, reason: str):
        self.ood_stats[f"ood_{reason}"] += 1
        self.ood_stats["ood_total"] += 1
        self.ood_stats["avg_ood_score"] = (
            (self.ood_stats.get("avg_ood_score", 0.0) * (self.ood_stats["ood_total"] - 1) + score) 
            / self.ood_stats["ood_total"]
        )
    
    # NOUVEAU: Corrections API
    def api_correction_applied(self, correction_type: str):
        self.api_corrections[correction_type] += 1

    def snapshot(self):
        p50 = statistics.median(self.last_100_lat) if self.last_100_lat else 0.0
        p95 = (sorted(self.last_100_lat)[int(0.95*len(self.last_100_lat))-1]
               if len(self.last_100_lat) >= 20 else p50)
        return {
            "counters": dict(self.counters),
            "cache_stats": dict(self.cache_stats),
            "search_stats": dict(self.search_stats),
            "intent_stats": dict(self.intent_stats),
            "semantic_cache_stats": dict(self.semantic_cache_stats),
            "ood_stats": dict(self.ood_stats),
            "api_corrections": dict(self.api_corrections),
            "p50_latency_sec": round(p50, 3),
            "p95_latency_sec": round(p95, 3),
            "samples": len(self.last_100_lat)
        }

METRICS = MetricsCollector()

# MODIFICATION: Détection de langue optimisée pour requêtes courtes
_FRENCH_HINTS = {" le ", " la ", " les ", " des ", " un ", " une ", " et ", " ou ", " que ", " est ", " avec ", " pour ", " d'", " l'", " j'", " au ", " aux ", " du "}
_ENGLISH_HINTS = {" the ", " and ", " or ", " is ", " are ", " with ", " for ", " a ", " an ", " of "}
_FRENCH_CHARS = set("éèêàùç")

def detect_language_enhanced(text: str, default: str = "fr") -> str:
    """Détection de langue optimisée pour requêtes courtes et techniques"""
    if len(text) < LANG_DETECTION_MIN_LENGTH:
        # Pour requêtes courtes: détection basique
        s = f" {text.lower()} "
        
        # Vérifier caractères spéciaux français
        if any(ch in text.lower() for ch in _FRENCH_CHARS):
            return "fr"
        
        # Compter mots indicateurs
        fr = sum(1 for w in _FRENCH_HINTS if w in s)
        en = sum(1 for w in _ENGLISH_HINTS if w in s)
        
        if fr > en + 1: return "fr"
        if en > fr + 1: return "en"
        
        # Patterns techniques français
        if re.search(r'\d+\s*[gj]', text.lower()):  # "35j", "2500g"
            return "fr"
        
        return default
    else:
        # Pour requêtes longues: utiliser langdetect si disponible
        try:
            import langdetect
            detected = langdetect.detect(text)
            return detected if detected in ["fr", "en"] else default
        except:
            # Fallback vers méthode basique
            s = f" {text.lower()} "
            fr = sum(1 for w in _FRENCH_HINTS if w in s)
            en = sum(1 for w in _ENGLISH_HINTS if w in s)
            if fr > en + 1: return "fr"
            if en > fr + 1: return "en"
            if any(ch in s for ch in _FRENCH_CHARS): return "fr"
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
    explain_score: Optional[Dict] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get(self, key: str, default=None):
        """Méthode get() pour compatibilité avec les guardrails"""
        if key == "content":
            return self.content
        elif key == "metadata":
            return self.metadata
        elif key == "score":
            return self.score
        elif key == "explain_score":
            return self.explain_score
        elif key in self.metadata:
            return self.metadata[key]
        else:
            return getattr(self, key, default)

# === EMBEDDER AVEC CACHE EXTERNE ===
class OpenAIEmbedder:
    """Embedder OpenAI avec cache Redis externe optimisé"""
    
    def __init__(self, client: AsyncOpenAI, cache_manager: RAGCacheManager = None, 
                 model: str = "text-embedding-3-small"):
        self.client = client
        self.cache_manager = cache_manager
        self.model = model
        
    async def embed_query(self, text: str) -> List[float]:
        # Vérifier le cache externe
        if self.cache_manager and self.cache_manager.enabled:
            cached_embedding = await self.cache_manager.get_embedding(text)
            if cached_embedding:
                METRICS.cache_hit("embedding")
                return cached_embedding
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            
            # Mettre en cache externe
            if self.cache_manager and self.cache_manager.enabled:
                await self.cache_manager.set_embedding(text, embedding)
            
            METRICS.cache_miss("embedding")
            return embedding
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            return []
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # Vérifier le cache pour chaque texte
        if self.cache_manager and self.cache_manager.enabled:
            for i, text in enumerate(texts):
                cached = await self.cache_manager.get_embedding(text)
                if cached:
                    results.append((i, cached))
                    METRICS.cache_hit("embedding")
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
                    if self.cache_manager and self.cache_manager.enabled:
                        await self.cache_manager.set_embedding(texts[idx], embedding)
                    results.append((idx, embedding))
                    METRICS.cache_miss("embedding")
            except Exception as e:
                logger.error(f"Erreur embeddings batch: {e}")
                return []
        
        # Trier par index original
        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]

# === RETRIEVER HYBRIDE CORRIGÉ ===
def _to_v4_filter(where_dict):
    """Convertit dict where v3 vers Filter v4 - Version corrigée pour Weaviate 4.16.9"""
    if not where_dict or not WEAVIATE_V4 or not wvc:
        return None
    
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
        operands = [op for op in operands if op is not None]
        
        if not operands:
            return None
            
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
    """Retriever hybride optimisé avec cache et fallbacks - Version corrigée pour Weaviate 4.16.9"""
    
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
        
        # État des API pour diagnostic - AMÉLIORÉ avec runtime flags
        self.api_capabilities = {
            "hybrid_with_vector": None,
            "hybrid_with_where": None,
            "near_vector_format": None,
            "diagnosed": False,
            "runtime_corrections": 0,
            "last_diagnostic_time": 0.0,
            "api_stability": "unknown",
            "explain_score_available": False
        }
    
    async def diagnose_weaviate_api(self):
        """Diagnostic des méthodes disponibles dans Weaviate v4.16.9 - Version Enhanced"""
        if self.api_capabilities["diagnosed"] and time.time() - self.api_capabilities["last_diagnostic_time"] < 3600:
            return
            
        try:
            collection = self.client.collections.get(self.collection_name)
            
            test_vector = [0.1] * 1536
            
            logger.info("=== DIAGNOSTIC WEAVIATE API v4.16.9 ===")
            
            # Test 1: Signature hybrid() avec vector
            try:
                result = collection.query.hybrid(
                    query="test diagnostic",
                    vector=test_vector,
                    alpha=0.7,
                    limit=1
                )
                self.api_capabilities["hybrid_with_vector"] = True
                logger.info("✅ Hybrid query fonctionne avec: query, vector, alpha, limit")
            except Exception as e:
                self.api_capabilities["hybrid_with_vector"] = False
                logger.error(f"❌ Hybrid query avec vector échoue: {e}")
                METRICS.api_correction_applied("hybrid_vector_fallback")
                
                try:
                    result = collection.query.hybrid(query="test diagnostic", limit=1)
                    logger.info("✅ Hybrid query fonctionne avec: query, limit seulement")
                    self.api_capabilities["api_stability"] = "limited"
                except Exception as e2:
                    logger.error(f"❌ Hybrid query minimal échoue: {e2}")
                    self.api_capabilities["api_stability"] = "degraded"
            
            # Test 2: Near vector avec explain_score
            formats_to_test = [
                {"vector": test_vector},
                {"near_vector": test_vector},
                {"query_vector": test_vector}
            ]
            
            for i, params in enumerate(formats_to_test):
                try:
                    params["limit"] = 1
                    if hasattr(wvc.query, 'MetadataQuery'):
                        params["return_metadata"] = wvc.query.MetadataQuery(
                            score=True, 
                            explain_score=True
                        )
                    result = collection.query.near_vector(**params)
                    self.api_capabilities["near_vector_format"] = list(params.keys())[0]
                    
                    # Test explain_score
                    if result.objects and hasattr(result.objects[0], 'metadata'):
                        if hasattr(result.objects[0].metadata, 'explain_score'):
                            self.api_capabilities["explain_score_available"] = True
                            logger.info("✅ explain_score disponible")
                        else:
                            self.api_capabilities["explain_score_available"] = False
                    
                    logger.info(f"✅ Near vector fonctionne avec: {list(params.keys())}")
                    break
                except Exception as e:
                    logger.error(f"❌ Format {i+1} near_vector échoue: {e}")
                    METRICS.api_correction_applied(f"near_vector_format_{i}")
            
            # Test 3: Hybrid avec filtre
            try:
                test_filter = wvc.query.Filter.by_property("species").equal("broiler")
                result = collection.query.hybrid(
                    query="test",
                    where=test_filter,
                    limit=1
                )
                self.api_capabilities["hybrid_with_where"] = True
                logger.info("✅ Hybrid avec where filter fonctionne")
            except Exception as e:
                self.api_capabilities["hybrid_with_where"] = False
                logger.error(f"❌ Hybrid avec where échoue: {e}")
                METRICS.api_correction_applied("hybrid_where_fallback")
            
            # Déterminer stabilité globale
            if self.api_capabilities["api_stability"] == "unknown":
                working_features = sum(1 for v in [
                    self.api_capabilities.get("hybrid_with_vector", False),
                    self.api_capabilities.get("hybrid_with_where", False),
                    self.api_capabilities.get("near_vector_format") is not None
                ] if v)
                
                if working_features >= 2:
                    self.api_capabilities["api_stability"] = "stable"
                elif working_features == 1:
                    self.api_capabilities["api_stability"] = "limited"
                else:
                    self.api_capabilities["api_stability"] = "degraded"
            
            self.api_capabilities["diagnosed"] = True
            self.api_capabilities["last_diagnostic_time"] = time.time()
            logger.info(f"📊 Capacités détectées: {self.api_capabilities}")
            logger.info(f"🎯 Stabilité API: {self.api_capabilities['api_stability']}")
            logger.info("=== FIN DIAGNOSTIC ===")
            
        except Exception as e:
            logger.error(f"Erreur diagnostic Weaviate: {e}")
            self.api_capabilities["diagnosed"] = True
            self.api_capabilities["api_stability"] = "error"
    
    async def adaptive_search(self, query_vector: List[float], query_text: str,
                            top_k: int = 15, where_filter: Dict = None) -> List[Document]:
        """Recherche adaptative qui ajuste alpha selon la requête"""
        
        if ENABLE_API_DIAGNOSTICS and not self.api_capabilities["diagnosed"]:
            await self.diagnose_weaviate_api()
        
        try:
            alpha = self._analyze_query_for_alpha(query_text)
            
            if HYBRID_SEARCH_ENABLED and self.is_v4:
                documents = await self._hybrid_search_v4_corrected(
                    query_vector, query_text, top_k, where_filter, alpha
                )
                if documents:
                    METRICS.search_stats["hybrid_native"] += 1
                    return documents
                else:
                    logger.warning("Recherche hybride n'a retourné aucun document, fallback vectoriel")
            
            # Fallback vers recherche vectorielle
            if self.is_v4:
                documents = await self._vector_search_v4_corrected(
                    query_vector, top_k, where_filter
                )
            else:
                documents = await self._vector_search_v3(
                    query_vector, top_k, where_filter
                )
            
            if documents:
                METRICS.search_stats["vector_only"] += 1
            
            # Retry sans age_band si nécessaire
            if not documents and where_filter and "age_band" in json.dumps(where_filter):
                logger.info("Retry recherche sans critère age_band")
                where_filter_no_age = self._remove_age_band_filter(where_filter)
                
                if self.is_v4:
                    documents = await self._hybrid_search_v4_corrected(
                        query_vector, query_text, top_k, where_filter_no_age, alpha
                    ) if HYBRID_SEARCH_ENABLED else await self._vector_search_v4_corrected(
                        query_vector, top_k, where_filter_no_age
                    )
                else:
                    documents = await self._vector_search_v3(
                        query_vector, top_k, where_filter_no_age
                    )
                    
                for doc in documents:
                    doc.metadata["age_band_fallback_used"] = True
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche adaptative: {e}")
            if self.is_v4:
                return await self._vector_search_v4_corrected(query_vector, top_k, None)
            else:
                return await self._vector_search_v3(query_vector, top_k, None)
    
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
        
        return 0.7
    
    async def _hybrid_search_v4_corrected(self, query_vector: List[float], query_text: str,
                                        top_k: int, where_filter: Dict, alpha: float) -> List[Document]:
        """Recherche hybride native Weaviate v4 - Version corrigée pour 4.16.9"""
        try:
            def _sync_hybrid_search():
                collection = self.client.collections.get(self.collection_name)
                
                search_params = {
                    "query": query_text,
                    "alpha": alpha,
                    "limit": top_k
                }
                
                # MODIFICATION: Ajouter explain_score si disponible
                if ENABLE_API_DIAGNOSTICS and self.api_capabilities.get("explain_score_available"):
                    search_params["return_metadata"] = wvc.query.MetadataQuery(
                        score=True, 
                        explain_score=True
                    )
                else:
                    search_params["return_metadata"] = wvc.query.MetadataQuery(score=True)
                
                if self.api_capabilities.get("hybrid_with_vector", True):
                    search_params["vector"] = query_vector
                
                if where_filter and self.api_capabilities.get("hybrid_with_where", True):
                    v4_filter = _to_v4_filter(where_filter)
                    if v4_filter is not None:
                        search_params["where"] = v4_filter
                
                try:
                    return collection.query.hybrid(**search_params)
                except TypeError as e:
                    self.api_capabilities["runtime_corrections"] += 1
                    METRICS.api_correction_applied("hybrid_runtime_fix")
                    
                    if "vector" in str(e) and "vector" in search_params:
                        logger.warning("Paramètre 'vector' non supporté dans hybrid(), retry sans vector")
                        del search_params["vector"]
                        self.api_capabilities["hybrid_with_vector"] = False
                        return collection.query.hybrid(**search_params)
                    elif "where" in str(e) and "where" in search_params:
                        logger.warning("Paramètre 'where' non supporté dans hybrid(), retry sans where")
                        del search_params["where"]
                        self.api_capabilities["hybrid_with_where"] = False
                        return collection.query.hybrid(**search_params)
                    else:
                        raise
            
            response = await anyio.to_thread.run_sync(_sync_hybrid_search)
            
            documents = []
            for obj in response.objects:
                hybrid_score = float(getattr(obj.metadata, "score", 0.0))
                
                # MODIFICATION: Extraire explain_score si disponible
                explain_score = None
                if hasattr(obj.metadata, "explain_score"):
                    explain_score = getattr(obj.metadata, "explain_score", None)
                
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
                        "alpha": alpha,
                        "vector_used": self.api_capabilities.get("hybrid_with_vector", False),
                        "runtime_corrections": self.api_capabilities.get("runtime_corrections", 0)
                    },
                    score=hybrid_score,
                    explain_score=explain_score
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche hybride v4: {e}")
            return await self._vector_search_v4_corrected(query_vector, top_k, where_filter)
    
    async def _vector_search_v4_corrected(self, query_vector: List[float], top_k: int, 
                                        where_filter: Dict) -> List[Document]:
        """Recherche vectorielle Weaviate v4 - Version corrigée pour 4.16.9"""
        try:
            def _sync_search():
                collection = self.client.collections.get(self.collection_name)
                
                base_params = {"limit": top_k}
                
                # MODIFICATION: Ajouter explain_score si disponible
                if ENABLE_API_DIAGNOSTICS and self.api_capabilities.get("explain_score_available"):
                    base_params["return_metadata"] = wvc.query.MetadataQuery(
                        distance=True, 
                        score=True, 
                        explain_score=True
                    )
                else:
                    base_params["return_metadata"] = wvc.query.MetadataQuery(distance=True, score=True)
                
                vector_param_name = self.api_capabilities.get("near_vector_format", "vector")
                
                params = base_params.copy()
                params[vector_param_name] = query_vector
                
                if where_filter:
                    v4_filter = _to_v4_filter(where_filter)
                    if v4_filter is not None:
                        params["where"] = v4_filter
                
                try:
                    return collection.query.near_vector(**params)
                except TypeError as e:
                    error_msg = str(e)
                    self.api_capabilities["runtime_corrections"] += 1
                    METRICS.api_correction_applied("vector_runtime_fix")
                    
                    if vector_param_name in error_msg:
                        for alternative in ["near_vector", "query_vector", "vector"]:
                            if alternative != vector_param_name:
                                try:
                                    alt_params = base_params.copy()
                                    alt_params[alternative] = query_vector
                                    if where_filter:
                                        v4_filter = _to_v4_filter(where_filter)
                                        if v4_filter is not None:
                                            alt_params["where"] = v4_filter
                                    
                                    result = collection.query.near_vector(**alt_params)
                                    self.api_capabilities["near_vector_format"] = alternative
                                    logger.info(f"Format vectoriel corrigé: {alternative}")
                                    return result
                                except:
                                    continue
                    
                    if "where" in error_msg and where_filter:
                        logger.warning("Filtre where non supporté, retry sans filtre")
                        params_no_filter = {k: v for k, v in params.items() if k != "where"}
                        return collection.query.near_vector(**params_no_filter)
                    
                    raise
            
            result = await anyio.to_thread.run_sync(_sync_search)
            
            documents = []
            for obj in result.objects:
                score = float(getattr(obj.metadata, "score", 0.0))
                distance = float(getattr(obj.metadata, "distance", 1.0))
                
                # MODIFICATION: Extraire explain_score si disponible
                explain_score = None
                if hasattr(obj.metadata, "explain_score"):
                    explain_score = getattr(obj.metadata, "explain_score", None)
                
                doc = Document(
                    content=obj.properties.get("content", ""),
                    metadata={
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "vector_format_used": self.api_capabilities.get("near_vector_format", "vector"),
                        "runtime_corrections": self.api_capabilities.get("runtime_corrections", 0)
                    },
                    score=score,
                    original_distance=distance,
                    explain_score=explain_score
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle v4: {e}")
            return await self._vector_search_fallback_minimal(query_vector, top_k)
    
    async def _vector_search_fallback_minimal(self, query_vector: List[float], top_k: int) -> List[Document]:
        """Recherche vectorielle minimale comme dernier recours"""
        try:
            def _sync_minimal_search():
                collection = self.client.collections.get(self.collection_name)
                return collection.query.near_vector(
                    near_vector=query_vector,
                    limit=top_k
                )
            
            result = await anyio.to_thread.run_sync(_sync_minimal_search)
            
            documents = []
            for obj in result.objects:
                score = getattr(obj.metadata, "score", 0.7) if hasattr(obj, "metadata") else 0.7
                
                doc = Document(
                    content=obj.properties.get("content", ""),
                    metadata={
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "fallback_search": True,
                        "minimal_api_used": True
                    },
                    score=float(score)
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche minimale: {e}")
            return []
    
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
                        "weaviate_v3_used": True
                    },
                    score=float(score) if score else 0.0,
                    original_distance=additional.get("distance")
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle v3: {e}")
            return []
    
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
    """Générateur avec enrichissement d'entités et cache externe + instrumentation sémantique"""
    
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
        """Génère une réponse enrichie avec cache externe + instrumentation sémantique"""
        try:
            # Vérifier le cache externe
            cache_hit_details = {"semantic_reasoning": "", "cache_type": ""}
            if self.cache_manager and self.cache_manager.enabled:
                context_hash = self.cache_manager.generate_context_hash(
                    [self._doc_to_dict(doc) for doc in context_docs]
                )
                cached_response = await self.cache_manager.get_response(
                    query, context_hash, language
                )
                if cached_response:
                    METRICS.cache_hit("response")
                    # MODIFICATION: Tracer le type de cache hit
                    if hasattr(self.cache_manager, 'get_last_cache_details'):
                        try:
                            cache_hit_details = await self.cache_manager.get_last_cache_details()
                            if cache_hit_details.get("semantic_fallback_used"):
                                METRICS.semantic_fallback_used()
                            else:
                                METRICS.semantic_cache_hit("exact")
                        except:
                            pass
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
            
            # MODIFICATION: Mettre en cache avec métadonnées enrichies
            if self.cache_manager and self.cache_manager.enabled:
                context_hash = self.cache_manager.generate_context_hash(
                    [self._doc_to_dict(doc) for doc in context_docs]
                )
                await self.cache_manager.set_response(
                    query, context_hash, generated_response, language,
                    metadata={
                        "generation_time": time.time(),
                        "enrichment_used": bool(enrichment),
                        "conversation_context_used": bool(conversation_context),
                        "intent_detected": str(intent_result.intent_type) if intent_result else None,
                        "entities_found": getattr(intent_result, 'detected_entities', {}) if intent_result else {}
                    }
                )
            
            return generated_response
            
        except Exception as e:
            logger.error(f"Erreur génération réponse enrichie: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."
    
    def _doc_to_dict(self, doc: Document) -> Dict:
        """Convertit Document en dict pour cache"""
        result = {
            "content": doc.content,
            "title": doc.metadata.get("title", ""),
            "source": doc.metadata.get("source", ""),
            "score": doc.score
        }
        if doc.explain_score:
            result["explain_score"] = doc.explain_score
        return result
    
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

        # MODIFICATION: Contexte conversationnel augmenté
        limited_context = conversation_context[:MAX_CONVERSATION_CONTEXT] if conversation_context else ""
        
        user_prompt = f"""CONTEXTE CONVERSATIONNEL:
{limited_context}

DOCUMENTS TECHNIQUES (avec métadonnées):
{context_text}

QUESTION ORIGINALE:
{query}

RÉPONSE TECHNIQUE (intégrant le contexte métier détecté):"""

        return system_prompt, user_prompt

# === DÉTECTEUR HORS DOMAINE ENRICHI ===
class EnhancedOODDetector:
    """Détecteur hors-domaine avec seuil dynamique basé sur l'intent"""
    
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
            path = os.getenv("BLOCKED_TERMS_FILE", "/app/blocked_terms.json")
            if not os.path.exists(path):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(base_dir, "blocked_terms.json")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                blocked_terms = json.load(f)
            
            logger.info(f"Loaded {len(blocked_terms)} blocked term categories from {path}")
            return blocked_terms
            
        except Exception as e:
            logger.warning(f"Erreur chargement blocked_terms depuis {path}: {e}")
            return {
                "general": ["crypto", "bitcoin", "football", "film", "politique", "news"]
            }
    
    def calculate_ood_score(self, query: str, intent_result=None) -> Tuple[bool, float, Dict[str, float]]:
        """MODIFICATION: Calcul score OOD avec seuil dynamique basé sur l'intent"""
        query_lower = (unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower())
        words = query_lower.split()
        
        # Boost entités métier
        entities_boost = 0.0
        genetic_metric_present = False
        if intent_result and hasattr(intent_result, 'detected_entities'):
            entities = intent_result.detected_entities
            business_entities = ['line', 'species', 'age_days', 'weight', 'fcr', 'phase']
            detected_business = [e for e in business_entities if e in entities]
            if detected_business:
                entities_boost = 0.3 * len(detected_business)
                # Détecter si génétique + métrique sont présents
                if ('line' in entities or 'species' in entities) and ('weight' in entities or 'fcr' in entities):
                    genetic_metric_present = True
        
        # NOUVEAU: Boost intent confidence si disponible
        intent_boost = 0.0
        if intent_result and hasattr(intent_result, 'confidence_breakdown'):
            breakdown = intent_result.confidence_breakdown
            # Si génétique + métrique détectés avec forte confidence
            if (breakdown.get('genetic_confidence', 0) > 0.7 and 
                breakdown.get('metric_confidence', 0) > 0.7):
                intent_boost = 0.2
        
        # Score vocabulaire domaine
        domain_words = [word for word in words if word in self.domain_keywords]
        vocab_score = (len(domain_words) / len(words) if words else 0.0) + entities_boost + intent_boost
        
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
        
        # MODIFICATION: Seuil dynamique
        threshold = OOD_MIN_SCORE
        generic_vocab_only = len(domain_words) <= 1 and entities_boost == 0
        
        if genetic_metric_present:
            # Requête spécifique avec génétique + métrique -> seuil plus souple
            threshold = max(0.2, OOD_MIN_SCORE - 0.1)
            METRICS.ood_stats["genetic_metric_threshold_applied"] += 1
        elif generic_vocab_only and len(words) > 3:
            # Vocabulaire générique seulement -> seuil plus strict
            threshold = OOD_STRICT_SCORE
            METRICS.ood_stats["strict_threshold_applied"] += 1
        
        is_in_domain = final_score > threshold
        
        # MODIFICATION: Tracer les raisons de filtrage
        if not is_in_domain:
            if blocked_score > 0.5:
                METRICS.ood_filtered(final_score, "blocked_terms")
            elif generic_vocab_only:
                METRICS.ood_filtered(final_score, "generic_vocab")
            else:
                METRICS.ood_filtered(final_score, "low_domain_score")
        
        score_details = {
            "vocab_score": vocab_score,
            "entities_boost": entities_boost,
            "intent_boost": intent_boost,
            "blocked_score": blocked_score,
            "final_score": final_score,
            "threshold_used": threshold,
            "genetic_metric_present": genetic_metric_present,
            "generic_vocab_only": generic_vocab_only
        }
        
        return is_in_domain, final_score, score_details

# === MÉMOIRE CONVERSATIONNELLE ENRICHIE ===
class ConversationMemory:
    """MODIFICATION: Mémoire conversationnelle avec plus de contexte"""
    
    def __init__(self, client):
        self.client = client
        self.memory_store = {}
        self.max_exchanges = 8  # MODIFICATION: 3 → 8 tours
    
    async def get_contextual_memory(self, tenant_id: str, current_query: str) -> str:
        """Récupère le contexte conversationnel enrichi"""
        if tenant_id not in self.memory_store:
            return ""
        
        history = self.memory_store[tenant_id]
        if not history:
            return ""
        
        try:
            # MODIFICATION: Retourner les 2-3 derniers échanges selon la longueur
            context_parts = []
            total_length = 0
            
            for exchange in reversed(history[-3:]):  # 3 derniers max
                exchange_text = f"Q: {exchange['question'][:150]}... R: {exchange['answer'][:200]}..."
                if total_length + len(exchange_text) <= MAX_CONVERSATION_CONTEXT:
                    context_parts.insert(0, exchange_text)
                    total_length += len(exchange_text)
                else:
                    break
            
            return " | ".join(context_parts)
            
        except Exception as e:
            logger.warning(f"Erreur mémoire: {e}")
            return ""
    
    def add_exchange(self, tenant_id: str, question: str, answer: str):
        """Ajoute un échange avec métadonnées"""
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
    """RAG Engine principal avec cache externe optimisé et corrections appliquées"""
    
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
        
        # MODIFICATION: Stats étendues avec nouvelles métriques
        self.optimization_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "semantic_cache_hits": 0,
            "fallback_cache_hits": 0,
            "hybrid_searches": 0,
            "guardrail_violations": 0,
            "entity_enrichments": 0,
            "api_corrections": 0,
            "external_cache_used": False,
            "semantic_debug_requests": 0,
            "explain_score_extractions": 0,
            "cache_semantic_reasoning_failures": 0,
            "intent_coverage_stats": defaultdict(int),
            "weaviate_capabilities": {},
            "dynamic_ood_threshold_adjustments": 0,
            "conversation_context_usage": 0
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
        """MODIFICATION: Initialisation avec await cache manager + orchestration corrigée"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation RAG Engine Enhanced avec cache externe")
        
        if not OPENAI_AVAILABLE or not WEAVIATE_AVAILABLE:
            self.degraded_mode = True
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return
        
        try:
            # MODIFICATION: 1. Cache Redis externe avec await obligatoire
            if CACHE_ENABLED and EXTERNAL_CACHE_AVAILABLE:
                self.cache_manager = RAGCacheManager()
                # CRITICAL: Assurer que l'initialisation est awaited
                await self.cache_manager.initialize()
                if self.cache_manager.enabled:
                    self.optimization_stats["external_cache_used"] = True
                    logger.info("✅ Cache Redis externe activé et initialisé")
                else:
                    logger.warning("⚠️ Cache Redis externe désactivé après initialisation")
            
            # 2. Connexion Weaviate
            await self._connect_weaviate()
            
            # 3. Composants de base avec ordre corrigé
            self.embedder = OpenAIEmbedder(self.openai_client, self.cache_manager)
            self.memory = ConversationMemory(self.openai_client)
            self.ood_detector = EnhancedOODDetector()
            
            # 4. Retriever hybride avec diagnostic intégré
            if self.weaviate_client:
                self.retriever = HybridWeaviateRetriever(self.weaviate_client)
                # Exécuter diagnostic au démarrage si activé
                if ENABLE_API_DIAGNOSTICS:
                    logger.info("🔍 Exécution diagnostic API Weaviate...")
                    await self.retriever.diagnose_weaviate_api()
                    # MODIFICATION: Stocker les capacités dans les stats
                    self.optimization_stats["weaviate_capabilities"] = self.retriever.api_capabilities.copy()
            
            # 5. Générateur enrichi
            if ENTITY_ENRICHMENT_ENABLED:
                self.generator = EnhancedResponseGenerator(self.openai_client, self.cache_manager)
            
            # 6. Guardrails avec explain_score si disponible
            if GUARDRAILS_AVAILABLE:
                self.guardrails = create_response_guardrails(self.openai_client, GUARDRAILS_LEVEL)
            
            # 7. Intent processor
            if INTENT_PROCESSOR_AVAILABLE:
                self.intent_processor = create_intent_processor()
            
            self.is_initialized = True
            logger.info("✅ RAG Engine Enhanced initialisé avec succès")
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            self.degraded_mode = True
            self.is_initialized = True
    
    async def _connect_weaviate(self):
        """Connexion Weaviate corrigée pour v4.16.9"""
        if WEAVIATE_V4:
            try:
                if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                    self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                        cluster_url=WEAVIATE_URL,
                        auth_credentials=wvc.init.Auth.api_key(WEAVIATE_API_KEY),
                        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                    )
                else:
                    if WEAVIATE_API_KEY:
                        self.weaviate_client = weaviate.connect_to_local(
                            host=WEAVIATE_URL.replace("http://", "").replace("https://", "").split(":")[0],
                            port=int(WEAVIATE_URL.split(":")[-1]) if ":" in WEAVIATE_URL else 8080,
                            auth_credentials=wvc.init.Auth.api_key(WEAVIATE_API_KEY),
                            headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                        )
                    else:
                        self.weaviate_client = weaviate.connect_to_local(
                            host=WEAVIATE_URL.replace("http://", "").replace("https://", "").split(":")[0],
                            port=int(WEAVIATE_URL.split(":")[-1]) if ":" in WEAVIATE_URL else 8080,
                            headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                        )
                
                def _test_connection():
                    return self.weaviate_client.is_ready()
                
                is_ready = await anyio.to_thread.run_sync(_test_connection)
                
                if not is_ready:
                    raise Exception("Weaviate not ready")
                    
            except Exception as e:
                logger.error(f"Erreur connexion Weaviate v4: {e}")
                try:
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
                    
                    def _check_fallback():
                        return self.weaviate_client.is_ready()
                    
                    is_ready = await anyio.to_thread.run_sync(_check_fallback)
                    
                    if not is_ready:
                        raise Exception("Weaviate fallback failed")
                        
                    logger.info("Fallback vers Weaviate v3 réussi")
                    
                except Exception as fallback_error:
                    logger.error(f"Erreur fallback Weaviate: {fallback_error}")
                    raise
        else:
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
        """MODIFICATION: Traitement avec toutes les optimisations appliquées"""
        if not RAG_ENABLED:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "rag_disabled"})
        
        if not self.is_initialized:
            await self.initialize()
        
        if self.degraded_mode:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "degraded_mode"})
        
        start_time = time.time()
        METRICS.inc("requests_total")
        
        try:
            # MODIFICATION: Détection langue optimisée
            if not language:
                language = detect_language_enhanced(query, default="fr")
            
            # Intent processing avec métriques
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                    if intent_result:
                        METRICS.intent_detected(
                            intent_result.intent_type, 
                            getattr(intent_result, 'confidence', 0.8)
                        )
                        self.optimization_stats["intent_coverage_stats"][intent_result.intent_type] += 1
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
            
            # MODIFICATION: OOD detection avec seuil dynamique
            if self.ood_detector:
                is_in_domain, domain_score, score_details = self.ood_detector.calculate_ood_score(query, intent_result)
                
                # Tracer ajustements de seuil
                if score_details.get("genetic_metric_present") or score_details.get("generic_vocab_only"):
                    self.optimization_stats["dynamic_ood_threshold_adjustments"] += 1
                
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
            
            # MODIFICATION: Contexte conversationnel enrichi
            conversation_context = ""
            if tenant_id and self.memory:
                try:
                    conversation_context = await self.memory.get_contextual_memory(tenant_id, query)
                    if conversation_context:
                        self.optimization_stats["conversation_context_usage"] += 1
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
            
            # Recherche hybride avec instrumentation
            documents = []
            if self.retriever:
                try:
                    documents = await self.retriever.adaptive_search(
                        query_vector, search_query, RAG_SIMILARITY_TOP_K, where_filter
                    )
                    if any(doc.metadata.get("hybrid_used") for doc in documents):
                        self.optimization_stats["hybrid_searches"] += 1
                    
                    # Compter corrections API
                    runtime_corrections = sum(doc.metadata.get("runtime_corrections", 0) for doc in documents)
                    if runtime_corrections > 0:
                        self.optimization_stats["api_corrections"] += runtime_corrections
                    
                    # Compter explain_score extraits
                    explain_scores_found = sum(1 for doc in documents if doc.explain_score is not None)
                    if explain_scores_found > 0:
                        self.optimization_stats["explain_score_extractions"] += explain_scores_found
                        
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
            
            # Génération de réponse enrichie avec cache sémantique
            response_text = ""
            cache_semantic_details = {}
            if self.generator and ENTITY_ENRICHMENT_ENABLED:
                try:
                    response_text = await self.generator.generate_response(
                        query, filtered_docs, conversation_context, language, intent_result
                    )
                    self.optimization_stats["entity_enrichments"] += 1
                    
                    # Récupérer détails cache sémantique
                    if (self.cache_manager and hasattr(self.cache_manager, 'get_last_semantic_details')):
                        try:
                            cache_semantic_details = await self.cache_manager.get_last_semantic_details()
                        except Exception as e:
                            logger.debug(f"Impossible de récupérer détails cache sémantique: {e}")
                            self.optimization_stats["cache_semantic_reasoning_failures"] += 1
                    
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
            
            # MODIFICATION: Vérification avec guardrails + explain_score
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
                        # MODIFICATION: Enrichir les métadonnées avec explain_score
                        docs_with_explain = []
                        for doc in filtered_docs:
                            doc_dict = doc.__dict__.copy()
                            if doc.explain_score:
                                doc_dict["explain_score"] = doc.explain_score
                            docs_with_explain.append(doc_dict)
                        
                        verification_result = await self.guardrails.verify_response(
                            query, response_text, docs_with_explain, intent_result
                        )
                        
                        if not verification_result.is_valid:
                            self.optimization_stats["guardrail_violations"] += 1
                            logger.warning(f"Violation guardrails: {verification_result.violations}")
                            
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
                doc_dict = {
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
                    "vector_format_used": doc.metadata.get("vector_format_used", ""),
                    "fallback_search": doc.metadata.get("fallback_search", False),
                    "minimal_api_used": doc.metadata.get("minimal_api_used", False),
                    "runtime_corrections": doc.metadata.get("runtime_corrections", 0),
                    "search_type": getattr(doc, 'search_type', 'unknown')
                }
                
                if doc.explain_score is not None:
                    doc_dict["explain_score"] = doc.explain_score
                
                context_docs.append(doc_dict)
            
            # MODIFICATION: Métadonnées complètes avec nouvelles infos
            metadata = {
                "approach": "enhanced_rag_external_cache_optimized_v4_16_9_corrected",
                "optimizations_enabled": {
                    "external_redis_cache": self.optimization_stats["external_cache_used"],
                    "semantic_cache": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False),
                    "hybrid_search": HYBRID_SEARCH_ENABLED,
                    "entity_enrichment": ENTITY_ENRICHMENT_ENABLED,
                    "advanced_guardrails": GUARDRAILS_AVAILABLE,
                    "api_diagnostics": ENABLE_API_DIAGNOSTICS,
                    "dynamic_ood_thresholds": True,
                    "enhanced_conversation_memory": True,
                    "explain_score_extraction": self.optimization_stats["explain_score_extractions"] > 0
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
                "language_detected": detect_language_enhanced(query),
                "optimization_stats": self.optimization_stats.copy(),
                "api_capabilities": self.retriever.api_capabilities if self.retriever else {},
                "api_corrections_applied": self.optimization_stats.get("api_corrections", 0) > 0,
                "cache_semantic_details": cache_semantic_details
            }
            
            if cache_semantic_details.get("semantic_keywords_used"):
                metadata["semantic_keywords_used"] = cache_semantic_details["semantic_keywords_used"]
            
            if intent_result:
                metadata.update({
                    "intent_type": getattr(intent_result, 'intent_type', 'unknown'),
                    "detected_entities": getattr(intent_result, 'detected_entities', {}),
                    "confidence_breakdown": getattr(intent_result, 'confidence_breakdown', {})
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
        """MODIFICATION: Status riche avec toutes les nouvelles métriques"""
        try:
            weaviate_connected = False
            api_capabilities = {}
            
            if self.weaviate_client:
                try:
                    def _check():
                        return self.weaviate_client.is_ready()
                    weaviate_connected = _check()
                except:
                    weaviate_connected = False
            
            if self.retriever and hasattr(self.retriever, 'api_capabilities'):
                api_capabilities = self.retriever.api_capabilities
            
            status = {
                "rag_enabled": RAG_ENABLED,
                "initialized": self.is_initialized,
                "degraded_mode": self.degraded_mode,
                "approach": "enhanced_rag_external_cache_optimized_v4_16_9_corrected",
                "optimizations": {
                    "external_cache_enabled": self.cache_manager.enabled if self.cache_manager else False,
                    "hybrid_search_enabled": HYBRID_SEARCH_ENABLED,
                    "semantic_cache_enabled": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False),
                    "entity_enrichment_enabled": ENTITY_ENRICHMENT_ENABLED,
                    "guardrails_level": GUARDRAILS_LEVEL,
                    "verification_smart": RAG_VERIFICATION_SMART,
                    "api_diagnostics_enabled": ENABLE_API_DIAGNOSTICS,
                    "dynamic_ood_thresholds": True,
                    "enhanced_conversation_memory": True,
                    "explain_score_extraction_enabled": api_capabilities.get("explain_score_available", False)
                },
                "components": {
                    "openai_available": OPENAI_AVAILABLE,
                    "weaviate_available": WEAVIATE_AVAILABLE,
                    "weaviate_version": weaviate_version if WEAVIATE_AVAILABLE else "N/A",
                    "weaviate_v4": WEAVIATE_V4,
                    "weaviate_connected": weaviate_connected,
                    "redis_available": REDIS_AVAILABLE,
                    "external_cache_available": EXTERNAL_CACHE_AVAILABLE,
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
                    "ood_strict_score": OOD_STRICT_SCORE,
                    "lang_detection_min_length": LANG_DETECTION_MIN_LENGTH,
                    "redis_url": REDIS_URL,
                    "weaviate_url": WEAVIATE_URL
                },
                "optimization_stats": self.optimization_stats.copy(),
                "weaviate_capabilities": api_capabilities,
                "intent_coverage_stats": dict(self.optimization_stats["intent_coverage_stats"]),
                "metrics": METRICS.snapshot()
            }
            
            # Stats cache externe
            if self.cache_manager and self.cache_manager.enabled:
                status["cache_stats"] = {
                    "enabled": True,
                    "external_cache_used": True,
                    "semantic_cache_enabled": getattr(self.cache_manager, 'ENABLE_SEMANTIC_CACHE', False),
                    "note": "Stats détaillées disponibles via cache externe"
                }
            else:
                status["cache_stats"] = {"enabled": False, "external_cache_used": False}
            
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
            
            logger.info("Enhanced RAG Engine avec cache externe nettoyé")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")


# === FONCTIONS UTILITAIRES POUR COMPATIBILITÉ ===
async def create_rag_engine(openai_client: AsyncOpenAI = None) -> InteliaRAGEngine:
    """MODIFICATION: Factory avec initialisation Redis asynchrone garantie"""
    try:
        engine = InteliaRAGEngine(openai_client)
        # CRITICAL: S'assurer que l'initialisation complète est awaited
        await engine.initialize()
        
        # Vérifier que le cache est bien initialisé
        if engine.cache_manager and not engine.cache_manager.enabled:
            logger.warning("⚠️ Cache manager créé mais pas enabled - vérifier configuration Redis")
        
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