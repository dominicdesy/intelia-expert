# -*- coding: utf-8 -*-
"""
retriever.py - Retriever hybride optimisé avec cache et fallbacks - Version corrigée pour Weaviate 4.16.9
"""

import logging
import time
import json
import re
import numpy as np
import anyio
from typing import Dict, List, Optional
from data_models import Document
from utilities import METRICS
from imports_and_dependencies import WEAVIATE_V4, wvc, wvc_query, ENABLE_API_DIAGNOSTICS
from config import HYBRID_SEARCH_ENABLED
from .hybrid_retriever import _fuse_results, hybrid_search

logger = logging.getLogger(__name__)

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

def retrieve(query: str, limit: int = 8, alpha: float = 0.6, **kwargs):
    """Façade simple qui utilise la recherche hybride par défaut."""
    return hybrid_search(query, limit=limit, alpha=alpha, **kwargs)

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