# -*- coding: utf-8 -*-
"""
Query processor - Handles query processing pipeline for RAG engine
"""

import logging
from utils.types import Dict, List, Any, Optional

from .data_models import RAGResult, RAGSource
from .query_enricher import ConversationalQueryEnricher
from utils.clarification_helper import get_clarification_helper

logger = logging.getLogger(__name__)


class RAGQueryProcessor:
    """Processes queries through the RAG pipeline"""

    def __init__(self, query_router, handlers, conversation_memory=None):
        """
        Initialize query processor

        Args:
            query_router: QueryRouter instance
            handlers: Dict of handler instances (temporal, comparative, standard)
            conversation_memory: Optional ConversationMemory instance
        """
        self.query_router = query_router
        self.temporal_handler = handlers.get("temporal")
        self.comparative_handler = handlers.get("comparative")
        self.standard_handler = handlers.get("standard")
        self.conversation_memory = conversation_memory
        self.enricher = ConversationalQueryEnricher()
        self.clarification_helper = get_clarification_helper()

    async def process_query(
        self,
        query: str,
        language: str,
        tenant_id: str,
        start_time: float,
        conversation_context: Dict = None,
        preextracted_entities: Dict[str, Any] = None,
    ) -> RAGResult:
        """
        Main query processing pipeline

        Args:
            query: User query
            language: Query language
            tenant_id: Tenant identifier
            start_time: Processing start timestamp
            conversation_context: Conversation context dict
            preextracted_entities: Pre-extracted entities (if any)

        Returns:
            RAGResult with response
        """
        logger.info(f"Processing query with language: {language}")

        # Step 1: Retrieve contextual history
        contextual_history = await self._get_contextual_history(tenant_id, query)

        # Step 2: Enrich query if history available
        enriched_query = self._enrich_query(query, contextual_history, language)

        # Step 3: Route query
        route = self.query_router.route(
            query=enriched_query,
            user_id=tenant_id,
            language=language,
            preextracted_entities=preextracted_entities,
        )

        logger.info(
            f"QueryRouter → destination: {route.destination}, confidence: {route.confidence:.2%}"
        )

        # Step 4: Check for clarification needs
        if route.destination == "needs_clarification":
            return self._build_clarification_result(route, language, query=query)

        # Step 5: Build preprocessed data
        preprocessed_data = self._build_preprocessed_data(
            enriched_query,
            query,
            route,
            language,
            conversation_context,
            contextual_history,
        )

        # Step 6: Route to appropriate handler
        return await self._route_to_handler(
            route, preprocessed_data, start_time, language
        )

    async def _get_contextual_history(
        self, tenant_id: str, query: str
    ) -> Optional[str]:
        """Retrieve contextual conversation history"""
        if not self.conversation_memory:
            logger.warning("ConversationMemory not available")
            return None

        try:
            contextual_history = await self.conversation_memory.get_contextual_memory(
                tenant_id, query
            )

            if contextual_history:
                logger.info(
                    f"Contextual history retrieved: {len(contextual_history)} elements"
                )
                return contextual_history
            else:
                logger.debug("No contextual history returned")
                return None

        except Exception as e:
            logger.error(f"Error retrieving contextual history: {e}", exc_info=True)
            return None

    def _enrich_query(
        self, query: str, contextual_history: Optional[str], language: str
    ) -> str:
        """Enrich query using conversation history"""
        if not contextual_history:
            return query

        try:
            enriched_query = self.enricher.enrich(query, contextual_history, language)

            if enriched_query != query:
                logger.info(f"Query enriched: '{query}' → '{enriched_query}'")

            return enriched_query

        except Exception as e:
            logger.warning(f"Query enrichment failed: {e}")
            return query

    def _build_clarification_result(self, route, language: str, query: str = "") -> RAGResult:
        """Build clarification result with intelligent contextual messages"""
        logger.info(f"Clarification needed - missing fields: {route.missing_fields}")

        # Utiliser le clarification helper pour message contextuel
        clarification_message = self.clarification_helper.build_clarification_message(
            missing_fields=route.missing_fields,
            language=language,
            query=query,
            entities=route.entities
        )

        return RAGResult(
            source=RAGSource.NEEDS_CLARIFICATION,
            answer=clarification_message,
            metadata={
                "needs_clarification": True,
                "missing_fields": route.missing_fields,
                "entities": route.entities,
                "validation_details": route.validation_details,
                "language": language,
            },
        )

    def _build_preprocessed_data(
        self,
        enriched_query: str,
        original_query: str,
        route,
        language: str,
        conversation_context: Dict,
        contextual_history: Optional[str],
    ) -> Dict[str, Any]:
        """Build preprocessed data structure"""
        # Determine query type from destination
        if route.destination == "postgresql":
            query_type = "standard"
        elif route.destination == "weaviate":
            query_type = "diagnostic"
        else:  # hybrid
            query_type = "standard"

        preprocessed_data = {
            "normalized_query": enriched_query,
            "original_query": original_query,
            "entities": route.entities,
            "language": language,
            "routing_hint": route.destination,
            "is_comparative": False,
            "comparison_entities": [],
            "query_type": query_type,
            "metadata": {
                "original_query": original_query,
                "normalized_query": enriched_query,
                "routing_hint": route.destination,
                "is_comparative": False,
                "routing_applied": True,
                "confidence": route.confidence,
                "language_detected": language,
                "validation_details": route.validation_details,
            },
        }

        # Add conversation context if available
        if conversation_context:
            preprocessed_data["conversation_context"] = conversation_context
            logger.info(
                f"Conversation context added: {list(conversation_context.keys())}"
            )

        # Add contextual history if available
        if contextual_history:
            preprocessed_data["contextual_history"] = contextual_history
            preprocessed_data["metadata"]["contextual_history_count"] = len(
                contextual_history
            )
            logger.info(f"Contextual history added: {len(contextual_history)} elements")

        return preprocessed_data

    async def _route_to_handler(
        self,
        route,
        preprocessed_data: Dict[str, Any],
        start_time: float,
        language: str,
    ) -> RAGResult:
        """Route to appropriate handler based on query type"""
        query_type = preprocessed_data["query_type"]

        if query_type == "temporal_range":
            logger.debug("→ Routing to TemporalQueryHandler")
            return await self.temporal_handler.handle(preprocessed_data, start_time)

        elif query_type == "comparative":
            logger.debug("→ Routing to ComparativeQueryHandler")
            return await self.comparative_handler.handle(preprocessed_data, start_time)

        elif query_type in ["optimization", "calculation"]:
            logger.debug(f"→ Routing to StandardHandler (type={query_type})")
            preprocessed_data["is_optimization"] = query_type == "optimization"
            preprocessed_data["is_calculation"] = query_type == "calculation"
            return await self.standard_handler.handle(
                preprocessed_data, start_time, language=language
            )

        elif query_type == "economic":
            logger.debug("→ Economic query detected")
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Les données économiques ne sont pas disponibles.",
                metadata={"query_type": "economic"},
            )

        elif query_type == "diagnostic":
            logger.debug("→ Routing to StandardHandler (diagnostic)")
            preprocessed_data["routing_hint"] = "weaviate"
            return await self.standard_handler.handle(
                preprocessed_data, start_time, language=language
            )

        else:  # standard
            logger.debug("→ Routing to StandardHandler (standard)")
            return await self.standard_handler.handle(
                preprocessed_data, start_time, language=language
            )

    def _build_clarification_message(
        self, missing_fields: List[str], language: str = "fr"
    ) -> str:
        """Build clarification message in appropriate language"""
        if language == "en":
            if len(missing_fields) == 1:
                return f"Please specify the {missing_fields[0]} to continue."
            else:
                fields = ", ".join(missing_fields[:-1]) + f" and {missing_fields[-1]}"
                return f"Please specify the following information: {fields}."
        else:  # French by default
            if len(missing_fields) == 1:
                field_fr = self._translate_field_name(missing_fields[0])
                return f"Veuillez préciser {field_fr} pour continuer."
            else:
                fields_fr = [self._translate_field_name(f) for f in missing_fields]
                fields_str = ", ".join(fields_fr[:-1]) + f" et {fields_fr[-1]}"
                return f"Veuillez préciser les informations suivantes : {fields_str}."

    def _translate_field_name(self, field: str) -> str:
        """Translate field name to French"""
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
