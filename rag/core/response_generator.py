# -*- coding: utf-8 -*-
"""
Response generator - Ensures answers are generated from retrieved documents
Version: 1.4.1
Last modified: 2025-10-26
"""
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
        user_id: str = None,  # 🆕 User profiling and Compass user identification
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
            user_id: User ID for profiling and Compass barn identification

        Returns:
            RAGResult with generated answer and optional follow-up
        """
        # 🆕 SPECIAL HANDLING FOR COMPASS_DATA - Fetch real-time barn data
        if result.source == RAGSource.COMPASS_DATA:
            logger.info("🏚️ Compass data request detected - fetching real barn data")

            try:
                import httpx
                import os

                # Extract metadata from result
                barn_number = result.metadata.get("barn_number")
                query_type = result.metadata.get("query_type", "current_temperature")

                if not barn_number:
                    logger.error("No barn_number in metadata for COMPASS_DATA")
                    result.answer = "Je n'ai pas pu identifier le numéro du poulailler dans votre question."
                    return result

                if not user_id:
                    logger.error("No user_id available for Compass API call")
                    result.answer = "Je ne peux pas identifier l'utilisateur pour accéder aux données du poulailler."
                    return result

                # Call internal Backend endpoint (service-to-service, no JWT needed)
                # Backend URL should point to internal backend service
                backend_url = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")
                compass_url = f"{backend_url}/api/v1/compass/internal/user/{user_id}/barns/{barn_number}"

                logger.info(f"📡 Fetching Compass data from internal endpoint: {compass_url}")

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(compass_url)

                    if response.status_code != 200:
                        logger.error(f"Backend Compass API error: {response.status_code} - {response.text}")
                        if response.status_code == 404:
                            result.answer = f"Le poulailler {barn_number} n'a pas été trouvé dans votre configuration, ou Compass n'est pas activé pour votre compte."
                        else:
                            result.answer = f"Je n'ai pas pu récupérer les données du poulailler {barn_number}."
                        return result

                    barn_data = response.json()
                    logger.info(f"✅ Compass data fetched: {barn_data}")

                # Generate natural language response based on query type
                result.answer = self._generate_compass_answer(
                    barn_data, query_type, barn_number, language
                )

                # Update metadata with actual data fetched
                result.metadata["compass_data_fetched"] = True
                result.metadata["barn_data"] = barn_data

                logger.info(f"✅ Compass answer generated: {result.answer[:100]}...")
                return result

            except Exception as e:
                logger.error(f"Error fetching Compass data: {e}", exc_info=True)
                result.answer = f"Je n'ai pas pu accéder aux données temps réel du poulailler {barn_number}. Erreur: {str(e)}"
                return result

        # If answer NOT already present, generate via LLM
        if not (result.answer and result.answer.strip()):
            # DEFENSIVE: Ensure context_docs is never None
            if result.context_docs is None:
                result.context_docs = []

            # If documents present but no answer, generate via LLM
            # Robust check: handle both None and empty list cases
            if result.context_docs:
                if not self.generator:
                    logger.warning(
                        "LLM generator not available, cannot generate response"
                    )
                    result.answer = (
                        "Data retrieved but response generation unavailable."
                    )
                else:
                    logger.info(
                        f"Generating LLM response for {len(result.context_docs)} documents"
                    )

                    # Retrieve contextual history
                    contextual_history = (
                        preprocessed_data.get("contextual_history")
                        if preprocessed_data
                        else None
                    )

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
                            user_id=user_id,  # 🆕 Pass user_id for profiling
                        )

                        result.answer = generated_answer

                        # Ensure metadata exists before updating
                        if not result.metadata:
                            result.metadata = {}

                        result.metadata["llm_generation_applied"] = True
                        result.metadata["llm_input_docs_count"] = len(
                            result.context_docs
                        )
                        result.metadata["conversation_context_used"] = bool(
                            conversation_context
                        )
                        result.metadata["conversation_context_length"] = len(
                            conversation_context
                        )

                        logger.info(
                            f"LLM response generated ({len(result.answer)} characters)"
                        )

                    except Exception as e:
                        logger.error(f"LLM generation error: {e}", exc_info=True)
                        result.answer = (
                            "Unable to generate response from the retrieved data."
                        )
                        result.metadata["llm_generation_error"] = str(e)

            # FALLBACK: If NO documents found or LOW confidence, generate LLM response without context
            elif (
                result.source in (RAGSource.NO_RESULTS, RAGSource.LOW_CONFIDENCE)
                and self.generator
            ):
                logger.info(
                    f"{result.source} detected - generating LLM fallback response without context"
                )

                # Try to use LLM Ensemble for high-quality consensus response
                if LLM_ENSEMBLE_AVAILABLE and get_llm_ensemble:
                    try:
                        logger.info(
                            "Using LLM Ensemble (multi-LLM consensus) for fallback response"
                        )

                        # Get ensemble instance (uses Claude + OpenAI + DeepSeek in parallel)
                        ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N)

                        # Generate ensemble response with empty context (with user profiling)
                        ensemble_result = await ensemble.generate_ensemble_response(
                            query=original_query,
                            context_docs=[],  # Empty context - use LLM general knowledge
                            language=language,
                            entities=result.metadata.get("entities", {}),
                            query_type=result.metadata.get("query_type", "standard"),
                            domain=result.metadata.get("detected_domain", "poultry"),
                            user_id=user_id,  # 🆕 Pass user_id for profiling
                        )

                        result.answer = ensemble_result["final_answer"]
                        result.source = RAGSource.FALLBACK_NEEDED

                        if not result.metadata:
                            result.metadata = {}

                        result.metadata["llm_fallback_used"] = True
                        result.metadata["llm_ensemble_used"] = True
                        result.metadata["ensemble_provider"] = ensemble_result.get(
                            "provider"
                        )
                        result.metadata["ensemble_confidence"] = ensemble_result.get(
                            "confidence"
                        )
                        result.metadata["no_documents_reason"] = "LOW_CONFIDENCE"

                        logger.info(
                            f"LLM Ensemble fallback response generated ({len(result.answer)} characters) "
                            f"via {ensemble_result.get('provider')} (confidence: {ensemble_result.get('confidence', 0):.2f})"
                        )

                    except Exception as e:
                        logger.warning(
                            f"LLM Ensemble fallback failed: {e}, falling back to single LLM"
                        )
                        # Fallback to single LLM if ensemble fails
                        await self._fallback_single_llm(
                            result, original_query, language
                        )
                else:
                    # Use single LLM if ensemble not available
                    logger.info(
                        "LLM Ensemble not available, using single LLM for fallback"
                    )
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
                    logger.info(
                        f"✅ Proactive follow-up generated: {follow_up[:80]}..."
                    )
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
                f"Single LLM fallback response generated ({len(result.answer)} characters)"
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

    def _generate_compass_answer(
        self, barn_data: dict, query_type: str, barn_number: str, language: str
    ) -> str:
        """
        Generate natural language answer from Compass barn data

        Args:
            barn_data: Barn data from Compass API
            query_type: Type of query (current_temperature, today_min_max_temperature, etc.)
            barn_number: Barn number
            language: Response language

        Returns:
            Natural language answer
        """
        barn_name = barn_data.get("name", f"Poulailler {barn_number}")

        # Current temperature
        if query_type == "current_temperature":
            temp = barn_data.get("temperature")
            if temp is not None:
                return f"La température actuelle dans le {barn_name} (poulailler {barn_number}) est de {temp}°C."
            else:
                return f"Désolé, la température actuelle du {barn_name} n'est pas disponible en ce moment."

        # Today's min/max temperature
        elif query_type == "today_min_max_temperature":
            temp_min = barn_data.get("temperature_min_today")
            temp_max = barn_data.get("temperature_max_today")

            if temp_min is not None and temp_max is not None:
                return f"Aujourd'hui dans le {barn_name} (poulailler {barn_number}):\n- Température minimale: {temp_min}°C\n- Température maximale: {temp_max}°C"
            elif temp_max is not None:
                return f"Aujourd'hui, la température maximale dans le {barn_name} (poulailler {barn_number}) a été de {temp_max}°C."
            elif temp_min is not None:
                return f"Aujourd'hui, la température minimale dans le {barn_name} (poulailler {barn_number}) a été de {temp_min}°C."
            else:
                return f"Désolé, les données de température min/max d'aujourd'hui ne sont pas disponibles pour le {barn_name}."

        # Yesterday's average temperature
        elif query_type == "yesterday_avg_temperature":
            temp_avg = barn_data.get("temperature_avg_yesterday")
            if temp_avg is not None:
                return f"Hier, la température moyenne dans le {barn_name} (poulailler {barn_number}) était de {temp_avg}°C."
            else:
                return f"Désolé, la température moyenne d'hier n'est pas disponible pour le {barn_name}."

        # Yesterday's min/max temperature
        elif query_type == "yesterday_min_max_temperature":
            temp_min = barn_data.get("temperature_min_yesterday")
            temp_max = barn_data.get("temperature_max_yesterday")

            if temp_min is not None and temp_max is not None:
                return f"Hier dans le {barn_name} (poulailler {barn_number}):\n- Température minimale: {temp_min}°C\n- Température maximale: {temp_max}°C"
            elif temp_max is not None:
                return f"Hier, la température maximale dans le {barn_name} (poulailler {barn_number}) était de {temp_max}°C."
            elif temp_min is not None:
                return f"Hier, la température minimale dans le {barn_name} (poulailler {barn_number}) était de {temp_min}°C."
            else:
                return f"Désolé, les données de température min/max d'hier ne sont pas disponibles pour le {barn_name}."

        # Generic temperature query (yesterday or today)
        elif query_type in ("yesterday_temperature", "today_temperature"):
            temp = barn_data.get("temperature")
            if temp is not None:
                period = "hier" if "yesterday" in query_type else "aujourd'hui"
                return f"La température {period} dans le {barn_name} (poulailler {barn_number}) est de {temp}°C."
            else:
                period = "d'hier" if "yesterday" in query_type else "d'aujourd'hui"
                return f"Désolé, la température {period} n'est pas disponible pour le {barn_name}."

        # Default fallback
        else:
            temp = barn_data.get("temperature")
            if temp is not None:
                return f"La température actuelle dans le {barn_name} (poulailler {barn_number}) est de {temp}°C."
            else:
                return f"Désolé, les données de température ne sont pas disponibles pour le {barn_name} en ce moment."
