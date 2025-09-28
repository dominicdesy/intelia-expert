# -*- coding: utf-8 -*-
"""
utils/language_detection.py - Module de détection de langue multilingue
Extrait de utilities.py pour modularisation
"""

import os
import re
import time
import logging
from typing import Optional
from dataclasses import dataclass

# Imports conditionnels pour détection de langue
try:
    import fasttext
except ImportError:
    fasttext = None

try:
    from fastlangdetect import detect, LangDetectException
except ImportError:
    detect = None
    LangDetectException = Exception

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None

# Imports configuration
from config.config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    FALLBACK_LANGUAGE,
    LANG_DETECTION_MIN_LENGTH,
    LANG_DETECTION_CONFIDENCE_THRESHOLD,
    FASTTEXT_MODEL_PATH,
)

logger = logging.getLogger(__name__)

# FLAGS de disponibilité des modules (définis après imports)
FASTTEXT_AVAILABLE = fasttext is not None
FAST_LANGDETECT_AVAILABLE = detect is not None
UNIDECODE_AVAILABLE = unidecode is not None

# Log des disponibilités
if FASTTEXT_AVAILABLE:
    logger.info("FastText disponible pour détection multilingue")
if FAST_LANGDETECT_AVAILABLE:
    logger.info("fast-langdetect disponible comme fallback")
if not FASTTEXT_AVAILABLE and not FAST_LANGDETECT_AVAILABLE:
    logger.warning("Aucun module de détection de langue disponible")

# Variables globales
_fasttext_model = None

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
# FONCTIONS DE DÉTECTION DE LANGUE
# ============================================================================


def _load_fasttext_model():
    """Charge le modèle FastText avec lazy loading"""
    global _fasttext_model

    if not FASTTEXT_AVAILABLE:
        return None

    if _fasttext_model is None:
        try:
            model_path = FASTTEXT_MODEL_PATH
            if not os.path.exists(model_path):
                logger.warning(f"Modèle FastText non trouvé: {model_path}")
                logger.info(
                    "Le modèle devrait être pré-chargé au démarrage de l'application"
                )
                return None

            _fasttext_model = fasttext.load_model(model_path)
            logger.info(f"Modèle FastText chargé: {model_path}")

        except Exception as e:
            logger.warning(f"Erreur chargement FastText: {e}")
            _fasttext_model = None

    return _fasttext_model


def _detect_with_universal_patterns(text: str) -> Optional[str]:
    """Détection de langue via patterns universels du dictionnaire"""
    # Import local pour éviter la circularité
    from utils.translation_utils import get_translation_service

    translation_service = get_translation_service()
    if not translation_service:
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
            question_terms = translation_service.get_domain_terms(
                "question_words", lang
            )
            if any(term in text_lower for term in question_terms[:5]):  # Top 5 termes
                return lang

    return None


def detect_language_enhanced(text: str, default: str = None) -> LanguageDetectionResult:
    """
    Détection de langue multilingue avec FastText
    Remplace l'ancienne version langdetect avec support 13 langues
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

    # === LOGIQUE LONGUE: FastText ou fast-langdetect ===

    # 1. Essayer FastText en priorité
    if FASTTEXT_AVAILABLE:
        model = _load_fasttext_model()
        if model:
            try:
                predictions = model.predict(text_clean.replace("\n", " "), k=1)
                if predictions and len(predictions) >= 2:
                    lang_label = predictions[0][0].replace("__label__", "")
                    confidence = float(predictions[1][0])

                    # Normalisation code langue
                    if lang_label == "zh-cn":
                        lang_label = "zh"

                    # Vérification langue supportée
                    if (
                        lang_label in SUPPORTED_LANGUAGES
                        and confidence >= LANG_DETECTION_CONFIDENCE_THRESHOLD
                    ):
                        return LanguageDetectionResult(
                            language=lang_label,
                            confidence=confidence,
                            source="fasttext",
                            processing_time_ms=int((time.time() - start_time) * 1000),
                        )

            except Exception as e:
                logger.debug(f"Erreur FastText pour '{text_clean[:50]}...': {e}")

    # 2. Fallback vers fast-langdetect
    if FAST_LANGDETECT_AVAILABLE:
        try:
            result = detect(text_clean, low_memory=True)
            detected_lang = result["lang"]
            confidence = result["score"]

            # Normalisation et validation
            if detected_lang == "zh-cn":
                detected_lang = "zh"

            if (
                detected_lang in SUPPORTED_LANGUAGES
                and confidence >= LANG_DETECTION_CONFIDENCE_THRESHOLD
            ):
                return LanguageDetectionResult(
                    language=detected_lang,
                    confidence=confidence,
                    source="fast-langdetect",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

        except Exception as e:
            logger.debug(f"Erreur fast-langdetect pour '{text_clean[:50]}...': {e}")

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
