#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_cot_multilingual.py - Test du système CoT multilingue unifié

Ce script teste que les templates CoT sont correctement chargés depuis system_prompts.json
pour toutes les langues supportées.
"""

import sys
from pathlib import Path

# Add llm directory to Python path
llm_dir = Path(__file__).parent
sys.path.insert(0, str(llm_dir))

from config.system_prompts import get_prompts_manager, LANGUAGE_DISPLAY_NAMES
from config.config import SUPPORTED_LANGUAGES

def test_cot_multilingual():
    """Test du système CoT multilingue unifié"""

    print("=" * 80)
    print("TEST: Système CoT Multilingue Unifié")
    print("=" * 80)

    # 1. Charger le prompts manager
    print("\n1. Chargement du SystemPromptsManager...")
    try:
        manager = get_prompts_manager()
        print("   [OK] SystemPromptsManager charge avec succes")
    except Exception as e:
        print(f"   [ERREUR] Erreur chargement: {e}")
        return False

    # 2. Tester pour toutes les langues supportées
    print(f"\n2. Test des templates CoT pour {len(SUPPORTED_LANGUAGES)} langues...")

    success_count = 0
    failed_languages = []

    for lang in sorted(SUPPORTED_LANGUAGES):
        lang_name = LANGUAGE_DISPLAY_NAMES.get(lang, lang.upper())

        try:
            # Test CoT complet (structured)
            cot_full = manager.get_cot_prompt(language=lang, use_simple=False)

            # Test CoT simple
            cot_simple = manager.get_cot_prompt(language=lang, use_simple=True)

            # Vérifications
            checks = [
                ("<thinking>" in cot_full, "Contient <thinking>"),
                ("<analysis>" in cot_full, "Contient <analysis>"),
                ("<answer>" in cot_full, "Contient <answer>"),
                (lang_name in cot_full, f"Contient '{lang_name}'"),
                (lang_name in cot_simple, f"Simple contient '{lang_name}'"),
                ("CRITICAL" in cot_full, "Contient directive CRITICAL"),
            ]

            all_passed = all(check[0] for check in checks)

            if all_passed:
                print(f"   [OK] {lang:>2} ({lang_name:>10}): OK")
                success_count += 1
            else:
                failed_checks = [check[1] for check in checks if not check[0]]
                print(f"   [FAIL] {lang:>2} ({lang_name:>10}): ECHEC - {', '.join(failed_checks)}")
                failed_languages.append(lang)

        except Exception as e:
            print(f"   [EXCEPTION] {lang:>2} ({lang_name:>10}): {e}")
            failed_languages.append(lang)

    # 3. Résumé
    print("\n" + "=" * 80)
    print(f"RESULTAT: {success_count}/{len(SUPPORTED_LANGUAGES)} langues testees avec succes")

    if failed_languages:
        print(f"[FAIL] Langues echouees: {', '.join(failed_languages)}")
        return False
    else:
        print("[OK] Tous les tests passes!")
        return True

    print("=" * 80)

def test_cot_content():
    """Test du contenu des templates CoT"""

    print("\n" + "=" * 80)
    print("TEST: Contenu des Templates CoT")
    print("=" * 80)

    manager = get_prompts_manager()

    # Test en français
    print("\nExemple de template CoT en FRANCAIS:")
    print("-" * 80)
    cot_fr = manager.get_cot_prompt(language="fr", use_simple=False)
    print(cot_fr[:500] + "..." if len(cot_fr) > 500 else cot_fr)

    # Test en anglais
    print("\nExemple de template CoT en ANGLAIS:")
    print("-" * 80)
    cot_en = manager.get_cot_prompt(language="en", use_simple=False)
    print(cot_en[:500] + "..." if len(cot_en) > 500 else cot_en)

    # Test en espagnol
    print("\nExemple de template CoT en ESPAGNOL:")
    print("-" * 80)
    cot_es = manager.get_cot_prompt(language="es", use_simple=False)
    print(cot_es[:500] + "..." if len(cot_es) > 500 else cot_es)

    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Run tests
    success = test_cot_multilingual()

    if success:
        test_cot_content()
        sys.exit(0)
    else:
        sys.exit(1)
