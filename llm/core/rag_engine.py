# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal - Version Corrigée Complète
Version 5.3 - Résolution de tous les problèmes identifiés

CORRECTIONS APPORTÉES:
1. Gestion sécurisée des imports avec fallbacks appropriés
2. Correction des erreurs RAGResult et RAGSource
3. Initialisation robuste avec gestion d'erreurs
4. Normalisation multilingue stable
5. Diagnostics améliorés pour le debugging
6. Correction des imports PostgreSQL et QueryType
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

# Imports standards placés en premier selon PEP 8
from config.config import (
    RAG_ENABLED,
    OPENAI_API_KEY,
    RAG_SIMILARITY_TOP_K,
    LANGSMITH_ENABLED,
)

# Import local des data models avec gestion d'erreur
try:
    from .data_models import RAGResult, RAGSource
except ImportError as e:
    logging.error(f"Erreur import data_models: {e}")
    raise

# Imports utilitaires avec fallbacks
try:
    from utils.imports_and_dependencies import (
        OPENAI_AVAILABLE,
        WEAVIATE_AVAILABLE,
        AsyncOpenAI,
    )
except ImportError as e:
    logging.warning(f"Imports dependencies partiels: {e}")
    OPENAI_AVAILABLE = False
    WEAVIATE_AVAILABLE = False
    AsyncOpenAI = None

try:
    from utils.utilities import METRICS, detect_language_enhanced
except ImportError as e:
    logging.warning(f"Utilities non disponibles: {e}")
    METRICS = None

    def detect_language_enhanced(text: str, default: str = "fr") -> str:
        """Fallback function for language detection"""
        return default


# Logger défini AVANT utilisation
logger = logging.getLogger(__name__)

# Imports des modules refactorisés avec gestion d'erreur robuste
POSTGRESQL_INTEGRATION_AVAILABLE = False
RAG_JSON_SYSTEM_AVAILABLE = False
WEAVIATE_CORE_AVAILABLE = False
LANGSMITH_INTEGRATION_AVAILABLE = False

PostgreSQLSystem = None
JSONSystem = None
WeaviateCore = None
LangSmithIntegration = None

# Import PostgreSQL System
try:
    from .rag_postgresql import PostgreSQLSystem

    POSTGRESQL_INTEGRATION_AVAILABLE = True
    logger.info("Système PostgreSQL avec normalisation multilingue importé")
except ImportError as e:
    logger.warning(f"PostgreSQL non disponible: {e}")
    PostgreSQLSystem = None
    POSTGRESQL_INTEGRATION_AVAILABLE = False

# Import JSON System
try:
    from .rag_json_system import JSONSystem

    RAG_JSON_SYSTEM_AVAILABLE = True
    logger.info("Système JSON importé")
except ImportError as e:
    logger.warning(f"JSON System non disponible: {e}")

# Import Weaviate Core
try:
    from .rag_weaviate_core import WeaviateCore

    WEAVIATE_CORE_AVAILABLE = True
    logger.info("Weaviate Core importé")
except ImportError as e:
    logger.warning(f"Weaviate Core non disponible: {e}")

# Import LangSmith
try:
    from .rag_langsmith import LangSmithIntegration

    LANGSMITH_INTEGRATION_AVAILABLE = True
    logger.info("LangSmith importé")
except ImportError as e:
    logger.warning(f"LangSmith non disponible: {e}")


