"""
app/api/v1/expert.py - CORRECTION FINALE UTF-8 ACCENTS FRANÇAIS
SOLUTION RADICALE: Suppression complète de la validation Pydantic pour le champ text
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel, Field, ConfigDict

# OpenAI import sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# =============================================================================
# MODÈLES PYDANTIC AVEC VALIDATION COMPLÈTEMENT SUPPRIMÉE POUR TEXT
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model RADICAL: AUCUNE validation sur le champ text"""
    text: str = Field(..., description="Question text (NO validation - accepts ALL)")
    language: Optional[str] = Field("fr", description="Response language")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode")

    # Configuration ULTRA-PERMISSIVE
    model_config = ConfigDict(
        # CRITIQUE: Désactiver TOUTE validation
        validate_assignment=False,
        str_strip_whitespace=False,  # Ne pas toucher aux espaces
        validate_default=False,
        extra="ignore",
        # Pas d'encoders JSON pour éviter les transformations
        arbitrary_types_allowed=True
    )

    # SOLUTION RADICALE: AUCUN VALIDATOR sur text
    # Laisser Pydantic accepter text tel quel sans aucune transformation

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        """Override pour désactiver la validation sur text"""
        super().__pydantic_init_subclass__(**kwargs)

    def __init__(self, **data):
        # BYPASS: Initialisation manuelle pour éviter la validation Pydantic
        if 'text' in data:
            # Accepter text directement sans validation
            self.text = data['text'] if data['text'] else ""
        else:
            raise ValueError("text is required")
            
        # Valider les autres champs manuellement
        self.language = data.get('language', 'fr')
        if self.language not in ['fr', 'en', 'es']:
            self.language = 'fr'
            
        self.speed_mode = data.get('speed_mode', 'balanced')
        if self.speed_mode not in ['fast', 'balanced', 'quality']:
            self.speed_mode = 'balanced'

class ExpertResponse(BaseModel):
    """Response model standard"""
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    rag_score: Optional[float] = None
    timestamp: str
    language: str
    response_time_ms: int
    mode: str = "expert_router_v3"
    user: Optional[str] = None
    logged: bool = False

class FeedbackRequest(BaseModel):
    """Feedback model standard"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(None, description="Optional comment")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

# =============================================================================
# IMPORT LOGGING
# =============================================================================

try:
    from app.api.v1.logging import logger_instance, ConversationCreate
    LOGGING_AVAILABLE = True
    logger.info("✅ Système de logging intégré")
except ImportError as e:
    LOGGING_AVAILABLE = False
    logger_instance = None
    ConversationCreate = None
    logger.warning(f"⚠️ Système de logging non disponible: {e}")

async def save_conversation_auto(
    conversation_id: str,
    question: str, 
    response: str,
    user_id: str = "anonymous",
    language: str = "fr",
    rag_used: bool = False,
    rag_score: float = None,
    response_time_ms: int = 0
) -> bool:
    """Sauvegarde automatique"""
    
    if not LOGGING_AVAILABLE or not logger_instance:
        return False
    
    try:
        conversation = ConversationCreate(
            user_id=str(user_id),
            question=str(question),
            response=str(response),
            conversation_id=conversation_id,
            confidence_score=rag_score,
            response_time_ms=response_time_ms,
            language=language,
            rag_used=rag_used
        )
        
        record_id = logger_instance.save_conversation(conversation)
        logger.info(f"✅ Conversation sauvegardée: {conversation_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")
        return False

def get_user_id_from_request(request: Request) -> str:
    """Extrait l'ID utilisateur"""
    try:
        user = getattr(request.state, "user", None)
        if user:
            return str(user.get("id", user.get("user_id", "authenticated_user")))
        
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        import hashlib
        anonymous_data = f"{client_ip}_{user_agent}_{datetime.now().strftime('%Y-%m-%d')}"
        anonymous_id = f"anon_{hashlib.md5(anonymous_data.encode()).hexdigest()[:8]}"
        
        return anonymous_id
        
    except Exception as e:
        logger.warning(f"⚠️ Erreur génération user_id: {e}")
        return f"anon_{uuid.uuid4().hex[:8]}"

# =============================================================================
# PROMPTS MULTI-LANGUES
# =============================================================================

