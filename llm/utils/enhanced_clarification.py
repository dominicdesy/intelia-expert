# -*- coding: utf-8 -*-
"""
enhanced_clarification.py - Enhanced Clarification System (Phase 3.2)

Wrapper that conditionally activates ClarificationHelper with graceful degradation
and integration with ContextManager for multi-turn conversations.

Features:
- Conditional activation based on API key availability
- Integration with ContextManager for context-aware clarification
- Graceful degradation if LLM translation unavailable
- Ambiguity detection (7 types)
- Multi-turn resolution support

Version: 1.0 (Phase 3.2)
"""

import logging
from typing import Dict, List, Optional, Any
from utils.clarification_helper import ClarificationHelper, get_clarification_helper

logger = logging.getLogger(__name__)


class EnhancedClarification:
    """
    Enhanced clarification system with conditional activation and graceful degradation

    Features:
    - Detects 7 types of ambiguity
    - Uses ContextManager for multi-turn context
    - Falls back gracefully if API key missing
    - Provides rich clarification messages in user's language

    Example:
        >>> clarifier = EnhancedClarification()
        >>> result = clarifier.check_and_clarify(
        ...     query="Traitement pour mes poulets",
        ...     missing_fields=['age', 'breed'],
        ...     language='fr'
        ... )
        >>> print(result['needs_clarification'])
        True
    """

    def __init__(
        self,
        config_path: str = "config/clarification_strategies.json",
        enable_llm_translation: bool = True
    ):
        """
        Initialize Enhanced Clarification system

        Args:
            config_path: Path to clarification strategies JSON
            enable_llm_translation: Enable LLM-based translation (default: True)
        """
        self.enable_llm_translation = enable_llm_translation
        self.helper = None
        self.helper_available = False

        # Try to initialize ClarificationHelper
        try:
            self.helper = get_clarification_helper(config_path)
            self.helper_available = True
            logger.info("✅ ClarificationHelper initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ ClarificationHelper initialization failed: {e}")
            logger.info("Will use fallback clarification (no LLM translation)")
            self.helper_available = False

    def is_available(self) -> bool:
        """
        Check if enhanced clarification is available

        Returns:
            True if ClarificationHelper is available
        """
        return self.helper_available

    def detect_ambiguity_type(
        self,
        query: str,
        missing_fields: List[str],
        entities: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Detect type of ambiguity in query

        7 Ambiguity Types:
        1. nutrition_ambiguity - Nutrition questions without production phase
        2. health_symptom_vague - Health questions with vague symptoms
        3. performance_incomplete - Performance questions missing breed/age
        4. environment_vague - Environment questions without specifics
        5. management_broad - Too broad management questions
        6. genetics_incomplete - Breed comparisons without criteria
        7. treatment_protocol_vague - Treatment questions without details

        Args:
            query: User query
            missing_fields: List of missing required fields
            entities: Extracted entities (optional)

        Returns:
            Ambiguity type string or None
        """
        if not self.helper_available or not self.helper:
            return None

        if entities is None:
            entities = {}

        try:
            ambiguity_type = self.helper.detect_ambiguity_type(
                query, missing_fields, entities
            )

            if ambiguity_type:
                logger.info(f"🔍 Ambiguity detected: {ambiguity_type}")

            return ambiguity_type

        except Exception as e:
            logger.error(f"Error detecting ambiguity: {e}")
            return None

    def build_clarification_message(
        self,
        query: str,
        missing_fields: List[str],
        language: str = 'en',
        entities: Optional[Dict] = None
    ) -> str:
        """
        Build contextual clarification message

        Args:
            query: Original user query
            missing_fields: List of missing required fields
            language: Target language code (en, fr, es, etc.)
            entities: Extracted entities (optional)

        Returns:
            Clarification message in target language
        """
        if entities is None:
            entities = {}

        # If helper available, use it
        if self.helper_available and self.helper:
            try:
                message = self.helper.build_clarification_message(
                    missing_fields=missing_fields,
                    language=language,
                    query=query,
                    entities=entities
                )
                logger.debug(f"✅ Clarification message built (lang={language})")
                return message

            except Exception as e:
                logger.error(f"Error building clarification message: {e}")
                # Fall through to fallback

        # Fallback: simple clarification without translation
        return self._build_fallback_message(missing_fields, language)

    def _build_fallback_message(
        self,
        missing_fields: List[str],
        language: str
    ) -> str:
        """
        Build simple fallback clarification message (no LLM translation)

        Args:
            missing_fields: List of missing fields
            language: Target language

        Returns:
            Simple clarification message
        """
        # Simple templates in English and French
        templates = {
            'en': {
                'intro': "To help you best, I need more information:",
                'breed': "- **Breed**: Ross 308, Cobb 500, other?",
                'age': "- **Age**: in days (e.g., 21 days, 35 days)",
                'sex': "- **Sex**: male, female, or as-hatched?",
                'metric': "- **Metric**: body weight, FCR, mortality?",
                'production_phase': "- **Production phase**: starter, grower, or finisher?",
            },
            'fr': {
                'intro': "Pour mieux vous aider, j'ai besoin de précisions:",
                'breed': "- **Race**: Ross 308, Cobb 500, autre?",
                'age': "- **Âge**: en jours (ex: 21 jours, 35 jours)",
                'sex': "- **Sexe**: mâle, femelle, ou mixte?",
                'metric': "- **Métrique**: poids vif, IC, mortalité?",
                'production_phase': "- **Phase de production**: démarrage, croissance, ou finition?",
            }
        }

        # Use English if language not supported
        lang_templates = templates.get(language, templates['en'])

        parts = [lang_templates['intro']]

        for field in missing_fields:
            if field in lang_templates:
                parts.append(lang_templates[field])

        return '\n'.join(parts)

    def check_and_clarify(
        self,
        query: str,
        missing_fields: List[str],
        language: str = 'en',
        entities: Optional[Dict] = None,
        intent_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Check if clarification is needed and build message

        Args:
            query: User query
            missing_fields: List of missing required fields
            language: Target language
            entities: Extracted entities
            intent_result: Intent classification result

        Returns:
            Dict with:
            - needs_clarification (bool): True if clarification needed
            - message (str): Clarification message
            - ambiguity_type (str|None): Type of ambiguity detected
            - missing_fields (List[str]): Original missing fields
        """
        if entities is None:
            entities = {}

        # Determine if clarification is needed
        needs_clarification = len(missing_fields) > 0

        if not needs_clarification:
            return {
                'needs_clarification': False,
                'message': '',
                'ambiguity_type': None,
                'missing_fields': []
            }

        # Detect ambiguity type
        ambiguity_type = self.detect_ambiguity_type(query, missing_fields, entities)

        # Build clarification message
        message = self.build_clarification_message(
            query=query,
            missing_fields=missing_fields,
            language=language,
            entities=entities
        )

        logger.info(f"📝 Clarification needed: {len(missing_fields)} fields, type={ambiguity_type}")

        return {
            'needs_clarification': True,
            'message': message,
            'ambiguity_type': ambiguity_type,
            'missing_fields': missing_fields,
            'language': language
        }

    def should_clarify_before_llm(
        self,
        query: str,
        missing_fields: List[str],
        confidence: float = 0.0
    ) -> bool:
        """
        Determine if should ask for clarification before LLM fallback

        Strategy:
        - If critical fields missing (breed, age) → clarify
        - If many fields missing (3+) → clarify
        - If low confidence and fields missing → clarify

        Args:
            query: User query
            missing_fields: List of missing fields
            confidence: Confidence score (0-1)

        Returns:
            True if should clarify before using LLM
        """
        # Critical fields that should trigger clarification
        critical_fields = {'breed', 'age', 'metric'}

        # If any critical field missing
        has_critical_missing = any(f in critical_fields for f in missing_fields)

        # If many fields missing
        many_missing = len(missing_fields) >= 3

        # If low confidence and any field missing
        low_confidence_missing = confidence < 0.5 and len(missing_fields) > 0

        should_clarify = has_critical_missing or many_missing or low_confidence_missing

        if should_clarify:
            logger.info(
                f"🔍 Should clarify: critical={has_critical_missing}, "
                f"many={many_missing}, low_conf={low_confidence_missing}"
            )

        return should_clarify


# Singleton instance
_enhanced_clarification_instance: Optional[EnhancedClarification] = None


def get_enhanced_clarification(
    config_path: str = "config/clarification_strategies.json",
    enable_llm_translation: bool = True
) -> EnhancedClarification:
    """
    Get singleton instance of EnhancedClarification

    Args:
        config_path: Path to clarification strategies
        enable_llm_translation: Enable LLM translation

    Returns:
        EnhancedClarification instance
    """
    global _enhanced_clarification_instance

    if _enhanced_clarification_instance is None:
        _enhanced_clarification_instance = EnhancedClarification(
            config_path=config_path,
            enable_llm_translation=enable_llm_translation
        )
        logger.debug("EnhancedClarification singleton initialized")

    return _enhanced_clarification_instance


__all__ = ['EnhancedClarification', 'get_enhanced_clarification']
