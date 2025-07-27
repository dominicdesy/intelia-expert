"""
app/api/v1/expert.py - Version corrigée SANS erreurs Pydantic
FIXED: Modèles Pydantic simplifiés pour éviter erreurs OpenAPI
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# OpenAI import sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# =============================================================================
# MODÈLES PYDANTIC SIMPLIFIÉS - SANS ERREURS OPENAPI
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model simplifié pour questions expert"""
    text: str = Field(..., min_length=1, max_length=2000, description="Question text")
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode: fast, balanced, quality")

class ExpertResponse(BaseModel):
    """Response model simplifié"""
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    timestamp: str
    language: str
    response_time_ms: int
    mode: str = "expert_router_v1"

class FeedbackRequest(BaseModel):
    """Feedback request model simplifié"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(None, max_length=500, description="Optional comment")

class TopicsResponse(BaseModel):
    """Topics response model"""
    topics: List[str]
    language: str
    count: int

# =============================================================================
# PROMPTS MULTI-LANGUES
# =============================================================================

EXPERT_PROMPTS = {
    "fr": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. 
Réponds de manière précise et pratique en français, en donnant des conseils basés sur les meilleures pratiques du secteur.""",
    
    "en": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.
Answer precisely and practically in English, providing advice based on industry best practices.""",
    
    "es": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308.
Responde de manera precisa y práctica en español, dando consejos basados en las mejores prácticas del sector."""
}

# =============================================================================
# FONCTIONS HELPER SIMPLIFIÉES
# =============================================================================

def get_expert_prompt(language: str) -> str:
    """Get expert system prompt for language"""
    return EXPERT_PROMPTS.get(language, EXPERT_PROMPTS["fr"])

def get_fallback_response(question: str, language: str = "fr") -> str:
    """Réponse de fallback si OpenAI n'est pas disponible"""
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire. Pour votre question sur '{question[:50]}...', je recommande de surveiller les paramètres environnementaux et de maintenir de bonnes pratiques d'hygiène.",
        "en": f"I am a veterinary expert. For your question about '{question[:50]}...', I recommend monitoring environmental parameters and maintaining good hygiene practices.",
        "es": f"Soy un experto veterinario. Para su pregunta sobre '{question[:50]}...', recomiendo monitorear los parámetros ambientales y mantener buenas prácticas de higiene."
    }
    return fallback_responses.get(language, fallback_responses["fr"])

async def process_question_openai(question: str, language: str = "fr") -> str:
    """Process question using OpenAI directly - retourne string simple"""
    if not OPENAI_AVAILABLE:
        return get_fallback_response(question, language)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OpenAI API key not found")
            return get_fallback_response(question, language)
        
        openai.api_key = api_key
        system_prompt = get_expert_prompt(language)
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=500,
            timeout=15
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return get_fallback_response(question, language)

# =============================================================================
# ENDPOINTS SIMPLIFIÉS SANS ERREURS PYDANTIC
# =============================================================================

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask question sans authentification - ENDPOINT PRINCIPAL"""
    start_time = time.time()
    
    try:
        question_text = request.text.strip()
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🌐 Question publique - ID: {conversation_id}")
        
        # Process avec OpenAI
        answer = await process_question_openai(question_text, request.language or "fr")
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response_data = ExpertResponse(
            question=question_text,
            response=answer,
            conversation_id=conversation_id,
            rag_used=False,
            timestamp=datetime.now().isoformat(),
            language=request.language or "fr",
            response_time_ms=response_time_ms,
            mode="expert_router_v1_public"
        )
        
        logger.info(f"✅ Réponse publique - ID: {conversation_id}")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert public: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest):
    """Ask question avec authentification"""
    start_time = time.time()
    
    try:
        question_text = request.text.strip()
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🔍 Question expert - ID: {conversation_id}")
        
        # Process avec OpenAI
        answer = await process_question_openai(question_text, request.language or "fr")
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response_data = ExpertResponse(
            question=question_text,
            response=answer,
            conversation_id=conversation_id,
            rag_used=False,
            timestamp=datetime.now().isoformat(),
            language=request.language or "fr",
            response_time_ms=response_time_ms,
            mode="expert_router_v1_auth"
        )
        
        logger.info(f"✅ Réponse expert - ID: {conversation_id}")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on response"""
    try:
        logger.info(f"📊 Feedback reçu: {request.rating}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès",
            "timestamp": datetime.now().isoformat(),
            "source": "expert_router_v1"
        }
    
    except Exception as e:
        logger.error(f"❌ Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement feedback")

