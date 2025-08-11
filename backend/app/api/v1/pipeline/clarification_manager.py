# -*- coding: utf-8 -*-
"""
Computes completeness and returns targeted follow-up questions.

AMÉLIORATIONS MAJEURES:
- Repondération pour PerfTargets (species+line quasi-obligatoires)
- Questions ultra-ciblées (2-3 maximum)
- Priorisation intelligente selon l'intention
- Questions contextuelles adaptées
- Scoring différencié par intention
"""
from typing import Dict, Any, List
from ..utils.question_classifier import Intention, REQUIRED_FIELDS_BY_TYPE

# ===== NOUVEAUX POIDS PAR INTENTION =====
INTENT_FIELD_WEIGHTS = {
    Intention.PerfTargets: {
        "species": 0.4,      # Quasi-obligatoire (40% du score)
        "line": 0.3,         # Quasi-obligatoire (30% du score) 
        "sex": 0.15,         # Important (15% du score)
        "age": 0.15,         # Utile (15% du score)
    },
    Intention.NutritionSpecs: {
        "species": 0.3,
        "phase": 0.3,
        "line": 0.2,
        "age": 0.2,
    },
    Intention.WaterFeedIntake: {
        "species": 0.25,
        "age": 0.25,
        "flock_size": 0.25,
        "line": 0.25,
    },
    Intention.EquipmentSizing: {
        "flock_size": 0.4,
        "species": 0.3,
        "age": 0.2,
        "housing": 0.1,
    },
    Intention.VentilationSizing: {
        "flock_size": 0.3,
        "species": 0.25,
        "age": 0.25,
        "housing": 0.2,
    },
    Intention.EnvSetpoints: {
        "species": 0.3,
        "age": 0.3,
        "phase": 0.25,
        "housing": 0.15,
    },
    Intention.Economics: {
        "flock_size": 0.3,
        "species": 0.25,
        "line": 0.25,
        "phase": 0.2,
    }
}

# ===== SEUILS DE COMPLÉTUDE PAR INTENTION =====
COMPLETENESS_THRESHOLDS = {
    Intention.PerfTargets: 0.85,     # Très strict car species+line critiques
    Intention.NutritionSpecs: 0.80,
    Intention.WaterFeedIntake: 0.75,
    Intention.EquipmentSizing: 0.75,
    Intention.VentilationSizing: 0.75,
    Intention.EnvSetpoints: 0.80,
    Intention.Economics: 0.75,
}

# ===== QUESTIONS CONTEXTUELLES PAR INTENTION =====
CONTEXTUAL_QUESTIONS = {
    Intention.PerfTargets: {
        "species": {
            "question": "Quel type d'oiseau ?",
            "options": ["broiler", "layer"],
            "help": "Pour des objectifs de performance précis"
        },
        "line": {
            "question": "Quelle lignée/souche ?",
            "options": ["Ross 308", "Ross 708", "Cobb 500", "ISA Brown", "Lohmann Brown", "Hy-Line Brown"],
            "help": "Chaque lignée a ses propres courbes de croissance"
        },
        "sex": {
            "question": "Sexe ?",
            "options": ["male", "female", "mixed"],
            "help": "Performances différentes selon le sexe"
        },
        "age": {
            "question": "Âge précis ?",
            "help": "En jours pour broilers, semaines pour pondeuses"
        }
    },
    Intention.NutritionSpecs: {
        "species": {
            "question": "Type d'élevage ?",
            "options": ["broiler", "layer"],
            "help": "Besoins nutritionnels très différents"
        },
        "phase": {
            "question": "Phase d'élevage ?",
            "options": ["starter", "grower", "finisher", "pre-lay", "peak", "post-peak"],
            "help": "Spécifications nutritionnelles évolutives"
        },
        "line": {
            "question": "Lignée ?",
            "options": ["Ross 308", "Ross 708", "Cobb 500", "ISA Brown", "Lohmann Brown"],
            "help": "Recommandations adaptées par souche"
        }
    },
    Intention.WaterFeedIntake: {
        "species": {
            "question": "Type d'oiseau ?",
            "options": ["broiler", "layer"],
            "help": "Consommations très différentes"
        },
        "age": {
            "question": "Âge ?",
            "help": "Consommation évolutive avec l'âge"
        },
        "flock_size": {
            "question": "Effectif du lot ?",
            "help": "Pour dimensionner les systèmes"
        }
    }
}

