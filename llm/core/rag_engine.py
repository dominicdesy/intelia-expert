# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal - Version Améliorée avec Normalisation Multilingue
Version 5.2 - Intégration du système de normalisation pour résoudre les problèmes multilingues

AMÉLIORATIONS APPORTÉES:
1. Intégration complète du système de normalisation multilingue
2. Confidence scoring amélioré pour les recherches normalisées
3. Métriques de performance pour le système de normalisation
4. Diagnostics étendus pour le debugging multilingue
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
from utils.imports_and_dependencies import (
    OPENAI_AVAILABLE,
    WEAVIATE_AVAILABLE,
    AsyncOpenAI,
)
from utils.utilities import METRICS, detect_language_enhanced

# Import local des data models
from .data_models import RAGResult, RAGSource

# Logger défini AVANT utilisation
logger = logging.getLogger(__name__)

# Imports des modules refactorisés avec gestion d'erreur
try:
    from .rag_postgresql import PostgreSQLSystem, QueryType

    POSTGRESQL_INTEGRATION_AVAILABLE = True
    logger.info("✅ Système PostgreSQL avec normalisation multilingue importé")
except ImportError as e:
    POSTGRESQL_INTEGRATION_AVAILABLE = False
    logger.warning(f"⚠️ PostgreSQL non disponible: {e}")
    QueryType = None

try:
    from .rag_json_system import JSONSystem

    RAG_JSON_SYSTEM_AVAILABLE = True
    logger.info("✅ Système JSON importé")
except ImportError as e:
    RAG_JSON_SYSTEM_AVAILABLE = False
    logger.warning(f"⚠️ JSON non disponible: {e}")

try:
    from .rag_weaviate_core import WeaviateCore

    WEAVIATE_CORE_AVAILABLE = True
    logger.info("✅ Weaviate Core importé")
except ImportError as e:
    WEAVIATE_CORE_AVAILABLE = False
    logger.warning(f"⚠️ Weaviate Core non disponible: {e}")

try:
    from .rag_langsmith import LangSmithIntegration

    LANGSMITH_INTEGRATION_AVAILABLE = True
    logger.info("✅ LangSmith importé")
except ImportError as e:
    LANGSMITH_INTEGRATION_AVAILABLE = False
    logger.warning(f"⚠️ LangSmith non disponible: {e}")


