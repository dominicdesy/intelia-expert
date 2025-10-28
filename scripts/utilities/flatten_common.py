"""
Script pour aplatir l'objet common imbrique en cles plates
"""
import json
import os

# Langues a traiter
LANGUAGES = ["fr", "en", "es", "de", "pt", "it", "nl", "pl", "zh", "ja", "hi", "ar", "th", "tr", "vi", "id"]

def flatten_common(file_path):
    """Convertit common imbrique en cles plates"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Verifier si common est un objet imbrique
    if 'common' in data and isinstance(data['common'], dict):
        common_obj = data['common']

        # Convertir en cles plates
        for key, value in common_obj.items():
            flat_key = f"common.{key}"
            data[flat_key] = value

        # Supprimer l'objet imbrique
        del data['common']

        # Sauvegarder
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"OK {os.path.basename(file_path)}: Converti {len(common_obj)} cles")
        return True
    else:
        print(f"SKIP {os.path.basename(file_path)}: Pas d'objet common imbrique")
        return False

if __name__ == "__main__":
    frontend_locales_dir = "frontend/public/locales"

    total_converted = 0
    for lang in LANGUAGES:
        file_path = os.path.join(frontend_locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            if flatten_common(file_path):
                total_converted += 1
        else:
            print(f"ERROR {lang}.json: Fichier non trouve")

    print(f"\nTermine! {total_converted}/{len(LANGUAGES)} fichiers convertis")
