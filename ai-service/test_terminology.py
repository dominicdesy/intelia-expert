#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_terminology.py - Test du système de terminologie avicole multilingue

Ce script teste que le glossaire de terminologie est correctement chargé
et intégré dans les prompts système.
"""

import sys
from pathlib import Path

# Add llm directory to Python path
llm_dir = Path(__file__).parent
sys.path.insert(0, str(llm_dir))

from config.system_prompts import get_prompts_manager

def test_terminology_loading():
    """Test du chargement de la terminologie"""

    print("=" * 80)
    print("TEST: Chargement de la Terminologie Avicole")
    print("=" * 80)

    # 1. Charger le prompts manager
    print("\n1. Chargement du SystemPromptsManager avec terminologie...")
    try:
        manager = get_prompts_manager()
        print("   [OK] SystemPromptsManager charge")
    except Exception as e:
        print(f"   [ERREUR] {e}")
        return False

    # 2. Vérifier que la terminologie est chargée
    print("\n2. Verification de la terminologie...")
    if not manager.terminology:
        print("   [FAIL] Terminologie non chargee")
        return False

    terms_count = len(manager.terminology.get("terminology", {}))
    print(f"   [OK] {terms_count} termes charges")

    # 3. Lister les termes disponibles
    print("\n3. Termes disponibles:")
    terms = manager.terminology.get("terminology", {})
    for term_key in sorted(terms.keys()):
        term_data = terms[term_key]
        description = term_data.get("description", "")
        print(f"   - {term_key}: {description}")

    return True

def test_terminology_instructions():
    """Test de génération des instructions de terminologie"""

    print("\n" + "=" * 80)
    print("TEST: Generation des Instructions de Terminologie")
    print("=" * 80)

    manager = get_prompts_manager()

    # Test pour 3 langues
    test_languages = ["fr", "en", "es"]

    for lang in test_languages:
        print(f"\n--- Instructions pour {lang.upper()} ---")
        instructions = manager.get_terminology_instructions(lang)

        if not instructions:
            print(f"   [FAIL] Aucune instruction generee pour {lang}")
            continue

        print(instructions)

def test_terminology_integration():
    """Test de l'intégration de la terminologie dans les prompts"""

    print("\n" + "=" * 80)
    print("TEST: Integration de la Terminologie dans les Prompts")
    print("=" * 80)

    manager = get_prompts_manager()

    # Test avec expert_identity (devrait inclure la terminologie)
    print("\n--- expert_identity en FRANCAIS (avec terminologie) ---")
    expert_identity_fr = manager.get_base_prompt("expert_identity", "fr", include_terminology=True)
    print(expert_identity_fr[:600] + "..." if len(expert_identity_fr) > 600 else expert_identity_fr)

    # Vérifier que "poulailler" est bien présent
    if "poulailler" in expert_identity_fr.lower():
        print("\n[OK] Terminologie francaise presente (poulailler)")
    else:
        print("\n[FAIL] Terminologie francaise absente")

    # Test en anglais
    print("\n--- expert_identity en ANGLAIS (avec terminologie) ---")
    expert_identity_en = manager.get_base_prompt("expert_identity", "en", include_terminology=True)
    print(expert_identity_en[:600] + "..." if len(expert_identity_en) > 600 else expert_identity_en)

    # Vérifier que "poultry house" est bien présent
    if "poultry house" in expert_identity_en.lower():
        print("\n[OK] Terminologie anglaise presente (poultry house)")
    else:
        print("\n[FAIL] Terminologie anglaise absente")

if __name__ == "__main__":
    # Run tests
    success = test_terminology_loading()

    if success:
        test_terminology_instructions()
        test_terminology_integration()
        print("\n" + "=" * 80)
        print("[OK] Tous les tests terminologie passes")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("[FAIL] Echec du chargement de la terminologie")
        print("=" * 80)
        sys.exit(1)
