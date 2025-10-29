# -*- coding: utf-8 -*-
"""
response_generator.py - Main orchestrator for response generation
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
response_generator.py - Main orchestrator for response generation

Simple orchestration layer that coordinates all generation modules.
This replaces the monolithic EnhancedResponseGenerator class.

Usage:
    from generation.response_generator import ResponseGenerator

    generator = ResponseGenerator(
        client=openai_client,
        cache_manager=cache_manager,
        language="fr"
    )

    response = await generator.generate_response(
        query="What is the target weight?",
        context_docs=documents,
        language="en"
    )
"""

import logging
from utils.types import List, Optional, Union
from core.data_models import Document
from utils.utilities import METRICS

# Import modular components
from .models import ContextEnrichment
from .entity_manager import EntityEnrichmentBuilder
from .language_handler import LanguageHandler
from .prompt_builder import PromptBuilder
from .post_processor import ResponsePostProcessor
from .document_utils import DocumentUtils
from .llm_router import get_llm_router
from .proactive_assistant import get_proactive_assistant

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Main orchestrator for response generation

    Coordinates entity enrichment, prompt building, LLM generation,
    and post-processing through specialized modules.

    This class is a simple orchestrator that delegates to:
    - EntityEnrichmentBuilder: Build context from entities
    - LanguageHandler: Handle language operations
    - PromptBuilder: Build prompts with enrichment
    - ResponsePostProcessor: Clean and enhance responses
    - DocumentUtils: Convert and extract document data
    """

    def __init__(
        self,
        client,
        cache_manager=None,
        language: str = "fr",
        prompts_path: Optional[str] = None,
        descriptions_path: Optional[str] = None,
    ):
        """
        Initialize response generator

        Args:
            client: OpenAI client for LLM calls
            cache_manager: Optional cache manager for response caching
            language: Default language for responses
            prompts_path: Custom path to system_prompts.json
            descriptions_path: Custom path to entity_descriptions.json
        """
        self.client = client
        self.cache_manager = cache_manager
        self.language = language

        # Initialize modular components
        self.entity_enrichment_builder = EntityEnrichmentBuilder(descriptions_path)
        self.language_handler = LanguageHandler()

        # Initialize Multi-LLM Router for cost optimization
        self.llm_router = get_llm_router()

        # Initialize Proactive Assistant for follow-up questions
        self.proactive_assistant = get_proactive_assistant(language=language)

        # Load prompts manager if available
        try:
            from config.system_prompts import get_prompts_manager

            if prompts_path:
                self.prompts_manager = get_prompts_manager(prompts_path)
            else:
                self.prompts_manager = get_prompts_manager()
            logger.info("✅ ResponseGenerator initialized with system_prompts.json")
        except Exception as e:
            logger.warning(f"⚠️ Could not load prompts manager: {e}")
            self.prompts_manager = None

        self.prompt_builder = PromptBuilder(self.prompts_manager)

    async def generate_response(
        self,
        query: str,
        context_docs: List[Union[Document, dict]],
        conversation_context: str = "",
        language: Optional[str] = None,
        intent_result=None,
        user_id: Optional[str] = None,  # 🆕 User profiling
    ) -> str:
        """
        Generate enriched response with caching and post-processing

        Args:
            query: User query
            context_docs: List of context documents (Document objects or dicts)
            conversation_context: Optional conversation history
            language: Target language (uses default if not specified)
            intent_result: Optional intent classification result for enrichment
            user_id: Optional user ID for profile-based personalization

        Returns:
            Generated and post-processed response

        Example:
            >>> generator = ResponseGenerator(client)
            >>> response = await generator.generate_response(
            ...     query="What is the target weight at 35 days?",
            ...     context_docs=documents,
            ...     language="en",
            ...     user_id="user_12345"
            ... )
        """
        lang = language or self.language

        # Validate language
        lang = self.language_handler.validate_language(lang)

        # Protection against empty documents
        if not context_docs or len(context_docs) == 0:
            logger.warning("⚠️ Generator called with 0 documents")
            return self._get_insufficient_data_message(lang)

        logger.info(f"📄 Generating response with {len(context_docs)} documents")

        try:
            # Check cache
            cache_key = None
            if self.cache_manager and self.cache_manager.enabled:
                context_hash = self.cache_manager.generate_context_hash(
                    [DocumentUtils._doc_to_dict(doc) for doc in context_docs]
                )
                cached_response = await self.cache_manager.get_response(
                    query, context_hash, lang
                )
                if cached_response:
                    METRICS.cache_hit("response")
                    self._track_semantic_cache_metrics()
                    return cached_response
                METRICS.cache_miss("response")

            # Build entity enrichment
            enrichment = self._build_enrichment(intent_result)

            # Build prompts (with user profiling if user_id provided)
            system_prompt, user_prompt = self.prompt_builder._build_enhanced_prompt(
                query=query,
                context_docs=context_docs,
                enrichment=enrichment,
                conversation_context=conversation_context,
                language=lang,
                user_id=user_id,  # 🆕 Pass user_id for profiling
            )

            # Route query to optimal LLM provider
            context_dicts = [DocumentUtils._doc_to_dict(doc) for doc in context_docs]
            provider = self.llm_router.route_query(query, context_dicts, intent_result)

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Generate response via Multi-LLM Router
            # max_tokens=None → use adaptive calculation based on query complexity
            generated_response = await self.llm_router.generate(
                provider=provider,
                messages=messages,
                temperature=0.1,
                max_tokens=None,  # Let adaptive length calculate optimal value
                query=query,
                entities=getattr(intent_result, "detected_entities", None) if intent_result else None,
                query_type=getattr(intent_result, "intent_type", None) if intent_result else None,
                context_docs=context_dicts,
            )

            # Post-process response
            enhanced_response = ResponsePostProcessor.post_process_response(
                response=generated_response,
                enrichment=enrichment,
                context_docs=[DocumentUtils._doc_to_dict(doc) for doc in context_docs],
                query=query,
                language=lang,
            )

            # Generate proactive follow-up question
            follow_up = self.proactive_assistant.generate_follow_up(
                query=query,
                response=enhanced_response,
                intent_result=intent_result,
                entities=getattr(intent_result, "detected_entities", None) if intent_result else None,
                language=lang,
            )

            # Append follow-up to response if generated
            if follow_up:
                enhanced_response = f"{enhanced_response}\n\n{follow_up}"
                logger.info(f"✅ Proactive follow-up added: {follow_up[:50]}...")

            # Cache response
            if self.cache_manager and self.cache_manager.enabled and cache_key:
                await self.cache_manager.set_response(
                    query, context_hash, enhanced_response, lang
                )

            return enhanced_response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."

    def _build_enrichment(self, intent_result) -> ContextEnrichment:
        """
        Build context enrichment from intent result

        Args:
            intent_result: Intent classification result

        Returns:
            ContextEnrichment with entity context
        """
        if intent_result:
            return self.entity_enrichment_builder.build_enrichment(intent_result)
        else:
            return ContextEnrichment("", "", "", "", [], [])

    def _get_insufficient_data_message(self, language: str) -> str:
        """
        Get error message for insufficient data

        Args:
            language: Target language

        Returns:
            Error message in target language
        """
        if self.prompts_manager:
            error_msg = self.prompts_manager.get_error_message(
                "insufficient_data", language
            )
            if error_msg:
                return error_msg

        # Fallback message
        return "Je n'ai pas trouvé d'informations pertinentes dans ma base de connaissances pour répondre à votre question. Pouvez-vous reformuler ou être plus spécifique ?"

    def _track_semantic_cache_metrics(self):
        """Track semantic cache hit metrics if available"""
        if hasattr(self.cache_manager, "get_last_cache_details"):
            try:
                cache_hit_details = self.cache_manager.get_last_cache_details()
                if cache_hit_details.get("semantic_fallback_used"):
                    METRICS.semantic_fallback_used()
                else:
                    METRICS.semantic_cache_hit("exact")
            except Exception:
                pass


def create_response_generator(
    openai_client,
    cache_manager=None,
    language: str = "fr",
    prompts_path: Optional[str] = None,
    descriptions_path: Optional[str] = None,
) -> ResponseGenerator:
    """
    Factory function to create ResponseGenerator

    Args:
        openai_client: OpenAI client
        cache_manager: Optional cache manager
        language: Default language
        prompts_path: Custom path to system_prompts.json
        descriptions_path: Custom path to entity_descriptions.json

    Returns:
        ResponseGenerator instance

    Example:
        >>> generator = create_response_generator(
        ...     openai_client=client,
        ...     language="en"
        ... )
    """
    return ResponseGenerator(
        openai_client, cache_manager, language, prompts_path, descriptions_path
    )


__all__ = ["ResponseGenerator", "create_response_generator"]
