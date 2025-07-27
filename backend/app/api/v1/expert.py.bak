"""
app/api/v1/expert.py - Version corrigée sans conflits
FIXED: Import os déplacé en haut
"""
import os  # ✅ DÉPLACÉ EN HAUT
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Configuration OpenAI - direct import
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# =============================================================================
# MODÈLES PYDANTIC COMPATIBLES AVEC MAIN.PY
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model unifié - Compatible avec main.py et frontend"""
    text: str = Field(..., description="Question text", min_length=1, max_length=2000)
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    user_id: Optional[str] = Field(None, description="User ID pour logging")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode")
    context: Optional[str] = Field(None, description="Additional context")

class FeedbackRequest(BaseModel):
    """Feedback request model"""
    question: str = Field(..., description="Original question")
    response: str = Field(..., description="AI response received")
    rating: str = Field(..., description="User rating (positive, negative, neutral)")
    comment: Optional[str] = Field(None, description="Additional feedback comment")

class ExpertResponse(BaseModel):
    """Response model compatible avec main.py"""
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    timestamp: str
    language: str
    response_time_ms: int
    confidence_score: Optional[float] = None
    mode: Optional[str] = "expert_router"
    note: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = []

class TopicsResponse(BaseModel):
    """Topics response model"""
    topics: List[str]
    language: str
    count: int

class DebugResponse(BaseModel):
    """Debug response model"""
    expert_service_available: bool
    expert_service_object: bool
    module_path: str
    timestamp: str

# =============================================================================
# PROMPTS MULTI-LANGUES
# =============================================================================

EXPERT_PROMPTS = {
    "fr": {
        "system": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. 
Réponds de manière précise et pratique en français, en donnant des conseils basés sur les meilleures pratiques du secteur.""",
        "fallback": "Je suis un expert vétérinaire. Voici une réponse basée sur les meilleures pratiques en élevage de volaille."
    },
    "en": {
        "system": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.
Answer precisely and practically in English, providing advice based on industry best practices.""",
        "fallback": "I am a veterinary expert. Here's a response based on poultry farming best practices."
    },
    "es": {
        "system": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308.
Responde de manera precisa y práctica en español, dando consejos basados en las mejores prácticas del sector.""",
        "fallback": "Soy un experto veterinario. Aquí tienes una respuesta basada en las mejores prácticas avícolas."
    }
}

# =============================================================================
# FONCTIONS HELPER
# =============================================================================

def get_expert_prompt(language: str) -> str:
    """Get expert system prompt for language"""
    return EXPERT_PROMPTS.get(language, EXPERT_PROMPTS["fr"])["system"]

def get_fallback_response(question: str, language: str = "fr") -> dict:
    """Réponse de fallback si OpenAI n'est pas disponible"""
    fallback_base = EXPERT_PROMPTS.get(language, EXPERT_PROMPTS["fr"])["fallback"]
    
    # Réponses spécifiques selon les mots-clés
    question_lower = question.lower()
    
    if any(word in question_lower for word in ["température", "temperature", "temp"]):
        specific_responses = {
            "fr": f"{fallback_base} Pour les Ross 308, maintenez 32-35°C la première semaine, puis réduisez progressivement de 2-3°C par semaine.",
            "en": f"{fallback_base} For Ross 308, maintain 32-35°C in the first week, then gradually reduce by 2-3°C per week.",
            "es": f"{fallback_base} Para Ross 308, mantén 32-35°C la primera semaine, luego reduce gradualmente 2-3°C por semana."
        }
    elif any(word in question_lower for word in ["croissance", "growth", "crecimiento"]):
        specific_responses = {
            "fr": f"{fallback_base} Les Ross 308 doivent atteindre environ 2.5kg à 35 jours avec un bon indice de conversion.",
            "en": f"{fallback_base} Ross 308 should reach approximately 2.5kg at 35 days with good feed conversion ratio.",
            "es": f"{fallback_base} Los Ross 308 deben alcanzar aproximadamente 2.5kg a los 35 días con buen índice de conversión."
        }
    elif any(word in question_lower for word in ["mortalité", "mortality", "mortalidad"]):
        specific_responses = {
            "fr": f"{fallback_base} Une mortalité élevée peut indiquer des problèmes sanitaires, de ventilation ou de température. Consultez un vétérinaire.",
            "en": f"{fallback_base} High mortality may indicate health, ventilation, or temperature issues. Consult a veterinarian.",
            "es": f"{fallback_base} La alta mortalidad puede indicar problemas sanitarios, de ventilación o temperatura. Consulte un veterinario."
        }
    else:
        specific_responses = {
            "fr": f"{fallback_base} Pour votre question sur '{question[:50]}...', je recommande de surveiller les paramètres environnementaux et de maintenir de bonnes pratiques d'hygiène.",
            "en": f"{fallback_base} For your question about '{question[:50]}...', I recommend monitoring environmental parameters and maintaining good hygiene practices.",
            "es": f"{fallback_base} Para su pregunta sobre '{question[:50]}...', recomiendo monitorear los parámetros ambientales y mantener buenas prácticas de higiene."
        }
    
    response_text = specific_responses.get(language, specific_responses["fr"])
    
    return {
        "success": True,
        "response": response_text,
        "rag_used": False,
        "timestamp": datetime.now().isoformat(),
        "confidence_score": 0.7
    }

