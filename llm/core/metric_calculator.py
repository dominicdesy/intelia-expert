# -*- coding: utf-8 -*-
"""
metric_calculator.py - Calculs mathématiques sur les métriques avicoles
VERSION CORRIGÉE : Gestion correcte des métriques où "plus bas = meilleur" (FCR, mortalité)
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Résultat d'une comparaison entre deux métriques"""

    value1: float
    value2: float
    label1: str
    label2: str
    absolute_difference: float
    relative_difference_pct: Optional[float]
    ratio: Optional[float]
    higher_label: str
    better_label: str  # NOUVEAU: qui a la meilleure valeur (selon le contexte)
    unit: str = ""
    metric_name: str = ""  # NOUVEAU: pour déterminer si lower is better

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "value1": {"value": self.value1, "label": self.label1},
            "value2": {"value": self.value2, "label": self.label2},
            "absolute_difference": self.absolute_difference,
            "relative_difference_pct": self.relative_difference_pct,
            "ratio": self.ratio,
            "higher": self.higher_label,
            "better": self.better_label,
            "unit": self.unit,
            "metric_name": self.metric_name,
        }


class MetricCalculator:
    """Effectue des calculs mathématiques sur les métriques"""

    # Métriques où une valeur PLUS BASSE est meilleure
    LOWER_IS_BETTER_METRICS = [
        "fcr",
        "feed_conversion",
        "conversion",
        "indice_conversion",
        "mortality",
        "mortalite",
        "mort",
        "death",
        "culling",
        "cull",
        "elimination",
        "cost",
        "cout",
        "price",
        "prix",
    ]

    @staticmethod
    def _is_lower_better(metric_name: str) -> bool:
        """
        Détermine si pour cette métrique, une valeur plus basse est meilleure

        Args:
            metric_name: Nom de la métrique (ex: "feed_conversion_ratio")

        Returns:
            True si lower is better (FCR, mortalité, coûts)
        """
        metric_lower = metric_name.lower().replace("_", " ")

        for pattern in MetricCalculator.LOWER_IS_BETTER_METRICS:
            if pattern in metric_lower:
                logger.debug(f"Metric '{metric_name}' identified as LOWER IS BETTER")
                return True

        logger.debug(f"Metric '{metric_name}' identified as HIGHER IS BETTER")
        return False

    @staticmethod
    def calculate_comparison(results: List[Dict[str, Any]]) -> ComparisonResult:
        """
        Calcule les différences entre deux résultats

        Args:
            results: Liste de 2 dictionnaires contenant:
                - 'sex' ou autre label de comparaison
                - 'data': liste de métriques avec 'value_numeric'

        Returns:
            ComparisonResult avec tous les calculs
        """
        if len(results) != 2:
            raise ValueError(
                f"Comparison requires exactly 2 result sets, got {len(results)}"
            )

        # Extraction des valeurs
        value1 = MetricCalculator._extract_primary_value(results[0]["data"])
        value2 = MetricCalculator._extract_primary_value(results[1]["data"])

        if value1 is None or value2 is None:
            raise ValueError("Missing values for comparison")

        # Extraction des labels
        label1 = results[0].get("sex") or results[0].get("label", "Value 1")
        label2 = results[1].get("sex") or results[1].get("label", "Value 2")

        # Extraction de l'unité et du nom de métrique
        unit = ""
        metric_name = ""
        if results[0]["data"] and len(results[0]["data"]) > 0:
            unit = results[0]["data"][0].get("unit", "")
            metric_name = results[0]["data"][0].get("metric_name", "")

        # Calculs
        absolute_diff = value1 - value2
        relative_diff_pct = ((value1 - value2) / value2) * 100 if value2 != 0 else None
        ratio = value1 / value2 if value2 != 0 else None
        higher_label = label1 if value1 > value2 else label2

        # NOUVEAU: Déterminer qui est "meilleur" selon le type de métrique
        is_lower_better = MetricCalculator._is_lower_better(metric_name)

        if is_lower_better:
            # Pour FCR, mortalité, etc. : le plus BAS est meilleur
            better_label = label1 if value1 < value2 else label2
        else:
            # Pour poids, production, etc. : le plus HAUT est meilleur
            better_label = label1 if value1 > value2 else label2

        logger.info(
            f"Comparison calculated: {label1}={value1} vs {label2}={value2}, "
            f"diff={absolute_diff:.3f} ({relative_diff_pct:.1f}%), "
            f"better={better_label} (lower_is_better={is_lower_better})"
        )

        return ComparisonResult(
            value1=value1,
            value2=value2,
            label1=label1,
            label2=label2,
            absolute_difference=absolute_diff,
            relative_difference_pct=relative_diff_pct,
            ratio=ratio,
            higher_label=higher_label,
            better_label=better_label,
            unit=unit,
            metric_name=metric_name,
        )

    @staticmethod
    def _extract_primary_value(data: List[Dict]) -> Optional[float]:
        """Extrait la valeur principale des résultats"""
        if not data or len(data) == 0:
            return None

        # Prendre le premier résultat et extraire value_numeric
        first_result = data[0]

        # Si c'est un dict
        if isinstance(first_result, dict):
            return first_result.get("value_numeric")

        # Si c'est un objet avec attribut
        if hasattr(first_result, "value_numeric"):
            return first_result.value_numeric

        return None

    @staticmethod
    def calculate_average(values: List[float]) -> float:
        """Calcule la moyenne de valeurs"""
        if not values:
            raise ValueError("Cannot calculate average of empty list")
        return sum(values) / len(values)

    @staticmethod
    def calculate_percentage_change(old_value: float, new_value: float) -> float:
        """Calcule le pourcentage de changement"""
        if old_value == 0:
            return float("inf") if new_value != 0 else 0.0
        return ((new_value - old_value) / old_value) * 100

    @staticmethod
    def format_comparison_text(
        comparison: ComparisonResult,
        metric_name: str = "métrique",
        language: str = "fr",
        terminology: Dict[str, Any] = None,
    ) -> str:
        """
        Formate le résultat de comparaison en texte naturel
        VERSION CORRIGÉE : Interprétation correcte selon le type de métrique

        Args:
            comparison: Résultat de comparaison
            metric_name: Nom de la métrique
            language: Langue ('fr' ou 'en')
            terminology: Dictionnaire de terminologie

        Returns:
            Texte formaté avec interprétation correcte
        """
        # Nettoyer le nom de métrique
        if "for" in metric_name:
            metric_name = metric_name.split("for")[0].strip()

        # Traduire le nom de métrique
        display_metric_name = metric_name
        if terminology and language in terminology:
            lang_terms = terminology[language]
            if "performance_metrics" in lang_terms:
                perf_metrics = lang_terms["performance_metrics"]
                metric_key = metric_name.lower().replace(" ", "_")
                if metric_key in perf_metrics and isinstance(
                    perf_metrics[metric_key], list
                ):
                    display_metric_name = perf_metrics[metric_key][0]

        # Déterminer si lower is better
        is_lower_better = MetricCalculator._is_lower_better(
            comparison.metric_name or metric_name
        )

        if language == "fr":
            unit_display = f" {comparison.unit}" if comparison.unit else ""

            # Affichage des valeurs
            text = f"Pour la **{display_metric_name}** :\n\n"
            text += f"• **{comparison.label1.capitalize()}** : {comparison.value1:.3f}{unit_display}\n"
            text += f"• **{comparison.label2.capitalize()}** : {comparison.value2:.3f}{unit_display}\n\n"
            text += f"**Différence** : {abs(comparison.absolute_difference):.3f}{unit_display}"

            if comparison.relative_difference_pct is not None:
                text += f" ({abs(comparison.relative_difference_pct):.1f}%)"

            text += "\n\n"

            # CORRECTION : Interprétation selon le type de métrique
            if is_lower_better:
                # Pour FCR, mortalité : plus bas = meilleur
                if comparison.value1 < comparison.value2:
                    text += f"Le **{comparison.label1}** présente une **meilleure** performance "
                    text += f"avec une valeur **{abs(comparison.relative_difference_pct):.1f}% inférieure** "
                    text += f"au **{comparison.label2}**.\n"
                    text += "_Une valeur plus basse indique une meilleure efficacité pour cette métrique._"
                else:
                    text += f"Le **{comparison.label2}** présente une **meilleure** performance "
                    text += f"avec une valeur **{abs(comparison.relative_difference_pct):.1f}% inférieure** "
                    text += f"au **{comparison.label1}**.\n"
                    text += "_Une valeur plus basse indique une meilleure efficacité pour cette métrique._"
            else:
                # Pour poids, production : plus haut = meilleur
                if comparison.absolute_difference > 0:
                    text += f"Le **{comparison.label1}** présente une valeur **{abs(comparison.relative_difference_pct):.1f}% supérieure** "
                    text += f"au **{comparison.label2}**."
                else:
                    text += f"Le **{comparison.label2}** présente une valeur **{abs(comparison.relative_difference_pct):.1f}% supérieure** "
                    text += f"au **{comparison.label1}**."

        else:  # English
            unit_display = f" {comparison.unit}" if comparison.unit else ""

            text = f"For **{display_metric_name}**:\n\n"
            text += f"• **{comparison.label1.capitalize()}**: {comparison.value1:.3f}{unit_display}\n"
            text += f"• **{comparison.label2.capitalize()}**: {comparison.value2:.3f}{unit_display}\n\n"
            text += f"**Difference**: {abs(comparison.absolute_difference):.3f}{unit_display}"

            if comparison.relative_difference_pct is not None:
                text += f" ({abs(comparison.relative_difference_pct):.1f}%)"

            text += "\n\n"

            # CORRECTION : Correct interpretation based on metric type
            if is_lower_better:
                # For FCR, mortality: lower = better
                if comparison.value1 < comparison.value2:
                    text += f"**{comparison.label1.capitalize()}** shows **better** performance "
                    text += f"with a value **{abs(comparison.relative_difference_pct):.1f}% lower** "
                    text += f"than **{comparison.label2}**.\n"
                    text += (
                        "_A lower value indicates better efficiency for this metric._"
                    )
                else:
                    text += f"**{comparison.label2.capitalize()}** shows **better** performance "
                    text += f"with a value **{abs(comparison.relative_difference_pct):.1f}% lower** "
                    text += f"than **{comparison.label1}**.\n"
                    text += (
                        "_A lower value indicates better efficiency for this metric._"
                    )
            else:
                # For weight, production: higher = better
                if comparison.absolute_difference > 0:
                    text += f"**{comparison.label1.capitalize()}** shows a value **{abs(comparison.relative_difference_pct):.1f}% higher** "
                    text += f"than **{comparison.label2}**."
                else:
                    text += f"**{comparison.label2.capitalize()}** shows a value **{abs(comparison.relative_difference_pct):.1f}% higher** "
                    text += f"than **{comparison.label1}**."

        return text


