"""
app/api/v1/expert.py - VERSION COMPLÈTE AVEC SYSTÈME DE MÉMOIRE CONVERSATIONNELLE
NOUVEAU: Intégration système de mémoire conversationnelle pour continuité contextuelle
CORRECTIONS: Support conversation_id pour mémoire + validation/clarification avec contexte
CONSERVATION: Toutes les autres fonctionnalités existantes (auth, validation, clarification, RAG)
"""
import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ConfigDict

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# =============================================================================
# IMPORT VALIDATEUR AGRICOLE - PRIORITÉ ABSOLUE
# =============================================================================

try:
    from app.api.v1.agricultural_domain_validator import (
        validate_agricultural_question,
        get_agricultural_validator_stats,
        is_agricultural_validation_enabled
    )
    AGRICULTURAL_VALIDATOR_AVAILABLE = True
    logger.info("✅ [Expert] Validateur agricole importé avec succès")
    logger.info(f"✅ [Expert] Validation agricole: {'ACTIVE' if is_agricultural_validation_enabled() else 'INACTIVE'}")
except ImportError as e:
    AGRICULTURAL_VALIDATOR_AVAILABLE = False
    logger.error(f"❌ [Expert] ERREUR CRITIQUE - Validateur agricole non disponible: {e}")
    logger.error("❌ [Expert] Toutes les questions seront acceptées sans filtrage!")
except Exception as e:
    AGRICULTURAL_VALIDATOR_AVAILABLE = False
    logger.error(f"❌ [Expert] Erreur inattendue import validateur: {e}")

# =============================================================================
# IMPORT SYSTÈME DE CLARIFICATION - NOUVEAU
# =============================================================================

try:
    from app.api.v1.question_clarification_system import (
        analyze_question_for_clarification,
        format_clarification_response,
        is_clarification_system_enabled,
        get_clarification_system_stats
    )
    CLARIFICATION_SYSTEM_AVAILABLE = True
    logger.info("✅ [Expert] Système de clarification importé avec succès")
    logger.info(f"✅ [Expert] Clarification: {'ACTIVE' if is_clarification_system_enabled() else 'INACTIVE'}")
except ImportError as e:
    CLARIFICATION_SYSTEM_AVAILABLE = False
    logger.warning(f"⚠️ [Expert] Système de clarification non disponible: {e}")
except Exception as e:
    CLARIFICATION_SYSTEM_AVAILABLE = False
    logger.error(f"❌ [Expert] Erreur inattendue import clarification: {e}")

# =============================================================================
# IMPORT SYSTÈME DE MÉMOIRE CONVERSATIONNELLE - NOUVEAU
# =============================================================================

try:
    from app.api.v1.conversation_memory import (
        add_message_to_conversation,
        get_conversation_context,
        get_context_for_clarification,
        get_context_for_rag,
        get_conversation_memory_stats,
        cleanup_expired_conversations
    )
    CONVERSATION_MEMORY_AVAILABLE = True
    logger.info("✅ [Expert] Système de mémoire conversationnelle importé avec succès")
except ImportError as e:
    CONVERSATION_MEMORY_AVAILABLE = False
    logger.warning(f"⚠️ [Expert] Système de mémoire non disponible: {e}")
except Exception as e:
    CONVERSATION_MEMORY_AVAILABLE = False
    logger.error(f"❌ [Expert] Erreur inattendue import mémoire: {e}")

# =============================================================================
# IMPORT AUTH
# =============================================================================

logger.info("=" * 60)
logger.info("🔍 DIAGNOSTIC IMPORT AUTH.PY - MÉTHODES MULTIPLES")

AUTH_AVAILABLE = False
get_current_user = None

try:
    from .auth import get_current_user
    AUTH_AVAILABLE = True
    logger.info("✅ Méthode 1 réussie: Import direct relatif")
except ImportError as e:
    logger.error(f"❌ Méthode 1 échouée: {e}")
    try:
        from app.api.v1.auth import get_current_user
        AUTH_AVAILABLE = True
        logger.info("✅ Méthode 2 réussie: Import absolu")
    except ImportError as e2:
        logger.error(f"❌ Méthode 2 échouée: {e2}")

logger.info(f"🎯 AUTH_AVAILABLE final: {AUTH_AVAILABLE}")
logger.info("=" * 60)

# OpenAI import sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

# Configuration sécurité pour authentification
security = HTTPBearer()

# =============================================================================
# MODÈLES PYDANTIC - CORRIGÉS AVEC CONVERSATION_ID + USER_ID
# =============================================================================

class QuestionRequest(BaseModel):
    """Request model avec support conversation_id et user_id"""
    text: str = Field(..., min_length=1, max_length=5000, description="Question text")
    language: Optional[str] = Field("fr", description="Response language (fr, en, es)")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode (fast, balanced, quality)")
    
    # ✅ NOUVEAUX CHAMPS CRITIQUES
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID to continue existing conversation")
    user_id: Optional[str] = Field(None, description="User ID for conversation tracking")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        if self.language not in ['fr', 'en', 'es']:
            self.language = 'fr'
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
    mode: str = "expert_router_corrected"
    user: Optional[str] = None
    logged: bool = False
    validation_passed: Optional[bool] = None
    validation_confidence: Optional[float] = None

class FeedbackRequest(BaseModel):
    """Feedback model standard"""
    rating: str = Field(..., description="Rating: positive, negative, neutral")
    comment: Optional[str] = Field(None, description="Optional comment")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        if self.rating not in ['positive', 'negative', 'neutral']:
            self.rating = 'neutral'

# =============================================================================
# IMPORT LOGGING - CORRIGÉ
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

