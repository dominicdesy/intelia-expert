# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal Refactorisé
Point d'entrée principal avec délégation vers modules spécialisés
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

from config.config import RAG_ENABLED

try:
    from .data_models import RAGResult, RAGSource
except ImportError as e:
    logging.error(f"Erreur import data_models: {e}")
    raise

try:
    from utils.imports_and_dependencies import OPENAI_AVAILABLE, AsyncOpenAI
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

# Import des modules refactorisés
from .rag_engine_core import RAGEngineCore
from .rag_engine_query_classifier import QueryClassifier
from .rag_engine_handlers import (
    TemporalQueryHandler,
    ComparativeQueryHandler,
    StandardQueryHandler,
)

logger = logging.getLogger(__name__)

# Imports conditionnels des modules externes
POSTGRESQL_INTEGRATION_AVAILABLE = False
QUERY_PREPROCESSOR_AVAILABLE = False
COMPARISON_HANDLER_AVAILABLE = False
WEAVIATE_CORE_AVAILABLE = False

PostgreSQLSystem = None
QueryPreprocessor = None
ComparisonHandler = None
WeaviateCore = None

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

try:
    from .rag_weaviate_core import WeaviateCore

    WEAVIATE_CORE_AVAILABLE = True
    logger.info("Weaviate Core importé")
except ImportError as e:
    logger.warning(f"Weaviate Core non disponible: {e}")


