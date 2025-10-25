"""
Script pour ajouter les traductions voiceSettings.fast et voiceSettings.veryFast
"""
import json
import os

# Langues et leurs traductions
TRANSLATIONS = {
    "fr": {"fast": "Rapide", "veryFast": "Très rapide"},
    "en": {"fast": "Fast", "veryFast": "Very fast"},
    "es": {"fast": "Rápido", "veryFast": "Muy rápido"},
    "de": {"fast": "Schnell", "veryFast": "Sehr schnell"},
    "pt": {"fast": "Rápido", "veryFast": "Muito rápido"},
    "it": {"fast": "Veloce", "veryFast": "Molto veloce"},
    "nl": {"fast": "Snel", "veryFast": "Heel snel"},
    "pl": {"fast": "Szybko", "veryFast": "Bardzo szybko"},
    "zh": {"fast": "快速", "veryFast": "非常快"},
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

    translations = TRANSLATIONS[lang_code]

    # Ajouter les nouvelles clés
    data["voiceSettings.fast"] = translations["fast"]
    data["voiceSettings.veryFast"] = translations["veryFast"]

    # Sauvegarder
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK {os.path.basename(file_path)}: Ajoute fast={translations['fast']}, veryFast={translations['veryFast']}")

if __name__ == "__main__":
    frontend_locales_dir = "frontend/public/locales"

    for lang_code in TRANSLATIONS.keys():
        file_path = os.path.join(frontend_locales_dir, f"{lang_code}.json")
        if os.path.exists(file_path):
            add_translations(file_path, lang_code)
        else:
            print(f"ERROR {lang_code}.json: Fichier non trouve")

    print(f"\nTermine! {len(TRANSLATIONS)} fichiers mis a jour")