class InteliaRAGEngine:
    """RAG Engine principal - Architecture modulaire avec normalisation multilingue"""

    def __init__(self, openai_client: AsyncOpenAI = None):
        self.openai_client = openai_client or self._build_openai_client()

        # Modules spécialisés
        self.postgresql_system = None
        self.json_system = None
        self.weaviate_core = None
        self.langsmith_integration = None

        # État
        self.is_initialized = False
        self.degraded_mode = False

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
            # NOUVEAU: Stats normalisation multilingue
            "multilingual_queries": 0,
            "normalization_hits": 0,
            "concept_mappings_used": 0,
        }

    def _build_openai_client(self) -> AsyncOpenAI:
        """Client OpenAI avec configuration timeout"""
        try:
            import httpx

            http_client = httpx.AsyncClient(timeout=30.0)
            return AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
        except Exception as e:
            logger.warning(f"Erreur client OpenAI: {e}")
            return AsyncOpenAI(api_key=OPENAI_API_KEY)

    async def initialize(self):
        """Initialisation modulaire avec support normalisation"""
        if self.is_initialized:
            return

        logger.info(
            "🚀 Initialisation RAG Engine v5.2 - Normalisation multilingue intégrée"
        )

        if not OPENAI_AVAILABLE or not WEAVIATE_AVAILABLE:
            self.degraded_mode = True
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return

        try:
            # 1. Système PostgreSQL avec normalisation
            if POSTGRESQL_INTEGRATION_AVAILABLE:
                await self._initialize_postgresql_system()

            # 2. Système JSON
            if RAG_JSON_SYSTEM_AVAILABLE:
                await self._initialize_json_system()

            # 3. Weaviate Core (obligatoire)
            if WEAVIATE_CORE_AVAILABLE:
                await self._initialize_weaviate_core()
            else:
                raise Exception("Weaviate Core requis")

            # 4. LangSmith (optionnel)
            if LANGSMITH_INTEGRATION_AVAILABLE and LANGSMITH_ENABLED:
                await self._initialize_langsmith()

            self.is_initialized = True
            logger.info("✅ RAG Engine v5.2 initialisé avec succès")

            # NOUVEAU: Log du statut de normalisation
            if self.postgresql_system:
                norm_status = self.postgresql_system.get_normalization_status()
                if norm_status.get("available"):
                    logger.info(
                        f"🌍 Normalisation multilingue: {norm_status['supported_concepts']}"
                    )

        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            self.degraded_mode = True
            self.is_initialized = True

    async def _initialize_postgresql_system(self):
        """Initialise le système PostgreSQL avec normalisation"""
        try:
            self.postgresql_system = PostgreSQLSystem()
            await self.postgresql_system.initialize()
            logger.info("✅ Système PostgreSQL avec normalisation initialisé")
        except Exception as e:
            logger.warning(f"PostgreSQL échoué: {e}")
            self.postgresql_system = None

    async def _initialize_json_system(self):
        """Initialise le système JSON"""
        try:
            self.json_system = JSONSystem()
            await self.json_system.initialize()
            logger.info("✅ Système JSON initialisé")
        except Exception as e:
            logger.warning(f"JSON échoué: {e}")
            self.json_system = None

    async def _initialize_weaviate_core(self):
        """Initialise Weaviate Core"""
        try:
            self.weaviate_core = WeaviateCore(self.openai_client)
            await self.weaviate_core.initialize()
            logger.info("✅ Weaviate Core initialisé")
        except Exception as e:
            logger.error(f"Weaviate Core échoué: {e}")
            raise

    async def _initialize_langsmith(self):
        """Initialise LangSmith"""
        try:
            self.langsmith_integration = LangSmithIntegration()
            await self.langsmith_integration.initialize()
            logger.info("✅ LangSmith initialisé")
        except Exception as e:
            logger.warning(f"LangSmith échoué: {e}")
            self.langsmith_integration = None

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
        """Point d'entrée principal avec détection automatique de normalisation"""

        if self.degraded_mode:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "degraded_mode"}
            )

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1
        METRICS.inc("requests_total")

        # NOUVEAU: Détection si normalisation sera nécessaire
        needs_normalization = self._detect_multilingual_query(query)
        if needs_normalization:
            self.optimization_stats["multilingual_queries"] += 1
            logger.debug(f"🌍 Requête multilingue détectée: {query}")

        # LangSmith si disponible
        if self.langsmith_integration:
            return await self.langsmith_integration.generate_response_with_tracing(
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

    def _detect_multilingual_query(self, query: str) -> bool:
        """
        Détecte si une requête nécessitera une normalisation multilingue
        NOUVEAU: Aide à optimiser les statistiques
        """
        if not self.postgresql_system or not self.postgresql_system.postgres_retriever:
            return False

        normalizer = self.postgresql_system.postgres_retriever.query_normalizer
        normalized_concepts, _ = normalizer.get_search_terms(query)

        # Si des concepts ont été normalisés, c'est multilingue
        return len(normalized_concepts) > 0

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
                language = detect_language_enhanced(query, default="fr")

            # NOUVEAU: Routage intelligent avec support normalisation
            if self.postgresql_system and self.postgresql_system.query_router:
                query_type = self.postgresql_system.route_query(query, None)

                if query_type == QueryType.METRICS:
                    logger.info(
                        "🎯 Requête routée vers PostgreSQL (métriques avec normalisation)"
                    )
                    result = await self._search_postgresql_with_normalization(
                        query, None, top_k=RAG_SIMILARITY_TOP_K
                    )
                    if result.source != RAGSource.NO_RESULTS:
                        return result
                    # Fallback vers Weaviate si pas de résultats
                    logger.warning("PostgreSQL sans résultats, fallback vers Weaviate")

                elif query_type == QueryType.HYBRID:
                    logger.info(
                        "🔄 Requête routée vers recherche hybride avec normalisation"
                    )
                    self.optimization_stats["hybrid_queries"] += 1
                    return await self._search_hybrid_sources_with_normalization(
                        query, conversation_context, language, start_time
                    )

            # JSON Search prioritaire
            if use_json_search and self.json_system:
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
                        query, json_results, language, conversation_context, start_time
                    )

            # Fallback Weaviate
            logger.info("📚 Utilisation Weaviate (fallback)")
            return await self._generate_response_core_weaviate_only(
                query, None, conversation_context, language, start_time, tenant_id
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
        """
        Recherche PostgreSQL avec tracking de normalisation
        NOUVEAU: Collecte des métriques de normalisation
        """
        if not self.postgresql_system:
            return RAGResult(source=RAGSource.NO_RESULTS)

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
                    f"🔧 Concepts normalisés utilisés: {normalized_concepts[:3]}..."
                )

        # Recherche avec normalisation
        result = await self.postgresql_system.search_metrics(
            query, intent_result, top_k
        )

        # Enrichir les métadonnées avec info normalisation
        if result.metadata and normalized_concepts:
            result.metadata["normalization_applied"] = True
            result.metadata["original_query"] = query
            result.metadata["concept_count"] = len(normalized_concepts)

        return result

    async def _search_hybrid_sources_with_normalization(
        self,
        query: str,
        conversation_context: List[Dict],
        language: str,
        start_time: float,
    ) -> RAGResult:
        """Recherche hybride avec normalisation intégrée"""
        try:
            # Recherche parallèle
            tasks = []

            if self.postgresql_system:
                tasks.append(self._search_postgresql_with_normalization(query, None))

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

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Fusion des résultats avec priorité aux résultats normalisés
            return self._merge_hybrid_results_with_normalization(
                results, query, start_time
            )

        except Exception as e:
            logger.error(f"Erreur recherche hybride avec normalisation: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "hybrid_normalized"},
            )

    def _merge_hybrid_results_with_normalization(
        self, results: List, query: str, start_time: float
    ) -> RAGResult:
        """
        Fusionne les résultats hybrides en priorisant les résultats normalisés
        NOUVEAU: Priorité aux résultats avec normalisation multilingue
        """
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
            logger.info("🌍 Résultat normalisé sélectionné comme meilleur")
        else:
            best_result = max(valid_results, key=lambda r: r.confidence)

        # Enrichir les métadonnées
        best_result.metadata["source_type"] = "hybrid_normalized"
        best_result.metadata["results_merged"] = len(valid_results)
        best_result.metadata["normalized_results_count"] = len(normalized_results)

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
        """Méthode Weaviate avec start_time"""

        if not self.weaviate_core:
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": "Weaviate Core non disponible"},
            )

        self.optimization_stats["weaviate_searches"] += 1

        # Déléguer à Weaviate Core
        return await self.weaviate_core.generate_response(
            query, intent_result, conversation_context, language, start_time, tenant_id
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

        return await self.json_system.generate_response_from_results(
            query, json_results, language, conversation_context, start_time
        )

    def get_status(self) -> Dict:
        """Status système complet avec informations de normalisation"""
        base_status = {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "approach": "enhanced_rag_v5.2_multilingual_normalization",
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
                "multilingual_normalization": bool(self.postgresql_system),  # NOUVEAU
            },
        }

        # NOUVEAU: Ajouter les statistiques de normalisation
        if self.postgresql_system:
            norm_status = self.postgresql_system.get_normalization_status()
            base_status["multilingual_normalization"] = norm_status

            # Statistiques d'utilisation
            base_status["normalization_stats"] = {
                "multilingual_queries": self.optimization_stats["multilingual_queries"],
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

        return base_status

    def get_multilingual_diagnostics(self, query: str) -> Dict[str, Any]:
        """
        Diagnostics détaillés pour le débogage de la normalisation multilingue
        NOUVEAU: Aide au debugging des problèmes de recherche
        """
        if not self.postgresql_system or not self.postgresql_system.postgres_retriever:
            return {"available": False, "reason": "PostgreSQL system not available"}

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
            "detected_language": detect_language_enhanced(query, default="fr"),
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

    async def close(self):
        """Fermeture propre de tous les modules"""

        if self.postgresql_system:
            await self.postgresql_system.close()

        if self.json_system:
            await self.json_system.close()

        if self.weaviate_core:
            await self.weaviate_core.close()

        if self.langsmith_integration:
            await self.langsmith_integration.close()

        logger.info("RAG Engine fermé proprement")


# Factory function pour compatibilité
def create_rag_engine(openai_client=None) -> InteliaRAGEngine:
    """Factory pour créer une instance RAG Engine"""
    return InteliaRAGEngine(openai_client)


# NOUVEAU: Fonction utilitaire pour tester la normalisation
async def test_multilingual_normalization(
    query: str, openai_client=None
) -> Dict[str, Any]:
    """
    Fonction de test pour la normalisation multilingue
    Utile pour déboguer les problèmes de recherche
    """
    engine = InteliaRAGEngine(openai_client)
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
                len(search_result.documents) if search_result.documents else 0
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

    await engine.close()
    return diagnostics
