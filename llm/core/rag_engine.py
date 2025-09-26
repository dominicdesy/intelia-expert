# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal - Version Refactorisée
Version 5.1 - Architecture modulaire pour maintenabilité

CORRECTIONS CRITIQUES APPORTÉES:
1. Ajout du paramètre start_time manquant dans _generate_response_core_weaviate_only()
2. Exclusion des termes techniques de la traduction automatique  
3. Refactorisation modulaire pour réduire la taille du fichier
"""

import os
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# CORRECTION CRITIQUE: Logger défini AVANT utilisation
logger = logging.getLogger(__name__)

# Imports des modules refactorisés
try:
    from .rag_postgresql import PostgreSQLSystem, QueryRouter, QueryType
    POSTGRESQL_INTEGRATION_AVAILABLE = True
    logger.info("✅ Système PostgreSQL importé")
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

# Imports existants conservés
from config.config import *
from utils.imports_and_dependencies import OPENAI_AVAILABLE, WEAVIATE_AVAILABLE, AsyncOpenAI
from .data_models import RAGResult, RAGSource, Document
from utils.utilities import METRICS, detect_language_enhanced


class InteliaRAGEngine:
    """RAG Engine principal - Architecture modulaire"""

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
        
        # Stats consolidées
        self.optimization_stats = {
            "requests_total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "postgresql_queries": 0,
            "json_searches": 0,
            "weaviate_searches": 0,
            "hybrid_queries": 0,
            "langsmith_traces": 0,
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
        """Initialisation modulaire"""
        if self.is_initialized:
            return

        logger.info("🚀 Initialisation RAG Engine v5.1 - Architecture modulaire")

        if not OPENAI_AVAILABLE or not WEAVIATE_AVAILABLE:
            self.degraded_mode = True
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return

        try:
            # 1. Système PostgreSQL
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
            logger.info("✅ RAG Engine v5.1 initialisé avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            self.degraded_mode = True
            self.is_initialized = True

    async def _initialize_postgresql_system(self):
        """Initialise le système PostgreSQL"""
        try:
            self.postgresql_system = PostgreSQLSystem()
            await self.postgresql_system.initialize()
            logger.info("✅ Système PostgreSQL initialisé")
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
        """Point d'entrée principal - CORRIGÉ avec routage intelligent"""

        if self.degraded_mode:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED, 
                metadata={"reason": "degraded_mode"}
            )

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1
        METRICS.inc("requests_total")

        # LangSmith si disponible
        if self.langsmith_integration:
            return await self.langsmith_integration.generate_response_with_tracing(
                query, tenant_id, conversation_context, language, explain_score,
                use_json_search, genetic_line_filter, performance_context,
                self
            )

        return await self._generate_response_core(
            query, tenant_id, conversation_context, language, explain_score,
            use_json_search, genetic_line_filter, performance_context, start_time
        )

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
        start_time: float  # CORRECTION: Paramètre ajouté
    ) -> RAGResult:
        """Méthode core avec routage intelligent - CORRIGÉE"""

        try:
            # Détection langue
            if not language:
                language = detect_language_enhanced(query, default="fr")

            # NOUVEAU: Routage intelligent des requêtes
            if self.postgresql_system and self.postgresql_system.query_router:
                query_type = self.postgresql_system.route_query(query, None)
                
                if query_type == QueryType.METRICS:
                    logger.info("🎯 Requête routée vers PostgreSQL (métriques)")
                    result = await self.postgresql_system.search_metrics(
                        query, None, top_k=RAG_SIMILARITY_TOP_K
                    )
                    if result.source != RAGSource.NO_RESULTS:
                        return result
                    # Fallback vers Weaviate si pas de résultats
                    logger.warning("PostgreSQL non disponible, fallback vers Weaviate")

                elif query_type == QueryType.HYBRID:
                    logger.info("🔄 Requête routée vers recherche hybride")
                    self.optimization_stats["hybrid_queries"] += 1
                    return await self._search_hybrid_sources(
                        query, conversation_context, language, start_time
                    )

            # JSON Search prioritaire
            if use_json_search and self.json_system:
                json_results = await self.json_system.search_enhanced(
                    query=query,
                    genetic_line=genetic_line_filter,
                    performance_metrics=performance_context.get("metrics") if performance_context else None
                )
                
                if json_results and len(json_results) >= 3:
                    self.optimization_stats["json_searches"] += 1
                    return await self._generate_response_from_json_results(
                        query, json_results, language, conversation_context, start_time
                    )

            # CORRECTION CRITIQUE: Appel avec start_time
            logger.info("📚 Utilisation Weaviate (fallback)")
            return await self._generate_response_core_weaviate_only(
                query, None, conversation_context, language, start_time, tenant_id
            )

        except Exception as e:
            logger.error(f"Erreur génération réponse core: {e}")
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e), "processing_time": time.time() - start_time}
            )

    async def _generate_response_core_weaviate_only(
        self,
        query: str,
        intent_result,
        conversation_context: List[Dict],
        language: str,
        start_time: float,  # CORRECTION CRITIQUE: Paramètre obligatoire ajouté
        tenant_id: str,
    ) -> RAGResult:
        """Méthode Weaviate - CORRIGÉE avec start_time"""
        
        if not self.weaviate_core:
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": "Weaviate Core non disponible"}
            )

        self.optimization_stats["weaviate_searches"] += 1
        
        # Déléguer à Weaviate Core
        return await self.weaviate_core.generate_response(
            query, intent_result, conversation_context, language, start_time, tenant_id
        )

    async def _search_hybrid_sources(
        self, query: str, conversation_context: List[Dict], language: str, start_time: float
    ) -> RAGResult:
        """Recherche hybride PostgreSQL + Weaviate"""
        try:
            # Recherche parallèle
            tasks = []
            
            if self.postgresql_system:
                tasks.append(self.postgresql_system.search_metrics(query, None))
                
            if self.weaviate_core:
                tasks.append(self.weaviate_core.generate_response(
                    query, None, conversation_context, language, start_time, "default"
                ))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Fusion des résultats
            return self._merge_hybrid_results(results, query, start_time)

        except Exception as e:
            logger.error(f"Erreur recherche hybride: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": str(e), "source_type": "hybrid"}
            )

    async def _generate_response_from_json_results(
        self,
        query: str,
        json_results: List[Dict[str, Any]], 
        language: str,
        conversation_context: List[Dict],
        start_time: float
    ) -> RAGResult:
        """Génère réponse depuis résultats JSON"""
        
        if not self.json_system:
            return RAGResult(source=RAGSource.INTERNAL_ERROR)
            
        return await self.json_system.generate_response_from_results(
            query, json_results, language, conversation_context, start_time
        )

    def _merge_hybrid_results(self, results: List, query: str, start_time: float) -> RAGResult:
        """Fusionne les résultats hybrides"""
        
        valid_results = [r for r in results if isinstance(r, RAGResult) and not isinstance(r, Exception)]
        
        if not valid_results:
            return RAGResult(
                source=RAGSource.NO_RESULTS,
                metadata={"source_type": "hybrid", "processing_time": time.time() - start_time}
            )

        # Prendre le meilleur résultat pour l'instant
        best_result = max(valid_results, key=lambda r: r.confidence)
        best_result.metadata["source_type"] = "hybrid"
        best_result.metadata["results_merged"] = len(valid_results)
        
        return best_result

    def get_status(self) -> Dict:
        """Status système complet"""
        return {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "approach": "enhanced_rag_v5.1_modular",
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
            }
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