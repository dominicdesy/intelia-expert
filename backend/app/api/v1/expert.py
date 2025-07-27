"""
app/api/v1/expert.py - Version Propre avec Intégration RAG
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
    openai = None

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# Variables globales pour stocker les références RAG
_rag_embedder = None
_process_question_with_rag = None
_get_rag_status = None

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
# FONCTION D'INITIALISATION RAG
# =============================================================================

def setup_rag_references(app):
    """Configure les références RAG directement"""
    global _rag_embedder, _process_question_with_rag, _get_rag_status
    
    try:
        # Initialisation directe sans événement startup
        if hasattr(app, 'state'):
            _rag_embedder = getattr(app.state, 'rag_embedder', None)
            _process_question_with_rag = getattr(app.state, 'process_question_with_rag', None)
            _get_rag_status = getattr(app.state, 'get_rag_status', None)
            
            if _process_question_with_rag:
                logger.info("✅ Système RAG connecté avec succès dans expert router")
                return True
            else:
                logger.warning("⚠️ Fonction process_question_with_rag non disponible")
                return False
        else:
            logger.error("❌ app.state non disponible")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation RAG: {e}")
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
    return EXPERT_PROMPTS.get(language.lower(), EXPERT_PROMPTS["fr"])

def get_fallback_response(question: str, language: str = "fr") -> str:
    """Réponse de fallback si ni RAG ni OpenAI disponibles"""
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire. Pour votre question sur '{question[:50]}...', je recommande de surveiller les paramètres environnementaux et de maintenir de bonnes pratiques d'hygiène.",
        "en": f"I am a veterinary expert. For your question about '{question[:50]}...', I recommend monitoring environmental parameters and maintaining good hygiene practices.",
        "es": f"Soy un experto veterinario. Para su pregunta sobre '{question[:50]}...', recomiendo monitorear los parámetros ambientales y mantener buenas prácticas de higiene."
    }
    return fallback_responses.get(language.lower(), fallback_responses["fr"])

async def process_question_openai(question: str, language: str = "fr", speed_mode: str = "balanced") -> str:
    """Process question using OpenAI directly"""
    if not OPENAI_AVAILABLE or not openai:
        return get_fallback_response(question, language)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OpenAI API key not found")
            return get_fallback_response(question, language)
        
        openai.api_key = api_key
        system_prompt = get_expert_prompt(language)
        
        # Configuration selon le mode
        model_config = {
            "fast": {"model": "gpt-3.5-turbo", "max_tokens": 300},
            "balanced": {"model": "gpt-3.5-turbo", "max_tokens": 500},
            "quality": {"model": "gpt-4o-mini", "max_tokens": 800}
        }
        
        config = model_config.get(speed_mode, model_config["balanced"])
        
        response = openai.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=config["max_tokens"],
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
async def ask_expert_public(request: QuestionRequest):
    """Ask question sans authentification - AVEC RAG si disponible"""
    start_time = time.time()
    
    try:
        question_text = request.text.strip()
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🌐 Question publique - ID: {conversation_id[:8]}...")
        
        # Essayer d'utiliser le RAG si disponible
        rag_used = False
        answer = ""
        mode = "direct_openai"
        
        if _process_question_with_rag:
            try:
                logger.info("🔍 Utilisation du système RAG...")
                result = await _process_question_with_rag(
                    question=question_text,
                    user=None,
                    language=request.language or "fr",
                    speed_mode=request.speed_mode or "balanced"
                )
                
                answer = result.get("response", "")
                rag_used = result.get("mode", "").startswith("rag")
                mode = result.get("mode", "rag_enhanced")
                
                logger.info(f"✅ RAG {'utilisé' if rag_used else 'consulté sans résultats'}")
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG, fallback OpenAI: {rag_error}")
                answer = await process_question_openai(
                    question_text, 
                    request.language or "fr",
                    request.speed_mode or "balanced"
                )
        else:
            # RAG non disponible, utiliser OpenAI direct
            logger.info("⚠️ RAG non disponible, utilisation OpenAI direct")
            answer = await process_question_openai(
                question_text,
                request.language or "fr",
                request.speed_mode or "balanced"
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return ExpertResponse(
            question=question_text,
            response=answer,
            conversation_id=conversation_id,
            rag_used=rag_used,
            timestamp=datetime.now().isoformat(),
            language=request.language or "fr",
            response_time_ms=response_time_ms,
            mode=mode
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert public: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest):
    """Ask question avec authentification - même logique pour l'instant"""
    return await ask_expert_public(request)

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
                "Ventilation et qualité d'air",
                "Protocoles de vaccination",
                "Indices de conversion alimentaire"
            ],
            "en": [
                "Compass Performance Analysis Protocol",
                "Ross 308 growth problems",
                "Weight Performance Diagnostic Patterns",
                "Optimal temperature for farming",
                "High mortality - diagnosis", 
                "Ventilation and air quality",
                "Vaccination protocols",
                "Feed conversion ratios"
            ],
            "es": [
                "Protocolos Compass análisis rendimiento",
                "Problemas crecimiento pollos Ross 308",
                "Patrones diagnóstico peso",
                "Temperatura óptima crianza",
                "Mortalidad alta - diagnóstico",
                "Ventilación y calidad aire",
                "Protocolos vacunación",
                "Índices conversión alimentaria"
            ]
        }
        
        topics = topics_by_language.get(language.lower(), topics_by_language["fr"])
        
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
    """Get conversation history - placeholder"""
    return {
        "conversations": [],
        "message": "Historique des conversations (fonctionnalité à venir)",
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# ENDPOINTS DE DEBUG
# =============================================================================

@router.get("/debug/status")
async def debug_status():
    """Debug endpoint pour vérifier le statut du service"""
    rag_status = "not_available"
    if _get_rag_status:
        try:
            rag_status = _get_rag_status()
        except:
            pass
    
    return {
        "expert_service": {
            "openai_available": OPENAI_AVAILABLE,
            "openai_key_configured": bool(os.getenv('OPENAI_API_KEY'))
        },
        "rag_system": {
            "embedder_connected": _rag_embedder is not None,
            "function_connected": _process_question_with_rag is not None,
            "status": rag_status
        },
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@router.get("/debug/test-question")
async def debug_test_question():
    """Test endpoint avec question sur Compass"""
    test_request = QuestionRequest(
        text="What are the Compass Performance Analysis Protocol diagnostic patterns for Ross 308?",
        language="en",
        speed_mode="quality"
    )
    
    try:
        response = await ask_expert_public(test_request)
        return {
            "test_status": "success",
            "rag_used": response.rag_used,
            "response_preview": response.response[:200] + "..." if len(response.response) > 200 else response.response,
            "response_time_ms": response.response_time_ms
        }
    except Exception as e:
        return {
            "test_status": "error",
            "error": str(e),
            "rag_available": _process_question_with_rag is not None
        }

@router.get("/debug/routes")
async def debug_routes():
    """Debug endpoint pour lister les routes disponibles"""
    return {
        "routes": [
            {"path": "/api/v1/expert/ask-public", "method": "POST", "description": "Question publique"},
            {"path": "/api/v1/expert/ask", "method": "POST", "description": "Question authentifiée"},
            {"path": "/api/v1/expert/feedback", "method": "POST", "description": "Soumettre feedback"},
            {"path": "/api/v1/expert/topics", "method": "GET", "description": "Sujets suggérés"},
            {"path": "/api/v1/expert/history", "method": "GET", "description": "Historique"},
            {"path": "/api/v1/expert/debug/status", "method": "GET", "description": "Statut système"},
            {"path": "/api/v1/expert/debug/test-question", "method": "GET", "description": "Test RAG"},
            {"path": "/api/v1/expert/debug/routes", "method": "GET", "description": "Liste routes"}
        ],
        "rag_connected": _process_question_with_rag is not None,
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# CONFIGURATION AU DÉMARRAGE
# =============================================================================

# Configuration OpenAI au chargement du module
if OPENAI_AVAILABLE and openai:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai.api_key = openai_api_key
        logger.info("✅ OpenAI configuré avec succès dans expert router")
    else:
        logger.warning("⚠️ OpenAI API key non trouvée dans les variables d'environnement")
else:
    logger.warning("⚠️ Module OpenAI non disponible")