"""
app/api/v1/expert.py - Version avec RAG fonctionnel
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# OpenAI import sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# Variable globale pour stocker les références RAG
_rag_system = None
_process_question_func = None

# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model pour questions expert"""
    text: str = Field(..., min_length=1, max_length=2000, description="Question text")
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode: fast, balanced, quality")

class ExpertResponse(BaseModel):
    """Response model avec support RAG"""
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    timestamp: str
    language: str
    response_time_ms: int
    mode: str = "expert_router_v1"

class FeedbackRequest(BaseModel):
    """Feedback request model"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(None, max_length=500, description="Optional comment")

class TopicsResponse(BaseModel):
    """Topics response model"""
    topics: List[str]
    language: str
    count: int

# =============================================================================
# INITIALISATION DU SYSTÈME RAG
# =============================================================================

def initialize_rag_references(app):
    """Initialise les références RAG depuis app.state"""
    global _rag_system, _process_question_func
    
    try:
        if hasattr(app.state, 'rag_embedder'):
            _rag_system = app.state.rag_embedder
            logger.info("✅ RAG embedder référencé depuis app.state")
        
        if hasattr(app.state, 'process_question_with_rag'):
            _process_question_func = app.state.process_question_with_rag
            logger.info("✅ Fonction process_question_with_rag référencée")
            
        return _rag_system is not None and _process_question_func is not None
    except Exception as e:
        logger.error(f"❌ Erreur initialisation RAG: {e}")
        return False

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
    """Réponse de fallback si ni RAG ni OpenAI disponibles"""
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire. Pour votre question sur '{question[:50]}...', je recommande de surveiller les paramètres environnementaux et de maintenir de bonnes pratiques d'hygiène.",
        "en": f"I am a veterinary expert. For your question about '{question[:50]}...', I recommend monitoring environmental parameters and maintaining good hygiene practices.",
        "es": f"Soy un experto veterinario. Para su pregunta sobre '{question[:50]}...', recomiendo monitorear los parámetros ambientales y mantener buenas prácticas de higiene."
    }
    return fallback_responses.get(language, fallback_responses["fr"])

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
# ENDPOINTS AVEC RAG
# =============================================================================

@router.on_event("startup")
async def startup_event():
    """Initialise les références RAG au démarrage du router"""
    # Cette fonction sera appelée après que l'app soit complètement initialisée
    pass

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask question sans authentification - AVEC RAG"""
    start_time = time.time()
    
    try:
        question_text = request.text.strip()
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🌐 Question publique - ID: {conversation_id}")
        
        # Essayer d'utiliser le RAG si disponible
        rag_used = False
        answer = ""
        mode = "direct_openai"
        
        if _process_question_func:
            try:
                logger.info(f"🔍 Tentative d'utilisation du RAG...")
                result = await _process_question_func(
                    question=question_text,
                    user=None,
                    language=request.language or "fr",
                    speed_mode=request.speed_mode or "balanced"
                )
                answer = result.get("response", "")
                rag_used = result.get("mode", "").startswith("rag")
                mode = result.get("mode", "rag_enhanced")
                logger.info(f"✅ RAG utilisé avec succès: {rag_used}")
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG: {rag_error}")
                # Fallback sur OpenAI
                answer = await process_question_openai(question_text, request.language or "fr")
        else:
            # RAG non disponible, utiliser OpenAI direct
            logger.info("⚠️ Fonction RAG non disponible, utilisation OpenAI direct")
            answer = await process_question_openai(question_text, request.language or "fr")
        
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
async def ask_expert(request: QuestionRequest):
    """Ask question avec authentification"""
    # Pour l'instant, même logique que public
    return await ask_expert_public(request)

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
        "rag_available": _process_question_func is not None
    }

# =============================================================================
# ENDPOINTS DE DEBUG
# =============================================================================

@router.get("/debug/status")
async def debug_status():
    """Debug endpoint pour vérifier le statut du service"""
    return {
        "expert_service_available": OPENAI_AVAILABLE,
        "rag_available": _process_question_func is not None,
        "rag_system_loaded": _rag_system is not None,
        "module_path": __name__,
        "timestamp": datetime.now().isoformat(),
        "version": "expert_router_v1_rag"
    }

@router.get("/debug/test-question")
async def debug_test_question():
    """Test endpoint avec question simple"""
    test_request = QuestionRequest(
        text="What are the Compass Performance Analysis Protocol patterns?",
        language="en",
        speed_mode="quality"
    )
    
    try:
        response = await ask_expert_public(test_request)
        return {
            "test_status": "success",
            "response_preview": response.response[:200] + "...",
            "response_time_ms": response.response_time_ms,
            "mode": response.mode,
            "rag_used": response.rag_used
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
        "rag_status": {
            "function_available": _process_question_func is not None,
            "system_available": _rag_system is not None
        },
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# HOOK POUR INITIALISER RAG APRÈS LE MONTAGE
# =============================================================================

@router.get("/init-rag")
async def init_rag_endpoint():
    """Endpoint pour forcer l'initialisation du RAG"""
    from fastapi import Request
    from starlette.applications import Starlette
    
    # Trouver l'app principale
    app = None
    for route in router.routes:
        if hasattr(route, 'app'):
            app = route.app
            break
    
    if app:
        success = initialize_rag_references(app)
        return {
            "initialized": success,
            "rag_function": _process_question_func is not None,
            "rag_system": _rag_system is not None
        }
    else:
        return {"error": "App not found"}

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