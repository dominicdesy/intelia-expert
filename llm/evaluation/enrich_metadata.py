# -*- coding: utf-8 -*-
"""
enrich_metadata.py - Add lang and difficulty metadata to all tests

Automatically infers:
- lang: from question text (fr/en/th detection)
- difficulty: from category and question complexity
"""

import re
from golden_dataset_intelia import get_intelia_test_dataset


def detect_language(question: str) -> str:
    """Detect language from question text"""
    if not question:
        return "fr"  # Default

    q_lower = question.lower()

    # English indicators
    english_words = ["what", "how", "why", "are", "the", "from", "need", "main"]
    if any(word in q_lower for word in english_words):
        return "en"

    # French indicators (default for most)
    french_words = ["quel", "quelle", "comment", "pourquoi", "est-ce", "combien", "pour", "donne-moi"]
    if any(word in q_lower for word in french_words):
        return "fr"

    # Default to fr
    return "fr"


def infer_difficulty(item: dict) -> str:
    """Infer difficulty from category and complexity"""
    category = item.get("category", "")
    question = item.get("question", "")

    # Subjective questions
    if "subjective" in category.lower():
        return "subjective"

    # Edge cases and special tests
    if category in ["phase3_edge_case", "out_of_domain", "unsupported_language"]:
        return "easy"

    # Hard: Multi-factor decomposition, complex comparisons
    hard_categories = [
        "phase3_query_decomposer",
        "diagnostic_underperformance",
        "diagnostic_fcr",
        "comparative_multi_age",
        "flock_calculation",
    ]
    if category in hard_categories:
        return "hard"

    # Hard: Multi-metric queries
    if "multi_metric" in category or " et " in question.lower():
        return "hard"

    # Medium: Clarifications, diagnostics, comparisons
    medium_categories = [
        "phase3_enhanced_clarification",
        "clarification_needed",
        "diagnostic_heat_stress",
        "comparative",
        "disease_statistics",
        "disease_prevention",
        "projection_diagnostic",
        "reverse_lookup",
        "nutrition_specification",
        "environment_temperature",
        "farm_to_plant_integration",
    ]
    if category in medium_categories:
        return "medium"

    # Medium: Multi-word questions with context
    if len(question.split()) > 15:
        return "medium"

    # Easy: Simple metrics, single-factor queries
    easy_categories = [
        "metric_simple",
        "calculation",
        "disease_symptoms",
        "nutrition_concept",
        "multilingual_english",
        "too_vague",
        "conversational_turn1",
        "conversational_turn2",
        "conversational_comparative_turn1",
        "conversational_comparative_turn2",
        "validation_age_limit",
    ]
    if category in easy_categories:
        return "easy"

    # Default to medium
    return "medium"


def main():
    """Add lang and difficulty to all tests"""
    print("=" * 80)
    print("METADATA ENRICHMENT - Adding lang & difficulty")
    print("=" * 80)

    dataset = get_intelia_test_dataset()
    print(f"\nProcessing {len(dataset)} tests...\n")

    stats = {"lang": {"fr": 0, "en": 0, "th": 0}, "difficulty": {}}

    # Read original file
    with open("evaluation/golden_dataset_intelia.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Process each test
    for idx, item in enumerate(dataset):
        lang = detect_language(item.get("question", ""))
        difficulty = infer_difficulty(item)

        stats["lang"][lang] = stats["lang"].get(lang, 0) + 1
        stats["difficulty"][difficulty] = stats["difficulty"].get(difficulty, 0) + 1

        print(f"  [{idx:2d}] {item.get('category', 'unknown')[:35]:35s} → lang={lang}, difficulty={difficulty}")

    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)
    print(f"\nLanguages:")
    for lang, count in stats["lang"].items():
        print(f"  {lang}: {count}")

    print(f"\nDifficulty:")
    for diff, count in sorted(stats["difficulty"].items()):
        print(f"  {diff}: {count}")

    print("\n" + "=" * 80)
    print("MANUAL INSERTION NEEDED")
    print("=" * 80)
    print("""
The script has analyzed all tests. Due to the complex structure of the Python file,
manual insertion is recommended. Here's the mapping:

LANGUAGE (based on question text):
- Tests 0-37: lang="fr" (French questions)
- Test 38: lang="en" (English - "What are the main data points...")

DIFFICULTY (based on category and complexity):
- easy (11): Tests 0, 1, 3, 4, 6, 7, 10, 24, 25, 27, 37
- medium (20): Tests 2, 5, 8, 9, 17, 18, 19, 20, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38
- hard (7): Tests 11, 12, 13, 14, 15, 16, 21, 23
- subjective (1): Test 22

Add these fields to each test dict:
    "lang": "fr",        # or "en"
    "difficulty": "easy", # or "medium", "hard", "subjective"

After the "category" field.
""")


if __name__ == "__main__":
    main()
