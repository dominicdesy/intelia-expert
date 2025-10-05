# -*- coding: utf-8 -*-
"""
Comparative query handler for processing comparison requests
"""

import time
import logging
import traceback
from utils.types import Dict, Any

from config.config import RAG_SIMILARITY_TOP_K
from ..data_models import RAGResult, RAGSource
from .base_handler import BaseQueryHandler

logger = logging.getLogger(__name__)


class ComparativeQueryHandler(BaseQueryHandler):
    """Handler pour les requêtes comparatives"""

    def configure(self, **kwargs):
        """Configure avec ComparisonHandler"""
        super().configure(**kwargs)
        self.comparison_handler = kwargs.get("comparison_handler")
        self.weaviate_core = kwargs.get("weaviate_core")
        self.postgresql_system = kwargs.get("postgresql_system")

    async def handle(
        self, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Traite les requêtes comparatives"""

        if not self.comparison_handler:
            logger.warning("ComparisonHandler non disponible, fallback vers standard")
            return await self._fallback_to_standard(preprocessed_data, start_time)

        try:
            logger.info("Executing comparative query via ComparisonHandler")

            comparison_result = await self.comparison_handler.handle_comparison_query(
                preprocessed_data
            )

            if not comparison_result["success"]:
                error_msg = comparison_result.get(
                    "error", "Erreur comparative inconnue"
                )
                logger.warning(f"Comparison failed: {error_msg}")
                return await self._fallback_to_standard(preprocessed_data, start_time)

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
        """Fallback vers traitement standard avec cascade PostgreSQL → Weaviate"""

        entities = preprocessed_data.get("entities", {})
        query = preprocessed_data["normalized_query"]
        language = preprocessed_data.get("language", "fr")

        logger.info(f"🌍 Fallback comparative avec langue: {language}")

        filters = self._extract_filters_from_entities(entities)

        availability_metadata = {
            "postgresql_available": self.postgresql_system is not None,
            "weaviate_available": self.weaviate_core is not None,
        }

        # 1. Tentative PostgreSQL
        if self.postgresql_system and entities:
            logger.info(
                f"🔍 Fallback comparative: tentative PostgreSQL (langue={language}, filters={filters})"
            )
            try:
                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=entities,
                    top_k=RAG_SIMILARITY_TOP_K,
                    filters=filters,
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    result.metadata.update(
                        {
                            "source_type": "comparative_fallback_postgresql",
                            "fallback_applied": True,
                            "processing_time": time.time() - start_time,
                            "language_used": language,
                            "filters_applied": filters,
                            **availability_metadata,
                        }
                    )
                    logger.info(
                        f"✅ Fallback PostgreSQL ({language}): {len(result.context_docs)} docs"
                    )
                    return result

                logger.info("⚠️ PostgreSQL fallback: 0 résultats")

            except Exception as e:
                logger.error(f"❌ Erreur PostgreSQL fallback: {e}")
                availability_metadata["postgresql_error"] = str(e)

        # 2. Tentative Weaviate
        if self.weaviate_core:
            logger.info(
                f"🔍 Fallback comparative: tentative Weaviate (langue={language}, filters={filters})"
            )
            try:
                weaviate_result = await self.weaviate_core.search(
                    query=query,
                    top_k=RAG_SIMILARITY_TOP_K,
                    language=language,
                    filters=filters,
                )

                if weaviate_result and weaviate_result.source == RAGSource.RAG_SUCCESS:
                    weaviate_result.metadata.update(
                        {
                            "source_type": "comparative_fallback_weaviate",
                            "fallback_applied": True,
                            "processing_time": time.time() - start_time,
                            "language_used": language,
                            "filters_applied": filters,
                            **availability_metadata,
                        }
                    )
                    logger.info(
                        f"✅ Fallback Weaviate ({language}): {len(weaviate_result.context_docs)} docs"
                    )
                    return weaviate_result

                logger.info("⚠️ Weaviate fallback: 0 résultats")

            except Exception as e:
                logger.error(f"❌ Erreur Weaviate fallback: {e}")
                availability_metadata["weaviate_error"] = str(e)

        # 3. Si tout échoue
        logger.warning("❌ Tous les fallbacks comparative ont échoué")
        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Je n'ai pas trouvé suffisamment d'informations pour répondre à cette comparaison.",
            metadata={
                "source_type": "comparative_no_results",
                "processing_time": time.time() - start_time,
                "result_type": "no_results",
                "is_success": False,
                "is_error": True,
                "language_attempted": language,
                "filters_attempted": filters,
                **availability_metadata,
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

            for result_item in results:
                if isinstance(result_item, dict):
                    if "all_docs" in result_item:
                        documents.extend(result_item["all_docs"])
                    elif "context_docs" in result_item:
                        documents.extend(result_item["context_docs"])

            logger.debug(f"Extracted {len(documents)} comparison documents")
            return documents

        except Exception as e:
            logger.warning(f"Erreur extraction documents comparatifs: {e}")
            return []
