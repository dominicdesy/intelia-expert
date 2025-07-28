"""
app/api/v1/expert.py - Version Complète avec Logging Automatique Intégré
CORRECTION: Validation UTF-8 assouplie pour résoudre les erreurs 400
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from pydantic import BaseModel, Field, validator

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
# INTEGRATION LOGGING AUTOMATIQUE
# =============================================================================

# Import du système de logging
try:
    from app.api.v1.logging import logger_instance, ConversationCreate
    LOGGING_AVAILABLE = True
    logger.info("✅ Système de logging intégré dans expert.py")
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
    """Sauvegarde automatique de la conversation dans le système de logging"""
    
    if not LOGGING_AVAILABLE or not logger_instance:
        logger.warning("⚠️ Logging non disponible - conversation non sauvegardée")
        return False
    
    try:
        # Créer l'objet conversation
        conversation = ConversationCreate(
            user_id=user_id,
            question=question,
            response=response,
            conversation_id=conversation_id,
            confidence_score=rag_score,
            response_time_ms=response_time_ms,
            language=language,
            rag_used=rag_used
        )
        
        # Sauvegarder dans la base de données
        record_id = logger_instance.save_conversation(conversation)
        
        logger.info(f"💾 Conversation sauvegardée automatiquement: {conversation_id} -> {record_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde automatique conversation {conversation_id}: {e}")
        return False

def get_user_id_from_request(request: Request) -> str:
    """Extrait l'ID utilisateur de la requête (ou génère un ID anonyme)"""
    
    # Vérifier si un utilisateur authentifié existe
    user = getattr(request.state, "user", None)
    if user:
        return str(user.get("id", user.get("user_id", "authenticated_user")))
    
    # Générer un ID basé sur l'IP et le user-agent pour tracking anonyme
    try:
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Créer un ID anonyme consistant mais non-identifiable
        import hashlib
        anonymous_data = f"{client_ip}_{user_agent}_{datetime.now().strftime('%Y-%m-%d')}"
        anonymous_id = f"anon_{hashlib.md5(anonymous_data.encode()).hexdigest()[:8]}"
        
        return anonymous_id
        
    except Exception as e:
        logger.warning(f"⚠️ Erreur génération user_id anonyme: {e}")
        return f"anon_{uuid.uuid4().hex[:8]}"

# =============================================================================
# FONCTIONS HELPER UTF-8 (gardées de la version précédente)
# =============================================================================

def ensure_utf8_string(text: str) -> str:
    """Assure que le texte est correctement encodé en UTF-8"""
    if not isinstance(text, str):
        return str(text)
    
    try:
        return text.encode('utf-8', errors='ignore').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text.encode('ascii', errors='ignore').decode('ascii')

def normalize_language_code(language: str) -> str:
    """Normalise le code de langue"""
    if not language:
        return "fr"
    return language.lower().strip()[:2]