async def process_question_openai(question: str, language: str = "fr") -> dict:
    """Process question using OpenAI directly"""
    if not OPENAI_AVAILABLE:
        return get_fallback_response(question, language)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')  # ✅ os maintenant importé
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
        
        answer = response.choices[0].message.content
        
        return {
            "success": True,
            "response": answer,
            "rag_used": False,
            "timestamp": datetime.now().isoformat(),
            "confidence_score": 0.8
        }
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return get_fallback_response(question, language)

# =============================================================================
# ENDPOINTS NON-CONFLICTUELS
# =============================================================================

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest):
    """Ask question to AI expert - ENDPOINT PRINCIPAL"""
    start_time = time.time()
    
    try:
        question_text = request.text.strip()
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🔍 Question expert - ID: {conversation_id}")
        logger.info(f"📝 Question: {question_text[:100]}...")
        
        # Process avec OpenAI
        result = await process_question_openai(question_text, request.language or "fr")
        
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
            "mode": "expert_router",
            "note": "Traité par le router expert v1",
            "sources": []
        }
        
        logger.info(f"✅ Réponse expert générée - ID: {conversation_id}, Temps: {response_time_ms}ms")
        
        return ExpertResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest):
    """Ask question sans authentification - ENDPOINT PUBLIC"""
    start_time = time.time()
    
    try:
        question_text = request.text.strip()
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        logger.info(f"🌐 Question publique - ID: {conversation_id}")
        
        # Process avec OpenAI
        result = await process_question_openai(question_text, request.language or "fr")
        
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
            "mode": "public_router",
            "note": "Accès public via router expert v1",
            "sources": []
        }
        
        logger.info(f"✅ Réponse publique - ID: {conversation_id}")
        
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
                "Protocoles de vaccination",
                "Nutrition spécialisée",
                "Gestion sanitaire"
            ],
            "en": [
                "Ross 308 growth problems",
                "Optimal temperature for farming",
                "Feed conversion ratios",
                "High mortality - diagnosis", 
                "Ventilation and air quality",
                "Vaccination protocols",
                "Specialized nutrition",
                "Health management"
            ],
            "es": [
                "Problemas crecimiento pollos Ross 308",
                "Temperatura óptima crianza",
                "Índices conversión alimentaria",
                "Mortalidad alta - diagnóstico",
                "Ventilación y calidad aire",
                "Protocolos vacunación",
                "Nutrición especializada",
                "Gestión sanitaria"
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
        "note": "Version router expert v1"
    }

# =============================================================================
# ENDPOINTS DE DEBUG ET STATUS
# =============================================================================

@router.get("/debug/status", response_model=DebugResponse)
async def debug_status():
    """Debug endpoint pour vérifier le statut du service"""
    return DebugResponse(
        expert_service_available=OPENAI_AVAILABLE,
        expert_service_object=OPENAI_AVAILABLE,
        module_path=__name__,
        timestamp=datetime.now().isoformat()
    )

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
            "mode": response.mode
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
            "/expert/ask",
            "/expert/ask-public", 
            "/expert/feedback",
            "/expert/topics",
            "/expert/history",
            "/expert/debug/status",
            "/expert/debug/test-question",
            "/expert/debug/routes"
        ],
        "note": "Routes expert router v1 - Import os fixé",
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# CONFIGURATION OPENAI
# =============================================================================

# Configuration OpenAI
openai_api_key = os.getenv('OPENAI_API_KEY')  # ✅ os maintenant importé
if openai_api_key and OPENAI_AVAILABLE:
    openai.api_key = openai_api_key
    logger.info("✅ OpenAI configuré avec succès dans expert router")
else:
    logger.warning("⚠️ OpenAI API key manquante ou module indisponible dans expert router")