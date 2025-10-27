# -*- coding: utf-8 -*-
"""
language_handler.py - Language handling utilities for response generation
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
language_handler.py - Language handling utilities for response generation

This module provides centralized language management functionality, including:
- Loading language display names from configuration
- Generating fallback language names from ISO codes
- Creating critical language instructions for LLM prompts
- Generating dynamic language examples for consistent multilingual responses

The LanguageHandler class encapsulates all language-related logic that was
previously embedded in the EnhancedResponseGenerator class.
"""

import logging
from typing import Dict

from config.config import SUPPORTED_LANGUAGES, FALLBACK_LANGUAGE

logger = logging.getLogger(__name__)


class LanguageHandler:
    """
    Centralized handler for language-related operations in response generation.

    This class manages:
    - Language display name mappings (e.g., 'fr' -> 'FRENCH / FRANÇAIS')
    - Fallback language name generation
    - Dynamic language instruction generation for LLM prompts
    - Language-specific formatting rules and examples

    Attributes:
        language_display_names (Dict[str, str]): Mapping of ISO language codes to display names
    """

    def __init__(self):
        """
        Initialize the LanguageHandler by loading language display names.

        Attempts to load names from languages.json metadata, falling back to
        auto-generated names if the file is unavailable or incomplete.
        """
        self.language_display_names = self._load_language_names()

    def _load_language_names(self) -> Dict[str, str]:
        """
        Load language display names from languages.json configuration.

        Attempts to load the language_names mapping from the metadata section
        of languages.json. If unavailable, falls back to generating names
        automatically from SUPPORTED_LANGUAGES.

        Returns:
            Dict[str, str]: Mapping of language codes to display names
                           (e.g., {'fr': 'FRENCH / FRANÇAIS', 'en': 'ENGLISH'})

        Examples:
            >>> handler = LanguageHandler()
            >>> handler._load_language_names()
            {'de': 'GERMAN / DEUTSCH', 'en': 'ENGLISH', 'fr': 'FRENCH / FRANÇAIS', ...}

        Notes:
            - Logs success or warning based on whether languages.json is available
            - Automatically falls back to _generate_fallback_language_names() on error
        """
        try:
            from config.messages import load_messages

            messages_data = load_messages()

            # Extract language names from metadata
            if (
                "metadata" in messages_data
                and "language_names" in messages_data["metadata"]
            ):
                logger.info("✅ Noms de langues chargés depuis languages.json")
                return messages_data["metadata"]["language_names"]

            logger.warning(
                "language_names absent de languages.json, utilisation fallback"
            )

        except Exception as e:
            logger.warning(
                f"Erreur chargement noms de langues: {e}, utilisation fallback"
            )

        # Fallback: automatic generation from SUPPORTED_LANGUAGES
        return self._generate_fallback_language_names()

    def _generate_fallback_language_names(self) -> Dict[str, str]:
        """
        Generate fallback language display names from ISO codes.

        Creates a mapping of language codes to human-readable display names
        using a predefined base mapping. Only includes languages that are
        in SUPPORTED_LANGUAGES from config.

        Returns:
            Dict[str, str]: Mapping of supported language codes to display names

        Examples:
            >>> handler = LanguageHandler()
            >>> handler._generate_fallback_language_names()
            {'de': 'GERMAN / DEUTSCH', 'en': 'ENGLISH', 'es': 'SPANISH / ESPAÑOL', ...}

        Notes:
            - For unmapped languages, uses uppercase ISO code as fallback
            - Only returns languages present in SUPPORTED_LANGUAGES
            - Logs the number of languages successfully loaded
        """
        # Minimal mapping for supported languages
        base_names = {
            "de": "GERMAN / DEUTSCH",
            "en": "ENGLISH",
            "es": "SPANISH / ESPAÑOL",
            "fr": "FRENCH / FRANÇAIS",
            "hi": "HINDI / हिन्दी",
            "id": "INDONESIAN / BAHASA INDONESIA",
            "it": "ITALIAN / ITALIANO",
            "nl": "DUTCH / NEDERLANDS",
            "pl": "POLISH / POLSKI",
            "pt": "PORTUGUESE / PORTUGUÊS",
            "th": "THAI / ไทย",
            "zh": "CHINESE / 中文",
        }

        # Keep only truly supported languages
        result = {}
        for lang_code in SUPPORTED_LANGUAGES:
            if lang_code in base_names:
                result[lang_code] = base_names[lang_code]
            else:
                # Fallback for unmapped languages
                result[lang_code] = lang_code.upper()

        logger.info(f"✅ Fallback language names loaded: {len(result)} languages")
        return result

    def _get_critical_language_instructions(self, language: str) -> str:
        """
        Generate critical language and formatting instructions for LLM prompts.

        Creates comprehensive instructions for the LLM to ensure:
        - Responses are in the correct language
        - Formatting is clean and consistent
        - Answers are concise and directly address the question
        - No unnecessary information is added

        Args:
            language (str): Target language code (e.g., 'fr', 'en', 'es')

        Returns:
            str: Multi-line instruction string for LLM system prompt

        Examples:
            >>> handler = LanguageHandler()
            >>> instructions = handler._get_critical_language_instructions('en')
            >>> 'ENGLISH' in instructions
            True
            >>> 'CRITICAL LANGUAGE REQUIREMENT' in instructions
            True

        Notes:
            - Validates language parameter and falls back to FALLBACK_LANGUAGE if invalid
            - Includes dynamic language examples generated from SUPPORTED_LANGUAGES
            - Contains strict formatting rules to prevent excessive formatting
            - Emphasizes minimalistic, precise responses

        See Also:
            _generate_language_examples(): Generates the language examples section
        """
        logger.info(f"🌍 _get_critical_language_instructions received: '{language}'")

        # Defensive validation
        if not language:
            logger.error("❌ CRITICAL: language parameter is empty/None!")
            language = FALLBACK_LANGUAGE
        elif language not in SUPPORTED_LANGUAGES:
            logger.warning(
                f"⚠️ WARNING: language '{language}' not in SUPPORTED_LANGUAGES, using fallback"
            )
            language = FALLBACK_LANGUAGE

        # Get display name
        language_name = self.language_display_names.get(language, language.upper())

        logger.info(f"🌍 Language mapped: '{language}' → '{language_name}'")

        # Generate language examples dynamically
        language_examples = self._generate_language_examples()

        return f"""
INSTRUCTIONS CRITIQUES - STRUCTURE ET FORMAT:
- NE commence JAMAIS par un titre (ex: "## Maladie", "**Maladie**") - commence directement par la phrase d'introduction
- Examine les tableaux de données pour extraire les informations précises
- RÉPONDS UNIQUEMENT À LA QUESTION POSÉE - ne donne RIEN d'autre
- Utilise un ton affirmatif mais sobre, sans formatage excessif
- NE conclus PAS avec des recommandations pratiques sauf si explicitement demandé

RÈGLE ABSOLUE - RÉPONSE MINIMALISTE:
- Question sur le poids → Donne UNIQUEMENT le poids (1-2 phrases maximum)
- Question sur le FCR → Donne UNIQUEMENT le FCR (1-2 phrases maximum)
- Question sur "what about X?" → Donne UNIQUEMENT X (1-2 phrases maximum)
- N'ajoute JAMAIS de métriques supplémentaires non demandées
- Une question = une métrique = une réponse courte
- Si on demande seulement le poids, NE DONNE PAS feed intake, FCR, daily gain, etc.

EXEMPLES DE RÉPONSES CORRECTES:
Question: "What's the target weight for Ross 308 males at 35 days?"
❌ MAUVAIS: "At 35 days, males weigh 2441g with FCR 1.52 and feed intake 3720g."
✅ BON: "The target weight for Ross 308 males at 35 days is 2441 grams."

Question: "And what about females at the same age?"
❌ MAUVAIS: "At 35 days, females weigh 2150g. Feed intake is 3028g. Daily gain is 89g."
✅ BON: "At 35 days old, Ross 308 females have an average body weight of 2150 grams."

Question: "Quel est le poids cible à 35 jours?"
❌ MAUVAIS: "Le poids cible est 2441g avec un FCR de 1.52 et une consommation de 3720g."
✅ BON: "Le poids cible pour les mâles Ross 308 à 35 jours est de 2441 grammes."

COMPORTEMENT CONVERSATIONNEL:
- Pour questions techniques: réponse ULTRA-CONCISE avec données chiffrées
- Pour questions générales: ton professionnel mais accessible, réponses courtes
- Évite de poser trop de questions - réponds d'abord à la requête
- N'utilise PAS d'emojis sauf si l'utilisateur en utilise
- Maintiens la cohérence de format entre TOUTES les langues

{"="*80}
⚠️ CRITICAL LANGUAGE REQUIREMENT - IMPÉRATIF ABSOLU DE LANGUE ⚠️
{"="*80}

DETECTED QUESTION LANGUAGE / LANGUE DÉTECTÉE: {language_name}

🔴 MANDATORY RULE - RÈGLE OBLIGATOIRE:
YOU MUST RESPOND EXCLUSIVELY IN THE SAME LANGUAGE AS THE QUESTION.
VOUS DEVEZ RÉPONDRE EXCLUSIVEMENT DANS LA MÊME LANGUE QUE LA QUESTION.

DO NOT translate. DO NOT switch languages. DO NOT mix languages.
NE PAS traduire. NE PAS changer de langue. NE PAS mélanger les langues.

{language_examples}

THIS INSTRUCTION OVERRIDES ALL OTHER INSTRUCTIONS.
CETTE INSTRUCTION PRÉVAUT SUR TOUTES LES AUTRES INSTRUCTIONS.

YOUR RESPONSE LANGUAGE MUST BE: {language_name}
LANGUE DE VOTRE RÉPONSE DOIT ÊTRE: {language_name}

🎯 CRITICAL FORMAT CONSISTENCY:
- Answer format MUST be IDENTICAL regardless of language
- ONE question = ONE metric = ONE short answer (1-2 sentences)
- If question asks ONLY for weight → give ONLY weight
- If question asks ONLY for FCR → give ONLY FCR
- NO extra metrics, NO extra sections, NO extra information beyond what was asked
- Maintain EXACT SAME concise format across ALL languages

{"="*80}
"""

    def _generate_language_examples(self) -> str:
        """
        Generate dynamic language examples for consistent multilingual responses.

        Creates example instructions for each supported language to reinforce
        the requirement that responses must match the question language.
        Generated dynamically from SUPPORTED_LANGUAGES instead of hardcoding.

        Returns:
            str: Multi-line string with language examples

        Examples:
            >>> handler = LanguageHandler()
            >>> examples = handler._generate_language_examples()
            >>> 'If question is in ENGLISH → Answer 100% in ENGLISH' in examples
            True
            >>> 'Si question en FRENCH / FRANÇAIS → Réponse 100% en FRENCH / FRANÇAIS' in examples
            True

        Notes:
            - Generates two lines per language (English and French versions)
            - Uses display names from language_display_names mapping
            - Languages are sorted alphabetically by code
            - Fallback to uppercase ISO code if display name not found

        See Also:
            _get_critical_language_instructions(): Uses these examples in prompt
        """
        examples = []

        for lang_code in sorted(SUPPORTED_LANGUAGES):
            lang_name = self.language_display_names.get(lang_code, lang_code.upper())
            examples.append(
                f"If question is in {lang_name} → Answer 100% in {lang_name}"
            )
            examples.append(f"Si question en {lang_name} → Réponse 100% en {lang_name}")

        return "\n".join(examples)

    def get_language_name(self, language_code: str) -> str:
        """
        Get the display name for a language code.

        Args:
            language_code (str): ISO 639-1 language code (e.g., 'fr', 'en')

        Returns:
            str: Display name of the language (e.g., 'FRENCH / FRANÇAIS')
                 Falls back to uppercase code if not found

        Examples:
            >>> handler = LanguageHandler()
            >>> handler.get_language_name('fr')
            'FRENCH / FRANÇAIS'
            >>> handler.get_language_name('en')
            'ENGLISH'
            >>> handler.get_language_name('unknown')
            'UNKNOWN'
        """
        return self.language_display_names.get(language_code, language_code.upper())

    def validate_language(self, language: str) -> str:
        """
        Validate a language code and return a valid language.

        Checks if the provided language code is supported. If not,
        returns the FALLBACK_LANGUAGE with appropriate logging.

        Args:
            language (str): Language code to validate

        Returns:
            str: Valid language code (original or fallback)

        Examples:
            >>> handler = LanguageHandler()
            >>> handler.validate_language('fr')
            'fr'
            >>> handler.validate_language('invalid')
            'en'  # or whatever FALLBACK_LANGUAGE is set to

        Notes:
            - Logs warning when invalid language is provided
            - Logs error when language parameter is empty/None
            - Always returns a valid language code
        """
        if not language:
            logger.error("❌ CRITICAL: language parameter is empty/None!")
            return FALLBACK_LANGUAGE
        elif language not in SUPPORTED_LANGUAGES:
            logger.warning(
                f"⚠️ WARNING: language '{language}' not in SUPPORTED_LANGUAGES, using fallback"
            )
            return FALLBACK_LANGUAGE
        return language
