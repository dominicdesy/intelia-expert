# -*- coding: utf-8 -*-
"""
Query processor - Handles query processing pipeline for RAG engine
"""

import logging
import structlog
import time
import uuid
from utils.types import Dict, List, Any, Optional

from .data_models import RAGResult, RAGSource
from .query_enricher import ConversationalQueryEnricher
from utils.clarification_helper import get_clarification_helper

logger = logging.getLogger(__name__)
structured_logger = structlog.get_logger()


class RAGQueryProcessor:
    """Processes queries through the RAG pipeline"""

    def __init__(self, query_router, handlers, conversation_memory=None, ood_detector=None):
        """
        Initialize query processor

        Args:
            query_router: QueryRouter instance
            handlers: Dict of handler instances (temporal, comparative, standard)
            conversation_memory: Optional ConversationMemory instance
            ood_detector: Optional OOD detector instance
        """
        self.query_router = query_router
        self.temporal_handler = handlers.get("temporal")
        self.comparative_handler = handlers.get("comparative")
        self.standard_handler = handlers.get("standard")
        self.conversation_memory = conversation_memory
        self.ood_detector = ood_detector
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
        Main query processing pipeline with clarification loop support

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
        # Generate unique request ID for tracking
        request_id = str(uuid.uuid4())

        # Structured logging: Query started
        structured_logger.info(
            "query_started",
            request_id=request_id,
            tenant_id=tenant_id,
            query_length=len(query),
            language=language,
            has_context=conversation_context is not None,
            has_preextracted_entities=preextracted_entities is not None,
            timestamp=time.time(),
        )

        logger.info(f"Processing query with language: {language}")

        # Step 0: Check if this is a clarification response
        pending_clarification = None
        saved_domain = None  # 🆕 Domaine sauvegardé pour réutilisation
        if self.conversation_memory:
            pending_clarification = self.conversation_memory.get_pending_clarification(
                tenant_id
            )

            if pending_clarification:
                # Check if current query is answering the clarification
                if self.conversation_memory.is_clarification_response(query, tenant_id):
                    logger.info(
                        f"✅ Clarification response detected for tenant {tenant_id}"
                    )

                    # 🆕 Récupérer le domaine sauvegardé pour réutilisation
                    saved_domain = pending_clarification.get("detected_domain")
                    if saved_domain:
                        logger.info(f"♻️ Réutilisation domaine sauvegardé: {saved_domain}")

                    # Merge original query with clarification
                    original_query = pending_clarification.get("original_query", "")
                    merged_query = (
                        self.conversation_memory.merge_query_with_clarification(
                            original_query, query
                        )
                    )

                    logger.info(f"🔗 Merged query: {merged_query}")

                    # Clear pending clarification
                    self.conversation_memory.clear_pending_clarification(tenant_id)

                    # Use merged query for processing
                    query = merged_query
                else:
                    # Increment attempt counter
                    self.conversation_memory.increment_clarification_attempt(tenant_id)

        # Step 0.5: OOD Detection (before routing)
        if self.ood_detector:
            try:
                is_in_domain, domain_score, score_details = (
                    self.ood_detector.calculate_ood_score_multilingual(
                        query, None, language
                    )
                )

                if not is_in_domain:
                    logger.warning(f"⛔ OUT-OF-DOMAIN query detected (LLM): '{query[:60]}...'")
                    from config.messages import get_message
                    ood_message = get_message("ood_rejection", language)
                    return RAGResult(
                        source=RAGSource.OOD_FILTERED,
                        answer=ood_message,
                        sources=[],
                        metadata={
                            "ood_score": domain_score,
                            "ood_details": score_details,
                            "query_type": "out_of_domain",
                        },
                        query_type="out_of_domain",
                        conversation_id=tenant_id,
                        processing_time_ms=(time.time() - start_time) * 1000,
                    )
                else:
                    logger.info(f"✅ IN-DOMAIN query (LLM): '{query[:60]}...'")
            except Exception as e:
                logger.error(f"❌ OOD detection error: {e}")
                # Continue processing on error (fail-open)

        # Step 1: Retrieve contextual history
        contextual_history = await self._get_contextual_history(tenant_id, query)

        # Step 2: Enrich query if history available
        enriched_query = self._enrich_query(query, contextual_history, language)

        # Step 2b: Always extract entities from context if available
        extracted_entities = None
        if contextual_history and self.conversation_memory:
            # Always try to extract entities from enriched context
            # 🔒 Pass current query to prevent age contamination in standalone queries
            try:
                extracted_entities = self.enricher.extract_entities_from_context(
                    contextual_history, language, current_query=query
                )
                if extracted_entities:
                    logger.info(
                        f"📦 Entities extracted from context: {extracted_entities}"
                    )

                    # Structured logging: Entity extraction
                    structured_logger.info(
                        "entities_extracted",
                        request_id=request_id,
                        extracted_entities=extracted_entities,
                    )
            except Exception as e:
                logger.warning(f"Failed to extract entities from context: {e}")
                structured_logger.warning(
                    "entity_extraction_failed", request_id=request_id, error=str(e)
                )

        # Step 3: Route query with context-extracted entities
        step3_start = time.time()
        route = self.query_router.route(
            query=enriched_query,
            user_id=tenant_id,
            language=language,
            preextracted_entities=preextracted_entities or extracted_entities,
            override_domain=saved_domain,  # 🆕 Forcer domaine sauvegardé si clarification
        )
        step3_duration = time.time() - step3_start

        logger.info(
            f"QueryRouter → destination: {route.destination}, confidence: {route.confidence:.2%}"
        )

        # Structured logging: Routing completed
        structured_logger.info(
            "routing_completed",
            request_id=request_id,
            destination=route.destination,
            confidence=route.confidence,
            query_type=route.query_type,
            duration_ms=step3_duration * 1000,
            has_missing_fields=bool(route.missing_fields),
        )

        # Step 4: Check for clarification needs
        if route.destination == "needs_clarification":
            # Build clarification message
            clarification_result = self._build_clarification_result(
                route, language, query=query, tenant_id=tenant_id
            )

            # Mark clarification as pending in memory AND save exchange immediately
            if self.conversation_memory:
                self.conversation_memory.mark_pending_clarification(
                    tenant_id=tenant_id,
                    original_query=query,
                    missing_fields=route.missing_fields,
                    suggestions=route.validation_details.get("suggestions"),
                    language=language,
                    detected_domain=route.detected_domain,  # Save domain for reuse
                )
                logger.info(f"🔒 Clarification marked pending for tenant {tenant_id} (domain: {route.detected_domain})")

                # 💾 SAVE EXCHANGE IMMEDIATELY so next query can use context
                self.conversation_memory.add_exchange(
                    tenant_id=tenant_id,
                    question=query,
                    answer=clarification_result.answer
                )
                logger.info(f"💾 Clarification exchange saved immediately for tenant {tenant_id}")

            # Structured logging: Clarification needed
            structured_logger.info(
                "clarification_needed",
                request_id=request_id,
                missing_fields=route.missing_fields,
                total_duration_ms=(time.time() - start_time) * 1000,
            )

            return clarification_result

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
        step6_start = time.time()
        result = await self._route_to_handler(
            route, preprocessed_data, start_time, language
        )
        step6_duration = time.time() - step6_start

        # Structured logging: Query completed
        structured_logger.info(
            "query_completed",
            request_id=request_id,
            handler_type=route.destination,
            sources_count=len(result.sources) if hasattr(result, "sources") else 0,
            response_length=len(result.answer) if hasattr(result, "answer") else 0,
            handler_duration_ms=step6_duration * 1000,
            total_duration_ms=(time.time() - start_time) * 1000,
        )

        return result

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

    def _build_clarification_result(
        self, route, language: str, query: str = "", tenant_id: str = None
    ) -> RAGResult:
        """Build clarification result with intelligent contextual messages"""
        logger.info(f"Clarification needed - missing fields: {route.missing_fields}")

        # Utiliser le clarification helper pour message contextuel
        clarification_message = self.clarification_helper.build_clarification_message(
            missing_fields=route.missing_fields,
            language=language,
            query=query,
            entities=route.entities,
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
                "tenant_id": tenant_id,
                "original_query": query,
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
