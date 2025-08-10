# app/api/v1/utils/validation_pipeline.py - VERSION AMÉLIORÉE
from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional
import logging

from .config import MAX_CLARIFICATION_ROUNDS
from .question_classifier import classify_question, REQUIRED_FIELDS_BY_TYPE

# Import avec fallback pour éviter les erreurs circulaires
try:
    from ..pipeline.intent_registry import get_intent_spec, critical_slots
except ImportError:
    def get_intent_spec(name: str) -> Dict[str, Any]:
        return {"required_context": [], "critical_context": []}
    def critical_slots(name: str) -> List[str]:
        return []

logger = logging.getLogger(__name__)

# Configuration de pondération par champ
FIELD_WEIGHTS = {
    # Champs critiques universels
    "species": 3.0,
    "line": 2.5,
    "race": 2.5,
    "breed": 2.5,
    
    # Champs contextuels importants
    "age_days": 2.0,
    "age_jours": 2.0,
    "sex": 1.5,
    "sexe": 1.5,
    
    # Champs spécialisés
    "phase": 1.5,
    "effectif": 1.5,
    "problem_type": 2.5,  # Critique pour diagnostic
    "symptoms": 3.0,      # Critique pour diagnostic
    
    # Champs optionnels
    "temperature": 1.0,
    "housing_type": 1.0,
    "objective": 1.0,
    
    # Valeurs par défaut pour champs non listés
    "default": 1.0
}

# Validation métier avicole
BUSINESS_RULES = {
    "age_consistency": {
        "starter": (0, 15),
        "grower": (10, 30),
        "finisher": (25, 50),
        "laying": (140, 600)  # en jours
    },
    "weight_ranges": {
        "broiler": {
            7: (150, 250),
            14: (350, 500),
            21: (700, 1000),
            28: (1300, 1700),
            35: (2000, 2600),
            42: (2500, 3200)
        },
        "layer": {
            140: (1200, 1600),  # début ponte
            200: (1600, 2000),  # pic ponte
            400: (1800, 2200)   # fin ponte
        }
    },
    "species_breeds": {
        "broiler": ["ross", "cobb", "hubbard"],
        "layer": ["isa", "lohmann", "hy-line", "hyline"]
    }
}

