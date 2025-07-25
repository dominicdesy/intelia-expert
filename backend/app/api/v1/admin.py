from fastapi import APIRouter, HTTPException
import logging
from typing import Dict, Any

router = APIRouter(prefix="/admin")
logger = logging.getLogger(__name__)

@router.get("/dashboard")
async def get_dashboard():
    """Get admin dashboard with comprehensive status."""
    try:
        from app.services.expert_service import expert_service
        
        # Get service status safely
        try:
            service_status = expert_service.get_status()
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            service_status = {
                "openai_configured": bool(expert_service.openai_client),
                "secrets_loaded": bool(expert_service.secrets.secrets),
                "rag_available": False,
                "rag_configured": False,
                "method": "error"
            }
        
        # Get RAG diagnostics safely
        try:
            rag_diagnostics = expert_service.get_rag_diagnostics()
        except Exception as e:
            logger.error(f"Error getting RAG diagnostics: {e}")
            rag_diagnostics = {
                "rag_available": False,
                "rag_configured": False,
                "rag_method": "error",
                "diagnostics": {"errors": [str(e)]}
            }
        
        return {
            "status": "active",
            "timestamp": expert_service._get_timestamp(),
            "services": {
                "openai": "✅ configured" if service_status.get("openai_configured", False) else "❌ not_configured",
                "secrets": "✅ loaded" if service_status.get("secrets_loaded", False) else "❌ not_loaded",
                "rag": _get_rag_status_icon(rag_diagnostics),
                "expert_service": "✅ operational"
            },
            "rag_detailed_status": rag_diagnostics,
            "metrics": {
                "total_questions": "N/A",
                "satisfaction_rate": "N/A", 
                "average_response_time": "N/A",
                "rag_usage_rate": "0%" if not rag_diagnostics.get("rag_configured") else "N/A"
            },
            "preferred_method": service_status.get("method", "unknown"),
            "recommendations": _get_recommendations(rag_diagnostics)
        }
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": expert_service._get_timestamp() if 'expert_service' in locals() else "unknown"
        }

@router.get("/rag/diagnostics")
async def get_rag_diagnostics():
    """Get comprehensive RAG system diagnostics."""
    try:
        from app.services.expert_service import expert_service
        
        diagnostics = expert_service.get_rag_diagnostics()
        
        return {
            "timestamp": expert_service._get_timestamp(),
            "rag_diagnostics": diagnostics,
            "status_summary": _analyze_rag_status(diagnostics),
            "troubleshooting_steps": _get_troubleshooting_steps(diagnostics)
        }
    except Exception as e:
        logger.error(f"RAG diagnostics error: {e}")
        return {
            "error": str(e),
            "timestamp": "unknown",
            "rag_diagnostics": {
                "rag_available": False,
                "rag_configured": False,
                "error": str(e)
            }
        }

@router.post("/rag/force-configure")
async def force_configure_rag():
    """Force RAG reconfiguration with detailed feedback."""
    try:
        from app.services.expert_service import expert_service
        
        logger.info("🔄 Force configuring RAG system...")
        
        # Force reconfiguration
        result = expert_service.force_configure_rag()
        
        # Get updated diagnostics
        try:
            diagnostics = expert_service.get_rag_diagnostics()
        except Exception as e:
            diagnostics = {"error": str(e)}
        
        return {
            "message": "RAG force configuration completed",
            "timestamp": expert_service._get_timestamp(),
            "configuration_result": result,
            "updated_diagnostics": diagnostics,
            "success": result.get("success", False)
        }
    except Exception as e:
        logger.error(f"RAG force configuration error: {e}")
        return {
            "error": str(e),
            "message": "RAG force configuration failed",
            "timestamp": "unknown",
            "success": False
        }