# =============================================================================
# FONCTION DE SAUVEGARDE CORRIGÉE
# =============================================================================

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
    """Sauvegarde automatique - COMPLÈTEMENT CORRIGÉE"""
    
    if not LOGGING_AVAILABLE or not logger_instance:
        logger.warning("⚠️ Logging non disponible pour sauvegarde")
        return False
    
    try:
        # Créer l'objet conversation
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
        
        # ✅ MÉTHODE 1: Essayer log_conversation
        try:
            if hasattr(logger_instance, 'log_conversation'):
                record_id = logger_instance.log_conversation(conversation)
                logger.info(f"✅ Conversation sauvegardée via log_conversation: {conversation_id}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ log_conversation échoué: {e}")
        
        # ✅ MÉTHODE 2: Essayer save_conversation
        try:
            if hasattr(logger_instance, 'save_conversation'):
                record_id = logger_instance.save_conversation(conversation)
                logger.info(f"✅ Conversation sauvegardée via save_conversation: {conversation_id}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ save_conversation échoué: {e}")
        
        # ✅ MÉTHODE 3: Sauvegarde directe SQL (fallback)
        logger.info("🔄 Tentative sauvegarde directe SQL...")
        
        import sqlite3
        from datetime import datetime
        
        with sqlite3.connect(logger_instance.db_path) as conn:
            record_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            conn.execute("""
                INSERT INTO conversations (
                    id, conversation_id, user_id, question, response, 
                    confidence_score, response_time_ms, language, rag_used, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id, conversation_id, str(user_id), str(question), str(response),
                rag_score, response_time_ms, language, rag_used, timestamp
            ))
            
            logger.info(f"✅ Conversation sauvegardée via SQL direct: {conversation_id}")
            return True
        
    except Exception as e:
        logger.error(f"❌ Toutes les méthodes de sauvegarde ont échoué: {e}")
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
# FONCTION DE VALIDATION AGRICOLE CENTRALISÉE AVEC MÉMOIRE
# =============================================================================

async def validate_question_agricultural_domain(
    question: str, 
    language: str, 
    user_id: str, 
    request_ip: str,
    conversation_id: str = None  # ✅ NOUVEAU PARAMÈTRE pour contexte
) -> tuple[bool, str, float]:
    """
    Valide qu'une question concerne le domaine agricole avec contexte conversationnel
    
    Returns:
        tuple[bool, str, float]: (is_valid, rejection_message_or_empty, confidence)
    """
    
    # Si le validateur n'est pas disponible, REJETER par sécurité
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        logger.error("❌ [Validation] Validateur agricole non disponible - REJET par sécurité")
        
        rejection_messages = {
            "fr": "Service temporairement indisponible. Veuillez réessayer plus tard.",
            "en": "Service temporarily unavailable. Please try again later.",
            "es": "Servicio temporalmente no disponible. Por favor, inténtelo más tarde."
        }
        
        return False, rejection_messages.get(language, rejection_messages["fr"]), 0.0
    
    # ✅ NOUVEAU: Enrichir la question avec le contexte de conversation
    enriched_question = question
    if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
        try:
            conversation_context = get_context_for_rag(conversation_id)
            if conversation_context:
                enriched_question = f"{question}\n\nContexte de conversation:\n{conversation_context}"
                logger.info(f"🧠 [Validation] Question enrichie avec contexte conversationnel")
        except Exception as e:
            logger.warning(f"⚠️ [Validation] Erreur enrichissement contexte: {e}")
    
    # Si la validation est désactivée, accepter
    if not is_agricultural_validation_enabled():
        logger.info("🔧 [Validation] Validation agricole désactivée - question acceptée")
        return True, "", 100.0
    
    try:
        # Utiliser le validateur avec la question enrichie
        validation_result = validate_agricultural_question(
            question=enriched_question,  # ✅ Question avec contexte
            language=language,
            user_id=user_id,
            request_ip=request_ip
        )
        
        logger.info(f"🔍 [Validation] Résultat: {validation_result.is_valid} (confiance: {validation_result.confidence:.1f}%)")
        
        if validation_result.is_valid:
            return True, "", validation_result.confidence
        else:
            return False, validation_result.reason or "Question hors domaine agricole", validation_result.confidence
    
    except Exception as e:
        logger.error(f"❌ [Validation] Erreur validateur: {e}")
        
        # En cas d'erreur du validateur, rejeter par sécurité
        rejection_messages = {
            "fr": "Erreur de validation. Veuillez reformuler votre question sur le domaine avicole.",
            "en": "Validation error. Please rephrase your question about the poultry domain.",
            "es": "Error de validación. Por favor, reformule su pregunta sobre el dominio avícola."
        }
        
        return False, rejection_messages.get(language, rejection_messages["fr"]), 0.0

# =============================================================================
# PROMPTS MULTI-LANGUES
# =============================================================================

EXPERT_PROMPTS = {
    "fr": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair. 
Réponds de manière précise et pratique en français. Tu peux utiliser tous les caractères français (é, è, à, ç, ù, etc.) et tous les symboles (°C, %, etc.) dans tes réponses.

IMPORTANT: Ne fais pas référence à une lignée génétique comme Ross ou Cobb, sauf si l'utilisateur la mentionne dans sa question. Donne une réponse générale qui s'applique à tous les poulets de chair.""",
    
    "en": """You are a veterinary expert specialized in animal health and nutrition, particularly for broiler chickens.
Answer precisely and practically in English, providing advice based on industry best practices.

IMPORTANT: Do not reference specific genetic lines like Ross or Cobb, unless the user mentions them in their question. Provide general answers that apply to all broiler chickens.""",
    
    "es": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde.
Responde de manera precisa y práctica en español. Puedes usar todos los caractéres especiales del español (ñ, ¿, ¡, acentos, etc.) en tus respuestas.

IMPORTANTE: No hagas referencia a líneas genéticas como Ross o Cobb, a menos que el usuario las mencione en su pregunta. Da respuestas generales que se apliquen a todos los pollos de engorde."""
}

def get_expert_prompt(language: str) -> str:
    """Get expert system prompt for language"""
    return EXPERT_PROMPTS.get(language.lower(), EXPERT_PROMPTS["fr"])

# =============================================================================
# FONCTIONS HELPER
# =============================================================================

def get_fallback_response(question: str, language: str = "fr") -> str:
    """Réponse de fallback - utilisée seulement si OpenAI échoue"""
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
# ENDPOINT PRINCIPAL AVEC VALIDATION AGRICOLE + CLARIFICATION + MÉMOIRE CONVERSATIONNELLE
# =============================================================================

@router.post("/ask", response_model=ExpertResponse)
async def ask_expert_secure(
    request_data: QuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user) if AUTH_AVAILABLE else None
):
    """Question avec authentification + validation agricole + clarification + MÉMOIRE CONVERSATIONNELLE"""
    start_time = time.time()
    
    try:
        logger.info("=" * 60)
        logger.info("🧠 DÉBUT ask_expert_secure avec MÉMOIRE CONVERSATIONNELLE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        logger.info(f"🆔 Conversation ID fourni: {request_data.conversation_id}")
        logger.info(f"👤 User ID fourni: {request_data.user_id}")
        logger.info(f"🌐 Langue: {request_data.language}")
        logger.info(f"⚡ Mode: {request_data.speed_mode}")
        
        # Vérification auth
        if not AUTH_AVAILABLE:
            logger.error("❌ AUTH_AVAILABLE = False")
            raise HTTPException(status_code=503, detail="Service d'authentification non disponible")
        
        if not current_user:
            logger.error("❌ current_user = None")
            raise HTTPException(status_code=503, detail="Service d'authentification non disponible")
        
        # L'utilisateur est authentifié
        user_id = current_user.get("user_id") or request_data.user_id
        user_email = current_user.get("email")
        request_ip = request.client.host if request.client else "unknown"
        
        logger.info(f"✅ Authentifié: {user_email} ({user_id[:8] if user_id else 'N/A'}...)")
        
        # Ajouter les infos utilisateur à la requête
        request.state.user = current_user
        
        # Récupération de la question avec validation
        question_text = request_data.text.strip()
        
        if not question_text:
            logger.error("❌ Question vide après nettoyage")
            raise HTTPException(status_code=400, detail="Question text is required")
        
        # ✅ CORRECTION CRITIQUE: Gestion du conversation_id
        if request_data.conversation_id and request_data.conversation_id.strip():
            # RÉUTILISER l'ID existant fourni par le client
            conversation_id = request_data.conversation_id.strip()
            logger.info(f"🔄 [conversation_id] CONTINUATION conversation: {conversation_id}")
        else:
            # CRÉER un nouveau conversation_id seulement si pas fourni
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 [conversation_id] NOUVELLE conversation: {conversation_id}")
        
        # ✅ NOUVEAU: Enregistrer le message utilisateur dans la mémoire conversationnelle
        if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
            try:
                conversation_context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id or "authenticated_user",
                    message=question_text,
                    role="user",
                    language=request_data.language
                )
                logger.info(f"🧠 [Memory] Message utilisateur enregistré dans conversation {conversation_id}")
                logger.info(f"🧠 [Memory] Entités connues: {conversation_context.extracted_entities}")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement message: {e}")
        
        # 🌾 === VALIDATION AGRICOLE OBLIGATOIRE AVEC CONTEXTE ===
        logger.info("🌾 [VALIDATION] Démarrage validation domaine agricole avec mémoire...")
        
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain(
            question=question_text,
            language=request_data.language,
            user_id=user_id or "authenticated_user",
            request_ip=request_ip,
            conversation_id=conversation_id  # ✅ NOUVEAU: Contexte conversationnel
        )
        
        if not is_valid:
            logger.warning(f"🚫 [VALIDATION] Question rejetée: {rejection_message}")
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # ✅ NOUVEAU: Enregistrer aussi la réponse de rejet dans la mémoire
            if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                try:
                    add_message_to_conversation(
                        conversation_id=conversation_id,
                        user_id=user_id or "authenticated_user",
                        message=rejection_message,
                        role="assistant",
                        language=request_data.language
                    )
                    logger.info(f"🧠 [Memory] Rejet enregistré dans conversation {conversation_id}")
                except Exception as e:
                    logger.warning(f"⚠️ [Memory] Erreur enregistrement rejet: {e}")
            
            await save_conversation_auto(
                conversation_id=conversation_id,
                question=question_text,
                response=rejection_message,
                user_id=user_id or "authenticated_user",
                language=request_data.language,
                rag_used=False,
                rag_score=None,
                response_time_ms=response_time_ms
            )
            
            response_obj = ExpertResponse(
                question=str(question_text),
                response=str(rejection_message),
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=request_data.language,
                response_time_ms=response_time_ms,
                mode="agricultural_validation_rejected_with_memory",
                user=user_email,
                logged=True,
                validation_passed=False,
                validation_confidence=validation_confidence
            )
            
            logger.info("🚫 [VALIDATION] Question rejetée et loggée avec mémoire")
            logger.info("=" * 60)
            return response_obj
        
        logger.info(f"✅ [VALIDATION] Question validée avec mémoire (confiance: {validation_confidence:.1f}%)")
        
        # ===🆕 SYSTÈME DE CLARIFICATION AVEC MÉMOIRE CONVERSATIONNELLE ===
        if CLARIFICATION_SYSTEM_AVAILABLE and is_clarification_system_enabled():
            logger.info("❓ [CLARIFICATION] Vérification avec contexte conversationnel...")
            
            # ✅ NOUVEAU: Récupérer le contexte conversationnel pour clarification
            conversation_context = {}
            if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                try:
                    conversation_context = get_context_for_clarification(conversation_id)
                    if conversation_context:
                        logger.info(f"🧠 [Clarification] Contexte trouvé: {conversation_context}")
                except Exception as e:
                    logger.warning(f"⚠️ [Clarification] Erreur récupération contexte: {e}")
            
            # ✅ NOUVEAU: Si le contexte contient déjà les infos principales, pas de clarification
            if conversation_context.get("breed") and conversation_context.get("age"):
                logger.info(f"🧠 [Clarification] Contexte conversationnel suffisant - pas de clarification")
                logger.info(f"🧠 [Clarification] Informations connues: {conversation_context}")
            else:
                # Analyse normale de clarification
                clarification_result = await analyze_question_for_clarification(
                    question=question_text,
                    language=request_data.language,
                    user_id=user_id or "authenticated_user",
                    conversation_id=conversation_id
                )
                
                if clarification_result.needs_clarification:
                    logger.info(f"❓ [CLARIFICATION] {len(clarification_result.questions)} questions générées")
                    
                    clarification_response = format_clarification_response(
                        questions=clarification_result.questions,
                        language=request_data.language,
                        original_question=question_text
                    )
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    # ✅ NOUVEAU: Enregistrer la demande de clarification dans la mémoire
                    if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                        try:
                            add_message_to_conversation(
                                conversation_id=conversation_id,
                                user_id=user_id or "authenticated_user",
                                message=clarification_response,
                                role="assistant",
                                language=request_data.language
                            )
                            logger.info(f"🧠 [Memory] Clarification enregistrée dans conversation {conversation_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ [Memory] Erreur enregistrement clarification: {e}")
                    
                    await save_conversation_auto(
                        conversation_id=conversation_id,
                        question=question_text,
                        response=clarification_response,
                        user_id=user_id or "authenticated_user",
                        language=request_data.language,
                        rag_used=False,
                        rag_score=None,
                        response_time_ms=response_time_ms
                    )
                    
                    response_obj = ExpertResponse(
                        question=str(question_text),
                        response=str(clarification_response),
                        conversation_id=conversation_id,
                        rag_used=False,
                        rag_score=None,
                        timestamp=datetime.now().isoformat(),
                        language=request_data.language,
                        response_time_ms=response_time_ms,
                        mode="clarification_needed_authenticated_with_memory",
                        user=user_email,
                        logged=True,
                        validation_passed=True,
                        validation_confidence=validation_confidence
                    )
                    
                    logger.info("❓ [CLARIFICATION] Demande envoyée et loggée avec mémoire")
                    logger.info("=" * 60)
                    return response_obj
                
                logger.info("✅ [CLARIFICATION] Question suffisamment claire avec contexte")
        # ===🆕 FIN CLARIFICATION AVEC MÉMOIRE ===
        
        # === TRAITEMENT NORMAL (RAG/OpenAI) AVEC CONTEXTE CONVERSATIONNEL ===
        user = getattr(request.state, "user", None)
        
        # Variables par défaut
        rag_used = False
        rag_score = None
        answer = ""
        mode = "authenticated_direct_openai_with_memory"
        
        # Essayer RAG d'abord avec contexte conversationnel
        app = request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG avec contexte conversationnel...")
                
                # ✅ NOUVEAU: Obtenir le contexte pour RAG
                rag_context = ""
                if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                    try:
                        rag_context = get_context_for_rag(conversation_id)
                        if rag_context:
                            logger.info(f"🧠 [RAG] Contexte conversationnel ajouté: {len(rag_context)} caractères")
                    except Exception as e:
                        logger.warning(f"⚠️ [RAG] Erreur contexte conversationnel: {e}")
                
                # Appel RAG avec possibilité de contexte supplémentaire
                try:
                    result = await process_rag(
                        question=question_text,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id,
                        context=rag_context  # ✅ NOUVEAU: Contexte conversationnel pour RAG
                    )
                except TypeError:
                    # Si process_rag ne supporte pas le paramètre context, l'ignorer
                    result = await process_rag(
                        question=question_text,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id
                    )
                
                answer = str(result.get("response", ""))
                rag_used = result.get("mode", "").startswith("rag")
                rag_score = result.get("score")
                mode = f"authenticated_{result.get('mode', 'rag_enhanced')}_with_memory"
                
                logger.info(f"✅ RAG traité avec mémoire - Mode: {mode}, Score: {rag_score}")
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG avec mémoire: {rag_error}")
                answer = await process_question_openai(
                    question_text, 
                    request_data.language,
                    request_data.speed_mode
                )
                mode = "authenticated_fallback_openai_with_memory"
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI direct avec mémoire")
            answer = await process_question_openai(
                question_text,
                request_data.language,
                request_data.speed_mode
            )
            mode = "authenticated_direct_openai_with_memory"
        
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"⏱️ Temps de traitement: {response_time_ms}ms")
        
        # ✅ NOUVEAU: Enregistrer la réponse dans la mémoire conversationnelle
        if CONVERSATION_MEMORY_AVAILABLE and conversation_id and answer:
            try:
                add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id or "authenticated_user",
                    message=answer,
                    role="assistant",
                    language=request_data.language
                )
                logger.info(f"🧠 [Memory] Réponse enregistrée dans conversation {conversation_id}")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement réponse: {e}")
        
        # Sauvegarde automatique avec le conversation_id approprié
        logged = await save_conversation_auto(
            conversation_id=conversation_id,
            question=question_text,
            response=answer,
            user_id=user_id or "authenticated_user",
            language=request_data.language,
            rag_used=rag_used,
            rag_score=rag_score,
            response_time_ms=response_time_ms
        )
        
        logger.info(f"💾 Sauvegarde: {'✅ Réussie' if logged else '❌ Échouée'}")
        
        # ✅ MODIFIÉ: Mode enrichi avec information mémoire
        mode_with_memory = f"{mode}_memory_{'enabled' if CONVERSATION_MEMORY_AVAILABLE else 'disabled'}"
        
        # Retourner la réponse avec le MÊME conversation_id
        response_obj = ExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,  # ✅ MÊME ID que reçu ou nouveau
            rag_used=rag_used,
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=request_data.language,
            response_time_ms=response_time_ms,
            mode=mode_with_memory,  # ✅ MODIFIÉ avec info mémoire
            user=user_email,
            logged=logged,
            validation_passed=True,
            validation_confidence=validation_confidence
        )
        
        logger.info(f"✅ FIN ask_expert_secure avec MÉMOIRE - conversation_id retourné: {conversation_id}")
        logger.info("=" * 60)
        
        return response_obj
    
    except HTTPException:
        logger.info("=" * 60)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask expert sécurisé avec mémoire: {e}")
        import traceback
        logger.error(f"❌ Traceback complet: {traceback.format_exc()}")
        logger.info("=" * 60)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# ENDPOINT PUBLIC AVEC VALIDATION AGRICOLE + CLARIFICATION + MÉMOIRE CONVERSATIONNELLE
# =============================================================================

@router.post("/ask-public", response_model=ExpertResponse)
async def ask_expert_public(
    request_data: QuestionRequest,
    request: Request
):
    """Question publique avec validation agricole + clarification + MÉMOIRE CONVERSATIONNELLE"""
    start_time = time.time()
    
    try:
        logger.info("=" * 60)
        logger.info("🧠 DÉBUT ask_expert_public avec MÉMOIRE CONVERSATIONNELLE")
        logger.info(f"📝 Question reçue: {request_data.text[:100]}...")
        logger.info(f"🆔 Conversation ID fourni: {request_data.conversation_id}")
        logger.info(f"👤 User ID fourni: {request_data.user_id}")
        logger.info(f"🌐 Langue: {request_data.language}")
        
        # Validation de la question
        question_text = request_data.text.strip()
        
        if not question_text:
            logger.error("❌ Question vide après nettoyage")
            raise HTTPException(status_code=400, detail="Question text is required")
        
        # ✅ CORRECTION CRITIQUE: Gestion du conversation_id
        if request_data.conversation_id and request_data.conversation_id.strip():
            # RÉUTILISER l'ID existant fourni par le client
            conversation_id = request_data.conversation_id.strip()
            logger.info(f"🔄 [conversation_id] CONTINUATION conversation publique: {conversation_id}")
        else:
            # CRÉER un nouveau conversation_id seulement si pas fourni
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 [conversation_id] NOUVELLE conversation publique: {conversation_id}")
        
        # User ID depuis requête ou généré
        user_id = request_data.user_id or get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        
        logger.info(f"👤 User ID: {user_id}")
        
        # ✅ NOUVEAU: Enregistrer le message utilisateur dans la mémoire conversationnelle
        if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
            try:
                conversation_context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=request_data.language
                )
                logger.info(f"🧠 [Memory] Message public enregistré dans conversation {conversation_id}")
                logger.info(f"🧠 [Memory] Entités connues: {conversation_context.extracted_entities}")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement message public: {e}")
        
        # 🌾 === VALIDATION AGRICOLE OBLIGATOIRE AVEC CONTEXTE ===
        logger.info("🌾 [VALIDATION] Démarrage validation domaine agricole avec mémoire...")
        
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain(
            question=question_text,
            language=request_data.language,
            user_id=user_id,
            request_ip=request_ip,
            conversation_id=conversation_id  # ✅ NOUVEAU: Contexte conversationnel
        )
        
        if not is_valid:
            logger.warning(f"🚫 [VALIDATION] Question publique rejetée: {rejection_message}")
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # ✅ NOUVEAU: Enregistrer aussi la réponse de rejet dans la mémoire
            if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                try:
                    add_message_to_conversation(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        message=rejection_message,
                        role="assistant",
                        language=request_data.language
                    )
                    logger.info(f"🧠 [Memory] Rejet public enregistré dans conversation {conversation_id}")
                except Exception as e:
                    logger.warning(f"⚠️ [Memory] Erreur enregistrement rejet public: {e}")
            
            await save_conversation_auto(
                conversation_id=conversation_id,
                question=question_text,
                response=rejection_message,
                user_id=user_id,
                language=request_data.language,
                rag_used=False,
                rag_score=None,
                response_time_ms=response_time_ms
            )
            
            response_obj = ExpertResponse(
                question=str(question_text),
                response=str(rejection_message),
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=request_data.language,
                response_time_ms=response_time_ms,
                mode="public_agricultural_validation_rejected_with_memory",
                user=None,
                logged=True,
                validation_passed=False,
                validation_confidence=validation_confidence
            )
            
            logger.info("🚫 [VALIDATION] Question publique rejetée et loggée avec mémoire")
            logger.info("=" * 60)
            return response_obj
        
        logger.info(f"✅ [VALIDATION] Question publique validée avec mémoire (confiance: {validation_confidence:.1f}%)")
        
        # ===🆕 SYSTÈME DE CLARIFICATION AVEC MÉMOIRE CONVERSATIONNELLE ===
        if CLARIFICATION_SYSTEM_AVAILABLE and is_clarification_system_enabled():
            logger.info("❓ [CLARIFICATION] Vérification avec contexte conversationnel...")
            
            # ✅ NOUVEAU: Récupérer le contexte conversationnel pour clarification
            conversation_context = {}
            if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                try:
                    conversation_context = get_context_for_clarification(conversation_id)
                    if conversation_context:
                        logger.info(f"🧠 [Clarification] Contexte public trouvé: {conversation_context}")
                except Exception as e:
                    logger.warning(f"⚠️ [Clarification] Erreur récupération contexte public: {e}")
            
            # ✅ NOUVEAU: Si le contexte contient déjà les infos principales, pas de clarification
            if conversation_context.get("breed") and conversation_context.get("age"):
                logger.info(f"🧠 [Clarification] Contexte conversationnel public suffisant - pas de clarification")
                logger.info(f"🧠 [Clarification] Informations connues: {conversation_context}")
            else:
                # Analyse normale de clarification
                clarification_result = await analyze_question_for_clarification(
                    question=question_text,
                    language=request_data.language,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                
                if clarification_result.needs_clarification:
                    logger.info(f"❓ [CLARIFICATION] {len(clarification_result.questions)} questions générées")
                    
                    clarification_response = format_clarification_response(
                        questions=clarification_result.questions,
                        language=request_data.language,
                        original_question=question_text
                    )
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    # ✅ NOUVEAU: Enregistrer la demande de clarification dans la mémoire
                    if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                        try:
                            add_message_to_conversation(
                                conversation_id=conversation_id,
                                user_id=user_id,
                                message=clarification_response,
                                role="assistant",
                                language=request_data.language
                            )
                            logger.info(f"🧠 [Memory] Clarification publique enregistrée dans conversation {conversation_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ [Memory] Erreur enregistrement clarification publique: {e}")
                    
                    await save_conversation_auto(
                        conversation_id=conversation_id,
                        question=question_text,
                        response=clarification_response,
                        user_id=user_id,
                        language=request_data.language,
                        rag_used=False,
                        rag_score=None,
                        response_time_ms=response_time_ms
                    )
                    
                    response_obj = ExpertResponse(
                        question=str(question_text),
                        response=str(clarification_response),
                        conversation_id=conversation_id,
                        rag_used=False,
                        rag_score=None,
                        timestamp=datetime.now().isoformat(),
                        language=request_data.language,
                        response_time_ms=response_time_ms,
                        mode="clarification_needed_public_with_memory",
                        user=None,
                        logged=True,
                        validation_passed=True,
                        validation_confidence=validation_confidence
                    )
                    
                    logger.info("❓ [CLARIFICATION] Demande publique envoyée et loggée avec mémoire")
                    logger.info("=" * 60)
                    return response_obj
                
                logger.info("✅ [CLARIFICATION] Question publique suffisamment claire avec contexte")
        # ===🆕 FIN CLARIFICATION AVEC MÉMOIRE ===
        
        # === TRAITEMENT NORMAL (RAG/OpenAI) AVEC CONTEXTE CONVERSATIONNEL ===
        user = getattr(request.state, "user", None)
        
        # Variables par défaut
        rag_used = False
        rag_score = None
        answer = ""
        mode = "direct_openai_with_memory"
        
        # Essayer RAG d'abord avec contexte conversationnel
        app = request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG public avec contexte conversationnel...")
                
                # ✅ NOUVEAU: Obtenir le contexte pour RAG
                rag_context = ""
                if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
                    try:
                        rag_context = get_context_for_rag(conversation_id)
                        if rag_context:
                            logger.info(f"🧠 [RAG] Contexte conversationnel public ajouté: {len(rag_context)} caractères")
                    except Exception as e:
                        logger.warning(f"⚠️ [RAG] Erreur contexte conversationnel public: {e}")
                
                # Appel RAG avec possibilité de contexte supplémentaire
                try:
                    result = await process_rag(
                        question=question_text,
                        user=user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id,
                        context=rag_context  # ✅ NOUVEAU: Contexte conversationnel pour RAG
                    )
                except TypeError:
                    # Si process_rag ne supporte pas le paramètre context, l'ignorer
                    result = await process_rag(
                        question=question_text,
                        user=user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id
                    )
                
                answer = str(result.get("response", ""))
                rag_used = result.get("mode", "").startswith("rag")
                rag_score = result.get("score")
                mode = f"{result.get('mode', 'rag_enhanced')}_with_memory"
                
                logger.info(f"✅ RAG public traité avec mémoire - Mode: {mode}, Score: {rag_score}")
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG public avec mémoire: {rag_error}")
                answer = await process_question_openai(
                    question_text, 
                    request_data.language,
                    request_data.speed_mode
                )
                mode = "fallback_openai_with_memory"
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI public avec mémoire")
            answer = await process_question_openai(
                question_text,
                request_data.language,
                request_data.speed_mode
            )
            mode = "direct_openai_with_memory"
        
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"⏱️ Temps de traitement: {response_time_ms}ms")
        
        # ✅ NOUVEAU: Enregistrer la réponse dans la mémoire conversationnelle
        if CONVERSATION_MEMORY_AVAILABLE and conversation_id and answer:
            try:
                add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=answer,
                    role="assistant",
                    language=request_data.language
                )
                logger.info(f"🧠 [Memory] Réponse publique enregistrée dans conversation {conversation_id}")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement réponse publique: {e}")
        
        # Sauvegarde automatique
        logged = await save_conversation_auto(
            conversation_id=conversation_id,
            question=question_text,
            response=answer,
            user_id=user_id,
            language=request_data.language,
            rag_used=rag_used,
            rag_score=rag_score,
            response_time_ms=response_time_ms
        )
        
        logger.info(f"💾 Sauvegarde: {'✅ Réussie' if logged else '❌ Échouée'}")
        
        # ✅ MODIFIÉ: Mode enrichi avec information mémoire
        mode_with_memory = f"{mode}_memory_{'enabled' if CONVERSATION_MEMORY_AVAILABLE else 'disabled'}"
        
        # Retourner la réponse
        response_obj = ExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,  # ✅ MÊME ID que reçu ou nouveau
            rag_used=rag_used,
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=request_data.language,
            response_time_ms=response_time_ms,
            mode=mode_with_memory,  # ✅ MODIFIÉ avec info mémoire
            user=str(user) if user else None,
            logged=logged,
            validation_passed=True,
            validation_confidence=validation_confidence
        )
        
        logger.info(f"✅ FIN ask_expert_public avec MÉMOIRE - conversation_id retourné: {conversation_id}")
        logger.info("=" * 60)
        
        return response_obj
    
    except HTTPException:
        logger.info("=" * 60)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask expert public avec mémoire: {e}")
        import traceback
        logger.error(f"❌ Traceback complet: {traceback.format_exc()}")
        logger.info("=" * 60)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# ENDPOINT FEEDBACK - COMPLÈTEMENT CORRIGÉ
# =============================================================================

@router.post("/feedback")
async def submit_feedback(feedback_data: FeedbackRequest):
    """Submit feedback - COMPLÈTEMENT CORRIGÉ"""
    try:
        logger.info(f"📊 Feedback reçu: {feedback_data.rating}")
        logger.info(f"📊 Conversation ID: {feedback_data.conversation_id}")
        logger.info(f"📊 Commentaire: {feedback_data.comment}")
        
        feedback_updated = False
        
        if feedback_data.conversation_id and LOGGING_AVAILABLE and logger_instance:
            try:
                # Convertir le rating en format numérique
                rating_numeric = {
                    "positive": 1,
                    "negative": -1,
                    "neutral": 0
                }.get(feedback_data.rating, 0)
                
                logger.info(f"📊 Rating numérique: {rating_numeric}")
                
                # ✅ MÉTHODE 1: Essayer update_feedback si disponible
                try:
                    if hasattr(logger_instance, 'update_feedback'):
                        feedback_updated = logger_instance.update_feedback(
                            feedback_data.conversation_id, 
                            rating_numeric
                        )
                        logger.info(f"✅ Feedback mis à jour via update_feedback: {feedback_updated}")
                    else:
                        logger.warning("⚠️ Méthode update_feedback non disponible")
                        feedback_updated = False
                except Exception as e:
                    logger.warning(f"⚠️ update_feedback échoué: {e}")
                    feedback_updated = False
                
                # ✅ MÉTHODE 2: SQL direct si update_feedback échoue
                if not feedback_updated:
                    logger.info("🔄 Tentative mise à jour feedback via SQL direct...")
                    
                    import sqlite3
                    with sqlite3.connect(logger_instance.db_path) as conn:
                        cursor = conn.execute("""
                            UPDATE conversations 
                            SET feedback = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE conversation_id = ?
                        """, (rating_numeric, feedback_data.conversation_id))
                        
                        feedback_updated = cursor.rowcount > 0
                        
                        if feedback_updated:
                            logger.info(f"✅ Feedback mis à jour via SQL direct: {feedback_data.conversation_id}")
                        else:
                            logger.warning(f"⚠️ Conversation non trouvée: {feedback_data.conversation_id}")
                
            except Exception as e:
                logger.error(f"❌ Erreur mise à jour feedback: {e}")
                feedback_updated = False
        else:
            if not feedback_data.conversation_id:
                logger.warning("⚠️ Conversation ID manquant")
            if not LOGGING_AVAILABLE:
                logger.warning("⚠️ Logging non disponible")
            if not logger_instance:
                logger.warning("⚠️ Logger instance non disponible")
        
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
        logger.error(f"❌ Erreur feedback critique: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement feedback: {str(e)}")

# =============================================================================
# AUTRES ENDPOINTS (conservés identiques)
# =============================================================================

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
            "validation_enabled": is_agricultural_validation_enabled() if AGRICULTURAL_VALIDATOR_AVAILABLE else False,
            "clarification_enabled": is_clarification_system_enabled() if CLARIFICATION_SYSTEM_AVAILABLE else False,
            "memory_enabled": CONVERSATION_MEMORY_AVAILABLE,  # ✅ NOUVEAU
            "note": "Topics génériques pour tous poulets de chair"
        }
    except Exception as e:
        logger.error(f"❌ Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

# =============================================================================
# NOUVEAUX ENDPOINTS MÉMOIRE CONVERSATIONNELLE
# =============================================================================

@router.get("/conversation/{conversation_id}/context")
async def get_conversation_context_endpoint(conversation_id: str):
    """Récupère le contexte d'une conversation"""
    try:
        if not CONVERSATION_MEMORY_AVAILABLE:
            raise HTTPException(status_code=503, detail="Service de mémoire non disponible")
        
        context = get_conversation_context(conversation_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
        
        return {
            "conversation_id": conversation_id,
            "context": context.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur récupération contexte: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.get("/memory/stats")
async def get_memory_stats():
    """Statistiques du système de mémoire conversationnelle"""
    try:
        if not CONVERSATION_MEMORY_AVAILABLE:
            return {
                "memory_available": False,
                "message": "Système de mémoire non disponible"
            }
        
        stats = get_conversation_memory_stats()
        
        return {
            "memory_available": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur stats mémoire: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur stats: {str(e)}")

@router.post("/memory/cleanup")
async def cleanup_expired_conversations_endpoint():
    """Nettoie les conversations expirées"""
    try:
        if not CONVERSATION_MEMORY_AVAILABLE:
            raise HTTPException(status_code=503, detail="Service de mémoire non disponible")
        
        cleanup_expired_conversations()
        
        return {
            "success": True,
            "message": "Nettoyage des conversations expirées effectué",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage mémoire: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur nettoyage: {str(e)}")

@router.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = Query(10, ge=1, le=50)):
    """Récupère l'historique d'une conversation"""
    try:
        if not CONVERSATION_MEMORY_AVAILABLE:
            raise HTTPException(status_code=503, detail="Service de mémoire non disponible")
        
        context = get_conversation_context(conversation_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
        
        # Limiter les messages retournés
        messages = context.messages[-limit:] if context.messages else []
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "message_count": len(messages),
            "total_messages": len(context.messages),
            "extracted_entities": context.extracted_entities,
            "language": context.language,
            "last_activity": context.last_activity.isoformat(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur historique conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# NOUVEAUX ENDPOINTS DE DIAGNOSTIC ET CLARIFICATION
# =============================================================================

@router.get("/validation-stats")
async def get_validation_stats():
    """Statistiques du validateur agricole"""
    try:
        if not AGRICULTURAL_VALIDATOR_AVAILABLE:
            return {
                "error": "Validateur agricole non disponible",
                "available": False,
                "stats": None
            }
        
        stats = get_agricultural_validator_stats()
        
        return {
            "available": True,
            "validation_enabled": is_agricultural_validation_enabled(),
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur stats validation: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération stats")

@router.post("/test-clarification")
async def test_clarification_system(
    request_data: QuestionRequest,
    request: Request
):
    """Endpoint de test pour le système de clarification"""
    try:
        question_text = request_data.text.strip()
        user_id = get_user_id_from_request(request)
        conversation_id = request_data.conversation_id or str(uuid.uuid4())
        
        if not CLARIFICATION_SYSTEM_AVAILABLE:
            return {
                "system_available": False,
                "message": "Système de clarification non disponible",
                "question": question_text,
                "timestamp": datetime.now().isoformat()
            }
        
        if not is_clarification_system_enabled():
            return {
                "system_available": True,
                "system_enabled": False,
                "message": "Système de clarification désactivé",
                "question": question_text,
                "timestamp": datetime.now().isoformat()
            }
        
        # Test de clarification
        clarification_result = await analyze_question_for_clarification(
            question=question_text,
            language=request_data.language,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        if clarification_result.needs_clarification:
            formatted_response = format_clarification_response(
                questions=clarification_result.questions,
                language=request_data.language,
                original_question=question_text
            )
            
            return {
                "system_available": True,
                "system_enabled": True,
                "needs_clarification": True,
                "question": question_text,
                "language": request_data.language,
                "clarification_questions": clarification_result.questions,
                "formatted_response": formatted_response,
                "confidence_score": clarification_result.confidence_score,
                "processing_time_ms": clarification_result.processing_time_ms,
                "model_used": clarification_result.model_used,
                "system_stats": get_clarification_system_stats(),
                "memory_context": get_context_for_clarification(conversation_id) if CONVERSATION_MEMORY_AVAILABLE and conversation_id else None,  # ✅ NOUVEAU
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "system_available": True,
                "system_enabled": True,
                "needs_clarification": False,
                "question": question_text,
                "language": request_data.language,
                "reason": clarification_result.reason,
                "processing_time_ms": clarification_result.processing_time_ms,
                "system_stats": get_clarification_system_stats(),
                "memory_context": get_context_for_clarification(conversation_id) if CONVERSATION_MEMORY_AVAILABLE and conversation_id else None,  # ✅ NOUVEAU
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"❌ [Clarification] Erreur test: {e}")
        return {
            "system_available": CLARIFICATION_SYSTEM_AVAILABLE,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/clarification-status")
async def get_clarification_status():
    """Retourne le statut du système de clarification"""
    if not CLARIFICATION_SYSTEM_AVAILABLE:
        return {
            "system_available": False,
            "message": "Module de clarification non importé",
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "system_available": True,
        "clarification_system": get_clarification_system_stats(),
        "configuration_source": "environment_variables_and_settings",
        "can_be_disabled": True,
        "disable_instruction": "Set ENABLE_CLARIFICATION_SYSTEM=false in .env",
        "timestamp": datetime.now().isoformat()
    }

@router.post("/test-validation")
async def test_validation(
    request_data: QuestionRequest,
    request: Request
):
    """Test endpoint pour tester la validation sans traitement"""
    try:
        question_text = request_data.text.strip()
        user_id = get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        conversation_id = request_data.conversation_id or str(uuid.uuid4())  # ✅ NOUVEAU
        
        if not AGRICULTURAL_VALIDATOR_AVAILABLE:
            return {
                "error": "Validateur agricole non disponible",
                "available": False
            }
        
        # Test de validation avec contexte conversationnel
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain(
            question=question_text,
            language=request_data.language,
            user_id=user_id,
            request_ip=request_ip,
            conversation_id=conversation_id  # ✅ NOUVEAU
        )
        
        return {
            "question": question_text,
            "language": request_data.language,
            "validation_passed": is_valid,
            "confidence": validation_confidence,
            "rejection_message": rejection_message if not is_valid else None,
            "validator_available": True,
            "validation_enabled": is_agricultural_validation_enabled(),
            "conversation_id": conversation_id,
            "memory_context": get_context_for_clarification(conversation_id) if CONVERSATION_MEMORY_AVAILABLE and conversation_id else None,  # ✅ NOUVEAU
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur test validation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur test validation: {str(e)}")

# =============================================================================
# ENDPOINTS DEBUG (conservés identiques)
# =============================================================================

@router.get("/debug-database")
async def debug_database_info():
    """Debug des informations de base de données - CORRIGÉ"""
    try:
        if not LOGGING_AVAILABLE or not logger_instance:
            return {
                "error": "Logging non disponible",
                "logging_available": LOGGING_AVAILABLE,
                "logger_instance": bool(logger_instance)
            }
        
        import sqlite3
        
        # Vérifier la structure de la base
        with sqlite3.connect(logger_instance.db_path) as conn:
            # Lister les tables
            tables = conn.execute("""
                SELECT name FROM sqlite_master WHERE type='table'
            """).fetchall()
            
            # Structure de la table conversations
            schema = []
            count = 0
            recent = []
            
            if tables:
                try:
                    schema = conn.execute("PRAGMA table_info(conversations)").fetchall()
                    count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
                    recent = conn.execute("""
                        SELECT conversation_id, user_id, feedback, timestamp 
                        FROM conversations 
                        ORDER BY timestamp DESC 
                        LIMIT 5
                    """).fetchall()
                except Exception as e:
                    logger.warning(f"⚠️ Erreur requêtes base: {e}")
        
        # Méthodes disponibles
        logger_methods = [method for method in dir(logger_instance) if not method.startswith('_')]
        
        return {
            "logging_available": LOGGING_AVAILABLE,
            "database_path": logger_instance.db_path,
            "tables": [table[0] for table in tables],
            "conversations_schema": [{"name": col[1], "type": col[2]} for col in schema],
            "conversations_count": count,
            "recent_conversations": [
                {
                    "conversation_id": row[0],
                    "user_id": row[1],
                    "feedback": row[2],
                    "timestamp": row[3]
                } for row in recent
            ],
            "logger_methods": logger_methods,
            "has_save_conversation": hasattr(logger_instance, 'save_conversation'),
            "has_log_conversation": hasattr(logger_instance, 'log_conversation'),
            "has_update_feedback": hasattr(logger_instance, 'update_feedback'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur debug database: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/debug-system")
async def debug_system_info():
    """Endpoint de diagnostic système complet avec validateur, clarification et MÉMOIRE"""
    import os
    import sys
    
    # Tests d'import détaillés
    import_tests = {}
    
    try:
        import app
        import_tests["app"] = "✅ OK"
    except Exception as e:
        import_tests["app"] = f"❌ {str(e)}"
    
    try:
        import app.api.v1.auth
        import_tests["app.api.v1.auth"] = "✅ OK"
        auth_attrs = dir(app.api.v1.auth)
        auth_functions = [attr for attr in auth_attrs if not attr.startswith('_') and callable(getattr(app.api.v1.auth, attr, None))]
        import_tests["app.api.v1.auth.functions"] = auth_functions
    except Exception as e:
        import_tests["app.api.v1.auth"] = f"❌ {str(e)}"
    
    # Test spécifique du validateur agricole
    try:
        import app.api.v1.agricultural_domain_validator
        import_tests["agricultural_validator_module"] = "✅ OK"
        
        validator_attrs = dir(app.api.v1.agricultural_domain_validator)
        validator_functions = [attr for attr in validator_attrs if not attr.startswith('_')]
        import_tests["agricultural_validator_functions"] = validator_functions
        
    except Exception as e:
        import_tests["agricultural_validator_module"] = f"❌ {str(e)}"
    
    # Test spécifique du système de clarification
    try:
        import app.api.v1.question_clarification_system
        import_tests["clarification_system_module"] = "✅ OK"
        
        clarification_attrs = dir(app.api.v1.question_clarification_system)
        clarification_functions = [attr for attr in clarification_attrs if not attr.startswith('_')]
        import_tests["clarification_system_functions"] = clarification_functions
        
    except Exception as e:
        import_tests["clarification_system_module"] = f"❌ {str(e)}"
    
    # ✅ NOUVEAU: Test spécifique du système de mémoire conversationnelle
    try:
        import app.api.v1.conversation_memory
        import_tests["conversation_memory_module"] = "✅ OK"
        
        memory_attrs = dir(app.api.v1.conversation_memory)
        memory_functions = [attr for attr in memory_attrs if not attr.startswith('_')]
        import_tests["conversation_memory_functions"] = memory_functions
        
    except Exception as e:
        import_tests["conversation_memory_module"] = f"❌ {str(e)}"
    
    return {
        "auth_available": AUTH_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "validation_enabled": is_agricultural_validation_enabled() if AGRICULTURAL_VALIDATOR_AVAILABLE else None,
        "clarification_system_available": CLARIFICATION_SYSTEM_AVAILABLE,
        "clarification_enabled": is_clarification_system_enabled() if CLARIFICATION_SYSTEM_AVAILABLE else None,
        "conversation_memory_available": CONVERSATION_MEMORY_AVAILABLE,  # ✅ NOUVEAU
        "openai_available": OPENAI_AVAILABLE,
        "logging_available": LOGGING_AVAILABLE,
        "conversation_id_support": "✅ Activé dans cette version",
        "user_id_support": "✅ Activé dans cette version",
        "memory_conversational_support": "✅ Activé avec continuité contextuelle",  # ✅ NOUVEAU
        "current_directory": os.path.dirname(__file__),
        "python_path_sample": sys.path[:3],
        "import_tests": import_tests,
        "validator_stats": get_agricultural_validator_stats() if AGRICULTURAL_VALIDATOR_AVAILABLE else None,
        "clarification_stats": get_clarification_system_stats() if CLARIFICATION_SYSTEM_AVAILABLE else None,
        "memory_stats": get_conversation_memory_stats() if CONVERSATION_MEMORY_AVAILABLE else None,  # ✅ NOUVEAU
        "timestamp": datetime.now().isoformat()
    }

@router.get("/debug-auth")
async def debug_auth_info(request: Request):
    """Endpoint de diagnostic rapide avec validation, clarification et MÉMOIRE"""
    auth_header = request.headers.get("Authorization")
    
    return {
        "auth_available": AUTH_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "validation_enabled": is_agricultural_validation_enabled() if AGRICULTURAL_VALIDATOR_AVAILABLE else None,
        "clarification_system_available": CLARIFICATION_SYSTEM_AVAILABLE,
        "clarification_enabled": is_clarification_system_enabled() if CLARIFICATION_SYSTEM_AVAILABLE else None,
        "conversation_memory_available": CONVERSATION_MEMORY_AVAILABLE,  # ✅ NOUVEAU
        "auth_header_present": bool(auth_header),
        "auth_header_preview": auth_header[:50] + "..." if auth_header else None,
        "openai_available": OPENAI_AVAILABLE,
        "logging_available": LOGGING_AVAILABLE,
        "conversation_id_support": "✅ Activé",
        "user_id_support": "✅ Activé",
        "conversational_memory_support": "✅ Activé avec continuité contextuelle",  # ✅ NOUVEAU
        "timestamp": datetime.now().isoformat()
    }

@router.post("/test-utf8")
async def test_utf8_direct(request: Request):
    """Test endpoint pour UTF-8 direct avec validation, clarification et MÉMOIRE"""
    try:
        # Récupérer le body brut
        body = await request.body()
        body_str = body.decode('utf-8')
        
        logger.info(f"📝 Body brut reçu: {body_str}")
        
        # Parser JSON manuellement
        import json
        data = json.loads(body_str)
        
        question_text = data.get('text', '')
        language = data.get('language', 'fr')
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))  # ✅ NOUVEAU
        
        logger.info(f"📝 Question extraite: {question_text}")
        logger.info(f"🔤 Caractères spéciaux: {[c for c in question_text if ord(c) > 127]}")
        logger.info(f"🆔 Conversation ID: {conversation_id}")
        
        # Test de validation
        user_id = get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        
        # ✅ NOUVEAU: Enregistrer le message dans la mémoire
        if CONVERSATION_MEMORY_AVAILABLE and conversation_id:
            try:
                conversation_context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=language
                )
                logger.info(f"🧠 [Memory] Message test UTF-8 enregistré: {conversation_context.extracted_entities}")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur test UTF-8: {e}")
        
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain(
            question=question_text,
            language=language,
            user_id=user_id,
            request_ip=request_ip,
            conversation_id=conversation_id  # ✅ NOUVEAU: Avec contexte
        )
        
        if not is_valid:
            return {
                "success": False,
                "question_received": question_text,
                "special_chars_detected": [c for c in question_text if ord(c) > 127],
                "validation_passed": False,
                "rejection_message": rejection_message,
                "confidence": validation_confidence,
                "conversation_id": conversation_id,
                "memory_context": get_context_for_clarification(conversation_id) if CONVERSATION_MEMORY_AVAILABLE else None,  # ✅ NOUVEAU
                "method": "direct_body_parsing_with_validation_and_memory",
                "timestamp": datetime.now().isoformat()
            }
        
        # Test de clarification si disponible avec mémoire
        clarification_result = None
        if CLARIFICATION_SYSTEM_AVAILABLE and is_clarification_system_enabled():
            clarification_result = await analyze_question_for_clarification(
                question=question_text,
                language=language,
                user_id=user_id,
                conversation_id=conversation_id  # ✅ NOUVEAU: Avec contexte
            )
        
        # Traitement direct seulement si validé et pas de clarification
        if clarification_result and clarification_result.needs_clarification:
            return {
                "success": True,
                "question_received": question_text,
                "special_chars_detected": [c for c in question_text if ord(c) > 127],
                "validation_passed": True,
                "confidence": validation_confidence,
                "needs_clarification": True,
                "clarification_questions": clarification_result.questions,
                "conversation_id": conversation_id,
                "memory_context": get_context_for_clarification(conversation_id) if CONVERSATION_MEMORY_AVAILABLE else None,  # ✅ NOUVEAU
                "method": "direct_body_parsing_with_validation_clarification_and_memory",
                "timestamp": datetime.now().isoformat()
            }
        
        answer = await process_question_openai(question_text, language, "fast")
        
        # ✅ NOUVEAU: Enregistrer la réponse dans la mémoire
        if CONVERSATION_MEMORY_AVAILABLE and conversation_id and answer:
            try:
                add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=answer,
                    role="assistant",
                    language=language
                )
                logger.info(f"🧠 [Memory] Réponse test UTF-8 enregistrée")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement réponse test: {e}")
        
        return {
            "success": True,
            "question_received": question_text,
            "special_chars_detected": [c for c in question_text if ord(c) > 127],
            "validation_passed": True,
            "confidence": validation_confidence,
            "needs_clarification": False,
            "response": answer,
            "conversation_id": conversation_id,
            "memory_context": get_context_for_clarification(conversation_id) if CONVERSATION_MEMORY_AVAILABLE else None,  # ✅ NOUVEAU
            "method": "direct_body_parsing_with_validation_clarification_and_memory",
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

logger.info("✅ EXPERT.PY AVEC SYSTÈME DE MÉMOIRE CONVERSATIONNELLE INTÉGRÉ")
logger.info(f"🧠 CONVERSATION_MEMORY_AVAILABLE: {CONVERSATION_MEMORY_AVAILABLE}")
logger.info(f"🔧 AUTH_AVAILABLE: {AUTH_AVAILABLE}")
logger.info(f"🌾 AGRICULTURAL_VALIDATOR_AVAILABLE: {AGRICULTURAL_VALIDATOR_AVAILABLE}")
logger.info(f"🌾 VALIDATION_ENABLED: {is_agricultural_validation_enabled() if AGRICULTURAL_VALIDATOR_AVAILABLE else 'N/A'}")
logger.info(f"❓ CLARIFICATION_SYSTEM_AVAILABLE: {CLARIFICATION_SYSTEM_AVAILABLE}")
logger.info(f"❓ CLARIFICATION_ENABLED: {is_clarification_system_enabled() if CLARIFICATION_SYSTEM_AVAILABLE else 'N/A'}")
logger.info(f"💾 LOGGING_AVAILABLE: {LOGGING_AVAILABLE}")
logger.info(f"🤖 OPENAI_AVAILABLE: {OPENAI_AVAILABLE}")
logger.info("🔧 FONCTIONNALITÉS CONVERSATIONNELLES ACTIVÉES:")
logger.info("   - 🧠 Mémoire conversationnelle avec extraction d'entités")
logger.info("   - 🔄 Continuité contextuelle entre questions d'une même conversation")
logger.info("   - 📊 Validation agricole enrichie avec contexte conversationnel")
logger.info("   - ❓ Clarification intelligente basée sur l'historique")
logger.info("   - 🏗️ RAG enrichi avec contexte de conversation")
logger.info("   - 💾 Persistance automatique avec expiration (24h)")
logger.info("   - 🗑️ Nettoyage automatique des conversations expirées")
logger.info("🔧 ENDPOINTS DISPONIBLES:")
logger.info("   - POST /ask (authentifié) + mémoire conversationnelle")
logger.info("   - POST /ask-public (public) + mémoire conversationnelle") 
logger.info("   - POST /feedback (amélioration avec conversation_id)")
logger.info("   - GET /topics (suggestions sujets)")
logger.info("   - GET /validation-stats (stats validateur)")
logger.info("   - POST /test-clarification (test clarifications + mémoire)")
logger.info("   - GET /clarification-status (status clarifications)")
logger.info("   - POST /test-validation (test validation)")
logger.info("🔧 NOUVEAUX ENDPOINTS MÉMOIRE:")
logger.info("   - GET /conversation/{id}/context (contexte conversationnel)")
logger.info("   - GET /conversation/{id}/history (historique messages)")
logger.info("   - GET /memory/stats (statistiques mémoire)")
logger.info("   - POST /memory/cleanup (nettoyage conversations expirées)")
logger.info("   - GET /debug-database (debug base données)")
logger.info("   - GET /debug-system (diagnostic complet + mémoire)")
logger.info("   - GET /debug-auth (diagnostic auth + mémoire)")
logger.info("   - POST /test-utf8 (test encodage UTF-8 + mémoire)")

if CONVERSATION_MEMORY_AVAILABLE:
    try:
        memory_stats = get_conversation_memory_stats()
        logger.info(f"📊 [Memory] Statistiques système: {memory_stats}")
        logger.info("🎉 [Memory] Système de mémoire conversationnelle pleinement opérationnel!")
        logger.info("🔧 [Memory] Configuration:")
        logger.info(f"   - Messages max par conversation: {memory_stats.get('max_messages_in_memory', 'N/A')}")
        logger.info(f"   - Expiration conversations: {memory_stats.get('context_expiry_hours', 'N/A')}h")
        logger.info(f"   - Extraction entités: {'✅ Activée' if memory_stats.get('enabled', False) else '❌ Désactivée'}")
        logger.info(f"   - Base de données: {memory_stats.get('database_path', 'N/A')}")
    except Exception as e:
        logger.warning(f"⚠️ [Memory] Erreur récupération stats: {e}")
else:
    logger.warning("⚠️ [Memory] Système de mémoire conversationnelle NON DISPONIBLE")
    logger.warning("⚠️ [Memory] Les conversations seront traitées de manière indépendante")
    logger.warning("⚠️ [Memory] Pour activer: créer app/api/v1/conversation_memory.py")

logger.info("🚀 [Expert] Système Expert Intelia avec mémoire conversationnelle prêt!")
logger.info("🎯 [Expert] Résolution du problème: Plus de questions redondantes sur la race/âge!")
logger.info("🧠 [Expert] Continuité conversationnelle: Ross 308 mentionné une fois = retenu pour la conversation")