# -*- coding: utf-8 -*-
"""
Intelia Expert — Backend (package init)
Version architecture modulaire - Imports sécurisés
"""

from __future__ import annotations
import logging
import os
from typing import Optional

# Version
__version__ = "2.3.0-modular"


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


def validate_modular_structure() -> bool:
    """Valide que la structure modulaire est correcte."""
    try:
        # Vérification des modules principaux
        required_modules = [
            "config",
            "core",
            "processing",
            "cache",
            "utils",
            "extensions",
        ]

        current_dir = os.path.dirname(__file__)
        for module in required_modules:
            module_path = os.path.join(current_dir, module)
            if not os.path.exists(module_path):
                return False

        return True
    except Exception:
        return False


def get_modular_info() -> dict:
    """Retourne des informations sur la structure modulaire."""
    return {
        "version": __version__,
        "structure": "modular",
        "valid": validate_modular_structure(),
        "modules": {
            "config": "Configuration centralisée",
            "core": "Moteurs RAG et données",
            "processing": "Traitement des requêtes",
            "cache": "Gestion du cache Redis",
            "utils": "Utilitaires partagés",
            "extensions": "Extensions optionnelles",
        },
    }


# IMPORTANT: Architecture modulaire - pas d'imports lourds ici !
# Les imports sont faits directement dans main.py selon les besoins
# Cela évite les imports circulaires et les initialisations prématurées

__all__ = [
    "get_version",
    "setup_logging",
    "load_env",
    "validate_modular_structure",
    "get_modular_info",
]
