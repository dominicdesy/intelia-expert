# -*- coding: utf-8 -*-
"""
prompt_builder.py - Prompt building utilities for response generation

This module provides the PromptBuilder class that handles all prompt construction
logic for the response generation pipeline. It extracts prompt building methods
from generators.py into a dedicated, testable, and maintainable component.

The PromptBuilder class provides:
- Enhanced prompt construction with entity enrichment
- Critical language instructions for multilingual support
- Dynamic language examples generation
- Fallback system prompts
- Specialized prompts based on intent types

All methods support both Document objects and dictionary representations of documents.
"""

import logging
from typing import List, Tuple, Dict, Union

from config.config import SUPPORTED_LANGUAGES, FALLBACK_LANGUAGE
from core.data_models import Document
from .models import ContextEnrichment
from .language_handler import LanguageHandler
from .document_utils import DocumentUtils

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Centralized prompt building class for response generation.

    This class encapsulates all prompt construction logic, providing clean separation
    of concerns from the response generation pipeline. It uses LanguageHandler for
    language-related operations and DocumentUtils for document processing.

    Attributes:
        language_handler (LanguageHandler): Handler for language-related operations
        prompts_manager: Optional system prompts manager from config
        language_display_names (Dict[str, str]): Cached language display names

    Example:
        >>> builder = PromptBuilder(prompts_manager=None)
        >>> system_prompt, user_prompt = builder._build_enhanced_prompt(
        ...     query="What is the target weight?",
        ...     context_docs=documents,
        ...     enrichment=enrichment,
        ...     conversation_context="",
        ...     language="en"
        ... )
    """

    def __init__(self, prompts_manager=None):
        """
        Initialize the PromptBuilder with optional prompts manager.

        Args:
            prompts_manager: Optional system prompts manager from config.system_prompts
                           If None, fallback prompts will be used

        Notes:
            - Initializes LanguageHandler for multilingual support
            - Caches language display names for performance
            - Prompts manager is optional for flexibility in testing
        """
        self.prompts_manager = prompts_manager
        self.language_handler = LanguageHandler()
        # Cache language display names for faster access
        self.language_display_names = self.language_handler.language_display_names

        logger.info("✅ PromptBuilder initialized")

    def _build_enhanced_prompt(
        self,
        query: str,
        context_docs: List[Union[Document, dict]],
        enrichment: ContextEnrichment,
        conversation_context: str,
        language: str,
    ) -> Tuple[str, str]:
        """
        Build an enhanced prompt with entity enrichment and language instructions.

        This is the main prompt construction method that combines:
        - Language instructions (positioned at the top for emphasis)
        - Expert identity and response guidelines
        - Business context from entity enrichment
        - Conversation history
        - Technical documentation context
        - Question and response structure

        The method supports both Document objects and dictionary representations,
        and includes species detection from the query for context filtering.

        Args:
            query: User's question
            context_docs: List of relevant documents (Document objects or dicts)
            enrichment: Context enrichment with detected entities
            conversation_context: Previous conversation history (if any)
            language: Target language code (e.g., 'fr', 'en', 'es')

        Returns:
            Tuple[str, str]: (system_prompt, user_prompt) ready for LLM

        Examples:
            >>> builder = PromptBuilder()
            >>> system, user = builder._build_enhanced_prompt(
            ...     query="What's the target weight for Ross 308 at 35 days?",
            ...     context_docs=[doc1, doc2],
            ...     enrichment=ContextEnrichment(...),
            ...     conversation_context="",
            ...     language="en"
            ... )

        Notes:
            - Language instructions are placed at the TOP of system prompt for emphasis
            - Detects target species from query for context filtering
            - Logs critical information for debugging (context length, species detection)
            - Supports both camelCase and snake_case metadata keys
            - Limits context docs to top 5 for token efficiency
            - Each document preview limited to 1000 characters

        See Also:
            _get_critical_language_instructions(): Generates language instructions
            _get_fallback_system_prompt(): Fallback when prompts_manager unavailable
        """
        # Debug logging for conversation context validation
        logger.info(
            f"🔍 PROMPT - conversation_context type: {type(conversation_context)}"
        )
        logger.info(
            f"🔍 PROMPT - conversation_context length: {len(conversation_context) if conversation_context else 0}"
        )
        logger.info(
            f"🔍 PROMPT - conversation_context preview: {conversation_context[:200] if conversation_context else 'VIDE'}"
        )
        logger.info(
            f"🔍 PROMPT - conversation_context is truthy: {bool(conversation_context)}"
        )

        # Debug logging for language parameter
        logger.info(
            f"🌍 _build_enhanced_prompt received language parameter: '{language}'"
        )
        logger.debug(f"Query: '{query[:50]}...'")

        # Detect target species from query (multilingual detection)
        query_lower = query.lower()
        target_species = None

        # Multilingual species detection
        broiler_terms = [
            "poulet de chair",
            "broiler",
            "chair",
            "meat chicken",
            "pollo de engorde",
            "frango de corte",
        ]
        layer_terms = [
            "pondeuse",
            "layer",
            "ponte",
            "laying hen",
            "gallina ponedora",
            "poedeira",
        ]
        breeder_terms = [
            "reproducteur",
            "breeder",
            "parent",
            "parent stock",
            "reproductor",
        ]

        if any(term in query_lower for term in broiler_terms):
            target_species = "broilers"
        elif any(term in query_lower for term in layer_terms):
            target_species = "layers"
        elif any(term in query_lower for term in breeder_terms):
            target_species = "breeders"

        # Log species detection result
        if target_species:
            logger.info(f"🔍 Target species detected: {target_species}")
        else:
            logger.debug("🔍 No specific species detected in query")

        # Build context text from documents using DocumentUtils
        context_text_parts = []
        for i, doc in enumerate(context_docs[:5]):  # Limit to top 5 documents
            genetic_line = DocumentUtils._get_doc_metadata(doc, "geneticLine", "N/A")
            species = DocumentUtils._get_doc_metadata(doc, "species", "N/A")
            content = DocumentUtils._get_doc_content(doc)

            # Debug logging for each document
            logger.debug(
                f"📄 Doc {i+1}: line={genetic_line}, species={species}, content_len={len(content)}"
            )

            doc_text = f"Document {i+1} ({genetic_line} - {species}):\n{content[:1000]}"
            context_text_parts.append(doc_text)

        context_text = "\n\n".join(context_text_parts)

        # Critical logging of final context
        logger.info(f"📋 Context text length: {len(context_text)} chars")
        logger.debug(f"📋 Context preview: {context_text[:300]}...")

        # Get language display name
        language_name = self.language_display_names.get(language, language.upper())

        # Build system prompt
        if self.prompts_manager:
            expert_identity = self.prompts_manager.get_base_prompt(
                "expert_identity", language
            )
            response_guidelines = self.prompts_manager.get_base_prompt(
                "response_guidelines", language
            )

            system_prompt_parts = []

            # Language instructions AT THE TOP (emphasized positioning)
            language_instruction = f"""You are an expert in poultry production.
