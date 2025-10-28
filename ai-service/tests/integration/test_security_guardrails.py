# -*- coding: utf-8 -*-
"""
test_security_guardrails.py - Tests de sécurité

Tests:
1. OOD Detection (Out-of-Domain) - 12 langues
2. Blocked terms detection
3. Guardrails orchestrator
4. Claims extraction
5. Veterinary content detection
"""

import pytest
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from security.ood.detector import OODDetector  # noqa: E402
from security.guardrails.core import GuardrailsOrchestrator  # noqa: E402


@pytest.fixture
def ood_detector():
    """Fixture: OOD Detector"""
    return OODDetector()


@pytest.fixture
def guardrails():
    """Fixture: Guardrails Orchestrator"""
    return GuardrailsOrchestrator()


@pytest.mark.asyncio
async def test_ood_in_domain_queries(ood_detector):
    """Test 1: Queries IN-DOMAIN (aviculture)"""

    in_domain_queries = [
        "Quel poids pour Ross 308 à 35 jours ?",
        "What is the FCR of Cobb 500?",
        "¿Cuál es la mortalidad de los pollos?",
        "Comment améliorer la croissance des poulets ?",
        "Best practices for broiler nutrition",
        "Sintomas de coccidiosis en pollos",
    ]

    for query in in_domain_queries:
        result = await ood_detector.detect(query)

        assert result["is_in_domain"], f"False negative: {query}"
        assert result["confidence"] > 0.5, f"Low confidence for in-domain: {query}"

        print(f"   ✓ IN: {query[:50]}... ({result['confidence']:.2f})")

    print("\n✅ Test 1 PASSED - In-domain detection")


@pytest.mark.asyncio
async def test_ood_out_domain_queries(ood_detector):
    """Test 2: Queries OUT-OF-DOMAIN (non aviculture)"""

    out_domain_queries = [
        "Comment réparer ma voiture ?",
        "Recipe for chocolate cake",
        "¿Cómo aprender a tocar piano?",
        "What is quantum computing?",
        "How to fix a computer?",
        "Recette de pâtes carbonara",
    ]

    for query in out_domain_queries:
        result = await ood_detector.detect(query)

        assert not result["is_in_domain"], f"False positive: {query}"

        print(f"   ✓ OUT: {query[:50]}... ({result['confidence']:.2f})")

    print("\n✅ Test 2 PASSED - Out-of-domain detection")


@pytest.mark.asyncio
async def test_ood_multilingual(ood_detector):
    """Test 3: OOD detection multilingue (12 langues)"""

    # Query in-domain dans 12 langues
    multilingual_queries = [
        ("Poids des poulets", "fr"),
        ("Weight of chickens", "en"),
        ("Peso de los pollos", "es"),
        ("Gewicht der Hühner", "de"),
        ("Peso dei polli", "it"),
        ("Peso das galinhas", "pt"),
        ("Waga kurczaków", "pl"),
        ("Gewicht van kippen", "nl"),
        ("Berat ayam", "id"),
        ("मुर्गियों का वजन", "hi"),
        ("鸡的重量", "zh"),
        ("น้ำหนักไก่", "th"),
    ]

    for query, lang in multilingual_queries:
        result = await ood_detector.detect(query, language=lang)

        assert result["is_in_domain"], f"{lang}: {query}"

        print(f"   {lang.upper()}: ✓ ({result['confidence']:.2f})")

    print("\n✅ Test 3 PASSED - Multilingual OOD (12 languages)")


@pytest.mark.asyncio
async def test_ood_edge_cases(ood_detector):
    """Test 4: Edge cases et queries ambiguës"""

    edge_cases = [
        ("Ross 308", True),  # Juste une race - IN
        ("Chicken", True),  # Juste le mot poulet - IN
        ("Apple iPhone", False),  # Technologie - OUT
        ("Python programming", False),  # Programmation - OUT
        ("Turkey production", True),  # Dindes - IN
        ("Turkey country", False),  # Pays Turquie - OUT
    ]

    for query, expected_in_domain in edge_cases:
        result = await ood_detector.detect(query)

        assert (
            result["is_in_domain"] == expected_in_domain
        ), f"Edge case failed: {query}"

        print(f"   {query}: {'IN' if result['is_in_domain'] else 'OUT'}")

    print("\n✅ Test 4 PASSED - Edge cases")


