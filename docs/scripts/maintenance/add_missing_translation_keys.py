#!/usr/bin/env python3
"""
Add missing translation keys to all locale files
"""

import json
from pathlib import Path

missing_keys = {
    "stripe": {
        "portal": {
            "error": "Error accessing customer portal"
        }
    }
}

def deep_merge(base, update):
    """Recursively merge update into base"""
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base

def main():
    frontend_dir = Path(__file__).parent / 'frontend'
    locales_dir = frontend_dir / 'public' / 'locales'

    # Process all locale files
    for json_file in locales_dir.glob('*.json'):
        if 'stripe_keys' in json_file.name:
            continue

        print(f"[INFO] Processing {json_file.name}")

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Merge missing keys
        data = deep_merge(data, missing_keys)

        # Write back
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Updated {json_file.name}")

    print("\n[DONE] All files updated")

if __name__ == '__main__':
    main()
