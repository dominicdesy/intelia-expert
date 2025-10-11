from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import os
from datetime import datetime
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/system")


@router.get("/health")
async def health_check():
    """Check system health."""
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "running",
            "openai": "configured" if openai_configured else "not_configured",
            "rag": "checking",
        },
        "version": "1.0.0",
    }


@router.get("/metrics")
async def get_metrics(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get system performance metrics.
    ⚠️ SÉCURISÉ: Accès admin uniquement
    """
    # Vérifier les droits admin
    user_type = current_user.get("user_type", "user")
    if user_type not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Accès refusé. Droits administrateur requis."
        )

    return {
        "status": "active",
        "metrics": {
            "uptime": "N/A",
            "memory_usage": "N/A",
            "cpu_usage": "N/A",
            "response_time_avg": "N/A",
        },
    }


@router.get("/status")
async def get_system_status():
    """Get detailed system status."""
    return {
        "api_status": "running",
        "database_status": "not_connected",
        "rag_status": "checking",
        "ai_status": "checking",
        "timestamp": datetime.now().isoformat(),
    }