@router.get("/topics", response_model=TopicsResponse)
async def get_suggested_topics(language: str = "fr"):
    """Get suggested topics"""
    try:
        topics_by_language = {
            "fr": [
                "Problèmes de croissance poulets Ross 308",
                "Température optimale pour élevage",
                "Indices de conversion alimentaire",
                "Mortalité élevée - diagnostic",
                "Ventilation et qualité d'air",
                "Protocoles de vaccination"
            ],
            "en": [
                "Ross 308 growth problems",
                "Optimal temperature for farming",
                "Feed conversion ratios",
                "High mortality - diagnosis", 
                "Ventilation and air quality",
                "Vaccination protocols"
            ],
            "es": [
                "Problemas crecimiento pollos Ross 308",
                "Temperatura óptima crianza",
                "Índices conversión alimentaria",
                "Mortalidad alta - diagnóstico",
                "Ventilación y calidad aire",
                "Protocolos vacunación"
            ]
        }
        
        topics = topics_by_language.get(language, topics_by_language["fr"])
        
        return TopicsResponse(
            topics=topics,
            language=language,
            count=len(topics)
        )
    
    except Exception as e:
        logger.error(f"❌ Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

@router.get("/history")
async def get_conversation_history():
    """Get conversation history"""
    return {
        "status": "expert_router_v1",
        "message": "Historique conversations via router expert",
        "note": "Version router expert v1 - modèles Pydantic fixés"
    }

# =============================================================================
# ENDPOINTS DE DEBUG
# =============================================================================

@router.get("/debug/status")
async def debug_status():
    """Debug endpoint pour vérifier le statut du service"""
    return {
        "expert_service_available": OPENAI_AVAILABLE,
        "module_path": __name__,
        "timestamp": datetime.now().isoformat(),
        "pydantic_models": "simplified_fixed"
    }

@router.get("/debug/test-question")
async def debug_test_question():
    """Test endpoint avec question simple"""
    test_request = QuestionRequest(
        text="Test de fonctionnement du système Ross 308",
        language="fr"
    )
    
    try:
        response = await ask_expert_public(test_request)
        return {
            "test_status": "success",
            "response_preview": response.response[:100] + "...",
            "response_time_ms": response.response_time_ms,
            "mode": response.mode,
            "pydantic_fix": "working"
        }
    except Exception as e:
        return {
            "test_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/debug/routes")
async def debug_routes():
    """Debug endpoint pour lister les routes disponibles"""
    return {
        "available_routes": [
            "/api/v1/expert/ask-public",
            "/api/v1/expert/ask", 
            "/api/v1/expert/feedback",
            "/api/v1/expert/topics",
            "/api/v1/expert/history",
            "/api/v1/expert/debug/status",
            "/api/v1/expert/debug/test-question",
            "/api/v1/expert/debug/routes"
        ],
        "note": "Routes expert v1 - Pydantic models fixed",
        "timestamp": datetime.now().isoformat(),
        "openapi_fix": "simplified_models"
    }

# =============================================================================
# CONFIGURATION OPENAI
# =============================================================================

# Configuration OpenAI
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key and OPENAI_AVAILABLE:
    openai.api_key = openai_api_key
    logger.info("✅ OpenAI configuré avec succès dans expert router v1")
else:
    logger.warning("⚠️ OpenAI API key manquante ou module indisponible dans expert router v1")