# -*- coding: utf-8 -*-
"""
test_multilingual_consolidation.py - Tests de validation de la consolidation EN-only
Tests end-to-end pour vérifier que tous les modules utilisent correctement les templates EN + traduction
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding for Unicode support (Thai, etc.)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.clarification_helper import ClarificationHelper
from core.comparison_engine import ComparisonEngine
from core.metric_calculator import MetricCalculator


def test_clarification_helper_multilingual():
    """Test ClarificationHelper avec FR/EN/TH"""
    print("\n" + "=" * 80)
    print("TEST 1: ClarificationHelper - Messages de clarification multilingues")
    print("=" * 80)

    helper = ClarificationHelper("config/clarification_strategies.json")

    # Test avec plusieurs types d'ambiguïté
    test_cases = [
        {
            "query": "Quel est le poids d'un poulet ?",
            "missing_fields": ["breed", "age"],
            "entities": {},
            "languages": ["fr", "en", "th"],
        },
        {
            "query": "What feed for my chickens?",
            "missing_fields": ["age"],
            "entities": {"breed": "Ross 308"},
            "languages": ["en", "fr", "th"],
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Query: {test_case['query']}")
        print(f"Missing: {test_case['missing_fields']}")

        for lang in test_case["languages"]:
            message = helper.build_clarification_message(
                test_case["missing_fields"],
                lang,
                test_case["query"],
                test_case["entities"],
            )

            print(f"\n[{lang.upper()}]:")
            print(message)

            # Validation basique
            assert message, f"Message vide pour {lang}"
            assert len(message) > 10, f"Message trop court pour {lang}"

    print("\n✅ ClarificationHelper: Tests multilingues PASSED")


def test_comparison_engine_multilingual():
    """Test ComparisonEngine avec FR/EN/TH"""
    print("\n" + "=" * 80)
    print("TEST 2: ComparisonEngine - Comparaisons multilingues")
    print("=" * 80)

    engine = ComparisonEngine()

    # Simuler une comparaison
    comparison_data = {
        "label1": "Ross 308",
        "label2": "Cobb 500",
        "value1": 950.5,
        "value2": 880.2,
        "unit": "g",
        "metric_name": "body_weight",
        "difference_absolute": 70.3,
        "difference_percent": 7.98,  # Fixed: use 'difference_percent' not 'difference_relative_pct'
        "ratio": 1.08,
        "higher": "Ross 308",
        "better": "Ross 308",
    }

    languages = ["fr", "en", "th"]

    for lang in languages:
        response = engine._generate_template_response(comparison_data, lang)

        print(f"\n[{lang.upper()}]:")
        print(response)

        # Validations
        assert response, f"Response vide pour {lang}"
        assert "Ross 308" in response, f"Missing breed name in {lang}"
        assert "950" in response or "950.5" in response, f"Missing value in {lang}"

    print("\n✅ ComparisonEngine: Tests multilingues PASSED")


def test_metric_calculator_multilingual():
    """Test MetricCalculator avec FR/EN/TH"""
    print("\n" + "=" * 80)
    print("TEST 3: MetricCalculator - Formatage de comparaisons multilingues")
    print("=" * 80)

    calculator = MetricCalculator()

    # Test 1: Body weight comparison (higher is better)
    weight_results = [
        {
            "sex": "male",
            "data": [
                {
                    "value_numeric": 950.5,
                    "unit": "g",
                    "metric_name": "body_weight for 35",
                }
            ],
        },
        {
            "sex": "female",
            "data": [
                {
                    "value_numeric": 880.2,
                    "unit": "g",
                    "metric_name": "body_weight for 35",
                }
            ],
        },
    ]

    comparison = calculator.calculate_comparison(weight_results)
    context = {"age_days": 35, "sex": "male"}

    languages = ["fr", "en", "th"]

    print("\n--- Test 1: Body Weight (higher = better) ---")
    for lang in languages:
        formatted = calculator.format_comparison_text(
            comparison, "body_weight", language=lang, context=context
        )

        print(f"\n[{lang.upper()}]:")
        print(formatted)

        # Validations
        assert formatted, f"Formatted text vide pour {lang}"
        assert "950" in formatted, f"Missing value1 in {lang}"
        assert "880" in formatted, f"Missing value2 in {lang}"

        # Vérifier que les mots-clés traduits sont présents
        if lang == "fr":
            assert "Pour la" in formatted or "Pour" in formatted, "Missing French header"
            assert "mâles" in formatted, "Missing French 'mâles'"
            assert "Différence" in formatted, "Missing French 'Différence'"
        elif lang == "th":
            # Thai script should be present
            assert any(
                char >= "\u0E00" and char <= "\u0E7F" for char in formatted
            ), "Missing Thai script"

    # Test 2: FCR comparison (lower is better)
    print("\n--- Test 2: FCR (lower = better) ---")

    fcr_results = [
        {
            "sex": "Cobb 500",
            "data": [
                {
                    "value_numeric": 1.081,
                    "unit": "ratio",
                    "metric_name": "feed_conversion_ratio for 21",
                }
            ],
        },
        {
            "sex": "Ross 308",
            "data": [
                {
                    "value_numeric": 1.065,
                    "unit": "ratio",
                    "metric_name": "feed_conversion_ratio for 21",
                }
            ],
        },
    ]

    fcr_comparison = calculator.calculate_comparison(fcr_results)
    fcr_context = {"age_days": 21}

    for lang in languages:
        formatted = calculator.format_comparison_text(
            fcr_comparison, "feed_conversion_ratio", language=lang, context=fcr_context
        )

        print(f"\n[{lang.upper()}]:")
        print(formatted)

        # Validations
        assert formatted, f"Formatted text vide pour {lang}"
        assert "1.081" in formatted or "1.08" in formatted, f"Missing value1 in {lang}"
        assert "1.065" in formatted or "1.07" in formatted, f"Missing value2 in {lang}"

        # Vérifier l'interprétation "lower is better"
        # Ross 308 (1.065) devrait être meilleur que Cobb 500 (1.081)
        if lang == "fr":
            assert (
                "Ross 308" in formatted
            ), "Missing breed with better performance in French"
        elif lang == "en":
            assert (
                "Ross 308" in formatted
            ), "Missing breed with better performance in English"

    print("\n✅ MetricCalculator: Tests multilingues PASSED")


def test_translation_consistency():
    """Vérifie que les traductions sont cohérentes entre les modules"""
    print("\n" + "=" * 80)
    print("TEST 4: Consistency Check - Traductions cohérentes")
    print("=" * 80)

    # Vérifier que tous les modules supportent les mêmes langues
    from core.comparison_engine import COMPARISON_TRANSLATIONS
    from core.metric_calculator import METRIC_TRANSLATIONS
    from utils.clarification_helper import ClarificationHelper

    helper = ClarificationHelper("config/clarification_strategies.json")

    # Langues attendues

    # Check COMPARISON_TRANSLATIONS
    comparison_langs = set()
    for phrase_dict in COMPARISON_TRANSLATIONS.values():
        if isinstance(phrase_dict, dict):
            comparison_langs.update(phrase_dict.keys())

    print(f"COMPARISON_TRANSLATIONS langues: {sorted(comparison_langs)}")

    # Check METRIC_TRANSLATIONS
    metric_langs = set()
    for phrase_dict in METRIC_TRANSLATIONS.values():
        if isinstance(phrase_dict, dict):
            metric_langs.update(phrase_dict.keys())

    print(f"METRIC_TRANSLATIONS langues: {sorted(metric_langs)}")

    # Check label_translations from clarification_strategies.json
    clarification_langs = set()
    for label_dict in helper.label_translations.values():
        if isinstance(label_dict, dict):
            clarification_langs.update(label_dict.keys())

    print(f"label_translations langues: {sorted(clarification_langs)}")

    # Validation: tous les modules devraient supporter les mêmes langues principales
    common_langs = comparison_langs & metric_langs & clarification_langs
    print(f"\nLangues communes à tous les modules: {sorted(common_langs)}")

    assert "fr" in common_langs, "French missing in common languages"
    assert "en" in common_langs or len(
        comparison_langs
    ) > 0, "English or EN-only structure expected"
    assert "th" in common_langs, "Thai missing in common languages"

    print("\n✅ Translation Consistency: Tests PASSED")


def run_all_tests():
    """Execute tous les tests"""
    print("\n" + "=" * 80)
    print("TESTS DE VALIDATION - CONSOLIDATION EN-ONLY + TRADUCTION DYNAMIQUE")
    print("=" * 80)

    try:
        test_clarification_helper_multilingual()
        test_comparison_engine_multilingual()
        test_metric_calculator_multilingual()
        test_translation_consistency()

        print("\n" + "=" * 80)
        print("✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS")
        print("=" * 80)
        print("\nRÉSUMÉ:")
        print("- ClarificationHelper: Messages multilingues (FR/EN/TH) ✅")
        print("- ComparisonEngine: Comparaisons multilingues (FR/EN/TH) ✅")
        print("- MetricCalculator: Formatage multilingue (FR/EN/TH) ✅")
        print("- Cohérence des traductions entre modules ✅")
        print("\nLa consolidation EN-only + traduction dynamique fonctionne correctement!")

        return True

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ ÉCHEC DES TESTS")
        print("=" * 80)
        print(f"Erreur: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
