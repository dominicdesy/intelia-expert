#!/usr/bin/env python3
"""
Update TranslationKeys interface in i18n.ts with all keys from en.json
"""

import json
import re
from pathlib import Path


def flatten_json(data, parent_key=''):
    """Flatten nested JSON to dot notation keys"""
    items = set()  # Use set to avoid duplicates
    for k, v in data.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_json(v, new_key))
        else:
            items.add(new_key)
    return items


def main():
    """Update i18n.ts interface"""
    frontend_dir = Path(__file__).parent / 'frontend'
    i18n_file = frontend_dir / 'lib' / 'languages' / 'i18n.ts'
    en_file = frontend_dir / 'public' / 'locales' / 'en.json'

    if not i18n_file.exists() or not en_file.exists():
        print("[ERROR] Required files not found")
        return

    print(f"[INFO] Extracting keys from {en_file}")
    with open(en_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    all_keys = sorted(flatten_json(data))
    print(f"[INFO] Found {len(all_keys)} translation keys")

    # Generate new interface
    interface_lines = ["export interface TranslationKeys {"]
    for key in all_keys:
        interface_lines.append(f'  "{key}": string;')
    interface_lines.append("}")
    new_interface = "\n".join(interface_lines)

    # Read current file
    with open(i18n_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace interface using regex
    pattern = r'export interface TranslationKeys \{[^}]*\}'

    # Find the interface
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("[ERROR] Could not find TranslationKeys interface")
        return

    # Replace it
    new_content = content[:match.start()] + new_interface + content[match.end():]

    # Write back
    with open(i18n_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"[OK] Updated {i18n_file}")
    print(f"[INFO] Interface now has {len(all_keys)} keys")


if __name__ == '__main__':
    main()
