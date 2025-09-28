# -*- coding: utf-8 -*-
"""
utils/language_detection.py - Module de détection de langue multilingue
Version corrigée avec FastText proper et téléchargement automatique pour Digital Ocean
"""

import re
import time
import logging
from dataclasses import dataclass

# Imports conditionnels pour détection de langue
try:
    from fasttext_langdetect import detect_language as fasttext_detect

    FASTTEXT_LANGDETECT_AVAILABLE = True
except ImportError:
    fasttext_detect = None
    FASTTEXT_LANGDETECT_AVAILABLE = False

try:
    from langdetect import detect as langdetect_detect, LangDetectException

    LANGDETECT_AVAILABLE = True
except ImportError:
    langdetect_detect = None
    LangDetectException = Exception
    LANGDETECT_AVAILABLE = False

try:
    from unidecode import unidecode

    UNIDECODE_AVAILABLE = True
except ImportError:
    unidecode = None
    UNIDECODE_AVAILABLE = False

# Imports configuration
from config.config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    FALLBACK_LANGUAGE,
    LANG_DETECTION_MIN_LENGTH,
    LANG_DETECTION_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)

# Log des disponibilités
if FASTTEXT_LANGDETECT_AVAILABLE:
    logger.info("fasttext-langdetect disponible pour détection multilingue")
if LANGDETECT_AVAILABLE:
    logger.info("langdetect disponible comme fallback")
if not FASTTEXT_LANGDETECT_AVAILABLE and not LANGDETECT_AVAILABLE:
    logger.warning("Aucun module de détection de langue disponible")

# Variables globales - Plus besoin de _fasttext_model
_model_download_attempted = False

# ============================================================================
# CLASSES DE DONNÉES
# ============================================================================


@dataclass
class LanguageDetectionResult:
    """Résultat de détection de langue avec confiance - CORRIGÉ pour sérialisation JSON"""

    language: str
    confidence: float
    source: str  # "fasttext", "fast-langdetect", "universal_patterns", "fallback"
    processing_time_ms: int = 0

    def to_dict(self) -> dict:
        """Conversion en dictionnaire pour sérialisation JSON"""
        return {
            "language": self.language,
            "confidence": self.confidence,
            "source": self.source,
            "processing_time_ms": self.processing_time_ms,
        }

    def __hash__(self):
        """Rendre hashable pour utilisation comme clé de cache"""
        return hash(
            (self.language, self.confidence, self.source, self.processing_time_ms)
        )

    def __eq__(self, other):
        """Comparaison d'égalité pour le cache"""
        if not isinstance(other, LanguageDetectionResult):
            return False
        return (
            self.language == other.language
            and self.confidence == other.confidence
            and self.source == other.source
            and self.processing_time_ms == other.processing_time_ms
        )


# ============================================================================
# FONCTIONS DE DÉTECTION DE LANGUE - VERSION SIMPLIFIÉE
# ============================================================================


def _detect_with_universal_patterns(text: str) -> str:
    """Détection de langue via patterns universels du dictionnaire"""
    # Import local pour éviter la circularité
    try:
        from utils.translation_utils import get_translation_service

        translation_service = get_translation_service()
        if not translation_service:
            return None
    except ImportError:
        return None

    text_lower = text.lower()

    # Patterns techniques universels (indépendants de la langue)
    technical_patterns = {
        "fcr",
        "ross",
        "cobb",
        "hubbard",
        "kg",
        "gr",
        "poids",
        "weight",
        "days",
        "jours",
        "j",
        "d",
        "%",
        "mortality",
        "mortalité",
    }

    # Si contient des termes techniques, probable contexte avicole
    if any(pattern in text_lower for pattern in technical_patterns):
        # Vérification patterns par langue via service traduction
        for lang in SUPPORTED_LANGUAGES:
            # Récupérer termes questions dans cette langue
            try:
                question_terms = translation_service.get_domain_terms(
                    "question_words", lang
                )
                if any(
                    term in text_lower for term in question_terms[:5]
                ):  # Top 5 termes
                    return lang
            except Exception:
                continue

    return None