class SmartValidationPipeline:
    """Pipeline de validation intelligent avec scoring pondéré et règles métier"""
    
    def __init__(self):
        self.field_weights = FIELD_WEIGHTS
        self.business_rules = BUSINESS_RULES
    
    def validate_and_score_enhanced(
        self, 
        context: Dict[str, Any], 
        question: str,
        intent: Optional[str] = None,
        intent_confidence: float = 1.0
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Validation et scoring améliorés avec règles métier et adaptation intention
        
        Returns:
            - score: score de complétude 0-1
            - missing: liste des champs manquants
            - diagnostics: détails de validation
        """
        
        # 1. Classification et spécifications
        q_type = intent or classify_question(question)
        intent_spec = get_intent_spec(q_type)
        
        # 2. Champs requis adaptatifs
        required_fields = self._get_adaptive_required_fields(q_type, intent_spec, question)
        critical_fields = set(critical_slots(q_type))
        
        # 3. Validation des champs présents et calcul scores
        validation_results = self._validate_individual_fields(context, required_fields, critical_fields)
        
        # 4. Score pondéré final
        final_score = self._calculate_weighted_score(
            validation_results, required_fields, critical_fields, intent_confidence
        )
        
        # 5. Validation des règles métier
        business_validation = self._validate_business_rules(context)
        
        # 6. Ajustements finaux
        adjusted_score, warnings = self._apply_final_adjustments(
            final_score, business_validation, context, q_type
        )
        
        # 7. Identification champs manquants prioritaires
        missing_fields = self._identify_missing_fields(
            validation_results, required_fields, critical_fields
        )
        
        # 8. Diagnostics complets
        diagnostics = {
            "intent": q_type,
            "intent_confidence": intent_confidence,
            "required_fields": required_fields,
            "critical_fields": list(critical_fields),
            "validation_details": validation_results,
            "business_validation": business_validation,
            "warnings": warnings,
            "field_scores": {f: v["score"] for f, v in validation_results.items()},
            "completeness_breakdown": {
                "base_score": final_score,
                "business_bonus": business_validation.get("bonus", 0),
                "final_score": adjusted_score
            }
        }
        
        logger.debug("📊 Validation: score=%.2f, missing=%d, warnings=%d", 
                    adjusted_score, len(missing_fields), len(warnings))
        
        return adjusted_score, missing_fields, diagnostics
    
    def _get_adaptive_required_fields(
        self, 
        intent: str, 
        intent_spec: Dict[str, Any], 
        question: str
    ) -> List[str]:
        """Détermine les champs requis de manière adaptative"""
        
        # Champs de base depuis intent
        base_required = intent_spec.get("required_context", [])
        
        # Champs depuis classification legacy si pas d'intent spécifique
        if not base_required:
            legacy_type = classify_question(question)
            base_required = REQUIRED_FIELDS_BY_TYPE.get(legacy_type, [])
        
        # Enrichissement adaptatif
        adaptive_fields = set(base_required)
        
        # Ajouter champs universellement utiles
        if not any(f in adaptive_fields for f in ["species", "production_type"]):
            adaptive_fields.add("species")
        
        # Logique selon type d'intention
        if intent.startswith("performance"):
            adaptive_fields.update(["line", "age_days", "sex"])
        elif intent.startswith("diagnosis"):
            adaptive_fields.update(["symptoms", "problem_type", "age_days"])
        elif intent.startswith("nutrition"):
            adaptive_fields.update(["phase", "species"])
        elif intent.startswith("equipment"):
            adaptive_fields.update(["effectif", "age_days"])
        
        # Détection depuis question
        question_lower = question.lower()
        if any(word in question_lower for word in ["poids", "weight", "kg", "gramme"]):
            adaptive_fields.update(["line", "age_days", "sex"])
        if any(word in question_lower for word in ["ponte", "œuf", "egg", "production"]):
            adaptive_fields.update(["line", "age_days"])
        
        return list(adaptive_fields)
    
    def _validate_individual_fields(
        self, 
        context: Dict[str, Any], 
        required_fields: List[str], 
        critical_fields: set
    ) -> Dict[str, Dict[str, Any]]:
        """Valide chaque champ individuellement avec scoring détaillé"""
        
        results = {}
        
        for field in required_fields:
            field_result = {
                "present": False,
                "score": 0.0,
                "quality": "missing",
                "value": None,
                "issues": []
            }
            
            # Vérifier présence
            value = context.get(field)
            if value is not None and str(value).strip():
                field_result["present"] = True
                field_result["value"] = value
                field_result["quality"] = "present"
                
                # Scoring selon qualité
                quality_score = self._assess_field_quality(field, value, context)
                field_result["score"] = quality_score
                
                if quality_score >= 0.8:
                    field_result["quality"] = "high"
                elif quality_score >= 0.6:
                    field_result["quality"] = "medium"
                else:
                    field_result["quality"] = "low"
                    field_result["issues"] = self._identify_field_issues(field, value, context)
            
            results[field] = field_result
        
        return results
    
    def _assess_field_quality(self, field: str, value: Any, context: Dict[str, Any]) -> float:
        """Évalue la qualité d'un champ spécifique"""
        
        if not value:
            return 0.0
        
        score = 1.0  # Score de base pour présence
        
        # Validation spécifique par type de champ
        if field in ["species", "production_type"]:
            if str(value).lower() in ["broiler", "layer", "breeder"]:
                score = 1.0
            elif any(term in str(value).lower() for term in ["poulet", "pondeuse", "chair"]):
                score = 0.8  # Synonyme acceptable
            else:
                score = 0.4  # Valeur ambiguë
        
        elif field in ["line", "race", "breed"]:
            value_lower = str(value).lower()
            known_lines = ["ross", "cobb", "hubbard", "isa", "lohmann", "hy-line"]
            if any(line in value_lower for line in known_lines):
                score = 1.0
            elif len(str(value)) > 2:  # Au moins quelques caractères
                score = 0.6
            else:
                score = 0.3
        
        elif field in ["age_days", "age_jours"]:
            try:
                age = int(value)
                if 0 < age <= 365:  # Plage raisonnable
                    score = 1.0
                elif 0 < age <= 500:  # Plage étendue
                    score = 0.8
                else:
                    score = 0.3
            except (ValueError, TypeError):
                score = 0.2
        
        elif field in ["sex", "sexe"]:
            if str(value).lower() in ["male", "female", "mixed", "mâle", "femelle", "mixte"]:
                score = 1.0
            else:
                score = 0.5
        
        elif field == "effectif":
            try:
                eff = int(value)
                if 10 <= eff <= 1000000:  # Plage raisonnable
                    score = 1.0
                else:
                    score = 0.5
            except (ValueError, TypeError):
                score = 0.3
        
        # Cohérence avec autres champs
        coherence_bonus = self._check_field_coherence(field, value, context)
        score = min(1.0, score + coherence_bonus)
        
        return score
    
    def _check_field_coherence(self, field: str, value: Any, context: Dict[str, Any]) -> float:
        """Vérifie la cohérence d'un champ avec le reste du contexte"""
        
        bonus = 0.0
        
        # Cohérence espèce-lignée
        if field == "species" and "line" in context:
            species = str(value).lower()
            line = str(context["line"]).lower()
            
            broiler_lines = ["ross", "cobb", "hubbard"]
            layer_lines = ["isa", "lohmann", "hy-line"]
            
            if species == "broiler" and any(bl in line for bl in broiler_lines):
                bonus += 0.1
            elif species == "layer" and any(ll in line for ll in layer_lines):
                bonus += 0.1
            elif species in ["broiler", "layer"] and any(bl in line for bl in broiler_lines + layer_lines):
                # Cohérent même si pas parfait
                bonus += 0.05
        
        # Cohérence âge-phase
        if field == "age_days" and "phase" in context:
            try:
                age = int(value)
                phase = str(context["phase"]).lower()
                
                age_ranges = self.business_rules["age_consistency"]
                for phase_name, (min_age, max_age) in age_ranges.items():
                    if phase_name in phase and min_age <= age <= max_age:
                        bonus += 0.1
                        break
            except (ValueError, TypeError):
                pass
        
        return bonus
    
    def _identify_field_issues(self, field: str, value: Any, context: Dict[str, Any]) -> List[str]:
        """Identifie les problèmes spécifiques d'un champ"""
        
        issues = []
        
        if field in ["age_days", "age_jours"]:
            try:
                age = int(value)
                if age <= 0:
                    issues.append("Âge doit être positif")
                elif age > 365:
                    issues.append("Âge semble élevé pour volaille")
            except (ValueError, TypeError):
                issues.append("Âge doit être numérique")
        
        elif field == "effectif":
            try:
                eff = int(value)
                if eff < 10:
                    issues.append("Effectif semble très faible")
                elif eff > 100000:
                    issues.append("Effectif semble très élevé")
            except (ValueError, TypeError):
                issues.append("Effectif doit être numérique")
        
        # Vérifications de cohérence
        if field == "species" and "line" in context:
            species = str(value).lower()
            line = str(context["line"]).lower()
            
            if species == "broiler" and any(term in line for term in ["isa", "lohmann", "hy-line"]):
                issues.append("Lignée de pondeuse avec espèce broiler")
            elif species == "layer" and any(term in line for term in ["ross", "cobb", "hubbard"]):
                issues.append("Lignée de broiler avec espèce pondeuse")
        
        return issues
    
    def _calculate_weighted_score(
        self,
        validation_results: Dict[str, Dict[str, Any]],
        required_fields: List[str],
        critical_fields: set,
        intent_confidence: float
    ) -> float:
        """Calcule le score pondéré final"""
        
        if not required_fields:
            return 1.0
        
        total_weight = 0.0
        achieved_weight = 0.0
        
        for field in required_fields:
            # Déterminer poids du champ
            base_weight = self.field_weights.get(field, self.field_weights["default"])
            
            # Bonus pour champs critiques
            if field in critical_fields:
                weight = base_weight * 1.5
            else:
                weight = base_weight
            
            total_weight += weight
            
            # Score du champ
            field_data = validation_results.get(field, {"score": 0.0})
            field_score = field_data["score"]
            
            achieved_weight += weight * field_score
        
        # Score de base
        base_score = achieved_weight / total_weight if total_weight > 0 else 0.0
        
        # Ajustement selon confiance intention
        confidence_factor = 0.5 + (intent_confidence * 0.5)  # Entre 0.5 et 1.0
        adjusted_score = base_score * confidence_factor
        
        return min(1.0, adjusted_score)
    
    def _validate_business_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Applique les règles métier avicoles"""
        
        validation = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "bonus": 0.0
        }
        
        # Validation âge-phase
        age_days = context.get("age_days") or context.get("age_jours")
        phase = context.get("phase")
        
        if age_days and phase:
            try:
                age = int(age_days)
                phase_lower = str(phase).lower()
                
                for phase_name, (min_age, max_age) in self.business_rules["age_consistency"].items():
                    if phase_name in phase_lower:
                        if min_age <= age <= max_age:
                            validation["bonus"] += 0.05  # Cohérence bonus
                        else:
                            validation["warnings"].append(
                                f"Âge {age}j inhabituel pour phase {phase} (attendu {min_age}-{max_age}j)"
                            )
                        break
            except (ValueError, TypeError):
                pass
        
        # Validation poids-âge
        weight_g = context.get("target_weight_g") or context.get("poids_moyen_g")
        species = context.get("species")
        
        if weight_g and age_days and species:
            try:
                weight = int(weight_g)
                age = int(age_days)
                
                weight_ranges = self.business_rules["weight_ranges"].get(species, {})
                
                # Trouver la plage d'âge la plus proche
                closest_age = min(weight_ranges.keys(), key=lambda x: abs(x - age), default=None)
                
                if closest_age and abs(closest_age - age) <= 7:  # Dans la semaine
                    min_weight, max_weight = weight_ranges[closest_age]
                    if min_weight <= weight <= max_weight:
                        validation["bonus"] += 0.05
                    else:
                        validation["warnings"].append(
                            f"Poids {weight}g à {age}j semble atypique (attendu {min_weight}-{max_weight}g)"
                        )
            except (ValueError, TypeError):
                pass
        
        # Validation espèce-lignée
        species = context.get("species")
        line = context.get("line") or context.get("race") or context.get("breed")
        
        if species and line:
            species_lower = str(species).lower()
            line_lower = str(line).lower()
            
            expected_breeds = self.business_rules["species_breeds"].get(species_lower, [])
            
            if any(breed in line_lower for breed in expected_breeds):
                validation["bonus"] += 0.03
            else:
                # Vérifier incohérence
                other_species = [s for s in self.business_rules["species_breeds"].keys() if s != species_lower]
                for other_sp in other_species:
                    other_breeds = self.business_rules["species_breeds"][other_sp]
                    if any(breed in line_lower for breed in other_breeds):
                        validation["errors"].append(
                            f"Lignée {line} correspond à {other_sp}, pas à {species}"
                        )
                        validation["valid"] = False
                        break
        
        return validation
    
    def _apply_final_adjustments(
        self,
        base_score: float,
        business_validation: Dict[str, Any],
        context: Dict[str, Any],
        intent: str
    ) -> Tuple[float, List[str]]:
        """Applique les ajustements finaux au score"""
        
        adjusted_score = base_score
        warnings = []
        
        # Bonus règles métier
        business_bonus = business_validation.get("bonus", 0.0)
        adjusted_score += business_bonus
        
        # Pénalités pour erreurs métier
        if not business_validation.get("valid", True):
            adjusted_score *= 0.7  # Pénalité 30%
            warnings.extend(business_validation.get("errors", []))
        
        # Warnings métier
        warnings.extend(business_validation.get("warnings", []))
        
        # Bonus contexte riche (beaucoup de champs)
        filled_fields = sum(1 for v in context.values() if v)
        if filled_fields >= 8:
            adjusted_score += 0.05
        
        # Malus pour intentions urgentes non complètes
        try:
            from ..pipeline.intent_registry import is_urgent_intent
            if is_urgent_intent(intent) and adjusted_score < 0.6:
                warnings.append("Information insuffisante pour situation urgente")
        except ImportError:
            pass
        
        return min(1.0, max(0.0, adjusted_score)), warnings
    
    def _identify_missing_fields(
        self,
        validation_results: Dict[str, Dict[str, Any]],
        required_fields: List[str],
        critical_fields: set
    ) -> List[str]:
        """Identifie les champs manquants par ordre de priorité"""
        
        missing = []
        
        # Champs critiques manquants en premier
        for field in critical_fields:
            if field in required_fields:
                field_data = validation_results.get(field, {})
                if not field_data.get("present", False):
                    missing.append(field)
        
        # Autres champs requis
        for field in required_fields:
            if field not in critical_fields:
                field_data = validation_results.get(field, {})
                if not field_data.get("present", False):
                    missing.append(field)
        
        return missing


# Instance globale pour compatibilité
_validator = SmartValidationPipeline()

def validate_and_score(context: Dict[str, Any], question: str) -> Tuple[float, List[str]]:
    """Fonction de compatibilité avec l'ancienne API"""
    score, missing, _ = _validator.validate_and_score_enhanced(context, question)
    return score, missing

def validate_and_score_enhanced(
    context: Dict[str, Any], 
    question: str,
    intent: Optional[str] = None,
    intent_confidence: float = 1.0
) -> Tuple[float, List[str], Dict[str, Any]]:
    """API enrichie avec diagnostics complets"""
    return _validator.validate_and_score_enhanced(context, question, intent, intent_confidence)

def validate_business_rules(context: Dict[str, Any]) -> Dict[str, Any]:
    """Validation des règles métier uniquement"""
    return _validator._validate_business_rules(context)