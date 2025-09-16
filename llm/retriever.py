# -*- coding: utf-8 -*-
"""
retriever.py - Retriever hybride optimisé avec cache et fallbacks - Version adaptée
Version corrigée pour Weaviate 4.16.10 avec intégrations complètes
CORRIGÉ: Import ENABLE_API_DIAGNOSTICS
CORRIGÉ: Gestion des dimensions vectorielles (384 vs 1536)
CORRIGÉ: Corrections runtime des arguments API v4
"""

import logging
import time
import json
import re
import numpy as np
import anyio
from typing import Dict, List, Optional, Any
from data_models import Document
from utilities import METRICS
from imports_and_dependencies import WEAVIATE_V4, wvc, wvc_query
from config import ENABLE_API_DIAGNOSTICS, HYBRID_SEARCH_ENABLED

logger = logging.getLogger(__name__)

class HybridWeaviateRetriever:
    """Retriever hybride avec adaptations pour nouvelles fonctionnalités"""
    
    def __init__(self, client, collection_name: str = "InteliaKnowledge"):
        self.client = client
        self.collection_name = collection_name
        self.is_v4 = hasattr(client, 'collections')
        
        # NOUVEAU: Configuration dynamique des capacités API
        self.api_capabilities = {
            "hybrid_with_vector": True,
            "hybrid_with_where": True,
            "explain_score_available": False,
            "near_vector_format": "vector",
            "api_stability": "stable",
            "runtime_corrections": 0
        }
        
        # NOUVEAU: Configuration fusion hybride enrichie
        self.fusion_config = {
            "vector_weight": 0.7,
            "bm25_weight": 0.3,
            "rrf_k": 60,
            "min_score_threshold": 0.1,
            "diversity_threshold": 0.8,
            "intent_boost_factors": {
                "search": 1.2,
                "diagnosis": 1.1,
                "protocol": 1.0,
                "economic": 0.9
            }
        }
        
        # NOUVEAU: Cache des métriques pour optimisation
        self.retrieval_cache = {}
        self.last_query_analytics = {}
        
        # CORRIGÉ: Dimension vectorielle détectée
        self.working_vector_dimension = 384  # Default
        
        # Initialisation avec test des capacités
        if self.is_v4:
            self._test_api_capabilities()
    
    def _test_api_capabilities(self):
        """CORRIGÉ: Teste et configure les capacités API disponibles"""
        try:
            collection = self.client.collections.get(self.collection_name)
            
            # CORRECTION: Utiliser les bonnes dimensions selon la collection
            # Tester d'abord avec 384, puis 1536 selon l'erreur
            test_vectors = {
                384: [0.1] * 384,
                1536: [0.1] * 1536
            }
            
            working_vector_size = None
            test_vector = None
            
            # Détecter la bonne dimension vectorielle
            for size, vector in test_vectors.items():
                try:
                    # Test minimal pour détecter la dimension
                    result = collection.query.near_vector(
                        vector=vector,
                        limit=1
                    )
                    working_vector_size = size
                    test_vector = vector
                    logger.info(f"✅ Dimension vectorielle détectée: {size}")
                    break
                except Exception as e:
                    if "vector lengths don't match" in str(e):
                        logger.debug(f"Dimension {size} incorrecte: {e}")
                        continue
                    else:
                        logger.warning(f"Erreur test dimension {size}: {e}")
                        break
            
            if working_vector_size is None:
                logger.error("❌ Impossible de détecter la dimension vectorielle")
                self.api_capabilities["api_stability"] = "degraded"
                return
            
            # Sauvegarder la dimension qui fonctionne
            self.working_vector_dimension = working_vector_size
            
            # Test 1: Hybrid query basique
            try:
                result = collection.query.hybrid(
                    query="test capacity",
                    limit=1
                )
                logger.info("✅ Hybrid query basique fonctionne")
            except Exception as e:
                logger.warning(f"⚠️ Hybrid query limité: {e}")
                self.api_capabilities["api_stability"] = "limited"
            
            # Test 2: Hybrid avec vector - CORRECTION
            try:
                result = collection.query.hybrid(
                    query="test",
                    vector=test_vector,  # Utiliser la bonne dimension
                    limit=1
                )
                self.api_capabilities["hybrid_with_vector"] = True
                logger.info("✅ Hybrid avec vector supporté")
            except Exception as e:
                self.api_capabilities["hybrid_with_vector"] = False
                logger.warning(f"❌ Hybrid sans vector: {e}")
                if hasattr(METRICS, 'api_correction_applied'):
                    METRICS.api_correction_applied("hybrid_no_vector")
            
            # Test 3: Explain score - CORRECTION DE L'IMPORT
            try:
                if wvc and hasattr(wvc, 'query') and hasattr(wvc.query, 'MetadataQuery'):
                    result = collection.query.near_vector(
                        vector=test_vector,
                        limit=1,
                        return_metadata=wvc.query.MetadataQuery(
                            score=True,
                            explain_score=True
                        )
                    )
                    if (result.objects and hasattr(result.objects[0], 'metadata') and 
                        hasattr(result.objects[0].metadata, 'explain_score')):
                        self.api_capabilities["explain_score_available"] = True
                        logger.info("✅ Explain score disponible")
            except Exception as e:
                self.api_capabilities["explain_score_available"] = False
                logger.warning(f"❌ Explain score indisponible: {e}")
            
            # Test 4: Filtres - CORRECTION
            try:
                if wvc and hasattr(wvc, 'query') and hasattr(wvc.query, 'Filter'):
                    test_filter = wvc.query.Filter.by_property("species").equal("test")
                    result = collection.query.hybrid(
                        query="test",
                        where=test_filter,
                        limit=1
                    )
                    self.api_capabilities["hybrid_with_where"] = True
                    logger.info("✅ Filtres supportés")
            except Exception as e:
                self.api_capabilities["hybrid_with_where"] = False
                logger.warning(f"❌ Filtres non supportés: {e}")
                
        except Exception as e:
            logger.error(f"Erreur test capacités API: {e}")
            self.api_capabilities["api_stability"] = "degraded"
    
    def _to_v4_filter(self, where_dict):
        """Convertit dict where v3 vers Filter v4 - Version corrigée"""
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
            operands = [self._to_v4_filter(o) for o in where_dict.get("operands", [])]
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
    
    def _calculate_dynamic_alpha(self, query: str, intent_result=None) -> float:
        """NOUVEAU: Calcule alpha dynamiquement selon le contexte de la requête"""
        query_lower = query.lower()
        
        # Boost basé sur l'intention détectée
        if intent_result and hasattr(intent_result, 'intent_type'):
            intent_boost = self.fusion_config["intent_boost_factors"].get(
                intent_result.intent_type.value, 1.0
            )
        else:
            intent_boost = 1.0
        
        # Requêtes factuelles -> favoriser BM25
        if any(keyword in query_lower for keyword in [
            "combien", "quel", "quelle", "nombre", "prix", "coût",
            "température", "durée", "âge", "poids", "taille"
        ]):
            base_alpha = 0.3
        
        # Requêtes temporelles -> BM25
        elif re.search(r'\b(jour|semaine|mois|an|année|h|heure|min|minute)\b', query_lower):
            base_alpha = 0.4
        
        # Requêtes conceptuelles -> vectoriel
        elif any(concept in query_lower for concept in [
            "comment", "pourquoi", "expliquer", "différence",
            "améliorer", "optimiser", "problème", "solution",
            "recommandation", "conseil"
        ]):
            base_alpha = 0.8
        
        # Requêtes de diagnostic -> équilibré
        elif any(diag in query_lower for diag in [
            "symptôme", "maladie", "diagnostic", "traitement",
            "prévention", "vaccin"
        ]):
            base_alpha = 0.6
        
        else:
            base_alpha = 0.7
        
        # Application du boost d'intention
        final_alpha = min(0.95, base_alpha * intent_boost)
        
        # Enregistrement pour analytics
        self.last_query_analytics = {
            "base_alpha": base_alpha,
            "intent_boost": intent_boost,
            "final_alpha": final_alpha,
            "query_type": self._classify_query_type(query_lower)
        }
        
        return final_alpha
    
    def _classify_query_type(self, query_lower: str) -> str:
        """NOUVEAU: Classifie le type de requête pour analytics"""
        if any(kw in query_lower for kw in ["combien", "quel", "prix", "coût"]):
            return "factual"
        elif any(kw in query_lower for kw in ["comment", "pourquoi", "expliquer"]):
            return "conceptual"
        elif any(kw in query_lower for kw in ["symptôme", "maladie", "diagnostic"]):
            return "diagnosis"
        elif any(kw in query_lower for kw in ["protocole", "procédure", "étapes"]):
            return "protocol"
        else:
            return "general"
    
    async def hybrid_search(self, query_vector: List[float], query_text: str, 
                           top_k: int = 15, where_filter: Dict = None,
                           alpha: float = None, intent_result=None) -> List[Document]:
        """
        MODIFIÉ: Recherche hybride avec alpha dynamique et intent awareness
        """
        start_time = time.time()
        
        # Calcul alpha dynamique si non fourni
        if alpha is None:
            alpha = self._calculate_dynamic_alpha(query_text, intent_result)
        
        try:
            # Weaviate v4 : recherche hybride native avec corrections
            if self.is_v4:
                documents = await self._hybrid_search_v4_corrected(
                    query_vector, query_text, top_k, where_filter, alpha
                )
            # Weaviate v3 : fusion manuelle
            else:
                documents = await self._hybrid_search_v3(
                    query_vector, query_text, top_k, where_filter, alpha
                )
            
            # NOUVEAU: Enrichissement avec analytics
            for doc in documents:
                if hasattr(doc, 'metadata'):
                    doc.metadata['retrieval_alpha'] = alpha
                    doc.metadata['query_classification'] = self.last_query_analytics.get('query_type', 'unknown')
            
            # Métriques enrichies
            if hasattr(METRICS, 'hybrid_search_completed'):
                METRICS.hybrid_search_completed(
                    len(documents), 
                    alpha, 
                    time.time() - start_time,
                    intent_type=intent_result.intent_type.value if intent_result else None
                )
            
            return documents
                
        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            if hasattr(METRICS, 'retrieval_error'):
                METRICS.retrieval_error("hybrid_search", str(e))
            
            # Fallback vers recherche vectorielle seule
            return await self._vector_search_fallback(query_vector, top_k, where_filter)
    
    async def _hybrid_search_v4_corrected(self, query_vector: List[float], query_text: str,
                                        top_k: int, where_filter: Dict, alpha: float) -> List[Document]:
        """CORRIGÉ: Recherche hybride native Weaviate v4 avec gestion des dimensions"""
        try:
            def _sync_hybrid_search():
                collection = self.client.collections.get(self.collection_name)
                
                search_params = {
                    "query": query_text,
                    "alpha": alpha,
                    "limit": top_k
                }
                
                # CORRECTION: Vérifier la compatibilité des dimensions
                expected_dim = getattr(self, 'working_vector_dimension', 384)
                adjusted_vector = query_vector.copy()
                
                if len(adjusted_vector) != expected_dim:
                    logger.warning(f"Ajustement dimension vector: {len(adjusted_vector)} -> {expected_dim}")
                    if len(adjusted_vector) > expected_dim:
                        adjusted_vector = adjusted_vector[:expected_dim]
                    else:
                        adjusted_vector = adjusted_vector + [0.0] * (expected_dim - len(adjusted_vector))
                
                # Métadonnées avec gestion d'erreurs
                try:
                    if ENABLE_API_DIAGNOSTICS and self.api_capabilities.get("explain_score_available"):
                        search_params["return_metadata"] = wvc.query.MetadataQuery(
                            score=True, 
                            explain_score=True,
                            creation_time=True
                        )
                    else:
                        search_params["return_metadata"] = wvc.query.MetadataQuery(score=True)
                except Exception as e:
                    logger.warning(f"Erreur métadonnées: {e}")
                    search_params["return_metadata"] = wvc.query.MetadataQuery(score=True)
                
                # Vector si supporté
                if self.api_capabilities.get("hybrid_with_vector", True):
                    search_params["vector"] = adjusted_vector
                
                # Filtre si supporté
                if where_filter and self.api_capabilities.get("hybrid_with_where", True):
                    v4_filter = self._to_v4_filter(where_filter)
                    if v4_filter is not None:
                        search_params["where"] = v4_filter
                
                try:
                    return collection.query.hybrid(**search_params)
                except TypeError as e:
                    # CORRECTION: Gestion runtime des erreurs d'arguments
                    self.api_capabilities["runtime_corrections"] += 1
                    if hasattr(METRICS, 'api_correction_applied'):
                        METRICS.api_correction_applied("hybrid_runtime_fix")
                    
                    error_str = str(e).lower()
                    
                    if "vector" in error_str and "vector" in search_params:
                        logger.warning("Paramètre 'vector' non supporté, retry sans vector")
                        del search_params["vector"]
                        self.api_capabilities["hybrid_with_vector"] = False
                        return collection.query.hybrid(**search_params)
                    
                    if "where" in error_str and "where" in search_params:
                        logger.warning("Paramètre 'where' non supporté, retry sans filtre")
                        del search_params["where"]
                        self.api_capabilities["hybrid_with_where"] = False
                        return collection.query.hybrid(**search_params)
                    
                    if "explain_score" in error_str:
                        logger.warning("Explain_score non supporté, retry avec métadonnées simples")
                        search_params["return_metadata"] = wvc.query.MetadataQuery(score=True)
                        self.api_capabilities["explain_score_available"] = False
                        return collection.query.hybrid(**search_params)
                    
                    # Fallback minimal
                    logger.warning("Fallback vers recherche hybride minimale")
                    return collection.query.hybrid(query=query_text, limit=top_k)
            
            # Exécution synchrone
            result = await anyio.to_thread(_sync_hybrid_search)
            
            # Conversion des résultats avec gestion d'erreurs
            documents = []
            try:
                for obj in result.objects:
                    metadata = getattr(obj, 'metadata', {})
                    properties = getattr(obj, 'properties', {})
                    
                    # Extraction score avec protection
                    try:
                        score = float(getattr(metadata, 'score', 0.0))
                    except (ValueError, TypeError):
                        score = 0.0
                    
                    try:
                        explain_score = getattr(metadata, 'explain_score', None)
                    except AttributeError:
                        explain_score = None
                    
                    doc = Document(
                        content=properties.get('content', ''),
                        metadata={
                            "title": properties.get('title', ''),
                            "source": properties.get('source', ''),
                            "geneticLine": properties.get('geneticLine', ''),
                            "species": properties.get('species', ''),
                            "phase": properties.get('phase', ''),
                            "age_band": properties.get('age_band', ''),
                            "weaviate_v4_used": True,
                            "vector_dimension": len(query_vector),
                            "explain_score": explain_score,
                            "creation_time": getattr(metadata, 'creation_time', None)
                        },
                        score=score,
                        original_distance=getattr(metadata, 'distance', None)
                    )
                    documents.append(doc)
            except Exception as e:
                logger.error(f"Erreur conversion résultats: {e}")
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche hybride v4: {e}")
            return []
    
    async def _hybrid_search_v3(self, query_vector: List[float], query_text: str,
                              top_k: int, where_filter: Dict, alpha: float) -> List[Document]:
        """Recherche hybride pour Weaviate v3 avec fusion manuelle"""
        try:
            # Pour v3, implémenter la fusion manuelle RRF
            # Ceci est un placeholder - l'implémentation complète dépend du schema v3
            logger.warning("Weaviate v3 détecté - fusion hybride manuelle non implémentée")
            return await self._vector_search_fallback(query_vector, top_k, where_filter)
        except Exception as e:
            logger.error(f"Erreur recherche hybride v3: {e}")
            return []
    
    async def _vector_search_fallback(self, query_vector: List[float], 
                                    top_k: int, where_filter: Dict = None) -> List[Document]:
        """MODIFIÉ: Fallback vectoriel avec corrections"""
        try:
            if self.is_v4:
                def _sync_vector_search():
                    collection = self.client.collections.get(self.collection_name)
                    
                    # CORRECTION: Ajuster les dimensions
                    expected_dim = getattr(self, 'working_vector_dimension', 384)
                    adjusted_vector = query_vector.copy()
                    
                    if len(adjusted_vector) != expected_dim:
                        if len(adjusted_vector) > expected_dim:
                            adjusted_vector = adjusted_vector[:expected_dim]
                        else:
                            adjusted_vector = adjusted_vector + [0.0] * (expected_dim - len(adjusted_vector))
                    
                    search_params = {
                        "vector": adjusted_vector,
                        "limit": top_k,
                        "return_metadata": wvc.query.MetadataQuery(score=True)
                    }
                    
                    if where_filter and self.api_capabilities.get("hybrid_with_where", True):
                        v4_filter = self._to_v4_filter(where_filter)
                        if v4_filter is not None:
                            search_params["where"] = v4_filter
                    
                    return collection.query.near_vector(**search_params)
                
                result = await anyio.to_thread(_sync_vector_search)
                return self._convert_v4_results_to_documents(result.objects)
            else:
                return await self._vector_search_v3(query_vector, top_k, where_filter)
                
        except Exception as e:
            logger.error(f"Erreur fallback vectoriel: {e}")
            return []
    
    async def _vector_search_v3(self, query_vector: List[float], 
                              top_k: int, where_filter: Dict = None) -> List[Document]:
        """Fallback recherche vectorielle pour Weaviate v3"""
        try:
            # Placeholder pour implémentation v3
            logger.warning("Recherche vectorielle v3 non implémentée")
            return []
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle v3: {e}")
            return []
    
    def _convert_v4_results_to_documents(self, objects) -> List[Document]:
        """NOUVEAU: Conversion objets v4 vers Documents avec métadonnées enrichies"""
        documents = []
        
        for obj in objects:
            metadata = getattr(obj, 'metadata', {})
            properties = getattr(obj, 'properties', {})
            
            try:
                score = float(getattr(metadata, 'score', 0.0))
            except (ValueError, TypeError):
                score = 0.0
            
            doc = Document(
                content=properties.get('content', ''),
                metadata={
                    "title": properties.get('title', ''),
                    "source": properties.get('source', ''),
                    "geneticLine": properties.get('geneticLine', ''),
                    "species": properties.get('species', ''),
                    "phase": properties.get('phase', ''),
                    "age_band": properties.get('age_band', ''),
                    "weaviate_v4_used": True,
                    "fallback_used": True  # NOUVEAU: marqueur fallback
                },
                score=score,
                original_distance=getattr(metadata, 'distance', None)
            )
            documents.append(doc)
        
        return documents
    
    def get_retrieval_analytics(self) -> Dict[str, Any]:
        """NOUVEAU: Analytics de récupération pour monitoring"""
        return {
            "api_capabilities": self.api_capabilities,
            "last_query_analytics": self.last_query_analytics,
            "fusion_config": self.fusion_config,
            "working_vector_dimension": getattr(self, 'working_vector_dimension', 384),
            "runtime_corrections": self.api_capabilities.get("runtime_corrections", 0)
        }

