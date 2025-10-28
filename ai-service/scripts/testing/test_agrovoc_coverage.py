# -*- coding: utf-8 -*-
"""
Test AGROVOC language coverage for Intelia Expert's 12 supported languages
"""

import requests
import sys

# Your 12 supported languages
SUPPORTED_LANGUAGES = {
    "fr": "French",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "hi": "Hindi",
    "id": "Indonesian",
    "th": "Thai",
    "zh": "Chinese",
}

print("Testing AGROVOC language coverage...\n")
print("=" * 80)

# Test a simple poultry term in each language
# AGROVOC concept URI for "poultry": http://aims.fao.org/aos/agrovoc/c_6105

sparql_endpoint = "https://agrovoc.fao.org/sparql"

results_summary = {"supported": [], "not_supported": [], "errors": []}

for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
    # Query for 'poultry' concept in this language
    query = f"""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?label
    WHERE {{
        <http://aims.fao.org/aos/agrovoc/c_6105> skos:prefLabel ?label .
        FILTER(LANG(?label) = "{lang_code}")
    }}
    LIMIT 1
    """

    try:
        response = requests.get(
            sparql_endpoint, params={"query": query, "format": "json"}, timeout=10
        )

        if response.status_code == 200:
            results = response.json()
            bindings = results["results"]["bindings"]

            if bindings:
                term = bindings[0]["label"]["value"]
                # Use ASCII-safe output for non-Latin scripts
                try:
                    print(f'[OK] {lang_name:15} ({lang_code}): "{term}"')
                except UnicodeEncodeError:
                    print(f"[OK] {lang_name:15} ({lang_code}): <non-Latin script>")
                results_summary["supported"].append((lang_code, lang_name, term))
            else:
                print(f"[NO] {lang_name:15} ({lang_code}): NOT FOUND")
                results_summary["not_supported"].append((lang_code, lang_name))
        else:
            print(
                f"[ER] {lang_name:15} ({lang_code}): API ERROR ({response.status_code})"
            )
            results_summary["errors"].append(
                (lang_code, lang_name, f"HTTP {response.status_code}")
            )

    except Exception as e:
        error_msg = str(e)[:50]
        print(f"[ER] {lang_name:15} ({lang_code}): {error_msg}")
        results_summary["errors"].append((lang_code, lang_name, error_msg))

print("=" * 80)
print("\nSUMMARY:")
print(f'  Supported languages: {len(results_summary["supported"])}/12')
print(f'  Not supported: {len(results_summary["not_supported"])}/12')
print(f'  Errors: {len(results_summary["errors"])}/12')

if results_summary["not_supported"]:
    print("\nLanguages NOT supported by AGROVOC:")
    for lang_code, lang_name in results_summary["not_supported"]:
        print(f"  - {lang_name} ({lang_code})")

if results_summary["errors"]:
    print("\nLanguages with errors:")
    for lang_code, lang_name, error in results_summary["errors"]:
        print(f"  - {lang_name} ({lang_code}): {error}")

# Test coverage percentage
coverage = len(results_summary["supported"]) / len(SUPPORTED_LANGUAGES) * 100
print(f"\nAGROVOC Coverage: {coverage:.1f}%")

if coverage >= 90:
    print("Result: EXCELLENT - AGROVOC covers nearly all languages")
elif coverage >= 70:
    print("Result: GOOD - AGROVOC covers most languages, need fallback for some")
elif coverage >= 50:
    print("Result: MODERATE - AGROVOC covers half, significant fallback needed")
else:
    print("Result: POOR - AGROVOC not suitable, use alternative")

sys.exit(0)
