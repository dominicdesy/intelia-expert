#!/usr/bin/env python3
"""
Add Nav About
Version: 1.4.1
Last modified: 2025-10-26
"""
"""Add nav.about translation to all locale files"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "public" / "locales"

NAV_ABOUT_TRANSLATIONS = {
    "de": "Über uns",
    "es": "Acerca de",
    "hi": "के बारे में",
    "id": "Tentang",
    "it": "Informazioni",
    "nl": "Over",
    "pl": "O nas",
    "pt": "Sobre",
    "th": "เกี่ยวกับ",
    "zh": "关于"
}

for lang_code, translation in NAV_ABOUT_TRANSLATIONS.items():
    locale_file = LOCALES_DIR / f"{lang_code}.json"

    if not locale_file.exists():
        print(f"[SKIP] {locale_file.name} not found")
        continue

    with open(locale_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Add nav.about if not exists
    if "nav.about" not in data:
        data["nav.about"] = translation

        with open(locale_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Added nav.about to {locale_file.name}")
    else:
        print(f"[SKIP] nav.about already exists in {locale_file.name}")

print("[DONE] Finished")