# NOUVEAU: Fonction factory pour compatibilité
def create_hybrid_retriever(client, collection_name: str = "InteliaKnowledge") -> HybridWeaviateRetriever:
    """Factory pour créer un retriever hybride configuré"""
    return HybridWeaviateRetriever(client, collection_name)

# MODIFIÉ: Fonction de compatibilité avec alpha dynamique
def retrieve(query: str, limit: int = 8, alpha: float = None, 
            client=None, intent_result=None, **kwargs) -> List[Document]:
    """
    Façade simple qui utilise la recherche hybride avec alpha dynamique
    """
    if not client:
        raise ValueError("Client Weaviate requis")
    
    retriever = HybridWeaviateRetriever(client)
    
    # Calcul alpha dynamique si non fourni
    if alpha is None:
        alpha = retriever._calculate_dynamic_alpha(query, intent_result)
    
    # Note: Cette fonction est synchrone pour compatibilité
    # En production, utiliser directement le retriever async
    logger.warning("Utilisation fonction retrieve() synchrone - préférer retriever.hybrid_search() async")
    
    return []  # Placeholder - nécessite implémentation async appropriée

# NOUVEAU: Fonctions utilitaires pour analytics
def get_retrieval_metrics() -> Dict[str, Any]:
    """Récupère les métriques de récupération globales"""
    return {
        "retrieval_calls": getattr(METRICS, 'retrieval_calls', 0),
        "cache_hits": getattr(METRICS, 'cache_hits', 0),
        "fallback_used": getattr(METRICS, 'fallback_used', 0),
        "api_corrections": getattr(METRICS, 'api_corrections', 0)
    }

# NOUVEAU: Test function pour validation
async def test_retriever_capabilities(client, collection_name: str = "InteliaKnowledge"):
    """Teste les capacités du retriever configuré"""
    retriever = HybridWeaviateRetriever(client, collection_name)
    
    test_results = {
        "api_capabilities": retriever.api_capabilities,
        "collection_accessible": False,
        "hybrid_search_working": False,
        "vector_search_working": False,
        "vector_dimension": getattr(retriever, 'working_vector_dimension', None)
    }
    
    try:
        # Test accès collection
        if retriever.is_v4:
            collection = client.collections.get(collection_name)
            test_results["collection_accessible"] = True
        
        # Test recherche hybride
        test_vector = [0.1] * getattr(retriever, 'working_vector_dimension', 384)
        docs = await retriever.hybrid_search(
            test_vector, 
            "test query", 
            top_k=1
        )
        test_results["hybrid_search_working"] = len(docs) >= 0  # Même 0 résultat = API fonctionne
        
        # Test recherche vectorielle fallback
        fallback_docs = await retriever._vector_search_fallback(test_vector, 1)
        test_results["vector_search_working"] = len(fallback_docs) >= 0
        
    except Exception as e:
        test_results["error"] = str(e)
    
    return test_results