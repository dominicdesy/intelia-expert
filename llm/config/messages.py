# -*- coding: utf-8 -*-
"""
messages.py - Gestionnaire centralisé des messages système multilingues
Charge les messages depuis languages.json avec cache et fallbacks
"""

import json
import logging
from utils.types import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache global des messages
_MESSAGES_CACHE: Optional[Dict] = None


def load_messages() -> Dict:
    """
    Charge les messages depuis languages.json (avec cache)
    Retourne un dictionnaire de messages par langue
    """
    global _MESSAGES_CACHE

    if _MESSAGES_CACHE is not None:
        return _MESSAGES_CACHE

    # Chemin du fichier languages.json
    config_dir = Path(__file__).parent
    languages_file = config_dir / "languages.json"

    if not languages_file.exists():
        logger.error(f"Fichier languages.json introuvable: {languages_file}")
        return _get_fallback_messages()

    try:
        with open(languages_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _MESSAGES_CACHE = data
            logger.info(f"Messages chargés: {len(data.get('messages', {}))} langues")
            return data
    except Exception as e:
        logger.error(f"Erreur chargement languages.json: {e}")
        return _get_fallback_messages()


def get_message(message_type: str, language: str = "fr", **kwargs) -> str:
    """
    Récupère un message traduit avec interpolation de variables

    Args:
        message_type: Type de message (out_of_domain, error_generic, welcome, etc.)
        language: Code langue ISO 639-1 (fr, en, es, etc.)
        **kwargs: Variables pour interpolation dans le message

    Returns:
        Message traduit et formaté

    Examples:
        >>> get_message("welcome", "en", user_name="John")
        "Hello John! I'm Intelia Expert..."

        >>> get_message("out_of_domain", "fr")
        "Je me spécialise dans l'aviculture..."
    """
    messages = load_messages()

    # Normaliser le code langue
    lang = _normalize_language_code(language)

    # Vérifier si la langue existe
    if "messages" not in messages or lang not in messages["messages"]:
        logger.warning(f"Langue non trouvée: {lang}, fallback vers 'fr'")
        lang = "fr"

    # Récupérer le message
    lang_messages = messages["messages"].get(lang, {})
    msg = lang_messages.get(message_type, "")

    # Fallback si message manquant
    if not msg and lang != "en":
        logger.warning(
            f"Message '{message_type}' manquant pour {lang}, fallback vers 'en'"
        )
        eng_messages = messages["messages"].get("en", {})
        msg = eng_messages.get(message_type, f"[Missing message: {message_type}]")

    # Interpolation des variables
    if kwargs:
        try:
            msg = msg.format(**kwargs)
        except KeyError as e:
            logger.error(f"Variable manquante dans le message: {e}")

    return msg


def get_all_messages_for_language(language: str) -> Dict[str, str]:
    """
    Retourne tous les messages pour une langue
    Utile pour l'export ou le debugging
    """
    messages = load_messages()
    lang = _normalize_language_code(language)

    return messages.get("messages", {}).get(lang, {})


def reload_messages() -> bool:
    """
    Force le rechargement des messages depuis le disque
    Utile en développement ou après modification du fichier
    """
    global _MESSAGES_CACHE
    _MESSAGES_CACHE = None

    try:
        load_messages()
        logger.info("Messages rechargés avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur rechargement messages: {e}")
        return False


def validate_messages_completeness() -> Dict:
    """
    Valide que tous les types de messages sont présents dans toutes les langues
    Retourne un rapport de validation
    """
    messages = load_messages()
    report = {
        "status": "ok",
        "languages_found": [],
        "missing_messages": {},
        "warnings": [],
    }

    if "messages" not in messages:
        report["status"] = "error"
        report["warnings"].append("Structure 'messages' manquante")
        return report

    # Types de messages attendus
    expected_types = [
        "out_of_domain",
        "error_generic",
        "welcome",
        "clarification_needed",
        "no_results",
        "processing",
        "farewell",
    ]

    all_langs = messages["messages"].keys()
    report["languages_found"] = list(all_langs)

    # Vérifier chaque langue
    for lang in all_langs:
        lang_messages = messages["messages"][lang]
        missing = [
            msg_type for msg_type in expected_types if msg_type not in lang_messages
        ]

        if missing:
            report["missing_messages"][lang] = missing
            report["status"] = "warning"
            report["warnings"].append(f"Langue {lang}: messages manquants {missing}")

    return report


def _normalize_language_code(language: str) -> str:
    """Normalise un code langue (zh-CN -> zh, en-US -> en, etc.)"""
    if not language:
        return "fr"

    # Mapping des codes spéciaux
    mappings = {
        "zh-cn": "zh",
        "zh-tw": "zh",
        "en-us": "en",
        "en-gb": "en",
        "fr-fr": "fr",
        "fr-ca": "fr",
        "es-es": "es",
        "es-mx": "es",
        "pt-br": "pt",
        "pt-pt": "pt",
    }

    lang_lower = language.lower()
    return mappings.get(lang_lower, lang_lower.split("-")[0])


def _get_fallback_messages() -> Dict:
    """Messages de fallback minimalistes si le fichier JSON est absent"""
    return {
        "messages": {
            "fr": {
                "out_of_domain": "Je me spécialise dans l'aviculture. Comment puis-je vous aider ?",
                "error_generic": "Une erreur s'est produite.",
                "welcome": "Bonjour ! Je suis Intelia Expert, spécialisé en aviculture.",
            },
            "en": {
                "out_of_domain": "I specialize in poultry farming. How can I help you?",
                "error_generic": "An error occurred.",
                "welcome": "Hello! I'm Intelia Expert, specialized in poultry farming.",
            },
        }
    }


# ============================================================================
# Export des fonctions publiques
# ============================================================================

__all__ = [
    "load_messages",
    "get_message",
    "get_all_messages_for_language",
    "reload_messages",
    "validate_messages_completeness",
]
