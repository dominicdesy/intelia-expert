# -*- coding: utf-8 -*-
"""
Response generator - Ensures answers are generated from retrieved documents
"""

import logging
from utils.types import Dict, Any

from .data_models import RAGResult

logger = logging.getLogger(__name__)

# Import ProactiveAssistant for follow-up questions
try:
    from generation.proactive_assistant import ProactiveAssistant
    PROACTIVE_ASSISTANT_AVAILABLE = True
except ImportError:
    PROACTIVE_ASSISTANT_AVAILABLE = False
    ProactiveAssistant = None
    logger.warning("ProactiveAssistant not available")


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
            # If documents present but no answer, generate via LLM
            if result.context_docs and len(result.context_docs) > 0:
                if not self.generator:
                    logger.warning("LLM generator not available, cannot generate response")
                    result.answer = "Data retrieved but response generation unavailable."
                else:
                    logger.info(
                        f"Generating LLM response for {len(result.context_docs)} documents"
                    )

                    # Retrieve contextual history
                    contextual_history = preprocessed_data.get("contextual_history", "")

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

                        # Generate answer with retrieved documents and conversation context
                        generated_answer = await self.generator.generate_response(
                            query=preprocessed_data.get("original_query", original_query),
                            context_docs=result.context_docs,
                            conversation_context=conversation_context,
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

                        logger.info(
                            f"LLM response generated ({len(generated_answer)} characters)"
                        )

                    except Exception as e:
                        logger.error(f"LLM generation error: {e}", exc_info=True)
                        result.answer = "Unable to generate response from the retrieved data."
                        result.metadata["llm_generation_error"] = str(e)
        else:
            logger.debug("Answer already present, skipping LLM generation")

        # Generate proactive follow-up if enabled and answer exists
        if self.proactive_assistant and result.answer and result.answer.strip():
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

        return result
