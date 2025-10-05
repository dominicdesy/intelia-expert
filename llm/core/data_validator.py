# -*- coding: utf-8 -*-
"""
data_validator.py - Validation de cohérence des données
Vérifie la cohérence mathématique et logique des données retournées
"""

import logging
from utils.types import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Un problème de validation détecté"""

    severity: str  # "error", "warning", "info"
    issue_type: str
    message: str
    expected: Optional[float] = None
    actual: Optional[float] = None
    tolerance: Optional[float] = None


@dataclass
class DataValidationResult:
    """Résultat de validation de données"""

    is_valid: bool
    issues: List[ValidationIssue]
    confidence_score: float


class DataValidator:
    """Validateur de cohérence des données avicoles"""

    # Plages de valeurs attendues
    EXPECTED_RANGES = {
        "body_weight": {
            "day_1": (40, 70),
            "day_7": (150, 250),
            "day_14": (450, 650),
            "day_21": (850, 1200),
            "day_28": (1400, 1900),
            "day_35": (2000, 2800),
            "day_42": (2500, 3500),
            "day_49": (3200, 4300),
            "day_56": (3800, 5000),
        },
        "feed_conversion_ratio": {
            "day_7": (0.65, 0.85),
            "day_14": (0.95, 1.05),
            "day_21": (1.08, 1.18),
            "day_28": (1.20, 1.32),
            "day_35": (1.32, 1.46),
            "day_42": (1.45, 1.60),
            "day_49": (1.58, 1.75),
            "day_56": (1.70, 1.90),
        },
        "daily_gain": {"min": 10, "max": 120},
    }

    # Tolérance pour calculs
    FCR_CALCULATION_TOLERANCE = 0.05  # 5%
    WEIGHT_GAIN_TOLERANCE = 0.10  # 10%

    def __init__(self):
        """Initialise le validateur"""
        pass

    def validate_query_results(
        self, results: List[Dict], query_type: str = "performance"
    ) -> DataValidationResult:
        """
        Valide les résultats d'une requête

        Args:
            results: Liste de résultats à valider
            query_type: Type de requête

        Returns:
            DataValidationResult
        """
        issues = []

        for result in results:
            # Validation FCR
            if "fcr" in result or "feed_conversion_ratio" in result:
                fcr_issues = self.validate_fcr_calculation(result)
                issues.extend(fcr_issues)

            # Validation plages de valeurs
            range_issues = self.validate_value_ranges(result)
            issues.extend(range_issues)

            # Validation cohérence gains
            if "daily_gain" in result and "weight" in result:
                growth_issues = self.validate_growth_consistency(result)
                issues.extend(growth_issues)

        # Calculer score de confiance
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        if errors:
            confidence = 0.3
            is_valid = False
        elif warnings:
            confidence = 0.7
            is_valid = True
        else:
            confidence = 1.0
            is_valid = True

        return DataValidationResult(
            is_valid=is_valid, issues=issues, confidence_score=confidence
        )

    def validate_fcr_calculation(self, data: Dict) -> List[ValidationIssue]:
        """
        Vérifie que IC = intake / weight

        Args:
            data: Dict avec weight, intake, fcr

        Returns:
            Liste de ValidationIssue
        """
        issues = []

        weight = data.get("weight") or data.get("body_weight") or data.get("weight_g")
        intake = (
            data.get("intake")
            or data.get("cumulative_intake")
            or data.get("feed_intake")
        )
        fcr = data.get("fcr") or data.get("feed_conversion_ratio")

        if not all([weight, intake, fcr]):
            return issues  # Pas assez de données pour valider

        try:
            weight = float(weight)
            intake = float(intake)
            fcr = float(fcr)

            # Calculer IC attendu
            expected_fcr = intake / weight if weight > 0 else 0

            # Vérifier écart
            relative_diff = (
                abs(fcr - expected_fcr) / expected_fcr if expected_fcr > 0 else 1.0
            )

            if relative_diff > self.FCR_CALCULATION_TOLERANCE:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="fcr_calculation_mismatch",
                        message=f"IC calculé ({expected_fcr:.3f}) diffère de l'IC fourni ({fcr:.3f})",
                        expected=round(expected_fcr, 3),
                        actual=fcr,
                        tolerance=self.FCR_CALCULATION_TOLERANCE,
                    )
                )

        except (ValueError, ZeroDivisionError) as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    issue_type="fcr_calculation_error",
                    message=f"Erreur calcul IC: {e}",
                    expected=None,
                    actual=None,
                )
            )

        return issues

    def validate_value_ranges(self, data: Dict) -> List[ValidationIssue]:
        """
        Vérifie que les valeurs sont dans les plages attendues

        Args:
            data: Dict avec métriques

        Returns:
            Liste de ValidationIssue
        """
        issues = []

        age = data.get("age") or data.get("age_min") or data.get("age_days")

        if not age:
            return issues

        try:
            age = int(age)

            # Validation poids
            weight = (
                data.get("weight") or data.get("body_weight") or data.get("weight_g")
            )
            if weight:
                weight_issues = self._validate_weight_range(float(weight), age)
                issues.extend(weight_issues)

            # Validation IC
            fcr = data.get("fcr") or data.get("feed_conversion_ratio")
            if fcr:
                fcr_issues = self._validate_fcr_range(float(fcr), age)
                issues.extend(fcr_issues)

            # Validation gain quotidien
            daily_gain = data.get("daily_gain")
            if daily_gain:
                gain_issues = self._validate_daily_gain_range(float(daily_gain))
                issues.extend(gain_issues)

        except (ValueError, TypeError) as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    issue_type="value_conversion_error",
                    message=f"Erreur conversion valeurs: {e}",
                )
            )

        return issues

    def _validate_weight_range(self, weight: float, age: int) -> List[ValidationIssue]:
        """Valide plage de poids pour un âge"""
        issues = []

        # Trouver plage la plus proche
        age_key = f"day_{age}"

        if age_key in self.EXPECTED_RANGES["body_weight"]:
            min_weight, max_weight = self.EXPECTED_RANGES["body_weight"][age_key]

            if weight < min_weight or weight > max_weight:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="weight_out_of_range",
                        message=f"Poids {weight}g à {age}j hors plage attendue ({min_weight}-{max_weight}g)",
                        expected=(min_weight + max_weight) / 2,
                        actual=weight,
                    )
                )

        return issues

    def _validate_fcr_range(self, fcr: float, age: int) -> List[ValidationIssue]:
        """Valide plage d'IC pour un âge"""
        issues = []

        age_key = f"day_{age}"

        if age_key in self.EXPECTED_RANGES["feed_conversion_ratio"]:
            min_fcr, max_fcr = self.EXPECTED_RANGES["feed_conversion_ratio"][age_key]

            if fcr < min_fcr or fcr > max_fcr:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="fcr_out_of_range",
                        message=f"IC {fcr:.3f} à {age}j hors plage attendue ({min_fcr:.3f}-{max_fcr:.3f})",
                        expected=(min_fcr + max_fcr) / 2,
                        actual=fcr,
                    )
                )

        return issues

    def _validate_daily_gain_range(self, daily_gain: float) -> List[ValidationIssue]:
        """Valide plage de gain quotidien"""
        issues = []

        min_gain = self.EXPECTED_RANGES["daily_gain"]["min"]
        max_gain = self.EXPECTED_RANGES["daily_gain"]["max"]

        if daily_gain < min_gain or daily_gain > max_gain:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    issue_type="daily_gain_out_of_range",
                    message=f"Gain quotidien {daily_gain}g hors plage attendue ({min_gain}-{max_gain}g)",
                    expected=(min_gain + max_gain) / 2,
                    actual=daily_gain,
                )
            )

        return issues

    def validate_growth_consistency(self, data: Dict) -> List[ValidationIssue]:
        """
        Vérifie la cohérence entre gains et poids

        Args:
            data: Dict avec daily_gain et weight

        Returns:
            Liste de ValidationIssue
        """
        issues = []

        # TODO: Implémenter validation séquentielle des gains
        # Nécessite données temporelles multiples

        return issues

    def validate_nutrition_progression(
        self, phases: List[Dict]
    ) -> List[ValidationIssue]:
        """
        Vérifie la progressivité des nutriments par phase (Cobb uniquement)

        Args:
            phases: Liste de phases nutritionnelles

        Returns:
            Liste de ValidationIssue
        """
        issues = []

        if len(phases) < 2:
            return issues

        # Vérifier que protéines diminuent progressivement
        for i in range(len(phases) - 1):
            current_protein = phases[i].get("crude_protein")
            next_protein = phases[i + 1].get("crude_protein")

            if current_protein and next_protein:
                if next_protein > current_protein:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            issue_type="protein_not_decreasing",
                            message=f"Protéines augmentent entre phases {i} et {i+1}",
                            expected=current_protein,
                            actual=next_protein,
                        )
                    )

        # Vérifier que énergie augmente progressivement
        for i in range(len(phases) - 1):
            current_energy = phases[i].get("metabolizable_energy")
            next_energy = phases[i + 1].get("metabolizable_energy")

            if current_energy and next_energy:
                if next_energy < current_energy:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            issue_type="energy_not_increasing",
                            message=f"Énergie diminue entre phases {i} et {i+1}",
                            expected=current_energy,
                            actual=next_energy,
                        )
                    )

        return issues

    def generate_validation_report(
        self, validation_result: DataValidationResult
    ) -> str:
        """
        Génère un rapport de validation lisible

        Args:
            validation_result: Résultat de validation

        Returns:
            Rapport formaté
        """
        if validation_result.is_valid and not validation_result.issues:
            return "✅ Données validées - Aucun problème détecté"

        report_lines = []
        report_lines.append(
            f"📊 Score de confiance: {validation_result.confidence_score:.1%}"
        )
        report_lines.append("")

        errors = [i for i in validation_result.issues if i.severity == "error"]
        warnings = [i for i in validation_result.issues if i.severity == "warning"]

        if errors:
            report_lines.append("❌ Erreurs:")
            for issue in errors:
                report_lines.append(f"  - {issue.message}")
            report_lines.append("")

        if warnings:
            report_lines.append("⚠️ Avertissements:")
            for issue in warnings:
                report_lines.append(f"  - {issue.message}")

        return "\n".join(report_lines)