def compute_completeness(intent: Intention, entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule la complétude avec repondération selon l'intention.
    
    AMÉLIORATIONS:
    - Scoring pondéré par importance des champs selon l'intention
    - Seuils adaptatifs par type de question  
    - Questions ultra-ciblées (max 2-3)
    - Messages d'aide contextuels
    """
    
    # Utiliser les poids spécifiques à l'intention ou fallback classique
    field_weights = INTENT_FIELD_WEIGHTS.get(intent, {})
    required = REQUIRED_FIELDS_BY_TYPE.get(intent, [])
    
    if not field_weights:
        # Fallback: poids égaux pour toutes les intentions non définies
        field_weights = {field.replace("-", "_").replace(" ", "_"): 1.0 for field in required if not field.endswith("?")}
        total_weight = len(field_weights)
        field_weights = {k: v/total_weight for k, v in field_weights.items()}

    def present(field: str) -> bool:
        val = entities.get(field)
        return val is not None and val != ""

    def age_present() -> bool:
        """Vérifie si l'âge est présent sous n'importe quelle forme"""
        return (present("age") or 
                present("age_days") or 
                present("age_jours") or 
                present("age_weeks") or 
                present("age_semaines"))

    # ===== CALCUL DU SCORE PONDÉRÉ =====
    total_possible_weight = 0.0
    achieved_weight = 0.0
    missing_fields = []
    missing_weights = {}  # Pour prioriser les questions

    for field, weight in field_weights.items():
        total_possible_weight += weight
        
        # Normalisation du nom de champ
        norm_field = field.replace("-", "_").replace(" ", "_")
        
        # Vérification spéciale pour l'âge
        if norm_field == "age":
            if age_present():
                achieved_weight += weight
            else:
                missing_fields.append(field)
                missing_weights[field] = weight
        elif "/" in norm_field:
            # Champs alternatifs (ex: "age_days/age_weeks")
            alts = [x.strip() for x in norm_field.split("/")]
            if any(present(a) for a in alts):
                achieved_weight += weight
            else:
                missing_fields.append(field)
                missing_weights[field] = weight
        else:
            if present(norm_field):
                achieved_weight += weight
            else:
                missing_fields.append(field)
                missing_weights[field] = weight

    # Score final pondéré
    completeness_score = achieved_weight / total_possible_weight if total_possible_weight > 0 else 1.0
    
    # ===== GÉNÉRATION DES QUESTIONS ULTRA-CIBLÉES =====
    questions = _generate_targeted_questions(intent, missing_fields, missing_weights, entities)
    
    return {
        "completeness_score": round(completeness_score, 3),
        "missing_fields": missing_fields,
        "follow_up_questions": questions,
        "intent_threshold": COMPLETENESS_THRESHOLDS.get(intent, 0.8),
        "is_complete": completeness_score >= COMPLETENESS_THRESHOLDS.get(intent, 0.8),
        "field_weights": field_weights,  # Pour debugging
        "achieved_weight": round(achieved_weight, 3),
        "total_weight": round(total_possible_weight, 3)
    }

def _generate_targeted_questions(intent: Intention, missing_fields: List[str], 
                                missing_weights: Dict[str, float], entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Génère 2-3 questions ultra-ciblées basées sur l'intention et les poids.
    
    STRATÉGIE:
    1. Prioriser par poids (champs les plus importants d'abord)
    2. Questions contextuelles selon l'intention
    3. Maximum 3 questions pour éviter la surcharge cognitive
    4. Messages d'aide pour expliquer pourquoi c'est important
    """
    
    # Trier les champs manquants par poids (plus important d'abord)
    sorted_missing = sorted(missing_fields, key=lambda f: missing_weights.get(f, 0), reverse=True)
    
    # Obtenir le template de questions pour cette intention
    question_templates = CONTEXTUAL_QUESTIONS.get(intent, {})
    
    questions = []
    max_questions = 2 if intent == Intention.PerfTargets else 3  # PerfTargets = super ciblé
    
    for field in sorted_missing[:max_questions]:
        norm_field = field.replace("-", "_").replace(" ", "_")
        
        # Question contextualisée si disponible
        if norm_field in question_templates:
            template = question_templates[norm_field]
            question_obj = {
                "field": norm_field,
                "question": template["question"],
                "priority": "high" if missing_weights.get(field, 0) > 0.25 else "medium",
                "weight": missing_weights.get(field, 0)
            }
            
            if "options" in template:
                question_obj["options"] = template["options"]
            
            if "help" in template:
                question_obj["help"] = template["help"]
                
        else:
            # Questions génériques de fallback
            question_obj = _generate_generic_question(norm_field, missing_weights.get(field, 0))
        
        questions.append(question_obj)
    
    # ===== POST-PROCESSING INTELLIGENT =====
    questions = _enhance_questions_with_context(questions, intent, entities)
    
    return questions

def _generate_generic_question(field: str, weight: float) -> Dict[str, Any]:
    """Génère une question générique pour les champs non définis dans CONTEXTUAL_QUESTIONS."""
    
    generic_questions = {
        "species": {
            "question": "Type d'élevage ?",
            "options": ["broiler", "layer"],
        },
        "line": {
            "question": "Lignée/souche ?",
            "options": ["Ross 308", "Ross 708", "Cobb 500", "ISA Brown", "Lohmann Brown", "Hy-Line Brown"],
        },
        "sex": {
            "question": "Sexe ?",
            "options": ["male", "female", "mixed"],
        },
        "age": {
            "question": "Âge précis ?",
        },
        "phase": {
            "question": "Phase d'élevage ?",
            "options": ["starter", "grower", "finisher", "pre-lay", "peak", "post-peak"],
        },
        "flock_size": {
            "question": "Effectif du lot ?",
        },
        "housing": {
            "question": "Type de bâtiment ?",
            "options": ["tunnel", "naturally_ventilated", "free_range"],
        },
        "program_type": {
            "question": "Type de programme ?",
            "options": ["vaccination", "lighting", "brooding", "feeding_program"],
        }
    }
    
    base_question = generic_questions.get(field, {"question": f"{field.replace('_', ' ').title()} ?"})
    
    return {
        "field": field,
        "question": base_question["question"],
        "options": base_question.get("options"),
        "priority": "high" if weight > 0.25 else "medium",
        "weight": weight
    }

def _enhance_questions_with_context(questions: List[Dict[str, Any]], intent: Intention, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Améliore les questions avec du contexte intelligent basé sur ce qui est déjà connu.
    
    AMÉLIORATIONS:
    - Messages d'aide adaptatifs
    - Options filtrées selon le contexte
    - Formulation optimisée selon l'intention
    """
    
    enhanced = []
    known_species = entities.get("species")
    known_line = entities.get("line") 
    
    for q in questions:
        field = q["field"]
        enhanced_q = q.copy()
        
        # ===== AMÉLIORATIONS CONTEXTUELLES =====
        
        # Si on connaît l'espèce, adapter les options de lignée
        if field == "line" and known_species:
            if known_species.lower() in ["broiler", "chair"]:
                enhanced_q["options"] = ["Ross 308", "Ross 708", "Cobb 500", "Hubbard"]
                enhanced_q["help"] = "Lignées de poulets de chair disponibles"
            elif known_species.lower() in ["layer", "pondeuse"]:
                enhanced_q["options"] = ["ISA Brown", "Lohmann Brown", "Lohmann White", "Hy-Line Brown", "Hy-Line W-36"]
                enhanced_q["help"] = "Lignées de pondeuses disponibles"
        
        # Adapter la question d'âge selon l'espèce
        if field == "age" and known_species:
            if known_species.lower() in ["broiler", "chair"]:
                enhanced_q["question"] = "Âge en jours ?"
                enhanced_q["help"] = "Ex: 21, 35, 42 jours"
            elif known_species.lower() in ["layer", "pondeuse"]:
                enhanced_q["question"] = "Âge en semaines ?"
                enhanced_q["help"] = "Ex: 20, 40, 60 semaines"
        
        # Messages d'aide spécifiques selon l'intention
        if intent == Intention.PerfTargets:
            if field == "species" and "help" not in enhanced_q:
                enhanced_q["help"] = "Essentiel pour les objectifs de performance précis"
            elif field == "line" and "help" not in enhanced_q:
                enhanced_q["help"] = "Chaque lignée a ses courbes de référence"
        
        elif intent == Intention.NutritionSpecs:
            if field == "phase" and "help" not in enhanced_q:
                enhanced_q["help"] = "Les spécifications nutritionnelles varient par phase"
        
        elif intent == Intention.WaterFeedIntake:
            if field == "flock_size" and "help" not in enhanced_q:
                enhanced_q["help"] = "Pour calculer la consommation totale"
        
        # ===== PRIORITÉ RENFORCÉE POUR CERTAINS CAS =====
        if intent == Intention.PerfTargets and field in ["species", "line"]:
            enhanced_q["priority"] = "critical"
            enhanced_q["required"] = True
        
        enhanced.append(enhanced_q)
    
    return enhanced

# ===== FONCTIONS UTILITAIRES POUR DEBUG ET MONITORING =====

def get_intent_requirements(intent: Intention) -> Dict[str, Any]:
    """Retourne les exigences de complétude pour une intention donnée."""
    return {
        "required_fields": REQUIRED_FIELDS_BY_TYPE.get(intent, []),
        "field_weights": INTENT_FIELD_WEIGHTS.get(intent, {}),
        "completeness_threshold": COMPLETENESS_THRESHOLDS.get(intent, 0.8),
        "max_questions": 2 if intent == Intention.PerfTargets else 3
    }

def analyze_completeness_distribution(intent: Intention, entities: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse détaillée de la distribution de complétude."""
    result = compute_completeness(intent, entities)
    
    field_weights = result.get("field_weights", {})
    analysis = {
        "overall_score": result["completeness_score"],
        "is_above_threshold": result["is_complete"],
        "missing_critical": [],
        "missing_important": [],
        "missing_optional": []
    }
    
    for field in result["missing_fields"]:
        weight = field_weights.get(field, 0)
        if weight >= 0.3:
            analysis["missing_critical"].append(field)
        elif weight >= 0.15:
            analysis["missing_important"].append(field)
        else:
            analysis["missing_optional"].append(field)
    
    return analysis

def test_completeness_scenarios() -> Dict[str, Any]:
    """Test des différents scénarios de complétude pour validation."""
    test_cases = [
        {
            "name": "PerfTargets_Complete",
            "intent": Intention.PerfTargets,
            "entities": {"species": "broiler", "line": "Ross 308", "sex": "male", "age": "35"}
        },
        {
            "name": "PerfTargets_MissingCritical", 
            "intent": Intention.PerfTargets,
            "entities": {"sex": "male", "age": "35"}  # Manque species et line
        },
        {
            "name": "NutritionSpecs_Partial",
            "intent": Intention.NutritionSpecs,
            "entities": {"species": "broiler", "phase": "starter"}
        }
    ]
    
    results = {}
    for test in test_cases:
        result = compute_completeness(test["intent"], test["entities"])
        results[test["name"]] = {
            "score": result["completeness_score"],
            "is_complete": result["is_complete"],
            "questions_count": len(result["follow_up_questions"]),
            "missing_fields": result["missing_fields"]
        }
    
    return results