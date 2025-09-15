# -*- coding: utf-8 -*-
"""
hybrid_retriever.py - Retriever hybride optimisé pour Weaviate
Combine recherche vectorielle et BM25 de façon native et optimisée
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional
import numpy as np
import anyio

logger = logging.getLogger(__name__)

class OptimizedHybridRetriever:
    """Retriever hybride avec fusion optimisée des scores"""
    
    def __init__(self, client, collection_name: str = "InteliaKnowledge"):
        self.client = client
        self.collection_name = collection_name
        self.is_v4 = hasattr(client, 'collections')
        
        # Configuration de fusion hybride
        self.fusion_config = {
            "vector_weight": 0.7,    # Poids recherche vectorielle
            "bm25_weight": 0.3,      # Poids recherche BM25
            "rrf_k": 60,             # Paramètre Reciprocal Rank Fusion
            "min_score_threshold": 0.1,  # Score minimum pour inclusion
            "diversity_threshold": 0.8    # Seuil de similarité pour diversité
        }
    
    async def hybrid_search(self, query_vector: List[float], query_text: str, 
                           top_k: int = 15, where_filter: Dict = None,
                           alpha: float = 0.7) -> List[Dict]:
        """
        Recherche hybride optimisée combinant vector et BM25
        alpha: poids de la recherche vectorielle (0.0 = BM25 pur, 1.0 = vector pur)
        """
        try:
            # Weaviate v4 : recherche hybride native
            if self.is_v4:
                return await self._hybrid_search_v4(
                    query_vector, query_text, top_k, where_filter, alpha
                )
            # Weaviate v3 : fusion manuelle
            else:
                return await self._hybrid_search_v3(
                    query_vector, query_text, top_k, where_filter, alpha
                )
                
        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            # Fallback vers recherche vectorielle seule
            return await self._vector_search_fallback(query_vector, top_k, where_filter)
    
    async def _hybrid_search_v4(self, query_vector: List[float], query_text: str,
                               top_k: int, where_filter: Dict, alpha: float) -> List[Dict]:
        """Recherche hybride native Weaviate v4"""
        try:
            def _sync_hybrid_search():
                import weaviate.classes as wvc
                
                collection = self.client.collections.get(self.collection_name)
                
                # Paramètres de recherche hybride
                search_params = {
                    "query": query_text,
                    "vector": query_vector,
                    "alpha": alpha,  # Fusion automatique par Weaviate
                    "limit": top_k,
                    "return_metadata": ["score", "explain_score"]
                }
                
                # Ajouter les filtres si présents
                if where_filter:
                    v4_filter = self._convert_to_v4_filter(where_filter)
                    if v4_filter:
                        search_params["where"] = v4_filter
                
                return collection.query.hybrid(**search_params)
            
            response = await anyio.to_thread.run_sync(_sync_hybrid_search)
            
            documents = []
            for obj in response.objects:
                # Score hybride fourni par Weaviate
                hybrid_score = float(getattr(obj.metadata, "score", 0.0))
                
                # Explication du score si disponible
                explain_score = getattr(obj.metadata, "explain_score", None)
                
                doc = {
                    "content": obj.properties.get("content", ""),
                    "metadata": {
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "phase": obj.properties.get("phase", ""),
                        "age_band": obj.properties.get("age_band", ""),
                        "hybrid_used": True,
                        "alpha": alpha,
                        "explain_score": explain_score
                    },
                    "score": hybrid_score,
                    "search_type": "hybrid_native_v4"
                }
                documents.append(doc)
            
            logger.debug(f"Recherche hybride v4: {len(documents)} documents (alpha={alpha})")
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche hybride v4: {e}")
            raise
    
    async def _hybrid_search_v3(self, query_vector: List[float], query_text: str,
                               top_k: int, where_filter: Dict, alpha: float) -> List[Dict]:
        """Recherche hybride manuelle pour Weaviate v3"""
        try:
            # Lancer recherche vectorielle et BM25 en parallèle
            vector_task = self._vector_search_v3(query_vector, top_k * 2, where_filter)
            bm25_task = self._bm25_search_v3(query_text, top_k * 2, where_filter)
            
            vector_results, bm25_results = await asyncio.gather(
                vector_task, bm25_task, return_exceptions=True
            )
            
            # Gérer les erreurs
            if isinstance(vector_results, Exception):
                logger.warning(f"Erreur recherche vectorielle: {vector_results}")
                vector_results = []
            if isinstance(bm25_results, Exception):
                logger.warning(f"Erreur recherche BM25: {bm25_results}")
                bm25_results = []
            
            # fusion RRF/pondérée (existant)
            fused_results = self._fuse_results(
                vector_results, bm25_results, alpha, top_k
            )
            
            logger.debug("hybrid_retriever: alpha=%.2f bm25=%d vector=%d fused=%d",
                         alpha, len(bm25_results), len(vector_results), len(fused_results))
            
            # Diversité: remove quasi-duplicates (cosine or hash on content)
            deduped: List[Dict] = []
            seen: set = set()
            for it in fused_results:
                key = (it.get("doc_id") or "")[:64] + "|" + (it.get("title") or "")[:64]
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(it)
            
            return deduped[:top_k]
            
        except Exception as e:
            logger.error(f"Erreur recherche hybride v3: {e}")
            raise
    
    def _fuse_results(self, vector_results: List[Dict], bm25_results: List[Dict],
                     alpha: float, top_k: int) -> List[Dict]:
        """Fusion avancée des résultats avec RRF et normalisation"""
        try:
            # Indexer par contenu pour déduplication
            all_docs = {}
            
            # Traiter les résultats vectoriels
            for i, doc in enumerate(vector_results):
                content_key = doc.get("content", "")[:100]  # Clé basée sur début du contenu
                
                if content_key not in all_docs:
                    all_docs[content_key] = {
                        "doc": doc,
                        "vector_rank": i + 1,
                        "vector_score": doc.get("score", 0.0),
                        "bm25_rank": None,
                        "bm25_score": 0.0
                    }
            
            # Traiter les résultats BM25
            for i, doc in enumerate(bm25_results):
                content_key = doc.get("content", "")[:100]
                
                if content_key in all_docs:
                    all_docs[content_key]["bm25_rank"] = i + 1
                    all_docs[content_key]["bm25_score"] = doc.get("score", 0.0)
                else:
                    # Document trouvé uniquement par BM25
                    all_docs[content_key] = {
                        "doc": doc,
                        "vector_rank": None,
                        "vector_score": 0.0,
                        "bm25_rank": i + 1,
                        "bm25_score": doc.get("score", 0.0)
                    }
            
            # Calcul du score hybride avec RRF (Reciprocal Rank Fusion)
            fused_docs = []
            for content_key, data in all_docs.items():
                doc = data["doc"]
                
                # Score RRF
                rrf_score = 0.0
                if data["vector_rank"]:
                    rrf_score += alpha / (self.fusion_config["rrf_k"] + data["vector_rank"])
                if data["bm25_rank"]:
                    rrf_score += (1 - alpha) / (self.fusion_config["rrf_k"] + data["bm25_rank"])
                
                # Score normalisé pondéré (alternative)
                normalized_score = (
                    alpha * data["vector_score"] + 
                    (1 - alpha) * data["bm25_score"]
                )
                
                # Utiliser le maximum des deux méthodes pour robustesse
                final_score = max(rrf_score * 10, normalized_score)  # *10 pour calibrer RRF
                
                if final_score >= self.fusion_config["min_score_threshold"]:
                    # Enrichir les métadonnées
                    if "metadata" not in doc:
                        doc["metadata"] = {}
                    
                    doc["metadata"].update({
                        "hybrid_used": True,
                        "fusion_method": "rrf_weighted",
                        "alpha": alpha,
                        "vector_rank": data["vector_rank"],
                        "bm25_rank": data["bm25_rank"],
                        "vector_score": data["vector_score"],
                        "bm25_score": data["bm25_score"],
                        "rrf_score": rrf_score,
                        "normalized_score": normalized_score
                    })
                    
                    doc["score"] = final_score
                    doc["search_type"] = "hybrid_manual_v3"
                    fused_docs.append(doc)
            
            # Trier par score final et appliquer diversité
            fused_docs.sort(key=lambda x: x["score"], reverse=True)
            diversified_docs = self._apply_diversity_filter(fused_docs)
            
            return diversified_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Erreur fusion résultats: {e}")
            # Fallback : retourner les résultats vectoriels
            return vector_results[:top_k] if vector_results else bm25_results[:top_k]
    
    def _apply_diversity_filter(self, documents: List[Dict]) -> List[Dict]:
        """Applique un filtre de diversité pour éviter les doublons sémantiques"""
        if len(documents) <= 3:
            return documents
        
        try:
            diversified = [documents[0]]  # Garder le premier (meilleur score)
            
            for candidate in documents[1:]:
                is_diverse = True
                candidate_content = candidate.get("content", "").lower()
                candidate_words = set(candidate_content.split())
                
                for selected in diversified:
                    selected_content = selected.get("content", "").lower()
                    selected_words = set(selected_content.split())
                    
                    if candidate_words and selected_words:
                        overlap = len(candidate_words.intersection(selected_words))
                        similarity = overlap / min(len(candidate_words), len(selected_words))
                        
                        if similarity > self.fusion_config["diversity_threshold"]:
                            is_diverse = False
                            break
                
                if is_diverse:
                    diversified.append(candidate)
                    
                # Limiter pour éviter une liste trop réduite
                if len(diversified) >= len(documents) * 0.7:
                    break
            
            return diversified
            
        except Exception as e:
            logger.warning(f"Erreur filtre diversité: {e}")
            return documents
    
    async def _vector_search_fallback(self, query_vector: List[float], 
                                    top_k: int, where_filter: Dict) -> List[Dict]:
        """Recherche vectorielle de fallback"""
        try:
            if self.is_v4:
                return await self._vector_search_v4(query_vector, top_k, where_filter)
            else:
                return await self._vector_search_v3(query_vector, top_k, where_filter)
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle fallback: {e}")
            return []
    
    def _convert_to_v4_filter(self, where_dict):
        """Convertit les filtres v3 vers v4 (réutilise la logique existante)"""
        if not where_dict:
            return None
        
        try:
            import weaviate.classes as wvc
            
            # Cas simple : propriété unique
            if "path" in where_dict:
                property_name = where_dict["path"][-1] if isinstance(where_dict["path"], list) else where_dict["path"]
                operator = where_dict.get("operator", "Equal")
                value = where_dict.get("valueText", where_dict.get("valueString", ""))
                
                if operator == "Like":
                    return wvc.query.Filter.by_property(property_name).like(value)
                else:
                    return wvc.query.Filter.by_property(property_name).equal(value)
            
            # Cas composé
            operator = where_dict.get("operator", "And").lower()
            operands = [self._convert_to_v4_filter(o) for o in where_dict.get("operands", [])]
            operands = [op for op in operands if op is not None]
            
            if not operands:
                return None
            
            if len(operands) == 1:
                return operands[0]
            
            if operator == "and":
                result = operands[0]
                for op in operands[1:]:
                    result = result & op
                return result
            elif operator == "or":
                result = operands[0]
                for op in operands[1:]:
                    result = result | op
                return result
            
            return operands[0]
            
        except Exception as e:
            logger.warning(f"Erreur conversion filter v4: {e}")
            return None
    
    async def adaptive_search(self, query_vector: List[float], query_text: str,
                            top_k: int = 15, where_filter: Dict = None) -> List[Dict]:
        """
        Recherche adaptative qui ajuste alpha selon la nature de la requête
        """
        try:
            # Analyse de la requête pour déterminer l'alpha optimal
            alpha = self._analyze_query_for_alpha(query_text)
            
            logger.debug(f"Recherche adaptative avec alpha={alpha} pour: {query_text[:50]}...")
            
            return await self.hybrid_search(
                query_vector, query_text, top_k, where_filter, alpha
            )
            
        except Exception as e:
            logger.error(f"Erreur recherche adaptative: {e}")
            return await self._vector_search_fallback(query_vector, top_k, where_filter)
    
    def _analyze_query_for_alpha(self, query_text: str) -> float:
        """Analyse la requête pour déterminer l'alpha optimal"""
        try:
            query_lower = query_text.lower()
            
            # Requêtes très spécifiques (noms, codes) -> favoriser BM25
            if any(pattern in query_lower for pattern in [
                "ross", "cobb", "hubbard", "isa", "lohmann",  # Lignées
                "fcr", "pv", "gmd",  # Acronymes
                "j0", "j7", "j21", "j35"  # Codes temporels
            ]):
                return 0.3  # Favoriser BM25
            
            # Requêtes numériques spécifiques -> équilibré vers BM25
            import re
            if re.search(r'\d+\s*(g|kg|%|jour|j)', query_lower):
                return 0.4
            
            # Requêtes conceptuelles -> favoriser vectoriel
            if any(concept in query_lower for concept in [
                "comment", "pourquoi", "expliquer", "différence",
                "améliorer", "optimiser", "problème", "solution"
            ]):
                return 0.8  # Favoriser vectoriel
            
            # Requêtes de performance mixtes -> équilibré
            if any(perf in query_lower for perf in [
                "performance", "résultat", "objectif", "norme"
            ]):
                return 0.6
            
            # Par défaut : léger avantage au vectoriel
            return 0.7
            
        except Exception as e:
            logger.warning(f"Erreur analyse alpha: {e}")
            return 0.7  # Valeur par défaut
    
    def get_fusion_stats(self) -> Dict:
        """Retourne les statistiques de configuration de fusion"""
        return {
            "fusion_config": self.fusion_config,
            "weaviate_version": "v4" if self.is_v4 else "v3",
            "native_hybrid_support": self.is_v4,
            "fusion_methods": [
                "reciprocal_rank_fusion",
                "weighted_score_normalization", 
                "diversity_filtering",
                "adaptive_alpha_selection"
            ]
        }