"""
app/api/expert.py - Version corrigée avec modèle unifié
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import uuid
import time
from datetime import datetime

# Correction : Utiliser le service si disponible, sinon fallback
try:
    from app.services.expert_service import expert_service
    EXPERT_SERVICE_AVAILABLE = True
except ImportError:
    EXPERT_SERVICE_AVAILABLE = False
    expert_service = None

router = APIRouter(prefix="/expert", tags=["expert"])
logger = logging.getLogger(__name__)

# ==================== MODÈLES PYDANTIC CORRIGÉS ====================

class QuestionRequest(BaseModel):
    """Request model unifié - Compatible avec main.py et frontend"""
    # ✅ CORRECTION : Accepter les deux formats
    text: Optional[str] = Field(None, description="Question text (format principal)")
    question: Optional[str] = Field(None, description="Question text (format alternatif)")
    language: Optional[str] = Field("fr", description="Response language")
    user_id: Optional[str] = Field(None, description="User ID pour logging")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode")
    context: Optional[str] = Field(None, description="Additional context")
    
    def get_question_text(self) -> str:
        """Récupère le texte de la question peu importe le format"""
        return self.text or self.question or ""
    
    def model_post_init(self, __context) -> None:
        """Validation post-init pour s'assurer qu'on a une question"""
        if not self.get_question_text().strip():
            raise ValueError("Question text is required (either 'text' or 'question' field)")

class FeedbackRequest(BaseModel):
    question: str
    response: str
    rating: str
    comment: Optional[str] = None

class ExpertResponse(BaseModel):
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    timestamp: str
    language: str
    response_time_ms: int
    confidence_score: Optional[float] = None
    mode: Optional[str] = "expert_service"
    note: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = []

# ==================== FONCTIONS HELPER ====================

def get_fallback_response(question: str, language: str = "fr") -> dict:
    """Réponse de fallback si le service expert n'est pas disponible"""
    fallback_responses = {
        "fr": f"Je reçois votre question : '{question}'. Le service expert est temporairement indisponible, mais voici une réponse générale basée sur les meilleures pratiques en élevage.",
        "en": f"I received your question: '{question}'. The expert service is temporarily unavailable, but here's a general response based on best practices in farming.",
        "es": f"Recibí su pregunta: '{question}'. El servicio experto está temporalmente no disponible, pero aquí hay una respuesta general basada en las mejores prácticas agrícolas."
    }
    
    return {
        "success": True,
        "response": fallback_responses.get(language, fallback_responses["en"]),
        "rag_used": False,
        "timestamp": datetime.now().isoformat(),
        "confidence_score": 0.3
    }

