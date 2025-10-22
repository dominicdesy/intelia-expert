#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify acronym loading from poultry_terminology.json
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add LLM directory to path
llm_dir = Path(__file__).parent / "llm"
sys.path.insert(0, str(llm_dir))

# Import the config module which loads acronyms
from security.ood.config import ACRONYM_EXPANSIONS

def test_acronym_loading():
    """Test that acronyms are loaded correctly from JSON"""

    print("=" * 80)
    print("ACRONYM EXPANSION TEST")
    print("=" * 80)
    print(f"\nTotal acronyms loaded: {len(ACRONYM_EXPANSIONS)}")
    print("\n" + "-" * 80)

    # Test some expected acronyms
    test_cases = [
        ("fcr", "feed conversion ratio"),
        ("ic", "indice"),  # Should contain "indice"
        ("adg", "gain"),   # Should contain "gain" or "average daily gain"
        ("bw", "poids vif"),
        ("epef", "production efficiency factor"),
        ("me", "metabolizable energy"),
        ("cp", "crude protein"),
        ("aa", "amino"),
        ("nd", "newcastle"),
        ("ai", "influenza"),
        ("ibd", "gumboro"),
        ("cfu", "colony forming unit"),
        ("eds", "egg drop syndrome"),
        ("elisa", "enzyme"),
        ("po", "per os"),
        ("im", "intramuscular"),
    ]

    print("\n✓ EXPECTED ACRONYMS (from terminology JSON):")
    print("-" * 80)

    found_count = 0
    missing_acronyms = []

    for acronym, expected_substring in test_cases:
        if acronym in ACRONYM_EXPANSIONS:
            expansion = ACRONYM_EXPANSIONS[acronym]
            if expected_substring.lower() in expansion.lower():
                print(f"  ✓ {acronym.upper():8} → {expansion}")
                found_count += 1
            else:
                print(f"  ⚠ {acronym.upper():8} → {expansion} (expected '{expected_substring}')")
                found_count += 1
        else:
            print(f"  ✗ {acronym.upper():8} → NOT FOUND")
            missing_acronyms.append(acronym)

    print("\n" + "-" * 80)
    print(f"Found: {found_count}/{len(test_cases)} expected acronyms")

    if missing_acronyms:
        print(f"\n⚠ Missing acronyms: {', '.join(missing_acronyms)}")

    # Show all loaded acronyms
    print("\n" + "=" * 80)
    print("ALL LOADED ACRONYMS:")
    print("=" * 80)

    for acronym, expansion in sorted(ACRONYM_EXPANSIONS.items()):
        print(f"  {acronym.upper():10} → {expansion}")

    print("\n" + "=" * 80)
    print(f"TOTAL: {len(ACRONYM_EXPANSIONS)} acronyms loaded successfully")
    print("=" * 80)

    # Test query normalization simulation
    print("\n" + "=" * 80)
    print("QUERY NORMALIZATION EXAMPLES:")
    print("=" * 80)

    test_queries = [
        "What is the FCR for Ross 308?",
        "Comment améliorer l'IC?",
        "Quel est le GMQ optimal?",
        "ADG vs FCR comparison",
        "Quelle est la dose PO recommandée?",
        "ELISA test for ND and AI",
        "BW at 35 days",
        "EPEF calculation method",
    ]

    for query in test_queries:
        normalized = query.lower()
        expanded_terms = []

        for acronym, expansion in ACRONYM_EXPANSIONS.items():
            if acronym in normalized:
                expanded_terms.append(f"{acronym.upper()}→{expansion}")

        if expanded_terms:
            print(f"\n  Query: {query}")
            print(f"  Expanded: {', '.join(expanded_terms)}")

    print("\n" + "=" * 80)

    return len(missing_acronyms) == 0

if __name__ == "__main__":
    success = test_acronym_loading()
    sys.exit(0 if success else 1)
