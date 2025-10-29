#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de synchronisation des fichiers de traduction
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Script de synchronisation des fichiers de traduction
Utilise en.json comme référence et synchronise tous les autres fichiers
"""

import json
import os

os.chdir('public/locales')

# Charger EN comme référence
print('=== SYNCHRONISATION DES TRADUCTIONS ===\n')
print('Chargement de en.json comme reference...')
with open('en.json', 'r', encoding='utf-8') as f:
    en_data = json.load(f)

en_keys = set(en_data.keys())
print(f'Reference EN: {len(en_keys)} cles\n')

# Langues à synchroniser
languages = ['fr', 'es', 'de', 'it', 'pt', 'nl', 'pl', 'ar', 'zh', 'ja', 'hi', 'id', 'th', 'tr', 'vi']

total_added = 0
total_removed = 0

for lang in languages:
    filename = f'{lang}.json'
    print(f'Traitement de {filename}...')

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Trouver les clés manquantes et en trop
    missing = en_keys - set(data.keys())
    extra = set(data.keys()) - en_keys

    # Ajouter les clés manquantes (avec valeur EN comme placeholder)
    for key in missing:
        data[key] = en_data[key]
        print(f'  + Ajout: {key}')

    # Supprimer les clés en trop
    for key in extra:
        del data[key]
        print(f'  - Suppression: {key}')

    total_added += len(missing)
    total_removed += len(extra)

    # Sauvegarder avec le même ordre que EN
    ordered_data = {key: data[key] for key in en_data.keys()}

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(ordered_data, f, ensure_ascii=False, indent=2)

    print(f'  OK: {len(missing)} ajoutees, {len(extra)} supprimees\n')

print('=== RESUME ===')
print(f'Total de cles ajoutees: {total_added}')
print(f'Total de cles supprimees: {total_removed}')
print(f'\nTous les fichiers ont maintenant exactement {len(en_keys)} cles!')
print('\nIMPORTANT: Les cles ajoutees utilisent la valeur EN comme placeholder.')
print('Vous devrez les traduire manuellement plus tard.')