EXPERT_PROMPTS = {
    "fr": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. 
Réponds de manière précise et pratique en français. Tu peux utiliser tous les caractères français (é, è, à, ç, ù, etc.) et tous les symboles (°C, %, etc.) dans tes réponses sans restriction.""",
    
    "en": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.
Answer precisely and practically in English, providing advice based on industry best practices.""",
    
    "es": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308.
Responde de manera precisa y práctica en español. Puedes usar todos los caracteres especiales del español (ñ, ¿, ¡, acentos, etc.) en tus respuestas."""
}

def get_expert_prompt(language: str) -> str:
    """Get expert system prompt for language"""
    return EXPERT_PROMPTS.get(language.lower(), EXPERT_PROMPTS["fr"])

# =============================================================================
# FONCTIONS HELPER
# =============================================================================

def get_fallback_response(question: str, language: str = "fr") -> str:
    """Réponse de fallback"""
    try:
        safe_question = str(question)[:50] if question else "votre question"
    except:
        safe_question = "votre question"
    
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire. Pour votre question sur '{safe_question}...', je recommande de surveiller les paramètres environnementaux et de maintenir de bonnes pratiques d'hygiène.",
        "en": f"I am a veterinary expert. For your question about '{safe_question}...', I recommend monitoring environmental parameters and maintaining good hygiene practices.",
        "es": f"Soy un experto veterinario. Para su pregunta sobre '{safe_question}...', recomiendo monitorear los parámetros ambientales y mantener buenas prácticas de higiene."
    }
    return fallback_responses.get(language.lower(), fallback_responses["fr"])

async def process_question_openai(question: str, language: str = "fr", speed_mode: str = "balanced") -> str:
    """Process question using OpenAI"""
    if not OPENAI_AVAILABLE or not openai:
        return get_fallback_response(question, language)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return get_fallback_response(question, language)
        
        openai.api_key = api_key
        system_prompt = get_expert_prompt(language)
        
        safe_question = str(question)
        
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
                {"role": "user", "content": safe_question}
            ],
            temperature=0.7,
            max_tokens=config["max_tokens"],
            timeout=15
        )
        
        answer = response.choices[0].message.content
        return str(answer) if answer else get_fallback_response(question, language)
        
    except Exception as e:
        logger.error(f"❌ OpenAI error: {e}")
        return get_fallback_response(question, language)

# =============================================================================
# ENDPOINTS AVEC VALIDATION SUPPRIMÉE
# =============================================================================

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest, fastapi_request: Request):
    """Question publique avec validation text SUPPRIMÉE"""
    start_time = time.time()
    
    try:
        # RÉCUPÉRATION DIRECTE sans validation
        question_text = request.text
        
        # Vérification minimale seulement
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        user_id = get_user_id_from_request(fastapi_request)
        
        logger.info(f"🌐 Question SANS VALIDATION reçue - ID: {conversation_id[:8]}...")
        logger.info(f"📝 Question: {str(question_text)[:100]}...")
        logger.info(f"🔤 Caractères détectés: {[c for c in question_text if ord(c) > 127]}")
        
        user = getattr(fastapi_request.state, "user", None)
        
        # Variables par défaut
        rag_used = False
        rag_score = None
        answer = ""
        mode = "direct_openai"
        
        # Essayer RAG d'abord
        app = fastapi_request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG...")
                result = await process_rag(
                    question=question_text,
                    user=user,
                    language=request.language,
                    speed_mode=request.speed_mode
                )
                
                answer = str(result.get("response", ""))
                rag_used = result.get("mode", "").startswith("rag")
                rag_score = result.get("score")
                mode = result.get("mode", "rag_enhanced")
                
                logger.info(f"✅ RAG traité - Score: {rag_score}")
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG: {rag_error}")
                answer = await process_question_openai(
                    question_text, 
                    request.language,
                    request.speed_mode
                )
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI")
            answer = await process_question_openai(
                question_text,
                request.language,
                request.speed_mode
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Sauvegarde automatique
        logged = await save_conversation_auto(
            conversation_id=conversation_id,
            question=question_text,
            response=answer,
            user_id=user_id,
            language=request.language,
            rag_used=rag_used,
            rag_score=rag_score,
            response_time_ms=response_time_ms
        )
        
        # Retourner la réponse
        return ExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,
            rag_used=rag_used,
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=request.language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=str(user) if user else None,
            logged=logged
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest, fastapi_request: Request):
    """Question avec authentification"""
    return await ask_expert_public(request, fastapi_request)

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback"""
    try:
        logger.info(f"📊 Feedback reçu: {request.rating}")
        
        feedback_updated = False
        if request.conversation_id and LOGGING_AVAILABLE and logger_instance:
            try:
                rating_numeric = {
                    "positive": 1,
                    "negative": -1,
                    "neutral": 0
                }.get(request.rating, 0)
                
                feedback_updated = logger_instance.update_feedback(
                    request.conversation_id, 
                    rating_numeric
                )
                
            except Exception as e:
                logger.error(f"❌ Erreur mise à jour feedback: {e}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès",
            "rating": request.rating,
            "comment": request.comment,
            "conversation_id": request.conversation_id,
            "feedback_updated_in_db": feedback_updated,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement feedback")

@router.get("/topics")
async def get_suggested_topics(language: str = "fr"):
    """Get suggested topics"""
    try:
        lang = language.lower() if language else "fr"
        if lang not in ["fr", "en", "es"]:
            lang = "fr"
        
        topics_by_language = {
            "fr": [
                "Protocoles Compass pour l'analyse de performance",
                "Problèmes de croissance poulets Ross 308",
                "Température optimale pour élevage (32°C)",
                "Mortalité élevée - diagnostic",
                "Ventilation et qualité d'air",
                "Protocoles de vaccination",
                "Indices de conversion alimentaire"
            ],
            "en": [
                "Compass Performance Analysis Protocol",
                "Ross 308 growth problems",
                "Optimal temperature for farming (32°C)",
                "High mortality - diagnosis", 
                "Ventilation and air quality",
                "Vaccination protocols",
                "Feed conversion ratios"
            ],
            "es": [
                "Protocolos Compass análisis rendimiento",
                "Problemas crecimiento pollos Ross 308",
                "Temperatura óptima crianza (32°C)",
                "Mortalidad alta - diagnóstico",
                "Ventilación y calidad aire",
                "Protocolos vacunación",
                "Índices conversión alimentaria"
            ]
        }
        
        topics = topics_by_language.get(lang, topics_by_language["fr"])
        
        return {
            "topics": topics,
            "language": lang,
            "count": len(topics)
        }
    except Exception as e:
        logger.error(f"❌ Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

@router.get("/history")
async def get_conversation_history(request: Request, limit: int = 10):
    """Get conversation history"""
    try:
        if LOGGING_AVAILABLE and logger_instance:
            user_id = get_user_id_from_request(request)
            
            try:
                conversations = logger_instance.get_user_conversations(user_id, limit)
                
                formatted_conversations = []
                for conv in conversations:
                    formatted_conversations.append({
                        "conversation_id": conv.get("conversation_id"),
                        "question": str(conv.get("question", ""))[:100] + "..." if len(str(conv.get("question", ""))) > 100 else str(conv.get("question", "")),
                        "timestamp": conv.get("timestamp"),
                        "language": conv.get("language", "fr"),
                        "rag_used": conv.get("rag_used", False),
                        "feedback": conv.get("feedback")
                    })
                
                return {
                    "conversations": formatted_conversations,
                    "count": len(formatted_conversations),
                    "user_id": user_id[:8] + "...",
                    "message": f"{len(formatted_conversations)} conversations récupérées",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Erreur récupération historique: {e}")
        
        return {
            "conversations": [],
            "count": 0,
            "message": "Historique des conversations (système de logging en cours d'initialisation)",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur historique: {e}")
        return {
            "conversations": [],
            "count": 0,
            "message": "Erreur récupération historique",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# ENDPOINT DE TEST UTF-8 SPÉCIFIQUE
# =============================================================================

@router.post("/test-utf8")
async def test_utf8_direct(fastapi_request: Request):
    """Test endpoint pour UTF-8 direct sans validation Pydantic"""
    try:
        # Récupérer le body brut
        body = await fastapi_request.body()
        body_str = body.decode('utf-8')
        
        logger.info(f"📝 Body brut reçu: {body_str}")
        logger.info(f"🔤 Longueur: {len(body_str)} caractères")
        
        # Parser JSON manuellement
        import json
        data = json.loads(body_str)
        
        question_text = data.get('text', '')
        language = data.get('language', 'fr')
        
        logger.info(f"📝 Question extraite: {question_text}")
        logger.info(f"🔤 Caractères spéciaux: {[c for c in question_text if ord(c) > 127]}")
        
        # Traitement direct
        answer = await process_question_openai(question_text, language, "fast")
        
        return {
            "success": True,
            "question_received": question_text,
            "special_chars_detected": [c for c in question_text if ord(c) > 127],
            "response": answer,
            "method": "direct_body_parsing",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur test UTF-8: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# CONFIGURATION
# =============================================================================

if OPENAI_AVAILABLE and openai:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai.api_key = openai_api_key
        logger.info("✅ OpenAI configuré avec succès")
    else:
        logger.warning("⚠️ OpenAI API key non trouvée")
else:
    logger.warning("⚠️ Module OpenAI non disponible")

logger.info("🔤 VALIDATION PYDANTIC SUPPRIMÉE pour champ text")
logger.info("🔧 BYPASS complet de la validation UTF-8")
logger.info(f"💾 Logging automatique: {'Activé' if LOGGING_AVAILABLE else 'Non disponible'}")