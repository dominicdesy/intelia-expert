#!/usr/bin/env python3
"""
Module de configuration pour le convertisseur Excel vers PostgreSQL
Gère le chargement des variables d'environnement et de intents.json
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Chargement variables d'environnement
try:
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent
    env_paths = [
        project_root / ".env",
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
    ]

    env_loaded = False
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Variables d'environnement chargées depuis: {env_path}")
            env_loaded = True
            break

    if not env_loaded:
        logger.warning("Aucun fichier .env trouvé, utilisation variables système")

except ImportError:
    logger.warning("python-dotenv non installé, utilisation variables système")


# Configuration PostgreSQL
DATABASE_CONFIG = {
    "user": os.getenv("DB_USER", "doadmin"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 25060)),
    "database": os.getenv("DB_NAME", "defaultdb"),
    "ssl": os.getenv("DB_SSL", "require"),
}


def validate_database_config():
    """Valide que les variables d'environnement requises sont présentes"""
    required_vars = ["DB_PASSWORD", "DB_HOST"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Variables d'environnement manquantes: {missing_vars}")
        raise ValueError(f"Variables d'environnement manquantes: {missing_vars}")


class IntentsConfigLoader:
    """Chargeur de configuration intents.json"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Charge la configuration intents.json"""

        # Chemins de recherche pour intents.json - PRIORITÉ: Fichier centralisé
        search_paths = [
            config_path if config_path else None,
            Path(__file__).parent.parent.parent / "llm" / "config" / "intents.json",  # Centralisé
            Path(__file__).parent / "intents.json",  # Fallback local
            Path(__file__).parent.parent / "intents.json",
            "intents.json",
            "../intents.json",
            "./config/intents.json",
            "../config/intents.json",
        ]

        for path in search_paths:
            if not path:
                continue

            try:
                path_obj = Path(path)
                if path_obj.exists():
                    with open(path_obj, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    logger.info(f"Configuration intents chargée depuis: {path_obj}")
                    return config
            except Exception as e:
                logger.debug(f"Erreur chargement {path}: {e}")
                continue

        logger.warning("intents.json non trouvé, utilisation configuration par défaut")
        return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Configuration par défaut si intents.json non trouvé"""
        return {
            "aliases": {
                "line": {
                    "ross 308": ["ross308", "ross-308", "r308", "ross"],
                    "cobb 500": ["cobb500", "cobb-500", "c500", "cobb"],
                    "hy-line brown": ["hyline", "hy-line", "hyline-brown"],
                },
                "metric": {
                    "performance": ["poids", "fcr", "gain", "croissance", "production"],
                    "consumption": ["eau", "aliment", "feed", "water"],
                    "environment": ["température", "humidité", "ventilation"],
                },
                "sex": {
                    "male": ["male", "mâle", "m", "coq", "rooster"],
                    "female": ["female", "femelle", "f", "poule", "hen"],
                    "mixed": ["mixed", "mixte", "as hatched"],
                },
            }
        }

    def get_line_aliases(self) -> Dict[str, List[str]]:
        """Retourne les alias des lignées génétiques"""
        return self.config.get("aliases", {}).get("line", {})

    def get_metric_types(self) -> Dict[str, List[str]]:
        """Retourne les types de métriques"""
        return self.config.get("aliases", {}).get("metric", {})

    def get_sex_aliases(self) -> Dict[str, List[str]]:
        """Retourne les alias de sexe"""
        return self.config.get("aliases", {}).get("sex", {})
