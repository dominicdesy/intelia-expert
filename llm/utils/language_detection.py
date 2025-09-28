# -*- coding: utf-8 -*-
"""
utils/language_detection.py - Module de détection de langue multilingue
Version corrigée avec FastText proper et téléchargement automatique pour Digital Ocean
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

    FASTTEXT_AVAILABLE = True
except ImportError:
    fasttext = None
    FASTTEXT_AVAILABLE = False

try:
    from fastlangdetect import detect, LangDetectException

    FAST_LANGDETECT_AVAILABLE = True
except ImportError:
    detect = None
    LangDetectException = Exception
    FAST_LANGDETECT_AVAILABLE = False

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
    FASTTEXT_MODEL_PATH,
)

logger = logging.getLogger(__name__)

# Log des disponibilités
if FASTTEXT_AVAILABLE:
    logger.info("FastText disponible pour détection multilingue")
if FAST_LANGDETECT_AVAILABLE:
    logger.info("fast-langdetect disponible comme fallback")
if not FASTTEXT_AVAILABLE and not FAST_LANGDETECT_AVAILABLE:
    logger.warning("Aucun module de détection de langue disponible")

# Variables globales
_fasttext_model = None
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
# FONCTIONS DE TÉLÉCHARGEMENT ET CHARGEMENT FASTTEXT
# ============================================================================


def _download_fasttext_model():
    """
    Télécharge automatiquement le modèle FastText sur Digital Ocean
    """
    global _model_download_attempted

    if _model_download_attempted:
        return None

    _model_download_attempted = True

    try:
        import requests
    except ImportError:
        logger.error("Module requests non disponible pour téléchargement FastText")
        return None

    model_url = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"

    # Essayer différents répertoires de destination sur Digital Ocean
    target_dirs = [
        "/tmp",  # Digital Ocean App Platform tmp
        "./models",
        ".",
        "/app/models",  # DO App Platform app directory
        os.path.join(os.path.dirname(__file__), "..", "models"),
    ]

    for target_dir in target_dirs:
        try:
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            model_path = os.path.join(target_dir, "lid.176.ftz")

            # Skip si déjà présent
            if os.path.exists(model_path) and os.path.getsize(model_path) > 100000:
                logger.info(f"Modèle FastText déjà présent: {model_path}")
                return model_path

            logger.info(f"Téléchargement du modèle FastText vers {model_path}...")

            response = requests.get(model_url, stream=True, timeout=120)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(model_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Log progress pour gros fichiers
                        if total_size > 0 and downloaded % (total_size // 10) == 0:
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Téléchargement: {progress:.1f}%")

            # Vérifier que le fichier est valide
            if os.path.getsize(model_path) > 100000:  # > 100KB
                logger.info(
                    f"✅ Modèle FastText téléchargé: {model_path} ({os.path.getsize(model_path)} bytes)"
                )
                return model_path
            else:
                logger.warning(f"Fichier téléchargé trop petit: {model_path}")
                os.remove(model_path)

        except Exception as e:
            logger.warning(f"Échec téléchargement vers {target_dir}: {e}")
            continue

    logger.error("❌ Impossible de télécharger le modèle FastText")
    return None


def _load_fasttext_model():
    """
    Charge le modèle FastText avec téléchargement automatique sur Digital Ocean
    """
    global _fasttext_model

    if not FASTTEXT_AVAILABLE:
        logger.warning(
            "FastText non disponible - installer avec: pip install fasttext==0.9.2"
        )
        return None

    if _fasttext_model is None:
        try:
            # Chemins possibles sur Digital Ocean App Platform
            possible_paths = [
                FASTTEXT_MODEL_PATH,  # Chemin configuré
                "/app/models/lid.176.ftz",
                "/tmp/lid.176.ftz",  # Tmp sur Digital Ocean
                "./models/lid.176.ftz",
                "./lid.176.ftz",
                os.path.join(os.path.dirname(__file__), "..", "models", "lid.176.ftz"),
            ]

            model_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    file_size = os.path.getsize(path)
                    if file_size > 100000:  # > 100KB
                        model_path = path
                        logger.debug(
                            f"Modèle FastText trouvé: {path} ({file_size} bytes)"
                        )
                        break

            # Si modèle non trouvé, télécharger automatiquement
            if not model_path:
                logger.info(
                    "Modèle FastText non trouvé - téléchargement automatique..."
                )
                model_path = _download_fasttext_model()

            if model_path and os.path.exists(model_path):
                logger.info(f"Chargement du modèle FastText: {model_path}")
                _fasttext_model = fasttext.load_model(model_path)
                logger.info("✅ Modèle FastText chargé avec succès")
            else:
                logger.error("❌ Impossible de charger le modèle FastText")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur chargement FastText: {e}")
            _fasttext_model = None

    return _fasttext_model


# ============================================================================
# FONCTIONS DE DÉTECTION DE LANGUE
# ============================================================================


def _detect_with_universal_patterns(text: str) -> Optional[str]:
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
    Détection de langue multilingue avec FastText - VERSION CORRIGÉE
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
                # Nettoyer le texte pour FastText
                text_for_fasttext = text_clean.replace("\n", " ").replace("\r", " ")
                predictions = model.predict(text_for_fasttext, k=1)

                if predictions and len(predictions) >= 2 and len(predictions[0]) > 0:
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