# Tests unitaires
if __name__ == "__main__":
    calculator = MetricCalculator()

    print("=" * 80)
    print("TEST 1: FCR Comparison (lower is better)")
    print("=" * 80)

    fcr_results = [
        {
            "sex": "Cobb 500",
            "data": [
                {
                    "value_numeric": 1.081,
                    "unit": "ratio",
                    "metric_name": "feed_conversion_ratio for 17",
                }
            ],
        },
        {
            "sex": "Ross 308",
            "data": [
                {
                    "value_numeric": 1.065,
                    "unit": "ratio",
                    "metric_name": "feed_conversion_ratio for 17",
                }
            ],
        },
    ]

    comparison = calculator.calculate_comparison(fcr_results)
    print(f"Value 1 (Cobb 500): {comparison.value1}")
    print(f"Value 2 (Ross 308): {comparison.value2}")
    print(f"Higher: {comparison.higher_label}")
    print(f"Better: {comparison.better_label}")
    print(f"Difference: {comparison.absolute_difference:.3f}")
    print(f"Relative: {comparison.relative_difference_pct:.1f}%")

    print("\n" + "-" * 80)
    print("FORMATTED TEXT:")
    print("-" * 80)
    print(calculator.format_comparison_text(comparison, "feed_conversion_ratio"))

    print("\n" + "=" * 80)
    print("TEST 2: Body Weight Comparison (higher is better)")
    print("=" * 80)

    weight_results = [
        {
            "sex": "male",
            "data": [
                {
                    "value_numeric": 950.5,
                    "unit": "g",
                    "metric_name": "body_weight for 17",
                }
            ],
        },
        {
            "sex": "female",
            "data": [
                {
                    "value_numeric": 880.2,
                    "unit": "g",
                    "metric_name": "body_weight for 17",
                }
            ],
        },
    ]

    comparison2 = calculator.calculate_comparison(weight_results)
    print(f"Value 1 (male): {comparison2.value1}")
    print(f"Value 2 (female): {comparison2.value2}")
    print(f"Higher: {comparison2.higher_label}")
    print(f"Better: {comparison2.better_label}")

    print("\n" + "-" * 80)
    print("FORMATTED TEXT:")
    print("-" * 80)
    print(calculator.format_comparison_text(comparison2, "body_weight"))