CRITICAL: Respond EXCLUSIVELY in {language_name} ({language}).

FORMATTING RULES - CLEAN & MODERN:
- NO bold headers with asterisks (**Header:**)
- Use simple paragraph structure with clear topic sentences
- Separate ideas with line breaks, not headers
- Use bullet points (- ) ONLY for lists, NEVER numbered lists (1., 2., 3.)
- Keep responses clean, concise and professional
- NO excessive formatting or visual artifacts
"""
            system_prompt_parts.append(language_instruction)

            if expert_identity:
                system_prompt_parts.append(expert_identity)

            context_section = f"""
CONTEXTE MÉTIER DÉTECTÉ:
{enrichment.entity_context}
{enrichment.species_focus}
{enrichment.temporal_context}
{enrichment.metric_focus}
"""
            system_prompt_parts.append(context_section)

            if response_guidelines:
                system_prompt_parts.append(response_guidelines)

            metrics_section = f"""
MÉTRIQUES PRIORITAIRES:
{', '.join(enrichment.performance_indicators[:3]) if enrichment.performance_indicators else 'Paramètres généraux de production'}
"""
            system_prompt_parts.append(metrics_section)

            system_prompt = "\n\n".join(system_prompt_parts)
        else:
            system_prompt = self._get_fallback_system_prompt(enrichment, language)

        # Simple validation of conversation context
        limited_context = conversation_context if conversation_context else ""

        # Build simplified user prompt
        user_prompt = f"""CONTEXTE CONVERSATIONNEL:
{limited_context}

