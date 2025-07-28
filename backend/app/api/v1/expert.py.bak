"""
app/api/v1/expert.py - VERSION COMPLÈTE AVEC AUTHENTIFICATION SUPABASE SÉCURISÉE
OPTION A: Authentification OBLIGATOIRE sur /ask
SOLUTION UTF-8: Validation Pydantic ultra-permissive fonctionnelle
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

# JWT import pour authentification Supabase
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None

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
# FONCTIONS D'AUTHENTIFICATION SUPABASE
# =============================================================================

def get_supabase_config():
    """Récupère la configuration Supabase"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_jwt_secret = os.getenv('SUPABASE_JWT_SECRET')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_jwt_secret:
        logger.warning("⚠️ Configuration Supabase incomplète")
        return None, None, None
    
    return supabase_url, supabase_jwt_secret, supabase_anon_key

async def verify_supabase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Vérifie le token JWT Supabase - AUTHENTIFICATION OBLIGATOIRE
    """
    if not JWT_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Service d'authentification non disponible (PyJWT requis)"
        )
    
    try:
        token = credentials.credentials
        supabase_url, jwt_secret, anon_key = get_supabase_config()
        
        if not jwt_secret:
            raise HTTPException(
                status_code=503, 
                detail="Service d'authentification non configuré (SUPABASE_JWT_SECRET manquant)"
            )
        
        # Vérification du JWT Supabase
        try:
            payload = jwt.decode(
                token, 
                jwt_secret, 
                algorithms=["HS256"],
                options={"verify_aud": False}  # Supabase n'utilise pas toujours aud
            )
            
            user_id = payload.get('sub')
            email = payload.get('email')
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Token invalide: pas d'utilisateur")
            
            logger.info(f"🔐 Utilisateur authentifié: {email} ({user_id[:8]}...)")
            
            # Retourner les infos utilisateur
            return {
                "user_id": user_id,
                "email": email,
                "raw_token": token,
                "payload": payload,
                "authenticated": True
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expiré")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Token invalide: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur vérification token: {e}")
        raise HTTPException(status_code=401, detail="Erreur d'authentification")

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
Réponds de manière précise et pratique en français. Tu peux utiliser tons les caractères français (é, è, à, ç, ù, etc.) et tous les symboles (°C, %, etc.) dans tes réponses.""",
    
    "en": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.
Answer precisely and practically in English, providing advice based on industry best practices.""",
    
    "es": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308.
Responde de manera precisa y práctica en español. Puedes usar todos los caractères especiales del español (ñ, ¿, ¡, acentos, etc.) en tus respuestas."""
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
# ENDPOINTS AVEC AUTHENTIFICATION SÉCURISÉE
# =============================================================================

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert_secure(
    request: QuestionRequest, 
    fastapi_request: Request,
    user_auth = Depends(verify_supabase_token)  # AUTHENTIFICATION OBLIGATOIRE
):
    """Question avec authentification Supabase OBLIGATOIRE - SÉCURISÉ"""
    start_time = time.time()
    
    try:
        # L'utilisateur est authentifié, on a ses infos dans user_auth
        logger.info(f"🔐 Question sécurisée de {user_auth['email']} ({user_auth['user_id'][:8]}...)")
        
        # Ajouter les infos utilisateur à la requête
        fastapi_request.state.user = user_auth
        
        # Récupération directe - plus de problème d'initialisation
        question_text = request.text
        
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
        
        # Essayer RAG d'abord
        app = fastapi_request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG pour utilisateur authentifié...")
                result = await process_rag(
                    question=question_text,
                    user=user_auth,  # Passer les infos utilisateur authentifié au RAG
                    language=request.language,
                    speed_mode=request.speed_mode
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
                    request.language,
                    request.speed_mode
                )
                mode = "authenticated_fallback_openai"
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI pour utilisateur authentifié")
            answer = await process_question_openai(
                question_text,
                request.language,
                request.speed_mode
            )
            mode = "authenticated_direct_openai"
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Sauvegarde automatique avec vrai user_id
        logged = await save_conversation_auto(
            conversation_id=conversation_id,
            question=question_text,
            response=answer,
            user_id=user_auth['user_id'],  # Vrai user_id authentifié Supabase
            language=request.language,
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
            language=request.language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=user_auth['email'],  # Email de l'utilisateur authentifié
            logged=logged
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert sécurisé: {e}")
        # Log détaillé pour debug
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest, fastapi_request: Request):
    """Question publique avec validation text FONCTIONNELLE"""
    start_time = time.time()
    
    try:
        # Récupération directe - plus de problème d'initialisation
        question_text = request.text
        
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
        # Log détaillé pour debug
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

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
# ENDPOINTS D'AUTHENTIFICATION UTILITAIRES
# =============================================================================

@router.get("/auth-status")
async def get_auth_status(user_auth = Depends(verify_supabase_token)):
    """Vérifier le statut d'authentification - REQUIERT TOKEN"""
    return {
        "authenticated": True,
        "user_id": user_auth['user_id'],
        "email": user_auth['email'],
        "message": "Utilisateur authentifié avec succès",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/test-auth")
async def test_auth_endpoint(
    request: QuestionRequest,
    user_auth = Depends(verify_supabase_token)
):
    """Endpoint de test pour vérifier l'authentification - REQUIERT TOKEN"""
    return {
        "success": True,
        "message": "🔐 Authentification fonctionnelle !",
        "user_email": user_auth['email'],
        "user_id": user_auth['user_id'][:8] + "...",
        "question_received": request.text,
        "question_length": len(request.text),
        "special_chars": [c for c in request.text if ord(c) > 127],
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
logger.info(f"💾 Logging automatique: {'Activé' if LOGGING_AVAILABLE else 'Non disponible'}")
logger.info(f"🔐 Authentification JWT: {'Activée' if JWT_AVAILABLE else 'PyJWT requis'}")
logger.info(f"🛡️ Sécurité /ask: Authentification Supabase OBLIGATOIRE")
logger.info(f"🌐 Endpoint public /ask-public: Toujours disponible sans auth")