# /backend/app/api/v1/utils/question_classifier.py

from typing import Dict, Any

# Exemples de champs requis par type de question (à adapter selon ton métier)
REQUIRED_FIELDS_BY_TYPE = {
    "performance": ["flock_id", "start_date", "end_date"],
    "anomaly": ["barn_id", "indicator"],
    "diagnosis": ["context", "symptoms"],
    "general": [],
    # ajoute tes propres types selon le cas
}

def classify_question(question: Dict[str, Any]) -> str:
    """
    Tente de classifier la question selon sa structure ou des mots-clés.
    Retourne un type (clé de REQUIRED_FIELDS_BY_TYPE).
    """
    if not question:
        return "general"
    # Si question est un texte brut, on peut faire une heuristique simple
    if isinstance(question, str):
        text = question.lower()
        if "poids" in text or "weight" in text or "croissance" in text:
            return "performance"
        if "anomalie" in text or "alert" in text or "écart" in text:
            return "anomaly"
        if "maladie" in text or "symptom" in text or "diagnostic" in text:
            return "diagnosis"
        return "general"
    # Si c'est un dict (format JSON)
    if isinstance(question, dict):
        # Champ explicite
        if "type" in question:
            return question["type"]
        # On essaie de deviner par présence de champs
        for type_, fields in REQUIRED_FIELDS_BY_TYPE.items():
            if all(f in question for f in fields) and fields:
                return type_
        # Fallback
        return "general"
    # Fallback absolu
    return "general"