# ==================== ENDPOINTS CORRIGÉS ====================

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest):
    """Ask question to AI expert - Version unifiée corrigée"""
    start_time = time.time()
    
    try:
        question_text = request.get_question_text()
        
        if not question_text.strip():
            raise HTTPException(status_code=400, detail="Question text is required")
        
        # Générer un ID unique pour cette conversation
        conversation_id = str(uuid.uuid4())
        logger.info(f"🔍 Nouvelle question - ID: {conversation_id}, User: {request.user_id}")
        logger.info(f"📝 Question reçue: {question_text[:100]}...")
        
        # Appel au service expert si disponible
        if EXPERT_SERVICE_AVAILABLE and expert_service:
            try:
                result = await expert_service.ask_expert(
                    question=question_text,
                    language=request.language or "fr"
                )
                logger.info("✅ Service expert utilisé avec succès")
            except Exception as service_error:
                logger.warning(f"⚠️ Service expert failed: {service_error}")
                result = get_fallback_response(question_text, request.language or "fr")
        else:
            logger.info("⚠️ Service expert non disponible, utilisation fallback")
            result = get_fallback_response(question_text, request.language or "fr")
        
        # Calculer le temps de réponse
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Préparer la réponse
        response_data = {
            "question": question_text,
            "response": result.get("response", "Réponse non disponible"),
            "conversation_id": conversation_id,
            "rag_used": result.get("rag_used", False),
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            "language": request.language or "fr",
            "response_time_ms": response_time_ms,
            "confidence_score": result.get("confidence_score"),
            "mode": "expert_service" if EXPERT_SERVICE_AVAILABLE else "fallback",
            "note": "Service expert" if EXPERT_SERVICE_AVAILABLE else "Mode de secours",
            "sources": []
        }
        
        logger.info(f"✅ Réponse générée - ID: {conversation_id}, Temps: {response_time_ms}ms")
        
        return ExpertResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask question sans authentification - Version publique corrigée"""
    start_time = time.time()
    
    try:
        question_text = request.get_question_text()
        
        if not question_text.strip():
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🌐 Question publique - ID: {conversation_id}")
        logger.info(f"📝 Question: {question_text[:100]}...")
        
        # Utiliser le service expert ou fallback
        if EXPERT_SERVICE_AVAILABLE and expert_service:
            try:
                result = await expert_service.ask_expert(
                    question=question_text,
                    language=request.language or "fr"
                )
                logger.info("✅ Service expert utilisé (public)")
            except Exception as service_error:
                logger.warning(f"⚠️ Service expert failed (public): {service_error}")
                result = get_fallback_response(question_text, request.language or "fr")
        else:
            logger.info("⚠️ Service expert non disponible (public)")
            result = get_fallback_response(question_text, request.language or "fr")
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response_data = {
            "question": question_text,
            "response": result.get("response", "Réponse non disponible"),
            "conversation_id": conversation_id,
            "rag_used": result.get("rag_used", False),
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            "language": request.language or "fr",
            "response_time_ms": response_time_ms,
            "confidence_score": result.get("confidence_score"),
            "mode": "public_access",
            "note": "Accès public - fonctionnalités limitées",
            "sources": []
        }
        
        logger.info(f"✅ Réponse publique générée - ID: {conversation_id}, Temps: {response_time_ms}ms")
        
        return ExpertResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert public: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on response"""
    try:
        logger.info(f"📊 Feedback reçu: {request.rating}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement feedback")

@router.get("/topics")
async def get_suggested_topics(language: str = "fr"):
    """Get suggested topics"""
    try:
        # Topics basiques par langue
        topics_by_language = {
            "fr": [
                "Problèmes de croissance poulets Ross 308",
                "Température optimale pour élevage",
                "Indices de conversion alimentaire",
                "Mortalité élevée - diagnostic",
                "Ventilation et qualité d'air"
            ],
            "en": [
                "Ross 308 growth problems",
                "Optimal temperature for farming",
                "Feed conversion ratios",
                "High mortality - diagnosis", 
                "Ventilation and air quality"
            ],
            "es": [
                "Problemas crecimiento pollos Ross 308",
                "Temperatura óptima crianza",
                "Índices conversión alimentaria",
                "Mortalidad alta - diagnóstico",
                "Ventilación y calidad aire"
            ]
        }
        
        topics = topics_by_language.get(language, topics_by_language["fr"])
        
        if EXPERT_SERVICE_AVAILABLE and expert_service:
            try:
                expert_topics = expert_service.get_suggested_topics(language)
                if expert_topics:
                    topics = expert_topics
            except Exception:
                pass  # Utiliser les topics par défaut
        
        return {
            "topics": topics,
            "language": language,
            "count": len(topics)
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

@router.get("/history")
async def get_conversation_history():
    """Get conversation history - Redirection vers logging system"""
    return {
        "status": "replaced_by_logging_system",
        "message": "Utilisez /api/v1/logging/user/{user_id}/conversations",
        "redirect": "/api/v1/logging/user/{user_id}/conversations"
    }

# ==================== ENDPOINTS DE DEBUG ====================

@router.get("/debug/status")
async def debug_status():
    """Debug endpoint pour vérifier le statut du service"""
    return {
        "expert_service_available": EXPERT_SERVICE_AVAILABLE,
        "expert_service_object": expert_service is not None,
        "module_path": __name__,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/debug/test-question")
async def debug_test_question():
    """Test endpoint avec question simple"""
    test_request = QuestionRequest(
        text="Test de fonctionnement du système",
        language="fr"
    )
    
    try:
        response = await ask_expert_public(test_request)
        return {
            "test_status": "success",
            "response_preview": response.response[:100] + "...",
            "response_time_ms": response.response_time_ms
        }
    except Exception as e:
        return {
            "test_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
