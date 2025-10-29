#!/usr/bin/env python3
"""
Extract all translation keys from JSON files and update TypeScript interface
"""

import json
from pathlib import Path


def flatten_json(data, parent_key=''):
    """Flatten nested JSON to dot notation keys"""
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_json(v, new_key))
        else:
            items.append(new_key)
    return items


def extract_keys_from_file(file_path):
    """Extract all keys from a translation file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(flatten_json(data))


def main():
    """Extract all translation keys"""
    frontend_dir = Path(__file__).parent / 'frontend'
    locales_dir = frontend_dir / 'public' / 'locales'
    en_file = locales_dir / 'en.json'

    if not en_file.exists():
        print(f"[ERROR] {en_file} not found")
        return

    print(f"[INFO] Extracting keys from {en_file}")
    all_keys = extract_keys_from_file(en_file)

    # Sort keys
    sorted_keys = sorted(all_keys)

    print(f"\n[INFO] Found {len(sorted_keys)} translation keys")
    print("\nTypeScript interface definition:\n")
    print("export interface TranslationKeys {")
    for key in sorted_keys:
        print(f'  "{key}": string;')
    print("}")

    # Save to file
    output_file = Path(__file__).parent / 'translation_keys.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for key in sorted_keys:
            f.write(f'  "{key}": string;\n')

    print(f"\n[INFO] Keys saved to {output_file}")


if __name__ == '__main__':
    main()
