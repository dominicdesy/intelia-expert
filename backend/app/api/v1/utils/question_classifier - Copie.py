# app/api/v1/utils/question_classifier.py
from __future__ import annotations
from typing import Dict, Any

"""
But :
- Exposer REQUIRED_FIELDS_BY_TYPE et classify_question sans ambiguïté
- Rester rétro-compatible avec les imports "from ... import REQUIRED_FIELDS_BY_TYPE"
- Ne jamais lever d'erreur à l'import (filet de sécurité)
"""

# Champs requis (étendus pour nouveaux intents)
REQUIRED_FIELDS_BY_TYPE: Dict[str, list[str]] = {
    "nutrition": ["race", "sexe", "age_jours"],
    "poids_cible": ["race", "sexe", "age_jours"],
    "performance": ["race", "sexe", "age_jours"],
    "sante": ["race", "age_jours", "symptomes"],
    "alimentation": ["race", "age_jours", "type_aliment"],
    "anomaly": ["race", "age_jours", "symptomes"],
    "diagnosis": ["race", "age_jours", "symptomes"],
    # Intents calculs / dimensionnements
    "iep": ["race", "age_jours", "sexe"],
    "costing": ["race", "age_jours"],
    "feeders": ["race", "age_jours"],
    "drinkers": ["race", "age_jours"],
    "tunnel_airflow": ["race", "age_jours"],
    "general": [],
}

def classify_question(question: Any) -> str:
    """
    Heuristiques légères sur texte libre, sinon par présence de champs.
    Filet de sécurité : ne lève jamais d'exception.
    """
    try:
        if not question:
            return "general"

        if isinstance(question, str):
            t = question.lower()

            # Poids cible
            if any(w in t for w in ["poids cible", "target weight", "poids optimal", "poids recommandé"]):
                return "poids_cible"

            # IEP / coût
            if any(w in t for w in ["iep", "epef", "indice europe", "production efficiency"]):
                return "iep"
            if any(w in t for w in ["coût aliment", "cout aliment", "feed cost", "coût/kg vif", "cout/kg vif"]):
                return "costing"

            # Dimensionnement équipements
            if any(w in t for w in ["mangeoire", "mangeoires", "feeder", "feeders", "assiette", "chaîne", "chaine"]):
                return "feeders"
            if any(w in t for w in ["abreuvoir", "abreuvoirs", "nipple", "cloche", "drinkers"]):
                return "drinkers"

            # Débit tunnel / chaleur
            if any(w in t for w in ["tunnel", "débit d'air", "debit d'air", "airflow", "chaleur à extraire", "heat load"]):
                return "tunnel_airflow"

            # Nutrition/croissance générique
            if any(w in t for w in ["poids", "weight", "croissance", "growth", "gain", "kg", "g"]):
                return "nutrition"

            # Santé / alimentation
            if any(w in t for w in ["maladie", "symptôme", "symptom", "infection", "traitement", "vaccin"]):
                return "sante"
            if any(w in t for w in ["aliment", "feed", "starter", "grower", "finisher", "protéine", "energie"]):
                return "alimentation"

            if any(w in t for w in ["diagnostic", "pourquoi", "que faire", "cause"]):
                return "diagnosis"
            if any(w in t for w in ["anomalie", "anormal", "inquiétant", "écart"]):
                return "anomaly"

            return "general"

        if isinstance(question, dict):
            if "type" in question:
                return str(question.get("type") or "general")
            for type_, fields in REQUIRED_FIELDS_BY_TYPE.items():
                if fields and all(f in question for f in fields):
                    return type_
            return "general"

        return "general"
    except Exception:
        return "general"

__all__ = ["REQUIRED_FIELDS_BY_TYPE", "classify_question"]
