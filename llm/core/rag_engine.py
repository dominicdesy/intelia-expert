# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal avec Support Comparatif
Version modulaire utilisant ComparisonHandler pour requêtes comparatives
Simplifié - garde seulement l'essentiel du code original
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

from config.config import (
    RAG_ENABLED,
    OPENAI_API_KEY,
    RAG_SIMILARITY_TOP_K,
)

try:
    from .data_models import RAGResult, RAGSource
except ImportError as e:
    logging.error(f"Erreur import data_models: {e}")
    raise

try:
    from utils.imports_and_dependencies import (
        OPENAI_AVAILABLE,
        WEAVIATE_AVAILABLE,
        AsyncOpenAI,
    )
except ImportError:
    OPENAI_AVAILABLE = False
    WEAVIATE_AVAILABLE = False
    AsyncOpenAI = None

logger = logging.getLogger(__name__)

# Imports des modules avec gestion d'erreur
POSTGRESQL_INTEGRATION_AVAILABLE = False
QUERY_PREPROCESSOR_AVAILABLE = False
COMPARISON_HANDLER_AVAILABLE = False

PostgreSQLSystem = None
QueryPreprocessor = None
ComparisonHandler = None

try:
    from .rag_postgresql import PostgreSQLSystem

    POSTGRESQL_INTEGRATION_AVAILABLE = True
    logger.info("PostgreSQL System importé")
except ImportError as e:
    logger.warning(f"PostgreSQL non disponible: {e}")

try:
    from .query_preprocessor import QueryPreprocessor

    QUERY_PREPROCESSOR_AVAILABLE = True
    logger.info("Query Preprocessor importé")
except ImportError as e:
    logger.warning(f"Query Preprocessor non disponible: {e}")

try:
    from .comparison_handler import ComparisonHandler

    COMPARISON_HANDLER_AVAILABLE = True
    logger.info("Comparison Handler importé")
except ImportError as e:
    logger.warning(f"Comparison Handler non disponible: {e}")


