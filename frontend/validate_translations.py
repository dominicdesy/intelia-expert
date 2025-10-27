#!/usr/bin/env python3
"""
Translation validation script - Compares all language files against FR/EN reference
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Translation validation script - Compares all language files against FR/EN reference
"""
import json
import os
from pathlib import Path
from collections import defaultdict

# Color codes for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def load_json(filepath):
    """Load and parse a JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_all_keys(data, prefix=''):
    """Recursively extract all keys from nested JSON"""
    keys = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(get_all_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys

def main():
    locales_dir = Path(__file__).parent / 'public' / 'locales'

    # Load reference files (FR and EN)
    print(f"{BLUE}Loading reference files...{RESET}")
    fr_data = load_json(locales_dir / 'fr.json')
    en_data = load_json(locales_dir / 'en.json')

    # Get all keys from both references
    fr_keys = get_all_keys(fr_data)
    en_keys = get_all_keys(en_data)

    # Union of both reference sets
    reference_keys = fr_keys | en_keys

    print(f"{GREEN}[OK] French reference: {len(fr_keys)} keys{RESET}")
    print(f"{GREEN}[OK] English reference: {len(en_keys)} keys{RESET}")
    print(f"{GREEN}[OK] Total reference keys: {len(reference_keys)} keys{RESET}\n")

    # Check if FR and EN have differences
    if fr_keys != en_keys:
        print(f"{YELLOW}[WARNING] FR and EN have different keys!{RESET}")
        fr_only = fr_keys - en_keys
        en_only = en_keys - fr_keys
        if fr_only:
            print(f"{YELLOW}  Keys only in FR: {sorted(fr_only)}{RESET}")
        if en_only:
            print(f"{YELLOW}  Keys only in EN: {sorted(en_only)}{RESET}")
        print()

    # Language files to check (excluding references and stripe_keys files)
    language_files = {
        'ar': 'Arabic',
        'de': 'German',
        'es': 'Spanish',
        'hi': 'Hindi',
        'id': 'Indonesian',
        'it': 'Italian',
        'ja': 'Japanese',
        'nl': 'Dutch',
        'pl': 'Polish',
        'pt': 'Portuguese',
        'th': 'Thai',
        'tr': 'Turkish',
        'vi': 'Vietnamese',
        'zh': 'Chinese'
    }

    # Track results
    results = {}
    all_missing = defaultdict(list)

    print(f"{BLUE}Validating language files...{RESET}\n")

    for lang_code, lang_name in sorted(language_files.items()):
        filepath = locales_dir / f'{lang_code}.json'

        if not filepath.exists():
            print(f"{RED}[MISSING] {lang_name} ({lang_code}.json): FILE NOT FOUND{RESET}")
            continue

        # Load and get keys
        lang_data = load_json(filepath)
        lang_keys = get_all_keys(lang_data)

        # Find missing keys
        missing = reference_keys - lang_keys

        results[lang_code] = {
            'name': lang_name,
            'total_keys': len(lang_keys),
            'missing_keys': sorted(missing),
            'missing_count': len(missing)
        }

        # Track which languages are missing each key
        for key in missing:
            all_missing[key].append(lang_code)

        # Display result
        if missing:
            print(f"{RED}[ERROR] {lang_name} ({lang_code}): {len(missing)} missing keys{RESET}")
        else:
            print(f"{GREEN}[OK] {lang_name} ({lang_code}): Complete! ({len(lang_keys)} keys){RESET}")

    # Summary report
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}SUMMARY REPORT{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

    complete_languages = [lang for lang, data in results.items() if data['missing_count'] == 0]
    incomplete_languages = [lang for lang, data in results.items() if data['missing_count'] > 0]

    print(f"{GREEN}Complete languages: {len(complete_languages)}{RESET}")
    if complete_languages:
        for lang in complete_languages:
            print(f"  [OK] {results[lang]['name']} ({lang})")

    print(f"\n{RED}Incomplete languages: {len(incomplete_languages)}{RESET}")
    if incomplete_languages:
        for lang in incomplete_languages:
            print(f"  [ERROR] {results[lang]['name']} ({lang}): {results[lang]['missing_count']} missing")

    # Detailed missing keys report
    if all_missing:
        print(f"\n{BLUE}{'='*80}{RESET}")
        print(f"{BLUE}MISSING KEYS BREAKDOWN{RESET}")
        print(f"{BLUE}{'='*80}{RESET}\n")

        # Group by how many languages are missing each key
        for key in sorted(all_missing.keys()):
            langs_missing = all_missing[key]
            count = len(langs_missing)

            if count == len(language_files):
                color = RED
                status = "MISSING IN ALL LANGUAGES"
            elif count > len(language_files) / 2:
                color = RED
                status = f"Missing in {count}/{len(language_files)} languages"
            else:
                color = YELLOW
                status = f"Missing in {count}/{len(language_files)} languages"

            print(f"{color}{key}: {status}{RESET}")
            print(f"  Languages: {', '.join(sorted(langs_missing))}")

    # Save detailed report to file
    report_file = locales_dir.parent.parent / 'translation_validation_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'reference_key_count': len(reference_keys),
            'reference_keys': sorted(reference_keys),
            'results': results,
            'missing_keys_by_key': {k: v for k, v in all_missing.items()},
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{GREEN}Detailed report saved to: {report_file}{RESET}")

if __name__ == '__main__':
    main()
