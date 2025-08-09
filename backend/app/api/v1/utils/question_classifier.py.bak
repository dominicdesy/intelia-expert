# /backend/app/api/v1/utils/question_classifier.py

from typing import Dict, Any

# ✅ CORRECTION MAJEURE: Champs requis adaptés aux questions réelles
REQUIRED_FIELDS_BY_TYPE = {
    "nutrition": ["race", "sexe", "age_jours"],           # ✅ NOUVEAU: Questions de nutrition/croissance
    "poids_cible": ["race", "sexe", "age_jours"],        # ✅ NOUVEAU: Questions de poids cible spécifiques
    "performance": ["race", "sexe", "age_jours"],        # ✅ CORRIGÉ: Champs plus pertinents
    "sante": ["race", "age_jours", "symptomes"],         # ✅ NOUVEAU: Questions de santé
    "alimentation": ["race", "age_jours", "type_aliment"], # ✅ NOUVEAU: Questions d'alimentation
    "anomaly": ["race", "age_jours", "symptomes"],       # ✅ CORRIGÉ: Plus spécifique
    "diagnosis": ["race", "age_jours", "symptomes"],     # ✅ CORRIGÉ: Plus spécifique
    "general": [],                                        # ✅ CONSERVÉ: Pas de champs requis
}

def classify_question(question: Dict[str, Any]) -> str:
    """
    ✅ AMÉLIORATION MAJEURE: Classification plus précise des questions
    Tente de classifier la question selon sa structure ou des mots-clés.
    Retourne un type (clé de REQUIRED_FIELDS_BY_TYPE).
    """
    if not question:
        return "general"
    
    # Si question est un texte brut, on peut faire une heuristique améliorée
    if isinstance(question, str):
        text = question.lower()
        
        # ✅ NOUVEAU: Détection spécifique des questions de poids cible
        if any(word in text for word in ["poids cible", "poids target", "target weight", "poids optimal", "poids recommandé"]):
            return "poids_cible"
        
        # ✅ AMÉLIORATION: Détection nutrition/croissance
        if any(word in text for word in ["poids", "weight", "croissance", "growth", "gain", "gramme", "kg", "taille", "size"]):
            return "nutrition"
        
        # ✅ NOUVEAU: Détection questions de santé
        if any(word in text for word in ["maladie", "malade", "symptôme", "symptom", "infection", "virus", "bactérie", "traitement", "vaccin"]):
            return "sante"
        
        # ✅ NOUVEAU: Détection questions d'alimentation
        if any(word in text for word in ["aliment", "feed", "nourriture", "ration", "starter", "grower", "finisher", "protéine", "energie"]):
            return "alimentation"
        
        # ✅ AMÉLIORATION: Détection anomalies
        if any(word in text for word in ["anomalie", "alert", "écart", "problème", "issue", "anormal", "inquiétant"]):
            return "anomaly"
        
        # ✅ AMÉLIORATION: Détection diagnostic
        if any(word in text for word in ["diagnostic", "diagnose", "identifier", "cause", "pourquoi", "que faire"]):
            return "diagnosis"
        
        # ✅ CONSERVATION: Fallback général
        return "general"
    
    # Si c'est un dict (format JSON)
    if isinstance(question, dict):
        # Champ explicite
        if "type" in question:
            return question["type"]
        
        # ✅ AMÉLIORATION: Essayer de deviner par présence de champs
        for type_, fields in REQUIRED_FIELDS_BY_TYPE.items():
            if all(f in question for f in fields) and fields:
                return type_
        
        # Fallback
        return "general"
    
    # Fallback absolu
    return "general"