# -*- coding: utf-8 -*-
"""
auto_add_metadata.py - Automatically add lang and difficulty to golden_dataset_intelia.py

Uses regex to insert metadata after "category" field in each test.
"""

import re
import shutil
from pathlib import Path


# Metadata mapping (test index → [lang, difficulty])
METADATA_MAP = {
    # Easy tests (simple metrics, single queries)
    0: ["fr", "easy"],    # calculation
    1: ["fr", "easy"],    # disease_statistics
    3: ["fr", "easy"],    # out_of_domain
    4: ["fr", "easy"],    # disease_symptoms
    6: ["fr", "easy"],    # multilingual_english
    7: ["fr", "easy"],    # too_vague
    10: ["fr", "easy"],   # metric_simple
    24: ["fr", "easy"],   # validation_age_limit
    25: ["fr", "easy"],   # conversational_turn1
    27: ["fr", "easy"],   # conversational_comparative_turn1
    37: ["fr", "easy"],   # phase3_edge_case (empty query)

    # Medium tests (clarifications, diagnostics, comparisons)
    2: ["fr", "medium"],  # disease_prevention
    5: ["fr", "medium"],  # clarification_needed
    8: ["fr", "medium"],  # unsupported_language
    9: ["fr", "medium"],  # comparative
    17: ["fr", "medium"], # nutrition_specification
    18: ["fr", "medium"], # nutrition_concept
    19: ["fr", "medium"], # environment_temperature
    20: ["fr", "medium"], # diagnostic_heat_stress
    26: ["fr", "medium"], # conversational_turn2
    28: ["fr", "medium"], # conversational_comparative_turn2
    29: ["fr", "medium"], # phase3_query_decomposer (multi-factor)
    30: ["fr", "medium"], # phase3_query_decomposer (comma list)
    31: ["fr", "medium"], # phase3_query_decomposer (compare)
    32: ["fr", "medium"], # phase3_enhanced_clarification (nutrition)
    33: ["fr", "medium"], # phase3_enhanced_clarification (health)
    34: ["fr", "medium"], # phase3_enhanced_clarification (environment)
    35: ["fr", "medium"], # phase3_enhanced_clarification (management)
    36: ["fr", "medium"], # phase3_enhanced_clarification (genetics)
    38: ["en", "medium"], # farm_to_plant_integration (English!)

    # Hard tests (complex calculations, multi-factor, multi-age)
    11: ["fr", "hard"],   # flock_calculation (10k birds)
    12: ["fr", "hard"],   # reverse_lookup
    13: ["fr", "hard"],   # projection_diagnostic
    14: ["fr", "hard"],   # diagnostic_underperformance
    15: ["fr", "hard"],   # diagnostic_fcr
    16: ["fr", "hard"],   # phase3_enhanced_clarification (treatment_protocol)
    21: ["fr", "hard"],   # multi_metric (3 metrics at once)
    23: ["fr", "hard"],   # comparative_multi_age (3 ages × 2 breeds)

    # Subjective test
    22: ["fr", "subjective"],  # subjective_comparison (Ross vs Cobb)
}


def add_metadata_to_file(input_file: Path, output_file: Path):
    """Add lang and difficulty metadata to all tests"""

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to find category lines
    # Matches: "category": "...",
    category_pattern = re.compile(r'("category":\s*"[^"]+",)')

    test_idx = 0
    last_pos = 0
    output_parts = []

    for match in category_pattern.finditer(content):
        match_start, match_end = match.span(1)

        # Add content before this match
        output_parts.append(content[last_pos:match_end])

        # Get metadata for this test
        if test_idx in METADATA_MAP:
            lang, difficulty = METADATA_MAP[test_idx]
            indent = " " * 12  # Match indentation in file

            # Add lang and difficulty right after category
            metadata_lines = f'\n{indent}"lang": "{lang}",\n{indent}"difficulty": "{difficulty}",'
            output_parts.append(metadata_lines)

            print(f"  [{ test_idx:2d}] Added: lang={lang}, difficulty={difficulty}")
        else:
            print(f"  [{test_idx:2d}] WARNING: No metadata mapping found, skipping")

        last_pos = match_end
        test_idx += 1

    # Add remaining content
    output_parts.append(content[last_pos:])

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("".join(output_parts))

    print(f"\n✅ Successfully added metadata to {test_idx} tests")
    print(f"📄 Output written to: {output_file}")


def main():
    """Main execution"""
    print("=" * 80)
    print("AUTO METADATA ENRICHMENT")
    print("=" * 80)

    input_file = Path("evaluation/golden_dataset_intelia.py")
    backup_file = Path("evaluation/golden_dataset_intelia.py.backup")
    output_file = Path("evaluation/golden_dataset_intelia_enriched.py")

    # Create backup
    print(f"\n📦 Creating backup: {backup_file}")
    shutil.copy2(input_file, backup_file)

    # Process file
    print(f"\n🔄 Processing: {input_file}\n")
    add_metadata_to_file(input_file, output_file)

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print(f"""
1. Review the enriched file: {output_file}
2. If correct, replace original:
   cp {output_file} {input_file}
3. If issues, restore backup:
   cp {backup_file} {input_file}
""")


if __name__ == "__main__":
    main()
