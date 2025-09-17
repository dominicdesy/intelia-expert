from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import os

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class DetailedHealthResponse(BaseModel):
    api_status: str
    memory_usage: str
    cpu_usage: str
    disk_space: str
    openai_configured: bool
    rag_configured: bool
    timestamp: str


@router.get("/", response_model=HealthResponse)
async def health():
    """
    Simple health check endpoint.
    """
    return HealthResponse(
        status="running",
        version=os.getenv("API_VERSION", "1.0"),
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health():
    """
    Detailed health check with configuration diagnostics.
    """
    vector_url = os.getenv("VECTOR_STORE_URL")
    vector_key = os.getenv("VECTOR_STORE_KEY")
    return DetailedHealthResponse(
        api_status="running",
        memory_usage="unknown",
        cpu_usage="unknown",
        disk_space="unknown",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        rag_configured=bool(vector_url and vector_key and os.getenv("OPENAI_API_KEY")),
        timestamp=datetime.utcnow().isoformat(),
    )
