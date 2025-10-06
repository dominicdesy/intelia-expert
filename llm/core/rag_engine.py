# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine with modular architecture
VERSION 5.0 - REFACTORED FOR MAINTAINABILITY:
- Extracted query processing to RAGQueryProcessor
- Extracted response generation to RAGResponseGenerator
- Simplified main engine class to orchestration only
- Removed code duplication between generate_response methods
"""

import logging
import time
from utils.types import Dict, List, Optional, Any

from config.config import RAG_ENABLED

try:
    from .data_models import RAGResult, RAGSource
except ImportError as e:
    logging.error(f"Error importing data_models: {e}")
    raise

try:
    from utils.imports_and_dependencies import OPENAI_AVAILABLE, AsyncOpenAI
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

# Import modular components
from .rag_engine_core import RAGEngineCore
from .handlers import (
    TemporalQueryHandler,
    ComparativeQueryHandler,
    StandardQueryHandler,
)
from .query_router import QueryRouter
from .entity_extractor import EntityExtractor
from .query_processor import RAGQueryProcessor
from .response_generator import RAGResponseGenerator
from .base import InitializableMixin

# Conversation memory (optional)
try:
    from core.memory import ConversationMemory

    CONVERSATION_MEMORY_AVAILABLE = True
except ImportError as e:
    CONVERSATION_MEMORY_AVAILABLE = False
    ConversationMemory = None
    logging.warning(f"ConversationMemory not available: {e}")

logger = logging.getLogger(__name__)

# External module availability flags
POSTGRESQL_RETRIEVER_AVAILABLE = False
COMPARISON_HANDLER_AVAILABLE = False
WEAVIATE_CORE_AVAILABLE = False

PostgreSQLRetriever = None
ComparisonHandler = None
WeaviateCore = None

# Import PostgreSQL Retriever
try:
    from retrieval.postgresql.retriever import PostgreSQLRetriever

    POSTGRESQL_RETRIEVER_AVAILABLE = True
    logger.info("PostgreSQL Retriever imported")
except ImportError as e:
    logger.warning(f"PostgreSQL Retriever not available: {e}")

# Import Comparison Handler
try:
    from .handlers.comparison_handler import ComparisonHandler

    COMPARISON_HANDLER_AVAILABLE = True
    logger.info("Comparison Handler imported")
except ImportError as e:
    logger.warning(f"Comparison Handler not available: {e}")

# Import Weaviate Core
try:
    from retrieval.weaviate.core import WeaviateCore

    WEAVIATE_CORE_AVAILABLE = True
    logger.info("Weaviate Core imported")
except ImportError as e:
    logger.warning(f"Weaviate Core not available: {e}")


class InteliaRAGEngine(InitializableMixin):
    """
    RAG Engine with modular architecture

    Responsibilities:
    - Initialize and manage all RAG components
    - Provide public API for query processing
    - Track statistics and status
    - Delegate to specialized processors for actual work
    """

    def __init__(self, openai_client: AsyncOpenAI = None):
        """Initialize RAG engine with modular components"""
        super().__init__()

        # Core components
        self.core = RAGEngineCore(openai_client)
        self.query_router = QueryRouter(config_dir="/app/config")
        self.entity_extractor = EntityExtractor()

        # Conversation memory (optional)
        self.conversation_memory = None
        if CONVERSATION_MEMORY_AVAILABLE and ConversationMemory:
            try:
                self.conversation_memory = ConversationMemory(client=openai_client)
                logger.info("ConversationMemory initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ConversationMemory: {e}")

        # Query handlers
        self.temporal_handler = TemporalQueryHandler()
        self.comparative_handler = ComparativeQueryHandler()
        self.standard_handler = StandardQueryHandler()

        # External modules
        self.postgresql_retriever = None
        self.comparison_handler = None
        self.weaviate_core = None

        # Processors (initialized after configure_handlers)
        self.query_processor = None
        self.response_generator = None

        # State
        self.degraded_mode = False

        # Statistics
        self.optimization_stats = {
            "requests_total": 0,
            "routing_success": 0,
            "routing_failures": 0,
            "clarification_needed": 0,
            "comparative_queries": 0,
            "temporal_queries": 0,
            "optimization_queries": 0,
            "calculation_queries": 0,
            "diagnostic_queries": 0,
            "postgresql_queries": 0,
            "llm_generations": 0,
            "errors_count": 0,
            "preextracted_entities_queries": 0,
            "contextual_memory_queries": 0,
            "queries_enriched": 0,
        }

    async def initialize(self):
        """Initialize all modules"""
        if self.is_initialized:
            return

        logger.info("Initializing RAG Engine v5.0 (Refactored)")

        try:
            await self.core.initialize()
            await self._initialize_external_modules()
            await self._configure_handlers()

            # Initialize processors after handlers are configured
            self.query_processor = RAGQueryProcessor(
                query_router=self.query_router,
                handlers={
                    "temporal": self.temporal_handler,
                    "comparative": self.comparative_handler,
                    "standard": self.standard_handler,
                },
                conversation_memory=self.conversation_memory,
            )

            self.response_generator = RAGResponseGenerator(
                llm_generator=self.core.generator
            )

            await super().initialize()

            active_modules = [
                name
                for name, module in [
                    ("QueryRouter", self.query_router),
                    ("PostgreSQLRetriever", self.postgresql_retriever),
                    ("WeaviateCore", self.weaviate_core),
                    ("ComparisonHandler", self.comparison_handler),
                    ("LLMGenerator", self.core.generator),
                    ("ConversationMemory", self.conversation_memory),
                ]
                if module is not None
            ]

            logger.info(
                f"RAG Engine initialized - Modules: {', '.join(active_modules)}"
            )

            if self.initialization_errors:
                logger.warning(f"Initialization warnings: {self.initialization_errors}")

        except Exception as e:
            logger.error(f"Critical initialization error: {e}")
            self.degraded_mode = True
            self.add_initialization_error(str(e))
            await super().initialize()  # Mark as initialized even in degraded mode

    async def _initialize_external_modules(self):
        """Initialize external modules (PostgreSQL, Weaviate, etc.)"""

        # PostgreSQL Retriever
        if POSTGRESQL_RETRIEVER_AVAILABLE and PostgreSQLRetriever:
            try:
                from retrieval.postgresql.config import POSTGRESQL_CONFIG

                if not POSTGRESQL_CONFIG.get("password"):
                    raise ValueError("PostgreSQL password missing in configuration")

                self.postgresql_retriever = PostgreSQLRetriever(
                    config=POSTGRESQL_CONFIG,
                    intents_file_path="/app/config/intents.json",
                )
                await self.postgresql_retriever.initialize()
                logger.info("PostgreSQL Retriever initialized")
            except Exception as e:
                logger.warning(f"PostgreSQL Retriever failed: {e}")
                self.add_initialization_error(f"PostgreSQLRetriever: {e}")

        # Weaviate Core
        if WEAVIATE_CORE_AVAILABLE and WeaviateCore and self.core.openai_client:
            try:
                self.weaviate_core = WeaviateCore(self.core.openai_client)
                await self.weaviate_core.initialize()
                logger.info("Weaviate Core initialized")
            except Exception as e:
                logger.warning(f"Weaviate Core failed: {e}")
                self.add_initialization_error(f"WeaviateCore: {e}")

        # Comparison Handler
        if COMPARISON_HANDLER_AVAILABLE and ComparisonHandler:
            try:
                self.comparison_handler = ComparisonHandler(self.postgresql_retriever)
                if not self.postgresql_retriever:
                    logger.warning(
                        "Comparison Handler in degraded mode (no PostgreSQL)"
                    )
                else:
                    logger.info("Comparison Handler initialized")
            except Exception as e:
                logger.warning(f"Comparison Handler failed: {e}")
                self.add_initialization_error(f"ComparisonHandler: {e}")

    async def _configure_handlers(self):
        """Configure handlers with retrieval systems"""
        self.temporal_handler.configure(postgresql_system=self.postgresql_retriever)

        self.comparative_handler.configure(
            comparison_handler=self.comparison_handler,
            weaviate_core=self.weaviate_core,
            postgresql_system=self.postgresql_retriever,
        )

        self.standard_handler.configure(
            postgresql_system=self.postgresql_retriever,
            weaviate_core=self.weaviate_core,
            postgresql_validator=None,
            response_generator=self.core.generator,
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
        """
        Main entry point for generating responses

        Args:
            query: User query
            tenant_id: Tenant identifier
            conversation_context: Conversation history (list format)
            language: Query language
            enable_preprocessing: Enable preprocessing (deprecated, always uses QueryRouter)
            **kwargs: Additional parameters (may contain conversation_context as dict)

        Returns:
            RAGResult with answer
        """
        if not self.is_initialized:
            logger.warning("RAG Engine not initialized, attempting initialization")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Initialization failed: {e}")

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1

        # Validation
        if not query or not query.strip():
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": "Empty query"},
            )

        effective_language = language or "fr"

        # Fallback if system unavailable
        if self.degraded_mode and not self.postgresql_retriever:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                answer="Le système RAG n'est pas disponible.",
                metadata={"reason": "système_indisponible"},
            )

        # Extract conversation_context from kwargs if present
        context_dict = kwargs.get("conversation_context")

        try:
            # Process query through processor
            result = await self.query_processor.process_query(
                query=query,
                language=effective_language,
                tenant_id=tenant_id,
                start_time=start_time,
                conversation_context=context_dict,
            )

            # Ensure answer is generated
            result = await self.response_generator.ensure_answer_generated(
                result=result,
                preprocessed_data=result.metadata,
                original_query=query,
                language=effective_language,
            )

            self.optimization_stats["routing_success"] += 1
            return result

        except Exception as e:
            logger.error(f"Error in generate_response: {e}")
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
        Entry point for queries with pre-extracted entities

        Used for conversational memory where entities are accumulated
        across multiple turns.

        Args:
            query: User query (may be accumulated)
            entities: Pre-extracted and merged entities
            tenant_id: Tenant identifier
            language: Query language

        Returns:
            RAGResult with answer
        """
        if not self.is_initialized:
            logger.warning("RAG Engine not initialized, attempting initialization")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Initialization failed: {e}")

        start_time = time.time()
        self.optimization_stats["requests_total"] += 1
        self.optimization_stats["preextracted_entities_queries"] += 1

        # Validation
        if not query or not query.strip():
            return RAGResult(
                source=RAGSource.ERROR,
                metadata={"error": "Empty query"},
            )

        effective_language = language or "fr"
        logger.info(f"generate_response_with_entities language: {effective_language}")
        logger.info(f"Pre-extracted entities provided: {entities}")

        # Fallback if system unavailable
        if self.degraded_mode and not self.postgresql_retriever:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                answer="Le système RAG n'est pas disponible.",
                metadata={"reason": "système_indisponible"},
            )

        # Extract conversation_context from kwargs if present
        context_dict = kwargs.get("conversation_context")

        try:
            # Process query with pre-extracted entities
            result = await self.query_processor.process_query(
                query=query,
                language=effective_language,
                tenant_id=tenant_id,
                start_time=start_time,
                conversation_context=context_dict,
                preextracted_entities=entities,
            )

            # Ensure answer is generated
            result = await self.response_generator.ensure_answer_generated(
                result=result,
                preprocessed_data=result.metadata,
                original_query=query,
                language=effective_language,
            )

            self.optimization_stats["routing_success"] += 1
            return result

        except Exception as e:
            logger.error(f"Error in generate_response_with_entities: {e}")
            self.optimization_stats["errors_count"] += 1
            return RAGResult(
                source=RAGSource.INTERNAL_ERROR,
                metadata={"error": str(e)},
            )

    def get_status(self) -> Dict:
        """Get system status"""
        return {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "degraded_mode": self.degraded_mode,
            "version": "v5.0_refactored_modular",
            "architecture": "modular_with_specialized_processors",
            "modules": {
                "core": True,
                "rag_engine": True,
                "query_router": bool(self.query_router),
                "query_processor": bool(self.query_processor),
                "response_generator": bool(self.response_generator),
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
        """Clean shutdown of all modules"""
        logger.info("Closing RAG Engine...")

        try:
            if self.postgresql_retriever:
                await self.postgresql_retriever.close()
        except Exception as e:
            logger.error(f"Error closing PostgreSQL Retriever: {e}")

        try:
            if self.weaviate_core:
                await self.weaviate_core.close()
        except Exception as e:
            logger.error(f"Error closing Weaviate Core: {e}")

        try:
            await self.core.close()
        except Exception as e:
            logger.error(f"Error closing Core: {e}")

        await super().close()
        logger.info("RAG Engine closed")


# Factory function
def create_rag_engine(openai_client=None) -> InteliaRAGEngine:
    """Factory to create RAG Engine instance"""
    return InteliaRAGEngine(openai_client)
