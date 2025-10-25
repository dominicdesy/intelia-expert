"""
Script corrigé pour ajouter les traductions manquantes
"""
import json
import os
import sys

# Force UTF-8 pour éviter les erreurs d'encodage
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Traductions manquantes (ja, hi, ar, th, tr, vi, id)
MISSING_TRANSLATIONS = {
    "ja": {"fast": "速い", "veryFast": "とても速い"},
    "hi": {"fast": "तेज़", "veryFast": "बहुत तेज़"},
    "ar": {"fast": "سريع", "veryFast": "سريع جداً"},
    "th": {"fast": "เร็ว", "veryFast": "เร็วมาก"},
    "tr": {"fast": "Hızlı", "veryFast": "Çok hızlı"},
    "vi": {"fast": "Nhanh", "veryFast": "Rất nhanh"},
    "id": {"fast": "Cepat", "veryFast": "Sangat cepat"}
}

def add_translations(file_path, lang_code):
    """Ajouter les traductions fast et veryFast"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    translations = MISSING_TRANSLATIONS[lang_code]

    # Ajouter les nouvelles clés
    data["voiceSettings.fast"] = translations["fast"]
    data["voiceSettings.veryFast"] = translations["veryFast"]

    # Sauvegarder
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK {lang_code}.json")

if __name__ == "__main__":
    frontend_locales_dir = "frontend/public/locales"

    for lang_code in MISSING_TRANSLATIONS.keys():
        file_path = os.path.join(frontend_locales_dir, f"{lang_code}.json")
        if os.path.exists(file_path):
            add_translations(file_path, lang_code)
        else:
            print(f"ERROR {lang_code}.json non trouve")

    print(f"\nTermine! {len(MISSING_TRANSLATIONS)} fichiers mis a jour")
