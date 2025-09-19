# -*- coding: utf-8 -*-
"""
utilities.py - Fonctions utilitaires multilingues
Version 2.1 avec CORRECTION SÉRIALISATION JSON pour LanguageDetectionResult
CORRECTION CRITIQUE: Sérialisation dataclass + validate_intent_result manquant
"""

import os
import re
import time
import json
import logging
import statistics
import dataclasses
from collections import defaultdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Imports configuration multilingue
from config.config import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    FALLBACK_LANGUAGE,
    LANG_DETECTION_MIN_LENGTH,
    LANG_DETECTION_CONFIDENCE_THRESHOLD,
    FASTTEXT_MODEL_PATH,
    # SUPPRIMÉ: FRENCH_HINTS, ENGLISH_HINTS, FRENCH_CHARS (remplacé par service traduction)
)

# Import service traduction (lazy loading)
_translation_service = None

# Import FastText (remplace langdetect)
try:
    import fasttext

    FASTTEXT_AVAILABLE = True
    _fasttext_model = None
    logger = logging.getLogger(__name__)
    logger.info("FastText disponible pour détection multilingue")
except ImportError:
    FASTTEXT_AVAILABLE = False
    fasttext = None
    # Fallback vers fast-langdetect si disponible
    try:
        from fastlangdetect import detect, LangDetectException

        FAST_LANGDETECT_AVAILABLE = True
        logger = logging.getLogger(__name__)
        logger.info("fast-langdetect disponible comme fallback")
    except ImportError:
        FAST_LANGDETECT_AVAILABLE = False
        detect = None
        LangDetectException = Exception

# Import conditionnel unidecode
try:
    from unidecode import unidecode

    UNIDECODE_AVAILABLE = True
except ImportError:
    UNIDECODE_AVAILABLE = False
    unidecode = None

logger = logging.getLogger(__name__)

# ============================================================================
# CLASSES DE DONNÉES - VERSION CORRIGÉE AVEC SÉRIALISATION JSON
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


@dataclass
class ValidationReport:
    """Rapport de validation détaillé - CORRIGÉ pour sérialisation JSON"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> dict:
        """Conversion en dictionnaire pour sérialisation JSON"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
            "recommendations": self.recommendations,
        }

    def __hash__(self):
        """Rendre hashable pour utilisation comme clé de cache"""
        return hash(
            (
                self.is_valid,
                tuple(self.errors),
                tuple(self.warnings),
                tuple(self.recommendations),
                # Ne pas inclure stats car peut contenir des types non-hashable
            )
        )


@dataclass
class ProcessingResult:
    """Résultat de traitement d'une requête - CORRIGÉ pour sérialisation JSON"""

    success: bool
    result: Optional[Any] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """Conversion en dictionnaire pour sérialisation JSON"""
        return {
            "success": self.success,
            "result": safe_serialize_for_json(self.result),
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
        }

    def __hash__(self):
        """Rendre hashable pour utilisation comme clé de cache"""
        return hash(
            (
                self.success,
                self.error_message,
                self.processing_time,
                # Ne pas inclure result et metadata car peuvent contenir des types non-hashable
            )
        )


# ============================================================================
# FONCTION DE SÉRIALISATION CORRIGÉE - SUPPORT DATACLASSES
# ============================================================================