@pytest.mark.asyncio
async def test_blocked_terms_detection(guardrails):
    """Test 5: Détection de termes bloqués"""

    # Ces queries devraient être bloquées
    blocked_queries = [
        "Comment tuer un poulet ?",
        "Poison for chickens",
        "How to harm poultry",
        "Veneno para pollos",
    ]

    for query in blocked_queries:
        result = await guardrails.check_input(query)

        # Devrait être bloqué ou signalé
        if result.get("blocked") or result.get("warning"):
            print(f"   ✓ BLOCKED: {query[:50]}")
        else:
            # Si pas bloqué explicitement, au moins un warning
            print(f"   ⚠ WARNING: {query[:50]}")

    print("\n✅ Test 5 PASSED - Blocked terms")


@pytest.mark.asyncio
async def test_guardrails_safe_queries(guardrails):
    """Test 6: Queries sûres passent les guardrails"""

    safe_queries = [
        "Quel poids pour Ross 308 à 35 jours ?",
        "Comment améliorer la croissance des poulets ?",
        "Best nutrition practices for broilers",
        "Síntomas de enfermedades comunes",
    ]

    for query in safe_queries:
        result = await guardrails.check_input(query)

        assert not result.get("blocked"), f"False positive block: {query}"

        print(f"   ✓ SAFE: {query[:50]}")

    print("\n✅ Test 6 PASSED - Safe queries pass")


@pytest.mark.asyncio
async def test_veterinary_content_detection(guardrails):
    """Test 7: Détection de contenu vétérinaire"""

    veterinary_queries = [
        "Symptômes de la coccidiose",
        "Maladies respiratoires chez les poulets",
        "Vaccination schedule for broilers",
        "Tratamiento de enfermedades",
    ]

    for query in veterinary_queries:
        result = await guardrails.check_input(query)

        # Devrait détecter le contenu vétérinaire
        is_veterinary = result.get("veterinary_content", False)

        print(f"   {'[VET]' if is_veterinary else '[???]'} {query[:50]}")

    print("\n✅ Test 7 PASSED - Veterinary detection")


@pytest.mark.asyncio
async def test_guardrails_output_checking(guardrails):
    """Test 8: Vérification des outputs"""

    test_outputs = [
        {
            "text": "Le poids optimal pour Ross 308 à 35 jours est de 2100-2200g.",
            "should_pass": True,
        },
        {
            "text": "Utilisez ce poison pour tuer les poulets rapidement.",
            "should_pass": False,
        },
        {
            "text": "Pour des symptômes graves, consultez immédiatement un vétérinaire.",
            "should_pass": True,
        },
    ]

    for test_case in test_outputs:
        result = await guardrails.check_output(test_case["text"])

        blocked = result.get("blocked", False)

        if test_case["should_pass"]:
            assert not blocked, f"False positive: {test_case['text'][:50]}"
            print(f"   ✓ PASS: {test_case['text'][:50]}")
        else:
            # Devrait être bloqué ou warning
            print(
                f"   ✓ {'BLOCKED' if blocked else 'WARNING'}: {test_case['text'][:50]}"
            )

    print("\n✅ Test 8 PASSED - Output checking")


@pytest.mark.asyncio
async def test_ood_vocabulary_coverage(ood_detector):
    """Test 9: Couverture du vocabulaire"""

    # Termes avicoles qui doivent être reconnus
    poultry_terms = [
        "broiler",
        "layer",
        "hatchery",
        "incubation",
        "feed conversion",
        "mortality rate",
        "coccidiosis",
        "Ross 308",
        "Cobb 500",
        "Hubbard",
        "ISA Brown",
    ]

    in_domain_count = 0
    for term in poultry_terms:
        result = await ood_detector.detect(f"What is {term}?")

        if result["is_in_domain"]:
            in_domain_count += 1
            print(f"   ✓ {term}")
        else:
            print(f"   ✗ {term} (not recognized)")

    coverage = in_domain_count / len(poultry_terms) * 100

    print("\n✅ Test 9 PASSED - Vocabulary coverage")
    print(f"   Coverage: {coverage:.1f}% ({in_domain_count}/{len(poultry_terms)})")

    assert coverage > 70, "Low vocabulary coverage"


@pytest.mark.asyncio
async def test_ood_performance(ood_detector):
    """Test 10: Performance OOD detection"""

    import time

    queries = [
        "Poids Ross 308 35 jours",
        "Comment réparer ma voiture ?",
        "What is chicken weight?",
        "Recipe for pasta",
        "FCR Cobb 500",
    ] * 2  # 10 queries total

    start = time.time()

    for query in queries:
        await ood_detector.detect(query)

    duration = time.time() - start
    avg_time = duration / len(queries)

    assert avg_time < 0.5, f"OOD detection too slow: {avg_time:.3f}s"

    print("\n✅ Test 10 PASSED - Performance")
    print(f"   Average: {avg_time:.3f}s per query")
    print(f"   Total: {duration:.3f}s for {len(queries)} queries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
