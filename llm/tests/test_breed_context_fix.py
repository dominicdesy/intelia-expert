# -*- coding: utf-8 -*-
"""
Test du fix pour conversation context bleeding
Vérifie que changer de breed bloque le merge des entités contextuelles
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.query_router import QueryRouter
from core.config_manager import ConfigManager


def test_breed_context_bleeding_fix():
    """
    Scénario:
    1. Conversation 1: "Quel est le poids d'un Cobb 500 mâle de 17 jours?"
       → entities: {breed: "Cobb 500", age_days: 17, sex: "male"}

    2. Nouvelle conversation: "Quel est le poids d'un Ross 308?"
       → entities contextuelles: {breed: "Cobb 500", age_days: 17, sex: "male"}
       → entities actuelles: {breed: "Ross 308"}

    COMPORTEMENT ATTENDU:
    - Le système détecte breed mismatch (Cobb 500 ≠ Ross 308)
    - Le système BLOQUE le merge de age_days et sex
    - Résultat: {breed: "Ross 308"} seulement
    - Le système devrait demander clarification pour age
    """

    # Initialize
    config = ConfigManager()
    router = QueryRouter(config)

    print("\n" + "=" * 80)
    print("TEST: Breed Context Bleeding Fix")
    print("=" * 80)

    # Simuler contexte extrait de conversation précédente (Cobb 500)
    preextracted_entities = {
        "breed": "Cobb 500",
        "age_days": 17,
        "sex": "male",
        "metric_type": "weight"
    }

    # Nouvelle query sur Ross 308
    query = "Quel est le poids d'un Ross 308 ?"

    print(f"\n📝 Query actuelle: {query}")
    print(f"📦 Entités du contexte (Cobb 500): {preextracted_entities}")

    # Route avec preextracted_entities
    result = router.route(
        query=query,
        language="fr",
        user_id="test_user",
        preextracted_entities=preextracted_entities
    )

    print("\n✅ Résultat du routing:")
    print(f"   Destination: {result.destination}")
    print(f"   Entities: {result.entities}")
    print(f"   Missing fields: {result.missing_fields}")

    # ASSERTIONS
    assert result.entities.get("breed") in ["Ross 308", "ross 308"], \
        f"Breed devrait être Ross 308, pas {result.entities.get('breed')}"

    # CRITICAL: age_days et sex NE doivent PAS être mergées (breed différente)
    assert "age_days" not in result.entities or result.entities["age_days"] is None, \
        f"age_days ne devrait PAS être mergée (breed mismatch): {result.entities}"

    assert "sex" not in result.entities or result.entities["sex"] is None, \
        f"sex ne devrait PAS être mergée (breed mismatch): {result.entities}"

    # Le système devrait identifier age_days comme champ manquant
    assert "age_days" in result.missing_fields, \
        f"age_days devrait être dans missing_fields: {result.missing_fields}"

    print("\n✅ SUCCESS: Le système a correctement bloqué le merge (breed mismatch)")
    print(f"   ✓ Breed actuelle utilisée: {result.entities.get('breed')}")
    print("   ✓ age_days du contexte BLOQUÉE (pas mergée)")
    print("   ✓ sex du contexte BLOQUÉE (pas mergée)")
    print(f"   ✓ Champs manquants identifiés: {result.missing_fields}")


def test_same_breed_context_merge():
    """
    Test le cas où la breed est la MÊME → le merge doit fonctionner

    Scénario:
    1. Conversation: "Quel est le poids d'un Cobb 500 mâle de 17 jours?"
    2. Suivi: "Quel est le FCR?" (même breed implicite)

    COMPORTEMENT ATTENDU:
    - Breed identique → merger contexte OK
    - Résultat: {breed: "Cobb 500", age_days: 17, sex: "male", metric_type: "fcr"}
    """

    config = ConfigManager()
    router = QueryRouter(config)

    print("\n" + "=" * 80)
    print("TEST: Same Breed Context Merge (Should Work)")
    print("=" * 80)

    # Contexte Cobb 500
    preextracted_entities = {
        "breed": "Cobb 500",
        "age_days": 17,
        "sex": "male",
        "metric_type": "weight"
    }

    # Query sur FCR (pas de breed mentionnée)
    query = "Quel est le FCR ?"

    print(f"\n📝 Query actuelle: {query}")
    print(f"📦 Entités du contexte (Cobb 500): {preextracted_entities}")

    result = router.route(
        query=query,
        language="fr",
        user_id="test_user_2",
        preextracted_entities=preextracted_entities
    )

    print("\n✅ Résultat du routing:")
    print(f"   Destination: {result.destination}")
    print(f"   Entities: {result.entities}")

    # ASSERTIONS: Le merge DOIT fonctionner (pas de breed dans query → compatible)
    assert result.entities.get("breed") == "Cobb 500", \
        f"Breed du contexte devrait être mergée: {result.entities}"

    assert result.entities.get("age_days") == 17, \
        f"age_days devrait être mergée (pas de conflit): {result.entities}"

    assert result.entities.get("sex") == "male", \
        f"sex devrait être mergée (pas de conflit): {result.entities}"

    print("\n✅ SUCCESS: Le merge fonctionne correctement (pas de breed conflict)")
    print("   ✓ Contexte correctement réutilisé pour question de suivi")


if __name__ == "__main__":
    try:
        test_breed_context_bleeding_fix()
        test_same_breed_context_merge()

        print("\n" + "=" * 80)
        print("✅ TOUS LES TESTS PASSENT - Fix validé!")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
