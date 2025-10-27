# -*- coding: utf-8 -*-
"""
tests/test_vision_integration.py - Tests d'intégration pour le système vision médical

Tests de bout en bout:
1. Upload d'image vers backend (DigitalOcean Spaces)
2. Analyse d'image avec Claude Vision + RAG
3. Validation des réponses vétérinaires

Run with: python -m pytest tests/test_vision_integration.py -v
"""

import pytest
import os
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image


# === TESTS UNITAIRES DU VISION ANALYZER ===

@pytest.mark.asyncio
async def test_vision_analyzer_initialization():
    """Test 1: Initialisation du ClaudeVisionAnalyzer"""
    from generation.claude_vision_analyzer import create_vision_analyzer

    # Créer l'analyzer
    analyzer = create_vision_analyzer(language="fr")

    assert analyzer is not None
    assert analyzer.language == "fr"
    # Le modèle peut être configuré via ANTHROPIC_VISION_MODEL/ANTHROPIC_MODEL ou utilise la valeur par défaut
    # Claude 4.5 models (current) or Claude 3.x models (legacy/deprecated)
    valid_models = [
        "claude-sonnet-4-5-20250929",  # Current default
        "claude-haiku-4-5-20251001",   # Current budget
        "claude-opus-4-1-20250805",    # Current premium
        "claude-3-5-sonnet-20240620",  # Legacy (retired Oct 22, 2025)
        "claude-3-opus-20240229",      # Legacy
    ]
    assert analyzer.model in valid_models
    assert analyzer.api_key is not None

    print(f"✅ ClaudeVisionAnalyzer initialized successfully - Model: {analyzer.model}")


@pytest.mark.asyncio
async def test_vision_analyzer_image_conversion():
    """Test 2: Conversion d'image en base64"""
    from generation.claude_vision_analyzer import create_vision_analyzer

    # Créer une image test (100x100 rouge)
    test_image = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    test_image.save(buffer, format='JPEG')
    image_data = buffer.getvalue()

    # Créer l'analyzer
    analyzer = create_vision_analyzer()

    # Tester la conversion
    base64_str, media_type = analyzer._image_to_base64(image_data, "image/jpeg")

    assert base64_str is not None
    assert len(base64_str) > 0
    assert media_type == "image/jpeg"

    # Vérifier que c'est bien du base64 valide
    decoded = base64.b64decode(base64_str)
    assert len(decoded) > 0

    print(f"✅ Image converted to base64 - Size: {len(base64_str)} chars")


@pytest.mark.asyncio
async def test_vision_analyzer_prompt_building():
    """Test 3: Construction du prompt vétérinaire"""
    from generation.claude_vision_analyzer import create_vision_analyzer

    analyzer = create_vision_analyzer(language="fr")

    # Construire un prompt
    prompt = analyzer._build_veterinary_prompt(
        user_query="Cette poule a l'air malade, qu'est-ce qu'elle a ?",
        context_docs=[
            {"content": "La coccidiose cause des diarrhées sanglantes", "metadata": {}}
        ],
        language="fr"
    )

    assert prompt is not None
    assert "vétérinaire" in prompt.lower()
    assert "diagnostic" in prompt.lower()
    assert "FRANÇAIS" in prompt
    assert "coccidiose" in prompt.lower()  # Context doc included

    print("✅ Veterinary prompt built successfully")
    print(f"   Prompt length: {len(prompt)} chars")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - skipping live API test"
)
async def test_vision_analyzer_live_api():
    """Test 4: Test réel avec l'API Claude (nécessite ANTHROPIC_API_KEY)"""
    from generation.claude_vision_analyzer import create_vision_analyzer

    # Créer une image test simple
    test_image = Image.new('RGB', (200, 200), color='blue')

    # Ajouter un texte simple pour que Claude ait quelque chose à voir
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(test_image)
    draw.text((50, 100), "TEST IMAGE", fill='white')

    buffer = BytesIO()
    test_image.save(buffer, format='JPEG')
    image_data = buffer.getvalue()

    # Créer l'analyzer
    analyzer = create_vision_analyzer(language="en")

    # Analyser l'image
    result = await analyzer.analyze_medical_image(
        image_data=image_data,
        user_query="What do you see in this test image?",
        content_type="image/jpeg",
        context_docs=None,
        language="en",
        max_tokens=500,
    )

    assert result is not None
    assert result.get("success") is True
    assert result.get("analysis") is not None
    assert len(result.get("analysis", "")) > 0
    assert result.get("usage") is not None
    assert result["usage"]["total_tokens"] > 0

    print("✅ Live Claude Vision API call successful")
    print(f"   Analysis preview: {result['analysis'][:100]}...")
    print(f"   Tokens used: {result['usage']['total_tokens']}")


