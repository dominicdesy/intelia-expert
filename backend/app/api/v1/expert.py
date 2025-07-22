from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.expert_service import expert_service

router = APIRouter(prefix="/expert")
logger = logging.getLogger(__name__)

class QuestionRequest(BaseModel):
    question: str
    language: Optional[str] = "en"

class FeedbackRequest(BaseModel):
    question: str
    response: str
    rating: str
    comment: Optional[str] = None

@router.post("/ask")
async def ask_expert(request: QuestionRequest):
    """Ask question to AI expert."""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Empty question")
        
        result = await expert_service.ask_expert(
            question=request.question,
            language=request.language
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "question": request.question,
            "response": result["response"],
            "rag_used": result["rag_used"],
            "timestamp": result["timestamp"],
            "language": request.language
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask expert error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on response."""
    try:
        logger.info(f"Feedback received: {request.rating}")
        
        return {
            "success": True,
            "message": "Feedback recorded successfully",
            "timestamp": expert_service._get_timestamp()
        }
    
    except Exception as e:
        logger.error(f"Feedback error: {e}")
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
        logger.error(f"Topics error: {e}")
        raise HTTPException(status_code=500, detail="Topics retrieval error")

@router.get("/history")
async def get_conversation_history():
    """Get conversation history."""
    return {
        "status": "not_implemented",
        "message": "Conversation history feature coming soon"
    }
