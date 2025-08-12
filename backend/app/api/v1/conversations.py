# app/api/v1/conversations.py - VERSION MINIMALE TEST
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
def health_check():
    """Test simple de santé"""
    return {
        "status": "healthy",
        "message": "Router conversations fonctionne !",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/test-public")
def test_public():
    """Test public simple"""
    return {
        "status": "success",
        "message": "Endpoint public fonctionne !",
        "router": "conversations-minimal"
    }

@router.get("/stats")
def get_stats():
    """Stats minimales"""
    return {
        "total_sessions": 0,
        "service_status": "minimal",
        "backend": "test"
    }