@router.get("/rag/test")
async def test_rag_comprehensive():
    """Comprehensive RAG system test."""
    try:
        from app.services.expert_service import expert_service
        
        test_question = "What is the optimal temperature for Ross 308 broilers?"
        
        try:
            result = await expert_service.ask_expert(test_question, "en")
            
            return {
                "timestamp": expert_service._get_timestamp(),
                "test_question": test_question,
                "test_result": result,
                "rag_working": result.get("rag_used", False),
                "success": result.get("success", False),
                "summary": "✅ RAG test completed" if result.get("success") else "❌ RAG test failed"
            }
        except Exception as e:
            return {
                "timestamp": expert_service._get_timestamp(),
                "test_question": test_question,
                "error": str(e),
                "rag_working": False,
                "success": False,
                "summary": f"❌ RAG test failed: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"RAG test error: {e}")
        return {
            "error": str(e),
            "timestamp": "unknown",
            "rag_working": False,
            "success": False
        }

@router.get("/rag/status")
async def get_rag_status():
    """Get detailed RAG system status."""
    try:
        from app.services.expert_service import expert_service
        
        diagnostics = expert_service.get_rag_diagnostics()
        
        return {
            "timestamp": expert_service._get_timestamp(),
            "rag_available": diagnostics.get("rag_available", False),
            "rag_configured": diagnostics.get("rag_configured", False),
            "rag_method": diagnostics.get("rag_method", "none"),
            "detailed_diagnostics": diagnostics.get("diagnostics", {}),
            "status_icon": _get_rag_status_icon(diagnostics),
            "human_readable_status": _get_human_readable_status(diagnostics)
        }
    except Exception as e:
        logger.error(f"RAG status error: {e}")
        return {
            "error": str(e),
            "timestamp": "unknown",
            "rag_available": False,
            "rag_configured": False
        }

@router.get("/analytics")
async def get_analytics():
    """Get usage analytics."""
    return {
        "status": "not_implemented",
        "message": "Detailed analytics coming soon",
        "available_metrics": [
            "question_volume_by_hour",
            "response_methods_distribution",
            "rag_usage_percentage", 
            "satisfaction_scores_trend",
            "response_times_distribution",
            "language_preference_distribution"
        ]
    }

@router.get("/documents")
async def get_documents_status():
    """Get RAG documents status."""
    try:
        from app.services.expert_service import expert_service
        
        try:
            diagnostics = expert_service.get_rag_diagnostics()
        except Exception as e:
            diagnostics = {"error": str(e), "rag_configured": False}
        
        return {
            "timestamp": expert_service._get_timestamp(),
            "rag_system": "✅ configured" if diagnostics.get("rag_configured") else "❌ not_configured",
            "documents_indexed": "N/A",
            "index_size": "N/A", 
            "last_update": "N/A",
            "embedding_method": diagnostics.get("diagnostics", {}).get("embedding_method", "unknown"),
            "full_diagnostics": diagnostics
        }
    except Exception as e:
        logger.error(f"Documents status error: {e}")
        return {
            "error": str(e),
            "timestamp": "unknown",
            "rag_system": "❌ error"
        }

@router.post("/documents/upload")
async def upload_document():
    """Upload document to RAG system."""
    return {
        "status": "not_implemented", 
        "message": "Document upload interface coming soon",
        "supported_formats": ["pdf", "txt", "docx", "md"],
        "max_file_size": "10MB"
    }

def _get_rag_status_icon(diagnostics: Dict[str, Any]) -> str:
    """Get visual status icon for RAG."""
    if diagnostics.get("rag_configured"):
        return "✅ fully_configured"
    elif diagnostics.get("rag_available"):
        return "⚠️ available_not_configured"
    else:
        return "❌ not_available"

def _analyze_rag_status(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze RAG status and provide summary."""
    diag_details = diagnostics.get("diagnostics", {})
    
    return {
        "overall_status": "configured" if diagnostics.get("rag_configured") else "not_configured",
        "availability": "available" if diagnostics.get("rag_available") else "not_available",
        "key_issues": [error for error in diag_details.get("errors", [])],
        "working_components": [
            component for component, status in diag_details.items() 
            if isinstance(status, bool) and status
        ]
    }

def _get_troubleshooting_steps(diagnostics: Dict[str, Any]) -> list:
    """Get troubleshooting steps based on diagnostics."""
    steps = []
    diag_details = diagnostics.get("diagnostics", {})
    
    if not diag_details.get("rag_config_manager_import", False):
        steps.append({
            "step": 1,
            "issue": "RAG config manager import failed",
            "action": "Check if core.config.rag_config_manager module exists",
            "solution": "Verify core/ directory structure"
        })
    
    if not diag_details.get("secrets_rag_config", False):
        steps.append({
            "step": 2,
            "issue": "No RAG configuration in secrets.toml",
            "action": "Add [rag] section to .streamlit/secrets.toml",
            "solution": 'Add: embedding_method = "OpenAI"'
        })
    
    if not diag_details.get("rag_index_path_exists", False):
        steps.append({
            "step": 3,
            "issue": "RAG index path doesn't exist",
            "action": "Create RAG index directory",
            "solution": "mkdir C:/broiler_agent/rag_index"
        })
    
    return steps

def _get_recommendations(diagnostics: Dict[str, Any]) -> list:
    """Generate recommendations based on RAG diagnostics."""
    recommendations = []
    
    if not diagnostics.get("rag_configured"):
        recommendations.append({
            "priority": "high",
            "title": "Activate RAG System",
            "description": "RAG system needs configuration",
            "action": "Use POST /admin/rag/force-configure"
        })
    
    return recommendations

def _get_human_readable_status(diagnostics: Dict[str, Any]) -> str:
    """Get human-readable status description."""
    if diagnostics.get("rag_configured"):
        return f"✅ RAG system operational with {diagnostics.get('rag_method', 'unknown')} method"
    elif diagnostics.get("rag_available"):
        return "⚠️ RAG available but needs configuration"
    else:
        return "❌ RAG system not available"