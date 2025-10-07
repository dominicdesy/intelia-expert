# -*- coding: utf-8 -*-
"""
api/endpoints_admin.py - Admin endpoints for system management

Includes:
- RAGAS evaluation trigger and results
- System diagnostics
- Performance monitoring
"""

import logging
import asyncio
import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from config.config import BASE_PATH

logger = logging.getLogger(__name__)


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
# HELPER FUNCTIONS
# ============================================================================


def estimate_evaluation_cost(test_cases: int, llm_model: str) -> Dict[str, Any]:
    """Estimate duration and cost for evaluation"""

    # Duration estimation (~6s per question for GPT-4o-mini)
    duration_per_case = 6 if llm_model == "gpt-4o-mini" else 10
    estimated_duration = test_cases * duration_per_case

    # Cost estimation
    cost_per_case = 0.01 if llm_model == "gpt-4o-mini" else 0.15
    estimated_cost = test_cases * cost_per_case

    return {
        "estimated_duration_seconds": estimated_duration,
        "estimated_cost_usd": round(estimated_cost, 2),
    }


async def run_ragas_evaluation_background(
    test_cases: int, llm_model: str, use_simulation: bool = False
):
    """Run RAGAS evaluation in background"""

    try:
        logger.info(
            f"🚀 Starting RAGAS evaluation: {test_cases} cases, model={llm_model}, simulate={use_simulation}"
        )

        # Import here to avoid circular dependencies
        import sys
        from pathlib import Path

        # Add llm directory to path if needed
        llm_dir = Path(__file__).parent.parent
        if str(llm_dir) not in sys.path:
            sys.path.insert(0, str(llm_dir))

        from scripts.run_ragas_evaluation import run_evaluation

        # Run evaluation
        result = await run_evaluation(
            num_test_cases=test_cases,
            llm_model=llm_model,
            use_real_rag=not use_simulation,
        )

        logger.info(
            f"✅ RAGAS evaluation completed: Overall score = {result['scores']['overall']:.2%}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Error in RAGAS evaluation: {e}", exc_info=True)
        raise


