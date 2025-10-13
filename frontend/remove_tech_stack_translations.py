#!/usr/bin/env python3
"""Remove tech stack translations from all locale files"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "public" / "locales"

# Keys to remove
KEYS_TO_REMOVE = [
    "about.technologyStack",
    "about.frontend",
    "about.backend",
    "about.aiml",
    "about.infrastructure",
]

# Get all locale files
locale_files = list(LOCALES_DIR.glob("*.json"))

for locale_file in locale_files:
    print(f"\n[PROCESSING] {locale_file.name}")

    with open(locale_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    removed_count = 0
    for key in KEYS_TO_REMOVE:
        if key in data:
            del data[key]
            removed_count += 1
            print(f"  [REMOVED] {key}")

    if removed_count > 0:
        with open(locale_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [OK] Removed {removed_count} keys from {locale_file.name}")
    else:
        print(f"  [SKIP] No keys to remove in {locale_file.name}")

print("\n[DONE] Finished removing tech stack translations")
