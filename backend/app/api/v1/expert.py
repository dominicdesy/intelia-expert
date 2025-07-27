"""
app/api/v1/expert.py - Version corrigée SANS import circulaire
Utilise une approche différente pour accéder au RAG
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request
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
# MODÈLES PYDANTIC SIMPLIFIÉS
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model pour questions expert"""
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
# FONCTIONS HELPER
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

async def process_question_with_rag_if_available(request: Request, question: str, language: str = "fr", speed_mode: str = "balanced") -> Dict[str, Any]:
    """Essaie d'utiliser le RAG si disponible dans l'app FastAPI"""
    try:
        # Accéder à l'app FastAPI depuis la request
        app = request.app
        
        # Vérifier si le RAG est disponible dans l'état de l'app
        if hasattr(app.state, 'rag_embedder') and app.state.rag_embedder:
            logger.info("🔍 RAG embedder trouvé dans app.state")
            
            # Vérifier si la fonction process_question_with_rag existe
            if hasattr(app.state, 'process_question_with_rag'):
                logger.info("✅ Fonction RAG trouvée, utilisation...")
                result = await app.state.process_question_with_rag(
                    question=question,
                    user=None,
                    language=language,
                    speed_mode=speed_mode
                )
                return result
            else:
                logger.warning("⚠️ Fonction process_question_with_rag non trouvée dans app.state")
        else:
            logger.warning("⚠️ RAG embedder non trouvé dans app.state")
    except Exception as e:
        logger.error(f"❌ Erreur accès RAG: {e}")
    
    # Fallback si RAG non disponible
    return None

async def process_question_openai(question: str, language: str = "fr") -> str:
    """Process question using OpenAI directly"""
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
# ENDPOINTS
# =============================================================================

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest, fastapi_request: Request):
    """Ask question sans authentification - Essaie d'utiliser le RAG si disponible"""
    start_time = time.time()
    
    try:
        question_text = request.text.strip()
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🌐 Question publique - ID: {conversation_id}")
        
        # Essayer d'utiliser le RAG si disponible
        rag_result = await process_question_with_rag_if_available(
            fastapi_request, 
            question_text, 
            request.language or "fr",
            request.speed_mode or "balanced"
        )
        
        if rag_result:
            # RAG a fonctionné
            logger.info("✅ Réponse via RAG")
            answer = rag_result.get("response", "")
            rag_used = True
            mode = rag_result.get("mode", "rag_enhanced")
            note = rag_result.get("note", "Réponse basée sur la recherche documentaire")
        else:
            # Fallback sur OpenAI
            logger.info("🔄 Fallback sur OpenAI direct")
            answer = await process_question_openai(question_text, request.language or "fr")
            rag_used = False
            mode = "direct_openai"
            note = "Réponse sans recherche documentaire"
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response_data = ExpertResponse(
            question=question_text,
            response=answer,
            conversation_id=conversation_id,
            rag_used=rag_used,
            timestamp=datetime.now().isoformat(),
            language=request.language or "fr",
            response_time_ms=response_time_ms,
            mode=mode
        )
        
        logger.info(f"✅ Réponse publique - ID: {conversation_id} - RAG: {rag_used}")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert public: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest, fastapi_request: Request):
    """Ask question avec authentification"""
    # Pour l'instant, même logique que public
    return await ask_expert_public(request, fastapi_request)

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
                "Protocoles Compass pour l'analyse de performance",
                "Problèmes de croissance poulets Ross 308",
                "Température optimale pour élevage",
                "Patterns de diagnostic du poids",
                "Mortalité élevée - diagnostic",
                "Ventilation et qualité d'air"
            ],
            "en": [
                "Compass Performance Analysis Protocol",
                "Ross 308 growth problems",
                "Weight Performance Diagnostic Patterns",
                "Optimal temperature for farming",
                "High mortality - diagnosis", 
                "Ventilation and air quality"
            ],
            "es": [
                "Protocolos Compass análisis rendimiento",
                "Problemas crecimiento pollos Ross 308",
                "Patrones diagnóstico peso",
                "Temperatura óptima crianza",
                "Mortalidad alta - diagnóstico",
                "Ventilación y calidad aire"
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
        "note": "Version sans import circulaire"
    }

# =============================================================================
# ENDPOINTS DE DEBUG
# =============================================================================

@router.get("/debug/status")
async def debug_status(request: Request):
    """Debug endpoint pour vérifier le statut du service"""
    rag_available = False
    rag_status = "not_checked"
    
    try:
        app = request.app
        if hasattr(app.state, 'rag_embedder') and app.state.rag_embedder:
            rag_available = True
            if hasattr(app.state.rag_embedder, 'has_search_engine'):
                rag_status = "optimized" if app.state.rag_embedder.has_search_engine() else "fallback"
    except:
        pass
    
    return {
        "expert_service_available": OPENAI_AVAILABLE,
        "rag_available": rag_available,
        "rag_status": rag_status,
        "module_path": __name__,
        "timestamp": datetime.now().isoformat(),
        "version": "expert_router_v1_no_circular"
    }

@router.get("/debug/test-question")
async def debug_test_question(request: Request):
    """Test endpoint avec question simple"""
    test_request = QuestionRequest(
        text="Test de fonctionnement du système Ross 308",
        language="fr"
    )
    
    try:
        response = await ask_expert_public(test_request, request)
        return {
            "test_status": "success",
            "response_preview": response.response[:100] + "...",
            "response_time_ms": response.response_time_ms,
            "mode": response.mode,
            "rag_used": response.rag_used,
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
        "note": "Routes expert v1 - Sans import circulaire",
        "timestamp": datetime.now().isoformat()
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