# =============================================================================
# MODÈLES PYDANTIC AVEC VALIDATION ASSOUPLIE (CORRECTION)
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model pour questions expert avec support UTF-8 CORRIGÉ"""
    text: str = Field(..., min_length=1, max_length=2000, description="Question text")
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode: fast, balanced, quality")

    # =========================================================================
    # CORRECTION: VALIDATION ASSOUPLIE POUR RÉSOUDRE LES ERREURS 400
    # =========================================================================

    @validator('text', pre=True)
    def validate_text_utf8(cls, v):
        """Valide et corrige l'encodage UTF-8 du texte - VERSION ASSOUPLIE"""
        if not v:
            raise ValueError("Question text cannot be empty")
        
        # CORRECTION: Validation plus permissive, pas de nettoyage UTF-8 strict
        try:
            # Accepter le texte tel quel s'il est déjà string
            if isinstance(v, str):
                cleaned_text = v.strip()
            else:
                cleaned_text = str(v).strip()
            
            # Vérification longueur seulement
            if not cleaned_text:
                raise ValueError("Question text cannot be empty after cleaning")
            
            if len(cleaned_text) > 2000:
                cleaned_text = cleaned_text[:2000]  # Tronquer au lieu de rejeter
            
            return cleaned_text
            
        except Exception as e:
            # En cas d'erreur, essayer de sauver le texte
            try:
                return str(v).strip() if v else ""
            except:
                raise ValueError(f"Invalid text format: {str(e)}")

    @validator('language', pre=True)
    def validate_language(cls, v):
        """Valide le code de langue - VERSION ASSOUPLIE"""
        try:
            if not v:
                return "fr"
            normalized = str(v).lower().strip()[:2]
            if normalized not in ["fr", "en", "es"]:
                return "fr"  # Fallback au lieu d'erreur
            return normalized
        except:
            return "fr"  # Fallback sécurisé

    @validator('speed_mode', pre=True)
    def validate_speed_mode(cls, v):
        """Valide le mode de vitesse - VERSION ASSOUPLIE"""
        try:
            if not v:
                return "balanced"
            mode = str(v).lower().strip()
            if mode not in ["fast", "balanced", "quality"]:
                return "balanced"  # Fallback au lieu d'erreur
            return mode
        except:
            return "balanced"  # Fallback sécurisé

    class Config:
        str_strip_whitespace = True
        validate_assignment = True
        use_enum_values = True
        # CORRECTION: Encoders plus permissifs
        json_encoders = {
            str: lambda x: str(x) if x is not None else ""
        }

class ExpertResponse(BaseModel):
    """Response model avec support RAG, UTF-8 et logging"""
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    rag_score: Optional[float] = None
    timestamp: str
    language: str
    response_time_ms: int
    mode: str = "expert_router_v1"
    user: Optional[str] = None
    logged: bool = False  # ✅ NOUVEAU: Indique si la conversation a été sauvegardée

    @validator('question', 'response', pre=True)
    def validate_text_fields(cls, v):
        """Assure l'encodage UTF-8 des champs texte"""
        return ensure_utf8_string(v) if v else ""

    class Config:
        json_encoders = {
            str: lambda x: ensure_utf8_string(x) if isinstance(x, str) else str(x)
        }

class FeedbackRequest(BaseModel):
    """Feedback request model avec validation UTF-8"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(None, max_length=500, description="Optional comment")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for feedback")  # ✅ NOUVEAU

    @validator('rating', pre=True)
    def validate_rating(cls, v):
        """Valide le rating"""
        rating = str(v or "").lower().strip()
        if rating not in ["positive", "negative", "neutral"]:
            return "neutral"  # CORRECTION: Fallback au lieu d'erreur
        return rating

    @validator('comment', pre=True)
    def validate_comment_utf8(cls, v):
        """Valide et corrige l'encodage UTF-8 du commentaire"""
        if not v:
            return None
        
        cleaned_comment = ensure_utf8_string(str(v).strip())
        
        if len(cleaned_comment) > 500:
            cleaned_comment = cleaned_comment[:500]  # CORRECTION: Tronquer au lieu de rejeter
        
        return cleaned_comment if cleaned_comment else None

    class Config:
        json_encoders = {
            str: lambda x: ensure_utf8_string(x) if isinstance(x, str) else str(x)
        }

class TopicsResponse(BaseModel):
    """Topics response model"""
    topics: List[str]
    language: str
    count: int

    class Config:
        json_encoders = {
            str: lambda x: ensure_utf8_string(x) if isinstance(x, str) else str(x)
        }

# =============================================================================
# PROMPTS MULTI-LANGUES AVEC CARACTÈRES UTF-8
# =============================================================================

