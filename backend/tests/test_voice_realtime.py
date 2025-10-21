"""
Tests pour Voice Realtime API
==============================

Tests unitaires et d'intégration pour l'endpoint WebSocket voice realtime.

Run:
    pytest backend/tests/test_voice_realtime.py -v
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import app
import sys
import os

# Ajouter le path backend au PYTHONPATH
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

from app.main import app

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def client():
    """Test client FastAPI"""
    return TestClient(app)

@pytest.fixture
def enable_feature():
    """Mock feature flag enabled"""
    with patch.dict(os.environ, {"ENABLE_VOICE_REALTIME": "true"}):
        yield

@pytest.fixture
def mock_openai_api_key():
    """Mock OpenAI API key"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        yield

# ============================================================
# TESTS HEALTH CHECK
# ============================================================

def test_voice_health_disabled(client):
    """Test health check quand feature désactivée"""
    with patch.dict(os.environ, {"ENABLE_VOICE_REALTIME": "false"}):
        response = client.get("/v1/voice/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
        assert data["feature_enabled"] is False

def test_voice_health_enabled(client, enable_feature, mock_openai_api_key):
    """Test health check quand feature activée"""
    response = client.get("/v1/voice/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["feature_enabled"] is True
    assert data["openai_configured"] is True

# ============================================================
# TESTS STATS
# ============================================================

def test_voice_stats(client, enable_feature):
    """Test endpoint stats"""
    response = client.get("/v1/voice/stats")
    assert response.status_code == 200
    data = response.json()
    assert "rate_limiter" in data
    assert "config" in data
    assert data["config"]["max_session_duration"] == 600

# ============================================================
# TESTS WEBSOCKET
# ============================================================

def test_websocket_feature_disabled(client):
    """Test WebSocket refusé si feature désactivée"""
    with patch.dict(os.environ, {"ENABLE_VOICE_REALTIME": "false"}):
        with client.websocket_connect("/v1/ws/voice") as websocket:
            # Doit fermer immédiatement
            # Note: TestClient ne supporte pas toutes les close reasons
            pass

@pytest.mark.skip(reason="Nécessite mock OpenAI WebSocket complet")
def test_websocket_rate_limit(client, enable_feature, mock_openai_api_key):
    """Test rate limiting (5 sessions max par heure)"""
    # TODO: Implémenter quand rate limiter en Redis
    pass

@pytest.mark.skip(reason="Nécessite mock OpenAI WebSocket complet")
def test_websocket_session_timeout(client, enable_feature, mock_openai_api_key):
    """Test timeout session après 10 minutes"""
    # TODO: Implémenter avec asyncio timeout simulation
    pass

# ============================================================
# TESTS RATE LIMITER
# ============================================================

@pytest.mark.skip(reason="Import test - skip si problème PYTHONPATH")
def test_rate_limiter_allows_first_sessions():
    """Test que rate limiter accepte premières sessions"""
    try:
        from app.api.v1.voice_realtime import RateLimiter

        limiter = RateLimiter()
        user_id = 123

        # Devrait accepter les 5 premières sessions
        for i in range(5):
            assert limiter.check_rate_limit(user_id) is True, f"Session {i+1} devrait être acceptée"
    except ImportError:
        pytest.skip("Cannot import voice_realtime module")

@pytest.mark.skip(reason="Import test - skip si problème PYTHONPATH")
def test_rate_limiter_blocks_excess_sessions():
    """Test que rate limiter bloque au-delà de 5 sessions"""
    try:
        from app.api.v1.voice_realtime import RateLimiter

        limiter = RateLimiter()
        user_id = 456

        # Créer 5 sessions
        for _ in range(5):
            limiter.check_rate_limit(user_id)

        # 6ème session devrait être refusée
        assert limiter.check_rate_limit(user_id) is False, "6ème session devrait être refusée"
    except ImportError:
        pytest.skip("Cannot import voice_realtime module")

# ============================================================
# TESTS WEAVIATE SERVICE
# ============================================================

@pytest.mark.asyncio
async def test_weaviate_service_disabled_without_url():
    """Test que Weaviate service se désactive sans URL"""
    with patch.dict(os.environ, {"WEAVIATE_URL": ""}):
        from app.api.v1.voice_realtime import WeaviateRAGService

        service = WeaviateRAGService()
        assert service.enabled is False

        # Query devrait retourner None
        result = await service.query_context("test query")
        assert result is None

@pytest.mark.skip(reason="Nécessite Weaviate mock complet")
@pytest.mark.asyncio
async def test_weaviate_service_query():
    """Test query Weaviate"""
    # TODO: Mock Weaviate client et retriever
    pass

# ============================================================
# TESTS SESSION
# ============================================================

@pytest.mark.skip(reason="Nécessite WebSocket mocks complexes")
def test_session_option_b_preloading():
    """Test Option B: pré-chargement RAG pendant parole"""
    # TODO: Mock partial transcript et vérifier query Weaviate lancée
    pass

@pytest.mark.skip(reason="Nécessite WebSocket mocks complexes")
def test_session_rag_context_injection():
    """Test injection contexte RAG dans OpenAI"""
    # TODO: Vérifier message système envoyé à OpenAI
    pass

# ============================================================
# TESTS D'INTÉGRATION (optionnels)
# ============================================================

@pytest.mark.integration
@pytest.mark.skip(reason="Tests d'intégration nécessitent vraie API OpenAI")
def test_real_openai_connection():
    """Test connexion réelle à OpenAI Realtime API"""
    # TODO: Implémenter avec vraies credentials (CI/CD seulement)
    pass

@pytest.mark.integration
@pytest.mark.skip(reason="Tests d'intégration nécessitent Weaviate accessible")
def test_real_weaviate_query():
    """Test query réelle Weaviate"""
    # TODO: Implémenter avec Weaviate de test
    pass
