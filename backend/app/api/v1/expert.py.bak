"""
app/api/v1/expert.py - VERSION CORRIGÉE AVEC AUTHENTIFICATION auth.py
CORRECTION: Utilise get_current_user de auth.py au lieu de dupliquer l'authentification
SOLUTION UTF-8: Validation Pydantic ultra-permissive fonctionnelle
MODIFICATION LIGNÉE GÉNÉTIQUE: Prompts adaptés pour éviter références spécifiques
CORRECTION 422: Renommage des paramètres request → question_data
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Import de l'authentification centralisée
try:
    from app.api.v1.auth import get_current_user
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    get_current_user = None

# OpenAI import sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# Configuration sécurité pour authentification
security = HTTPBearer()

# =============================================================================
# MODÈLES PYDANTIC AVEC VALIDATION SUPPRIMÉE POUR TEXT (VERSION FONCTIONNELLE)
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model avec validation text DÉSACTIVÉE mais compatible FastAPI"""
    text: str = Field(..., description="Question text (NO validation)")
    language: Optional[str] = Field("fr", description="Response language")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode")

    # Configuration PERMISSIVE
    model_config = ConfigDict(
        validate_assignment=False,
        str_strip_whitespace=False,  # CRITIQUE: Ne pas toucher au texte
        extra="ignore",
        validate_default=False
    )

    # SOLUTION: Validation qui n'échoue JAMAIS pour text
    @field_validator('text', mode='before')
    @classmethod
    def validate_text_always_pass(cls, v):
        """Validation qui accepte TOUT pour text"""
        # Si c'est vide, on rejette seulement
        if not v:
            raise ValueError("Question text cannot be empty")
        
        # Sinon, on accepte TOUT sans transformation
        return v

    @field_validator('language', mode='before')
    @classmethod
    def validate_language_safe(cls, v):
        """Validation langue safe"""
        if not v or str(v).lower() not in ['fr', 'en', 'es']:
            return 'fr'
        return str(v).lower()

    @field_validator('speed_mode', mode='before')
    @classmethod
    def validate_speed_mode_safe(cls, v):
        """Validation speed_mode safe"""
        if not v or str(v).lower() not in ['fast', 'balanced', 'quality']:
            return 'balanced'
        return str(v).lower()

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
    mode: str = "expert_router_final"
    user: Optional[str] = None
    logged: bool = False

class FeedbackRequest(BaseModel):
    """Feedback model standard"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(None, description="Optional comment")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

    @field_validator('rating', mode='before')
    @classmethod
    def validate_rating_safe(cls, v):
        if not v or str(v).lower() not in ['positive', 'negative', 'neutral']:
            return 'neutral'
        return str(v).lower()

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

def get_user_id_from_request(fastapi_request: Request) -> str:
    """Extrait l'ID utilisateur"""
    try:
        user = getattr(fastapi_request.state, "user", None)
        if user:
            return str(user.get("id", user.get("user_id", "authenticated_user")))
        
        client_ip = fastapi_request.client.host if fastapi_request.client else "unknown"
        user_agent = fastapi_request.headers.get("user-agent", "unknown")
        
        import hashlib
        anonymous_data = f"{client_ip}_{user_agent}_{datetime.now().strftime('%Y-%m-%d')}"
        anonymous_id = f"anon_{hashlib.md5(anonymous_data.encode()).hexdigest()[:8]}"
        
        return anonymous_id
        
    except Exception as e:
        logger.warning(f"⚠️ Erreur génération user_id: {e}")
        return f"anon_{uuid.uuid4().hex[:8]}"

# =============================================================================
# PROMPTS MULTI-LANGUES AVEC CONSIGNE LIGNÉE GÉNÉTIQUE
# =============================================================================

