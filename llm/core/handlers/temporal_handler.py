# -*- coding: utf-8 -*-
"""
Temporal query handler for processing time-range requests
"""

import re
import time
import logging
import traceback
from utils.types import Dict, Any, Optional, Tuple

from config.config import RAG_SIMILARITY_TOP_K
from ..data_models import RAGResult, RAGSource
from .base_handler import BaseQueryHandler

logger = logging.getLogger(__name__)


class TemporalQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes temporelles (plages d'âges)"""

    async def handle(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Traite les requêtes de plage temporelle"""

        query = preprocessed_data["normalized_query"]
        entities = preprocessed_data["entities"]
        language = preprocessed_data.get("language", "fr")

        filters = self._extract_filters_from_entities(entities)

        age_range = self._extract_age_range_from_query(query)
        if not age_range:
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Impossible d'extraire la plage d'âges de la requête.",
                metadata={"error": "age_range_extraction_failed"},
            )

        try:
            logger.info(
                f"Traitement plage temporelle: {age_range[0]}-{age_range[1]} jours (langue={language}, filters={filters})"
            )

            if hasattr(self.postgresql_system, "search_metrics_range"):
                result = await self.postgresql_system.search_metrics_range(
                    query=query,
                    entities=entities,
                    age_min=age_range[0],
                    age_max=age_range[1],
                    top_k=RAG_SIMILARITY_TOP_K,
                    filters=filters,
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    result.metadata.update(
                        {
                            "source_type": "temporal_optimized",
                            "age_range": age_range,
                            "processing_time": time.time() - start_time,
                            "optimization": "single_query_between",
                            "language_used": language,
                            "filters_applied": filters,
                        }
                    )
                    return result

            return await self._handle_temporal_fallback(
                query, entities, age_range, start_time, language, filters
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
        language: str = "fr",
        filters: Dict[str, Any] = None,
    ) -> RAGResult:
        """Fallback: requêtes multiples pour plage temporelle"""

        if filters is None:
            filters = {}

        age_min, age_max = age_range
        results = []

        for age in range(age_min, age_max + 1):
            age_entities = entities.copy()
            age_entities["age_days"] = age

            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=age_entities,
                top_k=3,
                filters=filters,
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
                    "language_used": language,
                    "filters_applied": filters,
                },
            )

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucune donnée trouvée pour cette plage temporelle.",
            metadata={
                "age_range": age_range,
                "language_attempted": language,
                "filters_attempted": filters,
            },
        )
