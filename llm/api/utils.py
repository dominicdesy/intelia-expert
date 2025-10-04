"""
Utilitaires communs pour l'API
Ce module contient des fonctions partagées pour éviter les importations circulaires
"""

from typing import Any
from datetime import datetime
from decimal import Decimal


def safe_serialize_for_json(obj: Any) -> Any:
    """
    Sérialise un objet pour le rendre compatible JSON.
    Gère les types datetime, Decimal, bytes, etc.

    Args:
        obj: L'objet à sérialiser

    Returns:
        L'objet sérialisé ou l'objet original si déjà compatible JSON
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode("utf-8", errors="ignore")
    elif isinstance(obj, set):
        return list(obj)
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    return obj
