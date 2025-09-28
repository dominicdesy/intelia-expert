# -*- coding: utf-8 -*-
"""
retriever_search.py - Méthodes de recherche hybride avec améliorations
VERSION AMÉLIORÉE avec gestion d'erreur robuste
"""

import logging
import time
from typing import Dict, List
from core.data_models import Document
from utils.utilities import METRICS
from utils.imports_and_dependencies import wvc

logger = logging.getLogger(__name__)


class SearchMixin:
    """Mixin contenant les méthodes de recherche pour HybridWeaviateRetriever"""

    async def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int = 15,
        where_filter: Dict = None,
        alpha: float = None,
        intent_result=None,
    ) -> List[Document]:
        """Recherche hybride principale avec gestion d'erreurs robuste"""
        start_time = time.time()

        # S'assurer que la dimension est détectée
        await self._ensure_dimension_detected()

        # Ajuster les dimensions du vecteur
        adjusted_vector = self._adjust_vector_dimension(query_vector)

        # Calcul alpha dynamique si non fourni
        if alpha is None:
            alpha = self._calculate_dynamic_alpha(query_text, intent_result)

        try:
            if self.is_v4:
                documents = await self._hybrid_search_v4_corrected(
                    adjusted_vector, query_text, top_k, where_filter, alpha
                )
            else:
                documents = await self._hybrid_search_v3(
                    adjusted_vector, query_text, top_k, where_filter, alpha
                )

            # Métriques enrichies
            if hasattr(METRICS, "hybrid_search_completed"):
                METRICS.hybrid_search_completed(
                    len(documents),
                    alpha,
                    time.time() - start_time,
                    intent_type=self._safe_extract_intent_type(intent_result),
                )

            return documents

        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            if hasattr(METRICS, "retrieval_error"):
                METRICS.retrieval_error("hybrid_search", str(e))

            # Fallback vers recherche vectorielle seule
            return await self._vector_search_fallback(
                adjusted_vector, top_k, where_filter
            )

    async def _hybrid_search_v4_corrected(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int,
        where_filter: Dict,
        alpha: float,
    ) -> List[Document]:
        """Recherche hybride avec gestion d'erreur améliorée"""
        try:
            collection = self.client.collections.get(self.collection_name)

            search_params = {
                "query": query_text,
                "alpha": alpha,
                "limit": top_k,
                "return_metadata": wvc.query.MetadataQuery(score=True),
            }

            # Ajouter vector seulement si supporté
            if self.api_capabilities.get("hybrid_with_vector", True):
                search_params["vector"] = query_vector

            # Ajouter filtre seulement si supporté
            if where_filter and self.api_capabilities.get("hybrid_with_where", True):
                v4_filter = self._to_v4_filter(where_filter)
                if v4_filter is not None:
                    search_params["where"] = v4_filter

            try:
                result = collection.query.hybrid(**search_params)
            except TypeError as e:
                # Gestion runtime des erreurs d'arguments
                self.api_capabilities["runtime_corrections"] += 1
                if hasattr(METRICS, "api_correction_applied"):
                    METRICS.api_correction_applied("hybrid_runtime_fix")

                error_str = str(e).lower()
                if "vector" in error_str and "vector" in search_params:
                    logger.warning("Paramètre 'vector' non supporté, retry sans vector")
                    del search_params["vector"]
                    self.api_capabilities["hybrid_with_vector"] = False
                    result = collection.query.hybrid(**search_params)
                elif "where" in error_str and "where" in search_params:
                    logger.warning("Paramètre 'where' non supporté, retry sans filtre")
                    del search_params["where"]
                    self.api_capabilities["hybrid_with_where"] = False
                    result = collection.query.hybrid(**search_params)
                else:
                    # Fallback minimal
                    logger.warning("Fallback vers recherche hybride minimale")
                    result = collection.query.hybrid(query=query_text, limit=top_k)

            # Conversion résultats avec protection d'erreur
            documents = []
            for obj in result.objects:
                try:
                    metadata = getattr(obj, "metadata", {})
                    properties = getattr(obj, "properties", {})
                    score = float(getattr(metadata, "score", 0.0))

                    doc = Document(
                        content=properties.get("content", ""),
                        metadata={
                            "title": properties.get("title", ""),
                            "source": properties.get("source", ""),
                            "geneticLine": properties.get("geneticLine", ""),
                            "species": properties.get("species", ""),
                            "phase": properties.get("phase", ""),
                            "age_band": properties.get("age_band", ""),
                            "weaviate_v4_used": True,
                            "vector_dimension": len(query_vector),
                            "retriever_version": "corrected_v4",
                            **properties,
                        },
                        score=score,
                        original_distance=getattr(metadata, "distance", None),
                    )
                    documents.append(doc)
                except Exception as e:
                    logger.warning(f"Erreur conversion objet: {e}")
                    continue

            return documents

        except Exception as e:
            logger.error(f"Erreur recherche hybride v4: {e}")
            return []

    async def _hybrid_search_v3(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int,
        where_filter: Dict,
        alpha: float,
    ) -> List[Document]:
        """Recherche hybride pour Weaviate v3 avec fusion manuelle"""
        try:
            # Pour v3, implémenter la fusion manuelle RRF
            logger.warning(
                "Weaviate v3 détecté - fusion hybride manuelle non implémentée"
            )
            return await self._vector_search_fallback(query_vector, top_k, where_filter)
        except Exception as e:
            logger.error(f"Erreur recherche hybride v3: {e}")
            return []

    async def _vector_search_fallback(
        self, query_vector: List[float], top_k: int, where_filter: Dict = None
    ) -> List[Document]:
        """Fallback vectoriel avec syntaxe v4 corrigée"""
        try:
            if self.is_v4:
                collection = self.client.collections.get(self.collection_name)

                # S'assurer de la bonne dimension
                adjusted_vector = self._adjust_vector_dimension(query_vector)

                # Syntaxe v4 pour near_vector
                try:
                    # Construire les paramètres optionnels
                    optional_params = {
                        "limit": top_k,
                        "return_metadata": wvc.query.MetadataQuery(score=True),
                    }

                    # Ajouter le filtre si disponible
                    if where_filter and self.api_capabilities.get(
                        "hybrid_with_where", True
                    ):
                        v4_filter = self._to_v4_filter(where_filter)
                        if v4_filter is not None:
                            optional_params["where"] = v4_filter

                    # Appel avec syntaxe v4 - vector en paramètre positionnel
                    result = collection.query.near_vector(
                        adjusted_vector,
                        **optional_params,
                    )

                except Exception as e:
                    logger.warning(f"Erreur near_vector avec filtres: {e}")
                    # Fallback sans filtres
                    result = collection.query.near_vector(
                        adjusted_vector,
                        limit=top_k,
                        return_metadata=wvc.query.MetadataQuery(score=True),
                    )

                return self._convert_v4_results_to_documents(result.objects)
            else:
                return await self._vector_search_v3(query_vector, top_k, where_filter)

        except Exception as e:
            logger.error(f"Erreur fallback vectoriel: {e}")
            return []

    async def _vector_search_v3(
        self, query_vector: List[float], top_k: int, where_filter: Dict = None
    ) -> List[Document]:
        """Fallback recherche vectorielle pour Weaviate v3"""
        try:
            logger.warning("Recherche vectorielle v3 non implémentée")
            return []
        except Exception as e:
            logger.error(f"Erreur recherche vectorielle v3: {e}")
            return []

    def _convert_v4_results_to_documents(self, objects) -> List[Document]:
        """Conversion objets v4 vers Documents avec métadonnées enrichies"""
        documents = []

        for obj in objects:
            metadata = getattr(obj, "metadata", {})
            properties = getattr(obj, "properties", {})

            try:
                score = float(getattr(metadata, "score", 0.0))
            except (ValueError, TypeError):
                score = 0.0

            doc = Document(
                content=properties.get("content", ""),
                metadata={
                    "title": properties.get("title", ""),
                    "source": properties.get("source", ""),
                    "geneticLine": properties.get("geneticLine", ""),
                    "species": properties.get("species", ""),
                    "phase": properties.get("phase", ""),
                    "age_band": properties.get("age_band", ""),
                    "weaviate_v4_used": True,
                    "fallback_used": True,
                    "vector_dimension": self.working_vector_dimension,
                    "retriever_version": "corrected_fallback",
                },
                score=score,
                original_distance=getattr(metadata, "distance", None),
            )
            documents.append(doc)

        return documents
