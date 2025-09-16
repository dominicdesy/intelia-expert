# -*- coding: utf-8 -*-
"""
Intelia Expert — Backend (package init)
Version minimale pour éviter les imports circulaires
"""

from __future__ import annotations
import logging
import os
from typing import Optional

# Version
__version__ = "2.3.0"

def get_version() -> str:
    """Retourne la version du package."""
    return __version__

def setup_logging(level: int | str = logging.INFO) -> None:
    """Configure un logging simple si rien n'est déjà configuré."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level)
    else:
        root.setLevel(level)

def load_env(env_file: Optional[str] = None) -> None:
    """Charge les variables d'environnement depuis un .env si présent."""
    if env_file is None:
        env_file = os.getenv("ENV_FILE", ".env")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except Exception:
        # Optionnel : pas critique si indisponible
        pass

# IMPORTANT: Pas d'imports des modules lourds ici !
# Les modules sont importés directement par main.py quand nécessaire
# Cela évite les imports circulaires et les initialisations prématurées

__all__ = [
    "get_version", 
    "setup_logging", 
    "load_env"
]