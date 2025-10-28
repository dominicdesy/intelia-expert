# -*- coding: utf-8 -*-
"""
api/endpoints_admin.py - Admin endpoints for system management
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_admin.py - Admin endpoints for system management

Includes:
- RAGAS evaluation trigger and results
- System diagnostics
- Performance monitoring
"""

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from config.config import BASE_PATH

from .admin_endpoint_handlers import (
    handle_trigger_ragas_evaluation,
    handle_get_evaluation_results,
    handle_get_evaluation_history,
    handle_delete_evaluation_result,
    handle_debug_imports,
    handle_admin_info,
    handle_reranker_status,
    handle_rrf_diagnostic,
    handle_service_registry_diagnostic,
    handle_ood_diagnostic,
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class EvaluationRequest(BaseModel):
    """Request model for RAGAS evaluation"""

    test_cases: int = Field(
        default=5, ge=1, le=100, description="Number of test cases to evaluate"
    )
    llm_model: str = Field(
        default="gpt-4o-mini", description="LLM model for evaluation"
    )
    use_simulation: bool = Field(
        default=False, description="Use simulation mode (don't call real RAG)"
    )


class EvaluationStatus(BaseModel):
    """Response model for evaluation status"""

    status: str
    message: str
    test_cases: Optional[int] = None
    llm_model: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class EvaluationResult(BaseModel):
    """Response model for evaluation results"""

    scores: Dict[str, float]
    summary: str
    timestamp: str
    llm_model: str
    num_test_cases: int
    duration_seconds: float


# ============================================================================
# ENDPOINT FACTORY
# ============================================================================


def create_admin_endpoints(services: Optional[Dict[str, Any]] = None) -> APIRouter:
    """
    Create admin endpoints router.

    Args:
        services: Dictionary of services (rag_engine, etc.)

    Returns:
        Configured APIRouter
    """

    router = APIRouter(prefix=f"{BASE_PATH}/admin", tags=["admin"])

    _services = services or {}

    def get_service(name: str) -> Any:
        """Helper to get service"""
        if name == "_all_services":
            return _services
        return _services.get(name)

    # ========================================================================
    # RAGAS EVALUATION ENDPOINTS
    # ========================================================================

    @router.post("/evaluate-rag")
    async def trigger_ragas_evaluation(request: EvaluationRequest):
        """Run RAGAS evaluation synchronously and return results immediately."""
        return await handle_trigger_ragas_evaluation(request)

    @router.get("/evaluation-results")
    async def get_evaluation_results():
        """Get latest RAGAS evaluation results."""
        return await handle_get_evaluation_results()

    @router.get("/evaluation-history")
    async def get_evaluation_history(limit: int = 10):
        """Get history of RAGAS evaluations."""
        return await handle_get_evaluation_history(limit)

    @router.delete("/evaluation-results/{filename}")
    async def delete_evaluation_result(filename: str):
        """Delete a specific evaluation result file."""
        return await handle_delete_evaluation_result(filename)

    # ========================================================================
    # PUBLIC RAGAS EVALUATION ENDPOINT (with API key)
    # ========================================================================

    @router.post("/public/evaluate-rag")
    async def public_trigger_ragas_evaluation(
        request: EvaluationRequest,
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ):
        """
        Public endpoint to run RAGAS evaluation with API key authentication.

        Usage:
            POST /llm/api/v1/admin/public/evaluate-rag
            Headers: X-API-Key: your-secret-key
            Body: {"test_cases": 10, "llm_model": "gpt-4o-mini"}

        API Key: Set RAGAS_API_KEY environment variable or use default
        """
        # Get API key from environment or use default
        expected_key = os.getenv("RAGAS_API_KEY", "intelia-ragas-2024")

        if not x_api_key or x_api_key != expected_key:
            raise HTTPException(
                status_code=403, detail="Invalid or missing X-API-Key header"
            )

        # Call the same handler as admin endpoint
        return await handle_trigger_ragas_evaluation(request)

    # ========================================================================
    # INFO ENDPOINTS
    # ========================================================================

    @router.get("/debug-imports")
    async def debug_imports():
        """Debug endpoint to check RAGAS dependencies availability."""
        return await handle_debug_imports()

    @router.get("/info")
    async def admin_info():
        """Get admin endpoints information."""
        return await handle_admin_info(get_service)

    @router.get("/reranker-status")
    async def check_reranker_status():
        """Check Cohere reranker configuration and status."""
        return await handle_reranker_status(get_service)

    @router.get("/rrf-diagnostic")
    async def check_rrf_diagnostic():
        """Diagnostic complet pour Intelligent RRF."""
        return await handle_rrf_diagnostic(get_service)

    @router.get("/service-registry-diagnostic")
    async def service_registry_diagnostic():
        """Diagnose service registry to understand service availability."""
        return await handle_service_registry_diagnostic(get_service)

    @router.post("/ood-diagnostic")
    async def ood_diagnostic_endpoint(query: str = "What is coccidiosis in broilers?"):
        """Test OOD detector directly to diagnose why queries are rejected."""
        return await handle_ood_diagnostic(get_service, query)

    return router
