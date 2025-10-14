#!/usr/bin/env python3
"""Add common.and translation key to all locale files."""

import json
import os

# Translations for "and" in each language
translations = {
    'en': 'and',
    'fr': 'et',
    'es': 'y',
    'de': 'und',
    'ar': 'و',
    'hi': 'और',
    'id': 'dan',
    'it': 'e',
    'ja': 'と',
    'nl': 'en',
    'pl': 'i',
    'pt': 'e',
    'th': 'และ',
    'tr': 've',
    'vi': 'và',
    'zh': '和'
}

locales_dir = os.path.join(os.path.dirname(__file__), 'public', 'locales')

for lang_code, translation in translations.items():
    file_path = os.path.join(locales_dir, f'{lang_code}.json')

    if not os.path.exists(file_path):
        print(f"[WARN] File not found: {file_path}")
        continue

    # Read the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if key already exists
    if 'common.and' in data:
        print(f"[OK] {lang_code}.json already has 'common.and'")
        continue

    # Add the new key
    data['common.and'] = translation

    # Write back to file (will reorder keys alphabetically in Python's json module)
    # To preserve order, we'll read as text and inject the line
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the line with "common.or" and insert before it
    new_lines = []
    for i, line in enumerate(lines):
        if '"common.or"' in line:
            # Insert the new key with the same indentation
            indent = len(line) - len(line.lstrip())
            new_line = ' ' * indent + f'"common.and": "{translation}",\n'
            new_lines.append(new_line)
        new_lines.append(line)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"[OK] Added 'common.and' to {lang_code}.json")

print("\n[DONE] All locale files updated.")
