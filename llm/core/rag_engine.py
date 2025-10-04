# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine Principal Refactorisé
Point d'entrée principal avec délégation vers modules spécialisés
VERSION 4.8.1 - INTÉGRATION HISTORIQUE CONVERSATIONNEL:
- ✅ NOUVEAU: Récupération automatique de l'historique via ConversationMemory
- ✅ Intégration de get_contextual_memory() avant routage
- ✅ Transmission de l'historique à tous les handlers
- ✅ Support natif de NEEDS_CLARIFICATION via QueryRouter
- ✅ Génération automatique de réponse LLM après récupération documents
- ✅ Support des entités pré-extraites pour fusion conversationnelle
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

# NOUVEAUX IMPORTS - QueryRouter remplace plusieurs modules
from .query_router import QueryRouter
from .entity_extractor import EntityExtractor
from .query_enricher import ConversationalQueryEnricher  # ✅ NOUVEAU

# ✅ NOUVEAU: Import de ConversationMemory pour l'historique
try:
    from core.memory import ConversationMemory

    CONVERSATION_MEMORY_AVAILABLE = True
except ImportError as e:
    CONVERSATION_MEMORY_AVAILABLE = False
    ConversationMemory = None
    logging.warning(f"⚠️ ConversationMemory non disponible: {e}")

logger = logging.getLogger(__name__)

# Imports conditionnels des modules externes
POSTGRESQL_RETRIEVER_AVAILABLE = False
COMPARISON_HANDLER_AVAILABLE = False
WEAVIATE_CORE_AVAILABLE = False

PostgreSQLRetriever = None
ComparisonHandler = None
WeaviateCore = None

# Import séparé du Retriever
try:
    from .rag_postgresql_retriever import PostgreSQLRetriever

    POSTGRESQL_RETRIEVER_AVAILABLE = True
    logger.info("✅ PostgreSQL Retriever importé")