class InteliaRAGEngine:
    """RAG Engine principal - Architecture modulaire avec normalisation multilingue"""

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialisation avec gestion d'erreurs robuste"""
        try:
            self.openai_client = openai_client or self._build_openai_client()
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            self.openai_client = None

        # Modules spécialisés
        self.postgresql_system = None
        self.json_system = None
        self.weaviate_core = None
        self.langsmith_integration = None

        # État
        self.is_initialized = False
        self.degraded_mode = False
        self.initialization_errors = []

        # Stats consolidées avec normalisation
        self.optimization_stats = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "postgresql_queries": 0,
            "json_searches": 0,
            "weaviate_searches": 0,
            "hybrid_queries": 0,
            "langsmith_traces": 0,
            # Stats normalisation multilingue
            "multilingual_queries": 0,
            "normalization_hits": 0,
            "concept_mappings_used": 0,
            "errors_count": 0,
        }

    def _build_openai_client(self) -> Optional[AsyncOpenAI]:
        """Client OpenAI avec configuration timeout et gestion d'erreurs"""
        if not OPENAI_AVAILABLE or not AsyncOpenAI:
            logger.warning("OpenAI non disponible")
            return None

        if not OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY non défini")
            return None

        try:
            # Essayer avec httpx pour timeout personnalisé
            try:
                import httpx

                http_client = httpx.AsyncClient(timeout=30.0)
                return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
            except ImportError:
                # Fallback sans httpx
                return AsyncOpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"Erreur création client OpenAI: {e}")
            return None

    async def initialize(self):
        """Initialisation modulaire avec gestion d'erreurs robuste"""
        if self.is_initialized:
            return

        logger.info("Initialisation RAG Engine v5.3 - Version corrigée complète")
        self.initialization_errors = []

        # Vérifications préliminaires
        if not OPENAI_AVAILABLE or not WEAVIATE_AVAILABLE:
            self.degraded_mode = True
            logger.warning("Mode dégradé activé - dépendances manquantes")

        try:
            # 1. Système PostgreSQL avec normalisation (optionnel)
            if POSTGRESQL_INTEGRATION_AVAILABLE and PostgreSQLSystem:
                await self._initialize_postgresql_system()

            # 2. Système JSON (optionnel)
            if RAG_JSON_SYSTEM_AVAILABLE and JSONSystem:
                await self._initialize_json_system()

            # 3. Weaviate Core (critique mais non bloquant)
            if WEAVIATE_CORE_AVAILABLE and WeaviateCore:
                await self._initialize_weaviate_core()
            else:
                logger.warning(
                    "Weaviate Core non disponible - fonctionnalités limitées"
                )

            # 4. LangSmith (complètement optionnel)
            if (
                LANGSMITH_INTEGRATION_AVAILABLE
                and LangSmithIntegration
                and LANGSMITH_ENABLED
            ):
                await self._initialize_langsmith()

            self.is_initialized = True

            # Log du statut final
            active_modules = [
                name
                for name, module in [
                    ("PostgreSQL", self.postgresql_system),
                    ("JSON", self.json_system),
                    ("Weaviate", self.weaviate_core),
                    ("LangSmith", self.langsmith_integration),
                ]
                if module is not None
            ]

            logger.info(f"RAG Engine initialisé - Modules actifs: {active_modules}")

            if self.initialization_errors:
                logger.warning(
                    f"Erreurs d'initialisation: {self.initialization_errors}"
                )

        except Exception as e:
            logger.error(f"Erreur initialisation critique: {e}")
            self.degraded_mode = True
            self.is_initialized = True
            self.initialization_errors.append(str(e))

    async def _initialize_postgresql_system(self):
        """Initialise le système PostgreSQL avec gestion d'erreurs"""
        try:
            self.postgresql_system = PostgreSQLSystem()
            await self.postgresql_system.initialize()
            logger.info("Système PostgreSQL avec normalisation initialisé")
        except Exception as e:
            logger.warning(f"PostgreSQL System échoué: {e}")
            self.postgresql_system = None
            self.initialization_errors.append(f"PostgreSQL: {e}")

    async def _initialize_json_system(self):
        """Initialise le système JSON avec gestion d'erreurs"""
        try:
            self.json_system = JSONSystem()
            await self.json_system.initialize()
            logger.info("Système JSON initialisé")
        except Exception as e:
            logger.warning(f"JSON System échoué: {e}")
            self.json_system = None
            self.initialization_errors.append(f"JSON: {e}")

    async def _initialize_weaviate_core(self):
        """Initialise Weaviate Core avec gestion d'erreurs"""
        try:
            self.weaviate_core = WeaviateCore(self.openai_client)
            await self.weaviate_core.initialize()
            logger.info("Weaviate Core initialisé")
        except Exception as e:
            logger.warning(f"Weaviate Core échoué: {e}")
            self.weaviate_core = None
            self.initialization_errors.append(f"Weaviate: {e}")

    async def _initialize_langsmith(self):
        """Initialise LangSmith avec gestion d'erreurs"""
        try:
            self.langsmith_integration = LangSmithIntegration()
            await self.langsmith_integration.initialize()
            logger.info("LangSmith initialisé")
        except Exception as e:
            logger.warning(f"LangSmith échoué: {e}")
            self.langsmith_integration = None
            self.initialization_errors.append(f"LangSmith: {e}")

    async def generate_response(
        self,
        query: str,
        tenant_id: str = "default",
        conversation_context: List[Dict] = None,
        language: Optional[str] = None,
        explain_score: Optional[float] = None,
        use_json_search: bool = True,
        genetic_line_filter: Optional[str] = None,
        performance_context: Optional[Dict[str, Any]] = None,
    ) -> RAGResult:
        """Point d'entrée principal avec gestion d'erreurs robuste"""

        if not self.is_initialized:
            logger.warning("RAG Engine non initialisé - tentative d'initialisation")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Échec initialisation: {e}")

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1

        if METRICS:
            METRICS.inc("requests_total")

        # Validation des entrées
        if not query or not query.strip():
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={
                    "error": "Query vide",
                    "processing_time": time.time() - start_time,
                },
            )

        # Fallback si système complètement indisponible
        if self.degraded_mode and not any(
            [self.postgresql_system, self.json_system, self.weaviate_core]
        ):
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                answer="Le système RAG n'est pas disponible actuellement.",
                metadata={
                    "reason": "tous_modules_indisponibles",
                    "processing_time": time.time() - start_time,
                    "initialization_errors": self.initialization_errors,
                },
            )

        try:
            # Détection de normalisation nécessaire
            needs_normalization = self._detect_multilingual_query(query)
            if needs_normalization:
                self.optimization_stats["multilingual_queries"] += 1
                logger.debug(f"Requête multilingue détectée: {query}")

            # LangSmith si disponible
            if self.langsmith_integration:
                try:
                    return (
                        await self.langsmith_integration.generate_response_with_tracing(
                            query,
                            tenant_id,
                            conversation_context,
                            language,
                            explain_score,
                            use_json_search,
                            genetic_line_filter,
                            performance_context,
                            self,
                        )
                    )
                except Exception as e:
                    logger.warning(f"LangSmith échec, fallback: {e}")

            # Traitement core
            return await self._generate_response_core(
                query,
                tenant_id,
                conversation_context,
                language,
                explain_score,
                use_json_search,
                genetic_line_filter,
                performance_context,
                start_time,
            )

        except Exception as e:
            logger.error(f"Erreur generate_response: {e}")
            self.optimization_stats["errors_count"] += 1
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                    "query": query[:100] + "..." if len(query) > 100 else query,
                },
            )

    def _detect_multilingual_query(self, query: str) -> bool:
        """Détecte si une requête nécessitera une normalisation multilingue"""
        if not self.postgresql_system or not self.postgresql_system.postgres_retriever:
            return False

        try:
            normalizer = self.postgresql_system.postgres_retriever.query_normalizer
            normalized_concepts, _ = normalizer.get_search_terms(query)
            return len(normalized_concepts) > 0
        except Exception as e:
            logger.debug(f"Erreur détection multilingue: {e}")
            return False

    async def _generate_response_core(
        self,
        query: str,
        tenant_id: str,
        conversation_context: List[Dict],
        language: Optional[str],
        explain_score: Optional[float],
        use_json_search: bool,
        genetic_line_filter: Optional[str],
        performance_context: Optional[Dict[str, Any]],
        start_time: float,
    ) -> RAGResult:
        """Méthode core avec routage intelligent et normalisation multilingue"""

        try:
            # Détection langue
            if not language:
                if detect_language_enhanced:
                    try:
                        language = detect_language_enhanced(query, default="fr")
                    except Exception:
                        language = "fr"
                else:
                    language = "fr"

            # Routage intelligent PostgreSQL
            if self.postgresql_system and self.postgresql_system.query_router:
                try:
                    query_type = self.postgresql_system.route_query(query, None)

                    if query_type and hasattr(query_type, "value"):
                        query_type_value = query_type.value
                    else:
                        query_type_value = str(query_type) if query_type else None

                    if query_type_value == "metrics":
                        logger.info("Requête routée vers PostgreSQL (métriques)")
                        result = await self._search_postgresql_with_normalization(
                            query, None, top_k=RAG_SIMILARITY_TOP_K
                        )
                        if result and result.source != RAGSource.NO_RESULTS:
                            return result
                        logger.warning("PostgreSQL sans résultats, fallback")

                    elif query_type_value == "hybrid":
                        logger.info("Requête routée vers recherche hybride")
                        self.optimization_stats["hybrid_queries"] += 1
                        return await self._search_hybrid_sources_with_normalization(
                            query, conversation_context, language, start_time
                        )
                except Exception as e:
                    logger.warning(f"Erreur routage PostgreSQL: {e}")

            # JSON Search si demandé et disponible
            if use_json_search and self.json_system:
                try:
                    json_results = await self.json_system.search_enhanced(
                        query=query,
                        genetic_line=genetic_line_filter,
                        performance_metrics=(
                            performance_context.get("metrics")
                            if performance_context
                            else None
                        ),
                    )

                    if json_results and len(json_results) >= 3:
                        self.optimization_stats["json_searches"] += 1
                        return await self._generate_response_from_json_results(
                            query,
                            json_results,
                            language,
                            conversation_context,
                            start_time,
                        )
                except Exception as e:
                    logger.warning(f"Erreur JSON search: {e}")

            # Fallback Weaviate
            if self.weaviate_core:
                logger.info("Utilisation Weaviate (fallback)")
                try:
                    return await self._generate_response_core_weaviate_only(
                        query,
                        None,
                        conversation_context,
                        language,
                        start_time,
                        tenant_id,
                    )
                except Exception as e:
                    logger.error(f"Erreur Weaviate: {e}")

            # Fallback ultime
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                answer="Aucun résultat trouvé dans les sources disponibles.",
                metadata={
                    "processing_time": time.time() - start_time,
                    "available_modules": [
                        name
                        for name, module in [
                            ("postgresql", self.postgresql_system),
                            ("json", self.json_system),
                            ("weaviate", self.weaviate_core),
                        ]
                        if module is not None
                    ],
                },
            )

        except Exception as e:
            logger.error(f"Erreur génération réponse core: {e}")
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e), "processing_time": time.time() - start_time},
            )

    async def _search_postgresql_with_normalization(
        self, query: str, intent_result, top_k: int = 10
    ) -> RAGResult:
        """Recherche PostgreSQL avec tracking de normalisation"""
        if not self.postgresql_system:
            return RAGResult(source=RAGSource.NO_RESULTS)

        try:
            # Capturer les concepts avant recherche
            if self.postgresql_system.postgres_retriever:
                normalizer = self.postgresql_system.postgres_retriever.query_normalizer
                normalized_concepts, _ = normalizer.get_search_terms(query)

                if normalized_concepts:
                    self.optimization_stats["normalization_hits"] += 1
                    self.optimization_stats["concept_mappings_used"] += len(
                        normalized_concepts
                    )
                    logger.debug(
                        f"Concepts normalisés utilisés: {normalized_concepts[:3]}"
                    )

            # Recherche avec normalisation
            result = await self.postgresql_system.search_metrics(
                query, intent_result, top_k
            )

            # Enrichir les métadonnées avec info normalisation
            if result and result.metadata and normalized_concepts:
                result.metadata["normalization_applied"] = True
                result.metadata["original_query"] = query
                result.metadata["concept_count"] = len(normalized_concepts)

            return result

        except Exception as e:
            logger.error(f"Erreur PostgreSQL avec normalisation: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "postgresql_normalized"},
            )

    async def _search_hybrid_sources_with_normalization(
        self,
        query: str,
        conversation_context: List[Dict],
        language: str,
        start_time: float,
    ) -> RAGResult:
        """Recherche hybride avec normalisation intégrée"""
        try:
            tasks = []

            # PostgreSQL avec normalisation
            if self.postgresql_system:
                tasks.append(self._search_postgresql_with_normalization(query, None))

            # Weaviate
            if self.weaviate_core:
                tasks.append(
                    self.weaviate_core.generate_response(
                        query,
                        None,
                        conversation_context,
                        language,
                        start_time,
                        "default",
                    )
                )

            if not tasks:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    metadata={
                        "source_type": "hybrid",
                        "reason": "no_sources_available",
                    },
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return self._merge_hybrid_results_with_normalization(
                results, query, start_time
            )

        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "hybrid_normalized"},
            )

    def _merge_hybrid_results_with_normalization(
        self, results: List, query: str, start_time: float
    ) -> RAGResult:
        """Fusionne les résultats hybrides en priorisant les résultats normalisés"""
        valid_results = [
            r
            for r in results
            if isinstance(r, RAGResult) and not isinstance(r, Exception)
        ]

        if not valid_results:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                metadata={
                    "source_type": "hybrid_normalized",
                    "processing_time": time.time() - start_time,
                },
            )

        # Prioriser les résultats avec normalisation appliquée
        normalized_results = [
            r
            for r in valid_results
            if r.metadata and r.metadata.get("normalization_applied")
        ]

        if normalized_results:
            best_result = max(normalized_results, key=lambda r: r.confidence)
            logger.info("Résultat normalisé sélectionné comme meilleur")
        else:
            best_result = max(valid_results, key=lambda r: r.confidence)

        # Enrichir les métadonnées
        best_result.metadata.update(
            {
                "source_type": "hybrid_normalized",
                "results_merged": len(valid_results),
                "normalized_results_count": len(normalized_results),
                "processing_time": time.time() - start_time,
            }
        )

        return best_result

    async def _generate_response_core_weaviate_only(
        self,
        query: str,
        intent_result,
        conversation_context: List[Dict],
        language: str,
        start_time: float,
        tenant_id: str,
    ) -> RAGResult:
        """Méthode Weaviate avec gestion d'erreurs"""
        if not self.weaviate_core:
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": "Weaviate Core non disponible"},
            )

        try:
            self.optimization_stats["weaviate_searches"] += 1
            return await self.weaviate_core.generate_response(
                query,
                intent_result,
                conversation_context,
                language,
                start_time,
                tenant_id,
            )
        except Exception as e:
            logger.error(f"Erreur Weaviate Core: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "weaviate"},
            )

    async def _generate_response_from_json_results(
        self,
        query: str,
        json_results: List[Dict[str, Any]],
        language: str,
        conversation_context: List[Dict],
        start_time: float,
    ) -> RAGResult:
        """Génère réponse depuis résultats JSON"""
        if not self.json_system:
            return RAGResult(source=RAGSource.INTERNAL_ERROR)

        try:
            return await self.json_system.generate_response_from_results(
                query, json_results, language, conversation_context, start_time
            )
        except Exception as e:
            logger.error(f"Erreur génération JSON: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "json"},
            )

    def get_status(self) -> Dict:
        """Status système complet avec informations de normalisation"""
        base_status = {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "approach": "enhanced_rag_v5.3_corrected",
            "modules": {
                "postgresql_system": bool(self.postgresql_system),
                "json_system": bool(self.json_system),
                "weaviate_core": bool(self.weaviate_core),
                "langsmith_integration": bool(self.langsmith_integration),
            },
            "optimization_stats": self.optimization_stats.copy(),
            "processing_capabilities": {
                "metrics_queries": bool(self.postgresql_system),
                "json_search": bool(self.json_system),
                "knowledge_base": bool(self.weaviate_core),
                "hybrid_search": bool(self.postgresql_system and self.weaviate_core),
                "monitoring": bool(self.langsmith_integration),
                "multilingual_normalization": bool(self.postgresql_system),
            },
            "initialization_errors": self.initialization_errors,
        }

        # Ajouter les statistiques de normalisation
        if self.postgresql_system:
            try:
                norm_status = self.postgresql_system.get_normalization_status()
                base_status["multilingual_normalization"] = norm_status

                # Statistiques d'utilisation
                base_status["normalization_stats"] = {
                    "multilingual_queries": self.optimization_stats[
                        "multilingual_queries"
                    ],
                    "normalization_hits": self.optimization_stats["normalization_hits"],
                    "concept_mappings_used": self.optimization_stats[
                        "concept_mappings_used"
                    ],
                    "normalization_hit_rate": (
                        (
                            self.optimization_stats["normalization_hits"]
                            / max(1, self.optimization_stats["multilingual_queries"])
                        )
                        * 100
                        if self.optimization_stats["multilingual_queries"] > 0
                        else 0
                    ),
                }
            except Exception as e:
                logger.warning(f"Erreur récupération stats normalisation: {e}")

        return base_status

    def get_multilingual_diagnostics(self, query: str) -> Dict[str, Any]:
        """Diagnostics détaillés pour le débogage de la normalisation multilingue"""
        if not self.postgresql_system or not self.postgresql_system.postgres_retriever:
            return {"available": False, "reason": "PostgreSQL system not available"}

        try:
            normalizer = self.postgresql_system.postgres_retriever.query_normalizer
            normalized_concepts, raw_words = normalizer.get_search_terms(query)

            # Analyser quel concept a déclenché quoi
            triggered_mappings = {}
            query_lower = query.lower()

            for concept, terms in normalizer.CONCEPT_MAPPINGS.items():
                matches = [term for term in terms if term in query_lower]
                if matches:
                    triggered_mappings[concept] = {
                        "matched_terms": matches,
                        "all_mapped_terms": terms,
                        "expansion_count": len(terms),
                    }

            return {
                "available": True,
                "original_query": query,
                "detected_language": (
                    detect_language_enhanced(query, default="fr")
                    if detect_language_enhanced
                    else "fr"
                ),
                "normalization_applied": len(normalized_concepts) > 0,
                "normalized_concepts": normalized_concepts,
                "raw_words": raw_words,
                "triggered_mappings": triggered_mappings,
                "total_concept_expansions": len(normalized_concepts),
                "would_improve_search": len(triggered_mappings) > 0,
                "debug_info": {
                    "query_length": len(query),
                    "word_count": len(query.split()),
                    "concept_mappings_available": len(normalizer.CONCEPT_MAPPINGS),
                    "total_terms_in_mappings": sum(
                        len(terms) for terms in normalizer.CONCEPT_MAPPINGS.values()
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Erreur diagnostics multilingues: {e}")
            return {"available": False, "error": str(e)}

    async def close(self):
        """Fermeture propre de tous les modules"""
        logger.info("Fermeture RAG Engine...")

        try:
            if self.postgresql_system:
                await self.postgresql_system.close()
        except Exception as e:
            logger.error(f"Erreur fermeture PostgreSQL: {e}")

        try:
            if self.json_system:
                await self.json_system.close()
        except Exception as e:
            logger.error(f"Erreur fermeture JSON: {e}")

        try:
            if self.weaviate_core:
                await self.weaviate_core.close()
        except Exception as e:
            logger.error(f"Erreur fermeture Weaviate: {e}")

        try:
            if self.langsmith_integration:
                await self.langsmith_integration.close()
        except Exception as e:
            logger.error(f"Erreur fermeture LangSmith: {e}")

        logger.info("RAG Engine fermé proprement")


# Factory function pour compatibilité
def create_rag_engine(openai_client=None) -> InteliaRAGEngine:
    """Factory pour créer une instance RAG Engine"""
    return InteliaRAGEngine(openai_client)


# Fonction utilitaire pour tester la normalisation
async def test_multilingual_normalization(
    query: str, openai_client=None
) -> Dict[str, Any]:
    """Fonction de test pour la normalisation multilingue"""
    engine = InteliaRAGEngine(openai_client)

    try:
        await engine.initialize()

        if not engine.postgresql_system:
            return {"error": "PostgreSQL system not available for testing"}

        # Diagnostics complets
        diagnostics = engine.get_multilingual_diagnostics(query)

        # Test de recherche si possible
        search_result = None
        try:
            search_result = await engine._search_postgresql_with_normalization(
                query, None, top_k=5
            )
            diagnostics["search_test"] = {
                "success": search_result.source != RAGSource.NO_RESULTS,
                "results_count": (
                    len(search_result.context_docs) if search_result.context_docs else 0
                ),
                "confidence": search_result.confidence,
                "source": (
                    search_result.source.value
                    if hasattr(search_result.source, "value")
                    else str(search_result.source)
                ),
            }
        except Exception as e:
            diagnostics["search_test"] = {"error": str(e)}

        return diagnostics

    except Exception as e:
        logger.error(f"Erreur test normalisation: {e}")
        return {"error": str(e)}

    finally:
        try:
            await engine.close()
        except Exception as e:
            logger.error(f"Erreur fermeture engine de test: {e}")


# Fonction utilitaire pour diagnostics système
async def diagnose_rag_system() -> Dict[str, Any]:
    """Diagnostique complet du système RAG"""
    diagnostics = {
        "timestamp": time.time(),
        "modules_availability": {
            "postgresql": POSTGRESQL_INTEGRATION_AVAILABLE,
            "json_system": RAG_JSON_SYSTEM_AVAILABLE,
            "weaviate_core": WEAVIATE_CORE_AVAILABLE,
            "langsmith": LANGSMITH_INTEGRATION_AVAILABLE,
        },
        "dependencies": {
            "openai": OPENAI_AVAILABLE,
            "weaviate": WEAVIATE_AVAILABLE,
            "asyncpg": POSTGRESQL_INTEGRATION_AVAILABLE,
        },
        "config": {
            "rag_enabled": RAG_ENABLED,
            "langsmith_enabled": LANGSMITH_ENABLED,
            "openai_key_present": bool(OPENAI_API_KEY),
        },
    }

    # Test d'initialisation rapide
    engine = InteliaRAGEngine()
    try:
        await engine.initialize()
        diagnostics["initialization"] = {
            "success": engine.is_initialized,
            "degraded_mode": engine.degraded_mode,
            "errors": engine.initialization_errors,
            "active_modules": [
                name
                for name, module in [
                    ("postgresql", engine.postgresql_system),
                    ("json", engine.json_system),
                    ("weaviate", engine.weaviate_core),
                    ("langsmith", engine.langsmith_integration),
                ]
                if module is not None
            ],
        }

        # Status détaillé si possible
        if engine.is_initialized:
            diagnostics["status"] = engine.get_status()

    except Exception as e:
        diagnostics["initialization"] = {"success": False, "error": str(e)}

    finally:
        try:
            await engine.close()
        except Exception as e:
            logger.error(f"Erreur fermeture diagnostics: {e}")

    return diagnostics
