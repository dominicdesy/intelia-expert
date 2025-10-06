# -*- coding: utf-8 -*-
"""
metric_calculator.py - Calculs mathématiques sur les métriques avicoles
VERSION 2.0 - English templates with dynamic translation
- Gestion correcte des métriques où "plus bas = meilleur" (FCR, mortalité)
- Validation stricte contre division par zéro
- Contexte enrichi (âge, sexe) dans la réponse
- Templates EN avec traduction dynamique (FR, ES, DE, IT, PT, TH, VI)
"""

import logging
from utils.types import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Translation mapping for metric formatting
METRIC_TRANSLATIONS = {
    "For": {
        "fr": "Pour la",
        "es": "Para",
        "de": "Für",
        "it": "Per",
        "pt": "Para",
        "th": "สำหรับ",
        "vi": "Cho",
    },
    "males": {
        "fr": "mâles",
        "es": "machos",
        "de": "Männchen",
        "it": "maschi",
        "pt": "machos",
        "th": "ตัวผู้",
        "vi": "trống",
    },
    "females": {
        "fr": "femelles",
        "es": "hembras",
        "de": "Weibchen",
        "it": "femmine",
        "pt": "fêmeas",
        "th": "ตัวเมีย",
        "vi": "mái",
    },
    "mixed sexes": {
        "fr": "sexes mélangés",
        "es": "sexos mixtos",
        "de": "gemischte Geschlechter",
        "it": "sessi misti",
        "pt": "sexos mistos",
        "th": "เพศผสม",
        "vi": "giới tính hỗn hợp",
    },
    "at": {
        "fr": "à",
        "es": "a",
        "de": "bei",
        "it": "a",
        "pt": "aos",
        "th": "ที่",
        "vi": "tại",
    },
    "days": {
        "fr": "jours",
        "es": "días",
        "de": "Tage",
        "it": "giorni",
        "pt": "dias",
        "th": "วัน",
        "vi": "ngày",
    },
    "Difference": {
        "fr": "Différence",
        "es": "Diferencia",
        "de": "Unterschied",
        "it": "Differenza",
        "pt": "Diferença",
        "th": "ความแตกต่าง",
        "vi": "Sự khác biệt",
    },
    "shows better performance with a value": {
        "fr": "présente une meilleure performance avec une valeur",
        "es": "muestra mejor rendimiento con un valor",
        "de": "zeigt bessere Leistung mit einem Wert",
        "it": "mostra prestazioni migliori con un valore",
        "pt": "apresenta melhor desempenho com um valor",
        "th": "แสดงประสิทธิภาพที่ดีขึ้นด้วยค่า",
        "vi": "cho thấy hiệu suất tốt hơn với giá trị",
    },
    "lower": {
        "fr": "inférieure",
        "es": "menor",
        "de": "niedriger",
        "it": "inferiore",
        "pt": "inferior",
        "th": "ต่ำกว่า",
        "vi": "thấp hơn",
    },
    "higher": {
        "fr": "supérieure",
        "es": "mayor",
        "de": "höher",
        "it": "superiore",
        "pt": "superior",
        "th": "สูงกว่า",
        "vi": "cao hơn",
    },
    "than": {
        "fr": "au",
        "es": "que",
        "de": "als",
        "it": "di",
        "pt": "que",
        "th": "กว่า",
        "vi": "so với",
    },
    "requires less feed to produce 1 kg of live weight, indicating better feed efficiency.": {
        "fr": "nécessite moins d'aliment pour produire 1 kg de poids vif, ce qui représente une meilleure efficacité alimentaire.",
        "es": "requiere menos alimento para producir 1 kg de peso vivo, lo que indica mejor eficiencia alimentaria.",
        "de": "benötigt weniger Futter zur Produktion von 1 kg Lebendgewicht, was eine bessere Futterverwertung bedeutet.",
        "it": "richiede meno mangime per produrre 1 kg di peso vivo, indicando una migliore efficienza alimentare.",
        "pt": "requer menos ração para produzir 1 kg de peso vivo, indicando melhor eficiência alimentar.",
        "th": "ต้องการอาหารน้อยลงเพื่อผลิต 1 กก. น้ำหนักตัว แสดงถึงประสิทธิภาพการใช้อาหารที่ดีขึ้น",
        "vi": "cần ít thức ăn hơn để tạo ra 1 kg trọng lượng sống, cho thấy hiệu quả thức ăn tốt hơn.",
    },
    "A lower value indicates better performance for this metric.": {
        "fr": "Une valeur plus basse indique une meilleure performance pour cette métrique.",
        "es": "Un valor más bajo indica mejor rendimiento para esta métrica.",
        "de": "Ein niedrigerer Wert zeigt eine bessere Leistung für diese Metrik an.",
        "it": "Un valore più basso indica prestazioni migliori per questa metrica.",
        "pt": "Um valor mais baixo indica melhor desempenho para esta métrica.",
        "th": "ค่าที่ต่ำกว่าแสดงถึงประสิทธิภาพที่ดีขึ้นสำหรับตัวชี้วัดนี้",
        "vi": "Giá trị thấp hơn cho thấy hiệu suất tốt hơn cho chỉ số này.",
    },
    "shows a value": {
        "fr": "présente une valeur",
        "es": "muestra un valor",
        "de": "zeigt einen Wert",
        "it": "mostra un valore",
        "pt": "apresenta um valor",
        "th": "แสดงค่า",
        "vi": "cho thấy giá trị",
    },
}