EXPERT_PROMPTS = {
    "fr": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair. 
Réponds de manière précise et pratique en français. Tu peux utiliser tous les caractères français (é, è, à, ç, ù, etc.) et tous les symboles (°C, %, etc.) dans tes réponses.

IMPORTANT: Ne fais pas référence à une lignée génétique comme Ross ou Cobb, sauf si l'utilisateur la mentionne dans sa question. Donne une réponse générale qui s'applique à tous les poulets de chair.""",
    
    "en": """You are a veterinary expert specialized in animal health and nutrition, particularly for broiler chickens.
Answer precisely and practically in English, providing advice based on industry best practices.

IMPORTANT: Do not reference specific genetic lines like Ross or Cobb, unless the user mentions them in their question. Provide general answers that apply to all broiler chickens.""",
    
    "es": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde.
Responde de manera precisa y práctica en español. Puedes usar todos los caractères especiales del español (ñ, ¿, ¡, acentos, etc.) en tus respuestas.

IMPORTANTE: No hagas referencia a líneas genéticas como Ross o Cobb, a menos que el usuario las mencione en su pregunta. Da respuestas generales que se apliquen a todos los pollos de engorde."""
}

def get_expert_prompt(language: str) -> str:
    """Get expert system prompt for language avec consigne lignée génétique"""
    return EXPERT_PROMPTS.get(language.lower(), EXPERT_PROMPTS["fr"])

# =============================================================================
# FONCTIONS HELPER
# =============================================================================

def get_fallback_response(question: str, language: str = "fr") -> str:
    """Réponse de fallback avec lignée générique"""
    try:
        safe_question = str(question)[:50] if question else "votre question"
    except:
        safe_question = "votre question"
    
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire. Pour votre question sur '{safe_question}...', je recommande de surveiller les paramètres environnementaux et de maintenir de bonnes pratiques d'hygiène pour vos poulets de chair.",
        "en": f"I am a veterinary expert. For your question about '{safe_question}...', I recommend monitoring environmental parameters and maintaining good hygiene practices for your broiler chickens.",
        "es": f"Soy un experto veterinario. Para su pregunta sobre '{safe_question}...', recomiendo monitorear los parámetros ambientales y mantener buenas prácticas de higiene para sus pollos de engorde."
    }
    return fallback_responses.get(language.lower(), fallback_responses["fr"])

