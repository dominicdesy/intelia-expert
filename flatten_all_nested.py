"""
Script pour aplatir TOUS les objets imbriques en cles plates
"""
import json
import os

# Langues a traiter
LANGUAGES = ["fr", "en", "es", "de", "pt", "it", "nl", "pl", "zh", "ja", "hi", "ar", "th", "tr", "vi", "id"]

def flatten_all_nested(file_path):
    """Convertit tous les objets imbriques en cles plates"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nested_objects = []
    keys_to_delete = []

    # Trouver tous les objets imbriques
    for key, value in data.items():
        if isinstance(value, dict):
            nested_objects.append((key, value))
            keys_to_delete.append(key)

    if not nested_objects:
        print(f"SKIP {os.path.basename(file_path)}: Pas d'objets imbriques")
        return False

    # Aplatir tous les objets imbriques
    total_keys = 0
    for parent_key, nested_dict in nested_objects:
        for child_key, child_value in nested_dict.items():
            flat_key = f"{parent_key}.{child_key}"
            data[flat_key] = child_value
            total_keys += 1

    # Supprimer les objets imbriques
    for key in keys_to_delete:
        del data[key]

    # Sauvegarder
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK {os.path.basename(file_path)}: Aplati {len(nested_objects)} objets ({total_keys} cles)")
    return True

if __name__ == "__main__":
    frontend_locales_dir = "frontend/public/locales"

    total_converted = 0
    for lang in LANGUAGES:
        file_path = os.path.join(frontend_locales_dir, f"{lang}.json")
        if os.path.exists(file_path):
            if flatten_all_nested(file_path):
                total_converted += 1
        else:
            print(f"ERROR {lang}.json: Fichier non trouve")

    print(f"\nTermine! {total_converted}/{len(LANGUAGES)} fichiers convertis")