def safe_serialize_for_json(obj: Any) -> Any:
    """Convertit récursivement les objets en types JSON-safe avec support dataclasses"""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, Enum):
        return obj.value
    elif dataclasses.is_dataclass(obj):
        # CORRECTION PRINCIPALE: Support spécifique pour les dataclasses
        if hasattr(obj, "to_dict"):
            # Utiliser la méthode to_dict si disponible
            return obj.to_dict()
        else:
            # Fallback vers conversion directe des champs
            return {
                field.name: safe_serialize_for_json(getattr(obj, field.name))
                for field in dataclasses.fields(obj)
            }
    elif isinstance(obj, dict):
        return {k: safe_serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [safe_serialize_for_json(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return safe_serialize_for_json(obj.__dict__)
    else:
        return str(obj)


# ============================================================================
# SERVICE DE TRADUCTION (LAZY LOADING)
# ============================================================================


def _get_translation_service():
    """Récupère le service de traduction avec lazy loading"""
    global _translation_service

    if _translation_service is None:
        try:
            from utils.translation_service import (
                get_translation_service,
                init_global_translation_service,
            )
            from config.config import (
                UNIVERSAL_DICT_PATH,
                GOOGLE_TRANSLATE_API_KEY,
                ENABLE_GOOGLE_TRANSLATE_FALLBACK,
                TRANSLATION_CACHE_SIZE,
                TRANSLATION_CACHE_TTL,
                TRANSLATION_CONFIDENCE_THRESHOLD,
            )

            # Initialisation si pas encore fait
            _translation_service = get_translation_service()
            if _translation_service is None:
                _translation_service = init_global_translation_service(
                    dict_path=UNIVERSAL_DICT_PATH,
                    supported_languages=SUPPORTED_LANGUAGES,
                    google_api_key=GOOGLE_TRANSLATE_API_KEY,
                    enable_google_fallback=ENABLE_GOOGLE_TRANSLATE_FALLBACK,
                    cache_size=TRANSLATION_CACHE_SIZE,
                    cache_ttl=TRANSLATION_CACHE_TTL,
                    confidence_threshold=TRANSLATION_CONFIDENCE_THRESHOLD,
                )

        except Exception as e:
            logger.warning(f"Service de traduction indisponible: {e}")
            _translation_service = None

    return _translation_service


# ============================================================================
# CORRECTION CRITIQUE: FONCTION MANQUANTE
# ============================================================================


def validate_intent_result(intent_result) -> bool:
    """
    Valide qu'un résultat d'intention est conforme aux attentes

    Args:
        intent_result: Résultat d'une classification d'intention

    Returns:
        bool: True si valide, False sinon
    """
    if intent_result is None:
        return False

    # Validation basique de la structure
    try:
        # Vérifier attributs requis
        required_attrs = ["intent_type", "confidence", "detected_entities"]

        for attr in required_attrs:
            if not hasattr(intent_result, attr):
                logger.debug(f"Attribut manquant dans intent_result: {attr}")
                return False

        # Validation de la confiance
        if not (0.0 <= intent_result.confidence <= 1.0):
            logger.debug(f"Confiance invalide: {intent_result.confidence}")
            return False

        # Validation du type d'intention
        if intent_result.intent_type is None:
            logger.debug("Type d'intention null")
            return False

        # Validation des entités (doit être une liste)
        if not isinstance(intent_result.detected_entities, list):
            logger.debug("detected_entities n'est pas une liste")
            return False

        return True

    except Exception as e:
        logger.debug(f"Erreur validation intent_result: {e}")
        return False


# ============================================================================
# DÉTECTION DE LANGUE MULTILINGUE (REMPLACE detect_language_enhanced)
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
    translation_service = _get_translation_service()
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


def get_universal_translation(
    term: str, target_language: str, domain: str = None
) -> str:
    """Interface unifiée vers le service de traduction"""
    translation_service = _get_translation_service()
    if not translation_service:
        return term

    try:
        result = translation_service.translate_term(
            term, target_language, domain=domain
        )
        return result.text if result.confidence >= 0.5 else term
    except Exception as e:
        logger.debug(f"Erreur traduction universelle {term}->{target_language}: {e}")
        return term


# ============================================================================
# FONCTIONS UTILITAIRES MULTILINGUES
# ============================================================================


def get_out_of_domain_message(language: str = None) -> str:
    """Message hors domaine traduit selon la langue détectée"""

    if language is None:
        language = DEFAULT_LANGUAGE

    # D'abord essayer le service de traduction
    translation_service = _get_translation_service()
    if translation_service:
        try:
            # Récupérer depuis le dictionnaire universel
            result = translation_service.translate_term(
                "out_of_domain_message", language, domain="system_messages"
            )
            if result.confidence >= 0.7:
                return result.text
        except Exception as e:
            logger.debug(f"Erreur service traduction pour message OOD: {e}")

    # Messages par défaut intégrés (fallback)
    default_messages = {
        "fr": "Je me spécialise dans l'aviculture et l'élevage de volailles. Je peux vous aider avec: Performance (FCR, poids, croissance), Nutrition (programmes alimentaires), Environnement (température, ventilation), Santé (prévention, vaccination), et Gestion technique. Posez-moi une question spécifique!",
        "en": "I specialize in poultry farming and broiler production. I can help with: Performance (FCR, weight, growth), Nutrition (feeding programs), Environment (temperature, ventilation), Health (prevention, vaccination), and Technical management. Ask me a specific question!",
        "es": "Me especializo en avicultura y producción de pollos. Puedo ayudar con: Rendimiento (FCR, peso, crecimiento), Nutrición (programas de alimentación), Ambiente (temperatura, ventilación), Salud (prevención, vacunación), y Gestión técnica. ¡Hágame una pregunta específica!",
        "de": "Ich spezialisiere mich auf Geflügelzucht und Hähnchenmast. Ich kann helfen bei: Leistung (FCR, Gewicht, Wachstum), Ernährung (Fütterungsprogramme), Umgebung (Temperatur, Lüftung), Gesundheit (Vorbeugung, Impfung), und Technisches Management. Stellen Sie mir eine spezifische Frage!",
        "it": "Mi specializzo in avicoltura e produzione di polli. Posso aiutare con: Prestazioni (FCR, peso, crescita), Nutrizione (programmi alimentari), Ambiente (temperatura, ventilazione), Salute (prevenzione, vaccinazione), e Gestione tecnica. Fatemi una domanda specifica!",
        "pt": "Especializo-me na avicultura e produção de frangos. Posso ajudar com: Desempenho (FCR, peso, crescimento), Nutrição (programas alimentares), Ambiente (temperatura, ventilação), Saúde (prevenção, vacinação), e Gestão técnica. Faça-me uma pergunta específica!",
        "nl": "Ik specialiseer me in pluimveehouderij en vleeskuikenproductie. Ik kan helpen met: Prestaties (FCR, gewicht, groei), Voeding (voerprogramma's), Omgeving (temperatuur, ventilatie), Gezondheid (preventie, vaccinatie), en Technisch beheer. Stel me een specifieke vraag!",
        "pl": "Specjalizuję się w hodowli drobiu i produkcji kurcząt. Mogę pomóc z: Wydajność (FCR, waga, wzrost), Żywienie (programy żywieniowe), Środowisko (temperatura, wentylacja), Zdrowie (profilaktyka, szczepienia), i Zarządzanie techniczne. Zadaj mi konkretne pytanie!",
        "hi": "मैं मुर्गीपालन और ब्रॉयलर उत्पादन में विशेषज्ञता रखता हूं। मैं इनमें मदद कर सकता हूं: प्रदर्शन (FCR, वजन, वृद्धि), पोषण (आहार कार्यक्रम), पर्यावरण (तापमान, वेंटिलेशन), स्वास्थ्य (रोकथाम, टीकाकरण), और तकनीकी प्रबंधन। मुझसे कोई विशिष्ट प्रश्न पूछें!",
        "zh": "我专门从事家禽养殖和肉鸡生产。我可以帮助: 性能 (FCR, 体重, 生长), 营养 (饲养计划), 环境 (温度, 通风), 健康 (预防, 疫苗接种), 和技术管理。请问我一个具体问题！",
        "th": "ฉันเชี่ยวชาญด้านการเลี้ยงสัตว์ปีกและการผลิตไก่เนื้อ ฉันสามารถช่วยได้ในเรื่อง: ประสิทธิภาพ (FCR, น้ำหนัก, การเจริญเติบโต), โภชนาการ (โปรแกรมการให้อาหาร), สิ่งแวดล้อม (อุณหภูมิ, การระบายอากาศ), สุขภาพ (การป้องกัน, การฉีดวัคซีน), และการจัดการทางเทคนิค กรุณาถามคำถามเฉพาะเจาะจง!",
        "id": "Saya ahli dalam budidaya unggas dan produksi ayam pedaging. Saya dapat membantu dengan: Performa (FCR, berat, pertumbuhan), Nutrisi (program pakan), Lingkungan (suhu, ventilasi), Kesehatan (pencegahan, vaksinasi), dan Manajemen teknis. Ajukan pertanyaan spesifik kepada saya!",
    }

    return default_messages.get(
        language, default_messages.get(FALLBACK_LANGUAGE, default_messages["en"])
    )


def get_aviculture_response(message: str, language: str = None) -> str:
    """Génère une réponse aviculture multilingue si le RAG échoue"""

    if language is None:
        # Détection automatique de la langue
        detection_result = detect_language_enhanced(message)
        language = detection_result.language

    # Normalisation du message
    message_lower = message.lower()

    # D'abord essayer le service de traduction pour des réponses avancées
    translation_service = _get_translation_service()

    # Détection du sujet principal
    topic = None
    if any(term in message_lower for term in ["fcr", "conversion", "indice"]):
        topic = "fcr_information"
    elif any(
        term in message_lower for term in ["poids", "weight", "croissance", "growth"]
    ):
        topic = "weight_curves"
    elif any(
        term in message_lower
        for term in ["température", "temperature", "ventilation", "climat"]
    ):
        topic = "temperature_program"
    elif any(
        term in message_lower for term in ["mortalité", "mortality", "santé", "health"]
    ):
        topic = "mortality_targets"
    elif any(
        term in message_lower
        for term in ["alimentation", "nutrition", "aliment", "feed"]
    ):
        topic = "feeding_program"
    else:
        topic = "general_poultry_help"

    # Essayer de récupérer la réponse traduite
    if translation_service and topic:
        try:
            result = translation_service.translate_term(
                topic, language, domain="aviculture_responses"
            )
            if result.confidence >= 0.6:
                return result.text
        except Exception as e:
            logger.debug(f"Erreur service traduction pour réponse aviculture: {e}")

    # Fallback vers réponses hardcodées multilingues
    if any(term in message_lower for term in ["fcr", "conversion", "indice"]):
        responses = {
            "fr": """L'indice de conversion alimentaire (FCR) optimal varie selon l'âge et la souche :

- **Poulets de chair Ross 308** :
  - 0-21 jours : FCR cible 1.2-1.3
  - 22-35 jours : FCR cible 1.4-1.6  
  - 36-42 jours : FCR cible 1.7-1.9

- **Facteurs influençant le FCR** :
  - Qualité de l'aliment et formulation
  - Température et ventilation du bâtiment
  - Densité d'élevage
  - Santé du troupeau
  - Gestion de l'abreuvement

Pour optimiser le FCR, surveillez la consommation quotidienne et ajustez la distribution selon les courbes de croissance standards.""",
            "en": """Feed Conversion Ratio (FCR) targets vary by age and strain:

- **Ross 308 Broilers**:
  - 0-21 days: FCR target 1.2-1.3
  - 22-35 days: FCR target 1.4-1.6
  - 36-42 days: FCR target 1.7-1.9

- **FCR Influencing Factors**:
  - Feed quality and formulation
  - House temperature and ventilation
  - Stocking density
  - Flock health status
  - Water management

To optimize FCR, monitor daily consumption and adjust distribution according to standard growth curves.""",
            "es": """Los objetivos de Conversión Alimenticia (FCR) varían según edad y cepa:

- **Pollos de engorde Ross 308**:
  - 0-21 días: FCR objetivo 1.2-1.3
  - 22-35 días: FCR objetivo 1.4-1.6
  - 36-42 días: FCR objetivo 1.7-1.9

- **Factores que influyen en FCR**:
  - Calidad y formulación del alimento
  - Temperatura y ventilación del galpón
  - Densidad de población
  - Estado de salud del lote
  - Manejo del agua

Para optimizar FCR, monitoree el consumo diario y ajuste la distribución según curvas de crecimiento estándar.""",
        }
        return responses.get(language, responses.get("en", responses["fr"]))

    # Réponse générale multilingue
    general_responses = {
        "fr": """Je suis spécialisé dans l'aviculture et l'élevage de poulets de chair. Je peux vous aider sur :

- **Performances** : FCR, poids, croissance, mortalité
- **Nutrition** : Programmes alimentaires, formulation
- **Environnement** : Température, ventilation, densité
- **Santé** : Prévention, vaccination, biosécurité
- **Technique** : Équipements, bâtiments, gestion

Posez-moi une question précise sur l'un de ces domaines !""",
        "en": """I specialize in poultry farming and broiler production. I can help with:

- **Performance**: FCR, weight, growth, mortality
- **Nutrition**: Feeding programs, formulation
- **Environment**: Temperature, ventilation, density
- **Health**: Prevention, vaccination, biosecurity
- **Technical**: Equipment, housing, management

Ask me a specific question about any of these areas!""",
        "es": """Me especializo en avicultura y producción de pollos de engorde. Puedo ayudar con:

- **Rendimiento**: FCR, peso, crecimiento, mortalidad
- **Nutrición**: Programas alimentarios, formulación
- **Ambiente**: Temperatura, ventilación, densidad
- **Salud**: Prevención, vacunación, bioseguridad
- **Técnico**: Equipos, alojamiento, gestión

¡Hágame una pregunta específica sobre cualquiera de estas áreas!""",
    }

    return general_responses.get(
        language, general_responses.get(FALLBACK_LANGUAGE, general_responses["en"])
    )


# ============================================================================
# FONCTIONS UTILITAIRES CORE (MAINTENUES POUR COMPATIBILITÉ)
# ============================================================================


class MetricsCollector:
    """Collecteur de métriques enrichi avec statistiques intent et cache sémantique"""

    def __init__(self):
        self.counters = defaultdict(int)
        self.last_100_lat = []
        self.cache_stats = defaultdict(int)
        self.search_stats = defaultdict(int)
        self.intent_stats = defaultdict(int)
        self.semantic_cache_stats = defaultdict(int)
        self.ood_stats = defaultdict(int)
        self.api_corrections = defaultdict(int)

    def inc(self, key: str, n: int = 1):
        self.counters[key] += n

    def observe_latency(self, sec: float):
        self.last_100_lat.append(sec)
        if len(self.last_100_lat) > 100:
            self.last_100_lat = self.last_100_lat[-100:]

    def cache_hit(self, cache_type: str):
        self.cache_stats[f"{cache_type}_hits"] += 1

    def cache_miss(self, cache_type: str):
        self.cache_stats[f"{cache_type}_misses"] += 1

    def intent_detected(self, intent_type: str, confidence: float):
        self.intent_stats[f"intent_{intent_type}"] += 1
        self.intent_stats["total_intents"] += 1
        self.intent_stats["avg_confidence"] = (
            self.intent_stats.get("avg_confidence", 0.0)
            * (self.intent_stats["total_intents"] - 1)
            + confidence
        ) / self.intent_stats["total_intents"]

    def semantic_cache_hit(self, cache_type: str):
        self.semantic_cache_stats[f"semantic_{cache_type}_hits"] += 1

    def semantic_fallback_used(self):
        self.semantic_cache_stats["fallback_hits"] += 1

    def ood_filtered(self, score: float, reason: str):
        """Enregistre un filtrage OOD avec détails"""
        self.ood_stats[f"ood_{reason}"] += 1
        self.ood_stats["ood_total"] += 1

        if isinstance(score, (int, float)):
            score_value = float(score)
        else:
            score_value = 0.5

        current_avg = self.ood_stats.get("avg_ood_score", 0.0)
        total_filtered = self.ood_stats["ood_total"]

        if total_filtered > 0:
            self.ood_stats["avg_ood_score"] = (
                current_avg * (total_filtered - 1) + score_value
            ) / total_filtered
        else:
            self.ood_stats["avg_ood_score"] = score_value

    def ood_accepted(self, score: float, reason: str = "accepted"):
        """Trace les requêtes acceptées après validation OOD"""
        self.ood_stats[f"ood_{reason}"] += 1
        self.ood_stats["ood_accepted_total"] += 1

        current_avg = self.ood_stats.get("avg_accepted_score", 0.0)
        total_accepted = self.ood_stats["ood_accepted_total"]
        if total_accepted > 0:
            self.ood_stats["avg_accepted_score"] = (
                current_avg * (total_accepted - 1) + score
            ) / total_accepted

    def hybrid_search_completed(
        self, results_count: int, alpha: float, duration: float, intent_type: str = None
    ):
        """Trace les recherches hybrides complétées"""
        self.search_stats["hybrid_searches"] += 1
        self.search_stats["total_results"] += results_count
        self.search_stats["total_duration"] += duration

        if intent_type:
            self.search_stats[f"intent_{intent_type}_searches"] += 1

        searches = self.search_stats["hybrid_searches"]
        if searches > 0:
            self.search_stats["avg_results_per_search"] = (
                self.search_stats["total_results"] / searches
            )
            self.search_stats["avg_duration_per_search"] = (
                self.search_stats["total_duration"] / searches
            )

    def retrieval_error(self, error_type: str, error_msg: str):
        """Trace les erreurs de récupération"""
        self.search_stats[f"error_{error_type}"] += 1
        self.search_stats["total_errors"] += 1

    def api_correction_applied(self, correction_type: str):
        self.api_corrections[correction_type] += 1

    def snapshot(self):
        p50 = statistics.median(self.last_100_lat) if self.last_100_lat else 0.0
        p95 = (
            sorted(self.last_100_lat)[int(0.95 * len(self.last_100_lat)) - 1]
            if len(self.last_100_lat) >= 20
            else p50
        )
        return {
            "counters": dict(self.counters),
            "cache_stats": dict(self.cache_stats),
            "search_stats": dict(self.search_stats),
            "intent_stats": dict(self.intent_stats),
            "semantic_cache_stats": dict(self.semantic_cache_stats),
            "ood_stats": dict(self.ood_stats),
            "api_corrections": dict(self.api_corrections),
            "p50_latency_sec": round(p50, 3),
            "p95_latency_sec": round(p95, 3),
            "samples": len(self.last_100_lat),
        }

    def as_json(self) -> dict:
        """Export JSON des métriques pour l'app"""
        return {
            "cache": self.cache_stats,
            "ood": self.ood_stats,
            "guardrails": self.api_corrections,
        }


# Instance globale
METRICS = MetricsCollector()


def get_all_metrics_json(
    metrics_instance: MetricsCollector, extra: dict = None
) -> dict:
    """Fonction d'export JSON consolidée des métriques avec données supplémentaires"""
    data = metrics_instance.as_json()
    if extra:
        data.update(extra)
    return data


def build_where_filter(intent_result) -> Dict:
    """Construire where filter par entités"""
    if not intent_result or not hasattr(intent_result, "detected_entities"):
        return None

    entities = intent_result.detected_entities
    where_conditions = []

    if "line" in entities:
        where_conditions.append(
            {
                "path": ["geneticLine"],
                "operator": "Like",
                "valueText": f"*{entities['line']}*",
            }
        )

    if "species" in entities:
        where_conditions.append(
            {
                "path": ["species"],
                "operator": "Like",
                "valueText": f"*{entities['species']}*",
            }
        )

    if "phase" in entities:
        where_conditions.append(
            {
                "path": ["phase"],
                "operator": "Like",
                "valueText": f"*{entities['phase']}*",
            }
        )

    if "age_days" in entities:
        age_days = entities["age_days"]
        if isinstance(age_days, (int, float)):
            if age_days <= 7:
                age_band = "0-7j"
            elif age_days <= 21:
                age_band = "8-21j"
            elif age_days <= 35:
                age_band = "22-35j"
            else:
                age_band = "36j+"

            where_conditions.append(
                {"path": ["age_band"], "operator": "Equal", "valueText": age_band}
            )

    if not where_conditions:
        return None

    if len(where_conditions) == 1:
        return where_conditions[0]
    else:
        return {"operator": "And", "operands": where_conditions}


# Autres fonctions utilitaires maintenues
def safe_get_attribute(obj: Any, attr: str, default: Any = None) -> Any:
    """Récupération sécurisée d'attributs avec validation de type"""
    try:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        elif hasattr(obj, attr):
            return getattr(obj, attr, default)
        else:
            return default
    except Exception as e:
        logger.debug(f"Erreur récupération attribut {attr}: {e}")
        return default


def safe_dict_get(obj: Any, key: str, default: Any = None) -> Any:
    """Version sécurisée de dict.get()"""
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        else:
            logger.debug(
                f"Tentative d'appel .get() sur type {type(obj)}: {str(obj)[:100]}"
            )
            return default
    except Exception as e:
        logger.debug(f"Erreur safe_dict_get pour {key}: {e}")
        return default


def sse_event(obj: Dict[str, Any]) -> bytes:
    """Formatage SSE avec gestion d'erreurs robuste"""
    try:
        safe_obj = safe_serialize_for_json(obj)
        data = json.dumps(safe_obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        error_obj = {"type": "error", "message": "Erreur formatage données"}
        data = json.dumps(error_obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")


def smart_chunk_text(text: str, max_chunk_size: int = None) -> list:
    """Découpe intelligente du texte avec validation"""
    if not isinstance(text, str):
        return []

    max_chunk_size = max_chunk_size or 400
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []

    try:
        chunks = []
        remaining_text = text

        while remaining_text:
            if len(remaining_text) <= max_chunk_size:
                chunks.append(remaining_text)
                break

            cut_point = max_chunk_size

            # Préférer les points après ponctuation
            for i in range(max_chunk_size, max(max_chunk_size // 2, 0), -1):
                if i < len(remaining_text) and remaining_text[i] in ".!?:":
                    cut_point = i + 1
                    break

            # Sinon, couper sur un espace
            if cut_point == max_chunk_size:
                for i in range(max_chunk_size, max(max_chunk_size // 2, 0), -1):
                    if i < len(remaining_text) and remaining_text[i] == " ":
                        cut_point = i
                        break

            chunks.append(remaining_text[:cut_point])
            remaining_text = remaining_text[cut_point:].lstrip()

        return chunks

    except Exception as e:
        logger.error(f"Erreur découpe texte: {e}")
        return [text[:max_chunk_size]] if text else []


def setup_logging(level: str = "INFO") -> None:
    """Configure le logging pour l'application"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            (
                logging.FileHandler("app.log")
                if os.getenv("LOG_TO_FILE")
                else logging.NullHandler()
            ),
        ],
    )


# Fonctions de processus d'intention (à maintenir pour compatibilité)
class IntentProcessorFactory:
    """Factory robuste pour créer des processeurs d'intentions"""

    @staticmethod
    def create_processor(
        intents_file_path: Optional[str] = None, validate_on_creation: bool = True
    ):
        try:
            from processing.intent_processor import IntentProcessor
        except ImportError as e:
            raise RuntimeError(f"Module intent_processor non disponible: {e}")

        if intents_file_path is None:
            base_dir = Path(__file__).parent.resolve()
            intents_file_path = base_dir.parent / "config" / "intents.json"

        processor = IntentProcessor(str(intents_file_path))
        if validate_on_creation:
            validation_result = processor.validate_current_config()
            if not validation_result.is_valid:
                raise ValueError(f"Configuration invalide: {validation_result.errors}")

        return processor


def create_intent_processor(intents_file_path: Optional[str] = None):
    """Factory principale pour créer un processeur d'intentions"""
    return IntentProcessorFactory.create_processor(
        intents_file_path, validate_on_creation=True
    )


def process_query_with_intents(
    processor, query: str, explain_score: Optional[float] = None, timeout: float = 5.0
) -> ProcessingResult:
    """Traite une requête avec le processeur d'intentions"""
    start_time = time.time()

    if not processor:
        return ProcessingResult(
            success=False, error_message="Processeur non fourni", processing_time=0.0
        )

    if not query or not query.strip():
        return ProcessingResult(
            success=False, error_message="Requête vide ou invalide", processing_time=0.0
        )

    try:
        result = processor.process_query(query.strip(), explain_score)
        processing_time = time.time() - start_time

        if not result:
            return ProcessingResult(
                success=False,
                error_message="Aucun résultat retourné par le processeur",
                processing_time=processing_time,
            )

        return ProcessingResult(
            success=True,
            result=result,
            processing_time=processing_time,
            metadata={
                "query_length": len(query),
                "entities_detected": len(result.detected_entities),
                "intent_type": (
                    result.intent_type.value
                    if hasattr(result.intent_type, "value")
                    else str(result.intent_type)
                ),
                "confidence_level": (
                    "high"
                    if result.confidence > 0.8
                    else "medium" if result.confidence > 0.5 else "low"
                ),
            },
        )

    except Exception as e:
        logger.error(f"Erreur traitement requête '{query[:50]}...': {e}")
        return ProcessingResult(
            success=False,
            error_message=f"Erreur de traitement: {str(e)}",
            processing_time=time.time() - start_time,
            metadata={"exception_type": type(e).__name__},
        )


def validate_intents_config(
    config_path: str, strict_mode: bool = True
) -> ValidationReport:
    """Valide rigoureusement un fichier de configuration intents.json"""
    errors = []
    warnings = []
    recommendations = []
    stats = {}

    try:
        config_file = Path(config_path)
        if not config_file.exists():
            return ValidationReport(
                is_valid=False,
                errors=[f"Fichier non trouvé: {config_path}"],
                warnings=[],
                stats={},
                recommendations=["Vérifiez le chemin du fichier de configuration"],
            )

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Validation basique
        required_sections = ["aliases", "intents", "universal_slots"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Section manquante: {section}")
            elif not isinstance(config[section], dict):
                errors.append(f"Section {section} doit être un dictionnaire")

        stats.update(
            {
                "file_size_bytes": config_file.stat().st_size,
                "validation_timestamp": time.time(),
                "strict_mode": strict_mode,
            }
        )

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
            recommendations=recommendations,
        )

    except Exception as e:
        return ValidationReport(
            is_valid=False,
            errors=[f"Erreur validation inattendue: {e}"],
            warnings=[],
            stats={},
            recommendations=["Contactez le support technique"],
        )


# Données de test
COMPREHENSIVE_TEST_QUERIES = [
    "Quel est le poids cible à 21 jours pour du Ross 308?",
    "FCR optimal pour poulet de chair Cobb 500 à 35 jours",
    "What is the optimal FCR for Ross 308 at 35 days?",
    "¿Cuál es el peso objetivo a 21 días para Ross 308?",
    "Ross 308在35天时的最佳FCR是多少？",
    "Ross 308 के लिए 35 दिन में अनुकूल FCR क्या है?",
    "อัตราแปลงอาหารที่เหมาะสมสำหรับ Ross 308 อายุ 35 วันคืออะไร?",
]

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Classes de données multilingues - NOUVEAU
    "LanguageDetectionResult",
    "ValidationReport",
    "ProcessingResult",
    # Détection langue multilingue - REMPLACÉ
    "detect_language_enhanced",
    # Support langues - NOUVEAU
    "is_supported_language",
    "normalize_language_code",
    "get_universal_translation",
    # Messages multilingues - ÉTENDU
    "get_out_of_domain_message",
    "get_aviculture_response",
    # CORRECTION CRITIQUE: Ajout fonction manquante
    "validate_intent_result",
    # Métriques - MAINTENU
    "METRICS",
    "MetricsCollector",
    "get_all_metrics_json",
    # Weaviate - MAINTENU
    "build_where_filter",
    # Intent processing - MAINTENU
    "create_intent_processor",
    "process_query_with_intents",
    "validate_intents_config",
    "IntentProcessorFactory",
    # Utilitaires - MAINTENU
    "safe_serialize_for_json",
    "safe_get_attribute",
    "safe_dict_get",
    "sse_event",
    "smart_chunk_text",
    "setup_logging",
    # Données test - ÉTENDU
    "COMPREHENSIVE_TEST_QUERIES",
]
