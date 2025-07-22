from fastapi import APIRouter
from app.models.responses import HealthResponse
from app.config.settings import settings
from datetime import datetime

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=settings.VERSION,
        services={
            "api": True,
            "rag": True,
            "database": False
        }
    )
