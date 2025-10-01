# -*- coding: utf-8 -*-
"""
validation_core.py - Validation centralisée
Remplace: data_availability_checker + query_validator + partie de rag_postgresql_validator
Version 2.2 - Correction _validate_age pour gérer types mixtes (int/str/float)
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from utils.breeds_registry import get_breeds_registry

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Statuts de validation possibles"""

    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    MISSING_DATA = "missing_data"
    PARTIAL_VALID = "partial_valid"


class ValidationSeverity(Enum):
    """Niveaux de sévérité des problèmes"""

    CRITICAL = "critical"  # Bloque l'exécution
    ERROR = "error"  # Erreur mais peut continuer
    WARNING = "warning"  # Avertissement simple
    INFO = "info"  # Information


@dataclass
class ValidationIssue:
    """Un problème de validation"""

    field: str
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "field": self.field,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Résultat complet de validation"""

    status: ValidationStatus
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)

    # Métadonnées
    confidence: float = 1.0
    allow_partial: bool = False
    missing_fields: List[str] = field(default_factory=list)
    validated_fields: List[str] = field(default_factory=list)

    # Alternatives proposées
    alternatives: Dict[str, List[Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "allow_partial": self.allow_partial,
            "missing_fields": self.missing_fields,
            "alternatives": self.alternatives,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def add_issue(
        self,
        field: str,
        severity: ValidationSeverity,
        message: str,
        suggestion: Optional[str] = None,
    ):
        """Ajoute un problème de validation"""
        issue = ValidationIssue(field, severity, message, suggestion)
        self.issues.append(issue)

        if (
            severity == ValidationSeverity.CRITICAL
            or severity == ValidationSeverity.ERROR
        ):
            self.errors.append(message)
        elif severity == ValidationSeverity.WARNING:
            self.warnings.append(message)

        if suggestion:
            self.suggestions.append(suggestion)


class ValidationCore:
    """
    Validateur central pour toutes les données avicoles

    Remplace:
    - data_availability_checker.py (validation disponibilité données)
    - query_validator.py (validation requêtes)
    - Partie validation de rag_postgresql_validator.py

    Version 2.2: Correction _validate_age pour gérer int/str/float
    """

    # ========================================================================
    # CONFIGURATION CENTRALISÉE - SEXES
    # ========================================================================

    VALID_SEXES = {
        "male": ["mâle", "male", "coq", "masculin"],
        "female": ["femelle", "female", "poule", "féminin"],
        "mixed": ["mixte", "mixed", "as hatched", "as_hatched"],
        "as_hatched": ["as hatched", "as_hatched", "non sexé"],
    }

    # ========================================================================
    # CONFIGURATION CENTRALISÉE - MÉTRIQUES
    # ========================================================================

    VALID_METRICS = {
        "body_weight": {
            "aliases": ["poids", "weight", "poids vif", "body weight", "masse"],
            "unit": "g",
            "typical_range": (0, 5000),
        },
        "feed_conversion_ratio": {
            "aliases": [
                "fcr",
                "ic",
                "indice de consommation",
                "conversion alimentaire",
            ],
            "unit": "",
            "typical_range": (1.0, 3.0),
        },
        "daily_gain": {
            "aliases": ["gain quotidien", "daily gain", "gmq", "croissance", "gain"],
            "unit": "g/j",
            "typical_range": (0, 100),
        },
        "feed_intake": {
            "aliases": ["consommation", "feed intake", "aliment consommé", "ingéré"],
            "unit": "g",
            "typical_range": (0, 10000),
        },
        "mortality": {
            "aliases": ["mortalité", "mortality", "mort", "décès", "pertes"],
            "unit": "%",
            "typical_range": (0, 100),
        },
        "livability": {
            "aliases": ["viabilité", "livability", "survie"],
            "unit": "%",
            "typical_range": (0, 100),
        },
        "production": {
            "aliases": ["production", "ponte", "laying", "œufs", "eggs"],
            "unit": "%",
            "typical_range": (0, 100),
        },
    }

    # ========================================================================
    # PLAGES D'ÂGES CRITIQUES
    # ========================================================================

    CRITICAL_AGE_RANGES = {
        "starter": (0, 10),
        "grower": (11, 24),
        "finisher": (25, 42),
        "extended": (43, 60),
    }

    def __init__(self, strict_mode: bool = False):
        """
        Initialise le validateur

        Args:
            strict_mode: Si True, erreurs au lieu de warnings pour problèmes mineurs
        """
        self.strict_mode = strict_mode

        # Charger le registre des races de manière dynamique
        self.breeds_registry = get_breeds_registry()

        logger.info(
            f"ValidationCore initialisé (strict_mode={strict_mode}, "
            f"breeds_registry chargé avec {len(self.breeds_registry.get_all_breeds())} races)"
        )

    def validate_entities(
        self,
        entities: Dict[str, Any],
        required_fields: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Validation complète des entités

        Args:
            entities: Dict avec breed, age_days, sex, metric_type, etc.
            required_fields: Liste de champs requis (optionnel)

        Returns:
            ValidationResult avec statut, erreurs, warnings, suggestions
        """
        result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
        )

        # Vérification champs requis
        if required_fields:
            for field in required_fields:
                if field not in entities or entities[field] is None:
                    result.missing_fields.append(field)
                    result.add_issue(
                        field=field,
                        severity=ValidationSeverity.ERROR,
                        message=f"Champ requis manquant: {field}",
                        suggestion=f"Veuillez spécifier {field} dans votre requête",
                    )

        # Validation BREED
        if "breed" in entities and entities["breed"]:
            breed_validation = self._validate_breed(entities["breed"])
            self._merge_validation_results(result, breed_validation, "breed")
            result.validated_fields.append("breed")

        # Validation AGE
        if "age_days" in entities and entities["age_days"] is not None:
            age_validation = self._validate_age(
                entities["age_days"], entities.get("breed")
            )
            self._merge_validation_results(result, age_validation, "age_days")
            result.validated_fields.append("age_days")

        # Validation SEX
        if "sex" in entities and entities["sex"]:
            sex_validation = self._validate_sex(entities["sex"])
            self._merge_validation_results(result, sex_validation, "sex")
            result.validated_fields.append("sex")

        # Validation METRIC
        if "metric_type" in entities and entities["metric_type"]:
            metric_validation = self._validate_metric(entities["metric_type"])
            self._merge_validation_results(result, metric_validation, "metric_type")
            result.validated_fields.append("metric_type")

        # Déterminer statut final
        result.status, result.is_valid = self._determine_final_status(result)

        # Calculer confiance
        result.confidence = self._calculate_confidence(result, entities)

        # Déterminer si traitement partiel autorisé
        result.allow_partial = len(result.errors) == 0 or (
            len(result.validated_fields) >= 2 and not self.strict_mode
        )

        logger.debug(
            f"Validation: {result.status.value}, "
            f"{len(result.errors)} erreurs, "
            f"{len(result.warnings)} warnings"
        )

        return result

    def _validate_breed(self, breed: str) -> Dict[str, Any]:
        """
        Valide la souche en utilisant le breeds_registry

        Returns:
            Dict avec 'issues', 'alternatives'
        """
        issues = []
        alternatives = []

        # Recherche via le registry - UTILISE LA NOUVELLE MÉTHODE get_breed()
        breed_info = self.breeds_registry.get_breed(breed)

        if breed_info:
            # Race trouvée directement
            logger.debug(
                f"Breed validé: '{breed}' → {breed_info['breed_id']} ({breed_info['species']})"
            )
            return {"issues": [], "alternatives": []}

        # Race non trouvée - suggérer des alternatives
        # Utiliser validate_breed pour vérifier l'existence
        is_valid, canonical = self.breeds_registry.validate_breed(breed)

        if is_valid and canonical:
            # La race existe mais sous un autre nom
            issues.append(
                ValidationIssue(
                    field="breed",
                    severity=ValidationSeverity.INFO,
                    message=f"Souche '{breed}' reconnue comme '{canonical}'",
                )
            )
            return {"issues": issues, "alternatives": []}

        # Race vraiment inconnue - proposer des alternatives
        # Récupérer quelques races similaires ou populaires
        all_breeds = self.breeds_registry.get_all_breeds()

        if all_breeds:
            # Proposer les 5 premières races comme alternatives
            breed_list = list(all_breeds)[:5]
            alternatives = breed_list

            issues.append(
                ValidationIssue(
                    field="breed",
                    severity=ValidationSeverity.ERROR,
                    message=f"Souche inconnue: '{breed}'",
                    suggestion=f"Souches disponibles: {', '.join(breed_list)}...",
                )
            )
        else:
            issues.append(
                ValidationIssue(
                    field="breed",
                    severity=ValidationSeverity.ERROR,
                    message=f"Souche inconnue: '{breed}' et aucune alternative disponible",
                )
            )

        return {"issues": issues, "alternatives": alternatives}

    def _validate_age(self, age: Any, breed: Optional[str] = None) -> Dict[str, Any]:
        """
        Valide l'âge avec contexte de souche en utilisant le breeds_registry
        
        ✅ FIX v2.2: Accepte int, str, ou float et convertit automatiquement
        
        Args:
            age: Âge en jours (peut être int, str, ou float)
            breed: Race optionnelle pour validation contextuelle
        
        Returns:
            Dict avec 'issues', 'alternatives'
        """
        issues = []
        alternatives = []
        
        # ✅ NOUVEAU: Conversion automatique du type
        try:
            if isinstance(age, str):
                age = int(age)
            elif isinstance(age, float):
                age = int(age)
            elif not isinstance(age, int):
                issues.append(
                    ValidationIssue(
                        field="age_days",
                        severity=ValidationSeverity.ERROR,
                        message=f"Type d'âge invalide: {type(age).__name__}",
                        suggestion="L'âge doit être un nombre entier",
                    )
                )
                return {"issues": issues, "alternatives": []}
        except (ValueError, TypeError) as e:
            issues.append(
                ValidationIssue(
                    field="age_days",
                    severity=ValidationSeverity.ERROR,
                    message=f"Impossible de convertir l'âge en entier: {age} ({e})",
                    suggestion="L'âge doit être un nombre valide",
                )
            )
            return {"issues": issues, "alternatives": []}

        # Validation basique (maintenant age est garanti int)
        if age < 0:
            issues.append(
                ValidationIssue(
                    field="age_days",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Âge négatif: {age}",
                    suggestion="L'âge doit être positif",
                )
            )
            return {"issues": issues, "alternatives": []}

        if age > 100:
            issues.append(
                ValidationIssue(
                    field="age_days",
                    severity=ValidationSeverity.WARNING,
                    message=f"Âge inhabituel: {age} jours",
                    suggestion="La plupart des données concernent 0-60 jours",
                )
            )

        # Validation avec contexte breed via registry
        if breed:
            breed_info = self.breeds_registry.get_breed(breed)

            if breed_info:
                # Déterminer les plages d'âge typiques selon l'espèce
                species = breed_info.get("species", "")
                breed_name = breed_info.get("name", breed)

                # Plages par défaut selon l'espèce
                if species == "broiler":
                    min_age, max_age = 0, 60
                elif species == "layer":
                    min_age, max_age = 0, 80
                elif species == "breeder":
                    min_age, max_age = 0, 65
                else:
                    min_age, max_age = 0, 60

                if age < min_age:
                    issues.append(
                        ValidationIssue(
                            field="age_days",
                            severity=ValidationSeverity.WARNING,
                            message=f"Âge {age}j inférieur à la plage typique pour {breed_name} ({min_age}-{max_age}j)",
                            suggestion=f"Les données pour {breed_name} commencent généralement à {min_age}j",
                        )
                    )
                    alternatives = list(range(min_age, min(min_age + 10, max_age)))

                elif age > max_age:
                    issues.append(
                        ValidationIssue(
                            field="age_days",
                            severity=ValidationSeverity.WARNING,
                            message=f"Âge {age}j supérieur à la plage typique pour {breed_name} ({min_age}-{max_age}j)",
                            suggestion=f"Les données pour {breed_name} vont généralement jusqu'à {max_age}j",
                        )
                    )
                    alternatives = list(range(max(min_age, max_age - 10), max_age + 1))

        # Identifier la phase
        phase = self._identify_phase(age)
        if phase:
            issues.append(
                ValidationIssue(
                    field="age_days",
                    severity=ValidationSeverity.INFO,
                    message=f"Âge {age}j correspond à la phase: {phase}",
                )
            )

        return {"issues": issues, "alternatives": alternatives}

    def _validate_sex(self, sex: str) -> Dict[str, Any]:
        """
        Valide le sexe

        Returns:
            Dict avec 'issues', 'alternatives'
        """
        issues = []
        alternatives = []

        sex_lower = sex.lower()

        # Recherche exacte
        for valid_sex, aliases in self.VALID_SEXES.items():
            if sex_lower in [alias.lower() for alias in aliases]:
                return {"issues": [], "alternatives": []}

        # Recherche partielle
        for valid_sex, aliases in self.VALID_SEXES.items():
            for alias in aliases:
                if sex_lower in alias.lower() or alias.lower() in sex_lower:
                    alternatives.append(valid_sex)
                    break

        if alternatives:
            issues.append(
                ValidationIssue(
                    field="sex",
                    severity=ValidationSeverity.WARNING,
                    message=f"Sexe '{sex}' interprété comme {alternatives[0]}",
                    suggestion=f"Utiliser: {', '.join(alternatives)}",
                )
            )
        else:
            valid_options = list(self.VALID_SEXES.keys())
            issues.append(
                ValidationIssue(
                    field="sex",
                    severity=ValidationSeverity.ERROR,
                    message=f"Sexe invalide: '{sex}'",
                    suggestion=f"Valeurs valides: {', '.join(valid_options)}",
                )
            )
            alternatives = valid_options

        return {"issues": issues, "alternatives": alternatives}

    def _validate_metric(self, metric: str) -> Dict[str, Any]:
        """
        Valide la métrique

        Returns:
            Dict avec 'issues', 'alternatives'
        """
        issues = []
        alternatives = []

        metric_normalized = metric.lower().replace(" ", "_")

        # Recherche exacte
        if metric_normalized in self.VALID_METRICS:
            return {"issues": [], "alternatives": []}

        # Recherche par alias
        for metric_key, metric_info in self.VALID_METRICS.items():
            for alias in metric_info["aliases"]:
                if metric.lower() in alias or alias in metric.lower():
                    alternatives.append(metric_key)
                    break

        if alternatives:
            issues.append(
                ValidationIssue(
                    field="metric_type",
                    severity=ValidationSeverity.INFO,
                    message=f"Métrique '{metric}' reconnue comme {alternatives[0]}",
                )
            )
        else:
            common_metrics = list(self.VALID_METRICS.keys())[:5]
            issues.append(
                ValidationIssue(
                    field="metric_type",
                    severity=ValidationSeverity.WARNING,
                    message=f"Métrique non standard: '{metric}'",
                    suggestion=f"Métriques courantes: {', '.join(common_metrics)}",
                )
            )
            alternatives = list(self.VALID_METRICS.keys())

        return {"issues": issues, "alternatives": alternatives}

    def validate_species_compatibility(
        self, breed1: str, breed2: str
    ) -> ValidationResult:
        """
        Valide que deux races sont comparables (même species)

        Args:
            breed1: Première race à comparer
            breed2: Deuxième race à comparer

        Returns:
            ValidationResult indiquant si les races sont comparables
        """
        result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
        )

        # Vérifier la compatibilité via le registry
        compatible, reason = self.breeds_registry.are_comparable(breed1, breed2)

        if not compatible:
            result.add_issue(
                field="breed_compatibility",
                severity=ValidationSeverity.ERROR,
                message=f"Races incomparables: {reason}",
                suggestion="Veuillez comparer des races de la même espèce (poulets avec poulets, dindes avec dindes, etc.)",
            )
            result.status = ValidationStatus.INVALID
            result.is_valid = False
        else:
            # Récupérer les informations des races pour le message
            breed1_info = self.breeds_registry.get_breed(breed1)
            breed2_info = self.breeds_registry.get_breed(breed2)

            if breed1_info and breed2_info:
                result.add_issue(
                    field="breed_compatibility",
                    severity=ValidationSeverity.INFO,
                    message=f"Races compatibles: {breed1_info['name']} et {breed2_info['name']} (même espèce: {breed1_info['species']})",
                )

        result.confidence = 1.0 if compatible else 0.0

        return result

    def _identify_phase(self, age: int) -> Optional[str]:
        """Identifie la phase de croissance selon l'âge"""
        for phase_name, (min_age, max_age) in self.CRITICAL_AGE_RANGES.items():
            if min_age <= age <= max_age:
                return phase_name
        return None

    def _merge_validation_results(
        self,
        main_result: ValidationResult,
        sub_validation: Dict[str, Any],
        field_name: str,
    ):
        """Fusionne les résultats de validation d'un champ dans le résultat principal"""
        # Ajouter les issues
        for issue in sub_validation.get("issues", []):
            main_result.issues.append(issue)

            # Catégoriser selon severity
            if issue.severity in [
                ValidationSeverity.CRITICAL,
                ValidationSeverity.ERROR,
            ]:
                if issue.message not in main_result.errors:
                    main_result.errors.append(issue.message)
            elif issue.severity == ValidationSeverity.WARNING:
                if issue.message not in main_result.warnings:
                    main_result.warnings.append(issue.message)

            # Ajouter suggestions
            if issue.suggestion and issue.suggestion not in main_result.suggestions:
                main_result.suggestions.append(issue.suggestion)

        # Ajouter alternatives
        if sub_validation.get("alternatives"):
            main_result.alternatives[field_name] = sub_validation["alternatives"]

    def _determine_final_status(
        self, result: ValidationResult
    ) -> Tuple[ValidationStatus, bool]:
        """
        Détermine le statut final de validation

        Returns:
            Tuple (ValidationStatus, is_valid)
        """
        # Erreurs critiques ou multiples erreurs
        critical_errors = [
            issue
            for issue in result.issues
            if issue.severity == ValidationSeverity.CRITICAL
        ]

        if critical_errors or len(result.errors) > 0:
            if len(result.validated_fields) >= 2:
                # Validation partielle possible
                return ValidationStatus.PARTIAL_VALID, False
            else:
                return ValidationStatus.INVALID, False

        # Seulement des warnings
        if result.warnings and not result.errors:
            return ValidationStatus.WARNING, True

        # Champs manquants
        if result.missing_fields:
            return ValidationStatus.MISSING_DATA, False

        # Tout est OK
        return ValidationStatus.VALID, True

    def _calculate_confidence(
        self,
        result: ValidationResult,
        entities: Dict[str, Any],
    ) -> float:
        """
        Calcule la confiance de validation basée sur:
        - Nombre d'erreurs/warnings
        - Nombre de champs validés
        - Qualité des correspondances
        """
        confidence = 1.0

        # Pénalité pour erreurs
        confidence -= len(result.errors) * 0.25

        # Pénalité pour warnings
        confidence -= len(result.warnings) * 0.1

        # Pénalité pour champs manquants
        confidence -= len(result.missing_fields) * 0.15

        # Bonus pour champs validés
        if len(result.validated_fields) >= 3:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def validate_query_feasibility(
        self, query: str, entities: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validation de faisabilité d'une requête complète
        Vérifie si la requête peut être exécutée avec les données disponibles

        Args:
            query: Requête utilisateur
            entities: Entités extraites

        Returns:
            ValidationResult avec faisabilité
        """
        result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
        )

        query_lower = query.lower()

        # Détection requêtes économiques (non supportées)
        if self._is_economic_query(query_lower):
            result.add_issue(
                field="query_type",
                severity=ValidationSeverity.ERROR,
                message="Les requêtes économiques ne sont pas supportées",
                suggestion=(
                    "Nous pouvons fournir des données de performance (poids, FCR, etc.) "
                    "que vous pouvez utiliser avec vos coûts locaux"
                ),
            )

        # Détection requêtes nutritionnelles Ross (données limitées)
        if self._is_nutrition_query(query_lower) and entities.get("breed"):
            breed_info = self.breeds_registry.get_breed(entities["breed"])
            if breed_info and "ross" in breed_info["name"].lower():
                result.add_issue(
                    field="query_type",
                    severity=ValidationSeverity.WARNING,
                    message=f"Données nutritionnelles limitées pour {breed_info['name']}",
                    suggestion="Les spécifications nutritionnelles détaillées sont plus disponibles pour Cobb 500",
                )

        # Validation des entités de base
        entities_validation = self.validate_entities(entities)

        # Fusionner les résultats
        result.errors.extend(entities_validation.errors)
        result.warnings.extend(entities_validation.warnings)
        result.suggestions.extend(entities_validation.suggestions)
        result.issues.extend(entities_validation.issues)
        result.alternatives.update(entities_validation.alternatives)

        # Déterminer statut final
        result.status, result.is_valid = self._determine_final_status(result)
        result.confidence = entities_validation.confidence
        result.allow_partial = entities_validation.allow_partial

        return result

    def _is_economic_query(self, query: str) -> bool:
        """Détecte si la requête est économique"""
        economic_keywords = [
            "coût",
            "cout",
            "cost",
            "prix",
            "price",
            "rentabilité",
            "rentabilite",
            "profitability",
            "marge",
            "margin",
            "roi",
            "économique",
            "economique",
            "€",
            "$",
            "dollar",
            "euro",
        ]
        return any(kw in query for kw in economic_keywords)

    def _is_nutrition_query(self, query: str) -> bool:
        """Détecte si la requête concerne la nutrition"""
        nutrition_keywords = [
            "nutrition",
            "nutritionnel",
            "aliment",
            "alimentation",
            "protéine",
            "protein",
            "lysine",
            "méthionine",
            "acide aminé",
            "amino acid",
            "énergie",
            "energy",
            "starter",
            "grower",
            "finisher",
            "formule",
        ]
        return any(kw in query for kw in nutrition_keywords)

    def get_validation_summary(self, result: ValidationResult) -> str:
        """
        Retourne un résumé textuel de la validation

        Args:
            result: ValidationResult

        Returns:
            Résumé lisible
        """
        summary_parts = [
            f"Statut: {result.status.value}",
            f"Valide: {'Oui' if result.is_valid else 'Non'}",
        ]

        if result.errors:
            summary_parts.append(f"Erreurs: {len(result.errors)}")

        if result.warnings:
            summary_parts.append(f"Warnings: {len(result.warnings)}")

        if result.validated_fields:
            summary_parts.append(
                f"Champs validés: {', '.join(result.validated_fields)}"
            )

        if result.missing_fields:
            summary_parts.append(
                f"Champs manquants: {', '.join(result.missing_fields)}"
            )

        summary_parts.append(f"Confiance: {result.confidence:.2%}")

        return " | ".join(summary_parts)

    def suggest_corrections(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggère des corrections pour des entités invalides

        Args:
            entities: Entités à corriger

        Returns:
            Dict avec entités corrigées et explications
        """
        corrected = entities.copy()
        corrections_applied = []

        validation_result = self.validate_entities(entities)

        # Appliquer corrections depuis alternatives
        for field_name, alternatives in validation_result.alternatives.items():
            if alternatives and field_name in corrected:
                # Prendre la première alternative
                old_value = corrected[field_name]
                corrected[field_name] = alternatives[0]
                corrections_applied.append(
                    {
                        "field": field_name,
                        "old_value": old_value,
                        "new_value": alternatives[0],
                        "reason": "Correction automatique basée sur correspondance partielle",
                    }
                )

        return {
            "corrected_entities": corrected,
            "corrections": corrections_applied,
            "still_invalid": not self.validate_entities(corrected).is_valid,
        }


# Factory function
def create_validation_core(strict_mode: bool = False) -> ValidationCore:
    """Factory pour créer une instance ValidationCore"""
    return ValidationCore(strict_mode=strict_mode)


# Tests unitaires
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    validator = ValidationCore(strict_mode=False)

    test_cases = [
        {
            "name": "Entités valides complètes",
            "entities": {
                "breed": "cobb500",
                "age_days": 21,
                "sex": "male",
                "metric_type": "body_weight",
            },
            "expected_valid": True,
        },
        {
            "name": "Breed avec alias",
            "entities": {
                "breed": "Cobb 500",
                "age_days": 35,
                "sex": "female",
            },
            "expected_valid": True,
        },
        {
            "name": "Âge hors plage",
            "entities": {
                "breed": "ross308",
                "age_days": 150,
                "sex": "male",
            },
            "expected_valid": True,  # Warning seulement
        },
        {
            "name": "Breed inconnu",
            "entities": {
                "breed": "invalid_breed",
                "age_days": 21,
            },
            "expected_valid": False,
        },
        {
            "name": "Sexe invalide",
            "entities": {
                "breed": "cobb500",
                "age_days": 21,
                "sex": "invalid_sex",
            },
            "expected_valid": False,
        },
        {
            "name": "Champs manquants avec required_fields",
            "entities": {
                "age_days": 21,
            },
            "expected_valid": False,
        },
    ]

    print("=== TESTS VALIDATION CORE ===\n")

    for test in test_cases:
        print(f"Test: {test['name']}")

        required = ["breed"] if "Champs manquants" in test["name"] else None
        result = validator.validate_entities(test["entities"], required_fields=required)

        status = "✅" if result.is_valid == test["expected_valid"] else "❌"

        print(f"  {status} {validator.get_validation_summary(result)}")

        if result.errors:
            print(f"  Erreurs: {result.errors}")

        if result.warnings:
            print(f"  Warnings: {result.warnings}")

        if result.suggestions:
            print(f"  Suggestions: {result.suggestions[:2]}")

        if result.alternatives:
            print(f"  Alternatives: {result.alternatives}")

        print()

    # Test corrections automatiques
    print("\n=== TEST CORRECTIONS AUTOMATIQUES ===\n")

    invalid_entities = {
        "breed": "cobb 500",  # Espace
        "age_days": 21,
        "sex": "mâle",  # Avec accent
    }

    print("Entités originales:", invalid_entities)
    corrections = validator.suggest_corrections(invalid_entities)
    print("Entités corrigées:", corrections["corrected_entities"])
    print("Corrections appliquées:", corrections["corrections"])
    print()

    # Test validation compatibilité espèces
    print("\n=== TEST VALIDATION COMPATIBILITÉ ESPÈCES ===\n")

    # Test 1: Deux poulets comparables
    comp_result1 = validator.validate_species_compatibility("cobb500", "ross308")
    print(f"Cobb500 vs Ross308: {comp_result1.is_valid}")
    print(
        f"  Message: {comp_result1.issues[0].message if comp_result1.issues else 'Aucun'}"
    )

    # Test 2: Poulet vs Dinde (si disponible dans le registry)
    try:
        comp_result2 = validator.validate_species_compatibility("cobb500", "but6")
        print(f"\nCobb500 vs BUT6 (dinde): {comp_result2.is_valid}")
        print(
            f"  Message: {comp_result2.issues[0].message if comp_result2.issues else 'Aucun'}"
        )
    except Exception as e:
        print(f"\nTest poulet vs dinde: {e}")

    print()