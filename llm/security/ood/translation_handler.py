# -*- coding: utf-8 -*-
"""
translation_handler.py - Translation service management with robust fallback

This module handles the initialization and management of the translation service
with safe initialization, caching, and health checking capabilities.
"""

import logging
from utils.types import Dict, Optional

logger = logging.getLogger(__name__)


class TranslationHandler:
    """
    Handler for translation service with robust error handling.

    This class manages the translation service lifecycle including safe
    initialization with fallback, query translation with caching, and
    health monitoring.

    Attributes:
        service: The translation service instance (or None if unavailable)
        cache: Translation cache for performance optimization
        supported_languages: List of supported language codes
    """

    def __init__(self, supported_languages: list = None):
        """
        Initialize the translation handler with safe fallback.

        Args:
            supported_languages: List of supported language codes (default: ['fr', 'en'])
        """
        self.service = self._init_translation_service_safe()
        self.cache = {}
        self.supported_languages = supported_languages or ["fr", "en"]

    def _init_translation_service_safe(self):
        """
        Initialize translation service with robust error handling.

        Attempts to initialize the translation service with multiple fallback
        strategies to ensure graceful degradation if the service is unavailable.

        Returns:
            Translation service instance or None if initialization fails
        """
        try:
            # Attempt to import and initialize
            from utils.translation_service import get_translation_service

            # Get existing service
            service = get_translation_service()

            if service is None:
                logger.debug(
                    "Service de traduction non initialisé, tentative d'initialisation..."
                )

                # Try to import configuration if available
                try:
                    from utils.translation_service import (
                        init_global_translation_service,
                    )
                    from config.config import (
                        SUPPORTED_LANGUAGES,
                        UNIVERSAL_DICT_PATH,
                        GOOGLE_TRANSLATE_API_KEY,
                        ENABLE_GOOGLE_TRANSLATE_FALLBACK,
                        TRANSLATION_CACHE_SIZE,
                        TRANSLATION_CACHE_TTL,
                        TRANSLATION_CONFIDENCE_THRESHOLD,
                    )

                    # Initialize with configuration
                    service = init_global_translation_service(
                        dict_path=UNIVERSAL_DICT_PATH,
                        supported_languages=SUPPORTED_LANGUAGES,
                        google_api_key=GOOGLE_TRANSLATE_API_KEY,
                        enable_google_fallback=ENABLE_GOOGLE_TRANSLATE_FALLBACK,
                        cache_size=TRANSLATION_CACHE_SIZE,
                        cache_ttl=TRANSLATION_CACHE_TTL,
                        confidence_threshold=TRANSLATION_CONFIDENCE_THRESHOLD,
                    )

                    if service:
                        logger.info("Service de traduction initialisé avec succès")
                    else:
                        logger.debug("Échec d'initialisation du service de traduction")

                except ImportError:
                    logger.debug(
                        "Configuration de traduction manquante, utilisation fallback"
                    )
                    service = None

            elif hasattr(service, "is_healthy") and not service.is_healthy():
                logger.debug("Service de traduction disponible mais non fonctionnel")
                service = None
            else:
                logger.debug("Service de traduction disponible et fonctionnel")

            return service

        except Exception as e:
            logger.debug(f"Erreur initialisation service de traduction: {e}")
            return None

    def translate_query(
        self,
        query: str,
        target_lang: str,
        source_lang: str = None,
        domain: str = "general_poultry",
    ) -> Optional[object]:
        """
        Translate a query with caching support.

        Translates the query using the translation service with result caching
        for improved performance on repeated queries.

        Args:
            query: The query text to translate
            target_lang: Target language code (e.g., 'fr', 'en')
            source_lang: Source language code (auto-detect if None)
            domain: Domain context for translation (default: 'general_poultry')

        Returns:
            Translation result object with text, confidence, and source attributes,
            or None if translation service is unavailable

        Raises:
            Exception: If translation fails with an error
        """
        if not self.is_available():
            logger.debug("Service de traduction indisponible pour traduction")
            return None

        # Check cache
        cache_key = f"{query}:{source_lang}:{target_lang}:{domain}"
        if cache_key in self.cache:
            logger.debug(f"Translation cache hit pour: {query[:30]}...")
            return self.cache[cache_key]

        try:
            # Perform translation
            translation_result = self.service.translate_term(
                query, target_lang, source_language=source_lang, domain=domain
            )

            # Cache the result
            self.cache[cache_key] = translation_result

            logger.debug(
                f"Traduction [{source_lang or 'auto'}→{target_lang}]: "
                f"'{query[:30]}...' → '{translation_result.text[:30]}...' "
                f"(confiance: {translation_result.confidence:.2f})"
            )

            return translation_result

        except Exception as e:
            logger.debug(f"Erreur lors de la traduction: {e}")
            raise

    def is_available(self) -> bool:
        """
        Check if translation service is available.

        Returns:
            True if translation service is initialized and available, False otherwise
        """
        return self.service is not None

    def is_healthy(self) -> bool:
        """
        Check if translation service is healthy and operational.

        Returns:
            True if service is available and healthy, False otherwise
        """
        if not self.is_available():
            return False

        if hasattr(self.service, "is_healthy"):
            return self.service.is_healthy()

        # If no health check method, assume healthy if available
        return True

    def get_stats(self) -> Dict:
        """
        Get translation handler statistics.

        Returns:
            Dictionary with handler statistics including cache size,
            service status, and supported languages
        """
        return {
            "service_available": self.is_available(),
            "service_healthy": self.is_healthy(),
            "cache_size": len(self.cache),
            "supported_languages": self.supported_languages,
            "service_type": (type(self.service).__name__ if self.service else "None"),
        }

    def clear_cache(self) -> None:
        """Clear the translation cache."""
        self.cache.clear()
        logger.debug("Translation cache cleared")
