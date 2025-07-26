from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import uuid
import time
from datetime import datetime

from app.services.expert_service import expert_service

router = APIRouter(prefix="/expert")
logger = logging.getLogger(__name__)

# ==================== MODÈLES PYDANTIC ====================

class QuestionRequest(BaseModel):
    question: str
    language: Optional[str] = "en"
    user_id: Optional[str] = None  # Pour le logging

class FeedbackRequest(BaseModel):
    question: str
    response: str
    rating: str
    comment: Optional[str] = None

class ExpertResponse(BaseModel):
    question: str
    response: str
    conversation_id: str  # Nouveau champ pour le logging
    rag_used: bool
    timestamp: str
    language: str
    response_time_ms: int  # Nouveau champ pour la performance
    confidence_score: Optional[float] = None

# ==================== ENDPOINTS ====================

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest):
    """Ask question to AI expert avec logging intégré."""
    start_time = time.time()
    
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Empty question")
        
        # Générer un ID unique pour cette conversation
        conversation_id = str(uuid.uuid4())
        logger.info(f"🔍 Nouvelle question - ID: {conversation_id}, User: {request.user_id}")
        
        # Appel au service expert existant
        result = await expert_service.ask_expert(
            question=request.question,
            language=request.language
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Calculer le temps de réponse
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Préparer la réponse complète avec toutes les métadonnées
        response_data = {
            "question": request.question,
            "response": result["response"],
            "conversation_id": conversation_id,
            "rag_used": result["rag_used"],
            "timestamp": result["timestamp"],
            "language": request.language or "en",
            "response_time_ms": response_time_ms,
            "confidence_score": result.get("confidence_score")
        }
        
        logger.info(f"✅ Réponse générée - ID: {conversation_id}, Temps: {response_time_ms}ms")
        
        return ExpertResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask question sans authentification - Version publique avec logging."""
    start_time = time.time()
    
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Empty question")
        
        # Générer un ID unique pour cette conversation publique
        conversation_id = str(uuid.uuid4())
        logger.info(f"🌐 Question publique - ID: {conversation_id}")
        
        # Appel au service expert existant
        result = await expert_service.ask_expert(
            question=request.question,
            language=request.language
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Calculer le temps de réponse
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Préparer la réponse complète
        response_data = {
            "question": request.question,
            "response": result["response"],
            "conversation_id": conversation_id,
            "rag_used": result["rag_used"],
            "timestamp": result["timestamp"],
            "language": request.language or "en",
            "response_time_ms": response_time_ms,
            "confidence_score": result.get("confidence_score")
        }
        
        logger.info(f"✅ Réponse publique générée - ID: {conversation_id}, Temps: {response_time_ms}ms")
        
        return ExpertResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert public: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on response."""
    try:
        logger.info(f"📊 Feedback reçu: {request.rating}")
        
        # TODO: Intégrer avec le système de logging pour associer le feedback
        # à une conversation spécifique via conversation_id
        
        return {
            "success": True,
            "message": "Feedback recorded successfully",
            "timestamp": expert_service._get_timestamp()
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail="Feedback recording error")

@router.get("/topics")
async def get_suggested_topics(language: str = "en"):
    """Get suggested topics."""
    try:
        topics = expert_service.get_suggested_topics(language)
        return {
            "topics": topics,
            "language": language,
            "count": len(topics)
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Topics retrieval error")

@router.get("/history")
async def get_conversation_history():
    """Get conversation history - Sera remplacé par le système de logging."""
    return {
        "status": "replaced_by_logging_system",
        "message": "Use /api/v1/logging/user/{user_id}/conversations instead",
        "redirect": "/api/v1/logging/user/{user_id}/conversations"
    }

# ==================== ENDPOINTS DE DEBUG ====================

@router.get("/debug/performance")
async def debug_performance():
    """Debug endpoint pour vérifier les performances."""
    start_time = time.time()
    
    try:
        # Test simple du service
        test_result = await expert_service.ask_expert(
            question="Test de performance",
            language="fr"
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            "status": "ok",
            "response_time_ms": response_time,
            "service_available": test_result["success"],
            "rag_status": test_result.get("rag_used", False),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return {
            "status": "error",
            "response_time_ms": response_time,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/debug/conversation-id")
async def debug_conversation_id():
    """Debug endpoint pour tester la génération d'ID."""
    conversation_ids = [str(uuid.uuid4()) for _ in range(5)]
    
    return {
        "message": "Test génération conversation IDs",
        "sample_ids": conversation_ids,
        "format": "UUID4",
        "timestamp": datetime.now().isoformat()
    }
