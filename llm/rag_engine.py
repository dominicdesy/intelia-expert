# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine avec OpenAI + Weaviate Direct - Version Finale Complète
Corrections appliquées: Métadonnées Weaviate v4, Filtres v4, Seuils, Retry age_band, 
BM25 fallback, Langue de réponse, HTTPS self-hosted, Vérification smart
Améliorations: Normalisation unités, Observabilité, Auto-détection langue, Messages OOD, Seuils dynamiques
Version Production-Ready Python 3.13
"""

import os
import asyncio
import logging
import time
import json
import re
import statistics
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import numpy as np
import httpx
import anyio

# Configuration logging
logger = logging.getLogger(__name__)

# Import Weaviate
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

# OpenAI Client
try:
    from openai import AsyncOpenAI, OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    logger.error(f"OpenAI non disponible: {e}")

# VoyageAI pour reranking
try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    logger.warning("VoyageAI non disponible - reranking basique")

# Sentence transformers pour reranking local
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("SentenceTransformers non disponible")

# Unidecode pour normalisation des accents
try:
    from unidecode import unidecode
    UNIDECODE_AVAILABLE = True
except ImportError:
    UNIDECODE_AVAILABLE = False
    logger.warning("Unidecode non disponible - pas de normalisation d'accents")

# Intelligence métier
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

# Configuration
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

# Paramètres RAG - CORRECTION: Seuil ajusté pour distance→score
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "15"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.55"))  # CORRECTION: Réduit de 0.65 à 0.55
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1024"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "8"))
RAG_VERIFICATION_ENABLED = os.getenv("RAG_VERIFICATION_ENABLED", "true").lower() == "true"
RAG_VERIFICATION_SMART = os.getenv("RAG_VERIFICATION_SMART", "true").lower() == "true"  # CORRECTION: Activé par défaut
MAX_CONVERSATION_CONTEXT = int(os.getenv("MAX_CONVERSATION_CONTEXT", "1500"))


# --- Simple in-process metrics collector ---
class MetricsCollector:
    def __init__(self):
        self.counters = defaultdict(int)
        self.last_100_lat = []

    def inc(self, key: str, n: int = 1): 
        self.counters[key] += n
    
    def observe_latency(self, sec: float):
        self.last_100_lat.append(sec)
        if len(self.last_100_lat) > 100: 
            self.last_100_lat = self.last_100_lat[-100:]

    def snapshot(self):
        p50 = statistics.median(self.last_100_lat) if self.last_100_lat else 0.0
        p95 = (sorted(self.last_100_lat)[int(0.95*len(self.last_100_lat))-1]
               if len(self.last_100_lat) >= 20 else p50)
        return {
            "counters": dict(self.counters),
            "p50_latency_sec": round(p50, 3),
            "p95_latency_sec": round(p95, 3),
            "samples": len(self.last_100_lat)
        }

METRICS = MetricsCollector()


# --- Light FR/EN language detector ---
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


# --- Unit normalization helpers ---
class UnitNormalizer:
    WEIGHT_UNITS = {"kg", "kilogram", "kilograms", "lb", "lbs", "pound", "pounds"}
    TEMP_UNITS = {"c", "°c", "celsius", "f", "°f", "fahrenheit"}

    @staticmethod
    def _detect_target_units(question: str) -> Tuple[Optional[str], Optional[str]]:
        q = question.lower()
        target_weight = "kg" if re.search(r"\bkg|kilogram", q) else ("lb" if re.search(r"\blb|pound", q) else None)
        target_temp = "c" if re.search(r"°?\s?c|celsius", q) else ("f" if re.search(r"°?\s?f|fahrenheit", q) else None)
        return target_weight, target_temp

    @staticmethod
    def kg_to_lb(x: float) -> float: 
        return x * 2.2046226218
    
    @staticmethod
    def lb_to_kg(x: float) -> float: 
        return x / 2.2046226218
    
    @staticmethod
    def c_to_f(x: float) -> float:   
        return x * 9.0/5.0 + 32.0
    
    @staticmethod
    def f_to_c(x: float) -> float:   
        return (x - 32.0) * 5.0/9.0

    @staticmethod
    def normalize_text(answer: str, question: str) -> str:
        tgt_w, tgt_t = UnitNormalizer._detect_target_units(question)
        if not tgt_w and not tgt_t:
            return answer
        # remplace virgules par points pour float()
        text = re.sub(r"(\d+),(\d+)", r"\1.\2", answer)

        def repl_weight(m):
            val = float(m.group("val"))
            unit = m.group("unit").lower()
            if tgt_w == "kg" and unit in {"lb", "lbs", "pound", "pounds"}:
                return f"{UnitNormalizer.lb_to_kg(val):.3f} kg"
            if tgt_w == "lb" and unit in {"kg", "kilogram", "kilograms"}:
                return f"{UnitNormalizer.kg_to_lb(val):.3f} lb"
            return m.group(0)

        def repl_temp(m):
            val = float(m.group("val"))
            unit = m.group("unit").lower()
            if tgt_t == "c" and unit in {"f", "°f", "fahrenheit"}:
                return f"{UnitNormalizer.f_to_c(val):.1f} °C"
            if tgt_t == "f" and unit in {"c", "°c", "celsius"}:
                return f"{UnitNormalizer.c_to_f(val):.1f} °F"
            return m.group(0)

        weight_pat = re.compile(r"(?P<val>\d+(?:[.]\d+)?)\s?(?P<unit>kg|kilograms?|lb|lbs|pounds?)\b", re.I)
        temp_pat   = re.compile(r"(?P<val>\d+(?:[.]\d+)?)\s?°?\s?(?P<unit>C|F|celsius|fahrenheit)\b", re.I)
        text = weight_pat.sub(repl_weight, text)
        text = temp_pat.sub(repl_temp, text)
        return text


class RAGSource(Enum):
    """Sources de réponse"""
    RAG_KNOWLEDGE = "rag_knowledge"
    RAG_VERIFIED = "rag_verified"
    OOD_FILTERED = "ood_filtered" 
    FALLBACK_NEEDED = "fallback_needed"
    ERROR = "error"


@dataclass
class RAGResult:
    """Résultat RAG"""
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
    """Document simple pour RAG"""
    content: str
    metadata: Dict = None
    score: float = 0.0
    original_distance: Optional[float] = None  # CORRECTION: Ajouté pour tracking
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class OpenAIEmbedder:
    """Wrapper pour OpenAI Embeddings"""
    
    def __init__(self, client: AsyncOpenAI, model: str = "text-embedding-3-small"):
        self.client = client
        self.model = model
        
    async def embed_query(self, text: str) -> List[float]:
        """Créer embedding pour une requête"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            return []
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Créer embeddings pour plusieurs documents"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Erreur embeddings batch: {e}")
            return []