class InteliaRAGEngine:
    """RAG Engine avec support des requêtes comparatives"""

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialisation"""
        try:
            self.openai_client = openai_client or self._build_openai_client()
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            self.openai_client = None

        # Modules
        self.postgresql_system = None
        self.query_preprocessor = None
        self.comparison_handler = None  # NOUVEAU

        # État
        self.is_initialized = False
        self.degraded_mode = False
        self.initialization_errors = []

        # Stats
        self.optimization_stats = {
            "requests_total": 0,
            "preprocessing_success": 0,
            "preprocessing_failures": 0,
            "comparative_queries": 0,  # NOUVEAU
            "comparative_success": 0,  # NOUVEAU
            "comparative_failures": 0,  # NOUVEAU
            "postgresql_queries": 0,
            "errors_count": 0,
        }

    def _build_openai_client(self) -> Optional[AsyncOpenAI]:
        """Client OpenAI"""
        if not OPENAI_AVAILABLE or not AsyncOpenAI:
            return None

        if not OPENAI_API_KEY:
            return None

        try:
            try:
                import httpx

                http_client = httpx.AsyncClient(timeout=30.0)
                return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
            except ImportError:
                return AsyncOpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Erreur création client OpenAI: {e}")
            return None

    async def initialize(self):
        """Initialisation modulaire"""
        if self.is_initialized:
            return

        logger.info("Initialisation RAG Engine avec support comparatif")
        self.initialization_errors = []

        try:
            # 1. Query Preprocessor
            if (
                QUERY_PREPROCESSOR_AVAILABLE
                and QueryPreprocessor
                and self.openai_client
            ):
                await self._initialize_query_preprocessor()

            # 2. PostgreSQL System
            if POSTGRESQL_INTEGRATION_AVAILABLE and PostgreSQLSystem:
                await self._initialize_postgresql_system()

            # 3. Comparison Handler (dépend de PostgreSQL)
            if (
                COMPARISON_HANDLER_AVAILABLE
                and ComparisonHandler
                and self.postgresql_system
            ):
                await self._initialize_comparison_handler()

            self.is_initialized = True

            active_modules = [
                name
                for name, module in [
                    ("Preprocessor", self.query_preprocessor),
                    ("PostgreSQL", self.postgresql_system),
                    ("ComparisonHandler", self.comparison_handler),
                ]
                if module is not None
            ]

            logger.info(f"RAG Engine initialisé - Modules: {active_modules}")

            if self.initialization_errors:
                logger.warning(f"Erreurs: {self.initialization_errors}")

        except Exception as e:
            logger.error(f"Erreur initialisation: {e}")
            self.degraded_mode = True
            self.is_initialized = True
            self.initialization_errors.append(str(e))

    async def _initialize_query_preprocessor(self):
        """Initialise le preprocessor"""
        try:
            self.query_preprocessor = QueryPreprocessor(self.openai_client)
            await self.query_preprocessor.initialize()
            logger.info("Query Preprocessor initialisé")
        except Exception as e:
            logger.warning(f"Query Preprocessor échoué: {e}")
            self.query_preprocessor = None
            self.initialization_errors.append(f"Preprocessor: {e}")

    async def _initialize_postgresql_system(self):
        """Initialise PostgreSQL"""
        try:
            self.postgresql_system = PostgreSQLSystem()
            await self.postgresql_system.initialize()
            logger.info("PostgreSQL System initialisé")
        except Exception as e:
            logger.warning(f"PostgreSQL échoué: {e}")
            self.postgresql_system = None
            self.initialization_errors.append(f"PostgreSQL: {e}")

    async def _initialize_comparison_handler(self):
        """Initialise le Comparison Handler"""
        try:
            self.comparison_handler = ComparisonHandler(self.postgresql_system)
            logger.info("Comparison Handler initialisé")
        except Exception as e:
            logger.warning(f"Comparison Handler échoué: {e}")
            self.comparison_handler = None
            self.initialization_errors.append(f"ComparisonHandler: {e}")

    async def generate_response(
        self,
        query: str,
        tenant_id: str = "default",
        conversation_context: List[Dict] = None,
        language: Optional[str] = None,
        enable_preprocessing: bool = True,
        **kwargs,
    ) -> RAGResult:
        """
        Point d'entrée principal avec support comparatif

        NOUVEAU: Détecte et traite les requêtes comparatives
        """

        if not self.is_initialized:
            logger.warning("RAG Engine non initialisé")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Échec initialisation: {e}")

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1

        # Validation
        if not query or not query.strip():
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": "Query vide"},
            )

        # Fallback si système indisponible
        if self.degraded_mode and not self.postgresql_system:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                answer="Le système RAG n'est pas disponible.",
                metadata={"reason": "système_indisponible"},
            )

        try:
            # Traitement core
            return await self._generate_response_core(
                query,
                language or "fr",
                enable_preprocessing,
                start_time,
            )

        except Exception as e:
            logger.error(f"Erreur generate_response: {e}")
            self.optimization_stats["errors_count"] += 1
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e)},
            )

    async def _generate_response_core(
        self,
        query: str,
        language: str,
        enable_preprocessing: bool,
        start_time: float,
    ) -> RAGResult:
        """
        Pipeline avec support comparatif

        NOUVEAU: Branche vers comparison_handler si requête comparative
        """

        try:
            # ============================================
            # PREPROCESSING INTELLIGENT
            # ============================================
            normalized_query = query
            routing_hint = None
            entities = {}
            is_comparative = False
            preprocessed_metadata = {}

            if enable_preprocessing and self.query_preprocessor:
                try:
                    logger.debug("Application du preprocessing")
                    preprocessed = await self.query_preprocessor.preprocess_query(
                        query=query, language=language
                    )

                    normalized_query = preprocessed["normalized_query"]
                    routing_hint = preprocessed["routing"]
                    entities = preprocessed["entities"]
                    is_comparative = preprocessed.get("is_comparative", False)

                    self.optimization_stats["preprocessing_success"] += 1

                    preprocessed_metadata = {
                        "original_query": query,
                        "normalized_query": normalized_query,
                        "routing_hint": routing_hint,
                        "is_comparative": is_comparative,
                        "preprocessing_applied": True,
                    }

                    logger.info(f"Preprocessing: '{query}' -> '{normalized_query}'")
                    logger.debug(f"Comparative: {is_comparative}")

                except Exception as e:
                    logger.warning(f"Preprocessing failed: {e}")
                    self.optimization_stats["preprocessing_failures"] += 1

            # ============================================
            # BRANCHEMENT COMPARATIF
            # ============================================
            if is_comparative and self.comparison_handler:
                logger.info(
                    "Requête COMPARATIVE détectée - routage vers ComparisonHandler"
                )
                self.optimization_stats["comparative_queries"] += 1

                result = await self._handle_comparative_query(
                    query, normalized_query, preprocessed, language, start_time
                )

                result.metadata.update(preprocessed_metadata)
                return result

            # ============================================
            # ROUTAGE STANDARD (non-comparatif)
            # ============================================

            # PostgreSQL si suggéré
            if routing_hint == "postgresql" and self.postgresql_system:
                logger.info("Routage PostgreSQL (preprocessing)")
                result = await self.postgresql_system.search_metrics(
                    query=normalized_query,
                    entities=entities,
                    top_k=RAG_SIMILARITY_TOP_K,
                    strict_sex_match=False,  # Mode normal
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    result.metadata.update(preprocessed_metadata)
                    return result

            # Fallback PostgreSQL standard
            if self.postgresql_system:
                logger.info("Fallback PostgreSQL standard")
                result = await self.postgresql_system.search_metrics(
                    query=normalized_query,
                    entities=entities,
                    top_k=RAG_SIMILARITY_TOP_K,
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    result.metadata.update(preprocessed_metadata)
                    return result

            # Aucun résultat
            final_result = RAGResult(
                source=RAGSource.NO_RESULTS,
                answer="Aucun résultat trouvé.",
                metadata={
                    "processing_time": time.time() - start_time,
                },
            )
            final_result.metadata.update(preprocessed_metadata)
            return final_result

        except Exception as e:
            logger.error(f"Erreur génération core: {e}")
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e)},
            )

    async def _handle_comparative_query(
        self,
        original_query: str,
        normalized_query: str,
        preprocessed: Dict[str, Any],
        language: str,
        start_time: float,
    ) -> RAGResult:
        """
        NOUVEAU: Gère les requêtes comparatives via ComparisonHandler

        Returns:
            RAGResult avec calculs de comparaison
        """
        try:
            # Utiliser le ComparisonHandler
            comparison_result = await self.comparison_handler.handle_comparative_query(
                normalized_query, preprocessed, top_k=RAG_SIMILARITY_TOP_K
            )

            if not comparison_result["success"]:
                logger.warning(f"Comparison failed: {comparison_result.get('error')}")
                self.optimization_stats["comparative_failures"] += 1

                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    answer=f"Impossible de comparer: {comparison_result.get('error')}",
                    metadata={
                        "source_type": "comparative",
                        "error": comparison_result.get("error"),
                        "processing_time": time.time() - start_time,
                    },
                )

            # Générer la réponse naturelle
            answer_text = await self.comparison_handler.generate_comparative_response(
                original_query, comparison_result, language
            )

            self.optimization_stats["comparative_success"] += 1

            # Construire le résultat
            comparison = comparison_result["comparison"]

            logger.info(
                f"Comparison SUCCESS: {comparison.label1}={comparison.value1} vs "
                f"{comparison.label2}={comparison.value2}"
            )

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=[],  # Les docs sont dans comparison_result si besoin
                confidence=0.95,  # Haute confiance pour comparaisons réussies
                metadata={
                    "source_type": "comparative",
                    "comparison_type": comparison_result.get("comparison_type"),
                    "operation": comparison_result.get("operation"),
                    "value1": comparison.value1,
                    "value2": comparison.value2,
                    "difference": comparison.absolute_difference,
                    "difference_pct": comparison.relative_difference_pct,
                    "processing_time": time.time() - start_time,
                    "result_count": len(comparison_result["results"]),
                },
            )

        except Exception as e:
            logger.error(f"Erreur traitement comparatif: {e}")
            self.optimization_stats["comparative_failures"] += 1

            return RAGResult(
                source=RAGSource.ERROR,
                metadata={
                    "error": str(e),
                    "source_type": "comparative",
                },
            )

    def get_status(self) -> Dict:
        """Status système avec stats comparatives"""
        return {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "version": "v7.0_with_comparative_support",
            "modules": {
                "query_preprocessor": bool(self.query_preprocessor),
                "postgresql_system": bool(self.postgresql_system),
                "comparison_handler": bool(self.comparison_handler),
            },
            "optimization_stats": self.optimization_stats.copy(),
            "capabilities": {
                "comparative_queries": bool(self.comparison_handler),
                "intelligent_preprocessing": bool(self.query_preprocessor),
                "metrics_queries": bool(self.postgresql_system),
            },
            "initialization_errors": self.initialization_errors,
        }

    async def close(self):
        """Fermeture propre"""
        logger.info("Fermeture RAG Engine...")

        try:
            if self.query_preprocessor:
                await self.query_preprocessor.close()
        except Exception as e:
            logger.error(f"Erreur fermeture Preprocessor: {e}")

        try:
            if self.postgresql_system:
                await self.postgresql_system.close()
        except Exception as e:
            logger.error(f"Erreur fermeture PostgreSQL: {e}")

        # comparison_handler n'a pas de close()

        logger.info("RAG Engine fermé")


# Factory function
def create_rag_engine(openai_client=None) -> InteliaRAGEngine:
    """Factory pour créer une instance RAG Engine"""
    return InteliaRAGEngine(openai_client)


# Fonction de test
async def test_comparative_query():
    """Test d'une requête comparative"""
    engine = InteliaRAGEngine()

    try:
        await engine.initialize()

        test_query = "Quelle est la différence de FCR entre un Cobb 500 mâle et femelle de 17 jours ?"

        logger.info(f"Testing: {test_query}")
        result = await engine.generate_response(test_query)

        print("\n" + "=" * 60)
        print("TEST RÉSULTAT")
        print("=" * 60)
        print(f"Source: {result.source}")
        print(f"Answer: {result.answer}")
        print(f"\nMetadata: {result.metadata}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Test error: {e}")
    finally:
        await engine.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_comparative_query())
