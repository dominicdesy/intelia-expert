"""
Health Check Router
Service health and metrics endpoints
"""

from fastapi import APIRouter, Response, Depends
from app.models.schemas import HealthResponse
from app.models.llm_client import LLMClient
from app.config import settings
from app.utils.metrics import get_metrics, get_metrics_content_type, set_model_status
from app.dependencies import get_llm_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(llm_client: LLMClient = Depends(get_llm_client)):
    """
    Health check endpoint

    Returns service health status and model availability.

    **Example response:**
    ```json
    {
      "status": "healthy",
      "service": "llm",
      "version": "1.0.0",
      "provider": "huggingface",
      "model_loaded": true,
      "timestamp": "2025-10-27T14:30:00Z"
    }
    ```
    """
    logger.debug("Health check requested")

    # Check if LLM provider is available
    try:
        model_loaded = llm_client.is_available()
        status = "healthy" if model_loaded else "unhealthy"

        # Update Prometheus metric
        set_model_status(
            model=settings.huggingface_model if settings.llm_provider == "huggingface" else "intelia-llama",
            provider=settings.llm_provider,
            available=model_loaded
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        model_loaded = False
        status = "unhealthy"

    return HealthResponse(
        status=status,
        service=settings.service_name,
        version=settings.version,
        provider=settings.llm_provider,
        model_loaded=model_loaded,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format for scraping.

    **Metrics exposed:**
    - `llm_requests_total`: Total inference requests
    - `llm_inference_duration_seconds`: Inference latency histogram
    - `llm_tokens_generated_total`: Total tokens generated
    - `llm_tokens_prompt_total`: Total prompt tokens
    - `llm_model_loaded`: Model availability (1=loaded, 0=not loaded)
    - `llm_errors_total`: Total errors by type

    **Example output:**
    ```
    # HELP llm_requests_total Total number of LLM inference requests
    # TYPE llm_requests_total counter
    llm_requests_total{model="intelia-llama",status="success"} 1523.0
    llm_requests_total{model="intelia-llama",status="error"} 12.0

    # HELP llm_inference_duration_seconds LLM inference latency in seconds
    # TYPE llm_inference_duration_seconds histogram
    llm_inference_duration_seconds_bucket{le="0.5",model="intelia-llama"} 892.0
    llm_inference_duration_seconds_bucket{le="1.0",model="intelia-llama"} 1450.0
    ...
    ```
    """
    logger.debug("Metrics requested")

    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


@router.get("/")
async def root():
    """
    Root endpoint - Service info

    Returns basic service information.
    """
    return {
        "service": settings.service_name,
        "version": settings.version,
        "provider": settings.llm_provider,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }
