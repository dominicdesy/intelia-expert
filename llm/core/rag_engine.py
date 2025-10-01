# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal Refactorisé
Point d'entrée principal avec délégation vers modules spécialisés
VERSION 4.5 - CORRECTION COMPLÈTE POSTGRESQL VALIDATOR:
- ✅ Initialisation du PostgreSQLValidator dans _initialize_external_modules()
- ✅ Transmission du validator au StandardHandler via configure()
- ✅ Ajout de async def initialize() au PostgreSQLValidator
- ✅ Séparation PostgreSQLRetriever (search_metrics) et PostgreSQLValidator (validation)
- ✅ Transmission correcte du paramètre language à tous les handlers
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
from .rag_engine_handlers import (
    TemporalQueryHandler,
    ComparativeQueryHandler,
    StandardQueryHandler,
)

# NOUVEAUX IMPORTS - Modules centralisés
from .query_classifier import UnifiedQueryClassifier, QueryType
from .entity_extractor import EntityExtractor
from .validation_core import ValidationCore

logger = logging.getLogger(__name__)

# Imports conditionnels des modules externes
POSTGRESQL_RETRIEVER_AVAILABLE = False
POSTGRESQL_VALIDATOR_AVAILABLE = False
QUERY_PREPROCESSOR_AVAILABLE = False
COMPARISON_HANDLER_AVAILABLE = False
WEAVIATE_CORE_AVAILABLE = False

PostgreSQLRetriever = None
PostgreSQLValidator = None
QueryPreprocessor = None
ComparisonHandler = None
WeaviateCore = None

# ✅ CORRECTION 1: Import séparé du Retriever et Validator
try:
    from .rag_postgresql_retriever import PostgreSQLRetriever

    POSTGRESQL_RETRIEVER_AVAILABLE = True
    logger.info("✅ PostgreSQL Retriever importé")
except ImportError as e:
    logger.warning(f"⚠️ PostgreSQL Retriever non disponible: {e}")

try:
    from .rag_postgresql_validator import PostgreSQLValidator

    POSTGRESQL_VALIDATOR_AVAILABLE = True
    logger.info("✅ PostgreSQL Validator importé")
except ImportError as e:
    logger.warning(f"⚠️ PostgreSQL Validator non disponible: {e}")

try:
    from .query_preprocessor import QueryPreprocessor

    QUERY_PREPROCESSOR_AVAILABLE = True
    logger.info("✅ Query Preprocessor importé")
except ImportError as e:
    logger.warning(f"⚠️ Query Preprocessor non disponible: {e}")

try:
    from .comparison_handler import ComparisonHandler

    COMPARISON_HANDLER_AVAILABLE = True
    logger.info("✅ Comparison Handler importé (wrapper)")
except ImportError as e:
    logger.warning(f"⚠️ Comparison Handler non disponible: {e}")

try:
    from .rag_weaviate_core import WeaviateCore

    WEAVIATE_CORE_AVAILABLE = True
    logger.info("✅ Weaviate Core importé")
except ImportError as e:
    logger.warning(f"⚠️ Weaviate Core non disponible: {e}")


