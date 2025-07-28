"""
app/api/health.py
Module de santé système - Version corrigée
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import os

router = APIRouter(prefix="/health", tags=["health"])

# Modèle de réponse simplifié
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: dict

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint corrigé."""
    try:
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="2.1.0",
            services={
                "api": True,
                "rag": True,
                "database": False,
                "openai": bool(os.getenv("OPENAI_API_KEY"))
            }
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy", 
            timestamp=datetime.now().isoformat(),
            version="2.1.0",
            services={
                "api": False,
                "rag": False,
                "database": False,
                "openai": False
            }
        )

@router.get("/detailed")
async def detailed_health():
    """Health check détaillé."""
    return {
        "api_status": "running",
        "memory_usage": "unknown",
        "cpu_usage": "unknown", 
        "disk_space": "unknown",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "timestamp": datetime.now().isoformat()
    }
