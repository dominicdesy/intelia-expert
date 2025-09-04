# app/api/v1/utils/context_validator.py - NOUVEAU FICHIER
from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Niveaux de sévérité pour les validations"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationIssue:
    """Issue de validation avec détails"""
    field: str
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None
    corrected_value: Optional[Any] = None

class PoultryContextValidator:
    """
    Validateur de contexte spécialisé pour l'aviculture.
    Applique les règles métier, détecte les incohérences et propose des corrections.
    """
    
    def __init__(self):
        # Règles de validation métier avicole
        self.validation_rules = {
            # Plages d'âges valides par espèce
            "age_ranges": {
                "broiler": (0, 60),      # 0-60 jours pour broilers
                "layer": (0, 600),       # 0-600 jours pour pondeuses (cycle complet)
                "breeder": (0, 450)      # 0-450 jours pour reproducteurs
            },
            
            # Plages de poids par espèce et âge (approximatives)
            "weight_ranges": {
                "broiler": {
                    7: (120, 200),
                    14: (300, 500),
                    21: (600, 1000),
                    28: (1100, 1700),
                    35: (1800, 2600),
                    42: (2400, 3500),
                    49: (3000, 4200)
                },
                "layer": {
                    140: (1200, 1600),  # début ponte (20 sem)
                    280: (1600, 2200),  # pic ponte (40 sem)
                    420: (1800, 2400)   # fin cycle (60 sem)
                }
            },
            
            # Correspondances lignées-espèces
            "breed_species_mapping": {
                "broiler": {
                    "ross": ["ross 308", "ross 500", "ross 708"],
                    "cobb": ["cobb 500", "cobb 700"],
                    "hubbard": ["hubbard ja", "hubbard flex", "hubbard classic"]
                },
                "layer": {
                    "isa": ["isa brown", "isa white"],
                    "lohmann": ["lohmann brown", "lohmann white", "lohmann lsl"],
                    "hy-line": ["hy-line brown", "hy-line white", "hy-line w36"]
                }
            },
            
            # Phases d'élevage par espèce
            "phase_mapping": {
                "broiler": {
                    "starter": (0, 10),
                    "grower": (11, 25),
                    "finisher": (26, 50)
                },
                "layer": {
                    "starter": (0, 42),     # 0-6 sem
                    "grower": (43, 112),    # 6-16 sem
                    "pre_lay": (113, 140),  # 16-20 sem
                    "laying": (141, 600)    # 20+ sem
                }
            },
            
            # Plages FCR typiques
            "fcr_ranges": {
                "broiler": {
                    28: (1.20, 1.60),
                    35: (1.40, 1.80),
                    42: (1.60, 2.00)
                }
            },
            
            # Plages de production pondeuses
            "production_ranges": {
                "layer": {
                    "peak": (85, 95),      # pic de ponte %
                    "average": (70, 85),   # moyenne cycle %
                    "end_cycle": (50, 70)  # fin de cycle %
                }
            }
        }
        
        # Corrections automatiques communes
        self.auto_corrections = {
            "species_normalization": {
                "poulet de chair": "broiler",
                "poulet chair": "broiler", 
                "chair": "broiler",
                "broilers": "broiler",
                "pondeuse": "layer",
                "pondeuses": "layer",
                "poule pondeuse": "layer",
                "reproducteur": "breeder",
                "reproducteurs": "breeder"
            },
            "sex_normalization": {
                "male": "male",
                "mâle": "male",
                "males": "male",
                "mâles": "male",
                "femelle": "female",
                "femelles": "female",
                "females": "female",
                "mixte": "mixed",
                "mix": "mixed"
            },
            "breed_normalization": {
                "ross trois cent huit": "Ross 308",
                "ross 3 0 8": "Ross 308",
                "cobb cinq cents": "Cobb 500",
                "isa brown": "ISA Brown",
                "lohmann brown": "Lohmann Brown"
            }
        }

    def validate_context(
        self,
        context: Dict[str, Any],
        intent: Optional[str] = None,
        strict_mode: bool = False
    ) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
        """
        Valide et corrige un contexte selon les règles métier avicoles
        
        Args:
            context: Contexte à valider
            intent: Intention pour validation ciblée
            strict_mode: Mode strict (plus de validations)
            
        Returns:
            (contexte_corrigé, liste_issues)
        """
        
        corrected_context = dict(context)
        issues = []
        
        # 1. Normalisation automatique
        corrected_context, normalization_issues = self._apply_auto_corrections(corrected_context)
        issues.extend(normalization_issues)
        
        # 2. Validation des champs individuels
        field_issues = self._validate_individual_fields(corrected_context, strict_mode)
        issues.extend(field_issues)
        
        # 3. Validation des cohérences inter-champs
        coherence_issues = self._validate_field_coherence(corrected_context)
        issues.extend(coherence_issues)
        
        # 4. Validation spécifique à l'intention
        if intent:
            intent_issues = self._validate_intent_specific(corrected_context, intent)
            issues.extend(intent_issues)
        
        # 5. Validation des règles métier complexes
        business_issues = self._validate_business_logic(corrected_context)
        issues.extend(business_issues)
        
        # 6. Proposer corrections supplémentaires
        corrected_context, correction_issues = self._apply_smart_corrections(
            corrected_context, issues
        )
        issues.extend(correction_issues)
        
        # Trier par sévérité
        issues.sort(key=lambda x: self._severity_order(x.severity), reverse=True)
        
        logger.debug("🔍 Validation: %d corrections, %d issues", 
                    len([i for i in issues if i.corrected_value]), len(issues))
        
        return corrected_context, issues

    def _apply_auto_corrections(
        self, 
        context: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
        """Applique les corrections automatiques"""
        
        corrected = dict(context)
        issues = []
        
        # Correction espèce
        species = corrected.get("species", "").lower()
        if species in self.auto_corrections["species_normalization"]:
            new_species = self.auto_corrections["species_normalization"][species]
            corrected["species"] = new_species
            issues.append(ValidationIssue(
                field="species",
                severity=ValidationSeverity.INFO,
                message=f"Espèce normalisée: '{species}' → '{new_species}'",
                corrected_value=new_species
            ))
        
        # Correction sexe
        sex = corrected.get("sex", "").lower()
        if sex in self.auto_corrections["sex_normalization"]:
            new_sex = self.auto_corrections["sex_normalization"][sex]
            corrected["sex"] = new_sex
            corrected["sexe"] = new_sex  # Synchroniser
            issues.append(ValidationIssue(
                field="sex",
                severity=ValidationSeverity.INFO,
                message=f"Sexe normalisé: '{sex}' → '{new_sex}'",
                corrected_value=new_sex
            ))
        
        # Correction lignée
        for field in ["line", "race", "breed"]:
            line = corrected.get(field, "").lower()
            if line in self.auto_corrections["breed_normalization"]:
                new_line = self.auto_corrections["breed_normalization"][line]
                corrected[field] = new_line
                issues.append(ValidationIssue(
                    field=field,
                    severity=ValidationSeverity.INFO,
                    message=f"Lignée normalisée: '{line}' → '{new_line}'",
                    corrected_value=new_line
                ))
        
        return corrected, issues

    def _validate_individual_fields(
        self, 
        context: Dict[str, Any], 
        strict_mode: bool
    ) -> List[ValidationIssue]:
        """Valide les champs individuellement"""
        
        issues = []
        
        # Validation âge
        age_days = context.get("age_days") or context.get("age_jours")
        species = context.get("species", "").lower()
        
        if age_days is not None:
            try:
                age = int(age_days)
                if age < 0:
                    issues.append(ValidationIssue(
                        field="age_days",
                        severity=ValidationSeverity.ERROR,
                        message="L'âge ne peut pas être négatif",
                        suggestion="Vérifiez la valeur d'âge saisie"
                    ))
                elif species in self.validation_rules["age_ranges"]:
                    min_age, max_age = self.validation_rules["age_ranges"][species]
                    if age > max_age:
                        issues.append(ValidationIssue(
                            field="age_days",
                            severity=ValidationSeverity.WARNING,
                            message=f"Âge {age}j inhabituel pour {species} (max typique: {max_age}j)",
                            suggestion="Vérifiez l'âge ou l'espèce"
                        ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    field="age_days",
                    severity=ValidationSeverity.ERROR,
                    message="L'âge doit être un nombre entier",
                    suggestion="Saisissez l'âge en jours (nombre entier)"
                ))
        
        # Validation effectif
        effectif = context.get("effectif")
        if effectif is not None:
            try:
                eff = int(effectif)
                if eff <= 0:
                    issues.append(ValidationIssue(
                        field="effectif",
                        severity=ValidationSeverity.ERROR,
                        message="L'effectif doit être positif",
                        suggestion="Vérifiez le nombre d'oiseaux"
                    ))
                elif eff < 10:
                    issues.append(ValidationIssue(
                        field="effectif",
                        severity=ValidationSeverity.WARNING,
                        message="Effectif très faible (< 10 oiseaux)",
                        suggestion="Confirmez si c'est un lot expérimental"
                    ))
                elif eff > 500000:
                    issues.append(ValidationIssue(
                        field="effectif",
                        severity=ValidationSeverity.WARNING,
                        message="Effectif très élevé (> 500k oiseaux)",
                        suggestion="Vérifiez s'il s'agit du total ou d'un bâtiment"
                    ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    field="effectif",
                    severity=ValidationSeverity.ERROR,
                    message="L'effectif doit être un nombre entier",
                    suggestion="Saisissez le nombre d'oiseaux (nombre entier)"
                ))
        
        # Validation FCR
        fcr = context.get("fcr")
        if fcr is not None:
            try:
                fcr_val = float(fcr)
                if fcr_val <= 0:
                    issues.append(ValidationIssue(
                        field="fcr",
                        severity=ValidationSeverity.ERROR,
                        message="Le FCR doit être positif",
                        suggestion="Vérifiez la valeur FCR"
                    ))
                elif fcr_val < 0.8:
                    issues.append(ValidationIssue(
                        field="fcr",
                        severity=ValidationSeverity.WARNING,
                        message="FCR très faible (< 0.8), vérifiez la valeur",
                        suggestion="FCR typique broiler: 1.4-2.0"
                    ))
                elif fcr_val > 5.0:
                    issues.append(ValidationIssue(
                        field="fcr",
                        severity=ValidationSeverity.WARNING,
                        message="FCR très élevé (> 5.0), possible problème",
                        suggestion="Vérifiez s'il y a des problèmes d'élevage"
                    ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    field="fcr",
                    severity=ValidationSeverity.ERROR,
                    message="Le FCR doit être un nombre",
                    suggestion="Format attendu: 1.65 (exemple)"
                ))
        
        return issues

    def _validate_field_coherence(self, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Valide la cohérence entre les champs"""
        
        issues = []
        
        # Cohérence espèce-lignée
        species = context.get("species", "").lower()
        line = (context.get("line") or context.get("race") or context.get("breed", "")).lower()
        
        if species and line:
            species_breeds = self.validation_rules["breed_species_mapping"].get(species, {})
            line_found = False
            
            for breed_family, breed_variants in species_breeds.items():
                if any(variant in line for variant in breed_variants):
                    line_found = True
                    break
            
            if not line_found:
                # Vérifier si lignée correspond à autre espèce
                conflicting_species = None
                for other_species, other_breeds in self.validation_rules["breed_species_mapping"].items():
                    if other_species != species:
                        for breed_family, breed_variants in other_breeds.items():
                            if any(variant in line for variant in breed_variants):
                                conflicting_species = other_species
                                break
                        if conflicting_species:
                            break
                
                if conflicting_species:
                    issues.append(ValidationIssue(
                        field="species",
                        severity=ValidationSeverity.ERROR,
                        message=f"Incohérence: lignée '{line}' correspond à {conflicting_species}, pas {species}",
                        suggestion=f"Corriger l'espèce en '{conflicting_species}' ou vérifier la lignée",
                        corrected_value=conflicting_species
                    ))
                else:
                    issues.append(ValidationIssue(
                        field="line",
                        severity=ValidationSeverity.WARNING,
                        message=f"Lignée '{line}' non reconnue pour {species}",
                        suggestion="Vérifiez l'orthographe de la lignée"
                    ))
        
        # Cohérence âge-phase
        age_days = context.get("age_days") or context.get("age_jours")
        phase = context.get("phase", "").lower()
        
        if age_days and phase and species:
            try:
                age = int(age_days)
                phase_mapping = self.validation_rules["phase_mapping"].get(species, {})
                
                if phase in phase_mapping:
                    min_age, max_age = phase_mapping[phase]
                    if not (min_age <= age <= max_age):
                        issues.append(ValidationIssue(
                            field="phase",
                            severity=ValidationSeverity.WARNING,
                            message=f"Âge {age}j inhabituel pour phase '{phase}' (attendu {min_age}-{max_age}j)",
                            suggestion="Vérifiez l'âge ou la phase d'élevage"
                        ))
            except (ValueError, TypeError):
                pass
        
        # Cohérence poids-âge-espèce
        weight_g = context.get("target_weight_g") or context.get("poids_moyen_g")
        
        if weight_g and age_days and species:
            try:
                weight = int(weight_g)
                age = int(age_days)
                
                weight_ranges = self.validation_rules["weight_ranges"].get(species, {})
                
                # Trouver l'âge de référence le plus proche
                if weight_ranges:
                    closest_age = min(weight_ranges.keys(), key=lambda x: abs(x - age))
                    if abs(closest_age - age) <= 7:  # Dans la semaine
                        min_weight, max_weight = weight_ranges[closest_age]
                        if not (min_weight <= weight <= max_weight):
                            issues.append(ValidationIssue(
                                field="weight",
                                severity=ValidationSeverity.WARNING,
                                message=f"Poids {weight}g à {age}j inhabituel pour {species} (attendu {min_weight}-{max_weight}g)",
                                suggestion="Vérifiez le poids, l'âge ou les conditions d'élevage"
                            ))
            except (ValueError, TypeError):
                pass
        
        return issues

    def _validate_intent_specific(self, context: Dict[str, Any], intent: str) -> List[ValidationIssue]:
        """Validation spécifique selon l'intention"""
        
        issues = []
        
        # Validation pour intentions de diagnostic
        if "diagnosis" in intent:
            if not any(field in context for field in ["symptoms", "problem_type", "problem_description"]):
                issues.append(ValidationIssue(
                    field="symptoms",
                    severity=ValidationSeverity.WARNING,
                    message="Aucun symptôme spécifié pour diagnostic",
                    suggestion="Précisez les symptômes observés"
                ))
        
        # Validation pour intentions de performance
        elif "performance" in intent:
            critical_fields = ["species", "line", "age_days"]
            missing_critical = [f for f in critical_fields if not context.get(f)]
            
            if len(missing_critical) > 1:
                issues.append(ValidationIssue(
                    field="context",
                    severity=ValidationSeverity.WARNING,
                    message=f"Informations manquantes pour performance: {', '.join(missing_critical)}",
                    suggestion="Ces informations sont critiques pour des recommandations précises"
                ))
        
        # Validation pour intentions nutritionnelles
        elif "nutrition" in intent:
            if not context.get("phase") and not context.get("age_days"):
                issues.append(ValidationIssue(
                    field="phase",
                    severity=ValidationSeverity.WARNING,
                    message="Phase d'élevage non spécifiée pour nutrition",
                    suggestion="Précisez la phase: starter, grower, finisher, etc."
                ))
        
        return issues

    def _validate_business_logic(self, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validation des règles métier complexes"""
        
        issues = []
        
        # Validation FCR selon âge et espèce
        fcr = context.get("fcr")
        age_days = context.get("age_days") or context.get("age_jours")
        species = context.get("species", "").lower()
        
        if fcr and age_days and species == "broiler":
            try:
                fcr_val = float(fcr)
                age = int(age_days)
                
                fcr_ranges = self.validation_rules["fcr_ranges"]["broiler"]
                closest_age = min(fcr_ranges.keys(), key=lambda x: abs(x - age))
                
                if abs(closest_age - age) <= 7:  # Dans la semaine
                    min_fcr, max_fcr = fcr_ranges[closest_age]
                    if fcr_val < min_fcr:
                        issues.append(ValidationIssue(
                            field="fcr",
                            severity=ValidationSeverity.INFO,
                            message=f"FCR {fcr_val} excellent pour {age}j (< {min_fcr})",
                            suggestion="Performance exceptionnelle"
                        ))
                    elif fcr_val > max_fcr:
                        issues.append(ValidationIssue(
                            field="fcr",
                            severity=ValidationSeverity.WARNING,
                            message=f"FCR {fcr_val} élevé pour {age}j (> {max_fcr})",
                            suggestion="Analyser les causes: aliment, santé, environnement"
                        ))
            except (ValueError, TypeError):
                pass
        
        # Validation production pondeuses
        production_rate = context.get("production_rate_pct")
        if production_rate and species == "layer":
            try:
                prod = float(production_rate)
                if prod > 100:
                    issues.append(ValidationIssue(
                        field="production_rate_pct",
                        severity=ValidationSeverity.ERROR,
                        message="Le taux de ponte ne peut pas dépasser 100%",
                        suggestion="Vérifiez le calcul du taux de ponte"
                    ))
                elif prod < 30:
                    issues.append(ValidationIssue(
                        field="production_rate_pct", 
                        severity=ValidationSeverity.WARNING,
                        message="Taux de ponte très faible (< 30%)",
                        suggestion="Vérifiez s'il y a des problèmes sanitaires ou nutritionnels"
                    ))
            except (ValueError, TypeError):
                pass
        
        return issues

    def _apply_smart_corrections(
        self, 
        context: Dict[str, Any], 
        existing_issues: List[ValidationIssue]
    ) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
        """Applique des corrections intelligentes basées sur les issues détectées"""
        
        corrected = dict(context)
        new_issues = []
        
        # Correction espèce basée sur lignée si incohérence
        for issue in existing_issues:
            if issue.field == "species" and issue.corrected_value and issue.severity == ValidationSeverity.ERROR:
                if "Incohérence: lignée" in issue.message:
                    corrected["species"] = issue.corrected_value
                    new_issues.append(ValidationIssue(
                        field="species",
                        severity=ValidationSeverity.INFO,
                        message=f"Espèce corrigée automatiquement: {issue.corrected_value}",
                        suggestion="Correction basée sur la lignée spécifiée"
                    ))
        
        # Déduction phase depuis âge si manquante
        if not corrected.get("phase") and corrected.get("age_days"):
            try:
                age = int(corrected["age_days"])
                species = corrected.get("species", "").lower()
                
                if species in self.validation_rules["phase_mapping"]:
                    phase_mapping = self.validation_rules["phase_mapping"][species]
                    for phase_name, (min_age, max_age) in phase_mapping.items():
                        if min_age <= age <= max_age:
                            corrected["phase"] = phase_name
                            new_issues.append(ValidationIssue(
                                field="phase",
                                severity=ValidationSeverity.INFO,
                                message=f"Phase déduite: {phase_name} (basée sur âge {age}j)",
                                corrected_value=phase_name
                            ))
                            break
            except (ValueError, TypeError):
                pass
        
        return corrected, new_issues

    def _severity_order(self, severity: ValidationSeverity) -> int:
        """Ordre de priorité des sévérités"""
        order = {
            ValidationSeverity.CRITICAL: 4,
            ValidationSeverity.ERROR: 3,
            ValidationSeverity.WARNING: 2,
            ValidationSeverity.INFO: 1
        }
        return order.get(severity, 0)

    def get_validation_summary(self, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Résumé des issues de validation"""
        
        summary = {
            "total_issues": len(issues),
            "by_severity": {},
            "corrected_fields": [],
            "critical_issues": [],
            "suggestions": []
        }
        
        # Compter par sévérité
        for severity in ValidationSeverity:
            count = len([i for i in issues if i.severity == severity])
            if count > 0:
                summary["by_severity"][severity.value] = count
        
        # Champs corrigés
        summary["corrected_fields"] = [i.field for i in issues if i.corrected_value is not None]
        
        # Issues critiques
        summary["critical_issues"] = [
            {"field": i.field, "message": i.message} 
            for i in issues 
            if i.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
        ]
        
        # Suggestions uniques
        suggestions = set()
        for issue in issues:
            if issue.suggestion:
                suggestions.add(issue.suggestion)
        summary["suggestions"] = list(suggestions)[:5]  # Limiter à 5
        
        return summary

# Instance globale
_validator = PoultryContextValidator()

def validate_poultry_context(
    context: Dict[str, Any],
    intent: Optional[str] = None,
    strict_mode: bool = False
) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
    """Interface publique pour validation de contexte avicole"""
    return _validator.validate_context(context, intent, strict_mode)

def get_validation_summary(issues: List[ValidationIssue]) -> Dict[str, Any]:
    """Obtient un résumé des issues de validation"""
    return _validator.get_validation_summary(issues)

def check_field_coherence(context: Dict[str, Any]) -> List[ValidationIssue]:
    """Vérifie uniquement la cohérence des champs"""
    return _validator._validate_field_coherence(context)