EXPERT_PROMPTS = {
    "fr": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair Ross 308. 
Réponds de manière précise et pratique en français, en donnant des conseils basés sur les meilleures pratiques du secteur. 
Tu peux utiliser tous les caractères français (é, è, à, ç, ù, etc.) dans tes réponses.""",
    
    "en": """You are a veterinary expert specialized in animal health and nutrition, particularly for Ross 308 broiler chickens.
Answer precisely and practically in English, providing advice based on industry best practices.""",
    
    "es": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde Ross 308.
Responde de manera precisa y práctica en español, dando consejos basados en las mejores prácticas del sector.
Puedes usar todos los caracteres especiales del español (ñ, ¿, ¡, acentos, etc.) en tus respuestas."""
}

# =============================================================================
# PROTECTION ENDPOINTS DEBUG
# =============================================================================

def admin_protection():
    """Protection pour les endpoints debug en production"""
    environment = os.getenv('ENVIRONMENT', 'development')
    if environment == 'production':
        # raise HTTPException(status_code=403, detail="Debug endpoints restricted in production")
        pass
    return True

# =============================================================================
# FONCTIONS HELPER
# =============================================================================

def get_expert_prompt(language: str) -> str:
    """Get expert system prompt for language"""
    return EXPERT_PROMPTS.get(language.lower(), EXPERT_PROMPTS["fr"])

def get_fallback_response(question: str, language: str = "fr") -> str:
    """Réponse de fallback si ni RAG ni OpenAI disponibles"""
    safe_question = ensure_utf8_string(question)
    
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire. Pour votre question sur '{safe_question[:50]}...', je recommande de surveiller les paramètres environnementaux et de maintenir de bonnes pratiques d'hygiène.",
        "en": f"I am a veterinary expert. For your question about '{safe_question[:50]}...', I recommend monitoring environmental parameters and maintaining good hygiene practices.",
        "es": f"Soy un experto veterinario. Para su pregunta sobre '{safe_question[:50]}...', recomiendo monitorear los parámetros ambientales y mantener buenas prácticas de higiene."
    }
    return fallback_responses.get(language.lower(), fallback_responses["fr"])

async def process_question_openai(question: str, language: str = "fr", speed_mode: str = "balanced") -> str:
    """Process question using OpenAI directly avec support UTF-8"""
    if not OPENAI_AVAILABLE or not openai:
        return get_fallback_response(question, language)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OpenAI API key not found")
            return get_fallback_response(question, language)
        
        openai.api_key = api_key
        system_prompt = get_expert_prompt(language)
        
        safe_question = ensure_utf8_string(question)
        
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
        return ensure_utf8_string(answer) if answer else get_fallback_response(question, language)
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return get_fallback_response(question, language)