class InteliaRAGEngine:
    """RAG Engine principal avec architecture modulaire"""

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialisation"""
        # Core engine
        self.core = RAGEngineCore(openai_client)

        # Query classification
        self.query_classifier = QueryClassifier()

        # Handlers spécialisés
        self.temporal_handler = TemporalQueryHandler()
        self.comparative_handler = ComparativeQueryHandler()
        self.standard_handler = StandardQueryHandler()

        # Modules externes
        self.postgresql_system = None
        self.query_preprocessor = None
        self.comparison_handler = None
        self.weaviate_core = None

        # État
        self.is_initialized = False
        self.degraded_mode = False
        self.initialization_errors = []

        # Stats
        self.optimization_stats = {
            "requests_total": 0,
            "preprocessing_success": 0,
            "preprocessing_failures": 0,
            "comparative_queries": 0,
            "comparative_success": 0,
            "comparative_failures": 0,
            "comparative_fallbacks": 0,
            "temporal_queries": 0,
            "optimization_queries": 0,  # ← AJOUTÉ
            "postgresql_queries": 0,
            "errors_count": 0,
        }

    async def initialize(self):
        """Initialisation modulaire"""
        if self.is_initialized:
            return

        logger.info("Initialisation RAG Engine modulaire")
        self.initialization_errors = []

        try:
            # Initialiser le core
            await self.core.initialize()

            # Initialiser les modules externes
            await self._initialize_external_modules()

            # Configurer les handlers avec les modules
            await self._configure_handlers()

            self.is_initialized = True

            active_modules = [
                name
                for name, module in [
                    ("Preprocessor", self.query_preprocessor),
                    ("PostgreSQL", self.postgresql_system),
                    ("WeaviateCore", self.weaviate_core),
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

    async def _initialize_external_modules(self):
        """Initialise les modules externes"""
        # Query Preprocessor
        if (
            QUERY_PREPROCESSOR_AVAILABLE
            and QueryPreprocessor
            and self.core.openai_client
        ):
            try:
                self.query_preprocessor = QueryPreprocessor(self.core.openai_client)
                await self.query_preprocessor.initialize()
                logger.info("Query Preprocessor initialisé")
            except Exception as e:
                logger.warning(f"Query Preprocessor échoué: {e}")
                self.initialization_errors.append(f"Preprocessor: {e}")

        # PostgreSQL System
        if POSTGRESQL_INTEGRATION_AVAILABLE and PostgreSQLSystem:
            try:
                self.postgresql_system = PostgreSQLSystem()
                await self.postgresql_system.initialize()
                logger.info("PostgreSQL System initialisé")
            except Exception as e:
                logger.warning(f"PostgreSQL échoué: {e}")
                self.initialization_errors.append(f"PostgreSQL: {e}")

        # Weaviate Core
        if WEAVIATE_CORE_AVAILABLE and WeaviateCore and self.core.openai_client:
            try:
                self.weaviate_core = WeaviateCore(self.core.openai_client)
                await self.weaviate_core.initialize()
                logger.info("Weaviate Core initialisé")
            except Exception as e:
                logger.warning(f"Weaviate Core échoué: {e}")
                self.initialization_errors.append(f"WeaviateCore: {e}")

        # Comparison Handler
        if (
            COMPARISON_HANDLER_AVAILABLE
            and ComparisonHandler
            and self.postgresql_system
        ):
            try:
                self.comparison_handler = ComparisonHandler(self.postgresql_system)
                logger.info("Comparison Handler initialisé")
            except Exception as e:
                logger.warning(f"Comparison Handler échoué: {e}")
                self.initialization_errors.append(f"ComparisonHandler: {e}")

    async def _configure_handlers(self):
        """Configure les handlers avec les modules"""
        # Configuration temporal handler
        self.temporal_handler.configure(postgresql_system=self.postgresql_system)

        # Configuration comparative handler
        self.comparative_handler.configure(comparison_handler=self.comparison_handler)

        # Configuration standard handler
        self.standard_handler.configure(
            postgresql_system=self.postgresql_system, weaviate_core=self.weaviate_core
        )

    async def generate_response(
        self,
        query: str,
        tenant_id: str = "default",
        conversation_context: List[Dict] = None,
        language: Optional[str] = None,
        enable_preprocessing: bool = True,
        **kwargs,
    ) -> RAGResult:
        """Point d'entrée principal avec routage intelligent"""

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
            return await self._process_query(
                query, language or "fr", enable_preprocessing, start_time
            )
        except Exception as e:
            logger.error(f"Erreur generate_response: {e}")
            self.optimization_stats["errors_count"] += 1
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e)},
            )

    async def _process_query(
        self,
        query: str,
        language: str,
        enable_preprocessing: bool,
        start_time: float,
    ) -> RAGResult:
        """Pipeline de traitement modulaire"""

        # 1. Preprocessing
        preprocessed_data = await self._apply_preprocessing(
            query, language, enable_preprocessing
        )

        # 2. Classification
        query_type = self.query_classifier.classify_query(
            preprocessed_data["normalized_query"],
            preprocessed_data["entities"],
            preprocessed_data.get("is_comparative", False),
        )

        logger.info(f"Type de requête détecté: {query_type}")

        # 3. Routage vers handler approprié
        result = await self._route_to_handler(query_type, preprocessed_data, start_time)

        # 4. Enrichir avec métadonnées de preprocessing
        result.metadata.update(preprocessed_data["metadata"])

        return result

    async def _apply_preprocessing(
        self, query: str, language: str, enable_preprocessing: bool
    ) -> Dict[str, Any]:
        """Applique le preprocessing si disponible"""

        if not enable_preprocessing or not self.query_preprocessor:
            return {
                "normalized_query": query,
                "entities": {},
                "routing_hint": None,
                "is_comparative": False,
                "comparison_entities": [],
                "metadata": {"preprocessing_applied": False},
            }

        try:
            logger.debug("Application du preprocessing")
            preprocessed = await self.query_preprocessor.preprocess_query(
                query=query, language=language
            )

            self.optimization_stats["preprocessing_success"] += 1

            return {
                "normalized_query": preprocessed["normalized_query"],
                "entities": preprocessed["entities"],
                "routing_hint": preprocessed["routing"],
                "is_comparative": preprocessed.get("is_comparative", False),
                "comparison_entities": preprocessed.get("comparison_entities", []),
                "metadata": {
                    "original_query": query,
                    "normalized_query": preprocessed["normalized_query"],
                    "routing_hint": preprocessed["routing"],
                    "is_comparative": preprocessed.get("is_comparative", False),
                    "preprocessing_applied": True,
                },
            }

        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}")
            self.optimization_stats["preprocessing_failures"] += 1

            return {
                "normalized_query": query,
                "entities": {},
                "routing_hint": None,
                "is_comparative": False,
                "comparison_entities": [],
                "metadata": {
                    "preprocessing_applied": False,
                    "preprocessing_error": str(e),
                },
            }

    async def _route_to_handler(
        self, query_type: str, preprocessed_data: Dict[str, Any], start_time: float
    ) -> RAGResult:
        """Route vers le handler approprié"""

        if query_type == "temporal_range":
            self.optimization_stats["temporal_queries"] += 1
            return await self.temporal_handler.handle(preprocessed_data, start_time)

        elif query_type == "comparative":
            self.optimization_stats["comparative_queries"] += 1
            return await self.comparative_handler.handle(preprocessed_data, start_time)

        elif query_type == "optimization":
            # Pour l'instant, router vers standard avec flag optimization
            self.optimization_stats["optimization_queries"] += 1
            preprocessed_data["is_optimization"] = True
            return await self.standard_handler.handle(preprocessed_data, start_time)

        else:  # standard
            return await self.standard_handler.handle(preprocessed_data, start_time)

    def get_status(self) -> Dict:
        """Status système complet"""
        return {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "version": "v8.0_modular_architecture",
            "modules": {
                "core": True,
                "query_classifier": True,
                "temporal_handler": True,
                "comparative_handler": True,
                "standard_handler": True,
                "query_preprocessor": bool(self.query_preprocessor),
                "postgresql_system": bool(self.postgresql_system),
                "weaviate_core": bool(self.weaviate_core),
                "comparison_handler": bool(self.comparison_handler),
            },
            "optimization_stats": self.optimization_stats.copy(),
            "capabilities": {
                "temporal_range_queries": True,
                "comparative_queries": bool(self.comparison_handler),
                "optimization_queries": True,  # ← AJOUTÉ
                "comparative_fallback": True,
                "intelligent_preprocessing": bool(self.query_preprocessor),
                "metrics_queries": bool(self.postgresql_system),
                "weaviate_search": bool(self.weaviate_core),
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

        try:
            if self.weaviate_core:
                await self.weaviate_core.close()
        except Exception as e:
            logger.error(f"Erreur fermeture Weaviate Core: {e}")

        await self.core.close()
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