INFORMATIONS TECHNIQUES DISPONIBLES:
{context_text}

ENRICHISSEMENT DÉTECTÉ:
- Entités métier: {enrichment.entity_context or 'Non spécifiées'}
- Focus performance: {', '.join(enrichment.performance_indicators) if enrichment.performance_indicators else 'Général'}
- Contexte temporel: {enrichment.temporal_context or 'Non spécifié'}

QUESTION:
{query}

RÉPONSE EXPERTE (affirmative, structurée, sans mention de sources):"""

        return system_prompt, user_prompt

    def _get_critical_language_instructions(self, language: str) -> str:
        """
        Generate critical language and formatting instructions for LLM prompts.

        This method delegates to LanguageHandler for consistent language instruction
        generation. It ensures the LLM responds in the correct language with proper
        formatting and minimal, precise answers.

        The instructions include:
        - Formatting rules (no excessive headers, clean structure)
        - Minimalistic response requirements (answer only what's asked)
        - Language consistency enforcement (no mixing languages)
        - Dynamic language examples for all supported languages

        Args:
            language: Target language code (e.g., 'fr', 'en', 'es')

        Returns:
            str: Multi-line instruction string for LLM system prompt

        Examples:
            >>> builder = PromptBuilder()
            >>> instructions = builder._get_critical_language_instructions('en')
            >>> 'ENGLISH' in instructions
            True
            >>> 'CRITICAL LANGUAGE REQUIREMENT' in instructions
            True

        Notes:
            - Validates language parameter and falls back if invalid
            - Includes strict formatting rules to prevent over-formatting
            - Emphasizes one question = one metric = one short answer
            - Contains concrete examples of good vs bad responses

        See Also:
            LanguageHandler._get_critical_language_instructions(): Actual implementation
        """
        return self.language_handler._get_critical_language_instructions(language)

    def _generate_language_examples(self) -> str:
        """
        Generate dynamic language examples for all supported languages.

        This method delegates to LanguageHandler to generate examples showing
        how to respond in each supported language. The examples are generated
        dynamically from SUPPORTED_LANGUAGES configuration.

        Returns:
            str: Multi-line string with language examples for all supported languages

        Examples:
            >>> builder = PromptBuilder()
            >>> examples = builder._generate_language_examples()
            >>> 'If question is in ENGLISH → Answer 100% in ENGLISH' in examples
            True

        Notes:
            - Generates two lines per language (English and French versions)
            - Uses display names from LanguageHandler
            - Languages sorted alphabetically by code

        See Also:
            LanguageHandler._generate_language_examples(): Actual implementation
        """
        return self.language_handler._generate_language_examples()

    def _get_fallback_system_prompt(
        self, enrichment: ContextEnrichment, language: str
    ) -> str:
        """
        Generate a fallback system prompt when prompts_manager is unavailable.

        This method provides a simplified but complete system prompt that can be used
        when the SystemPromptsManager is not available (e.g., during testing or if
        system_prompts.json is missing).

        The fallback prompt includes:
        - Language specification with validation
        - Business context from entity enrichment
        - Response directives (concise, precise, no source mentions)
        - Priority metrics

        Args:
            enrichment: Context enrichment with detected entities
            language: Target language code (e.g., 'fr', 'en', 'es')

        Returns:
            str: Complete fallback system prompt

        Examples:
            >>> builder = PromptBuilder(prompts_manager=None)
            >>> enrichment = ContextEnrichment(
            ...     entity_context="Ross 308",
            ...     metric_focus="weight",
            ...     temporal_context="35 days",
            ...     species_focus="broilers",
            ...     performance_indicators=["body weight", "FCR"],
            ...     confidence_boosters=[]
            ... )
            >>> prompt = builder._get_fallback_system_prompt(enrichment, 'en')
            >>> 'ENGLISH' in prompt
            True

        Notes:
            - Validates language and falls back to FALLBACK_LANGUAGE if invalid
            - Logs warning when invalid language is provided
            - Includes all essential context for coherent responses
            - Format is identical for all languages (only language name changes)
        """
        # Validate language
        if not language or language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Invalid language '{language}', using {FALLBACK_LANGUAGE}")
            language = FALLBACK_LANGUAGE

        language_name = self.language_display_names.get(language, language.upper())

        return f"""You are an expert in poultry production.
CRITICAL: Respond EXCLUSIVELY in {language_name} ({language}).

CONTEXTE MÉTIER:
{enrichment.entity_context}
{enrichment.species_focus}
{enrichment.temporal_context}
{enrichment.metric_focus}

DIRECTIVES:
- Réponse directe et concise (2-3 points maximum)
- Données chiffrées précises quand pertinent
- Format identique pour toutes les langues
- Ne JAMAIS mentionner les sources

MÉTRIQUES: {', '.join(enrichment.performance_indicators[:3]) if enrichment.performance_indicators else 'Paramètres généraux'}
"""

    def build_specialized_prompt(
        self, intent_type, entities: Dict[str, str], language: str
    ) -> str:
        """
        Generate a specialized prompt based on the intent type.

        This method creates intent-specific prompts that guide the LLM to provide
        focused responses appropriate to the type of question being asked. Different
        intent types receive different instructions for optimal response quality.

        Supported intent types:
        - METRIC_QUERY: Performance data and zootechnical standards
        - ENVIRONMENT_SETTING: Environmental parameters (temp, humidity, etc.)
        - DIAGNOSIS_TRIAGE: Structured differential diagnosis
        - ECONOMICS_COST: Economic analysis and cost data
        - PROTOCOL_QUERY: Veterinary protocols and biosecurity
        - GENERAL_POULTRY: General poultry expertise

        Args:
            intent_type: Type of intent (from processing.intent_types.IntentType)
            entities: Dictionary of detected entities (line, age_days, species, metrics)
            language: Target language code (currently not used in implementation)

        Returns:
            str: Specialized prompt enriched with entity context

        Examples:
            >>> from processing.intent_types import IntentType
            >>> builder = PromptBuilder()
            >>> prompt = builder.build_specialized_prompt(
            ...     IntentType.METRIC_QUERY,
            ...     {"line": "Ross 308", "age_days": "35", "species": "broilers"},
            ...     "en"
            ... )
            >>> "performances" in prompt.lower()
            True
            >>> "Ross 308" in prompt
            True

        Notes:
            - Returns empty string for unrecognized intent types
            - Entity context is appended if entities are provided
            - Supports multiple entity types: line, age_days, species, metrics
            - Language parameter preserved for future multilingual expansion

        See Also:
            processing.intent_types.IntentType: Intent type enumeration
        """
        from processing.intent_types import IntentType

        # Mapping of intents to specialized prompts
        specialized_prompts = {
            IntentType.METRIC_QUERY: """Focus: Données de performances et standards zootechniques.
Fournis valeurs cibles, plages optimales et facteurs d'influence.""",
            IntentType.ENVIRONMENT_SETTING: """Focus: Paramètres d'ambiance et gestion environnementale.
Fournis valeurs optimales de température, humidité, ventilation selon l'âge.""",
            IntentType.DIAGNOSIS_TRIAGE: """Focus: Diagnostic différentiel structuré.
Liste hypothèses par probabilité et examens complémentaires nécessaires.""",
            IntentType.ECONOMICS_COST: """Focus: Analyse économique et coûts.
Fournis données chiffrées sur coûts, marges et benchmarks du marché.""",
            IntentType.PROTOCOL_QUERY: """Focus: Protocoles vétérinaires et biosécurité.
Fournis calendriers de vaccination et mesures de prévention détaillés.""",
            IntentType.GENERAL_POULTRY: """Focus: Expertise avicole générale.
Style professionnel et structuré avec recommandations actionnables.""",
        }

        base_prompt = specialized_prompts.get(intent_type, "")

        # Contextual enrichment with entities
        if entities:
            entity_parts = []
            if "line" in entities:
                entity_parts.append(f"Lignée: {entities['line']}")
            if "age_days" in entities:
                entity_parts.append(f"Âge: {entities['age_days']}j")
            if "species" in entities:
                entity_parts.append(f"Espèce: {entities['species']}")
            if "metrics" in entities:
                entity_parts.append(f"Métriques: {entities['metrics']}")

            if entity_parts:
                base_prompt += f"\n\nCONTEXTE DÉTECTÉ: {' | '.join(entity_parts)}"

        return base_prompt


__all__ = ["PromptBuilder"]
