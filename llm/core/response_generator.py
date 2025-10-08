# -*- coding: utf-8 -*-
"""
Response generator - Ensures answers are generated from retrieved documents
"""

import logging
from utils.types import Dict, Any

from .data_models import RAGResult, RAGSource

logger = logging.getLogger(__name__)

# Import ProactiveAssistant for follow-up questions
try:
    from generation.proactive_assistant import ProactiveAssistant
    PROACTIVE_ASSISTANT_AVAILABLE = True
except ImportError:
    PROACTIVE_ASSISTANT_AVAILABLE = False
    ProactiveAssistant = None
    logger.warning("ProactiveAssistant not available")

# Import LLM Ensemble for high-quality fallback responses
try:
    from generation.llm_ensemble import get_llm_ensemble, EnsembleMode
    LLM_ENSEMBLE_AVAILABLE = True
except ImportError:
    LLM_ENSEMBLE_AVAILABLE = False
    get_llm_ensemble = None
    EnsembleMode = None
    logger.warning("LLM Ensemble not available")


class RAGResponseGenerator:
    """Generates LLM responses from retrieved documents"""

    def __init__(self, llm_generator, enable_proactive: bool = True):
        """
        Initialize response generator

        Args:
            llm_generator: LLM generator instance
            enable_proactive: Enable proactive follow-up questions (default: True)
        """
        self.generator = llm_generator
        self.enable_proactive = enable_proactive

        # Initialize ProactiveAssistant if available
        self.proactive_assistant = None
        if enable_proactive and PROACTIVE_ASSISTANT_AVAILABLE and ProactiveAssistant:
            try:
                self.proactive_assistant = ProactiveAssistant(default_language="fr")
                logger.info("✅ ProactiveAssistant initialized in RAGResponseGenerator")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize ProactiveAssistant: {e}")

    async def ensure_answer_generated(
        self,
        result: RAGResult,
        preprocessed_data: Dict[str, Any],
        original_query: str,
        language: str,
    ) -> RAGResult:
        """
        Ensure RAGResult has a generated answer

        Checks if RAGResult contains documents but no answer, and generates
        one using the LLM generator if needed.

        Also adds proactive follow-up questions if enabled.

        Args:
            result: RAGResult from handler
            preprocessed_data: Preprocessed data (contains contextual_history)
            original_query: Original query
            language: Query language

        Returns:
            RAGResult with generated answer and optional follow-up
        """
        # If answer NOT already present, generate via LLM
        if not (result.answer and result.answer.strip()):
            # DEFENSIVE: Ensure context_docs is never None
            if result.context_docs is None:
                result.context_docs = []

            # If documents present but no answer, generate via LLM
            # Robust check: handle both None and empty list cases
            if result.context_docs:
                if not self.generator:
                    logger.warning("LLM generator not available, cannot generate response")
                    result.answer = "Data retrieved but response generation unavailable."
                else:
                    logger.info(
                        f"Generating LLM response for {len(result.context_docs)} documents"
                    )

                    # Retrieve contextual history
                    contextual_history = preprocessed_data.get("contextual_history") if preprocessed_data else None

                    logger.debug(
                        f"Contextual history type: {type(contextual_history)}, "
                        f"length: {len(contextual_history) if contextual_history else 0}"
                    )

                    # Format history for generator
                    conversation_context = ""
                    if contextual_history:
                        conversation_context = str(contextual_history)
                        logger.info(
                            f"Conversation context transmitted to generator: {len(conversation_context)} chars"
                        )
                    else:
                        logger.debug("No history in preprocessed_data")

                    try:
                        logger.debug(
                            f"Calling generate_response with conversation_context length: {len(conversation_context)}"
                        )

                        # Extract query with fallback
                        query_to_use = (
                            preprocessed_data.get("original_query", original_query)
                            if preprocessed_data
                            else original_query
                        )

                        # Generate answer with retrieved documents and conversation context
                        generated_answer = await self.generator.generate_response(
                            query=query_to_use,
                            context_docs=result.context_docs,
                            conversation_context=conversation_context,
                            language=language,
                            intent_result=None,
                        )

                        result.answer = generated_answer

                        # Ensure metadata exists before updating
                        if not result.metadata:
                            result.metadata = {}

                        result.metadata["llm_generation_applied"] = True
                        result.metadata["llm_input_docs_count"] = len(result.context_docs)
                        result.metadata["conversation_context_used"] = bool(
                            conversation_context
                        )
                        result.metadata["conversation_context_length"] = len(
                            conversation_context
                        )

                        logger.info(
                            f"LLM response generated ({len(generated_answer)} characters)"
                        )

                    except Exception as e:
                        logger.error(f"LLM generation error: {e}", exc_info=True)
                        result.answer = "Unable to generate response from the retrieved data."
                        result.metadata["llm_generation_error"] = str(e)

            # FALLBACK: If NO documents found or LOW confidence, generate LLM response without context
            elif result.source in (RAGSource.NO_RESULTS, RAGSource.LOW_CONFIDENCE) and self.generator:
                logger.info(f"{result.source} detected - generating LLM fallback response without context")

                # Try to use LLM Ensemble for high-quality consensus response
                if LLM_ENSEMBLE_AVAILABLE and get_llm_ensemble:
                    try:
                        logger.info("Using LLM Ensemble (multi-LLM consensus) for fallback response")

                        # Get ensemble instance (uses Claude + OpenAI + DeepSeek in parallel)
                        ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N)

                        # Generate ensemble response with empty context
                        ensemble_result = await ensemble.generate_ensemble_response(
                            query=original_query,
                            context_docs=[],  # Empty context - use LLM general knowledge
                            language=language,
                            entities=result.metadata.get("entities", {}),
                            query_type=result.metadata.get("query_type", "standard"),
                            domain=result.metadata.get("detected_domain", "poultry"),
                        )

                        result.answer = ensemble_result["final_answer"]
                        result.source = RAGSource.FALLBACK_NEEDED

                        if not result.metadata:
                            result.metadata = {}

                        result.metadata["llm_fallback_used"] = True
                        result.metadata["llm_ensemble_used"] = True
                        result.metadata["ensemble_provider"] = ensemble_result.get("provider")
                        result.metadata["ensemble_confidence"] = ensemble_result.get("confidence")
                        result.metadata["no_documents_reason"] = "LOW_CONFIDENCE"

                        logger.info(
                            f"LLM Ensemble fallback response generated ({len(result.answer)} characters) "
                            f"via {ensemble_result.get('provider')} (confidence: {ensemble_result.get('confidence', 0):.2f})"
                        )

                    except Exception as e:
                        logger.warning(f"LLM Ensemble fallback failed: {e}, falling back to single LLM")
                        # Fallback to single LLM if ensemble fails
                        await self._fallback_single_llm(result, original_query, language)
                else:
                    # Use single LLM if ensemble not available
                    logger.info("LLM Ensemble not available, using single LLM for fallback")
                    await self._fallback_single_llm(result, original_query, language)
        else:
            logger.debug("Answer already present, skipping LLM generation")

        # Generate proactive follow-up if enabled and answer exists
        # 🔧 FIX: Don't generate follow-up for clarifications (user needs to provide info first)
        is_clarification = (
            result.metadata.get("query_type") == "clarification_needed"
            or result.metadata.get("needs_clarification") is True
        )

        if (
            self.proactive_assistant
            and result.answer
            and result.answer.strip()
            and not is_clarification
        ):
            try:
                # Extract information for follow-up generation
                intent_result = {
                    "domain": result.metadata.get("detected_domain"),
                    "query_type": result.metadata.get("query_type"),
                }

                entities = result.metadata.get("entities", {})

                # Generate follow-up
                follow_up = self.proactive_assistant.generate_follow_up(
                    query=original_query,
                    response=result.answer,
                    intent_result=intent_result,
                    entities=entities,
                    language=language,
                )

                # Store follow-up in metadata (will be sent as separate SSE event)
                if follow_up and follow_up.strip():
                    result.metadata["proactive_followup"] = follow_up
                    logger.info(f"✅ Proactive follow-up generated: {follow_up[:80]}...")
                else:
                    logger.debug("No proactive follow-up generated for this query")

            except Exception as e:
                logger.warning(f"⚠️ Error generating proactive follow-up: {e}")
                # Don't fail the whole response if follow-up generation fails
        elif is_clarification:
            logger.debug(
                "🔒 Skipping proactive follow-up for clarification (waiting for user input)"
            )

        return result

    async def _fallback_single_llm(
        self, result: RAGResult, original_query: str, language: str
    ):
        """
        Fallback to single LLM when ensemble is unavailable or fails

        Args:
            result: RAGResult to update with generated answer
            original_query: Original user query
            language: Query language
        """
        try:
            # Generate response without specific context (general knowledge from LLM)
            generated_answer = await self.generator.generate_response(
                query=original_query,
                context_docs=[],  # Empty context
                language=language,
                conversation_context="",
            )

            result.answer = generated_answer
            result.source = RAGSource.FALLBACK_NEEDED

            if not result.metadata:
                result.metadata = {}

            result.metadata["llm_fallback_used"] = True
            result.metadata["llm_ensemble_used"] = False
            result.metadata["no_documents_reason"] = "LOW_CONFIDENCE"

            logger.info(
                f"Single LLM fallback response generated ({len(generated_answer)} characters)"
            )

        except Exception as e:
            logger.error(f"Single LLM fallback generation error: {e}", exc_info=True)
            result.answer = (
                "I don't have specific information about this in my database, "
                "but I can help with general poultry production questions."
            )
            if not result.metadata:
                result.metadata = {}
            result.metadata["llm_fallback_error"] = str(e)
