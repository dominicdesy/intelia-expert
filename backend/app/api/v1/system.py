from fastapi import APIRouter
import os
from datetime import datetime

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
            "rag": "checking"
        },
        "version": "1.0.0"
    }

@router.get("/metrics")
async def get_metrics():
    """Get system performance metrics."""
    return {
        "status": "active",
        "metrics": {
            "uptime": "N/A",
            "memory_usage": "N/A",
            "cpu_usage": "N/A",
            "response_time_avg": "N/A"
        }
    }

@router.get("/status")
async def get_system_status():
    """Get detailed system status."""
    return {
        "api_status": "running",
        "database_status": "not_connected", 
        "rag_status": "checking",
        "ai_status": "checking",
        "timestamp": datetime.now().isoformat()
    }
