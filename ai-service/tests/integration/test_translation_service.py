# -*- coding: utf-8 -*-
"""
test_translation_service.py - Tests du service de traduction

Tests:
1. Traduction 12 langues
2. 24 domaines techniques
3. Préservation termes techniques
4. Détection de langue
5. Fallback si dictionnaire manquant
"""

import pytest
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.translation_service import get_translation_service  # noqa: E402


@pytest.fixture
def translation_service():
    """Fixture: Translation Service"""
    return get_translation_service()


def test_translation_service_initialization(translation_service):
    """Test 1: Initialisation du service"""

    assert translation_service is not None
    assert translation_service.is_initialized

    # Vérifier que les dictionnaires sont chargés
    num_dicts = len(translation_service._language_dictionaries)
    assert num_dicts > 0, "No dictionaries loaded"

    print("\n✅ Test 1 PASSED - Service initialized")
    print(f"   Dictionaries loaded: {num_dicts}")


def test_translation_12_languages(translation_service):
    """Test 2: Traduction vers 12 langues"""

    source_text = "chicken weight at 35 days"
    from_lang = "en"

    target_languages = [
        "fr",
        "es",
        "de",
        "it",
        "pt",
        "pl",
        "nl",
        "id",
        "hi",
        "zh",
        "th",
    ]

    for to_lang in target_languages:
        translated = translation_service.translate(
            text=source_text, from_lang=from_lang, to_lang=to_lang
        )

        assert translated is not None, f"Translation to {to_lang} failed"
        assert len(translated) > 0

        print(f"   {to_lang.upper()}: {translated}")

    print("\n✅ Test 2 PASSED - 12 languages translation")


def test_translation_technical_terms_preservation(translation_service):
    """Test 3: Préservation des termes techniques"""

    technical_terms = [
        "Ross 308",
        "Cobb 500",
        "FCR",
        "GPS",
        "API",
        "Hubbard",
    ]

    for term in technical_terms:
        text = f"The {term} performance is excellent"

        translated = translation_service.translate(
            text=text, from_lang="en", to_lang="fr"
        )

        # Le terme technique doit être préservé
        assert term in translated, f"Technical term '{term}' not preserved"

        print(f"   {term}: ✓ preserved")

    print("\n✅ Test 3 PASSED - Technical terms preserved")


def test_translation_domains(translation_service):
    """Test 4: Traduction par domaine (24 domaines)"""

    # Tester quelques domaines clés
    domains = [
        "genetic_lines",
        "clinical_signs",
        "substrate_materials",
        "bird_types",
        "biosecurity_health",
        "nutrition_feeding",
        "production_metrics",
    ]

    for domain in domains:
        translated = translation_service.translate(
            text="chicken weight performance",
            from_lang="en",
            to_lang="fr",
            domain=domain,
        )

        assert translated is not None
        print(f"   {domain}: OK")

    print("\n✅ Test 4 PASSED - Domain translation")


def test_translation_get_available_domains(translation_service):
    """Test 5: Lister domaines disponibles"""

    domains = translation_service.get_available_domains()

    assert len(domains) > 0, "No domains available"
    assert "genetic_lines" in domains or len(domains) > 20

    print("\n✅ Test 5 PASSED - Available domains")
    print(f"   Total domains: {len(domains)}")
    print(f"   Sample: {list(domains)[:5]}")


def test_translation_fallback_missing_dict(translation_service):
    """Test 6: Fallback si dictionnaire manquant"""

    # Essayer de traduire avec une langue non supportée
    translated = translation_service.translate(
        text="chicken weight",
        from_lang="en",
        to_lang="xx",  # Langue invalide
        fallback=True,
    )

    # Devrait fallback sur le texte original ou une langue par défaut
    assert translated is not None

    print("\n✅ Test 6 PASSED - Fallback on missing dict")


def test_translation_empty_text(translation_service):
    """Test 7: Texte vide"""

    translated = translation_service.translate(text="", from_lang="en", to_lang="fr")

    # Devrait retourner chaîne vide ou None
    assert translated == "" or translated is None

    print("\n✅ Test 7 PASSED - Empty text handling")


def test_translation_very_long_text(translation_service):
    """Test 8: Texte très long"""

    long_text = "chicken weight performance " * 100  # Texte répété

    translated = translation_service.translate(
        text=long_text, from_lang="en", to_lang="fr"
    )

    assert translated is not None
    assert len(translated) > 100

    print("\n✅ Test 8 PASSED - Long text translation")
    print(f"   Length: {len(translated)} chars")


def test_translation_mixed_content(translation_service):
    """Test 9: Contenu mixte (texte + nombres + termes techniques)"""

    mixed_text = "Ross 308 weight at 35 days is 2100g with FCR of 1.5"

    translated = translation_service.translate(
        text=mixed_text, from_lang="en", to_lang="fr"
    )

    # Vérifier que les termes techniques et nombres sont préservés
    assert "Ross 308" in translated
    assert "FCR" in translated
    assert "2100" in translated
    assert "1.5" in translated

    print("\n✅ Test 9 PASSED - Mixed content")
    print(f"   Translated: {translated}")


def test_translation_batch(translation_service):
    """Test 10: Traduction batch (plusieurs textes)"""

    texts = [
        "chicken weight",
        "feed conversion ratio",
        "mortality rate",
        "water consumption",
        "temperature control",
    ]

    results = []
    for text in texts:
        translated = translation_service.translate(
            text=text, from_lang="en", to_lang="fr"
        )
        results.append(translated)

    assert len(results) == len(texts)
    assert all(r is not None for r in results)

    print("\n✅ Test 10 PASSED - Batch translation")
    for original, translated in zip(texts, results):
        print(f"   {original} -> {translated}")


def test_translation_all_supported_languages_loaded(translation_service):
    """Test 11: Vérifier que toutes les langues sont chargées"""

    expected_languages = [
        "fr",
        "en",
        "es",
        "de",
        "it",
        "pt",
        "pl",
        "nl",
        "id",
        "hi",
        "zh",
        "th",
    ]

    loaded_languages = translation_service.get_loaded_languages()

    for lang in expected_languages:
        assert lang in loaded_languages, f"Language {lang} not loaded"
        print(f"   {lang.upper()}: ✓ loaded")

    print("\n✅ Test 11 PASSED - All languages loaded")
    print(f"   Total: {len(loaded_languages)}/12")


def test_translation_roundtrip(translation_service):
    """Test 12: Traduction aller-retour"""

    original = "chicken weight at 35 days"

    # EN -> FR
    translated_fr = translation_service.translate(
        text=original, from_lang="en", to_lang="fr"
    )

    # FR -> EN
    back_to_en = translation_service.translate(
        text=translated_fr, from_lang="fr", to_lang="en"
    )

    # Devrait être similaire (pas forcément identique)
    assert "chicken" in back_to_en.lower() or "weight" in back_to_en.lower()

    print("\n✅ Test 12 PASSED - Roundtrip translation")
    print(f"   Original: {original}")
    print(f"   FR: {translated_fr}")
    print(f"   Back: {back_to_en}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
