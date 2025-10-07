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
from utils.llm_translator import LLMTranslator

logger = logging.getLogger(__name__)
structured_logger = structlog.get_logger()


class RAGQueryProcessor:
    """Processes queries through the RAG pipeline"""

    def __init__(self, query_router, handlers, conversation_memory=None, ood_detector=None):
        """
        Initialize query processor

        Args:
            query_router: QueryRouter instance
            handlers: Dict of handler instances (temporal, comparative, standard, calculation)
            conversation_memory: Optional ConversationMemory instance
            ood_detector: Optional OOD detector instance
        """
        self.query_router = query_router
        self.temporal_handler = handlers.get("temporal")
        self.comparative_handler = handlers.get("comparative")
        self.standard_handler = handlers.get("standard")
        self.calculation_handler = handlers.get("calculation")
        self.conversation_memory = conversation_memory
        self.ood_detector = ood_detector
        self.enricher = ConversationalQueryEnricher()
        self.clarification_helper = get_clarification_helper()

        # Initialize LLM translator for multilingual support
        self.translator = LLMTranslator(cache_enabled=True)
        logger.info("✅ LLMTranslator initialized for query translation")

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

        # 🆕 STEP 0: Héritage de langue pour TOUTE la conversation
        # Si on a déjà une langue sauvegardée pour cette conversation, l'utiliser
        # Sauf si la query actuelle est longue et claire (> 10 mots)
        if self.conversation_memory:
            saved_language = self.conversation_memory.get_conversation_language(tenant_id)

            if saved_language:
                # Détecter si la query actuelle est courte/ambiguë
                query_stripped = query.strip()
                is_short_query = (
                    len(query_stripped) < 50 or  # Moins de 50 caractères
                    query_stripped.isdigit() or  # Juste un nombre
                    len(query_stripped.split()) <= 5  # 5 mots ou moins
                )

                # Hériter la langue sauf si query longue et langue détectée différente avec haute confiance
                if is_short_query or saved_language == language:
                    if saved_language != language:
                        logger.info(
                            f"🌍 Langue héritée de la conversation: {language} → {saved_language} "
                            f"(query: '{query_stripped[:50]}...')"
                        )
                        language = saved_language
            else:
                # Première question de la conversation: sauvegarder la langue
                self.conversation_memory.set_conversation_language(tenant_id, language)
                logger.info(f"🌍 Première question - langue sauvegardée: {language}")

        logger.info(f"Processing query with language: {language}")

        # Step 0.1: Check if this is a clarification response
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
        # 🆕 SKIP OOD detection si clarification en attente et query courte/numérique
        skip_ood = False
        if pending_clarification:
            # Détecter si query ressemble à une réponse de clarification
            query_stripped = query.strip()
            is_short = len(query_stripped) < 50
            is_numeric = query_stripped.isdigit()
            is_simple_response = is_short and (is_numeric or len(query_stripped.split()) <= 3)

            if is_simple_response:
                skip_ood = True
                logger.info(
                    f"⏭️ Skipping OOD detection - clarification response likely: '{query[:30]}...'"
                )

        if self.ood_detector and not skip_ood:
            try:
                is_in_domain, domain_score, score_details = (
                    self.ood_detector.calculate_ood_score_multilingual(
                        query, None, language
                    )
                )

                if not is_in_domain:
                    logger.warning(f"⛔ OUT-OF-DOMAIN query detected (LLM): '{query[:60]}...'")
                    from config.messages import get_message
                    ood_message = get_message("out_of_domain", language)
                    return RAGResult(
                        source=RAGSource.OOD_FILTERED,
                        answer=ood_message,
                        context_docs=[],  # Fixed: was 'sources'
                        processing_time=(time.time() - start_time),  # Fixed: was 'processing_time_ms'
                        metadata={
                            "ood_score": domain_score,
                            "ood_details": score_details,
                            "query_type": "out_of_domain",
                            "conversation_id": tenant_id,  # Moved to metadata
                        },
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

        # Step 2.5: Translate query to English for universal entity extraction
        # 🌍 Universal multilingual support: translate all non-English queries to English
        # before routing/extraction, allowing us to use only English patterns
        query_for_routing = enriched_query
        if language != "en":
            try:
                translation_start = time.time()
                query_for_routing = self.translator.translate(
                    enriched_query,
                    target_language="en",
                    source_language=language
                )
                translation_duration = time.time() - translation_start

                logger.info(
                    f"🌍 Query translated {language}→en ({translation_duration*1000:.0f}ms): "
                    f"'{enriched_query[:50]}...' → '{query_for_routing[:50]}...'"
                )

                structured_logger.info(
                    "query_translated",
                    request_id=request_id,
                    source_lang=language,
                    target_lang="en",
                    duration_ms=translation_duration * 1000,
                    original_length=len(enriched_query),
                    translated_length=len(query_for_routing),
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Translation failed ({language}→en), using original: {e}"
                )
                # Fallback: use original query if translation fails
                query_for_routing = enriched_query
        else:
            logger.debug("Query already in English, skipping translation")

        # Step 3: Route query with context-extracted entities
        step3_start = time.time()
        route = self.query_router.route(
            query=query_for_routing,  # 🆕 Use translated query for routing/extraction
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
            query_for_routing,  # 🆕 Use translated query for extraction/retrieval
            query,  # Keep original for display
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
        elif route.destination == "comparative":
            query_type = "comparative"
        elif route.destination == "calculation":
            query_type = "calculation"
        else:  # hybrid
            query_type = "standard"

        # Extract comparative info from entities
        is_comparative = route.entities.get("is_comparative", False)
        comparison_entities = route.entities.get("comparison_entities", [])

        preprocessed_data = {
            "normalized_query": enriched_query,
            "original_query": original_query,
            "entities": route.entities,
            "language": language,
            "routing_hint": route.destination,
            "is_comparative": is_comparative,
            "comparison_entities": comparison_entities,
            "query_type": query_type,
            "metadata": {
                "original_query": original_query,
                "normalized_query": enriched_query,
                "routing_hint": route.destination,
                "is_comparative": is_comparative,
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

        elif query_type == "calculation":
            logger.debug("→ Routing to CalculationQueryHandler")
            if self.calculation_handler:
                # Extract entities for calculation
                entities = preprocessed_data.get("entities", {})
                query = preprocessed_data.get("query", "")
                result = await self.calculation_handler.handle(
                    query=query,
                    entities=entities,
                    language=language
                )

                # Convert to RAGResult format
                if result.get("success"):
                    calc_result = result.get("calculation_result", {})

                    # Build context_docs from calculation details for RAGAS evaluation
                    context_docs = self._build_calculation_contexts(calc_result, result.get("calculation_type"))

                    # Debug: Verify contexts are being built
                    logger.info(f"🔍 DEBUG: Built {len(context_docs)} context docs for calculation")
                    for i, ctx in enumerate(context_docs):
                        logger.info(f"   Context {i+1}: {len(ctx.get('content', ''))} chars")

                    return RAGResult(
                        source=RAGSource.RETRIEVAL_SUCCESS,
                        answer=self._format_calculation_answer(calc_result, language),
                        confidence=calc_result.get("confidence", 0.9),
                        context_docs=context_docs,
                        metadata={
                            "query_type": "calculation",
                            "calculation_type": result.get("calculation_type"),
                            "calculation_result": calc_result,
                            "context_docs_count": len(context_docs),  # DEBUG
                        },
                    )
                else:
                    return RAGResult(
                        source=RAGSource.ERROR,
                        answer=f"Calculation error: {result.get('error', 'Unknown error')}",
                        metadata={"query_type": "calculation", "error": result.get("error")},
                    )
            else:
                logger.warning("⚠️ CalculationHandler not available, falling back to StandardHandler")
                preprocessed_data["is_calculation"] = True
                return await self.standard_handler.handle(
                    preprocessed_data, start_time, language=language
                )

        elif query_type == "optimization":
            logger.debug(f"→ Routing to StandardHandler (type=optimization)")
            preprocessed_data["is_optimization"] = True
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

    def _format_calculation_answer(self, calc_result: Dict[str, Any], language: str = "fr") -> str:
        """Format calculation result into natural language answer"""

        # Cumulative feed calculation
        if "total_feed_kg" in calc_result:
            age_start = calc_result.get("age_start")
            age_end = calc_result.get("age_end")
            total_kg = calc_result.get("total_feed_kg")
            target_weight = calc_result.get("target_weight")
            details = calc_result.get("details", {})
            interpolation_applied = details.get("interpolation_applied", False)

            if language == "en":
                answer = f"To reach a target weight of {target_weight}g at day {age_end}, "
                answer += f"you will need {total_kg} kg of feed per bird "
                answer += f"from day {age_start} to day {age_end}"
                if interpolation_applied:
                    ratio = details.get("interpolation_ratio", 1.0)
                    answer += f" (with proportional adjustment of {ratio:.1%} for the final day)"
                answer += "."
            else:
                answer = f"Pour atteindre un poids cible de {target_weight}g au jour {age_end}, "
                answer += f"vous aurez besoin de {total_kg} kg d'aliment par poulet "
                answer += f"entre le jour {age_start} et le jour {age_end}"
                if interpolation_applied:
                    ratio = details.get("interpolation_ratio", 1.0)
                    answer += f" (avec ajustement proportionnel de {ratio:.1%} pour le dernier jour)"
                answer += "."

            return answer

        # Reverse lookup (age for target weight)
        elif "age_found" in calc_result:
            age = calc_result.get("age_found")
            target = calc_result.get("target_weight")
            actual = calc_result.get("weight_found")

            if language == "en":
                answer = f"The target weight of {target}g is reached at approximately day {age} "
                answer += f"(actual weight: {actual}g)."
            else:
                answer = f"Le poids cible de {target}g est atteint vers le jour {age} "
                answer += f"(poids réel: {actual}g)."

            return answer

        # Projection
        elif "projected_weight_kg" in calc_result:
            weight_kg = calc_result.get("projected_weight_kg")
            age_end = calc_result.get("age_end")

            if language == "en":
                answer = f"The projected weight at day {age_end} is approximately {weight_kg} kg."
            else:
                answer = f"Le poids projeté au jour {age_end} est d'environ {weight_kg} kg."

            return answer

        # Flock calculation
        elif "total_live_weight_kg" in calc_result:
            flock_size = calc_result.get("flock_size")
            total_weight = calc_result.get("total_live_weight_kg")
            total_feed = calc_result.get("total_feed_consumed_kg")

            if language == "en":
                answer = f"For a flock of {flock_size} birds: "
                answer += f"total live weight = {total_weight} kg, "
                answer += f"total feed consumed = {total_feed} kg."
            else:
                answer = f"Pour un troupeau de {flock_size} poulets : "
                answer += f"poids vif total = {total_weight} kg, "
                answer += f"aliment total consommé = {total_feed} kg."

            return answer

        # Fallback
        return str(calc_result)

    def _build_calculation_contexts(self, calc_result: Dict[str, Any], calc_type: str) -> List[Dict[str, Any]]:
        """
        Build context documents from calculation results for RAGAS evaluation.

        Args:
            calc_result: Calculation result dictionary
            calc_type: Type of calculation performed

        Returns:
            List of context documents with content and metadata
        """
        contexts = []

        # Extract breed and gender info
        breed = calc_result.get("breed", "unknown")
        gender = calc_result.get("gender", "unknown")

        # Context 1: Source data used for calculation
        source_context = f"Source des données: Standards de performance pour {breed}"
        if gender != "unknown":
            source_context += f" ({gender})"
        source_context += ".\n"

        # Add calculation-specific details
        if "total_feed_kg" in calc_result:
            # Cumulative feed calculation
            age_start = calc_result.get("age_start")
            age_end = calc_result.get("age_end")
            target_weight = calc_result.get("target_weight")
            total_feed = calc_result.get("total_feed_kg")

            source_context += f"Données utilisées: Consommation alimentaire cumulée du jour {age_start} au jour {age_end}.\n"
            source_context += f"Poids cible: {target_weight}g au jour {age_end}.\n"
            source_context += f"Résultat calculé: {total_feed} kg d'aliment par poulet."

            # Add interpolation details if present
            details = calc_result.get("details", {})
            if details.get("interpolation_applied"):
                ratio = details.get("interpolation_ratio", 1.0)
                source_context += f"\nAjustement proportionnel appliqué: {ratio:.1%} pour le dernier jour."

        elif "age_found" in calc_result:
            # Reverse lookup
            age = calc_result.get("age_found")
            target = calc_result.get("target_weight")
            actual = calc_result.get("weight_found")

            source_context += f"Recherche inversée effectuée pour trouver l'âge correspondant au poids cible de {target}g.\n"
            source_context += f"Résultat: Jour {age} avec poids réel de {actual}g."

        elif "projected_weight_kg" in calc_result:
            # Projection
            weight_kg = calc_result.get("projected_weight_kg")
            age_end = calc_result.get("age_end")

            source_context += f"Projection du poids au jour {age_end}.\n"
            source_context += f"Poids projeté: {weight_kg} kg."

        elif "total_live_weight_kg" in calc_result:
            # Flock calculation
            flock_size = calc_result.get("flock_size")
            total_weight = calc_result.get("total_live_weight_kg")
            total_feed = calc_result.get("total_feed_consumed_kg")

            source_context += f"Calcul pour un troupeau de {flock_size} poulets.\n"
            source_context += f"Poids vif total: {total_weight} kg.\n"
            source_context += f"Aliment total consommé: {total_feed} kg."

        contexts.append({
            "content": source_context,
            "metadata": {
                "source": "calculation_engine",
                "calculation_type": calc_type,
                "breed": breed,
                "gender": gender
            }
        })

        # Context 2: Methodology explanation
        methodology = "Méthodologie de calcul: "

        if "total_feed_kg" in calc_result:
            methodology += "Sommation de la consommation alimentaire quotidienne basée sur les courbes de référence pour la race. "
            methodology += "Les valeurs sont interpolées si l'âge exact n'est pas disponible dans les standards."

        elif "age_found" in calc_result:
            methodology += "Recherche dans les courbes de croissance pour identifier le jour où le poids cible est atteint. "
            methodology += "Interpolation linéaire utilisée entre les points de données disponibles."

        elif "projected_weight_kg" in calc_result:
            methodology += "Projection du poids basée sur les courbes de croissance standard pour la race. "
            methodology += "Extrapolation si l'âge dépasse les données de référence."

        elif "total_live_weight_kg" in calc_result:
            methodology += "Calcul du poids et de la consommation totale en multipliant les valeurs individuelles par la taille du troupeau."

        contexts.append({
            "content": methodology,
            "metadata": {
                "source": "calculation_methodology",
                "calculation_type": calc_type
            }
        })

        # Context 3: Data quality and confidence
        confidence = calc_result.get("confidence", 0.0)
        quality_context = f"Niveau de confiance du calcul: {confidence:.1%}.\n"

        # Add details about data quality
        details = calc_result.get("details", {})
        if details:
            if details.get("interpolation_applied"):
                quality_context += "Interpolation appliquée: Les valeurs pour certains jours ont été interpolées à partir des données disponibles.\n"
            if details.get("extrapolation_applied"):
                quality_context += "Extrapolation appliquée: Projection au-delà des données de référence disponibles.\n"
            if details.get("data_source"):
                quality_context += f"Source des données: {details.get('data_source')}.\n"

        quality_context += "Les calculs sont basés sur les standards de performance publiés par les sélectionneurs."

        contexts.append({
            "content": quality_context,
            "metadata": {
                "source": "data_quality",
                "confidence": confidence
            }
        })

        return contexts