except ImportError as e:
    logger.warning(f"⚠️ PostgreSQL Retriever non disponible: {e}")

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

    VERSION 4.8.1 - INTÉGRATION HISTORIQUE CONVERSATIONNEL:
    - QueryRouter unifie classification, validation et routage
    - Support natif de NEEDS_CLARIFICATION
    - Configuration PostgreSQL chargée automatiquement depuis rag_postgresql_config.py
    - Instanciation PostgreSQLRetriever avec config centralisée
    - Transmission correcte du paramètre language à tous les handlers
    - ✅ CORRECTION CRITIQUE: Génération LLM automatique après récupération documents
    - ✅ NOUVEAU: Méthode generate_response_with_entities() pour fusion conversationnelle
    - ✅ Support du paramètre conversation_context dans generate_response()
    - ✅ NOUVEAU: Intégration ConversationMemory pour historique contextuel
    """

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialisation avec QueryRouter centralisé et ConversationMemory"""
        # Core engine
        self.core = RAGEngineCore(openai_client)

        # NOUVEAU MODULE CENTRALISÉ - QueryRouter
        self.query_router = QueryRouter(config_dir="/app/config")
        self.entity_extractor = EntityExtractor()

        # ✅ NOUVEAU: ConversationMemory pour historique
        # DEBUG CRITIQUE - INITIALISATION
        logger.info(f"🔍 INIT - openai_client type: {type(openai_client)}")
        logger.info(f"🔍 INIT - openai_client is None: {openai_client is None}")
        logger.info(
            f"🔍 INIT - CONVERSATION_MEMORY_AVAILABLE: {CONVERSATION_MEMORY_AVAILABLE}"
        )

        self.conversation_memory = None
        if CONVERSATION_MEMORY_AVAILABLE and ConversationMemory:
            logger.info("🔍 INIT - Tentative d'initialisation ConversationMemory...")
            try:
                self.conversation_memory = ConversationMemory(client=openai_client)
                logger.info(
                    f"✅ ConversationMemory initialisée - Type: {type(self.conversation_memory)}"
                )
            except Exception as e:
                logger.error(
                    f"❌ INIT - Échec initialisation ConversationMemory: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"⚠️ INIT - ConversationMemory NON disponible (AVAILABLE={CONVERSATION_MEMORY_AVAILABLE})"
            )

        # Handlers spécialisés
        self.temporal_handler = TemporalQueryHandler()
        self.comparative_handler = ComparativeQueryHandler()
        self.standard_handler = StandardQueryHandler()

        # Modules externes (Retriever uniquement, plus de Validator)
        self.postgresql_retriever = None
        self.comparison_handler = None
        self.weaviate_core = None

        # État
        self.is_initialized = False
        self.degraded_mode = False
        self.initialization_errors = []

        # Stats
        self.optimization_stats = {
            "requests_total": 0,
            "routing_success": 0,
            "routing_failures": 0,
            "clarification_needed": 0,
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
            "llm_generations": 0,
            "errors_count": 0,
            "preextracted_entities_queries": 0,
            "contextual_memory_queries": 0,
            "queries_enriched": 0,  # ✅ NOUVEAU
        }

    async def initialize(self):
        """Initialisation modulaire avec QueryRouter"""
        if self.is_initialized:
            return

        logger.info(
            "🚀 Initialisation RAG Engine v4.8.1 (QueryRouter + ConversationMemory)"
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
                    ("QueryRouter", self.query_router),
                    ("PostgreSQLRetriever", self.postgresql_retriever),
                    ("WeaviateCore", self.weaviate_core),
                    ("ComparisonHandler", self.comparison_handler),
                    ("EntityExtractor", self.entity_extractor),
                    ("LLMGenerator", self.core.generator),
                    ("ConversationMemory", self.conversation_memory),
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
        """Initialise Retriever avec config centralisée"""

        # PostgreSQL Retriever (pour search_metrics)
        if POSTGRESQL_RETRIEVER_AVAILABLE and PostgreSQLRetriever:
            try:
                # Import de la configuration centralisée
                from .rag_postgresql_config import POSTGRESQL_CONFIG

                # Validation de la config
                if not POSTGRESQL_CONFIG.get("password"):
                    logger.warning(
                        "⚠️ PostgreSQL config incomplète - variables d'environnement manquantes"
                    )
                    raise ValueError(
                        "PostgreSQL password manquant dans la configuration"
                    )

                # Instanciation avec config centralisée
                self.postgresql_retriever = PostgreSQLRetriever(
                    config=POSTGRESQL_CONFIG,
                    intents_file_path="/app/config/intents.json",
                )
                await self.postgresql_retriever.initialize()
                logger.info(
                    "✅ PostgreSQL Retriever initialisé avec config centralisée"
                )
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL Retriever échoué: {e}")
                self.initialization_errors.append(f"PostgreSQLRetriever: {e}")

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
        """Configure handlers avec Retriever"""

        # Configuration temporal handler (utilise le Retriever)
        self.temporal_handler.configure(postgresql_system=self.postgresql_retriever)

        # Configuration comparative handler (utilise le Retriever)
        self.comparative_handler.configure(
            comparison_handler=self.comparison_handler,
            weaviate_core=self.weaviate_core,
            postgresql_system=self.postgresql_retriever,
        )

        # Configuration standard handler (utilise RETRIEVER, plus de VALIDATOR)
        self.standard_handler.configure(
            postgresql_system=self.postgresql_retriever,
            weaviate_core=self.weaviate_core,
            postgresql_validator=None,  # Plus de validator séparé
            response_generator=self.core.generator,  # ✅ AJOUTER LE GÉNÉRATEUR
        )

        logger.debug(
            f"🔍 HANDLER CONFIGURED - postgresql_system type: {type(self.standard_handler.postgresql_system)}"
        )
        logger.debug(
            f"🔍 HANDLER CONFIGURED - postgresql_system is None: {self.standard_handler.postgresql_system is None}"
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
        """Point d'entrée principal avec routage intelligent via QueryRouter

        Args:
            query: Requête utilisateur
            tenant_id: Identifiant du tenant
            conversation_context: Historique de conversation (format liste)
            language: Langue de la requête
            enable_preprocessing: Activer le preprocessing (ignoré, toujours via QueryRouter)
            **kwargs: Paramètres additionnels (peut contenir conversation_context au format dict)
        """

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
        logger.info(f"🌐 generate_response reçoit langue: {effective_language}")

        # Fallback si système indisponible
        if self.degraded_mode and not self.postgresql_retriever:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                answer="Le système RAG n'est pas disponible.",
                metadata={"reason": "système_indisponible"},
            )

        # ✅ Extraire conversation_context au format dict depuis kwargs si présent
        context_dict = kwargs.get("conversation_context")

        # ✅ NOUVEAU: Récupérer l'historique conversationnel contextuel
        # DEBUG CRITIQUE - AVANT RÉCUPÉRATION
        logger.info(
            f"🔍 GENERATE - self.conversation_memory: {self.conversation_memory}"
        )
        logger.info(
            f"🔍 GENERATE - conversation_memory is None: {self.conversation_memory is None}"
        )
        logger.info(f"🔍 GENERATE - tenant_id: {tenant_id}")
        logger.info(f"🔍 GENERATE - query: {query[:50]}...")

        contextual_history = None
        if self.conversation_memory:
            logger.info("🔍 GENERATE - TENTATIVE de récupération historique...")
            try:
                contextual_history = (
                    await self.conversation_memory.get_contextual_memory(
                        tenant_id, query
                    )
                )
                logger.info(
                    f"🔍 GENERATE - RÉSULTAT brut: type={type(contextual_history)}, value={contextual_history}"
                )

                if contextual_history:
                    self.optimization_stats["contextual_memory_queries"] += 1
                    logger.info(
                        f"📚 Historique contextuel récupéré: {len(contextual_history)} éléments"
                    )
                else:
                    logger.warning(
                        f"⚠️ GENERATE - Historique VIDE retourné (contextual_history={contextual_history})"
                    )
            except Exception as e:
                logger.error(
                    f"❌ GENERATE - Exception récupération historique: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                "⚠️ GENERATE - conversation_memory est None, impossible de récupérer l'historique"
            )

        # ✅ NOUVEAU : Enrichissement conversationnel
        original_query = query
        if contextual_history:
            try:
                enricher = ConversationalQueryEnricher()
                query = enricher.enrich(query, contextual_history, effective_language)

                if query != original_query:
                    logger.info(f"🔄 Query enrichie: '{original_query}' → '{query}'")
                    self.optimization_stats["queries_enriched"] = (
                        self.optimization_stats.get("queries_enriched", 0) + 1
                    )
            except Exception as e:
                logger.warning(f"⚠️ Échec enrichissement query: {e}")
                # En cas d'erreur, on garde la query originale
                query = original_query

        try:
            return await self._process_query(
                query,  # ← Query possiblement enrichie
                effective_language,
                tenant_id,
                start_time,
                conversation_context=context_dict,
                contextual_history=contextual_history,
            )
        except Exception as e:
            logger.error(f"❌ Erreur generate_response: {e}")
            self.optimization_stats["errors_count"] += 1
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e)},
            )

    async def generate_response_with_entities(
        self,
        query: str,
        entities: Dict[str, Any],
        tenant_id: str = "default",
        language: Optional[str] = None,
        **kwargs,
    ) -> RAGResult:
        """
        Point d'entrée spécial pour requêtes avec entités pré-extraites

        UTILISÉ POUR LA MÉMOIRE CONVERSATIONNELLE:
        - Permet de passer directement les entités fusionnées depuis la session
        - Bypass l'extraction normale du QueryRouter
        - Garantit que les entités accumulées sont utilisées

        Args:
            query: Requête utilisateur (peut être accumulée)
            entities: Entités pré-extraites et fusionnées
            tenant_id: Identifiant du tenant
            language: Langue de la requête

        Returns:
            RAGResult avec réponse générée
        """

        if not self.is_initialized:
            logger.warning("⚠️ RAG Engine non initialisé, tentative d'initialisation")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"❌ Échec initialisation: {e}")

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1
        self.optimization_stats["preextracted_entities_queries"] += 1

        # Validation
        if not query or not query.strip():
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": "Query vide"},
            )

        effective_language = language or "fr"
        logger.info(
            f"🌐 generate_response_with_entities reçoit langue: {effective_language}"
        )
        logger.info(f"📋 Entités pré-extraites fournies: {entities}")

        # Fallback si système indisponible
        if self.degraded_mode and not self.postgresql_retriever:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                answer="Le système RAG n'est pas disponible.",
                metadata={"reason": "système_indisponible"},
            )

        # ✅ Extraire conversation_context depuis kwargs si présent
        context_dict = kwargs.get("conversation_context")

        # ✅ NOUVEAU: Récupérer l'historique conversationnel contextuel
        contextual_history = None
        if self.conversation_memory:
            try:
                contextual_history = (
                    await self.conversation_memory.get_contextual_memory(
                        tenant_id, query
                    )
                )
                if contextual_history:
                    self.optimization_stats["contextual_memory_queries"] += 1
                    logger.info(
                        f"📚 Historique contextuel récupéré: {len(contextual_history)} éléments"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Échec récupération historique: {e}")

        # ✅ NOUVEAU : Enrichissement conversationnel
        original_query = query
        if contextual_history:
            try:
                enricher = ConversationalQueryEnricher()
                query = enricher.enrich(query, contextual_history, effective_language)

                if query != original_query:
                    logger.info(f"🔄 Query enrichie: '{original_query}' → '{query}'")
                    self.optimization_stats["queries_enriched"] = (
                        self.optimization_stats.get("queries_enriched", 0) + 1
                    )
            except Exception as e:
                logger.warning(f"⚠️ Échec enrichissement query: {e}")
                # En cas d'erreur, on garde la query originale
                query = original_query

        try:
            return await self._process_query_with_entities(
                query,  # ← Query possiblement enrichie
                entities,
                effective_language,
                tenant_id,
                start_time,
                conversation_context=context_dict,
                contextual_history=contextual_history,
            )
        except Exception as e:
            logger.error(f"❌ Erreur generate_response_with_entities: {e}")
            self.optimization_stats["errors_count"] += 1
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e)},
            )

    async def _process_query(
        self,
        query: str,
        language: str,
        tenant_id: str,
        start_time: float,
        conversation_context: Dict = None,
        contextual_history: List[Dict] = None,
    ) -> RAGResult:
        """Pipeline de traitement avec QueryRouter

        Args:
            query: Requête utilisateur
            language: Langue de la requête
            tenant_id: Identifiant du tenant
            start_time: Timestamp de début
            conversation_context: Contexte conversationnel (format dict)
            contextual_history: Historique contextuel récupéré par ConversationMemory
        """

        logger.info(f"🌐 _process_query traite avec langue: {language}")

        # 1. ROUTAGE VIA QUERY ROUTER
        route = self.query_router.route(
            query=query, user_id=tenant_id, language=language
        )

        logger.info(
            f"🎯 QueryRouter → destination: {route.destination}, confiance: {route.confidence:.2%}"
        )

        # 2. VÉRIFIER CLARIFICATION NÉCESSAIRE
        if route.destination == "needs_clarification":
            self.optimization_stats["clarification_needed"] += 1
            logger.info(
                f"⚠️ Clarification nécessaire - champs manquants: {route.missing_fields}"
            )

            return RAGResult(
                source=RAGSource.NEEDS_CLARIFICATION,
                answer=self._build_clarification_message(
                    route.missing_fields, language
                ),
                metadata={
                    "needs_clarification": True,
                    "missing_fields": route.missing_fields,
                    "entities": route.entities,
                    "validation_details": route.validation_details,
                    "language": language,
                },
            )

        # 3. DÉTERMINER QUERY_TYPE DEPUIS DESTINATION
        if route.destination == "postgresql":
            query_type = "standard"
        elif route.destination == "weaviate":
            query_type = "diagnostic"
        else:  # hybrid
            query_type = "standard"

        # 4. CRÉER PREPROCESSED_DATA DEPUIS ROUTE
        preprocessed_data = {
            "normalized_query": query,
            "original_query": query,
            "entities": route.entities,
            "language": language,
            "routing_hint": route.destination,
            "is_comparative": False,
            "comparison_entities": [],
            "query_type": query_type,
            "metadata": {
                "original_query": query,
                "normalized_query": query,
                "routing_hint": route.destination,
                "is_comparative": False,
                "routing_applied": True,
                "confidence": route.confidence,
                "language_detected": language,
                "validation_details": route.validation_details,
            },
        }

        # ✅ AJOUTER le contexte conversationnel
        if conversation_context:
            preprocessed_data["conversation_context"] = conversation_context
            logger.info(
                f"📝 Contexte conversationnel ajouté: {list(conversation_context.keys())}"
            )

        # ✅ NOUVEAU: AJOUTER l'historique contextuel
        if contextual_history:
            preprocessed_data["contextual_history"] = contextual_history
            preprocessed_data["metadata"]["contextual_history_count"] = len(
                contextual_history
            )
            logger.info(
                f"📚 Historique contextuel ajouté: {len(contextual_history)} éléments"
            )

        # 5. MISE À JOUR DES STATS (basé sur query_type déterminé)
        if query_type == "comparative":
            self.optimization_stats["comparative_queries"] += 1
        elif query_type == "temporal_range":
            self.optimization_stats["temporal_queries"] += 1
        elif query_type == "optimization":
            self.optimization_stats["optimization_queries"] += 1
        elif query_type == "calculation":
            self.optimization_stats["calculation_queries"] += 1
        elif query_type == "economic":
            self.optimization_stats["economic_queries"] += 1
        elif query_type == "diagnostic":
            self.optimization_stats["diagnostic_queries"] += 1

        # 6. ROUTAGE VERS HANDLER
        result = await self._route_to_handler(
            query_type, preprocessed_data, start_time, language
        )

        # ✅ CORRECTION CRITIQUE: Générer réponse LLM si nécessaire
        result = await self._ensure_answer_generated(
            result, preprocessed_data, query, language
        )

        # 7. ENRICHIR MÉTADONNÉES
        result.metadata.update(preprocessed_data["metadata"])
        result.metadata["route_confidence"] = route.confidence
        result.metadata["route_destination"] = route.destination

        self.optimization_stats["routing_success"] += 1

        return result

    async def _process_query_with_entities(
        self,
        query: str,
        entities: Dict[str, Any],
        language: str,
        tenant_id: str,
        start_time: float,
        conversation_context: Dict = None,
        contextual_history: List[Dict] = None,
    ) -> RAGResult:
        """
        Pipeline de traitement avec entités pré-extraites

        Similaire à _process_query mais utilise les entités fournies
        au lieu de les extraire via le QueryRouter

        Args:
            query: Requête utilisateur
            entities: Entités pré-extraites
            language: Langue de la requête
            tenant_id: Identifiant du tenant
            start_time: Timestamp de début
            conversation_context: Contexte conversationnel (format dict)
            contextual_history: Historique contextuel récupéré par ConversationMemory
        """

        logger.info(f"🌐 _process_query_with_entities traite avec langue: {language}")
        logger.info(f"📋 Utilisation des entités pré-extraites: {entities}")

        # 1. ROUTAGE VIA QUERY ROUTER (qui utilisera les entités si fournies)
        route = self.query_router.route(
            query=query,
            user_id=tenant_id,
            language=language,
            preextracted_entities=entities,  # Passer les entités pré-extraites
        )

        logger.info(
            f"🎯 QueryRouter → destination: {route.destination}, confiance: {route.confidence:.2%}"
        )

        # 2. VÉRIFIER CLARIFICATION (même avec entités pré-extraites)
        if route.destination == "needs_clarification":
            self.optimization_stats["clarification_needed"] += 1
            logger.info(
                f"⚠️ Clarification nécessaire malgré entités - champs: {route.missing_fields}"
            )

            return RAGResult(
                source=RAGSource.NEEDS_CLARIFICATION,
                answer=self._build_clarification_message(
                    route.missing_fields, language
                ),
                metadata={
                    "needs_clarification": True,
                    "missing_fields": route.missing_fields,
                    "entities": route.entities,
                    "validation_details": route.validation_details,
                    "language": language,
                    "entities_preextracted": True,
                },
            )

        # 3. DÉTERMINER QUERY_TYPE DEPUIS DESTINATION
        if route.destination == "postgresql":
            query_type = "standard"
        elif route.destination == "weaviate":
            query_type = "diagnostic"
        else:  # hybrid
            query_type = "standard"

        # 4. CRÉER PREPROCESSED_DATA
        preprocessed_data = {
            "normalized_query": query,
            "original_query": query,
            "entities": route.entities,  # Utiliser les entités validées par le router
            "language": language,
            "routing_hint": route.destination,
            "is_comparative": False,
            "comparison_entities": [],
            "query_type": query_type,
            "metadata": {
                "original_query": query,
                "normalized_query": query,
                "routing_hint": route.destination,
                "is_comparative": False,
                "routing_applied": True,
                "entities_preextracted": True,
                "confidence": route.confidence,
                "language_detected": language,
                "validation_details": route.validation_details,
            },
        }

        # ✅ AJOUTER le contexte conversationnel
        if conversation_context:
            preprocessed_data["conversation_context"] = conversation_context
            logger.info(
                f"📝 Contexte conversationnel ajouté: {list(conversation_context.keys())}"
            )

        # ✅ NOUVEAU: AJOUTER l'historique contextuel
        if contextual_history:
            preprocessed_data["contextual_history"] = contextual_history
            preprocessed_data["metadata"]["contextual_history_count"] = len(
                contextual_history
            )
            logger.info(
                f"📚 Historique contextuel ajouté: {len(contextual_history)} éléments"
            )

        # 5. MISE À JOUR DES STATS
        if query_type == "comparative":
            self.optimization_stats["comparative_queries"] += 1
        elif query_type == "temporal_range":
            self.optimization_stats["temporal_queries"] += 1
        elif query_type == "optimization":
            self.optimization_stats["optimization_queries"] += 1
        elif query_type == "calculation":
            self.optimization_stats["calculation_queries"] += 1
        elif query_type == "economic":
            self.optimization_stats["economic_queries"] += 1
        elif query_type == "diagnostic":
            self.optimization_stats["diagnostic_queries"] += 1

        # 6. ROUTAGE VERS HANDLER (force standard pour PostgreSQL)
        result = await self.standard_handler.handle(
            preprocessed_data, start_time, language=language
        )

        # ✅ CORRECTION CRITIQUE: Générer réponse LLM si nécessaire
        result = await self._ensure_answer_generated(
            result, preprocessed_data, query, language
        )

        # 7. ENRICHIR MÉTADONNÉES
        result.metadata.update(preprocessed_data["metadata"])
        result.metadata["route_confidence"] = route.confidence
        result.metadata["route_destination"] = route.destination
        result.metadata["entities_source"] = "preextracted_from_session"

        self.optimization_stats["routing_success"] += 1

        return result

    async def _ensure_answer_generated(
        self,
        result: RAGResult,
        preprocessed_data: Dict[str, Any],
        original_query: str,
        language: str,
    ) -> RAGResult:
        """
        ✅ NOUVELLE MÉTHODE CRITIQUE: Génère la réponse LLM avec contexte conversationnel

        Vérifie si le RAGResult contient des documents mais pas de réponse,
        et dans ce cas appelle le générateur LLM pour créer la réponse.

        Args:
            result: RAGResult du handler
            preprocessed_data: Données preprocessées (contient contextual_history)
            original_query: Requête originale
            language: Langue de la requête

        Returns:
            RAGResult avec answer généré
        """
        # Si on a déjà une réponse, on ne fait rien
        if result.answer and result.answer.strip():
            logger.debug("✅ Réponse déjà présente, génération LLM non nécessaire")
            return result

        # Si on a des documents mais pas de réponse, générer via LLM
        if result.context_docs and len(result.context_docs) > 0:
            if not self.core.generator:
                logger.warning(
                    "⚠️ Générateur LLM non disponible, impossible de générer réponse"
                )
                result.answer = "Data retrieved but response generation unavailable."
                return result

            logger.info(
                f"🔧 Génération réponse LLM pour {len(result.context_docs)} documents PostgreSQL"
            )

            # ✅ CORRECTION : Récupérer le contexte conversationnel
            contextual_history = preprocessed_data.get("contextual_history", "")

            # DEBUG CRITIQUE - AJOUTER CES LOGS
            logger.info(
                f"🔍 ENSURE - contextual_history type: {type(contextual_history)}"
            )
            logger.info(
                f"🔍 ENSURE - contextual_history length: {len(contextual_history) if contextual_history else 0}"
            )
            logger.info(
                f"🔍 ENSURE - contextual_history preview: {contextual_history[:200] if contextual_history else 'VIDE'}"
            )

            # Formater l'historique pour le générateur
            conversation_context = ""
            if contextual_history:
                # Le contexte est déjà formaté en string
                conversation_context = str(contextual_history)
                logger.info(
                    f"📚 Contexte conversationnel transmis au générateur: {len(conversation_context)} chars"
                )
                logger.info(f"📚 Preview contexte: {conversation_context[:200]}")
            else:
                logger.warning("⚠️ ENSURE - Pas d'historique dans preprocessed_data!")

            try:
                # DEBUG : Vérifier ce qu'on envoie au générateur
                logger.info(
                    f"🔧 ENSURE - Appel generate_response avec conversation_context length: {len(conversation_context)}"
                )

                # Appel du générateur avec les documents récupérés ET le contexte conversationnel
                generated_answer = await self.core.generator.generate_response(
                    query=preprocessed_data.get("original_query", original_query),
                    context_docs=result.context_docs,
                    conversation_context=conversation_context,  # ✅ CORRECTION - DOIT CONTENIR LE CONTEXTE
                    language=language,
                    intent_result=None,
                )

                result.answer = generated_answer
                result.metadata["llm_generation_applied"] = True
                result.metadata["llm_input_docs_count"] = len(result.context_docs)
                result.metadata["conversation_context_used"] = bool(
                    conversation_context
                )
                result.metadata["conversation_context_length"] = len(
                    conversation_context
                )
                self.optimization_stats["llm_generations"] += 1

                logger.info(
                    f"✅ Réponse LLM générée ({len(generated_answer)} caractères)"
                )

            except Exception as e:
                logger.error(f"❌ Erreur génération LLM: {e}", exc_info=True)
                result.answer = "Unable to generate response from the retrieved data."
                result.metadata["llm_generation_error"] = str(e)

        return result

    def _build_clarification_message(
        self, missing_fields: List[str], language: str = "fr"
    ) -> str:
        """
        Construit un message de clarification en français ou anglais

        Args:
            missing_fields: Liste des champs manquants
            language: Langue du message ('fr' ou 'en')

        Returns:
            Message de clarification formaté
        """
        if language == "en":
            if len(missing_fields) == 1:
                return f"Please specify the {missing_fields[0]} to continue."
            else:
                fields = ", ".join(missing_fields[:-1]) + f" and {missing_fields[-1]}"
                return f"Please specify the following information: {fields}."
        else:  # français par défaut
            if len(missing_fields) == 1:
                field_fr = self._translate_field_name(missing_fields[0])
                return f"Veuillez préciser {field_fr} pour continuer."
            else:
                fields_fr = [self._translate_field_name(f) for f in missing_fields]
                fields_str = ", ".join(fields_fr[:-1]) + f" et {fields_fr[-1]}"
                return f"Veuillez préciser les informations suivantes : {fields_str}."

    def _translate_field_name(self, field: str) -> str:
        """Traduit un nom de champ en français"""
        translations = {
            "breed": "la race",
            "age": "l'âge",
            "gender": "le sexe",
            "weight": "le poids",
            "metric": "la métrique",
            "period": "la période",
            "date": "la date",
            "location": "le lieu",
            "building": "le bâtiment",
            "batch": "le lot",
        }
        return translations.get(field, field)

    async def _route_to_handler(
        self,
        query_type: str,
        preprocessed_data: Dict[str, Any],
        start_time: float,
        language: str,
    ) -> RAGResult:
        """Route vers le handler approprié"""

        logger.info(f"🌐 _route_to_handler avec langue: {language}")

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
            "version": "v4.8.2_query_enrichment",
            "architecture": "modular_query_router_with_memory_and_enrichment",
            "modules": {
                "core": True,
                "rag_engine": True,
                "query_router": bool(self.query_router),
                "entity_extractor": bool(self.entity_extractor),
                "temporal_handler": True,
                "comparative_handler": True,
                "standard_handler": True,
                "postgresql_retriever": bool(self.postgresql_retriever),
                "weaviate_core": bool(self.weaviate_core),
                "comparison_handler": bool(self.comparison_handler),
                "llm_generator": bool(self.core.generator),
                "conversation_memory": bool(self.conversation_memory),
            },
            "optimization_stats": self.optimization_stats.copy(),
            "initialization_errors": self.initialization_errors,
        }

    async def close(self):
        """Fermeture propre de tous les modules"""
        logger.info("🔒 Fermeture RAG Engine...")

        try:
            if self.postgresql_retriever:
                await self.postgresql_retriever.close()
        except Exception as e:
            logger.error(f"❌ Erreur fermeture PostgreSQL Retriever: {e}")

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