async def process_question_openai(question: str, language: str = "fr", speed_mode: str = "balanced") -> str:
    """Process question using OpenAI avec consigne lignée génétique"""
    if not OPENAI_AVAILABLE or not openai:
        return get_fallback_response(question, language)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return get_fallback_response(question, language)
        
        openai.api_key = api_key
        # get_expert_prompt contient maintenant la consigne lignée génétique
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
# ENDPOINTS AVEC AUTHENTIFICATION CENTRALISÉE
# =============================================================================

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert_secure(
    question_data: QuestionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user) if AUTH_AVAILABLE else None,
    fastapi_request: Request = None
):
    """Question avec authentification Supabase via auth.py"""
    start_time = time.time()
    
    try:
        # Vérifier si l'authentification est disponible
        if not AUTH_AVAILABLE or not current_user:
            raise HTTPException(
                status_code=503,
                detail="Service d'authentification non disponible"
            )
        
        # L'utilisateur est authentifié via auth.py
        user_id = current_user.get("user_id")
        user_email = current_user.get("email")
        
        logger.info(f"🔐 Question sécurisée de {user_email} ({user_id[:8] if user_id else 'N/A'}...)")
        
        # Ajouter les infos utilisateur à la requête (si disponible)
        if fastapi_request:
            fastapi_request.state.user = current_user
        
        # Récupération directe de la question
        question_text = question_data.text
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        
        logger.info(f"🌐 Question SÉCURISÉE reçue - ID: {conversation_id[:8]}...")
        logger.info(f"📝 Question: {str(question_text)[:100]}...")
        logger.info(f"🔤 Caractères spéciaux: {[c for c in question_text if ord(c) > 127]}")
        
        # Variables par défaut
        rag_used = False
        rag_score = None
        answer = ""
        mode = "authenticated_direct_openai"
        
        # Essayer RAG d'abord (si fastapi_request disponible)
        if fastapi_request:
            app = fastapi_request.app
            process_rag = getattr(app.state, 'process_question_with_rag', None)
            
            if process_rag:
                try:
                    logger.info("🔍 Utilisation du système RAG pour utilisateur authentifié...")
                    result = await process_rag(
                        question=question_text,
                        user=current_user,  # Passer current_user de auth.py
                        language=question_data.language,
                        speed_mode=question_data.speed_mode
                    )
                    
                    answer = str(result.get("response", ""))
                    rag_used = result.get("mode", "").startswith("rag")
                    rag_score = result.get("score")
                    mode = f"authenticated_{result.get('mode', 'rag_enhanced')}"
                    
                    logger.info(f"✅ RAG traité pour utilisateur authentifié - Score: {rag_score}")
                    
                except Exception as rag_error:
                    logger.error(f"❌ Erreur RAG pour utilisateur authentifié: {rag_error}")
                    answer = await process_question_openai(
                        question_text, 
                        question_data.language,
                        question_data.speed_mode
                    )
                    mode = "authenticated_fallback_openai"
            else:
                logger.info("⚠️ RAG non disponible, utilisation OpenAI pour utilisateur authentifié")
                answer = await process_question_openai(
                    question_text,
                    question_data.language,
                    question_data.speed_mode
                )
                mode = "authenticated_direct_openai"
        else:
            # Pas de fastapi_request, utilisation directe OpenAI
            logger.info("⚠️ Pas de fastapi_request, utilisation OpenAI direct")
            answer = await process_question_openai(
                question_text,
                question_data.language,
                question_data.speed_mode
            )
            mode = "authenticated_direct_openai"
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Sauvegarde automatique avec vrai user_id
        logged = await save_conversation_auto(
            conversation_id=conversation_id,
            question=question_text,
            response=answer,
            user_id=user_id or "authenticated_user",  # user_id de auth.py
            language=question_data.language,
            rag_used=rag_used,
            rag_score=rag_score,
            response_time_ms=response_time_ms
        )
        
        # Retourner la réponse avec infos utilisateur
        return ExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,
            rag_used=rag_used,
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=question_data.language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=user_email,  # Email de l'utilisateur authentifié via auth.py
            logged=logged
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert sécurisé: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(question_data: QuestionRequest, fastapi_request: Request):
    """Question publique avec validation text FONCTIONNELLE"""
    start_time = time.time()
    
    try:
        # Récupération directe - plus de problème d'initialisation
        question_text = question_data.text
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        user_id = get_user_id_from_request(fastapi_request)
        
        logger.info(f"🌐 Question PUBLIQUE reçue - ID: {conversation_id[:8]}...")
        logger.info(f"📝 Question: {str(question_text)[:100]}...")
        logger.info(f"🔤 Caractères spéciaux: {[c for c in question_text if ord(c) > 127]}")
        
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
                    language=question_data.language,
                    speed_mode=question_data.speed_mode
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
                    question_data.language,
                    question_data.speed_mode
                )
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI")
            answer = await process_question_openai(
                question_text,
                question_data.language,
                question_data.speed_mode
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Sauvegarde automatique
        logged = await save_conversation_auto(
            conversation_id=conversation_id,
            question=question_text,
            response=answer,
            user_id=user_id,
            language=question_data.language,
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
            language=question_data.language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=str(user) if user else None,
            logged=logged
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/feedback")
async def submit_feedback(feedback_data: FeedbackRequest):
    """Submit feedback"""
    try:
        logger.info(f"📊 Feedback reçu: {feedback_data.rating}")
        
        feedback_updated = False
        if feedback_data.conversation_id and LOGGING_AVAILABLE and logger_instance:
            try:
                rating_numeric = {
                    "positive": 1,
                    "negative": -1,
                    "neutral": 0
                }.get(feedback_data.rating, 0)
                
                feedback_updated = logger_instance.update_feedback(
                    feedback_data.conversation_id, 
                    rating_numeric
                )
                
            except Exception as e:
                logger.error(f"❌ Erreur mise à jour feedback: {e}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès",
            "rating": feedback_data.rating,
            "comment": feedback_data.comment,
            "conversation_id": feedback_data.conversation_id,
            "feedback_updated_in_db": feedback_updated,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement feedback")

@router.get("/topics")
async def get_suggested_topics(language: str = "fr"):
    """Get suggested topics avec lignées génériques"""
    try:
        lang = language.lower() if language else "fr"
        if lang not in ["fr", "en", "es"]:
            lang = "fr"
        
        topics_by_language = {
            "fr": [
                "Protocoles Compass pour l'analyse de performance",
                "Problèmes de croissance poulets de chair",
                "Température optimale pour élevage (32°C)",
                "Mortalité élevée - diagnostic",
                "Ventilation et qualité d'air",
                "Protocoles de vaccination",
                "Indices de conversion alimentaire"
            ],
            "en": [
                "Compass Performance Analysis Protocol",
                "Broiler chicken growth problems",
                "Optimal temperature for farming (32°C)",
                "High mortality - diagnosis", 
                "Ventilation and air quality",
                "Vaccination protocols",
                "Feed conversion ratios"
            ],
            "es": [
                "Protocolos Compass análisis rendimiento",
                "Problemas crecimiento pollos de engorde",
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
            "count": len(topics),
            "note": "Topics génériques pour tous poulets de chair"
        }
    except Exception as e:
        logger.error(f"❌ Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

@router.get("/history")
async def get_conversation_history(fastapi_request: Request, limit: int = 10):
    """Get conversation history"""
    try:
        if LOGGING_AVAILABLE and logger_instance:
            user_id = get_user_id_from_request(fastapi_request)
            
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
# ENDPOINTS D'AUTHENTIFICATION UTILITAIRES
# =============================================================================

@router.get("/auth-status")
async def get_auth_status(current_user: Dict[str, Any] = Depends(get_current_user) if AUTH_AVAILABLE else None):
    """Vérifier le statut d'authentification - REQUIERT TOKEN"""
    if not AUTH_AVAILABLE or not current_user:
        raise HTTPException(
            status_code=503,
            detail="Service d'authentification non disponible"
        )
    
    return {
        "authenticated": True,
        "user_id": current_user.get('user_id'),
        "email": current_user.get('email'),
        "message": "Utilisateur authentifié avec succès via auth.py",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/test-auth")
async def test_auth_endpoint(
    question_data: QuestionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user) if AUTH_AVAILABLE else None
):
    """Endpoint de test pour vérifier l'authentification - REQUIERT TOKEN"""
    if not AUTH_AVAILABLE or not current_user:
        raise HTTPException(
            status_code=503,
            detail="Service d'authentification non disponible"
        )
    
    return {
        "success": True,
        "message": "🔐 Authentification fonctionnelle via auth.py !",
        "user_email": current_user.get('email'),
        "user_id": str(current_user.get('user_id', ''))[:8] + "...",
        "question_received": question_data.text,
        "question_length": len(question_data.text),
        "special_chars": [c for c in question_data.text if ord(c) > 127],
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# ENDPOINT DE TEST UTF-8 (GARDE CAR IL FONCTIONNE)
# =============================================================================

@router.post("/test-utf8")
async def test_utf8_direct(fastapi_request: Request):
    """Test endpoint pour UTF-8 direct - FONCTIONNE PARFAITEMENT"""
    try:
        # Récupérer le body brut
        body = await fastapi_request.body()
        body_str = body.decode('utf-8')
        
        logger.info(f"📝 Body brut reçu: {body_str}")
        
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
            "genetic_line_note": "Response uses generic 'broiler chickens' terminology",
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

logger.info("🔤 VALIDATION UTF-8 FONCTIONNELLE avec field_validator")
logger.info("🔧 Compatible FastAPI - plus d'erreur 500")
logger.info("🧬 LIGNÉE GÉNÉTIQUE: Prompts génériques sauf mention utilisateur")
logger.info(f"💾 Logging automatique: {'Activé' if LOGGING_AVAILABLE else 'Non disponible'}")
logger.info(f"🔐 Authentification centralisée: {'Activée' if AUTH_AVAILABLE else 'auth.py requis'}")
logger.info(f"🛡️ Sécurité /ask: Authentification via auth.py")
logger.info(f"🌐 Endpoint public /ask-public: Toujours disponible sans auth")
logger.info(f"📝 Topics suggérés: Terminologie générique (poulets de chair/broiler chickens/pollos de engorde)")
logger.info("🔧 CORRECTION 422: Paramètres renommés request → question_data/feedback_data")