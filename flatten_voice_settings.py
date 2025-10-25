"""
Script pour aplatir la structure voiceSettings imbriquée en clés plates
"""
import json
import os

# Langues à traiter
LANGUAGES = ["fr", "en", "es", "de", "pt", "it", "nl", "pl", "zh", "ja", "hi", "ar", "th", "tr", "vi", "id"]

def flatten_voice_settings(file_path):
    """Convertit voiceSettings imbriqué en clés plates"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Vérifier si voiceSettings est un objet imbriqué
    if 'voiceSettings' in data and isinstance(data['voiceSettings'], dict):
        voice_settings = data['voiceSettings']

        # Convertir en clés plates
        for key, value in voice_settings.items():
            flat_key = f"voiceSettings.{key}"
            data[flat_key] = value

        # Supprimer l'objet imbriqué
        del data['voiceSettings']

        # Sauvegarder
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"OK {os.path.basename(file_path)}: Converti {len(voice_settings)} cles")
        return True
    else:
        print(f"SKIP {os.path.basename(file_path)}: Deja en format plat")
        return False

if __name__ == "__main__":
    frontend_locales_dir = "frontend/public/locales"

    total_converted = 0
    for lang in LANGUAGES:
        file_path = os.path.join(frontend_locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            if flatten_voice_settings(file_path):
                total_converted += 1
        else:
            print(f"ERROR {lang}.json: Fichier non trouve")

    print(f"\nTermine! {total_converted}/{len(LANGUAGES)} fichiers convertis")