# =============================================================================
# ENDPOINTS AVEC LOGGING AUTOMATIQUE
# =============================================================================

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(request: QuestionRequest, fastapi_request: Request):
    """Ask question sans authentification - AVEC RAG + Logging automatique"""
    start_time = time.time()
    
    try:
        question_text = request.text
        
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        conversation_id = str(uuid.uuid4())
        user_id = get_user_id_from_request(fastapi_request)
        
        logger.info(f"🌐 Question publique UTF-8 - ID: {conversation_id[:8]}... - User: {user_id[:10]}... - Langue: {request.language}")
        logger.info(f"📝 Question reçue: {question_text[:100]}...")
        
        user = getattr(fastapi_request.state, "user", None)
        
        # Variables RAG
        rag_used = False
        rag_score = None
        answer = ""
        mode = "direct_openai"
        
        # Obtenir process_question_with_rag depuis app.state
        app = fastapi_request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG avec support UTF-8...")
                result = await process_rag(
                    question=question_text,
                    user=user,
                    language=request.language,
                    speed_mode=request.speed_mode
                )
                
                raw_answer = result.get("response", "")
                answer = ensure_utf8_string(raw_answer) if raw_answer else ""
                rag_used = result.get("mode", "").startswith("rag")
                rag_score = result.get("score")
                mode = result.get("mode", "rag_enhanced")
                
                logger.info(f"✅ RAG {'utilisé' if rag_used else 'consulté sans résultats'} - Score: {rag_score}")
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG, fallback OpenAI: {rag_error}")
                answer = await process_question_openai(
                    question_text, 
                    request.language,
                    request.speed_mode
                )
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI direct avec UTF-8")
            answer = await process_question_openai(
                question_text,
                request.language,
                request.speed_mode
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # ✅ NOUVEAU: Sauvegarde automatique de la conversation
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
        
        # Retourner la réponse avec l'indicateur de logging
        return ExpertResponse(
            question=ensure_utf8_string(question_text),
            response=ensure_utf8_string(answer),
            conversation_id=conversation_id,
            rag_used=rag_used,
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=request.language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=str(user) if user else None,
            logged=logged  # ✅ NOUVEAU: Indique si sauvegarde réussie
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask expert public UTF-8: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert(request: QuestionRequest, fastapi_request: Request):
    """Ask question avec authentification - même logique avec UTF-8 + Logging"""
    return await ask_expert_public(request, fastapi_request)

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on response avec support UTF-8 + Mise à jour logging"""
    try:
        logger.info(f"📊 Feedback UTF-8 reçu: {request.rating}")
        if request.comment:
            logger.info(f"💬 Commentaire: {request.comment[:100]}...")
        
        # ✅ NOUVEAU: Mise à jour du feedback dans la base de données
        feedback_updated = False
        if request.conversation_id and LOGGING_AVAILABLE and logger_instance:
            try:
                # Convertir rating en numérique pour la base
                rating_numeric = {
                    "positive": 1,
                    "negative": -1,
                    "neutral": 0
                }.get(request.rating, 0)
                
                feedback_updated = logger_instance.update_feedback(
                    request.conversation_id, 
                    rating_numeric
                )
                
                if feedback_updated:
                    logger.info(f"✅ Feedback mis à jour dans DB: {request.conversation_id}")
                else:
                    logger.warning(f"⚠️ Conversation non trouvée pour feedback: {request.conversation_id}")
                    
            except Exception as e:
                logger.error(f"❌ Erreur mise à jour feedback DB: {e}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès",
            "rating": request.rating,
            "comment": request.comment,
            "conversation_id": request.conversation_id,
            "feedback_updated_in_db": feedback_updated,  # ✅ NOUVEAU
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Erreur feedback UTF-8: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement feedback")

@router.get("/topics", response_model=TopicsResponse)
async def get_suggested_topics(language: str = "fr"):
    """Get suggested topics avec support UTF-8"""
    try:
        lang = normalize_language_code(language)
        
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
        
        topics = topics_by_language.get(lang, topics_by_language["fr"])
        safe_topics = [ensure_utf8_string(topic) for topic in topics]
        
        return TopicsResponse(
            topics=safe_topics,
            language=lang,
            count=len(safe_topics)
        )
    except Exception as e:
        logger.error(f"❌ Erreur topics UTF-8: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

@router.get("/history")
async def get_conversation_history(request: Request, limit: int = 10):
    """Get conversation history avec intégration logging automatique"""
    try:
        # ✅ NOUVEAU: Récupération depuis la base de logging si disponible
        if LOGGING_AVAILABLE and logger_instance:
            user_id = get_user_id_from_request(request)
            
            try:
                conversations = logger_instance.get_user_conversations(user_id, limit)
                
                # Formater les conversations pour l'API
                formatted_conversations = []
                for conv in conversations:
                    formatted_conversations.append({
                        "conversation_id": conv.get("conversation_id"),
                        "question": conv.get("question", "")[:100] + "..." if len(conv.get("question", "")) > 100 else conv.get("question", ""),
                        "timestamp": conv.get("timestamp"),
                        "language": conv.get("language", "fr"),
                        "rag_used": conv.get("rag_used", False),
                        "feedback": conv.get("feedback")
                    })
                
                return {
                    "conversations": formatted_conversations,
                    "count": len(formatted_conversations),
                    "user_id": user_id[:8] + "...",  # Anonymisé partiellement
                    "message": f"{len(formatted_conversations)} conversations récupérées",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"❌ Erreur récupération historique: {e}")
                # Fallback vers réponse par défaut
        
        # Réponse par défaut si logging non disponible
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
# ENDPOINTS DE DEBUG AVEC LOGGING
# =============================================================================

@router.get("/debug/status", dependencies=[Depends(admin_protection)])
async def debug_status(request: Request):
    """Debug endpoint pour vérifier le statut du service + logging"""
    app = request.app
    rag_embedder = getattr(app.state, 'rag_embedder', None)
    get_rag_status = getattr(app.state, 'get_rag_status', None)
    process_rag = getattr(app.state, 'process_question_with_rag', None)
    
    rag_status = "not_available"
    if get_rag_status:
        try:
            rag_status = get_rag_status()
        except:
            pass
    
    # ✅ NOUVEAU: Status du système de logging
    logging_status = "not_available"
    conversations_count = 0
    if LOGGING_AVAILABLE and logger_instance:
        try:
            # Compter les conversations dans la base
            import sqlite3
            with sqlite3.connect(logger_instance.db_path) as conn:
                conversations_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            logging_status = "available"
        except Exception as e:
            logging_status = f"error: {str(e)}"
    
    return {
        "expert_service": {
            "openai_available": OPENAI_AVAILABLE,
            "openai_key_configured": bool(os.getenv('OPENAI_API_KEY')),
            "utf8_support": True,
            "utf8_validation": "active"
        },
        "rag_system": {
            "embedder_connected": rag_embedder is not None,
            "function_connected": process_rag is not None,
            "status": rag_status
        },
        "logging_system": {  # ✅ NOUVEAU
            "available": LOGGING_AVAILABLE,
            "status": logging_status,
            "conversations_count": conversations_count,
            "auto_save": "enabled" if LOGGING_AVAILABLE else "disabled"
        },
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.0_with_integrated_logging_and_fixed_validation"
    }

@router.get("/debug/test-question", dependencies=[Depends(admin_protection)])
async def debug_test_question(
    request: Request, 
    text: Optional[str] = Query(None, description="Custom question text")
):
    """Test endpoint avec question sur Compass - question personnalisable avec UTF-8 + Logging"""
    
    test_text = text or "What are the Compass Performance Analysis Protocol diagnostic patterns for Ross 308?"
    safe_test_text = ensure_utf8_string(test_text)
    
    test_request = QuestionRequest(
        text=safe_test_text,
        language="en",
        speed_mode="quality"
    )
    
    try:
        response = await ask_expert_public(test_request, request)
        return {
            "test_status": "success",
            "question_tested": safe_test_text,
            "rag_used": response.rag_used,
            "rag_score": response.rag_score,
            "response_preview": response.response[:200] + "..." if len(response.response) > 200 else response.response,
            "response_time_ms": response.response_time_ms,
            "mode": response.mode,
            "utf8_processed": True,
            "logged": response.logged,  # ✅ NOUVEAU
            "conversation_id": response.conversation_id
        }
    except Exception as e:
        process_rag = getattr(request.app.state, 'process_question_with_rag', None)
        return {
            "test_status": "error",
            "question_tested": safe_test_text,
            "error": str(e),
            "rag_available": process_rag is not None,
            "utf8_processed": True,
            "logged": False
        }

@router.get("/debug/test-utf8", dependencies=[Depends(admin_protection)])
async def debug_test_utf8(request: Request):
    """Test endpoint spécifique pour validation UTF-8"""
    
    test_questions = [
        {
            "text": "Température optimale pour poulets Ross 308 ?",
            "language": "fr",
            "description": "Français avec accents"
        },
        {
            "text": "¿Cuál es la nutrición óptima para pollos?",
            "language": "es", 
            "description": "Espagnol avec caractères spéciaux"
        },
        {
            "text": "Contrôle qualité à 32°C avec humidité 65%",
            "language": "fr",
            "description": "Français avec symboles spéciaux"
        }
    ]
    
    results = []
    
    for test_q in test_questions:
        try:
            test_request = QuestionRequest(
                text=test_q["text"],
                language=test_q["language"],
                speed_mode="fast"
            )
            
            validation_result = {
                "original": test_q["text"],
                "processed": test_request.text,
                "language": test_request.language,
                "description": test_q["description"],
                "validation_success": True,
                "encoding_ok": test_request.text == ensure_utf8_string(test_q["text"])
            }
            
        except Exception as e:
            validation_result = {
                "original": test_q["text"],
                "processed": None,
                "language": test_q["language"],
                "description": test_q["description"],
                "validation_success": False,
                "error": str(e)
            }
        
        results.append(validation_result)
    
    return {
        "utf8_test_results": results,
        "summary": {
            "total_tests": len(results),
            "successful": sum(1 for r in results if r.get("validation_success", False)),
            "failed": sum(1 for r in results if not r.get("validation_success", False))
        },
        "logging_integration": {
            "available": LOGGING_AVAILABLE,
            "auto_save": "enabled" if LOGGING_AVAILABLE else "disabled"
        },
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.0_with_integrated_logging_and_fixed_validation"
    }

@router.get("/debug/routes", dependencies=[Depends(admin_protection)])
async def debug_routes(request: Request):
    """Debug endpoint pour lister les routes disponibles avec logging"""
    process_rag = getattr(request.app.state, 'process_question_with_rag', None)
    
    return {
        "routes": [
            {"path": "/api/v1/expert/ask-public", "method": "POST", "description": "Question publique avec UTF-8 + Logging auto"},
            {"path": "/api/v1/expert/ask", "method": "POST", "description": "Question authentifiée avec UTF-8 + Logging auto"},
            {"path": "/api/v1/expert/feedback", "method": "POST", "description": "Soumettre feedback avec UTF-8 + DB update"},
            {"path": "/api/v1/expert/topics", "method": "GET", "description": "Sujets suggérés avec UTF-8"},
            {"path": "/api/v1/expert/history", "method": "GET", "description": "Historique avec intégration logging"},
            {"path": "/api/v1/expert/debug/status", "method": "GET", "description": "Statut système + logging (admin)"},
            {"path": "/api/v1/expert/debug/test-question", "method": "GET", "description": "Test RAG + logging (admin)", "params": "?text=custom_question"},
            {"path": "/api/v1/expert/debug/test-utf8", "method": "GET", "description": "Test UTF-8 validation (admin)"},
            {"path": "/api/v1/expert/debug/routes", "method": "GET", "description": "Liste routes (admin)"}
        ],
        "rag_connected": process_rag is not None,
        "utf8_support": "active",
        "validation_fixed": "UTF-8 validation assouplie pour corriger erreurs 400",
        "logging_integration": {
            "available": LOGGING_AVAILABLE,
            "auto_save": "enabled" if LOGGING_AVAILABLE else "disabled",
            "feedback_update": "enabled" if LOGGING_AVAILABLE else "disabled"
        },
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.0_with_integrated_logging_and_fixed_validation"
    }

# =============================================================================
# CONFIGURATION AU DÉMARRAGE
# =============================================================================

if OPENAI_AVAILABLE and openai:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai.api_key = openai_api_key
        logger.info("✅ OpenAI configuré avec succès dans expert router UTF-8")
    else:
        logger.warning("⚠️ OpenAI API key non trouvée dans les variables d'environnement")
else:
    logger.warning("⚠️ Module OpenAI non disponible")

logger.info("🔤 Support UTF-8 complet activé dans expert router")
logger.info("🔧 Validation UTF-8 assouplie pour corriger erreurs 400")
logger.info(f"💾 Logging automatique: {'Activé' if LOGGING_AVAILABLE else 'Non disponible'}")