def get_latest_evaluation_file() -> Optional[str]:
    """Get path to latest evaluation results file"""

    try:
        # Find all evaluation files
        files = glob.glob("logs/ragas_evaluation_*.json")

        if not files:
            return None

        # Return most recent
        return max(files, key=lambda x: Path(x).stat().st_mtime)

    except Exception as e:
        logger.error(f"Error finding evaluation files: {e}")
        return None


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
        return _services.get(name)

    # ========================================================================
    # RAGAS EVALUATION ENDPOINTS
    # ========================================================================

    @router.post("/evaluate-rag", response_model=EvaluationStatus)
    async def trigger_ragas_evaluation(
        request: EvaluationRequest, background_tasks: BackgroundTasks
    ):
        """
        Trigger RAGAS evaluation in background.

        The evaluation will run asynchronously and results will be saved to
        logs/ragas_evaluation_{timestamp}.json

        **Cost estimates (approximate):**
        - test_cases=3: ~$0.03, ~18 seconds
        - test_cases=5: ~$0.05, ~30 seconds
        - test_cases=10: ~$0.10, ~60 seconds
        - test_cases=28: ~$0.50, ~3 minutes

        **Example:**
        ```
        POST /admin/evaluate-rag
        {
            "test_cases": 5,
            "llm_model": "gpt-4o-mini",
            "use_simulation": false
        }
        ```
        """

        # Estimate cost
        estimates = estimate_evaluation_cost(request.test_cases, request.llm_model)

        # Add task to background
        background_tasks.add_task(
            run_ragas_evaluation_background,
            test_cases=request.test_cases,
            llm_model=request.llm_model,
            use_simulation=request.use_simulation,
        )

        logger.info(
            f"📊 RAGAS evaluation queued: {request.test_cases} cases, model={request.llm_model}"
        )

        return EvaluationStatus(
            status="evaluation_started",
            message=f"RAGAS evaluation started with {request.test_cases} test cases. "
            f"Results will be available in ~{estimates['estimated_duration_seconds']}s. "
            f"Check /admin/evaluation-results endpoint.",
            test_cases=request.test_cases,
            llm_model=request.llm_model,
            estimated_duration_seconds=estimates["estimated_duration_seconds"],
            estimated_cost_usd=estimates["estimated_cost_usd"],
        )

    @router.get("/evaluation-results")
    async def get_evaluation_results():
        """
        Get latest RAGAS evaluation results.

        Returns the most recent evaluation results from logs directory.

        **Example response:**
        ```json
        {
            "scores": {
                "context_precision": 0.89,
                "context_recall": 0.85,
                "faithfulness": 0.91,
                "answer_relevancy": 0.84,
                "overall": 0.87
            },
            "summary": "✅ Très Bon: Qualité élevée (80-90%)",
            "timestamp": "2025-10-07T14:30:00",
            "llm_model": "gpt-4o-mini",
            "num_test_cases": 5,
            "duration_seconds": 32.5
        }
        ```
        """

        latest_file = get_latest_evaluation_file()

        if not latest_file:
            raise HTTPException(
                status_code=404,
                detail="No evaluation results found. Run /admin/evaluate-rag first.",
            )

        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                results = json.load(f)

            # Extract key information
            return {
                "scores": results.get("scores", {}),
                "summary": results.get("summary", ""),
                "timestamp": results.get("timestamp", ""),
                "llm_model": results.get("llm_model", ""),
                "num_test_cases": results.get("num_test_cases", 0),
                "duration_seconds": results.get("duration_seconds", 0),
                "file_path": latest_file,
            }

        except Exception as e:
            logger.error(f"Error reading evaluation results: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error reading evaluation results: {str(e)}"
            )

    @router.get("/evaluation-history")
    async def get_evaluation_history(limit: int = 10):
        """
        Get history of RAGAS evaluations.

        Args:
            limit: Maximum number of evaluations to return (default: 10)

        Returns list of evaluation summaries sorted by date (most recent first).

        **Example:**
        ```
        GET /admin/evaluation-history?limit=5
        ```
        """

        try:
            # Find all evaluation files
            files = glob.glob("logs/ragas_evaluation_*.json")

            if not files:
                return {
                    "count": 0,
                    "evaluations": [],
                    "message": "No evaluation history found",
                }

            # Sort by modification time (most recent first)
            files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)

            # Limit results
            files = files[:limit]

            # Extract summary from each file
            evaluations = []
            for filepath in files:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    evaluations.append(
                        {
                            "timestamp": data.get("timestamp", ""),
                            "overall_score": data.get("scores", {}).get("overall", 0),
                            "num_test_cases": data.get("num_test_cases", 0),
                            "llm_model": data.get("llm_model", ""),
                            "duration_seconds": data.get("duration_seconds", 0),
                            "file_path": filepath,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error reading {filepath}: {e}")
                    continue

            return {"count": len(evaluations), "evaluations": evaluations}

        except Exception as e:
            logger.error(f"Error getting evaluation history: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting evaluation history: {str(e)}",
            )

    @router.delete("/evaluation-results/{filename}")
    async def delete_evaluation_result(filename: str):
        """
        Delete a specific evaluation result file.

        **Warning:** This action is irreversible.

        **Example:**
        ```
        DELETE /admin/evaluation-results/ragas_evaluation_20251007_143000.json
        ```
        """

        # Security: only allow deleting ragas_evaluation_*.json files
        if not filename.startswith("ragas_evaluation_") or not filename.endswith(
            ".json"
        ):
            raise HTTPException(
                status_code=400, detail="Invalid filename format for deletion"
            )

        filepath = f"logs/{filename}"

        if not Path(filepath).exists():
            raise HTTPException(status_code=404, detail="Evaluation file not found")

        try:
            Path(filepath).unlink()
            logger.info(f"🗑️ Deleted evaluation file: {filepath}")

            return {"status": "deleted", "filename": filename, "filepath": filepath}

        except Exception as e:
            logger.error(f"Error deleting evaluation file: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting file: {str(e)}"
            )

    # ========================================================================
    # INFO ENDPOINTS
    # ========================================================================

    @router.get("/info")
    async def admin_info():
        """
        Get admin endpoints information.

        Returns available admin operations and system status.
        """

        return {
            "endpoints": {
                "evaluate-rag": {
                    "method": "POST",
                    "description": "Trigger RAGAS evaluation",
                    "cost": "$0.05-0.50 depending on test_cases",
                },
                "evaluation-results": {
                    "method": "GET",
                    "description": "Get latest evaluation results",
                },
                "evaluation-history": {
                    "method": "GET",
                    "description": "Get evaluation history",
                },
            },
            "evaluation_info": {
                "dataset_size": 28,
                "categories": [
                    "calculations",
                    "diagnostics",
                    "nutrition",
                    "environment",
                    "comparative",
                    "multilingual",
                    "conversational",
                ],
                "cost_estimates": {
                    "test_3_cases": {"cost_usd": 0.03, "duration_seconds": 18},
                    "quick_5_cases": {"cost_usd": 0.05, "duration_seconds": 30},
                    "full_28_cases": {"cost_usd": 0.50, "duration_seconds": 180},
                },
            },
            "system_status": {
                "services_available": list(_services.keys()),
                "rag_engine_initialized": bool(get_service("rag_engine")),
            },
        }

    return router