def detect_language_enhanced(text: str, default: str = None) -> LanguageDetectionResult:
    """
    Détection de langue multilingue sans compilation FastText
    Version optimisée pour Digital Ocean App Platform
    """
    start_time = time.time()

    if default is None:
        default = DEFAULT_LANGUAGE

    if not text or len(text.strip()) < 2:
        return LanguageDetectionResult(
            language=default,
            confidence=0.0,
            source="fallback",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    text_clean = text.strip()

    # === LOGIQUE COURTE: Patterns universels ===
    if len(text_clean) < LANG_DETECTION_MIN_LENGTH:

        # 1. Essayer patterns universels du dictionnaire
        universal_lang = _detect_with_universal_patterns(text_clean)
        if universal_lang:
            return LanguageDetectionResult(
                language=universal_lang,
                confidence=0.8,
                source="universal_patterns",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # 2. Patterns Unicode basiques
        # Chinois
        if re.search(r"[\u4e00-\u9fff]", text_clean):
            return LanguageDetectionResult(
                language="zh",
                confidence=0.9,
                source="unicode_patterns",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Hindi
        if re.search(r"[\u0900-\u097f]", text_clean):
            return LanguageDetectionResult(
                language="hi",
                confidence=0.9,
                source="unicode_patterns",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Thaï
        if re.search(r"[\u0e00-\u0e7f]", text_clean):
            return LanguageDetectionResult(
                language="th",
                confidence=0.9,
                source="unicode_patterns",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # Fallback pour texte court
        return LanguageDetectionResult(
            language=default,
            confidence=0.3,
            source="fallback",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # === LOGIQUE LONGUE: fasttext-langdetect puis langdetect ===

    # 1. Essayer fasttext-langdetect en priorité (sans compilation)
    if FASTTEXT_LANGDETECT_AVAILABLE:
        try:
            result = fasttext_detect(text_clean)
            detected_lang = result["lang"]
            confidence = result["score"]

            # Normalisation code langue
            if detected_lang == "zh-cn":
                detected_lang = "zh"

            # Vérification langue supportée
            if (
                detected_lang in SUPPORTED_LANGUAGES
                and confidence >= LANG_DETECTION_CONFIDENCE_THRESHOLD
            ):
                return LanguageDetectionResult(
                    language=detected_lang,
                    confidence=confidence,
                    source="fasttext_langdetect",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

        except Exception as e:
            logger.debug(f"Erreur fasttext-langdetect pour '{text_clean[:50]}...': {e}")

    # 2. Fallback vers langdetect standard
    if LANGDETECT_AVAILABLE:
        try:
            detected_lang = langdetect_detect(text_clean)
            confidence = 0.8  # langdetect ne fournit pas de score

            # Normalisation et validation
            if detected_lang == "zh-cn":
                detected_lang = "zh"

            if detected_lang in SUPPORTED_LANGUAGES:
                return LanguageDetectionResult(
                    language=detected_lang,
                    confidence=confidence,
                    source="langdetect",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

        except Exception as e:
            logger.debug(f"Erreur langdetect pour '{text_clean[:50]}...': {e}")

    # 3. Dernier recours: patterns universels même pour texte long
    universal_lang = _detect_with_universal_patterns(text_clean)
    if universal_lang:
        return LanguageDetectionResult(
            language=universal_lang,
            confidence=0.6,
            source="universal_patterns_fallback",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # 4. Fallback final
    return LanguageDetectionResult(
        language=FALLBACK_LANGUAGE,
        confidence=0.2,
        source="final_fallback",
        processing_time_ms=int((time.time() - start_time) * 1000),
    )


# ============================================================================
# SUPPORT DES LANGUES ET VALIDATION
# ============================================================================


def is_supported_language(language: str) -> bool:
    """Vérifie si une langue est supportée"""
    return language in SUPPORTED_LANGUAGES


def normalize_language_code(language: str) -> str:
    """Normalise un code langue vers le format supporté"""
    if not language:
        return DEFAULT_LANGUAGE

    # Normalisation des codes courants
    lang_lower = language.lower()

    # Mappings spéciaux
    mappings = {
        "zh-cn": "zh",
        "zh-tw": "zh",
        "zh-hans": "zh",
        "zh-hant": "zh",
        "en-us": "en",
        "en-gb": "en",
        "fr-fr": "fr",
        "fr-ca": "fr",
        "es-es": "es",
        "es-mx": "es",
        "pt-br": "pt",
        "pt-pt": "pt",
    }

    normalized = mappings.get(lang_lower, lang_lower.split("-")[0])

    # Vérification finale
    if normalized in SUPPORTED_LANGUAGES:
        return normalized

    return DEFAULT_LANGUAGE
