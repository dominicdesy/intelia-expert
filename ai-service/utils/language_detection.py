# -*- coding: utf-8 -*-
"""
utils/language_detection.py - Module de détection de langue multilingue
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
utils/language_detection.py - Module de détection de langue multilingue
Version corrigée avec FastText proper et téléchargement automatique pour Digital Ocean
"""

import re
import time
import logging
from dataclasses import dataclass
from typing import Optional
from utils.mixins import SerializableMixin

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
class LanguageDetectionResult(SerializableMixin):
    """Résultat de détection de langue avec confiance - CORRIGÉ pour sérialisation JSON"""

    language: str
    confidence: float
    source: str  # "fasttext", "fast-langdetect", "universal_patterns", "fallback"
    processing_time_ms: int = 0

    # to_dict() now inherited from SerializableMixin (removed 8 lines)

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


def _detect_language_by_grammar_patterns(text: str) -> Optional[str]:
    """
    Détection de langue via patterns grammaticaux forts

    Cette fonction utilise des marqueurs grammaticaux distinctifs pour identifier
    la langue de manière fiable, même en présence de termes techniques latins/internationaux.

    Args:
        text: Texte à analyser

    Returns:
        Code langue détecté (en, fr, es, etc.) ou None si incertain
    """
    text_lower = text.lower()
    text_words = text_lower.split()

    # === ENGLISH PATTERNS ===
    # Question words + auxiliaries
    english_indicators = [
        # Question patterns (high weight for certainty) - compiled regex
        (re.compile(r'^is\s+'), 3.0),  # "Is ..." at start (question)
        (re.compile(r'^are\s+'), 3.0),  # "Are ..." at start
        (re.compile(r'^do\s+'), 3.0),  # "Do ..." at start
        (re.compile(r'^does\s+'), 3.0),  # "Does ..." at start
        (re.compile(r'^can\s+'), 3.0),  # "Can ..." at start
        (re.compile(r'^what\s+is\b'), 3.5),  # "What is"
        (re.compile(r'^what\s+are\b'), 3.5),  # "What are"
        (re.compile(r'^how\s+to\b'), 3.5),  # "How to"
        (re.compile(r'^how\s+(can|do)\b'), 3.5),  # "How can", "How do"

        # Mid-sentence patterns
        (re.compile(r'\bis\s+\w+'), 1.5),  # "is safe", "is vaccination"
        (re.compile(r'\bare\s+\w+'), 1.5),  # "are birds"
        (re.compile(r'\bdo\s+\w+'), 1.5),  # "do chickens"

        # Articles + prepositions (literal strings)
        ('the ', 1.5),
        (' a ', 1.5),
        (' an ', 1.5),
        (' of ', 1.0),
        (' for ', 1.0),
        (' with ', 1.0),
        (' safe', 2.0),  # Common English word unlikely in other languages
        (' dangerous', 2.0),
    ]

    # === FRENCH PATTERNS ===
    french_indicators = [
        # Question words (high weight) - using compiled regex for regex patterns
        (re.compile(r'^quel\s+est\b'), 4.0),  # "Quel est"
        (re.compile(r'^quelle\s+est\b'), 4.0),  # "Quelle est"
        (re.compile(r'^quels\s+sont\b'), 4.0),  # "Quels sont"
        (re.compile(r'^quelles\s+sont\b'), 4.0),  # "Quelles sont"
        (re.compile(r'^comment\s+'), 4.0),  # "Comment"
        (re.compile(r'^pourquoi\s+'), 4.0),  # "Pourquoi"
        (re.compile(r'^est-ce\s+que\b'), 4.0),  # "Est-ce que"
        (re.compile(r'^qu\'est-ce\b'), 4.0),  # "Qu'est-ce"

        # Mid-sentence
        (re.compile(r'\best-ce\s+que\b'), 2.5),  # "est-ce que"
        (re.compile(r'\bqu\'est-ce\b'), 2.5),  # "qu'est-ce"
        (re.compile(r'\bquel\s+est\b'), 2.5),  # "quel est"
        (re.compile(r'\bquelle\s+est\b'), 2.5),  # "quelle est"

        # Articles + prepositions (literal strings)
        (' le ', 1.5),
        (' la ', 1.5),
        (' les ', 1.5),
        (' un ', 1.5),
        (' une ', 1.5),
        (' des ', 1.5),
        (' du ', 1.5),
        (' de la ', 2.0),
        (' pour ', 1.0),
        (' avec ', 1.0),
        (" d'un ", 2.0),  # "d'un"
        (" d'une ", 2.0),  # "d'une"
    ]

    # === SPANISH PATTERNS ===
    spanish_indicators = [
        # Question words - compiled regex
        (re.compile(r'^¿?qué\s+es\b'), 3.5),  # "¿Qué es" or "qué es"
        (re.compile(r'^¿?cuál\s+es\b'), 3.5),  # "¿Cuál es"
        (re.compile(r'^¿?cómo\s+'), 3.5),  # "¿Cómo"
        (re.compile(r'^¿?dónde\s+'), 3.5),  # "¿Dónde"
        (re.compile(r'\bqué\s+es\b'), 2.5),  # "qué es" mid-sentence
        (re.compile(r'\bcuál\s+es\b'), 2.5),  # "cuál es" mid-sentence

        # Articles + prepositions (literal strings)
        (' el ', 1.5),
        (' la ', 1.5),
        (' los ', 1.5),
        (' las ', 1.5),
        (' un ', 1.5),
        (' una ', 1.5),
        (' de ', 1.0),
        (' para ', 1.0),
        (' con ', 1.0),
    ]

    # === ITALIAN PATTERNS ===
    italian_indicators = [
        # Question words - compiled regex
        (re.compile(r'^cos\'è\b'), 3.5),  # "Cos'è"
        (re.compile(r'^che\s+cos\'è\b'), 3.5),  # "Che cos'è"
        (re.compile(r'^come\s+'), 3.5),  # "Come"
        (re.compile(r'^qual\s+è\b'), 3.5),  # "Qual è"

        # Mid-sentence
        (re.compile(r'\bcos\'è\b'), 2.5),  # "cos'è"
        (re.compile(r'\bcome\s+'), 1.5),  # "come"

        # Articles + prepositions (literal strings)
        (' il ', 1.5),
        (' la ', 1.5),
        (' gli ', 1.5),
        (' le ', 1.5),
        (' un ', 1.5),
        (' una ', 1.5),
        (' del ', 1.5),
        (' della ', 1.5),
    ]

    # === GERMAN PATTERNS ===
    german_indicators = [
        # Question words - compiled regex
        (re.compile(r'^was\s+ist\b'), 3.5),  # "Was ist"
        (re.compile(r'^wie\s+'), 3.5),  # "Wie"
        (re.compile(r'^warum\s+'), 3.5),  # "Warum"

        # Articles + prepositions (literal strings)
        (' der ', 2.0),
        (' die ', 2.0),
        (' das ', 2.0),
        (' den ', 1.5),
        (' dem ', 1.5),
        (' ein ', 1.5),
        (' eine ', 1.5),
        (' ist ', 1.5),
        (' sind ', 1.5),
    ]

    # === PORTUGUESE PATTERNS ===
    portuguese_indicators = [
        # Question words - compiled regex
        (re.compile(r'^o\s+que\s+é\b'), 3.5),  # "O que é"
        (re.compile(r'^qual\s+é\b'), 3.5),  # "Qual é"
        (re.compile(r'^como\s+'), 3.5),  # "Como"

        # Articles + prepositions (literal strings)
        (' o ', 1.5),
        (' a ', 1.5),
        (' os ', 1.5),
        (' as ', 1.5),
        (' um ', 1.5),
        (' uma ', 1.5),
        (' de ', 1.0),
        (' para ', 1.0),
        (' com ', 1.0),
        (' são ', 2.0),  # "são" (are)
    ]

    # === DUTCH PATTERNS ===
    dutch_indicators = [
        # Question words - compiled regex
        (re.compile(r'^wat\s+is\b'), 3.5),  # "Wat is"
        (re.compile(r'^hoe\s+'), 3.5),  # "Hoe"
        (re.compile(r'^waarom\s+'), 3.5),  # "Waarom"

        # Articles + prepositions (literal strings)
        (' de ', 1.5),
        (' het ', 1.5),
        (' een ', 1.5),
        (' van ', 1.0),
        (' voor ', 1.0),
        (' met ', 1.0),
        (' zijn ', 1.5),
    ]

    # === POLISH PATTERNS ===
    polish_indicators = [
        # Question words - compiled regex
        (re.compile(r'^co\s+to\s+jest\b'), 3.5),  # "Co to jest"
        (re.compile(r'^jak\s+'), 3.5),  # "Jak"
        (re.compile(r'^dlaczego\s+'), 3.5),  # "Dlaczego"

        # Common words (literal strings)
        (' jest ', 2.0),
        (' są ', 2.0),
        (' to ', 1.5),
        (' na ', 1.0),
        (' w ', 1.0),
        (' z ', 1.0),
    ]

    # === INDONESIAN PATTERNS ===
    indonesian_indicators = [
        # Question words - compiled regex
        (re.compile(r'^apa\s+'), 3.5),  # "Apa"
        (re.compile(r'^bagaimana\s+'), 3.5),  # "Bagaimana"
        (re.compile(r'^mengapa\s+'), 3.5),  # "Mengapa"

        # Common words (literal strings)
        (' yang ', 2.0),
        (' adalah ', 2.0),
        (' untuk ', 1.5),
        (' dengan ', 1.5),
        (' dari ', 1.5),
    ]

    # Calculate scores for each language
    scores = {
        'en': 0.0,
        'fr': 0.0,
        'es': 0.0,
        'it': 0.0,
        'de': 0.0,
        'pt': 0.0,
        'nl': 0.0,
        'pl': 0.0,
        'id': 0.0,
        # Note: hi (Hindi), th (Thai), zh (Chinese) use Unicode patterns, not grammar patterns
    }

    # Score English
    for pattern, weight in english_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['en'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['en'] += weight

    # Score French
    for pattern, weight in french_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['fr'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['fr'] += weight

    # Score Spanish
    for pattern, weight in spanish_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['es'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['es'] += weight

    # Score Italian
    for pattern, weight in italian_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['it'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['it'] += weight

    # Score German
    for pattern, weight in german_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['de'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['de'] += weight

    # Score Portuguese
    for pattern, weight in portuguese_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['pt'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['pt'] += weight

    # Score Dutch
    for pattern, weight in dutch_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['nl'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['nl'] += weight

    # Score Polish
    for pattern, weight in polish_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['pl'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['pl'] += weight

    # Score Indonesian
    for pattern, weight in indonesian_indicators:
        if isinstance(pattern, str):
            if pattern in text_lower:
                scores['id'] += weight
        else:  # compiled regex pattern
            if pattern.search(text_lower):
                scores['id'] += weight

    # Find language with highest score
    max_score = max(scores.values())
    if max_score >= 2.0:  # Threshold: need at least score of 2.0
        detected_lang = max(scores, key=scores.get)
        logger.debug(f"Grammar pattern detected: {detected_lang} (score: {max_score:.1f})")
        return detected_lang

    return None


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


def detect_language_enhanced(text: str, default: Optional[str] = None) -> LanguageDetectionResult:
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

    # === LOGIQUE LONGUE ===

    # PRIORITY 1: Grammar-based detection (most reliable for questions with technical terms)
    # This handles cases like "Is in ovo vaccination safe?" where fasttext might
    # incorrectly detect "in ovo" as Italian, ignoring the English grammar
    grammar_lang = _detect_language_by_grammar_patterns(text_clean)
    if grammar_lang:
        return LanguageDetectionResult(
            language=grammar_lang,
            confidence=0.95,  # High confidence for grammar-based detection
            source="grammar_patterns",
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # PRIORITY 2: fasttext-langdetect (fallback for non-grammatical text)
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
