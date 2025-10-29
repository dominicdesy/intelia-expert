#!/usr/bin/env python3
"""
Script pour copier les nouvelles traductions de en.json vers tous les autres fichiers de langues
"""
import json
from pathlib import Path

def copy_new_keys_from_en_to_other_langs():
    """Copier les clés manquantes de en.json vers les autres langues"""
    locales_dir = Path("frontend/public/locales")

    # Lire en.json comme référence
    en_file = locales_dir / "en.json"
    with open(en_file, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    # Liste des autres langues
    other_langs = ["ar", "de", "es", "hi", "id", "it", "ja", "nl", "pl", "pt", "th", "tr", "vi", "zh"]

    for lang in other_langs:
        lang_file = locales_dir / f"{lang}.json"
        if not lang_file.exists():
            print(f"⚠ File not found: {lang_file}")
            continue

        print(f"Processing {lang}.json...")

        with open(lang_file, 'r', encoding='utf-8') as f:
            lang_data = json.load(f)

        added_count = 0
        for key, value in en_data.items():
            if key not in lang_data:
                lang_data[key] = value  # Use English as fallback
                added_count += 1

        with open(lang_file, 'w', encoding='utf-8') as f:
            json.dump(lang_data, f, ensure_ascii=False, indent=2)

        print(f"  Added {added_count} new translations")

    print("\nDone!")

if __name__ == "__main__":
    copy_new_keys_from_en_to_other_langs()
