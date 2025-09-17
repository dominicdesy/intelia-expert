from pydantic import BaseModel
from typing import Optional, Dict, List


class ExpertResponse(BaseModel):
    response: str
    rag_status: str
    rag_configured: bool
    model_used: str
    processing_time: float
    timestamp: str
    error: Optional[bool] = False


class SystemStatusResponse(BaseModel):
    ai_analyzer_available: bool
    api_client_available: bool
    rag_configured: bool
    rag_status: str
    services: Dict[str, bool]


class ExamplesResponse(BaseModel):
    examples: List[str]


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str
    version: str
    services: Dict[str, bool]