class InteliaRAGEngine:
    """
    RAG Engine principal avec architecture modulaire refactorisée

    VERSION 4.5 - CORRECTIONS CRITIQUES:
    - ✅ Initialisation complète du PostgreSQLValidator
    - ✅ Transmission du validator au StandardHandler
    - ✅ Séparation PostgreSQLRetriever (search_metrics) et PostgreSQLValidator (validation)
    - ✅ Transmission correcte du paramètre language à tous les handlers
    - Utilise UnifiedQueryClassifier au lieu de QueryClassifier legacy
    - Intègre EntityExtractor pour extraction centralisée
    - Utilise ValidationCore pour validation unifiée
    - ComparisonHandler est maintenant un wrapper vers ComparisonEngine
    """

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialisation avec nouveaux modules centralisés"""
        # Core engine
        self.core = RAGEngineCore(openai_client)

        # NOUVEAUX MODULES CENTRALISÉS
        self.query_classifier = UnifiedQueryClassifier()
        self.entity_extractor = EntityExtractor()
        self.validator = ValidationCore()

        # Handlers spécialisés
        self.temporal_handler = TemporalQueryHandler()
        self.comparative_handler = ComparativeQueryHandler()
        self.standard_handler = StandardQueryHandler()

        # ✅ CORRECTION 2: Modules externes avec Retriever ET Validator séparés
        self.postgresql_retriever = None  # ✅ Pour search_metrics()
        self.postgresql_validator = None  # ✅ Pour validation
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
            "optimization_queries": 0,
            "calculation_queries": 0,
            "economic_queries": 0,
            "diagnostic_queries": 0,
            "postgresql_queries": 0,
            "errors_count": 0,
        }

    async def initialize(self):
        """Initialisation modulaire avec nouveaux composants"""
        if self.is_initialized:
            return

        logger.info(
            "🚀 Initialisation RAG Engine v4.5 (PostgreSQL Validator fix complet)"
        )
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
                    ("PostgreSQLRetriever", self.postgresql_retriever),
                    ("PostgreSQLValidator", self.postgresql_validator),
                    ("WeaviateCore", self.weaviate_core),
                    ("ComparisonHandler", self.comparison_handler),
                    ("QueryClassifier", self.query_classifier),
                    ("EntityExtractor", self.entity_extractor),
                    ("ValidationCore", self.validator),
                ]
                if module is not None
            ]

            logger.info(
                f"✅ RAG Engine initialisé - Modules: {', '.join(active_modules)}"
            )

            if self.initialization_errors:
                logger.warning(
                    f"⚠️ Erreurs d'initialisation: {self.initialization_errors}"
                )

        except Exception as e:
            logger.error(f"❌ Erreur initialisation critique: {e}")
            self.degraded_mode = True
            self.is_initialized = True
            self.initialization_errors.append(str(e))

    async def _initialize_external_modules(self):
        """✅ CORRECTION 3: Initialise Retriever et Validator séparément avec initialize()"""

        # Query Preprocessor
        if QUERY_PREPROCESSOR_AVAILABLE and QueryPreprocessor:
            try:
                self.query_preprocessor = QueryPreprocessor()
                await self.query_preprocessor.initialize()
                logger.info("✅ Query Preprocessor initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Query Preprocessor échoué: {e}")
                self.initialization_errors.append(f"Preprocessor: {e}")

        # ✅ PostgreSQL Retriever (pour search_metrics)
        if POSTGRESQL_RETRIEVER_AVAILABLE and PostgreSQLRetriever:
            try:
                self.postgresql_retriever = PostgreSQLRetriever()
                await self.postgresql_retriever.initialize()
                logger.info("✅ PostgreSQL Retriever initialisé")
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL Retriever échoué: {e}")
                self.initialization_errors.append(f"PostgreSQLRetriever: {e}")

        # ✅ PostgreSQL Validator (pour validation) - CORRECTION CRITIQUE
        if POSTGRESQL_VALIDATOR_AVAILABLE and PostgreSQLValidator:
            try:
                self.postgresql_validator = PostgreSQLValidator()
                # ✅ AJOUT CRITIQUE: Appeler initialize() si la méthode existe
                if hasattr(self.postgresql_validator, "initialize"):
                    await self.postgresql_validator.initialize()
                logger.info("✅ PostgreSQL Validator initialisé")
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL Validator échoué: {e}")
                self.initialization_errors.append(f"PostgreSQLValidator: {e}")

        # Weaviate Core
        if WEAVIATE_CORE_AVAILABLE and WeaviateCore and self.core.openai_client:
            try:
                self.weaviate_core = WeaviateCore(self.core.openai_client)
                await self.weaviate_core.initialize()
                logger.info("✅ Weaviate Core initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Weaviate Core échoué: {e}")
                self.initialization_errors.append(f"WeaviateCore: {e}")

        # Comparison Handler (utilise le Retriever)
        if COMPARISON_HANDLER_AVAILABLE and ComparisonHandler:
            try:
                self.comparison_handler = ComparisonHandler(self.postgresql_retriever)
                if not self.postgresql_retriever:
                    logger.warning(
                        "⚠️ Comparison Handler en mode dégradé (pas de PostgreSQL)"
                    )
                else:
                    logger.info("✅ Comparison Handler initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Comparison Handler échoué: {e}")
                self.initialization_errors.append(f"ComparisonHandler: {e}")

    async def _configure_handlers(self):
        """✅ CORRECTION 4: Configure handlers avec Retriever ET Validator"""

        # Configuration temporal handler (utilise le Retriever)
        self.temporal_handler.configure(postgresql_system=self.postgresql_retriever)

        # Configuration comparative handler (utilise le Retriever)
        self.comparative_handler.configure(
            comparison_handler=self.comparison_handler,
            weaviate_core=self.weaviate_core,
            postgresql_system=self.postgresql_retriever,
        )

        # ✅ Configuration standard handler (utilise RETRIEVER + VALIDATOR)
        self.standard_handler.configure(
            postgresql_system=self.postgresql_retriever,  # Pour search_metrics()
            weaviate_core=self.weaviate_core,
            postgresql_validator=self.postgresql_validator,  # ✅ AJOUT CRITIQUE
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
            logger.warning("⚠️ RAG Engine non initialisé, tentative d'initialisation")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"❌ Échec initialisation: {e}")

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1

        # Validation
        if not query or not query.strip():
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": "Query vide"},
            )

        effective_language = language or "fr"
        logger.info(f"🌍 generate_response reçoit langue: {effective_language}")

        # Fallback si système indisponible
        if self.degraded_mode and not self.postgresql_retriever:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                answer="Le système RAG n'est pas disponible.",
                metadata={"reason": "système_indisponible"},
            )

        try:
            return await self._process_query(
                query, effective_language, enable_preprocessing, start_time
            )
        except Exception as e:
            logger.error(f"❌ Erreur generate_response: {e}")
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

        logger.info(f"🌍 _process_query traite avec langue: {language}")

        # 1. Preprocessing
        preprocessed_data = await self._apply_preprocessing(
            query, language, enable_preprocessing
        )

        if "language" not in preprocessed_data:
            preprocessed_data["language"] = language
            logger.info(f"🌍 Langue ajoutée à preprocessed_data: {language}")

        # 2. Classification
        classification = self.query_classifier.classify(
            preprocessed_data["normalized_query"]
        )

        query_type = classification.query_type.value
        logger.info(
            f"🎯 Type de requête détecté: {query_type} (confiance: {classification.confidence:.2%})"
        )

        # Mise à jour des stats
        if classification.query_type == QueryType.COMPARATIVE:
            self.optimization_stats["comparative_queries"] += 1
        elif classification.query_type == QueryType.TEMPORAL_RANGE:
            self.optimization_stats["temporal_queries"] += 1
        elif classification.query_type == QueryType.OPTIMIZATION:
            self.optimization_stats["optimization_queries"] += 1
        elif classification.query_type == QueryType.CALCULATION:
            self.optimization_stats["calculation_queries"] += 1
        elif classification.query_type == QueryType.ECONOMIC:
            self.optimization_stats["economic_queries"] += 1
        elif classification.query_type == QueryType.DIAGNOSTIC:
            self.optimization_stats["diagnostic_queries"] += 1

        # 3. Enrichir preprocessed_data
        preprocessed_data["query_type"] = query_type
        preprocessed_data["classification"] = classification.to_dict()

        # 4. Routage vers handler
        result = await self._route_to_handler(
            query_type, preprocessed_data, start_time, language
        )

        # 5. Enrichir métadonnées
        result.metadata.update(preprocessed_data["metadata"])
        result.metadata["classification"] = classification.to_dict()

        return result

    async def _apply_preprocessing(
        self, query: str, language: str, enable_preprocessing: bool
    ) -> Dict[str, Any]:
        """Applique le preprocessing"""

        logger.debug(f"🌍 _apply_preprocessing avec langue: {language}")

        if not enable_preprocessing or not self.query_preprocessor:
            logger.debug("📋 Preprocessing minimal")

            extracted = self.entity_extractor.extract(query)
            entities_dict = extracted.to_dict()

            return {
                "normalized_query": query,
                "original_query": query,
                "entities": entities_dict,
                "language": language,
                "routing_hint": None,
                "is_comparative": False,
                "comparison_entities": [],
                "metadata": {
                    "preprocessing_applied": False,
                    "extraction_confidence": extracted.confidence,
                    "entities_found": extracted.get_entity_count(),
                    "language_detected": language,
                },
            }

        try:
            logger.debug("🔧 Application du preprocessing complet")
            preprocessed = await self.query_preprocessor.preprocess_query(
                query=query, language=language
            )

            self.optimization_stats["preprocessing_success"] += 1

            return {
                "normalized_query": preprocessed.get("normalized_query", query),
                "original_query": query,
                "entities": preprocessed.get("entities", {}),
                "language": language,
                "routing_hint": preprocessed.get("routing"),
                "is_comparative": preprocessed.get("is_comparative", False),
                "comparison_entities": preprocessed.get("comparison_entities", []),
                "temporal_range": preprocessed.get("temporal_range"),
                "metadata": {
                    "original_query": query,
                    "normalized_query": preprocessed.get("normalized_query", query),
                    "routing_hint": preprocessed.get("routing"),
                    "is_comparative": preprocessed.get("is_comparative", False),
                    "preprocessing_applied": True,
                    "confidence": preprocessed.get("confidence", 1.0),
                    "language_detected": language,
                },
            }

        except Exception as e:
            logger.warning(f"⚠️ Preprocessing échoué: {e}, fallback basique")
            self.optimization_stats["preprocessing_failures"] += 1

            extracted = self.entity_extractor.extract(query)
            entities_dict = extracted.to_dict()

            return {
                "normalized_query": query,
                "original_query": query,
                "entities": entities_dict,
                "language": language,
                "routing_hint": None,
                "is_comparative": False,
                "comparison_entities": [],
                "metadata": {
                    "preprocessing_applied": False,
                    "preprocessing_error": str(e),
                    "fallback_extraction": True,
                    "extraction_confidence": extracted.confidence,
                    "language_detected": language,
                },
            }

    async def _route_to_handler(
        self,
        query_type: str,
        preprocessed_data: Dict[str, Any],
        start_time: float,
        language: str,
    ) -> RAGResult:
        """Route vers le handler approprié"""

        logger.info(f"🌍 _route_to_handler avec langue: {language}")

        if query_type == "temporal_range":
            logger.debug("→ Routage vers TemporalQueryHandler")
            return await self.temporal_handler.handle(preprocessed_data, start_time)

        elif query_type == "comparative":
            logger.debug("→ Routage vers ComparativeQueryHandler")
            return await self.comparative_handler.handle(preprocessed_data, start_time)

        elif query_type in ["optimization", "calculation"]:
            logger.debug(f"→ Routage vers StandardHandler (type={query_type})")
            preprocessed_data["is_optimization"] = query_type == "optimization"
            preprocessed_data["is_calculation"] = query_type == "calculation"
            return await self.standard_handler.handle(
                preprocessed_data, start_time, language=language
            )

        elif query_type == "economic":
            logger.debug("→ Requête économique détectée")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Les données économiques ne sont pas disponibles.",
                metadata={"query_type": "economic"},
            )

        elif query_type == "diagnostic":
            logger.debug("→ Routage vers StandardHandler (diagnostic)")
            preprocessed_data["routing_hint"] = "weaviate"
            return await self.standard_handler.handle(
                preprocessed_data, start_time, language=language
            )

        else:  # standard
            logger.debug("→ Routage vers StandardHandler (standard)")
            return await self.standard_handler.handle(
                preprocessed_data, start_time, language=language
            )

    def get_status(self) -> Dict:
        """Status système complet"""
        return {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "version": "v4.5_postgresql_validator_complete_fix",
            "architecture": "modular_centralized",
            "modules": {
                "core": True,
                "rag_engine": True,
                "query_classifier": bool(self.query_classifier),
                "entity_extractor": bool(self.entity_extractor),
                "validation_core": bool(self.validator),
                "temporal_handler": True,
                "comparative_handler": True,
                "standard_handler": True,
                "query_preprocessor": bool(self.query_preprocessor),
                "postgresql_retriever": bool(self.postgresql_retriever),
                "postgresql_validator": bool(self.postgresql_validator),
                "weaviate_core": bool(self.weaviate_core),
                "comparison_handler": bool(self.comparison_handler),
            },
            "optimization_stats": self.optimization_stats.copy(),
            "initialization_errors": self.initialization_errors,
        }

    async def close(self):
        """Fermeture propre de tous les modules"""
        logger.info("🔒 Fermeture RAG Engine...")

        try:
            if self.query_preprocessor:
                await self.query_preprocessor.close()
        except Exception as e:
            logger.error(f"❌ Erreur fermeture Preprocessor: {e}")

        try:
            if self.postgresql_retriever:
                await self.postgresql_retriever.close()
        except Exception as e:
            logger.error(f"❌ Erreur fermeture PostgreSQL Retriever: {e}")

        try:
            if self.postgresql_validator and hasattr(
                self.postgresql_validator, "close"
            ):
                await self.postgresql_validator.close()
        except Exception as e:
            logger.error(f"❌ Erreur fermeture PostgreSQL Validator: {e}")

        try:
            if self.weaviate_core:
                await self.weaviate_core.close()
        except Exception as e:
            logger.error(f"❌ Erreur fermeture Weaviate Core: {e}")

        try:
            await self.core.close()
        except Exception as e:
            logger.error(f"❌ Erreur fermeture Core: {e}")

        logger.info("✅ RAG Engine fermé complètement")


# Factory function
def create_rag_engine(openai_client=None) -> InteliaRAGEngine:
    """Factory pour créer une instance RAG Engine"""
    return InteliaRAGEngine(openai_client)


# Fonction de test
async def test_clarification_query():
    """Test d'une requête nécessitant clarification"""
    engine = InteliaRAGEngine()

    try:
        await engine.initialize()

        test_query = "Quel est le poids pour du Ross 308 ?"

        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {test_query}")
        logger.info(f"{'='*60}")

        result = await engine.generate_response(test_query, language="fr")

        print(f"Source: {result.source}")
        print(f"Answer: {result.answer}")
        print(f"Metadata: {result.metadata}")

    except Exception as e:
        logger.error(f"❌ Test error: {e}")
    finally:
        await engine.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(test_clarification_query())