@pytest.mark.asyncio
async def test_vision_analyzer_error_handling():
    """Test 5: Gestion d'erreurs avec image invalide"""
    from generation.claude_vision_analyzer import create_vision_analyzer

    analyzer = create_vision_analyzer()

    # Données invalides
    invalid_data = b"not an image"

    # Doit lever une ValueError
    with pytest.raises(ValueError):
        analyzer._image_to_base64(invalid_data, "image/jpeg")

    print("✅ Error handling works correctly for invalid images")


@pytest.mark.asyncio
async def test_vision_analyzer_disclaimer():
    """Test 6: Vérification du disclaimer vétérinaire"""
    from generation.claude_vision_analyzer import create_vision_analyzer

    analyzer = create_vision_analyzer()

    # Tester disclaimer en plusieurs langues
    for lang in ["fr", "en", "es", "de"]:
        disclaimer = analyzer._get_veterinary_disclaimer(lang)

        assert disclaimer is not None
        assert len(disclaimer) > 0
        assert "⚠️" in disclaimer
        # Le disclaimer doit mentionner la consultation vétérinaire
        assert any(word in disclaimer.lower() for word in ["vétérinaire", "veterinarian", "veterinario", "tierarzt"])

        print(f"✅ Disclaimer verified for language: {lang}")


# === TESTS D'INTÉGRATION (NÉCESSITENT LES SERVICES) ===

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Integration tests require ANTHROPIC_API_KEY"
)
async def test_full_vision_pipeline():
    """
    Test 7: Pipeline complet - Upload backend + Analyse LLM

    NOTE: Ce test nécessite que les services backend et LLM soient en cours d'exécution
    """
    # Ce test sera exécuté manuellement avec les serveurs en marche
    pytest.skip("Manual integration test - requires running backend and LLM services")


# === NOTES POUR TESTS MANUELS ===

def print_manual_test_instructions():
    """
    Instructions pour tester manuellement le système complet
    """
    instructions = """
    ═══════════════════════════════════════════════════════════════════════════
    TESTS MANUELS - SYSTÈME VISION MÉDICAL
    ═══════════════════════════════════════════════════════════════════════════

    1. DÉMARRER LES SERVICES:
       Terminal 1: cd backend && python -m uvicorn app.main:app --reload --port 8001
       Terminal 2: cd llm && python main.py

    2. TESTER L'UPLOAD D'IMAGE (Backend):
       curl -X POST http://localhost:8001/api/v1/images/upload \\
         -F "file=@test_image.jpg" \\
         -F "user_id=test-user-123" \\
         -F "description=Poule malade - diarrhée"

       Attendu: {"success": true, "image_id": "...", "url": "..."}

    3. TESTER L'ANALYSE VISION (LLM):
       curl -X POST http://localhost:8000/llm/chat-with-image \\
         -F "image_url=<URL_FROM_STEP_2>" \\
         -F "message=Cette poule a des diarrhées, qu'est-ce qu'elle a ?" \\
         -F "tenant_id=test-tenant" \\
         -F "language=fr" \\
         -F "use_rag_context=true"

       Attendu: {"success": true, "analysis": "...", "metadata": {...}}

    4. TESTER AVEC UPLOAD DIRECT (LLM):
       curl -X POST http://localhost:8000/llm/chat-with-image \\
         -F "file=@test_image.jpg" \\
         -F "message=What disease does this chicken have?" \\
         -F "language=en"

    5. HEALTH CHECK VISION:
       curl http://localhost:8000/llm/vision/health

       Attendu: {"status": "healthy", "configured": true}

    ═══════════════════════════════════════════════════════════════════════════
    """
    print(instructions)


if __name__ == "__main__":
    print_manual_test_instructions()
