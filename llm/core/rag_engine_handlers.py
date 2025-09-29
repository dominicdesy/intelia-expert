# -*- coding: utf-8 -*-
"""
rag_engine_handlers.py - Handlers spécialisés pour différents types de requêtes
VERSION CORRIGÉE : Compatible avec la structure harmonisée du comparison_handler
"""

import re
import time
import logging
import traceback
from typing import Dict, Any, Optional, Tuple

from config.config import RAG_SIMILARITY_TOP_K
from .data_models import RAGResult, RAGSource

logger = logging.getLogger(__name__)


class BaseQueryHandler:
    """Handler de base avec fonctionnalités communes"""

    def __init__(self):
        self.postgresql_system = None
        self.weaviate_core = None

    def configure(self, **kwargs):
        """Configure le handler avec les modules nécessaires"""
        for key, value in kwargs.items():
            setattr(self, key, value)


class ComparativeQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes comparatives"""

    def configure(self, **kwargs):
        """Configure avec ComparisonHandler"""
        super().configure(**kwargs)
        self.comparison_handler = kwargs.get("comparison_handler")

    async def handle(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Traite les requêtes comparatives"""

        if not self.comparison_handler:
            logger.warning("ComparisonHandler non disponible, fallback vers standard")
            return await self._fallback_to_standard(preprocessed_data, start_time)

        try:
            logger.info("Executing comparative query via ComparisonHandler")

            # Appel au ComparisonHandler
            comparison_result = await self.comparison_handler.handle_comparison_query(
                preprocessed_data
            )

            if not comparison_result["success"]:
                error_msg = comparison_result.get(
                    "error", "Erreur comparative inconnue"
                )
                logger.warning(f"Comparison failed: {error_msg}")

                # Fallback intelligent vers requête standard
                return await self._fallback_to_standard(preprocessed_data, start_time)

            # Succès: générer la réponse comparative
            answer_text = await self.comparison_handler.generate_comparative_response(
                preprocessed_data.get(
                    "original_query", preprocessed_data["normalized_query"]
                ),
                comparison_result,
                "fr",
            )

            # 🔧 CORRECTION: Accès sécurisé aux métadonnées
            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=self._extract_comparison_documents(comparison_result),
                confidence=0.95,
                metadata={
                    "source_type": "comparative",
                    "comparison_type": comparison_result.get("comparison_type"),
                    "operation": comparison_result.get("operation"),
                    "entities_compared": comparison_result.get("metadata", {}).get(
                        "entities_compared", 2
                    ),
                    "processing_time": time.time() - start_time,
                    "result_count": len(comparison_result.get("results", [])),
                    "preprocessing_applied": comparison_result.get("metadata", {}).get(
                        "preprocessing_applied", False
                    ),
                },
            )

        except ValueError as ve:
            logger.error(f"ValueError in comparative handling: {ve}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            return RAGResult(
                source=RAGSource.ERROR,
                answer=f"Erreur de comparaison: {str(ve)}",
                metadata={
                    "source_type": "comparative_error",
                    "error_type": "ValueError",
                    "error_message": str(ve),
                    "processing_time": time.time() - start_time,
                },
            )

        except ZeroDivisionError as zde:
            logger.error(f"ZeroDivisionError in comparative handling: {zde}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur de comparaison: division par zéro détectée. Les métriques comparées contiennent des valeurs nulles.",
                metadata={
                    "source_type": "comparative_error",
                    "error_type": "ZeroDivisionError",
                    "error_message": str(zde),
                    "processing_time": time.time() - start_time,
                },
            )

        except Exception as e:
            logger.error("Critical error in comparative handling")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error(f"Error args: {e.args}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")

            return await self._fallback_to_standard(preprocessed_data, start_time)

    async def _fallback_to_standard(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Fallback vers traitement standard"""

        entities = preprocessed_data.get("entities", {})
        query = preprocessed_data["normalized_query"]

        if self.postgresql_system and entities:
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=entities,
                top_k=RAG_SIMILARITY_TOP_K,
            )

            if result and result.source != RAGSource.NO_RESULTS:
                result.metadata.update(
                    {
                        "source_type": "comparative_fallback",
                        "fallback_applied": True,
                        "processing_time": time.time() - start_time,
                    }
                )
                return result

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Impossible de traiter cette demande de comparaison.",
            metadata={
                "source_type": "comparative_error",
                "processing_time": time.time() - start_time,
            },
        )

    def _extract_comparison_documents(self, comparison_result: Dict) -> list:
        """
        Extrait les documents des résultats de comparaison
        Compatible avec la nouvelle structure harmonisée
        """
        try:
            documents = []
            results = comparison_result.get("results", [])

            # Nouvelle structure: Liste de dicts avec "all_docs"
            for result_item in results:
                if isinstance(result_item, dict):
                    # Format harmonisé avec all_docs
                    if "all_docs" in result_item:
                        documents.extend(result_item["all_docs"])
                    # Ancien format avec context_docs
                    elif "context_docs" in result_item:
                        documents.extend(result_item["context_docs"])

            logger.debug(f"Extracted {len(documents)} comparison documents")
            return documents

        except Exception as e:
            logger.warning(f"Erreur extraction documents comparatifs: {e}")
            return []


class TemporalQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes temporelles (plages d'âges)"""

    async def handle(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Traite les requêtes de plage temporelle"""

        query = preprocessed_data["normalized_query"]
        entities = preprocessed_data["entities"]

        age_range = self._extract_age_range_from_query(query)
        if not age_range:
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Impossible d'extraire la plage d'âges de la requête.",
                metadata={"error": "age_range_extraction_failed"},
            )

        try:
            logger.info(
                f"Traitement plage temporelle: {age_range[0]}-{age_range[1]} jours"
            )

            if hasattr(self.postgresql_system, "search_metrics_range"):
                result = await self.postgresql_system.search_metrics_range(
                    query=query,
                    entities=entities,
                    age_min=age_range[0],
                    age_max=age_range[1],
                    top_k=RAG_SIMILARITY_TOP_K,
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    result.metadata.update(
                        {
                            "source_type": "temporal_optimized",
                            "age_range": age_range,
                            "processing_time": time.time() - start_time,
                            "optimization": "single_query_between",
                        }
                    )
                    return result

            return await self._handle_temporal_fallback(
                query, entities, age_range, start_time
            )

        except Exception as e:
            logger.error(f"Erreur traitement temporel: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors du traitement de la requête temporelle.",
                metadata={"error": str(e)},
            )

    def _extract_age_range_from_query(self, query: str) -> Optional[Tuple[int, int]]:
        """Extrait la plage d'âges d'une requête"""
        patterns = [
            r"entre\s+(\d+)\s+et\s+(\d+)\s+jours?",
            r"de\s+(\d+)\s+à\s+(\d+)\s+jours?",
            r"du\s+jour\s+(\d+)\s+au\s+jour\s+(\d+)",
            r"(\d+)\s*-\s*(\d+)\s+jours?",
            r"between\s+(\d+)\s+and\s+(\d+)\s+days?",
        ]

        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                age_min = int(match.group(1))
                age_max = int(match.group(2))
                return (age_min, age_max)

        return None

    async def _handle_temporal_fallback(
        self,
        query: str,
        entities: Dict[str, Any],
        age_range: Tuple[int, int],
        start_time: float,
    ) -> RAGResult:
        """Fallback: requêtes multiples pour plage temporelle"""

        age_min, age_max = age_range
        results = []

        for age in range(age_min, age_max + 1):
            age_entities = entities.copy()
            age_entities["age_days"] = age

            result = await self.postgresql_system.search_metrics(
                query=query, entities=age_entities, top_k=3
            )

            if result and result.context_docs:
                results.extend(result.context_docs)

        if results:
            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                context_docs=results,
                metadata={
                    "source_type": "temporal_multiple_queries",
                    "age_range": age_range,
                    "queries_executed": age_max - age_min + 1,
                    "processing_time": time.time() - start_time,
                },
            )

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucune donnée trouvée pour cette plage temporelle.",
            metadata={"age_range": age_range},
        )


class StandardQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes standard"""

    async def handle(
        self,
        preprocessed_data: Dict[str, Any],
        start_time: float,
        original_query: str = None,
        tenant_id: str = None,
        conversation_context: list = None,
        language: str = "fr",
        **kwargs,
    ) -> RAGResult:
        """Traite les requêtes standard avec fallback intelligent"""

        query = preprocessed_data["normalized_query"]
        entities = preprocessed_data["entities"]
        routing_hint = preprocessed_data.get("routing_hint")

        if original_query is None:
            original_query = preprocessed_data.get("original_query", query)

        # PostgreSQL avec hint prioritaire
        if routing_hint == "postgresql" and self.postgresql_system:
            logger.info("Routage PostgreSQL (preprocessing hint)")
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=entities,
                top_k=RAG_SIMILARITY_TOP_K,
                strict_sex_match=False,
            )

            if result and result.source != RAGSource.NO_RESULTS:
                return result

        # PostgreSQL standard
        if self.postgresql_system:
            logger.info("Recherche PostgreSQL standard")
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=entities,
                top_k=RAG_SIMILARITY_TOP_K,
            )

            if result and result.source != RAGSource.NO_RESULTS:
                return result

        # Weaviate si disponible
        if self.weaviate_core:
            logger.info("Recherche Weaviate fallback")
            result = await self.weaviate_core.search(
                query=query,
                top_k=RAG_SIMILARITY_TOP_K,
            )

            if result and result.source != RAGSource.NO_RESULTS:
                return result

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucune information trouvée pour cette requête.",
            metadata={"query_type": "standard"},
        )
