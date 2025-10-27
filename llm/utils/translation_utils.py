# -*- coding: utf-8 -*-
"""
utils/translation_utils.py - Module de traduction et messages multilingues
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
utils/translation_utils.py - Module de traduction et messages multilingues
Extrait de utilities.py pour modularisation
"""

import logging
from typing import Optional
from utils.language_detection import normalize_language_code
from config.config import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    UNIVERSAL_DICT_PATH,
    GOOGLE_TRANSLATE_API_KEY,
    ENABLE_GOOGLE_TRANSLATE_FALLBACK,
    TRANSLATION_CACHE_SIZE,
    TRANSLATION_CACHE_TTL,
    TRANSLATION_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)

# Variable globale pour lazy loading
_translation_service = None

# ============================================================================
# SERVICE DE TRADUCTION (LAZY LOADING)
# ============================================================================


def get_translation_service():
    """Récupère le service de traduction avec lazy loading"""
    global _translation_service

    if _translation_service is None:
        try:
            from utils.translation_service import (
                get_translation_service as _get_service,
                init_global_translation_service,
            )

            # Initialisation si pas encore fait
            _translation_service = _get_service()
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


def get_universal_translation(
    term: str, target_language: str, domain: Optional[str] = None
) -> str:
    """Interface unifiée vers le service de traduction"""
    translation_service = get_translation_service()
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
# MESSAGES MULTILINGUES - MODIFIÉ: UTILISE config/messages.py
# ============================================================================


def get_out_of_domain_message(language: Optional[str] = None) -> str:
    """
    Message hors domaine traduit - UTILISE config/messages.py
    """
    from config.messages import get_message

    if language is None:
        language = DEFAULT_LANGUAGE

    # Normaliser le code de langue
    language = normalize_language_code(language)

    try:
        return get_message("out_of_domain", language)
    except Exception as e:
        logger.warning(f"Erreur récupération message OOD: {e}")

        # Fallback ultra-minimal
        if language == "en":
            return "I specialize in poultry farming. How can I help you?"
        else:
            return "Je me spécialise dans l'aviculture. Comment puis-je vous aider ?"


def get_system_message(message_type: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Interface générique pour récupérer n'importe quel message système

    Args:
        message_type: Type de message (error_generic, welcome, clarification_needed, etc.)
        language: Code langue
        **kwargs: Variables pour interpolation

    Returns:
        Message traduit

    Examples:
        >>> get_system_message("welcome", "en", user_name="John")
        >>> get_system_message("error_generic", "fr")
    """
    from config.messages import get_message

    if language is None:
        language = DEFAULT_LANGUAGE

    language = normalize_language_code(language)

    try:
        return get_message(message_type, language, **kwargs)
    except Exception as e:
        logger.error(f"Erreur récupération message système: {e}")
        return f"[System message: {message_type}]"


def get_aviculture_response(message: str, language: Optional[str] = None) -> str:
    """Génère une réponse aviculture multilingue si le RAG échoue"""
    from utils.language_detection import detect_language_enhanced

    if language is None:
        # Détection automatique de la langue
        detection_result = detect_language_enhanced(message)
        language = detection_result.language

    # Normalisation du message
    message_lower = message.lower()

    # D'abord essayer le service de traduction pour des réponses avancées
    translation_service = get_translation_service()

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

    from config.config import FALLBACK_LANGUAGE

    return general_responses.get(
        language, general_responses.get(FALLBACK_LANGUAGE, general_responses["en"])
    )
