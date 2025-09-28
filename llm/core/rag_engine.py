# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal avec Support Comparatif
Version modulaire utilisant ComparisonHandler pour requêtes comparatives
Simplifié - garde seulement l'essentiel du code original
Version corrigée avec gestion d'erreur comparative robuste
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Any, Tuple

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

# NOUVEAU: Import Weaviate Core
WEAVIATE_CORE_AVAILABLE = False
WeaviateCore = None

try:
    from .rag_weaviate_core import WeaviateCore

    WEAVIATE_CORE_AVAILABLE = True
    logger.info("Weaviate Core importé")
except ImportError as e:
    logger.warning(f"Weaviate Core non disponible: {e}")


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

        # NOUVEAU: Module Weaviate
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
            "comparative_queries": 0,  # NOUVEAU
            "comparative_success": 0,  # NOUVEAU
            "comparative_failures": 0,  # NOUVEAU
            "comparative_fallbacks": 0,  # NOUVEAU
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

            # 3. NOUVEAU: Weaviate Core
            if WEAVIATE_CORE_AVAILABLE and WeaviateCore and self.openai_client:
                await self._initialize_weaviate_core()

            # 4. Comparison Handler (dépend de PostgreSQL)
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
                    ("WeaviateCore", self.weaviate_core),  # NOUVEAU
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

    async def _initialize_weaviate_core(self):
        """Initialise Weaviate Core"""
        try:
            self.weaviate_core = WeaviateCore(self.openai_client)
            await self.weaviate_core.initialize()

            # Connecter le cache si disponible
            cache_core = getattr(self, "cache_manager", None)
            if cache_core:
                self.weaviate_core.set_cache_manager(cache_core)

            logger.info("Weaviate Core initialisé")
        except Exception as e:
            logger.warning(f"Weaviate Core échoué: {e}")
            self.weaviate_core = None
            self.initialization_errors.append(f"WeaviateCore: {e}")

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

                    # Debug: vérifier si comparison_handler est disponible
                    if is_comparative:
                        logger.debug(
                            f"ComparisonHandler available: {self.comparison_handler is not None}"
                        )
                        if preprocessed.get("comparison_entities"):
                            logger.debug(
                                f"Comparison entities: {len(preprocessed['comparison_entities'])} sets"
                            )

                except Exception as e:
                    logger.warning(f"Preprocessing failed: {e}")
                    self.optimization_stats["preprocessing_failures"] += 1

            # ============================================
            # BRANCHEMENT COMPARATIF
            # ============================================
            if is_comparative:
                if self.comparison_handler:
                    logger.info(
                        "Requête COMPARATIVE détectée - routage vers ComparisonHandler"
                    )
                    self.optimization_stats["comparative_queries"] += 1

                    result = await self._handle_comparative_query(
                        query, normalized_query, preprocessed, language, start_time
                    )

                    result.metadata.update(preprocessed_metadata)
                    return result
                else:
                    logger.warning(
                        "Requête comparative détectée mais ComparisonHandler non disponible"
                    )
                    # Fallback vers traitement standard
                    is_comparative = False

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
        NOUVEAU: Gestion robuste des requêtes comparatives avec fallback intelligent
        """

        try:
            logger.info("Executing comparative query via ComparisonHandler")

            # Utiliser le ComparisonHandler
            comparison_result = await self.comparison_handler.handle_comparative_query(
                normalized_query, preprocessed, top_k=RAG_SIMILARITY_TOP_K
            )

            if not comparison_result["success"]:
                error_msg = comparison_result.get(
                    "error", "Erreur comparative inconnue"
                )
                logger.warning(f"Comparison failed: {error_msg}")
                self.optimization_stats["comparative_failures"] += 1

                # NOUVEAU: Fallback intelligent vers requête standard
                logger.info("Attempting fallback to standard query processing")

                # Vérifier si c'est une comparaison temporelle (plage d'âges)
                if (
                    comparison_result.get("error")
                    == "Comparaison impossible avec une seule entité"
                ):
                    age_range = self._extract_age_range_from_query(original_query)
                    if age_range:
                        logger.info(f"Requête temporelle détectée: {age_range}")
                        return await self._handle_temporal_query(
                            original_query,
                            preprocessed.get("entities", {}),
                            age_range,
                            start_time,
                        )

                # Extraire la première entité pour requête standard
                entities = preprocessed.get("entities", {})
                if entities:
                    fallback_result = await self._execute_standard_query(
                        normalized_query, entities, start_time
                    )

                    # Enrichir avec info sur l'échec comparatif
                    fallback_result.metadata.update(
                        {
                            "source_type": "comparative_fallback",
                            "comparative_error": error_msg,
                            "suggestion": comparison_result.get("suggestion"),
                            "fallback_applied": True,
                        }
                    )

                    self.optimization_stats["comparative_fallbacks"] += 1
                    return fallback_result

                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    answer=self._generate_helpful_error_message(comparison_result),
                    metadata={
                        "source_type": "comparative",
                        "error": error_msg,
                        "processing_time": time.time() - start_time,
                    },
                )

            # Succès: générer la réponse comparative
            self.optimization_stats["comparative_success"] += 1

            answer_text = await self.comparison_handler.generate_comparative_response(
                original_query, comparison_result, language
            )

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=self._extract_comparison_documents(comparison_result),
                confidence=0.95,  # Haute confiance pour comparaisons réussies
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
            self.optimization_stats["comparative_failures"] += 1

            # Fallback d'urgence
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                answer="Une erreur s'est produite lors de la comparaison. Veuillez reformuler votre question.",
                metadata={
                    "error": str(e),
                    "source_type": "comparative_error",
                    "processing_time": time.time() - start_time,
                },
            )

    def _generate_helpful_error_message(self, comparison_result: Dict) -> str:
        """Générer des messages d'erreur utiles"""

        error = comparison_result.get("error", "")
        suggestion = comparison_result.get("suggestion", "")

        if "Insufficient results" in error:
            return f"""Je n'ai pas pu trouver suffisamment de données pour effectuer cette comparaison. 

{suggestion}

Vous pouvez essayer de :
- Vérifier les noms des souches (Cobb 500, Ross 308)
- Préciser l'âge en jours
- Reformuler votre question de manière plus simple"""

        elif "entités de comparaison" in error:
            return f"""Il me faut au moins deux éléments à comparer pour répondre à votre question.

{suggestion}

Exemple de formulation : "Compare le poids du Cobb 500 et du Ross 308 à 42 jours" """

        else:
            return f"""Je n'ai pas pu traiter cette demande de comparaison.

{suggestion if suggestion else "Veuillez reformuler votre question plus clairement."}"""

    async def _execute_standard_query(
        self, query: str, entities: Dict, start_time: float
    ) -> RAGResult:
        """Exécution d'une requête standard en fallback"""

        if self.postgresql_system:
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=entities,
                top_k=RAG_SIMILARITY_TOP_K,
            )

            if result and result.source != RAGSource.NO_RESULTS:
                return result

        return RAGResult(
            source=RAGSource.NO_RESULTS,
            answer="Aucun résultat trouvé même en mode standard.",
            metadata={
                "processing_time": time.time() - start_time,
                "fallback_type": "standard_query",
            },
        )

    def _extract_comparison_documents(self, comparison_result: Dict) -> List:
        """Extrait les documents des résultats de comparaison"""
        try:
            documents = []

            # Extraire les documents des résultats si disponibles
            if "results" in comparison_result:
                for result_set in comparison_result["results"]:
                    if isinstance(result_set, dict) and "context_docs" in result_set:
                        documents.extend(result_set["context_docs"])

            return documents
        except Exception as e:
            logger.warning(f"Erreur extraction documents comparatifs: {e}")
            return []

    def _extract_age_range_from_query(self, query: str) -> Optional[Tuple[int, int]]:
        """Extrait plage d'âges de la requête"""
        patterns = [
            r"entre\s+(\d+)\s+et\s+(\d+)\s+jours?",
            r"de\s+(\d+)\s+à\s+(\d+)\s+jours?",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return (int(match.group(1)), int(match.group(2)))
        return None

    async def _handle_temporal_query(
        self, query: str, entities: Dict, age_range: Tuple[int, int], start_time: float
    ) -> RAGResult:
        """Gère les requêtes temporelles (comparaison sur plage d'âges)"""

        try:
            logger.info(
                f"Traitement requête temporelle: âges {age_range[0]}-{age_range[1]} jours"
            )

            results = []
            successful_ages = []

            # Rechercher pour chaque âge dans la plage
            for age in range(age_range[0], age_range[1] + 1):
                entities_age = entities.copy()
                entities_age["age_days"] = age

                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=entities_age,
                    top_k=3,  # Moins de résultats par âge
                )

                if result and result.source != RAGSource.NO_RESULTS:
                    results.append(
                        {
                            "age": age,
                            "result": result,
                            "metrics": result.metadata.get("metrics", []),
                        }
                    )
                    successful_ages.append(age)

            if not results:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    answer=f"Aucune donnée trouvée pour la plage d'âges {age_range[0]}-{age_range[1]} jours.",
                    metadata={
                        "source_type": "temporal",
                        "age_range": age_range,
                        "processing_time": time.time() - start_time,
                    },
                )

            # Générer réponse temporelle
            answer = await self._generate_temporal_response(query, results, age_range)

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer,
                context_docs=[],
                confidence=0.85,
                metadata={
                    "source_type": "temporal",
                    "age_range": age_range,
                    "successful_ages": successful_ages,
                    "data_points": len(results),
                    "processing_time": time.time() - start_time,
                },
            )

        except Exception as e:
            logger.error(f"Erreur requête temporelle: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors du traitement de la requête temporelle.",
                metadata={
                    "error": str(e),
                    "source_type": "temporal_error",
                    "processing_time": time.time() - start_time,
                },
            )

    async def _generate_temporal_response(
        self, query: str, results: List[Dict], age_range: Tuple[int, int]
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
            metrics = result_data.get("metrics", [])

            if metrics:
                # Extraire les valeurs principales
                main_values = []
                for metric in metrics[:2]:  # Maximum 2 métriques principales
                    if "value" in metric:
                        main_values.append(
                            f"{metric.get('name', 'Métrique')}: {metric['value']}"
                        )

                if main_values:
                    response_parts.append(f"- {age} jours : {', '.join(main_values)}")

        return "\n".join(response_parts)

    async def _handle_out_of_range_age(
        self, query: str, age: int, entities: Dict, start_time: float
    ) -> RAGResult:
        """Gère les âges hors plage"""

        # Chercher l'âge le plus proche disponible
        closest_age = min(56, age)  # Max observé = 56 jours

        entities_fallback = entities.copy()
        entities_fallback["age_days"] = closest_age

        result = await self.postgresql_system.search_metrics(
            query=query, entities=entities_fallback, top_k=12
        )

        if result and result.source != RAGSource.NO_RESULTS:
            # Ajouter note d'extrapolation
            result.answer = (
                f"Données disponibles jusqu'à {closest_age} jours pour cette race. "
                + result.answer
            )
            result.metadata.update(
                {
                    "extrapolated": True,
                    "requested_age": age,
                    "provided_age": closest_age,
                    "processing_time": time.time() - start_time,
                }
            )

        return result

    def get_status(self) -> Dict:
        """Status système avec stats comparatives"""
        return {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "version": "v7.2_with_weaviate_integration",
            "modules": {
                "query_preprocessor": bool(self.query_preprocessor),
                "postgresql_system": bool(self.postgresql_system),
                "weaviate_core": bool(self.weaviate_core),  # NOUVEAU
                "comparison_handler": bool(self.comparison_handler),
            },
            "optimization_stats": self.optimization_stats.copy(),
            "capabilities": {
                "comparative_queries": bool(self.comparison_handler),
                "comparative_fallback": True,  # NOUVEAU
                "intelligent_preprocessing": bool(self.query_preprocessor),
                "metrics_queries": bool(self.postgresql_system),
                "weaviate_search": bool(self.weaviate_core),  # NOUVEAU
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

        # NOUVEAU: Fermeture Weaviate Core
        try:
            if self.weaviate_core:
                await self.weaviate_core.close()
        except Exception as e:
            logger.error(f"Erreur fermeture Weaviate Core: {e}")

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
