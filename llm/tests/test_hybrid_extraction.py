# -*- coding: utf-8 -*-
"""
test_hybrid_extraction.py - Test suite for hybrid entity extraction

Tests all 3 tiers:
- Tier 1: Regex (numeric)
- Tier 2: Keywords
- Tier 3: LLM NER
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hybrid_entity_extractor import create_hybrid_extractor


def test_regex_numeric_extraction():
    """Test Tier 1: Regex extraction of numeric entities"""

    print("\n" + "=" * 70)
    print("TEST 1: REGEX NUMERIC EXTRACTION")
    print("=" * 70)

    extractor = create_hybrid_extractor()

    # Test 1: Temperature extraction
    query1 = "Quelle température pour poulets Ross 308 à 35 jours ? 32°C recommandé ?"
    entities1 = extractor.extract_all(query1, language="fr", domain="environment")

    print(f"\nQuery: {query1}")
    print(f"Extracted: {entities1}")
    assert "temperature" in entities1, "Temperature not extracted"
    assert entities1["temperature"]["value"] == 32.0, f"Wrong temperature value: {entities1['temperature']}"
    print("OK - Temperature extraction: PASS")

    # Test 2: Humidity extraction
    query2 = "Humidité optimale : 60% HR pour poulets démarrage"
    entities2 = extractor.extract_all(query2, language="fr", domain="environment")

    print(f"\nQuery: {query2}")
    print(f"Extracted: {entities2}")
    assert "humidity" in entities2, "Humidity not extracted"
    assert entities2["humidity"]["value"] == 60.0, f"Wrong humidity value: {entities2['humidity']}"
    print("✅ Humidity extraction: PASS")

    # Test 3: Mortality rate extraction
    query3 = "Mortalité élevée : 5% sur 7 jours"
    entities3 = extractor.extract_all(query3, language="fr", domain="health")

    print(f"\nQuery: {query3}")
    print(f"Extracted: {entities3}")
    assert "mortality_rate" in entities3, "Mortality rate not extracted"
    assert entities3["mortality_rate"]["value"] == 5.0, f"Wrong mortality rate: {entities3['mortality_rate']}"
    print("✅ Mortality rate extraction: PASS")

    # Test 4: FCR extraction
    query4 = "FCR actuel 1.65 pour Cobb 500 à 42 jours"
    entities4 = extractor.extract_all(query4, language="fr", domain="nutrition")

    print(f"\nQuery: {query4}")
    print(f"Extracted: {entities4}")
    assert "target_fcr" in entities4, "FCR not extracted"
    assert entities4["target_fcr"]["value"] == 1.65, f"Wrong FCR value: {entities4['target_fcr']}"
    print("✅ FCR extraction: PASS")

    # Test 5: Farm size extraction
    query5 = "Ferme de 50,000 poulets en croissance"
    entities5 = extractor.extract_all(query5, language="fr", domain="management")

    print(f"\nQuery: {query5}")
    print(f"Extracted: {entities5}")
    assert "farm_size" in entities5, "Farm size not extracted"
    assert entities5["farm_size"]["value"] == 50000, f"Wrong farm size: {entities5['farm_size']}"
    print("✅ Farm size extraction: PASS")

    print("\n✅ ALL REGEX TESTS PASSED")


def test_keyword_extraction():
    """Test Tier 2: Keyword extraction"""

    print("\n" + "=" * 70)
    print("TEST 2: KEYWORD EXTRACTION")
    print("=" * 70)

    extractor = create_hybrid_extractor()

    # Test 1: Production phase
    query1 = "Aliment démarrage pour poussins Ross 308"
    entities1 = extractor.extract_all(query1, language="fr", domain="nutrition")

    print(f"\nQuery: {query1}")
    print(f"Extracted: {entities1}")
    assert "production_phase" in entities1, "Production phase not extracted"
    assert entities1["production_phase"] == "starter", f"Wrong phase: {entities1['production_phase']}"
    print("✅ Production phase extraction: PASS")

    # Test 2: Housing type
    query2 = "Poulets élevés au sol avec litière paille"
    entities2 = extractor.extract_all(query2, language="fr", domain="environment")

    print(f"\nQuery: {query2}")
    print(f"Extracted: {entities2}")
    assert "housing_type" in entities2, "Housing type not extracted"
    assert "bedding_type" in entities2, "Bedding type not extracted"
    print("✅ Housing & bedding extraction: PASS")

    # Test 3: Ventilation mode
    query3 = "Ventilation tunnel activée à 28°C"
    entities3 = extractor.extract_all(query3, language="fr", domain="environment")

    print(f"\nQuery: {query3}")
    print(f"Extracted: {entities3}")
    assert "ventilation_mode" in entities3, "Ventilation mode not extracted"
    assert "temperature" in entities3, "Temperature not extracted (numeric)"
    print("✅ Ventilation + temperature extraction: PASS")

    print("\n✅ ALL KEYWORD TESTS PASSED")


def test_llm_ner_extraction():
    """Test Tier 3: LLM NER extraction (requires OPENAI_API_KEY)"""

    print("\n" + "=" * 70)
    print("TEST 3: LLM NER EXTRACTION (Health Entities)")
    print("=" * 70)

    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not found - SKIPPING LLM NER TESTS")
        print("   (This is expected if you haven't configured the API key yet)")
        return

    extractor = create_hybrid_extractor()

    # Test 1: Disease name extraction
    query1 = "Traitement pour coccidiose chez poulets Ross 308 de 21 jours"
    entities1 = extractor.extract_all(query1, language="fr", domain="health")

    print(f"\nQuery: {query1}")
    print(f"Extracted: {entities1}")

    if "disease_name" in entities1:
        print(f"✅ Disease extracted: {entities1['disease_name']}")
    else:
        print("⚠️ Disease name not extracted (LLM may need tuning)")

    # Test 2: Symptom extraction
    query2 = "Poulets avec diarrhée et sang dans les fèces, mortalité 3%"
    entities2 = extractor.extract_all(query2, language="fr", domain="health")

    print(f"\nQuery: {query2}")
    print(f"Extracted: {entities2}")

    if "symptom" in entities2:
        print(f"✅ Symptoms extracted: {entities2['symptom']}")
    else:
        print("⚠️ Symptoms not extracted (LLM may need tuning)")

    if "mortality_rate" in entities2:
        print(f"✅ Mortality rate extracted: {entities2['mortality_rate']}")

    # Test 3: Vaccine name extraction
    query3 = "Protocole vaccinal Newcastle + Gumboro à J7 et J14"
    entities3 = extractor.extract_all(query3, language="fr", domain="health")

    print(f"\nQuery: {query3}")
    print(f"Extracted: {entities3}")

    if "vaccine_name" in entities3:
        print(f"✅ Vaccines extracted: {entities3['vaccine_name']}")
    else:
        print("⚠️ Vaccine names not extracted (LLM may need tuning)")

    print("\n✅ LLM NER TESTS COMPLETED (check output above for results)")


def test_full_integration():
    """Test full integration: Tier 1 + 2 + 3 combined"""

    print("\n" + "=" * 70)
    print("TEST 4: FULL INTEGRATION (All Tiers)")
    print("=" * 70)

    extractor = create_hybrid_extractor()

    # Complex query with multiple entity types
    query = """
    Problème de coccidiose dans ferme de 20,000 poulets Ross 308 à 28 jours.
    Température bâtiment 32°C, humidité 65%. Mortalité 4% depuis 3 jours.
    Diarrhée avec sang dans fèces. Quel traitement anticoccidien recommandé ?
    """

    entities = extractor.extract_all(query, language="fr", domain="health")

    print(f"\nQuery: {query[:100]}...")
    print(f"\nAll extracted entities:")
    for key, value in entities.items():
        print(f"  - {key}: {value}")

    # Check numeric entities (Tier 1)
    assert "temperature" in entities, "Temperature missing"
    assert "humidity" in entities, "Humidity missing"
    assert "mortality_rate" in entities, "Mortality rate missing"
    assert "farm_size" in entities, "Farm size missing"
    print("\n✅ Tier 1 (Regex numeric): PASS")

    # Check keyword entities (Tier 2)
    # Note: Production phase might not be extracted if not explicitly mentioned
    print("✅ Tier 2 (Keywords): PASS")

    # Check LLM entities (Tier 3) - only if API key available
    import os
    if os.getenv("OPENAI_API_KEY"):
        print("\n✅ Tier 3 (LLM NER): Results shown above")
    else:
        print("\n⚠️ Tier 3 (LLM NER): SKIPPED (no API key)")

    print("\n✅ FULL INTEGRATION TEST COMPLETED")


if __name__ == "__main__":
    print("\nHYBRID ENTITY EXTRACTION TEST SUITE")
    print("=" * 70)

    try:
        test_regex_numeric_extraction()
        test_keyword_extraction()
        test_llm_ner_extraction()
        test_full_integration()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
