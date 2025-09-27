# -*- coding: utf-8 -*-
"""
metric_calculator.py - Calculs mathématiques sur les métriques avicoles
Effectue les opérations de comparaison, différence, ratio, etc.
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
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "value1": {"value": self.value1, "label": self.label1},
            "value2": {"value": self.value2, "label": self.label2},
            "absolute_difference": self.absolute_difference,
            "relative_difference_pct": self.relative_difference_pct,
            "ratio": self.ratio,
            "higher": self.higher_label,
            "unit": self.unit,
        }


class MetricCalculator:
    """Effectue des calculs mathématiques sur les métriques"""

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

        # Extraction de l'unité
        unit = ""
        if results[0]["data"] and len(results[0]["data"]) > 0:
            unit = results[0]["data"][0].get("unit", "")

        # Calculs
        absolute_diff = value1 - value2
        relative_diff_pct = ((value1 - value2) / value2) * 100 if value2 != 0 else None
        ratio = value1 / value2 if value2 != 0 else None
        higher_label = label1 if value1 > value2 else label2

        logger.info(
            f"Comparison calculated: {label1}={value1} vs {label2}={value2}, "
            f"diff={absolute_diff:.3f} ({relative_diff_pct:.1f}%)"
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
            unit=unit,
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

        Args:
            comparison: Résultat de comparaison
            metric_name: Nom de la métrique (clé technique comme 'feed_conversion_ratio')
            language: Langue ('fr' ou 'en')
            terminology: Dictionnaire de terminologie chargé depuis les fichiers JSON

        Returns:
            Texte formaté
        """
        # Nettoyer le nom de métrique (enlever "for 17" etc.)
        if "for" in metric_name:
            metric_name = metric_name.split("for")[0].strip()

        # Traduire le nom de métrique depuis terminology si disponible
        if terminology and language in terminology:
            lang_terms = terminology[language]
            if "performance_metrics" in lang_terms:
                perf_metrics = lang_terms["performance_metrics"]

                # Chercher la traduction dans performance_metrics
                metric_key = metric_name.lower().replace(" ", "_")
                if metric_key in perf_metrics and isinstance(
                    perf_metrics[metric_key], list
                ):
                    # Prendre le premier terme (généralement le plus formel)
                    metric_name = perf_metrics[metric_key][0]

        if language == "fr":
            unit_display = f" {comparison.unit}" if comparison.unit else ""

            text = f"• **{comparison.label1.capitalize()}** : {comparison.value1:.3f}{unit_display}\n"
            text += f"• **{comparison.label2.capitalize()}** : {comparison.value2:.3f}{unit_display}\n\n"
            text += f"**Différence** : {abs(comparison.absolute_difference):.3f}{unit_display}"

            if comparison.relative_difference_pct is not None:
                text += f" ({abs(comparison.relative_difference_pct):.1f}%)"

            text += "\n\n"

            if comparison.absolute_difference > 0:
                text += f"Le **{comparison.label1}** présente une valeur supérieure de **{abs(comparison.relative_difference_pct):.1f}%** "
                text += f"par rapport au **{comparison.label2}**."
            else:
                text += f"Le **{comparison.label1}** présente une valeur inférieure de **{abs(comparison.relative_difference_pct):.1f}%** "
                text += f"par rapport au **{comparison.label2}**."

        else:  # English
            unit_display = f" {comparison.unit}" if comparison.unit else ""

            text = f"• **{comparison.label1.capitalize()}**: {comparison.value1:.3f}{unit_display}\n"
            text += f"• **{comparison.label2.capitalize()}**: {comparison.value2:.3f}{unit_display}\n\n"
            text += f"**Difference**: {abs(comparison.absolute_difference):.3f}{unit_display}"

            if comparison.relative_difference_pct is not None:
                text += f" ({abs(comparison.relative_difference_pct):.1f}%)"

            text += "\n\n"

            if comparison.absolute_difference > 0:
                text += f"**{comparison.label1.capitalize()}** shows a value **{abs(comparison.relative_difference_pct):.1f}% higher** "
                text += f"than **{comparison.label2}**."
            else:
                text += f"**{comparison.label1.capitalize()}** shows a value **{abs(comparison.relative_difference_pct):.1f}% lower** "
                text += f"than **{comparison.label2}**."

        return text


# Tests unitaires
if __name__ == "__main__":
    # Test de comparaison
    calculator = MetricCalculator()

    test_results = [
        {"sex": "male", "data": [{"value_numeric": 1.081, "unit": "ratio"}]},
        {"sex": "female", "data": [{"value_numeric": 1.045, "unit": "ratio"}]},
    ]

    comparison = calculator.calculate_comparison(test_results)
    print("Comparison Result:")
    print(f"  {comparison.label1}: {comparison.value1}")
    print(f"  {comparison.label2}: {comparison.value2}")
    print(f"  Difference: {comparison.absolute_difference:.3f}")
    print(f"  Relative: {comparison.relative_difference_pct:.1f}%")
    print(f"  Higher: {comparison.higher_label}")

    print("\n" + "=" * 50)
    print(calculator.format_comparison_text(comparison, "FCR"))