def _translate_metric(text_en: str, language: str) -> str:
    """
    Traduit un texte EN vers la langue cible pour metric_calculator

    Args:
        text_en: Texte en anglais
        language: Code langue (fr, es, de, etc.)

    Returns:
        Texte traduit ou EN si langue non supportée
    """
    if language == "en" or language not in [
        "fr",
        "es",
        "de",
        "it",
        "pt",
        "th",
        "vi",
    ]:
        return text_en

    return METRIC_TRANSLATIONS.get(text_en, {}).get(language, text_en)


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
    better_label: str
    unit: str = ""
    metric_name: str = ""

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
        VERSION CORRIGÉE : Validation stricte contre valeurs nulles/zéro

        Args:
            results: Liste de 2 dictionnaires contenant:
                - 'sex' ou autre label de comparaison
                - 'data': liste de métriques avec 'value_numeric'

        Returns:
            ComparisonResult avec tous les calculs

        Raises:
            ValueError: Si valeurs manquantes, nulles ou égales à zéro
        """
        if len(results) != 2:
            raise ValueError(
                f"Comparison requires exactly 2 result sets, got {len(results)}"
            )

        # Extraction des valeurs
        value1 = MetricCalculator._extract_primary_value(results[0]["data"])
        value2 = MetricCalculator._extract_primary_value(results[1]["data"])

        # ✅ VALIDATION NIVEAU 1 : Valeurs manquantes
        if value1 is None or value2 is None:
            error_msg = (
                f"Missing values for comparison: "
                f"value1={'None' if value1 is None else value1}, "
                f"value2={'None' if value2 is None else value2}"
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # ✅ VALIDATION NIVEAU 2 : Valeurs nulles ou zéro
        if value1 == 0 or value2 == 0:
            error_msg = (
                f"Cannot compare with zero values: "
                f"value1={value1}, value2={value2}. "
                f"This would cause division by zero in percentage calculations."
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # ✅ VALIDATION NIVEAU 3 : Valeurs négatives (optionnel selon contexte)
        if value1 < 0 or value2 < 0:
            logger.warning(
                f"⚠️ Negative values detected: value1={value1}, value2={value2}. "
                f"Proceeding but this may indicate data issues."
            )

        # Extraction des labels
        label1 = results[0].get("sex") or results[0].get("label", "Value 1")
        label2 = results[1].get("sex") or results[1].get("label", "Value 2")

        # Extraction de l'unité et du nom de métrique
        unit = ""
        metric_name = ""
        if results[0]["data"] and len(results[0]["data"]) > 0:
            unit = results[0]["data"][0].get("unit", "")
            metric_name = results[0]["data"][0].get("metric_name", "")

        # Calculs (maintenant sûrs car valeurs validées)
        absolute_diff = value1 - value2
        relative_diff_pct = ((value1 - value2) / value2) * 100  # Safe: value2 != 0
        ratio = value1 / value2  # Safe: value2 != 0
        higher_label = label1 if value1 > value2 else label2

        # Déterminer qui est "meilleur" selon le type de métrique
        is_lower_better = MetricCalculator._is_lower_better(metric_name)

        if is_lower_better:
            # Pour FCR, mortalité, etc. : le plus BAS est meilleur
            better_label = label1 if value1 < value2 else label2
        else:
            # Pour poids, production, etc. : le plus HAUT est meilleur
            better_label = label1 if value1 > value2 else label2

        logger.info(
            f"✅ Comparison calculated successfully: "
            f"{label1}={value1:.3f} vs {label2}={value2:.3f}, "
            f"diff={absolute_diff:.3f} ({relative_diff_pct:.1f}%), "
            f"ratio={ratio:.3f}, better={better_label} "
            f"(lower_is_better={is_lower_better})"
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
        """
        Extrait la valeur principale des résultats
        VERSION CORRIGÉE : Validation et logs améliorés
        """
        if not data or len(data) == 0:
            logger.warning("No data provided to _extract_primary_value")
            return None

        # Prendre le premier résultat et extraire value_numeric
        first_result = data[0]

        # Si c'est un dict
        if isinstance(first_result, dict):
            value = first_result.get("value_numeric")
            if value is not None:
                logger.debug(f"Extracted value_numeric: {value}")
            else:
                logger.warning(
                    f"value_numeric is None in first result: {first_result.keys()}"
                )
            return value

        # Si c'est un objet avec attribut
        if hasattr(first_result, "value_numeric"):
            value = first_result.value_numeric
            logger.debug(f"Extracted value_numeric from object: {value}")
            return value

        logger.error(f"Cannot extract value_numeric from: {type(first_result)}")
        return None

    @staticmethod
    def calculate_average(values: List[float]) -> float:
        """Calcule la moyenne de valeurs"""
        if not values:
            raise ValueError("Cannot calculate average of empty list")
        return sum(values) / len(values)

    @staticmethod
    def calculate_percentage_change(old_value: float, new_value: float) -> float:
        """
        Calcule le pourcentage de changement
        VERSION CORRIGÉE : Gestion explicite du cas zéro
        """
        if old_value == 0:
            if new_value == 0:
                return 0.0
            else:
                logger.warning(
                    f"Cannot calculate percentage change from zero: "
                    f"old={old_value}, new={new_value}"
                )
                return float("inf") if new_value > 0 else float("-inf")

        return ((new_value - old_value) / old_value) * 100

    @staticmethod
    def format_comparison_text(
        comparison: ComparisonResult,
        metric_name: str = "métrique",
        language: str = "fr",
        terminology: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
    ) -> str:
        """
        Formate le résultat de comparaison en texte naturel
        VERSION CORRIGÉE : Interprétation correcte + contexte enrichi

        Args:
            comparison: Résultat de comparaison
            metric_name: Nom de la métrique
            language: Langue ('fr' ou 'en')
            terminology: Dictionnaire de terminologie
            context: Contexte supplémentaire (age_days, sex, etc.)

        Returns:
            Texte formaté avec interprétation correcte et contexte
        """
        # Extraire le contexte
        age_days = None
        sex = None
        if context:
            age_days = context.get("age_days")
            sex = context.get("sex")

        # Nettoyer le nom de métrique et extraire l'âge si présent
        if "for" in metric_name:
            parts = metric_name.split("for")
            metric_name = parts[0].strip()
            if len(parts) > 1 and not age_days:
                try:
                    age_days = int(parts[1].strip())
                except (ValueError, IndexError):
                    pass

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

        # ===== UNIFIED TEMPLATE WITH DYNAMIC TRANSLATION =====
        unit_display = f" {comparison.unit}" if comparison.unit else ""

        # Construction de l'en-tête avec contexte
        for_label = _translate_metric("For", language)
        header = f"{for_label} **{display_metric_name}**"

        # Ajouter le contexte s'il est disponible
        context_parts = []
        if sex and sex != "as_hatched":
            if sex == "male":
                sex_display = _translate_metric("males", language)
            elif sex == "female":
                sex_display = _translate_metric("females", language)
            else:
                sex_display = sex

            # Format differs by language
            if language == "fr":
                context_parts.append(f"des {sex_display}")
            else:
                context_parts.append(sex_display)
        elif sex == "as_hatched":
            mixed_sexes = _translate_metric("mixed sexes", language)
            context_parts.append(f"({mixed_sexes})")

        if age_days:
            at_label = _translate_metric("at", language)
            days_label = _translate_metric("days", language)
            context_parts.append(f"{at_label} {age_days} {days_label}")

        if context_parts:
            if language == "fr":
                header += f" {' '.join(context_parts)}"
            else:
                header += f" ({', '.join(context_parts)})"

        header += " :\n\n" if language == "fr" else ":\n\n"

        text = header

        # Affichage des valeurs
        separator = " :" if language == "fr" else ":"
        text += f"• **{comparison.label1.capitalize()}**{separator} {comparison.value1:.3f}{unit_display}\n"
        text += f"• **{comparison.label2.capitalize()}**{separator} {comparison.value2:.3f}{unit_display}\n\n"

        diff_label = _translate_metric("Difference", language)
        text += f"**{diff_label}**{separator} {abs(comparison.absolute_difference):.3f}{unit_display}"

        if comparison.relative_difference_pct is not None:
            text += f" ({abs(comparison.relative_difference_pct):.1f}%)"

        text += "\n\n"

        # Interprétation selon le type de métrique
        if is_lower_better:
            # Pour FCR, mortalité : plus bas = meilleur
            if comparison.value1 < comparison.value2:
                better_perf = _translate_metric("shows better performance with a value", language)
                lower_label = _translate_metric("lower", language)
                than_label = _translate_metric("than", language)

                text += f"**{comparison.label1.capitalize()}** {better_perf} "
                text += f"**{abs(comparison.relative_difference_pct):.1f}% {lower_label}** "
                text += f"{than_label} **{comparison.label2}**.\n\n"

                if "fcr" in metric_name.lower() or "conversion" in metric_name.lower():
                    fcr_explanation = _translate_metric(
                        "requires less feed to produce 1 kg of live weight, indicating better feed efficiency.",
                        language
                    )
                    text += f"_{comparison.label1.capitalize()} {fcr_explanation}_"
                else:
                    lower_explanation = _translate_metric(
                        "A lower value indicates better performance for this metric.",
                        language
                    )
                    text += f"_{lower_explanation}_"
            else:
                better_perf = _translate_metric("shows better performance with a value", language)
                lower_label = _translate_metric("lower", language)
                than_label = _translate_metric("than", language)

                text += f"**{comparison.label2.capitalize()}** {better_perf} "
                text += f"**{abs(comparison.relative_difference_pct):.1f}% {lower_label}** "
                text += f"{than_label} **{comparison.label1}**.\n\n"

                if "fcr" in metric_name.lower() or "conversion" in metric_name.lower():
                    fcr_explanation = _translate_metric(
                        "requires less feed to produce 1 kg of live weight, indicating better feed efficiency.",
                        language
                    )
                    text += f"_{comparison.label2.capitalize()} {fcr_explanation}_"
                else:
                    lower_explanation = _translate_metric(
                        "A lower value indicates better performance for this metric.",
                        language
                    )
                    text += f"_{lower_explanation}_"
        else:
            # Pour poids, production : plus haut = meilleur
            shows_value = _translate_metric("shows a value", language)
            higher_label = _translate_metric("higher", language)
            than_label = _translate_metric("than", language)

            if comparison.absolute_difference > 0:
                text += f"**{comparison.label1.capitalize()}** {shows_value} "
                text += f"**{abs(comparison.relative_difference_pct):.1f}% {higher_label}** "
                text += f"{than_label} **{comparison.label2}**."
            else:
                text += f"**{comparison.label2.capitalize()}** {shows_value} "
                text += f"**{abs(comparison.relative_difference_pct):.1f}% {higher_label}** "
                text += f"{than_label} **{comparison.label1}**."

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
    context = {"age_days": 17, "sex": "male"}
    print(
        calculator.format_comparison_text(
            comparison, "feed_conversion_ratio", context=context
        )
    )

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
    print(
        calculator.format_comparison_text(comparison2, "body_weight", context=context)
    )

    print("\n" + "=" * 80)
    print("TEST 3: Zero Value Detection")
    print("=" * 80)

    zero_results = [
        {
            "sex": "Test 1",
            "data": [{"value_numeric": 0, "unit": "g", "metric_name": "test"}],
        },
        {
            "sex": "Test 2",
            "data": [{"value_numeric": 100, "unit": "g", "metric_name": "test"}],
        },
    ]

    try:
        comparison3 = calculator.calculate_comparison(zero_results)
        print("ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"✅ Successfully caught zero value: {e}")
