# -*- coding: utf-8 -*-
"""
rag_engine_handlers.py - Handlers spécialisés pour différents types de requêtes
"""

import re
import time
import logging
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


class TemporalQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes temporelles (plages d'âges)"""

    async def handle(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Traite les requêtes de plage temporelle"""

        query = preprocessed_data["normalized_query"]
        entities = preprocessed_data["entities"]

        # Extraire la plage d'âges
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

            # Utiliser la méthode optimisée si disponible
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

            # Fallback vers méthode multiple
            return await self._handle_temporal_fallback(
                query, entities, age_range, start_time
            )

        except Exception as e:
            logger.error(f"Erreur traitement temporel: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors du traitement de la requête temporelle.",
                metadata={"error": str(e), "processing_time": time.time() - start_time},
            )

    def _extract_age_range_from_query(self, query: str) -> Optional[Tuple[int, int]]:
        """Extrait plage d'âges de la requête"""
        patterns = [
            r"entre\s+(\d+)\s+et\s+(\d+)\s+jours?",
            r"de\s+(\d+)\s+à\s+(\d+)\s+jours?",
            r"(\d+)\s*-\s*(\d+)\s+jours?",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                age_min, age_max = int(match.group(1)), int(match.group(2))
                if 0 <= age_min <= age_max <= 150:
                    return (age_min, age_max)
        return None

    async def _handle_temporal_fallback(
        self, query: str, entities: Dict, age_range: Tuple[int, int], start_time: float
    ) -> RAGResult:
        """Fallback pour plages temporelles"""

        results = []
        successful_ages = []

        # Rechercher pour chaque âge dans la plage (limitée)
        step = max(1, (age_range[1] - age_range[0]) // 5)  # Max 5 points
        for age in range(age_range[0], age_range[1] + 1, step):
            entities_age = entities.copy()
            entities_age["age_days"] = age

            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=entities_age,
                top_k=3,
            )

            if result and result.source != RAGSource.NO_RESULTS:
                results.append({"age": age, "result": result})
                successful_ages.append(age)

        if not results:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                answer=f"Aucune donnée trouvée pour la plage d'âges {age_range[0]}-{age_range[1]} jours.",
                metadata={
                    "source_type": "temporal_fallback",
                    "age_range": age_range,
                    "processing_time": time.time() - start_time,
                },
            )

        # Générer réponse temporelle
        answer = self._generate_temporal_response(results, age_range)

        return RAGResult(
            source=RAGSource.RAG_SUCCESS,
            answer=answer,
            context_docs=[],
            confidence=0.85,
            metadata={
                "source_type": "temporal_fallback",
                "age_range": age_range,
                "successful_ages": successful_ages,
                "data_points": len(results),
                "processing_time": time.time() - start_time,
            },
        )

    def _generate_temporal_response(
        self, results: list, age_range: Tuple[int, int]
    ) -> str:
        """Génère une réponse pour les requêtes temporelles"""

        if len(results) == 1:
            age = results[0]["age"]
            return f"Pour {age} jours : {results[0]['result'].answer}"

        # Multi-âges : créer un résumé
        response_parts = [
            f"Évolution sur la période {age_range[0]}-{age_range[1]} jours :"
        ]

        for result_data in results:
            age = result_data["age"]
            answer = result_data["result"].answer
            if answer and len(answer) < 100:  # Résumé court
                response_parts.append(f"- {age} jours : {answer}")

        return "\n".join(response_parts)


class ComparativeQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes comparatives"""

    def __init__(self):
        super().__init__()
        self.comparison_handler = None

    def configure(self, **kwargs):
        """Configure avec le comparison handler"""
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

            comparison_result = await self.comparison_handler.handle_comparative_query(
                preprocessed_data["normalized_query"],
                preprocessed_data,
                top_k=RAG_SIMILARITY_TOP_K,
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

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=self._extract_comparison_documents(comparison_result),
                confidence=0.95,
                metadata={
                    "source_type": "comparative",
                    "comparison_type": comparison_result.get("comparison_type"),
                    "operation": comparison_result.get("operation"),
                    "entities_compared": comparison_result["metadata"][
                        "entities_compared"
                    ],
                    "successful_queries": comparison_result["metadata"][
                        "successful_queries"
                    ],
                    "processing_time": time.time() - start_time,
                    "result_count": len(comparison_result["results"]),
                },
            )

        except Exception as e:
            logger.error(f"Critical error in comparative handling: {e}")
            return await self._fallback_to_standard(preprocessed_data, start_time)

    async def _fallback_to_standard(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Fallback vers traitement standard"""

        # Extraire la première entité pour requête standard
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
        """Extrait les documents des résultats de comparaison"""
        try:
            documents = []
            if "results" in comparison_result:
                for result_set in comparison_result["results"]:
                    if isinstance(result_set, dict) and "context_docs" in result_set:
                        documents.extend(result_set["context_docs"])
            return documents
        except Exception as e:
            logger.warning(f"Erreur extraction documents comparatifs: {e}")
            return []


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

        # Utiliser original_query si fourni, sinon fallback sur normalized_query
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
            try:
                logger.info("Tentative Weaviate")
                result = await self.weaviate_core.generate_response(
                    query=original_query,
                    tenant_id=tenant_id,
                    conversation_context=conversation_context,
                    language=language,
                    **kwargs,
                )

                if result and result.source != RAGSource.INTERNAL_ERROR:
                    logger.info("Weaviate fallback réussi")
                    return result
                else:
                    logger.warning("Weaviate fallback échoué")

            except AttributeError as e:
                logger.warning(f"Erreur Weaviate: {e}")
                # Fallback gracieux
            except Exception as e:
                logger.error(f"Erreur inattendue Weaviate: {e}")

        # Aucun résultat trouvé
        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucun résultat trouvé.",
            metadata={
                "processing_time": time.time() - start_time,
                "sources_tried": [
                    "postgresql" if self.postgresql_system else None,
                    "weaviate" if self.weaviate_core else None,
                ],
            },
        )
