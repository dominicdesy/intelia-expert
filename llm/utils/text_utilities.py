# -*- coding: utf-8 -*-
"""
utils/text_utilities.py - Utilitaires de traitement de texte et données
Extrait de utilities.py pour modularisation
"""

import json
import logging
from typing import Any

from utils.data_classes import safe_serialize_for_json

logger = logging.getLogger(__name__)

# ============================================================================
# FONCTIONS UTILITAIRES CORE (MAINTENUES POUR COMPATIBILITÉ)
# ============================================================================


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


def sse_event(obj: dict[str, Any]) -> bytes:
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