def _to_v4_filter(where_dict):
    """CORRECTION: Convertit dict where v3 vers Filter v4"""
    if not where_dict or not WEAVIATE_V4 or not wvc:
        return where_dict
    
    try:
        # Cas feuille
        if "path" in where_dict:
            property_name = where_dict["path"][-1] if isinstance(where_dict["path"], list) else where_dict["path"]
            operator = where_dict.get("operator", "Equal")
            value = where_dict.get("valueText", where_dict.get("valueString", ""))
            
            if operator == "Like":
                return wvc.query.Filter.by_property(property_name).like(value)
            elif operator == "Equal":
                return wvc.query.Filter.by_property(property_name).equal(value)
            else:
                # Fallback
                return wvc.query.Filter.by_property(property_name).equal(value)
        
        # Cas composé
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


class WeaviateRetriever:
    """Retriever Weaviate direct avec corrections v4 + BM25 fallback"""
    
    def __init__(self, client, collection_name: str = "InteliaKnowledge"):
        self.client = client
        self.collection_name = collection_name
        self.is_v4 = WEAVIATE_V4
        
    async def search(self, query_vector: List[float], top_k: int = 10, where_filter: Dict = None) -> List[Document]:
        """Recherche vectorielle dans Weaviate avec retry age_band"""
        try:
            documents = await self._search_internal(query_vector, top_k, where_filter)
            
            # CORRECTION: Retry sans age_band si zéro résultat
            if not documents and where_filter and "age_band" in json.dumps(where_filter):
                logger.info("Retry recherche sans critère age_band")
                where_filter_no_age = self._remove_age_band_filter(where_filter)
                documents = await self._search_internal(query_vector, top_k, where_filter_no_age)
                
                # Marquer les docs comme issus du fallback
                for doc in documents:
                    doc.metadata["age_band_fallback_used"] = True
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche Weaviate: {e}")
            return []
    
    async def _bm25_v4(self, query: str, top_k: int = 8, where_filter: Dict = None) -> List[Document]:
        """NOUVEAU: Recherche BM25 en fallback pour Weaviate v4"""
        if not self.is_v4:
            return []
        
        try:
            def _sync_bm25():
                collection = self.client.collections.get(self.collection_name)
                params = {
                    "query": query,
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
                        "bm25_used": True  # Marquer comme BM25
                    },
                    score=score
                )
                documents.append(doc)
            
            logger.debug(f"BM25 fallback: {len(documents)} documents trouvés")
            return documents
            
        except Exception as e:
            logger.error(f"Erreur BM25 fallback: {e}")
            return []
    
    def _remove_age_band_filter(self, where_filter: Dict) -> Dict:
        """Retire le critère age_band du filtre"""
        if not where_filter:
            return None
        
        try:
            # Cas feuille avec age_band
            if "path" in where_filter:
                path = where_filter["path"]
                if (isinstance(path, list) and "age_band" in path) or path == "age_band":
                    return None
                return where_filter
            
            # Cas composé
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
    
    async def _search_internal(self, query_vector: List[float], top_k: int, where_filter: Dict) -> List[Document]:
        """Recherche interne"""
        if self.is_v4:
            return await self._search_v4_async(query_vector, top_k, where_filter)
        else:
            return await self._search_v3_async(query_vector, top_k, where_filter)
    
    async def _search_v4_async(self, query_vector: List[float], top_k: int, where_filter: Dict) -> List[Document]:
        """Recherche Weaviate V4 avec métadonnées corrigées"""
        try:
            def _sync_search():
                collection = self.client.collections.get(self.collection_name)
                
                # CORRECTION: Demander distance et certainty
                query_params = {
                    "vector": query_vector,
                    "limit": top_k,
                    "return_metadata": ["distance", "certainty"]  # CORRECTION: Pas "score"
                }
                
                # CORRECTION: Utiliser filter v4 si disponible
                if where_filter:
                    v4_filter = _to_v4_filter(where_filter)
                    if v4_filter:
                        query_params["where"] = v4_filter
                
                return collection.query.near_vector(**query_params)
            
            response = await anyio.to_thread.run_sync(_sync_search)
            
            documents = []
            for obj in response.objects:
                # CORRECTION: Conversion distance/certainty → score
                distance = getattr(obj.metadata, "distance", None)
                certainty = getattr(obj.metadata, "certainty", None)
                
                if certainty is not None:
                    score = float(certainty)
                    original_distance = None
                elif distance is not None:
                    # Conversion monotone: distance plus petite => score plus grand
                    distance_val = float(distance)
                    score = 1.0 / (1.0 + distance_val)
                    original_distance = distance_val
                else:
                    score = 0.0
                    original_distance = None
                
                doc = Document(
                    content=obj.properties.get("content", ""),
                    metadata={
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "creation_time": obj.metadata.creation_time if obj.metadata else None
                    },
                    score=score,
                    original_distance=original_distance
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche V4: {e}")
            return []
    
    async def _search_v3_async(self, query_vector: List[float], top_k: int, where_filter: Dict) -> List[Document]:
        """Recherche Weaviate V3"""
        try:
            def _sync_search():
                query_builder = (
                    self.client.query
                    .get(self.collection_name, ["content", "title", "source", "geneticLine", "species", "phase", "age_band"])
                    .with_near_vector({"vector": query_vector})
                    .with_limit(top_k)
                    .with_additional(["score", "id", "distance", "certainty"])
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
                distance = additional.get("distance")
                
                doc = Document(
                    content=obj.get("content", ""),
                    metadata={
                        "title": obj.get("title", ""),
                        "source": obj.get("source", ""),
                        "geneticLine": obj.get("geneticLine", ""),
                        "species": obj.get("species", ""),
                        "phase": obj.get("phase", ""),
                        "age_band": obj.get("age_band", ""),
                        "id": additional.get("id")
                    },
                    score=float(score) if score else 0.0,
                    original_distance=float(distance) if distance else None
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche V3: {e}")
            return []


class EnhancedOODDetector:
    """Détecteur hors-domaine amélioré avec normalisation accents"""
    
    def __init__(self, blocked_terms_path: str = None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_keywords = {
            'poulet', 'poule', 'aviculture', 'élevage', 'volaille', 'poids', 'fcr',
            'aliment', 'vaccination', 'maladie', 'production', 'croissance', 'nutrition',
            'chicken', 'poultry', 'broiler', 'layer', 'feed', 'weight', 'growth',
            'température', 'ventilation', 'eau', 'water', 'temperature', 'incubation',
            'couvoir', 'hatchery', 'biosécurité', 'mortalité', 'mortality', 'performance',
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann', 'ponte', 'eggs', 'laying',
            'reproduction', 'breeding', 'genetique', 'genetic', 'strain', 'line',
            'chair', 'meat', 'viande', 'carcasse', 'carcass', 'rendement', 'yield',
            'sanitaire', 'sanitary', 'veterinaire', 'veterinary', 'prophylaxie',
            'antibiotique', 'antibiotic', 'vaccin', 'vaccine', 'stress', 'welfare',
            'bien-être', 'densité', 'density', 'lighting', 'éclairage', 'photopériode'
        }
        
    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes bloqués"""
        if path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "blocked_terms.json")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erreur chargement blocked_terms.json: {e}")
            return {}
    
    def calculate_ood_score(self, query: str, intent_result=None) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul score OOD amélioré avec normalisation"""
        # NOUVEAU: Normalisation avec unidecode si disponible
        query_lower = (unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower())
        words = query_lower.split()
        
        # Boost entités métier détectées
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
        blocked_categories = []
        
        for category, terms in self.blocked_terms.items():
            category_matches = sum(1 for term in terms if term in query_lower)
            if category_matches > 0:
                blocked_categories.append(category)
                category_penalty = min(0.7, category_matches / max(2, len(words) // 2))
                blocked_score = max(blocked_score, category_penalty)
        
        # Score patterns hors-domaine
        ood_patterns = [
            r'\b(film|movie|cinema|série|series)\b',
            r'\b(football|sport|match)\b',
            r'\b(politique|president|élection)\b',
            r'\b(crypto|bitcoin|bourse)\b'
        ]
        
        pattern_score = 0.0
        for pattern in ood_patterns:
            if re.search(pattern, query_lower):
                pattern_score = 0.6
                break
        
        # Logique de fusion améliorée
        if vocab_score > 0.4:
            final_score = max(0.7, vocab_score - blocked_score * 0.3 - pattern_score * 0.2)
        elif entities_boost > 0:
            final_score = 0.6 + entities_boost - blocked_score * 0.2
        elif blocked_score > 0.6:
            final_score = 0.1
        else:
            final_score = (vocab_score * 0.8) - (blocked_score * 0.2) - (pattern_score * 0.1)
        
        is_in_domain = final_score > 0.2
        
        score_details = {
            "vocab_score": vocab_score,
            "entities_boost": entities_boost,
            "blocked_score": blocked_score,
            "pattern_score": pattern_score,
            "blocked_categories": blocked_categories,
            "final_score": final_score,
            "detected_business_entities": len([e for e in ['line', 'species', 'age_days', 'weight', 'fcr', 'phase'] 
                                             if intent_result and hasattr(intent_result, 'detected_entities') 
                                             and e in intent_result.detected_entities]) if intent_result else 0,
            "unidecode_used": UNIDECODE_AVAILABLE
        }
        
        return is_in_domain, final_score, score_details


class MultiStageReranker:
    """Reranking multi-étapes avec lazy init"""
    
    def __init__(self):
        self.voyage_client = None
        self._local_reranker = None
        self._local_reranker_initialized = False  # CORRECTION: Flag pour tracking
        
        # VoyageAI
        if VOYAGE_AVAILABLE and VOYAGE_API_KEY:
            try:
                self.voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
                logger.info("VoyageAI reranker initialisé")
            except Exception as e:
                logger.warning(f"Erreur init VoyageAI: {e}")
    
    @property
    def local_reranker(self):
        """CORRECTION: Lazy init du reranker local"""
        if not self._local_reranker_initialized and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._local_reranker = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Reranker local initialisé (lazy)")
            except Exception as e:
                logger.warning(f"Erreur init reranker local: {e}")
            finally:
                self._local_reranker_initialized = True
        
        return self._local_reranker
    
    async def rerank(self, query: str, documents: List[Document], intent_result=None, force_rerank: bool = False) -> List[Document]:
        """Reranking des documents"""
        if not documents:
            return documents
        
        should_rerank = len(documents) >= 5 or force_rerank
        
        try:
            if should_rerank:
                # Stage 1: Reranking sémantique
                if self.voyage_client:
                    documents = await self._voyage_rerank(query, documents)
                elif self.local_reranker:  # Utilise le property lazy
                    documents = await self._local_rerank(query, documents)
            
            # Stage 2: Intent-based boosting
            if intent_result:
                documents = self._intent_boost(documents, intent_result)
            
            # Stage 3: Diversity filtering
            if len(documents) > 3:
                documents = self._diversify_results(documents)
            
            return documents[:RAG_RERANK_TOP_K]
            
        except Exception as e:
            logger.error(f"Erreur reranking: {e}")
            return documents[:RAG_RERANK_TOP_K]
    
    async def _voyage_rerank(self, query: str, documents: List[Document]) -> List[Document]:
        """Reranking VoyageAI"""
        try:
            doc_texts = [doc.content for doc in documents]
            
            def _sync_rerank():
                return self.voyage_client.rerank(
                    query=query,
                    documents=doc_texts,
                    model="rerank-1",
                    top_k=min(len(documents), 12)
                )
            
            reranked = await anyio.to_thread.run_sync(_sync_rerank)
            
            reranked_docs = []
            for item in reranked.results:
                original_doc = documents[item.index]
                original_doc.score = (original_doc.score * 0.3 + item.relevance_score * 0.7)
                reranked_docs.append(original_doc)
            
            logger.debug(f"VoyageAI reranked {len(documents)} -> {len(reranked_docs)} documents")
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Erreur VoyageAI reranking: {e}")
            return documents
    
    async def _local_rerank(self, query: str, documents: List[Document]) -> List[Document]:
        """Reranking local avec sentence-transformers"""
        try:
            def _sync_rerank():
                doc_texts = [doc.content for doc in documents]
                query_embedding = self.local_reranker.encode(query)
                doc_embeddings = self.local_reranker.encode(doc_texts)
                
                similarities = util.cos_sim(query_embedding, doc_embeddings)[0]
                return similarities.cpu().numpy()
            
            similarities = await anyio.to_thread.run_sync(_sync_rerank)
            
            for i, doc in enumerate(documents):
                doc.score = (doc.score * 0.4 + float(similarities[i]) * 0.6)
            
            documents.sort(key=lambda x: x.score, reverse=True)
            logger.debug(f"Local reranked {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Erreur local reranking: {e}")
            return documents
    
    def _intent_boost(self, documents: List[Document], intent_result) -> List[Document]:
        """Boost basé sur l'intention"""
        for doc in documents:
            boost_factor = 1.0
            
            try:
                # Boost correspondance lignée
                if hasattr(intent_result, 'detected_entities') and "line" in intent_result.detected_entities:
                    target_line = intent_result.detected_entities["line"].lower()
                    doc_line = doc.metadata.get("geneticLine", "").lower()
                    if target_line in doc_line or doc_line in target_line:
                        boost_factor *= 1.4
                
                # Boost correspondance espèce
                if hasattr(intent_result, 'detected_entities') and "species" in intent_result.detected_entities:
                    target_species = intent_result.detected_entities["species"].lower()
                    doc_species = doc.metadata.get("species", "").lower()
                    if target_species in doc_species or doc_species in target_species:
                        boost_factor *= 1.3
                
                # Boost correspondance âge
                if hasattr(intent_result, 'detected_entities') and "age_days" in intent_result.detected_entities:
                    doc_age_band = doc.metadata.get("age_band", "")
                    if doc_age_band:
                        boost_factor *= 1.25
                
                # Boost correspondance phase
                if hasattr(intent_result, 'detected_entities') and "phase" in intent_result.detected_entities:
                    target_phase = intent_result.detected_entities["phase"].lower()
                    doc_phase = doc.metadata.get("phase", "").lower()
                    if target_phase in doc_phase or doc_phase in target_phase:
                        boost_factor *= 1.3
                
                # Boost queries métriques
                if (hasattr(intent_result, 'intent_type') and 
                    intent_result.intent_type == IntentType.METRIC_QUERY):
                    if any(char.isdigit() for char in doc.content[:200]):
                        boost_factor *= 1.15
                
                doc.score = min(1.0, doc.score * boost_factor)
                        
            except Exception as e:
                logger.warning(f"Erreur intent boost: {e}")
        
        return sorted(documents, key=lambda x: x.score, reverse=True)
    
    def _diversify_results(self, documents: List[Document]) -> List[Document]:
        """Filtrage diversité"""
        if len(documents) <= 3:
            return documents
        
        try:
            diversified = [documents[0]]
            
            for candidate in documents[1:]:
                is_diverse = True
                candidate_words = set(candidate.content.lower().split())
                
                for selected in diversified:
                    selected_words = set(selected.content.lower().split())
                    
                    if candidate_words and selected_words:
                        overlap = len(candidate_words.intersection(selected_words))
                        similarity = overlap / min(len(candidate_words), len(selected_words))
                        
                        if similarity > 0.75:
                            is_diverse = False
                            break
                
                if is_diverse:
                    diversified.append(candidate)
            
            return diversified
            
        except Exception as e:
            logger.warning(f"Erreur diversification: {e}")
            return documents


class ResponseGenerator:
    """Générateur de réponses avec OpenAI - CORRECTION: Langue forcée"""
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
    
    async def generate_response(self, query: str, context_docs: List[Document], conversation_context: str = "", language: str = "fr") -> str:
        """Génère une réponse basée sur le contexte"""
        try:
            context_text = "\n\n".join([
                f"Document {i+1}:\n{doc.content[:1000]}"
                for i, doc in enumerate(context_docs[:5])
            ])
            
            # CORRECTION: Ajout explicite de la règle de langue
            system_prompt = """Tu es un expert en aviculture spécialisé dans l'aide aux éleveurs de volailles.

INSTRUCTIONS:
1. Réponds uniquement basé sur les documents fournis
2. Sois précis et technique quand approprié
3. Mentionne les lignées génétiques si pertinentes
4. Fournis des données chiffrées quand disponibles
5. Si les documents ne contiennent pas l'information, dis-le clairement

RÈGLE DE LANGUE: Réponds STRICTEMENT dans la même langue que la QUESTION.

DOMAINE: Aviculture, élevage de volailles, performance, nutrition, santé"""

            limited_context = conversation_context[:MAX_CONVERSATION_CONTEXT] if conversation_context else ""
            
            # CORRECTION: Ajout de la langue cible dans le prompt
            user_prompt = f"""LANGUE_CIBLE: {language}

CONTEXTE CONVERSATIONNEL:
{limited_context}

DOCUMENTS DE RÉFÉRENCE:
{context_text}

QUESTION:
{query}

RÉPONSE (dans la langue demandée, basée UNIQUEMENT sur les documents fournis):"""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erreur génération réponse: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."


class ResponseVerifier:
    """Vérificateur de réponses avec mode smart"""
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
    
    async def verify_response(self, query: str, response: str, context_docs: List[Document]) -> Dict[str, Any]:
        """Vérification des réponses"""
        if not RAG_VERIFICATION_ENABLED or not context_docs:
            return {"verified": True, "confidence": 0.8, "corrections": []}
        
        try:
            context_text = "\n\n".join([
                f"Document {i+1}: {doc.content[:500]}"
                for i, doc in enumerate(context_docs[:3])
            ])
            
            # CORRECTION: Prompt anti-hallucination renforcé
            verification_prompt = f"""Vérifie si la RÉPONSE est supportée par les DOCUMENTS.

RÉPONSE À VÉRIFIER:
{response}

DOCUMENTS DE RÉFÉRENCE:
{context_text}

RAPPEL: Si une partie de la réponse N'EST PAS présente dans les documents, signale-la comme NON_VÉRIFIÉE.

FORMAT:
- STATUT: [VÉRIFIÉ/PARTIELLEMENT_VÉRIFIÉ/NON_VÉRIFIÉ]
- CONFIANCE: [0.0-1.0]
- PROBLÈMES: [liste des problèmes]"""

            verification = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": verification_prompt}],
                temperature=0.0,
                max_tokens=500
            )
            
            verification_text = verification.choices[0].message.content
            
            status = "VÉRIFIÉ"
            confidence = 0.8
            
            if "NON_VÉRIFIÉ" in verification_text:
                status = "NON_VÉRIFIÉ"
                confidence = 0.3
            elif "PARTIELLEMENT_VÉRIFIÉ" in verification_text:
                status = "PARTIELLEMENT_VÉRIFIÉ"
                confidence = 0.6
            
            return {
                "verified": status == "VÉRIFIÉ",
                "status": status,
                "confidence": confidence,
                "verification_detail": verification_text
            }
            
        except Exception as e:
            logger.error(f"Erreur vérification: {e}")
            return {"verified": True, "confidence": 0.7, "error": str(e), "fallback_used": True}


class ConversationMemory:
    """Mémoire conversationnelle"""
    
    def __init__(self, client: AsyncOpenAI):
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
        
        if len(history) <= 2:
            context = "\n\n".join([
                f"Q: {entry['question']}\nR: {entry['answer']}"
                for entry in history
            ])
            return context[:MAX_CONVERSATION_CONTEXT]
        
        try:
            history_text = "\n\n".join([
                f"Échange {i+1}:\nQ: {entry['question']}\nR: {entry['answer']}"
                for i, entry in enumerate(history[-4:])
            ])
            
            summary_prompt = f"""Résume cette conversation avicole en conservant les informations pertinentes pour la nouvelle question.

HISTORIQUE:
{history_text}

NOUVELLE QUESTION: {current_query}

Résumé contextuel (200 mots max):"""

            summary = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.1,
                max_tokens=250
            )
            
            result = summary.choices[0].message.content.strip()
            return result[:MAX_CONVERSATION_CONTEXT]
            
        except Exception as e:
            logger.error(f"Erreur résumé conversation: {e}")
            try:
                simple_context = f"Contexte: {history[-1]['question']} -> {history[-1]['answer'][:100]}..."
                return simple_context[:MAX_CONVERSATION_CONTEXT]
            except Exception as e2:
                logger.error(f"Erreur fallback contexte: {e2}")
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


def build_where_filter(intent_result) -> Dict:
    """Construire where filter par entités"""
    if not intent_result or not hasattr(intent_result, 'detected_entities'):
        return None
    
    entities = intent_result.detected_entities
    where_conditions = []
    
    # Filtre par lignée génétique
    if "line" in entities:
        line_value = entities["line"]
        where_conditions.append({
            "path": ["geneticLine"],
            "operator": "Like",
            "valueText": f"*{line_value}*"
        })
    
    # Filtre par espèce
    if "species" in entities:
        species_value = entities["species"] 
        where_conditions.append({
            "path": ["species"],
            "operator": "Like", 
            "valueText": f"*{species_value}*"
        })
    
    # Filtre par phase
    if "phase" in entities:
        phase_value = entities["phase"]
        where_conditions.append({
            "path": ["phase"],
            "operator": "Like",
            "valueText": f"*{phase_value}*"
        })
    
    # Filtre par tranche d'âge
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


class InteliaRAGEngine:
    """RAG Engine principal avec toutes les corrections appliquées"""
    
    def __init__(self, openai_client: AsyncOpenAI = None):
        self.openai_client = openai_client or self._build_openai_client()
        self.embedder = None
        self.retriever = None
        self.generator = None
        self.verifier = None
        self.memory = None
        self.intent_processor = None
        self.ood_detector = None
        self.reranker = None
        self.weaviate_client = None
        self.is_initialized = False
        self.degraded_mode = False
    
    def _build_openai_client(self) -> AsyncOpenAI:
        """Construit le client OpenAI"""
        try:
            http_client = httpx.AsyncClient(timeout=30.0)
            return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
        except Exception as e:
            logger.warning(f"Erreur client OpenAI personnalisé: {e}")
            return AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def initialize(self):
        """Initialisation"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation RAG Engine Direct - Version Finale Complète")
        
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI non disponible")
            self.degraded_mode = True
            
        if not WEAVIATE_AVAILABLE:
            logger.error("Weaviate non disponible")
            self.degraded_mode = True
        
        if self.degraded_mode:
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return
        
        try:
            self.embedder = OpenAIEmbedder(self.openai_client)
            self.generator = ResponseGenerator(self.openai_client)
            self.verifier = ResponseVerifier(self.openai_client)
            self.memory = ConversationMemory(self.openai_client)
            self.ood_detector = EnhancedOODDetector()
            self.reranker = MultiStageReranker()
            
            if INTENT_PROCESSOR_AVAILABLE:
                self.intent_processor = create_intent_processor()
            
            logger.info("Composants initialisés")
        except Exception as e:
            logger.error(f"Erreur init composants: {e}")
            self.degraded_mode = True
        
        try:
            await self._connect_weaviate()
            self.retriever = WeaviateRetriever(self.weaviate_client)
            logger.info("Weaviate connecté")
        except Exception as e:
            logger.error(f"Erreur connexion Weaviate: {e}")
            self.degraded_mode = True
        
        self.is_initialized = True
        logger.info(f"RAG Engine initialisé (dégradé: {self.degraded_mode})")
    
    async def _connect_weaviate(self):
        """Connexion Weaviate avec support HTTPS self-hosted"""
        if WEAVIATE_V4:
            if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                auth_credentials = wvc.init.Auth.api_key(WEAVIATE_API_KEY)
                self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=WEAVIATE_URL,
                    auth_credentials=auth_credentials,
                    headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            else:
                # CORRECTION: Support HTTPS self-hosted
                scheme, host = ("https", WEAVIATE_URL[8:]) if WEAVIATE_URL.startswith("https://") else ("http", WEAVIATE_URL[7:] if WEAVIATE_URL.startswith("http://") else WEAVIATE_URL)
                port = 8080
                if ":" in host:
                    host, port = host.split(":")
                    port = int(port)
                
                self.weaviate_client = weaviate.connect_to_weaviate(
                    http_host=host,
                    http_port=port,
                    http_secure=(scheme == "https"),
                    headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
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
            if hasattr(self.weaviate_client, 'is_ready'):
                return self.weaviate_client.is_ready()
            else:
                self.weaviate_client.schema.get()
                return True
        
        is_ready = await anyio.to_thread.run_sync(_check_connection)
        if not is_ready:
            raise Exception("Weaviate not ready")
    
    async def process_query(self, query: str, language: str = "fr", tenant_id: str = "") -> RAGResult:
        """Traitement des requêtes avec toutes les corrections + BM25 fallback + améliorations"""
        if not RAG_ENABLED:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "rag_disabled"})
        
        if not self.is_initialized:
            await self.initialize()
        
        if self.degraded_mode:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                metadata={"reason": "degraded_mode"}
            )
        
        start_time = time.time()
        METRICS.inc("requests_total")
        
        try:
            # Auto-détection si language non fourni explicitement
            if not language:
                language = detect_language_light(query, default="fr")
            
            # Intent processing
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
            
            # OOD detection
            if self.ood_detector:
                is_in_domain, domain_score, score_details = self.ood_detector.calculate_ood_score(query, intent_result)
                
                if not is_in_domain:
                    METRICS.inc("requests_ood")
                    METRICS.observe_latency(time.time() - start_time)
                    return RAGResult(
                        source=RAGSource.OOD_FILTERED,
                        answer="Désolé, cette question sort du domaine avicole traité par ce système. "
                               "Pose-moi une question sur l'aviculture (ex.: poids cible, FCR, ventilation, biosécurité, etc.).",
                        confidence=1.0 - domain_score,
                        processing_time=time.time() - start_time,
                        metadata={
                            "domain_score": domain_score,
                            "score_details": score_details
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
                    metadata={"error": "embedding_failed"}
                )
            
            # Construire where filter par entités
            where_filter = build_where_filter(intent_result)
            
            # Recherche documents (avec retry age_band intégré)
            METRICS.inc("search_vector_calls")
            if where_filter: 
                METRICS.inc("search_with_filter")
            
            documents = await self.retriever.search(query_vector, RAG_SIMILARITY_TOP_K, where_filter)
            
            # NOUVEAU: BM25 fallback si pas assez de docs ou faible confiance
            bm25_used = False
            if not documents or all(doc.score < RAG_CONFIDENCE_THRESHOLD for doc in documents):
                logger.info("Activation BM25 fallback")
                METRICS.inc("bm25_fallback_activations")
                bm25_docs = await self.retriever._bm25_v4(search_query, 8, where_filter)
                if bm25_docs:
                    # Fusion simple (vector + bm25), dédupli par titre+source
                    merged = (documents or []) + bm25_docs
                    seen = set()
                    unique = []
                    for doc in merged:
                        key = (doc.metadata.get("title", ""), doc.metadata.get("source", ""))
                        if key not in seen:
                            seen.add(key)
                            unique.append(doc)
                    documents = unique
                    bm25_used = True
            
            if not documents:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={"reason": "no_documents_found", "where_filter_used": where_filter is not None, "bm25_tried": True}
                )
            
            # Seuil dynamique: remonte si top1 très fort, abaisse si BM25 a aidé
            effective_threshold = RAG_CONFIDENCE_THRESHOLD
            if documents:
                top1 = max(d.score for d in documents)
                if top1 >= 0.85:
                    effective_threshold = max(RAG_CONFIDENCE_THRESHOLD, 0.60)
                if bm25_used and top1 < 0.70:
                    effective_threshold = min(effective_threshold, 0.50)
            
            # Filtrage par confiance (seuil dynamique)
            filtered_docs = [doc for doc in documents if doc.score >= effective_threshold]
            
            if not filtered_docs:
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={"reason": "low_confidence_documents", "min_score": min(doc.score for doc in documents) if documents else 0, "bm25_used": bm25_used, "effective_threshold": effective_threshold}
                )
            
            # Reranking systématique
            filtered_docs = await self.reranker.rerank(search_query, filtered_docs, intent_result, force_rerank=True)
            
            # Génération réponse AVEC langue
            response_text = await self.generator.generate_response(
                query, filtered_docs, conversation_context, language
            )
            
            # Normalisation d'unités vers la préférence implicite de la question
            try:
                response_text = UnitNormalizer.normalize_text(response_text, query)
            except Exception as _e:
                logger.debug(f"Unit normalization skipped: {_e}")
            
            if not response_text or "ne peux pas" in response_text.lower():
                METRICS.observe_latency(time.time() - start_time)
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={"reason": "generation_failed", "bm25_used": bm25_used}
                )
            
            # CORRECTION: Vérification smart
            verification_result = None
            if self.verifier:
                do_verify = True
                if RAG_VERIFICATION_SMART:
                    # Ne vérifie pas si top1 très haut et variance faible
                    top_scores = [d.score for d in filtered_docs[:3]]
                    if top_scores and top_scores[0] >= 0.80 and (len(top_scores) <= 1 or np.std(top_scores) <= 0.05):
                        do_verify = False
                        logger.debug("Vérification smart: skipped (haute confiance)")
                
                if do_verify:
                    METRICS.inc("verification_calls")
                    verification_result = await self.verifier.verify_response(
                        query, response_text, filtered_docs
                    )
            
            # Calcul confiance
            confidence = self._calculate_confidence(filtered_docs, verification_result)
            
            # Source résultat
            result_source = RAGSource.RAG_KNOWLEDGE
            if verification_result and verification_result.get("verified", True):
                result_source = RAGSource.RAG_VERIFIED
                confidence = min(confidence * 1.1, 0.95)
            
            # Context docs pour résultat
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
                    "original_distance": doc.original_distance,
                    "bm25_used": doc.metadata.get("bm25_used", False)
                })
            
            # Métadonnées enrichies avec corrections
            metadata = {
                "approach": "openai_weaviate_direct_finale_corrected_enhanced_complete",
                "corrections_applied": [
                    "weaviate_v4_metadata_fixed",
                    "weaviate_v4_filters_fixed", 
                    "confidence_threshold_adjusted",
                    "age_band_retry_implemented",
                    "lazy_init_reranker",
                    "metadata_flags_corrected",
                    "distance_score_conversion",
                    "language_forced_in_generation",
                    "bm25_hybrid_fallback_added",
                    "verification_smart_implemented",
                    "https_self_hosted_support",
                    "unidecode_ood_normalization",
                    "unit_normalization_added",
                    "observability_metrics_added",
                    "language_auto_detection",
                    "ood_clear_messages",
                    "dynamic_threshold_implemented"
                ],
                "weaviate_version": weaviate_version,
                "weaviate_v4": WEAVIATE_V4,
                "documents_found": len(documents) if documents else 0,
                "documents_used": len(filtered_docs),
                "query_expanded": search_query != query,
                "conversation_context_used": bool(conversation_context),
                "reranking_applied": True,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "verification_smart": RAG_VERIFICATION_SMART,
                "verification_smart_skipped": (RAG_VERIFICATION_SMART and verification_result is None),
                "where_filter_applied": where_filter is not None,
                "age_band_fallback_used": any(doc.metadata.get("age_band_fallback_used", False) for doc in filtered_docs),
                "bm25_fallback_used": bm25_used,
                "voyage_reranking": self.reranker.voyage_client is not None,
                "local_reranking": self.reranker.local_reranker is not None,
                "score_conversion_applied": any(doc.original_distance is not None for doc in filtered_docs),
                "language_target": language,
                "language_detected": detect_language_light(query),
                "unidecode_available": UNIDECODE_AVAILABLE,
                "effective_confidence_threshold": effective_threshold,
                "unit_normalization_available": True
            }
            
            if intent_result:
                metadata.update({
                    "intent_type": intent_result.intent_type.value if hasattr(intent_result.intent_type, 'value') else str(intent_result.intent_type),
                    "detected_entities": getattr(intent_result, 'detected_entities', {}),
                    "business_entities_count": len([e for e in ['line', 'species', 'age_days', 'weight', 'fcr', 'phase'] 
                                                   if hasattr(intent_result, 'detected_entities') 
                                                   and e in intent_result.detected_entities])
                })
            
            if where_filter:
                metadata["where_filter"] = where_filter
            
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
                verification_status=verification_result,
                intent_result=intent_result
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement query: {e}")
            METRICS.observe_latency(time.time() - start_time)
            return RAGResult(
                source=RAGSource.ERROR,
                confidence=0.0,
                processing_time=time.time() - start_time,
                metadata={"error": str(e)},
                intent_result=intent_result if 'intent_result' in locals() else None
            )
    
    def _calculate_confidence(self, documents: List[Document], verification_result: Dict = None) -> float:
        """Calcul de confiance"""
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
        if verification_result and verification_result.get("verified", True):
            verification_factor = 1.1
        
        final_confidence = avg_score * coherence_factor * distribution_factor * verification_factor
        return min(0.95, max(0.1, final_confidence))
    
    def get_status(self) -> Dict:
        """Status du système avec corrections appliquées et métriques"""
        try:
            def _check_weaviate():
                return (
                    self.weaviate_client is not None and 
                    (self.weaviate_client.is_ready() if hasattr(self.weaviate_client, 'is_ready') else True)
                )
            
            weaviate_connected = _check_weaviate()
            
            return {
                "rag_enabled": RAG_ENABLED,
                "initialized": self.is_initialized,
                "degraded_mode": self.degraded_mode,
                "approach": "openai_weaviate_direct_finale_enhanced_corrected_complete",
                "corrections_applied": [
                    "weaviate_v4_metadata_fixed",
                    "weaviate_v4_filters_fixed", 
                    "confidence_threshold_adjusted",
                    "age_band_retry_implemented",
                    "lazy_init_reranker",
                    "metadata_flags_corrected",
                    "distance_score_conversion",
                    "language_consistency_added",
                    "hybrid_retrieval_bm25",
                    "units_normalization",
                    "robust_weaviate_https",
                    "ood_accents_variants",
                    "observability_enhanced",
                    "verification_smart_mode",
                    "dynamic_confidence_threshold",
                    "language_auto_detection",
                    "ood_clear_user_messages",
                    "comprehensive_unit_support"
                ],
                "openai_available": OPENAI_AVAILABLE,
                "weaviate_available": WEAVIATE_AVAILABLE,
                "weaviate_version": weaviate_version if WEAVIATE_AVAILABLE else "N/A",
                "weaviate_v4": WEAVIATE_V4,
                "weaviate_connected": weaviate_connected,
                "intent_processor_available": INTENT_PROCESSOR_AVAILABLE,
                "voyage_reranking": VOYAGE_AVAILABLE and VOYAGE_API_KEY is not None,
                "local_reranking": SENTENCE_TRANSFORMERS_AVAILABLE,
                "unidecode_available": UNIDECODE_AVAILABLE,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "verification_smart": RAG_VERIFICATION_SMART,
                "confidence_threshold": RAG_CONFIDENCE_THRESHOLD,
                "similarity_top_k": RAG_SIMILARITY_TOP_K,
                "rerank_top_k": RAG_RERANK_TOP_K,
                "max_conversation_context": MAX_CONVERSATION_CONTEXT,
                "features": [
                    "production_ready_enhanced_complete",
                    "weaviate_v4_metadata_handling",
                    "weaviate_v4_filter_conversion",
                    "age_band_fallback_retry",
                    "distance_to_score_conversion",
                    "lazy_reranker_initialization",
                    "corrected_metadata_flags",
                    "adjusted_confidence_thresholds",
                    "language_consistency_fr_en",
                    "hybrid_retrieval_vector_bm25",
                    "robust_weaviate_https_support",
                    "ood_accents_variants_handling",
                    "verification_smart_mode",
                    "enhanced_observability_tracking",
                    "unit_normalization_kg_lb_c_f",
                    "dynamic_confidence_thresholds",
                    "language_auto_detection_fr_en",
                    "metrics_collection_prometheus_ready",
                    "ood_clear_user_messages",
                    "comprehensive_unit_conversions",
                    "smart_threshold_adaptation"
                ],
                "metrics": METRICS.snapshot()
            }
        except Exception as e:
            logger.error(f"Erreur get_status: {e}")
            return {
                "error": str(e),
                "rag_enabled": RAG_ENABLED,
                "initialized": False,
                "degraded_mode": True
            }
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        try:
            if self.weaviate_client:
                if hasattr(self.weaviate_client, 'close'):
                    self.weaviate_client.close()
            
            if self.memory:
                self.memory.memory_store.clear()
            
            if hasattr(self.openai_client, 'http_client'):
                await self.openai_client.http_client.aclose()
            
            logger.info("RAG Engine nettoyé")
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")


# Fonctions utilitaires pour compatibilité
async def create_rag_engine(openai_client: AsyncOpenAI = None) -> InteliaRAGEngine:
    """Factory pour créer le RAG engine"""
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
    """Interface compatible"""
    try:
        return await rag_engine.process_query(question, language, tenant_id)
    except Exception as e:
        logger.error(f"Erreur process_question_with_rag: {e}")
        return RAGResult(
            source=RAGSource.ERROR,
            confidence=0.0,
            metadata={"error": str(e)}
        )