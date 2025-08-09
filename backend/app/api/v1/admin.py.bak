from fastapi import APIRouter, HTTPException
import logging
import os
from datetime import datetime
from typing import Dict, Any

router = APIRouter(prefix="/admin")
logger = logging.getLogger(__name__)

@router.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """
    Get admin dashboard with comprehensive status.
    Checks OpenAI and Vector Store configuration.
    """
    try:
        openai_configured = bool(os.getenv("OPENAI_API_KEY"))
        vector_url = os.getenv("VECTOR_STORE_URL")
        vector_key = os.getenv("VECTOR_STORE_KEY")
        rag_available = bool(vector_url and vector_key)
        rag_configured = rag_available and openai_configured

        diagnostics = {
            "openai_configured": openai_configured,
            "rag_available": rag_available,
            "rag_configured": rag_configured,
            "timestamp": datetime.utcnow().isoformat()
        }

        return {
            "status": "success",
            "diagnostics": diagnostics
        }
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard status")

@router.get("/users")
async def get_users() -> Dict[str, Any]:
    """
    Management endpoint for user overview.
    Placeholder implementation that tracks active sessions.
    """
    try:
        # Example: retrieve active session count from memory store
        from app.api.v1.pipeline.memory import ConversationMemory
        memory = ConversationMemory()
        # For demo, assume memory.store keys are user sessions
        sessions = list(memory.store.keys())
        total_users = len(sessions)
        return {
            "users": sessions,
            "total_users": total_users,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users list")

@router.get("/rag/diagnostics")
async def get_rag_diagnostics() -> Dict[str, Any]:
    """
    Get comprehensive RAG system diagnostics.
    """
    try:
        openai_configured = bool(os.getenv("OPENAI_API_KEY"))
        vector_url = os.getenv("VECTOR_STORE_URL")
        vector_key = os.getenv("VECTOR_STORE_KEY")
        rag_available = bool(vector_url and vector_key)
        rag_configured = rag_available and openai_configured
        return {
            "openai_configured": openai_configured,
            "rag_available": rag_available,
            "rag_configured": rag_configured,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"RAG diagnostics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve RAG diagnostics")

@router.get("/rag/test")
async def test_rag_end_to_end() -> Dict[str, Any]:
    """
    Test the RAG pipeline end-to-end with a sample question.
    """
    try:
        from app.api.v1.pipeline.rag_engine import RAGEngine
        rag = RAGEngine()
        test_question = "What is the optimal temperature for Ross 308 broilers?"
        # Use empty context for a basic test
        answer = rag.generate_answer(test_question, {})
        return {
            "test_question": test_question,
            "test_answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"RAG test error: {e}")
        raise HTTPException(status_code=500, detail="RAG end-to-end test failed")

@router.get("/analytics")
async def get_analytics() -> Dict[str, Any]:
    """
    Get usage analytics. Not implemented yet.
    """
    return {
        "status": "not_implemented"
    }
