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
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from config.config import BASE_PATH

logger = logging.getLogger(__name__)


# Custom JSON encoder pour gérer numpy arrays et valeurs non-finies
class NumpyEncoder(json.JSONEncoder):
    """JSON encoder qui gère les types numpy et valeurs float invalides"""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.generic):
            return obj.item()
        return super().default(obj)

    def encode(self, obj):
        """Override encode to handle NaN/Infinity values"""
        def sanitize(o):
            if isinstance(o, float):
                if np.isnan(o):
                    return 0.0  # Replace NaN with 0
                elif np.isinf(o):
                    return 1.0 if o > 0 else 0.0  # Replace Inf with 1, -Inf with 0
            elif isinstance(o, dict):
                return {k: sanitize(v) for k, v in o.items()}
            elif isinstance(o, list):
                return [sanitize(item) for item in o]
            return o

        return super().encode(sanitize(obj))


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

    @router.post("/evaluate-rag")
    async def trigger_ragas_evaluation(request: EvaluationRequest):
        """
        Run RAGAS evaluation synchronously and return results immediately.

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

        **Returns:** Complete evaluation results with scores
        """

        # Estimate cost
        estimates = estimate_evaluation_cost(request.test_cases, request.llm_model)

        logger.info(
            f"🚀 Starting RAGAS evaluation: {request.test_cases} cases, model={request.llm_model} "
            f"(estimated: {estimates['estimated_duration_seconds']}s, ${estimates['estimated_cost_usd']})"
        )

        # Run evaluation synchronously
        try:
            result = await run_ragas_evaluation_background(
                test_cases=request.test_cases,
                llm_model=request.llm_model,
                use_simulation=request.use_simulation,
            )

            logger.info(
                f"✅ RAGAS evaluation completed: Overall score = {result['scores']['overall']:.2%}"
            )

            # Retourner avec JSONResponse et NumpyEncoder pour gérer numpy arrays
            return JSONResponse(
                content=json.loads(json.dumps(result, cls=NumpyEncoder))
            )

        except Exception as e:
            logger.error(f"❌ Error during RAGAS evaluation: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Evaluation failed: {str(e)}"
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

    @router.get("/debug-imports")
    async def debug_imports():
        """
        Debug endpoint to check RAGAS dependencies availability.

        Returns import status for ragas, datasets, and langchain-openai.
        """
        import_status = {}

        # Test RAGAS
        try:
            from ragas import evaluate
            from ragas.metrics import context_precision
            import_status["ragas"] = {"available": True, "version": "imported"}
        except ImportError as e:
            import_status["ragas"] = {"available": False, "error": str(e)}

        # Test datasets
        try:
            from datasets import Dataset
            import_status["datasets"] = {"available": True, "version": "imported"}
        except ImportError as e:
            import_status["datasets"] = {"available": False, "error": str(e)}

        # Test langchain-openai
        try:
            from langchain_openai import ChatOpenAI
            import_status["langchain_openai"] = {"available": True, "version": "imported"}
        except ImportError as e:
            import_status["langchain_openai"] = {"available": False, "error": str(e)}

        return {
            "imports": import_status,
            "ready_for_evaluation": all(
                imp["available"] for imp in import_status.values()
            ),
        }

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
                    "description": "Run RAGAS evaluation synchronously (returns results immediately)",
                    "cost": "$0.05-0.50 depending on test_cases",
                    "duration": "18s-3min depending on test_cases",
                },
                "evaluation-results": {
                    "method": "GET",
                    "description": "Get latest evaluation results (file-based, may not work on ephemeral filesystems)",
                },
                "evaluation-history": {
                    "method": "GET",
                    "description": "Get evaluation history (file-based, may not work on ephemeral filesystems)",
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
                "rag_engine_initialized": bool(get_service("rag_engine_enhanced") or get_service("rag_engine")),
            },
        }

    @router.get("/reranker-status")
    async def check_reranker_status():
        """
        Check Cohere reranker configuration and status.

        Returns details about reranker availability, configuration, and statistics.
        """
        import os

        status = {
            "cohere_api_key_set": bool(os.getenv("COHERE_API_KEY")),
            "cohere_model": os.getenv("COHERE_RERANK_MODEL", "rerank-multilingual-v3.0"),
            "cohere_top_n": int(os.getenv("COHERE_RERANK_TOP_N", "3")),
            "reranker_available": False,
            "reranker_enabled": False,
            "reranker_stats": None,
            "weaviate_core_available": False,
        }

        # Check if reranker module is available
        try:
            from retrieval.reranker import CohereReranker
            status["reranker_available"] = True

            # Try to initialize reranker
            reranker = CohereReranker()
            status["reranker_enabled"] = reranker.is_enabled()

            if status["reranker_enabled"]:
                status["reranker_stats"] = reranker.get_stats()

        except ImportError as e:
            status["import_error"] = str(e)
        except Exception as e:
            status["initialization_error"] = str(e)

        # Check Weaviate Core reranker integration
        try:
            # Try both possible service names
            rag_engine = get_service("rag_engine_enhanced") or get_service("rag_engine")
            if rag_engine and hasattr(rag_engine, "weaviate_core"):
                weaviate_core = rag_engine.weaviate_core
                status["weaviate_core_available"] = bool(weaviate_core)

                if weaviate_core and hasattr(weaviate_core, "reranker"):
                    status["weaviate_reranker_configured"] = bool(weaviate_core.reranker)
                    if weaviate_core.reranker:
                        status["weaviate_reranker_enabled"] = weaviate_core.reranker.is_enabled()

                if weaviate_core and hasattr(weaviate_core, "optimization_stats"):
                    status["weaviate_stats"] = {
                        "cohere_reranking_used": weaviate_core.optimization_stats.get("cohere_reranking_used", 0),
                        "hybrid_searches": weaviate_core.optimization_stats.get("hybrid_searches", 0),
                        "intelligent_rrf_used": weaviate_core.optimization_stats.get("intelligent_rrf_used", 0),
                        "total_queries": weaviate_core.optimization_stats.get("total_queries", 0),
                    }
        except Exception as e:
            status["weaviate_check_error"] = str(e)

        # Check PostgreSQL retriever reranker
        try:
            if rag_engine and hasattr(rag_engine, "postgresql_retriever"):
                postgresql_retriever = rag_engine.postgresql_retriever
                if postgresql_retriever and hasattr(postgresql_retriever, "reranker"):
                    pg_reranker = postgresql_retriever.reranker
                    status["postgresql_reranker_configured"] = bool(pg_reranker)
                    if pg_reranker:
                        status["postgresql_reranker_enabled"] = pg_reranker.is_enabled()
                        # Get real stats from PostgreSQL reranker
                        if hasattr(pg_reranker, "get_stats"):
                            status["postgresql_reranker_stats"] = pg_reranker.get_stats()
        except Exception as e:
            status["postgresql_check_error"] = str(e)

        return status

    @router.get("/rrf-diagnostic")
    async def check_rrf_diagnostic():
        """
        Diagnostic complet pour Intelligent RRF.

        Vérifie toutes les conditions nécessaires pour que RRF intelligent fonctionne.
        """
        import os
        from config.config import ENABLE_INTELLIGENT_RRF, CACHE_ENABLED

        diagnostic = {
            "config": {
                "ENABLE_INTELLIGENT_RRF": ENABLE_INTELLIGENT_RRF,
                "CACHE_ENABLED": CACHE_ENABLED,
                "REDIS_URL_set": bool(os.getenv("REDIS_URL")),
            },
            "imports": {
                "IntelligentRRFFusion_available": False,
            },
            "runtime": {
                "cache_manager_exists": False,
                "cache_manager_enabled": False,
                "intelligent_rrf_initialized": False,
                "weaviate_core_exists": False,
            },
            "conclusion": "UNKNOWN"
        }

        # Check imports
        try:
            from retrieval.enhanced_rrf_fusion import IntelligentRRFFusion
            diagnostic["imports"]["IntelligentRRFFusion_available"] = True
        except ImportError as e:
            diagnostic["imports"]["import_error"] = str(e)

        # Check runtime state
        try:
            # Try both possible service names
            rag_engine = get_service("rag_engine_enhanced") or get_service("rag_engine")
            diagnostic["runtime"]["rag_engine_found"] = bool(rag_engine)

            if rag_engine:
                # Check cache_core service separately
                cache_core = get_service("cache_core")
                diagnostic["runtime"]["cache_core_service_exists"] = bool(cache_core)
                if cache_core:
                    diagnostic["runtime"]["cache_manager_exists"] = True
                    diagnostic["runtime"]["cache_manager_enabled"] = getattr(cache_core, "enabled", False)
                    diagnostic["runtime"]["cache_manager_initialized"] = getattr(cache_core, "is_initialized", False)

                # Check weaviate core
                if hasattr(rag_engine, "weaviate_core"):
                    weaviate_core = rag_engine.weaviate_core
                    diagnostic["runtime"]["weaviate_core_exists"] = bool(weaviate_core)

                    if weaviate_core:
                        # Check intelligent_rrf
                        has_intelligent_rrf = hasattr(weaviate_core, "intelligent_rrf")
                        intelligent_rrf = getattr(weaviate_core, "intelligent_rrf", None)

                        diagnostic["runtime"]["intelligent_rrf_initialized"] = bool(intelligent_rrf)
                        diagnostic["runtime"]["intelligent_rrf_attribute_exists"] = has_intelligent_rrf

                        # CRITICAL: Check if intelligent_rrf.enabled is True
                        if intelligent_rrf:
                            diagnostic["runtime"]["intelligent_rrf_enabled"] = getattr(intelligent_rrf, "enabled", False)
                            diagnostic["runtime"]["intelligent_rrf_has_enabled_attr"] = hasattr(intelligent_rrf, "enabled")

                        # Check cache_manager dans weaviate_core
                        has_cache_manager = hasattr(weaviate_core, "cache_manager")
                        cache_manager_value = getattr(weaviate_core, "cache_manager", None)

                        diagnostic["runtime"]["weaviate_cache_manager_exists"] = has_cache_manager
                        diagnostic["runtime"]["weaviate_cache_manager_value"] = bool(cache_manager_value)

        except Exception as e:
            diagnostic["runtime"]["error"] = str(e)

        # Conclusion
        if (diagnostic["config"]["ENABLE_INTELLIGENT_RRF"] and
            diagnostic["imports"]["IntelligentRRFFusion_available"] and
            diagnostic["runtime"].get("cache_manager_enabled", False) and
            diagnostic["runtime"].get("intelligent_rrf_initialized", False) and
            diagnostic["runtime"].get("intelligent_rrf_enabled", False)):
            diagnostic["conclusion"] = "✅ RRF Intelligent ACTIF"
        elif not diagnostic["config"]["ENABLE_INTELLIGENT_RRF"]:
            diagnostic["conclusion"] = "❌ ENABLE_INTELLIGENT_RRF=false"
        elif not diagnostic["imports"]["IntelligentRRFFusion_available"]:
            diagnostic["conclusion"] = "❌ IntelligentRRFFusion non importable"
        elif not diagnostic["runtime"].get("cache_manager_enabled", False):
            diagnostic["conclusion"] = "❌ Cache Manager désactivé ou non connecté"
        elif not diagnostic["runtime"].get("intelligent_rrf_initialized", False):
            diagnostic["conclusion"] = "❌ intelligent_rrf non initialisé dans WeaviateCore"
        elif not diagnostic["runtime"].get("intelligent_rrf_enabled", False):
            diagnostic["conclusion"] = "❌ intelligent_rrf.enabled=False (lecture env variable)"
        else:
            diagnostic["conclusion"] = "❌ Conditions partiellement remplies"

        return diagnostic

    @router.get("/service-registry-diagnostic")
    async def service_registry_diagnostic():
        """
        Diagnose service registry to understand why chat endpoint can't access RAG engine.

        Returns:
            Detailed analysis of service availability and initialization
        """
        diagnostic = {
            "services_in_registry": list(_services.keys()) if _services else [],
            "health_monitor_exists": bool(get_service("health_monitor")),
            "rag_engine_tests": {}
        }

        try:
            # Test 1: Direct access
            rag_direct = get_service("rag_engine_enhanced")
            diagnostic["rag_engine_tests"]["direct_access"] = {
                "found": bool(rag_direct),
                "type": type(rag_direct).__name__ if rag_direct else None,
                "is_initialized": getattr(rag_direct, "is_initialized", None) if rag_direct else None
            }

            # Test 2: Via health_monitor (same as chat endpoint)
            health_monitor = get_service("health_monitor")
            if health_monitor:
                rag_via_health = health_monitor.get_service("rag_engine_enhanced")
                diagnostic["rag_engine_tests"]["via_health_monitor"] = {
                    "health_monitor_found": True,
                    "rag_found": bool(rag_via_health),
                    "type": type(rag_via_health).__name__ if rag_via_health else None,
                    "is_initialized": getattr(rag_via_health, "is_initialized", None) if rag_via_health else None
                }

                # Test 3: All services in health_monitor
                if hasattr(health_monitor, "get_all_services"):
                    all_services = health_monitor.get_all_services()
                    diagnostic["health_monitor_services"] = list(all_services.keys())
            else:
                diagnostic["rag_engine_tests"]["via_health_monitor"] = {
                    "health_monitor_found": False
                }

        except Exception as e:
            diagnostic["error"] = str(e)
            import traceback
            diagnostic["traceback"] = traceback.format_exc()

        return diagnostic

    @router.post("/ood-diagnostic")
    async def ood_diagnostic_endpoint(query: str = "What is coccidiosis in broilers?"):
        """
        Test OOD detector directly to diagnose why queries are rejected.

        Args:
            query: Test query to classify (default: disease question)

        Returns:
            Detailed OOD detection result
        """
        diagnostic = {
            "test_query": query,
            "ood_detector_available": False,
            "detection_result": None,
            "error": None
        }

        try:
            # Get RAG engine
            rag_engine = get_service("rag_engine_enhanced") or get_service("rag_engine")
            diagnostic["rag_engine_found"] = bool(rag_engine)

            if not rag_engine:
                diagnostic["error"] = "RAG engine not found in services"
                return diagnostic

            # Get WeaviateCore
            weaviate_core = getattr(rag_engine, "weaviate_core", None)
            diagnostic["weaviate_core_found"] = bool(weaviate_core)

            if not weaviate_core:
                diagnostic["error"] = "WeaviateCore not found in RAG engine"
                return diagnostic

            # Get OOD detector
            ood_detector = getattr(weaviate_core, "ood_detector", None)
            diagnostic["ood_detector_available"] = bool(ood_detector)
            diagnostic["ood_detector_type"] = type(ood_detector).__name__ if ood_detector else None

            if not ood_detector:
                diagnostic["error"] = "OOD detector not initialized in WeaviateCore"
                return diagnostic

            # Test detection
            logger.info(f"Testing OOD detector with query: {query}")
            is_in_domain, confidence, details = ood_detector.is_in_domain(query, language="en")

            diagnostic["detection_result"] = {
                "is_in_domain": is_in_domain,
                "confidence": confidence,
                "details": details
            }

        except Exception as e:
            logger.error(f"OOD diagnostic error: {e}")
            diagnostic["error"] = str(e)
            import traceback
            diagnostic["traceback"] = traceback.format_exc()

        return diagnostic

    return router
