"""
Backend i18n (internationalization) system for PDF exports and other server-side translations.
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Backend i18n (internationalization) system for PDF exports and other server-side translations.
Supports 16 languages with JSON-based translation files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class I18n:
    """
    Internationalization utility for backend services.
    Loads and caches translation files for PDF exports and other server-side content.
    """

    # Supported languages
    SUPPORTED_LANGUAGES = [
        'en', 'fr', 'es', 'de', 'pt', 'it', 'nl', 'pl',
        'tr', 'ar', 'zh', 'ja', 'hi', 'th', 'vi', 'id'
    ]

    # Default language fallback
    DEFAULT_LANGUAGE = 'en'

    def __init__(self):
        """Initialize the i18n system"""
        self._translations: Dict[str, Dict[str, str]] = {}
        self._locales_path = Path(__file__).parent.parent / "locales"
        logger.info(f"I18n initialized with locales path: {self._locales_path}")

    def _load_translation_file(self, language: str) -> Dict[str, str]:
        """
        Load a translation file for a specific language.

        Args:
            language: Language code (e.g., 'en', 'fr', 'es')

        Returns:
            Dictionary of translation keys and values
        """
        file_path = self._locales_path / f"{language}.json"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                logger.debug(f"Loaded {len(translations)} translations for language '{language}'")
                return translations
        except FileNotFoundError:
            logger.warning(f"Translation file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in translation file {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading translation file {file_path}: {e}")
            return {}

    def get_translations(self, language: str) -> Dict[str, str]:
        """
        Get translations for a specific language (with caching).

        Args:
            language: Language code

        Returns:
            Dictionary of translations
        """
        # Normalize language code
        language = language.lower().strip()

        # Validate language
        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language '{language}', falling back to '{self.DEFAULT_LANGUAGE}'")
            language = self.DEFAULT_LANGUAGE

        # Check cache
        if language not in self._translations:
            self._translations[language] = self._load_translation_file(language)

        return self._translations[language]

    def translate(self, key: str, language: str, fallback: Optional[str] = None) -> str:
        """
        Translate a key to the specified language.

        Args:
            key: Translation key (e.g., 'pdf.generatedOn')
            language: Target language code
            fallback: Optional fallback text if translation not found

        Returns:
            Translated string
        """
        translations = self.get_translations(language)

        # Try to get translation
        if key in translations:
            return translations[key]

        # Try English fallback
        if language != self.DEFAULT_LANGUAGE:
            english_translations = self.get_translations(self.DEFAULT_LANGUAGE)
            if key in english_translations:
                logger.warning(f"Translation key '{key}' not found for '{language}', using English")
                return english_translations[key]

        # Use provided fallback or return the key itself
        if fallback:
            logger.warning(f"Translation key '{key}' not found, using fallback: {fallback}")
            return fallback

        logger.error(f"Translation key '{key}' not found for language '{language}'")
        return key  # Return the key itself as last resort

    def t(self, key: str, language: str = DEFAULT_LANGUAGE, fallback: Optional[str] = None) -> str:
        """
        Shorthand alias for translate()

        Args:
            key: Translation key
            language: Target language (default: English)
            fallback: Optional fallback text

        Returns:
            Translated string
        """
        return self.translate(key, language, fallback)


# Global singleton instance
_i18n_instance: Optional[I18n] = None


def get_i18n() -> I18n:
    """
    Get the global i18n instance (singleton pattern).

    Returns:
        I18n instance
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n()
    return _i18n_instance


# Convenience function for direct translation
def t(key: str, language: str = I18n.DEFAULT_LANGUAGE, fallback: Optional[str] = None) -> str:
    """
    Translate a key to the specified language (convenience function).

    Args:
        key: Translation key (e.g., 'pdf.generatedOn')
        language: Target language code (default: 'en')
        fallback: Optional fallback text

    Returns:
        Translated string

    Example:
        >>> from app.utils.i18n import t
        >>> t('pdf.page', 'fr')
        'Page'
        >>> t('pdf.generatedOn', 'es')
        'Generado el'
    """
    return get_i18n().translate(key, language, fallback)
