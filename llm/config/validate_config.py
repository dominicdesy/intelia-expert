#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validation script for centralized configuration files
Checks JSON structure, required fields, and data integrity
"""
import json
import os
import sys

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
ERRORS = []
WARNINGS = []


def error(msg):
    ERRORS.append(f"ERROR: {msg}")
    print(f"[ERROR] {msg}")


def warning(msg):
    WARNINGS.append(f"WARNING: {msg}")
    print(f"[WARN] {msg}")


def success(msg):
    print(f"[OK] {msg}")


def validate_json_file(filename):
    """Validate that file exists and is valid JSON"""
    filepath = os.path.join(CONFIG_DIR, filename)

    if not os.path.exists(filepath):
        error(f"{filename} not found")
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        success(f"{filename} - Valid JSON")
        return data
    except json.JSONDecodeError as e:
        error(f"{filename} - Invalid JSON: {e}")
        return None


def validate_veterinary_terms(data):
    """Validate veterinary_terms.json structure"""
    print("\n" + "=" * 80)
    print("VALIDATING veterinary_terms.json")
    print("=" * 80)

    if not data:
        return

    # Check metadata
    if "metadata" not in data:
        error("Missing 'metadata' section")
    else:
        meta = data["metadata"]
        required_meta = ["version", "total_terms", "languages_supported"]
        for field in required_meta:
            if field not in meta:
                warning(f"Missing metadata.{field}")

    # Check categories
    expected_categories = [
        "diseases",
        "symptoms",
        "treatments",
        "pathogens",
        "diagnosis",
        "veterinary_questions",
        "health_issues",
    ]

    found_categories = [k for k in data.keys() if k != "metadata"]

    for cat in expected_categories:
        if cat not in data:
            warning(f"Missing category: {cat}")
        else:
            # Check languages in category
            if not isinstance(data[cat], dict):
                error(f"Category {cat} is not a dictionary")
                continue

            langs = list(data[cat].keys())
            if not langs:
                warning(f"Category {cat} has no languages")

            # Check for empty term lists
            for lang, terms in data[cat].items():
                if not isinstance(terms, list):
                    error(f"Category {cat}.{lang} is not a list")
                elif len(terms) == 0:
                    warning(f"Category {cat}.{lang} is empty")

    success(f"Found {len(found_categories)} categories")


def validate_breeds_mapping(data):
    """Validate breeds_mapping.json structure"""
    print("\n" + "=" * 80)
    print("VALIDATING breeds_mapping.json")
    print("=" * 80)

    if not data:
        return

    # Check metadata
    if "metadata" not in data:
        warning("Missing 'metadata' section")

    # Check species
    species_categories = ["broilers", "layers", "breeders"]

    for species in species_categories:
        if species not in data:
            error(f"Missing species category: {species}")
            continue

        breeds = data[species]
        if not isinstance(breeds, dict):
            error(f"Species {species} is not a dictionary")
            continue

        # Validate each breed
        for breed_id, breed_info in breeds.items():
            required_fields = ["canonical_name", "aliases", "supplier", "db_name"]

            for field in required_fields:
                if field not in breed_info:
                    error(f"Breed {species}.{breed_id} missing required field: {field}")

            # Check aliases is a list
            if "aliases" in breed_info:
                if not isinstance(breed_info["aliases"], list):
                    error(f"Breed {species}.{breed_id}.aliases is not a list")
                elif len(breed_info["aliases"]) == 0:
                    warning(f"Breed {species}.{breed_id} has no aliases")

            # Species-specific validation
            if species == "broilers" and "typical_market_age_days" not in breed_info:
                warning(f"Broiler {breed_id} missing typical_market_age_days")

            if species == "layers" and "egg_color" not in breed_info:
                warning(f"Layer {breed_id} missing egg_color")

        success(f"Found {len(breeds)} {species}")


def validate_metrics_normalization(data):
    """Validate metrics_normalization.json structure"""
    print("\n" + "=" * 80)
    print("VALIDATING metrics_normalization.json")
    print("=" * 80)

    if not data:
        return

    # Check metadata
    if "metadata" not in data:
        warning("Missing 'metadata' section")

    metrics = [k for k in data.keys() if k != "metadata"]

    required_fields = ["canonical", "category", "unit", "translations"]
    valid_categories = ["performance", "health", "nutrition", "environment", "carcass"]

    for metric_id in metrics:
        metric = data[metric_id]

        # Check required fields
        for field in required_fields:
            if field not in metric:
                error(f"Metric {metric_id} missing required field: {field}")

        # Validate category
        if "category" in metric:
            if metric["category"] not in valid_categories:
                warning(
                    f"Metric {metric_id} has unknown category: {metric['category']}"
                )

        # Validate translations
        if "translations" in metric:
            trans = metric["translations"]
            if not isinstance(trans, dict):
                error(f"Metric {metric_id}.translations is not a dictionary")
            else:
                expected_langs = [
                    "fr",
                    "en",
                    "es",
                    "de",
                    "it",
                    "pt",
                    "nl",
                    "pl",
                    "id",
                    "hi",
                    "th",
                    "zh",
                ]
                missing_langs = [lang for lang in expected_langs if lang not in trans]

                if missing_langs:
                    warning(
                        f"Metric {metric_id} missing translations for: {', '.join(missing_langs)}"
                    )

                # Check each language has terms
                for lang, terms in trans.items():
                    if not isinstance(terms, list):
                        error(f"Metric {metric_id}.translations.{lang} is not a list")
                    elif len(terms) == 0:
                        warning(f"Metric {metric_id}.translations.{lang} is empty")

        # Check typical_range if present
        if "typical_range" in metric:
            ranges = metric["typical_range"]
            if not isinstance(ranges, dict):
                error(f"Metric {metric_id}.typical_range is not a dictionary")
            else:
                for range_name, range_vals in ranges.items():
                    if not isinstance(range_vals, list) or len(range_vals) != 2:
                        error(
                            f"Metric {metric_id}.typical_range.{range_name} should be [min, max]"
                        )

    success(f"Found {len(metrics)} metrics")


def main():
    print("=" * 80)
    print("CENTRALIZED CONFIG VALIDATION")
    print("=" * 80)

    # Validate each file
    vet_data = validate_json_file("veterinary_terms.json")
    validate_veterinary_terms(vet_data)

    breeds_data = validate_json_file("breeds_mapping.json")
    validate_breeds_mapping(breeds_data)

    metrics_data = validate_json_file("metrics_normalization.json")
    validate_metrics_normalization(metrics_data)

    # Final report
    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)

    if ERRORS:
        print(f"\n[ERROR] ERRORS: {len(ERRORS)}")
        for err in ERRORS:
            print(f"  {err}")

    if WARNINGS:
        print(f"\n[WARN] WARNINGS: {len(WARNINGS)}")
        for warn in WARNINGS:
            print(f"  {warn}")

    if not ERRORS and not WARNINGS:
        print("\n[OK] ALL VALIDATION CHECKS PASSED")
        print("   Configuration files are valid and complete")
    elif not ERRORS:
        print(f"\n[OK] NO ERRORS (but {len(WARNINGS)} warnings)")
        print("   Configuration files are valid")
    else:
        print("\n[ERROR] VALIDATION FAILED")
        print(f"   {len(ERRORS)} errors, {len(WARNINGS)} warnings")
        sys.exit(1)

    print("=" * 80)


if __name__ == "__main__":
    main()
