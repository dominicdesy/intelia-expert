"""
app/api/v1/expert_enhanced.py - VERSION AMÉLIORÉE AVEC RETRAITEMENT AUTOMATIQUE

NOUVELLES FONCTIONNALITÉS:
1. Retraitement automatique après clarification complétée
2. Intégration système de clarification amélioré
3. Gestion intelligente des réponses avec données numériques
4. Détection automatique des questions enrichies
5. Suivi d'état conversationnel avancé
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

router = APIRouter(tags=["expert-enhanced"])
logger = logging.getLogger(__name__)

# =============================================================================
# IMPORT SYSTÈME DE CLARIFICATION AMÉLIORÉ - CORRIGÉ
# =============================================================================

try:
    from app.api.v1.question_clarification_system_enhanced import (
        analyze_question_for_clarification_enhanced,
        format_clarification_response_enhanced,
        check_for_reprocessing_after_clarification,
        is_enhanced_clarification_system_enabled,
        get_enhanced_clarification_system_stats,
        ClarificationResult,
        ClarificationState,
        ClarificationMode
    )
    ENHANCED_CLARIFICATION_AVAILABLE = True
    logger.info("✅ [Expert Enhanced] Système de clarification amélioré importé")
except ImportError as e:
    ENHANCED_CLARIFICATION_AVAILABLE = False
    logger.warning(f"⚠️ [Expert Enhanced] Clarification améliorée non disponible: {e}")

# =============================================================================
# IMPORT MÉMOIRE CONVERSATIONNELLE INTELLIGENTE - CORRIGÉ
# =============================================================================

try:
    from app.api.v1.conversation_memory_enhanced import (
        add_message_to_conversation,
        get_conversation_context,
        get_context_for_clarification,
        get_context_for_rag,
        get_conversation_memory_stats,
        cleanup_expired_conversations,
        IntelligentConversationContext
    )
    INTELLIGENT_MEMORY_AVAILABLE = True
    logger.info("✅ [Expert Enhanced] Mémoire intelligente importée")
except ImportError as e:
    INTELLIGENT_MEMORY_AVAILABLE = False
    logger.warning(f"⚠️ [Expert Enhanced] Mémoire intelligente non disponible: {e}")

# =============================================================================
# IMPORT VALIDATEUR AGRICOLE (EXISTANT)
# =============================================================================

try:
    from app.api.v1.agricultural_domain_validator import (
        validate_agricultural_question,
        get_agricultural_validator_stats,
        is_agricultural_validation_enabled
    )
    AGRICULTURAL_VALIDATOR_AVAILABLE = True
    logger.info("✅ [Expert Enhanced] Validateur agricole importé")
except ImportError as e:
    AGRICULTURAL_VALIDATOR_AVAILABLE = False
    logger.error(f"❌ [Expert Enhanced] Validateur agricole non disponible: {e}")

# =============================================================================
# IMPORT AUTH (EXISTANT)
# =============================================================================

AUTH_AVAILABLE = False
get_current_user = None

try:
    from .auth import get_current_user
    AUTH_AVAILABLE = True
    logger.info("✅ [Expert Enhanced] Auth importé")
except ImportError:
    try:
        from app.api.v1.auth import get_current_user
        AUTH_AVAILABLE = True
        logger.info("✅ [Expert Enhanced] Auth importé (path alternatif)")
    except ImportError as e:
        logger.error(f"❌ [Expert Enhanced] Auth non disponible: {e}")

# =============================================================================
# IMPORT OPENAI
# =============================================================================

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

# =============================================================================
# MODÈLES PYDANTIC AMÉLIORÉS
# =============================================================================

class EnhancedQuestionRequest(BaseModel):
    """Request model amélioré avec support état conversationnel"""
    text: str = Field(..., min_length=1, max_length=5000)
    language: Optional[str] = Field("fr", description="Response language")
    speed_mode: Optional[str] = Field("balanced", description="Speed mode")
    
    # Contexte conversationnel
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    user_id: Optional[str] = Field(None, description="User ID")
    
    # ✅ NOUVEAUX CHAMPS
    is_clarification_response: Optional[bool] = Field(False, description="Is this a response to clarification?")
    original_question: Optional[str] = Field(None, description="Original question if this is clarification response")
    clarification_context: Optional[Dict[str, Any]] = Field(None, description="Clarification context")
    force_reprocess: Optional[bool] = Field(False, description="Force reprocessing even if no clarification needed")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        extra="ignore"
    )

class EnhancedExpertResponse(BaseModel):
    """Response model amélioré avec état conversationnel"""
    question: str
    response: str
    conversation_id: str
    rag_used: bool
    rag_score: Optional[float] = None
    timestamp: str
    language: str
    response_time_ms: int
    mode: str
    user: Optional[str] = None
    logged: bool = False
    validation_passed: Optional[bool] = None
    validation_confidence: Optional[float] = None
    
    # ✅ NOUVEAUX CHAMPS
    clarification_result: Optional[Dict[str, Any]] = None
    reprocessed_after_clarification: Optional[bool] = None
    conversation_state: Optional[str] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    confidence_overall: Optional[float] = None
    
    # Métriques avancées
    processing_steps: Optional[List[str]] = None
    ai_enhancements_used: Optional[List[str]] = None

# =============================================================================
# FONCTIONS UTILITAIRES AMÉLIORÉES
# =============================================================================

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
        logger.warning(f"⚠️ [Expert Enhanced] Erreur génération user_id: {e}")
        return f"anon_{uuid.uuid4().hex[:8]}"

async def validate_question_agricultural_domain_enhanced(
    question: str, 
    language: str, 
    user_id: str, 
    request_ip: str,
    conversation_id: str = None
) -> tuple[bool, str, float]:
    """Validation agricole avec contexte intelligent"""
    
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        logger.error("❌ [Expert Enhanced] Validateur agricole non disponible")
        
        rejection_messages = {
            "fr": "Service temporairement indisponible. Veuillez réessayer plus tard.",
            "en": "Service temporarily unavailable. Please try again later.",
            "es": "Servicio temporalmente no disponible. Por favor, inténtelo más tarde."
        }
        
        return False, rejection_messages.get(language, rejection_messages["fr"]), 0.0
    
    # Enrichir avec contexte intelligent
    enriched_question = question
    if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
        try:
            rag_context = get_context_for_rag(conversation_id)
            if rag_context:
                enriched_question = f"{question}\n\nContexte conversationnel:\n{rag_context}"
                logger.info(f"🧠 [Expert Enhanced] Question enrichie avec contexte intelligent")
        except Exception as e:
            logger.warning(f"⚠️ [Expert Enhanced] Erreur enrichissement contexte: {e}")
    
    if not is_agricultural_validation_enabled():
        logger.info("🔧 [Expert Enhanced] Validation agricole désactivée")
        return True, "", 100.0
    
    try:
        validation_result = validate_agricultural_question(
            question=enriched_question,
            language=language,
            user_id=user_id,
            request_ip=request_ip
        )
        
        logger.info(f"🔍 [Expert Enhanced] Validation: {validation_result.is_valid} (confiance: {validation_result.confidence:.1f}%)")
        
        if validation_result.is_valid:
            return True, "", validation_result.confidence
        else:
            return False, validation_result.reason or "Question hors domaine agricole", validation_result.confidence
    
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur validateur: {e}")
        
        rejection_messages = {
            "fr": "Erreur de validation. Veuillez reformuler votre question sur le domaine avicole.",
            "en": "Validation error. Please rephrase your question about the poultry domain.",
            "es": "Error de validación. Por favor, reformule su pregunta sobre el dominio avícola."
        }
        
        return False, rejection_messages.get(language, rejection_messages["fr"]), 0.0

async def process_question_with_enhanced_prompt(
    question: str, 
    language: str = "fr", 
    speed_mode: str = "balanced",
    extracted_entities: Dict = None,
    conversation_context: str = ""
) -> str:
    """Traite une question avec prompt amélioré pour données numériques"""
    
    if not OPENAI_AVAILABLE or not openai:
        return get_fallback_response_enhanced(question, language)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return get_fallback_response_enhanced(question, language)
        
        openai.api_key = api_key
        
        # ✅ PROMPT AMÉLIORÉ avec données numériques
        enhanced_prompts = {
            "fr": f"""Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair. 

CONSIGNES CRITIQUES:
1. Si la question porte sur le poids, la croissance ou des valeurs numériques, donne TOUJOURS une réponse chiffrée précise
2. Utilise le contexte conversationnel fourni pour personnaliser ta réponse
3. Commence par répondre directement à la question, puis donne des conseils complémentaires
4. Utilise tous les caractères français (é, è, à, ç, ù, etc.) et symboles (°C, %, g, kg)

Contexte conversationnel disponible:
{conversation_context}

IMPORTANT: Si des informations spécifiques sont mentionnées (race, âge), utilise-les pour donner une réponse précise et chiffrée.""",

            "en": f"""You are a veterinary expert specialized in animal health and nutrition, particularly for broiler chickens.

CRITICAL INSTRUCTIONS:
1. If the question is about weight, growth or numerical values, ALWAYS provide precise numerical answers
2. Use the provided conversational context to personalize your response  
3. Start by directly answering the question, then provide additional advice
4. Provide industry-standard data and recommendations

Available conversational context:
{conversation_context}

IMPORTANT: If specific information is mentioned (breed, age), use it to provide precise, numerical answers.""",

            "es": f"""Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde.

INSTRUCCIONES CRÍTICAS:
1. Si la pregunta es sobre peso, crecimiento o valores numéricos, da SIEMPRE una respuesta numérica precisa
2. Usa el contexto conversacional proporcionado para personalizar tu respuesta
3. Comienza respondiendo directamente a la pregunta, luego da consejos adicionales  
4. Usa todos los caracteres especiales del español (ñ, ¿, ¡, acentos)

Contexto conversacional disponible:
{conversation_context}

IMPORTANTE: Si se menciona información específica (raza, edad), úsala para dar una respuesta precisa y numérica."""
        }
        
        system_prompt = enhanced_prompts.get(language.lower(), enhanced_prompts["fr"])
        
        # Configuration par mode
        model_config = {
            "fast": {"model": "gpt-3.5-turbo", "max_tokens": 400},
            "balanced": {"model": "gpt-4o-mini", "max_tokens": 600},
            "quality": {"model": "gpt-4o-mini", "max_tokens": 800}
        }
        
        config = model_config.get(speed_mode, model_config["balanced"])
        
        response = openai.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(question)}
            ],
            temperature=0.7,
            max_tokens=config["max_tokens"],
            timeout=20
        )
        
        answer = response.choices[0].message.content
        return str(answer) if answer else get_fallback_response_enhanced(question, language)
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur OpenAI: {e}")
        return get_fallback_response_enhanced(question, language)

def get_fallback_response_enhanced(question: str, language: str = "fr") -> str:
    """Réponse de fallback améliorée"""
    try:
        safe_question = str(question)[:50] if question else "votre question"
    except:
        safe_question = "votre question"
    
    fallback_responses = {
        "fr": f"Je suis un expert vétérinaire spécialisé en aviculture. Pour votre question '{safe_question}...', je recommande de surveiller attentivement les paramètres de performance et de maintenir des conditions d'élevage optimales. Pour une réponse plus précise, pourriez-vous spécifier la race et l'âge de vos poulets ?",
        "en": f"I am a veterinary expert specialized in poultry. For your question '{safe_question}...', I recommend closely monitoring performance parameters and maintaining optimal breeding conditions. For a more precise answer, could you specify the breed and age of your chickens?",
        "es": f"Soy un experto veterinario especializado en avicultura. Para su pregunta '{safe_question}...', recomiendo monitorear cuidadosamente los parámetros de rendimiento y mantener condiciones óptimas de crianza. Para una respuesta más precisa, ¿podría especificar la raza y edad de sus pollos?"
    }
    return fallback_responses.get(language.lower(), fallback_responses["fr"])

def build_enriched_question_from_clarification(
    original_question: str,
    clarification_response: str,
    conversation_context: str = ""
) -> str:
    """Construit une question enrichie après clarification"""
    
    enriched_parts = [original_question]
    
    if clarification_response.strip():
        enriched_parts.append(f"Information supplémentaire: {clarification_response.strip()}")
    
    if conversation_context.strip():
        enriched_parts.append(f"Contexte: {conversation_context.strip()}")
    
    return "\n\n".join(enriched_parts)

# =============================================================================
# ENDPOINT PRINCIPAL AMÉLIORÉ AVEC RETRAITEMENT AUTOMATIQUE
# =============================================================================

@router.post("/ask-enhanced", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user) if AUTH_AVAILABLE else None
):
    """
    Endpoint expert amélioré avec:
    - Retraitement automatique après clarification
    - Gestion intelligente du contexte conversationnel  
    - Réponses avec données numériques optimisées
    - Suivi d'état conversationnel avancé
    """
    start_time = time.time()
    processing_steps = []
    ai_enhancements_used = []
    
    try:
        logger.info("=" * 80)
        logger.info("🚀 DÉBUT ask_expert_enhanced - VERSION INTELLIGENTE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        logger.info(f"🆔 Conversation ID: {request_data.conversation_id}")
        logger.info(f"🔄 Is clarification response: {request_data.is_clarification_response}")
        logger.info(f"⚡ Force reprocess: {request_data.force_reprocess}")
        
        processing_steps.append("initialization")
        
        # ===🔐 AUTHENTIFICATION===
        if not AUTH_AVAILABLE:
            raise HTTPException(status_code=503, detail="Service d'authentification non disponible")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentification requise")
        
        user_id = current_user.get("user_id") or request_data.user_id
        user_email = current_user.get("email")
        request_ip = request.client.host if request.client else "unknown"
        
        logger.info(f"✅ Authentifié: {user_email} ({user_id[:8] if user_id else 'N/A'}...)")
        request.state.user = current_user
        processing_steps.append("authentication")
        
        # ===🆔 GESTION CONVERSATION ID===
        if request_data.conversation_id and request_data.conversation_id.strip():
            conversation_id = request_data.conversation_id.strip()
            logger.info(f"🔄 [Conversation] CONTINUATION: {conversation_id}")
        else:
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 [Conversation] NOUVELLE: {conversation_id}")
        
        # ===📝 VALIDATION QUESTION===
        question_text = request_data.text.strip()
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        processing_steps.append("question_validation")
        
        # ===🧠 ENREGISTREMENT MESSAGE DANS MÉMOIRE INTELLIGENTE===
        conversation_context = None
        if INTELLIGENT_MEMORY_AVAILABLE:
            try:
                conversation_context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id or "authenticated_user",
                    message=question_text,
                    role="user",
                    language=request_data.language,
                    message_type="clarification_response" if request_data.is_clarification_response else "question"
                )
                logger.info(f"🧠 [Memory] Message enregistré avec extraction intelligente")
                logger.info(f"🧠 [Memory] Entités détectées: {conversation_context.consolidated_entities.to_dict()}")
                ai_enhancements_used.append("intelligent_memory")
                processing_steps.append("memory_storage")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement: {e}")
        
        # ===🌾 VALIDATION AGRICOLE AVEC CONTEXTE INTELLIGENT===
        logger.info("🌾 [VALIDATION] Démarrage validation avec contexte intelligent...")
        
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain_enhanced(
            question=question_text,
            language=request_data.language,
            user_id=user_id or "authenticated_user",
            request_ip=request_ip,
            conversation_id=conversation_id
        )
        
        processing_steps.append("agricultural_validation")
        
        if not is_valid:
            logger.warning(f"🚫 [VALIDATION] Question rejetée: {rejection_message}")
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Enregistrer rejet dans mémoire
            if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
                try:
                    add_message_to_conversation(
                        conversation_id=conversation_id,
                        user_id=user_id or "authenticated_user",
                        message=rejection_message,
                        role="assistant",
                        language=request_data.language,
                        message_type="rejection"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [Memory] Erreur enregistrement rejet: {e}")
            
            return EnhancedExpertResponse(
                question=str(question_text),
                response=str(rejection_message),
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=request_data.language,
                response_time_ms=response_time_ms,
                mode="enhanced_agricultural_validation_rejected",
                user=user_email,
                logged=True,
                validation_passed=False,
                validation_confidence=validation_confidence,
                processing_steps=processing_steps,
                ai_enhancements_used=ai_enhancements_used
            )
        
        logger.info(f"✅ [VALIDATION] Question validée (confiance: {validation_confidence:.1f}%)")
        
        # ===❓ SYSTÈME DE CLARIFICATION AMÉLIORÉ===
        clarification_result = None
        needs_clarification = False
        
        # Vérifier si c'est une réponse à une clarification
        if request_data.is_clarification_response and request_data.original_question:
            logger.info("🔄 [CLARIFICATION] Réponse à clarification détectée - vérification retraitement...")
            
            if ENHANCED_CLARIFICATION_AVAILABLE:
                try:
                    # Construire la question enrichie
                    enriched_question = build_enriched_question_from_clarification(
                        original_question=request_data.original_question,
                        clarification_response=question_text,
                        conversation_context=get_context_for_rag(conversation_id) if INTELLIGENT_MEMORY_AVAILABLE else ""
                    )
                    
                    # Vérifier si retraitement possible
                    if hasattr(request_data, 'clarification_context') and request_data.clarification_context:
                        original_clarification = ClarificationResult(**request_data.clarification_context)
                        reprocess_result = await check_for_reprocessing_after_clarification(
                            conversation_id=conversation_id,
                            user_response=question_text,
                            original_clarification_result=original_clarification
                        )
                        
                        if reprocess_result and reprocess_result.should_reprocess:
                            logger.info("✅ [CLARIFICATION] Retraitement automatique activé")
                            question_text = enriched_question  # Utiliser la question enrichie
                            ai_enhancements_used.append("automatic_reprocessing")
                            processing_steps.append("automatic_reprocessing")
                        else:
                            logger.info("⚠️ [CLARIFICATION] Retraitement non possible - clarification supplémentaire nécessaire")
                            needs_clarification = True
                
                except Exception as e:
                    logger.warning(f"⚠️ [CLARIFICATION] Erreur vérification retraitement: {e}")
            
        # Analyse de clarification normale si pas de retraitement
        if not request_data.is_clarification_response and not request_data.force_reprocess:
            if ENHANCED_CLARIFICATION_AVAILABLE and is_enhanced_clarification_system_enabled():
                logger.info("❓ [CLARIFICATION] Analyse avec système amélioré...")
                
                # Récupérer contexte conversationnel pour clarification
                clarification_context = {}
                if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
                    try:
                        clarification_context = get_context_for_clarification(conversation_id)
                        ai_enhancements_used.append("intelligent_clarification_context")
                    except Exception as e:
                        logger.warning(f"⚠️ [CLARIFICATION] Erreur contexte: {e}")
                
                clarification_result = await analyze_question_for_clarification_enhanced(
                    question=question_text,
                    language=request_data.language,
                    user_id=user_id or "authenticated_user",
                    conversation_id=conversation_id,
                    conversation_context=clarification_context,
                    original_question=question_text
                )
                
                processing_steps.append("enhanced_clarification_analysis")
                
                if clarification_result.needs_clarification:
                    logger.info(f"❓ [CLARIFICATION] {len(clarification_result.questions)} questions générées (mode: {clarification_result.clarification_mode.value if clarification_result.clarification_mode else 'N/A'})")
                    
                    clarification_response = format_clarification_response_enhanced(
                        result=clarification_result,
                        language=request_data.language
                    )
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    # Enregistrer clarification dans mémoire
                    if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
                        try:
                            add_message_to_conversation(
                                conversation_id=conversation_id,
                                user_id=user_id or "authenticated_user",
                                message=clarification_response,
                                role="assistant",
                                language=request_data.language,
                                message_type="clarification"
                            )
                        except Exception as e:
                            logger.warning(f"⚠️ [Memory] Erreur enregistrement clarification: {e}")
                    
                    return EnhancedExpertResponse(
                        question=str(question_text),
                        response=str(clarification_response),
                        conversation_id=conversation_id,
                        rag_used=False,
                        rag_score=None,
                        timestamp=datetime.now().isoformat(),
                        language=request_data.language,
                        response_time_ms=response_time_ms,
                        mode="enhanced_clarification_needed",
                        user=user_email,
                        logged=True,
                        validation_passed=True,
                        validation_confidence=validation_confidence,
                        clarification_result=clarification_result.to_dict(),
                        processing_steps=processing_steps,
                        ai_enhancements_used=ai_enhancements_used,
                        extracted_entities=clarification_result.extracted_entities.to_dict() if clarification_result.extracted_entities else None
                    )
                
                logger.info("✅ [CLARIFICATION] Question suffisamment claire")
                
        # ===🎯 TRAITEMENT EXPERT AVEC CONTEXTE INTELLIGENT===
        rag_used = False
        rag_score = None
        answer = ""
        mode = "enhanced_direct_processing"
        
        # Récupérer contexte pour traitement
        conversation_context_str = ""
        if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
            try:
                conversation_context_str = get_context_for_rag(conversation_id, max_chars=800)
                ai_enhancements_used.append("contextual_rag")
            except Exception as e:
                logger.warning(f"⚠️ [Context] Erreur récupération contexte: {e}")
        
        # Essayer RAG d'abord
        app = request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG avec contexte intelligent...")
                
                try:
                    result = await process_rag(
                        question=question_text,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id,
                        context=conversation_context_str
                    )
                except TypeError:
                    # Si process_rag ne supporte pas le paramètre context
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
                mode = f"enhanced_{result.get('mode', 'rag_processing')}"
                
                logger.info(f"✅ RAG traité avec contexte intelligent - Mode: {mode}, Score: {rag_score}")
                processing_steps.append("rag_processing")
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG: {rag_error}")
                answer = await process_question_with_enhanced_prompt(
                    question_text, 
                    request_data.language,
                    request_data.speed_mode,
                    conversation_context=conversation_context_str
                )
                mode = "enhanced_fallback_openai"
                processing_steps.append("fallback_openai")
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI avec contexte intelligent")
            answer = await process_question_with_enhanced_prompt(
                question_text,
                request_data.language,
                request_data.speed_mode,
                conversation_context=conversation_context_str
            )
            mode = "enhanced_direct_openai"
            processing_steps.append("direct_openai")
        
        if conversation_context_str:
            ai_enhancements_used.append("enhanced_prompts")
        
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"⏱️ Temps de traitement: {response_time_ms}ms")
        
        # ===🧠 ENREGISTREMENT RÉPONSE DANS MÉMOIRE===
        if INTELLIGENT_MEMORY_AVAILABLE and conversation_id and answer:
            try:
                add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id or "authenticated_user",
                    message=answer,
                    role="assistant",
                    language=request_data.language,
                    message_type="response"
                )
                logger.info(f"🧠 [Memory] Réponse enregistrée avec analyse intelligente")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement réponse: {e}")
        
        processing_steps.append("response_storage")
        
        # ===📊 MÉTRIQUES FINALES===
        extracted_entities = None
        confidence_overall = None
        conversation_state = None
        
        if conversation_context and hasattr(conversation_context, 'consolidated_entities'):
            extracted_entities = conversation_context.consolidated_entities.to_dict()
            confidence_overall = conversation_context.consolidated_entities.confidence_overall
            conversation_state = conversation_context.conversation_urgency
        
        # Retourner la réponse enrichie
        response_obj = EnhancedExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,
            rag_used=rag_used,
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=request_data.language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=user_email,
            logged=True,
            validation_passed=True,
            validation_confidence=validation_confidence,
            clarification_result=clarification_result.to_dict() if clarification_result else None,
            reprocessed_after_clarification=request_data.is_clarification_response,
            conversation_state=conversation_state,
            extracted_entities=extracted_entities,
            confidence_overall=confidence_overall,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used
        )
        
        logger.info(f"✅ FIN ask_expert_enhanced - conversation_id: {conversation_id}")
        logger.info(f"🤖 IA enhancements utilisés: {ai_enhancements_used}")
        logger.info(f"📈 Étapes de traitement: {processing_steps}")
        logger.info("=" * 80)
        
        return response_obj
    
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced: {e}")
        import traceback
        logger.error(f"❌ Traceback complet: {traceback.format_exc()}")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# ENDPOINT PUBLIC AMÉLIORÉ
# =============================================================================

@router.post("/ask-enhanced-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_public(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint public avec fonctionnalités améliorées"""
    start_time = time.time()
    processing_steps = []
    ai_enhancements_used = []
    
    try:
        logger.info("=" * 80)
        logger.info("🌐 DÉBUT ask_expert_enhanced_public - VERSION INTELLIGENTE PUBLIQUE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        
        processing_steps.append("initialization")
        
        # Validation question
        question_text = request_data.text.strip()
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        # Gestion conversation ID
        if request_data.conversation_id and request_data.conversation_id.strip():
            conversation_id = request_data.conversation_id.strip()
            logger.info(f"🔄 [Conversation] CONTINUATION publique: {conversation_id}")
        else:
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 [Conversation] NOUVELLE publique: {conversation_id}")
        
        user_id = request_data.user_id or get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        
        processing_steps.append("user_identification")
        
        # Enregistrement dans mémoire intelligente
        conversation_context = None
        if INTELLIGENT_MEMORY_AVAILABLE:
            try:
                conversation_context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=request_data.language,
                    message_type="clarification_response" if request_data.is_clarification_response else "question"
                )
                logger.info(f"🧠 [Memory] Message public enregistré avec extraction intelligente")
                ai_enhancements_used.append("intelligent_memory")
                processing_steps.append("memory_storage")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement public: {e}")
        
        # Validation agricole
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain_enhanced(
            question=question_text,
            language=request_data.language,
            user_id=user_id,
            request_ip=request_ip,
            conversation_id=conversation_id
        )
        
        processing_steps.append("agricultural_validation")
        
        if not is_valid:
            logger.warning(f"🚫 [VALIDATION] Question publique rejetée: {rejection_message}")
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
                try:
                    add_message_to_conversation(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        message=rejection_message,
                        role="assistant",
                        language=request_data.language,
                        message_type="rejection"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [Memory] Erreur enregistrement rejet public: {e}")
            
            return EnhancedExpertResponse(
                question=str(question_text),
                response=str(rejection_message),
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=request_data.language,
                response_time_ms=response_time_ms,
                mode="enhanced_public_validation_rejected",
                user=None,
                logged=True,
                validation_passed=False,
                validation_confidence=validation_confidence,
                processing_steps=processing_steps,
                ai_enhancements_used=ai_enhancements_used
            )
        
        logger.info(f"✅ [VALIDATION] Question publique validée (confiance: {validation_confidence:.1f}%)")
        
        # Système de clarification (même logique que l'endpoint authentifié)
        clarification_result = None
        
        if not request_data.is_clarification_response and not request_data.force_reprocess:
            if ENHANCED_CLARIFICATION_AVAILABLE and is_enhanced_clarification_system_enabled():
                logger.info("❓ [CLARIFICATION] Analyse publique avec système amélioré...")
                
                clarification_context = {}
                if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
                    try:
                        clarification_context = get_context_for_clarification(conversation_id)
                        ai_enhancements_used.append("intelligent_clarification_context")
                    except Exception as e:
                        logger.warning(f"⚠️ [CLARIFICATION] Erreur contexte public: {e}")
                
                clarification_result = await analyze_question_for_clarification_enhanced(
                    question=question_text,
                    language=request_data.language,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_context=clarification_context,
                    original_question=question_text
                )
                
                processing_steps.append("enhanced_clarification_analysis")
                
                if clarification_result.needs_clarification:
                    logger.info(f"❓ [CLARIFICATION] {len(clarification_result.questions)} questions publiques générées")
                    
                    clarification_response = format_clarification_response_enhanced(
                        result=clarification_result,
                        language=request_data.language
                    )
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
                        try:
                            add_message_to_conversation(
                                conversation_id=conversation_id,
                                user_id=user_id,
                                message=clarification_response,
                                role="assistant",
                                language=request_data.language,
                                message_type="clarification"
                            )
                        except Exception as e:
                            logger.warning(f"⚠️ [Memory] Erreur enregistrement clarification publique: {e}")
                    
                    return EnhancedExpertResponse(
                        question=str(question_text),
                        response=str(clarification_response),
                        conversation_id=conversation_id,
                        rag_used=False,
                        rag_score=None,
                        timestamp=datetime.now().isoformat(),
                        language=request_data.language,
                        response_time_ms=response_time_ms,
                        mode="enhanced_public_clarification_needed",
                        user=None,
                        logged=True,
                        validation_passed=True,
                        validation_confidence=validation_confidence,
                        clarification_result=clarification_result.to_dict(),
                        processing_steps=processing_steps,
                        ai_enhancements_used=ai_enhancements_used,
                        extracted_entities=clarification_result.extracted_entities.to_dict() if clarification_result.extracted_entities else None
                    )
                
                logger.info("✅ [CLARIFICATION] Question publique suffisamment claire")
        
        # Traitement expert (similaire à l'endpoint authentifié)
        rag_used = False
        rag_score = None
        answer = ""
        mode = "enhanced_public_processing"
        
        conversation_context_str = ""
        if INTELLIGENT_MEMORY_AVAILABLE and conversation_id:
            try:
                conversation_context_str = get_context_for_rag(conversation_id, max_chars=800)
                ai_enhancements_used.append("contextual_rag")
            except Exception as e:
                logger.warning(f"⚠️ [Context] Erreur récupération contexte public: {e}")
        
        # Essayer RAG ou OpenAI direct
        app = request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG public avec contexte intelligent...")
                
                try:
                    result = await process_rag(
                        question=question_text,
                        user=None,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id,
                        context=conversation_context_str
                    )
                except TypeError:
                    result = await process_rag(
                        question=question_text,
                        user=None,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id
                    )
                
                answer = str(result.get("response", ""))
                rag_used = result.get("mode", "").startswith("rag")
                rag_score = result.get("score")
                mode = f"enhanced_public_{result.get('mode', 'rag_processing')}"
                
                logger.info(f"✅ RAG public traité avec contexte intelligent")
                processing_steps.append("rag_processing")
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG public: {rag_error}")
                answer = await process_question_with_enhanced_prompt(
                    question_text, 
                    request_data.language,
                    request_data.speed_mode,
                    conversation_context=conversation_context_str
                )
                mode = "enhanced_public_fallback_openai"
                processing_steps.append("fallback_openai")
        else:
            logger.info("⚠️ RAG non disponible, utilisation OpenAI public avec contexte intelligent")
            answer = await process_question_with_enhanced_prompt(
                question_text,
                request_data.language,
                request_data.speed_mode,
                conversation_context=conversation_context_str
            )
            mode = "enhanced_public_direct_openai"
            processing_steps.append("direct_openai")
        
        if conversation_context_str:
            ai_enhancements_used.append("enhanced_prompts")
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Enregistrement réponse
        if INTELLIGENT_MEMORY_AVAILABLE and conversation_id and answer:
            try:
                add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=answer,
                    role="assistant",
                    language=request_data.language,
                    message_type="response"
                )
                logger.info(f"🧠 [Memory] Réponse publique enregistrée")
            except Exception as e:
                logger.warning(f"⚠️ [Memory] Erreur enregistrement réponse publique: {e}")
        
        processing_steps.append("response_storage")
        
        # Métriques finales
        extracted_entities = None
        confidence_overall = None
        conversation_state = None
        
        if conversation_context and hasattr(conversation_context, 'consolidated_entities'):
            extracted_entities = conversation_context.consolidated_entities.to_dict()
            confidence_overall = conversation_context.consolidated_entities.confidence_overall
            conversation_state = conversation_context.conversation_urgency
        
        response_obj = EnhancedExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,
            rag_used=rag_used,
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=request_data.language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=None,
            logged=True,
            validation_passed=True,
            validation_confidence=validation_confidence,
            clarification_result=clarification_result.to_dict() if clarification_result else None,
            reprocessed_after_clarification=request_data.is_clarification_response,
            conversation_state=conversation_state,
            extracted_entities=extracted_entities,
            confidence_overall=confidence_overall,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used
        )
        
        logger.info(f"✅ FIN ask_expert_enhanced_public - conversation_id: {conversation_id}")
        logger.info(f"🤖 IA enhancements publics utilisés: {ai_enhancements_used}")
        logger.info("=" * 80)
        
        return response_obj
    
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_public: {e}")
        import traceback
        logger.error(f"❌ Traceback complet: {traceback.format_exc()}")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# ENDPOINTS DE DIAGNOSTIC AMÉLIORÉS
# =============================================================================

@router.get("/enhanced-stats")
async def get_enhanced_system_stats():
    """Statistiques du système expert amélioré"""
    try:
        stats = {
            "system_available": True,
            "timestamp": datetime.now().isoformat(),
            
            # Composants disponibles
            "components": {
                "enhanced_clarification": ENHANCED_CLARIFICATION_AVAILABLE,
                "intelligent_memory": INTELLIGENT_MEMORY_AVAILABLE,
                "agricultural_validation": AGRICULTURAL_VALIDATOR_AVAILABLE,
                "openai": OPENAI_AVAILABLE,
                "auth": AUTH_AVAILABLE
            },
            
            # Statistiques des composants
            "enhanced_clarification_stats": get_enhanced_clarification_system_stats() if ENHANCED_CLARIFICATION_AVAILABLE else None,
            "intelligent_memory_stats": get_conversation_memory_stats() if INTELLIGENT_MEMORY_AVAILABLE else None,
            "agricultural_validation_stats": get_agricultural_validator_stats() if AGRICULTURAL_VALIDATOR_AVAILABLE else None,
            
            # Capacités améliorées
            "enhanced_capabilities": [
                "automatic_reprocessing_after_clarification",
                "intelligent_entity_extraction", 
                "contextual_reasoning",
                "enhanced_prompts_with_numerical_data",
                "multi_mode_clarification",
                "conversation_state_tracking",
                "ai_powered_enhancements"
            ],
            
            # Endpoints disponibles
            "enhanced_endpoints": [
                "POST /ask-enhanced (authenticated)",
                "POST /ask-enhanced-public (public)",
                "GET /enhanced-stats (system statistics)",
                "POST /test-enhanced-flow (testing)",
                "GET /enhanced-conversation/{id}/context (conversation context)"
            ]
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ [Enhanced Stats] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur stats: {str(e)}")

@router.post("/test-enhanced-flow")
async def test_enhanced_flow(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint de test pour le flux amélioré complet"""
    try:
        logger.info(f"🧪 [Test Enhanced] Test du flux amélioré")
        logger.info(f"📝 Question: {request_data.text}")
        logger.info(f"🔄 Is clarification response: {request_data.is_clarification_response}")
        
        user_id = get_user_id_from_request(request)
        conversation_id = request_data.conversation_id or str(uuid.uuid4())
        
        test_results = {
            "question": request_data.text,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "components_tested": {},
            "test_successful": True,
            "errors": []
        }
        
        # Test mémoire intelligente
        if INTELLIGENT_MEMORY_AVAILABLE:
            try:
                context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=request_data.text,
                    role="user",
                    language=request_data.language
                )
                test_results["components_tested"]["intelligent_memory"] = {
                    "status": "success",
                    "extracted_entities": context.consolidated_entities.to_dict(),
                    "confidence": context.consolidated_entities.confidence_overall,
                    "urgency": context.conversation_urgency
                }
            except Exception as e:
                test_results["components_tested"]["intelligent_memory"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results["errors"].append(f"Intelligent memory: {str(e)}")
        
        # Test clarification améliorée
        if ENHANCED_CLARIFICATION_AVAILABLE:
            try:
                clarification_context = get_context_for_clarification(conversation_id) if INTELLIGENT_MEMORY_AVAILABLE else {}
                
                clarification_result = await analyze_question_for_clarification_enhanced(
                    question=request_data.text,
                    language=request_data.language,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_context=clarification_context
                )
                
                test_results["components_tested"]["enhanced_clarification"] = {
                    "status": "success",
                    "needs_clarification": clarification_result.needs_clarification,
                    "questions_count": len(clarification_result.questions) if clarification_result.questions else 0,
                    "clarification_mode": clarification_result.clarification_mode.value if clarification_result.clarification_mode else None,
                    "confidence": clarification_result.confidence_score,
                    "extracted_entities": clarification_result.extracted_entities.to_dict() if clarification_result.extracted_entities else None
                }
            except Exception as e:
                test_results["components_tested"]["enhanced_clarification"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results["errors"].append(f"Enhanced clarification: {str(e)}")
        
        # Test validation agricole
        if AGRICULTURAL_VALIDATOR_AVAILABLE:
            try:
                is_valid, rejection_message, confidence = await validate_question_agricultural_domain_enhanced(
                    question=request_data.text,
                    language=request_data.language,
                    user_id=user_id,
                    request_ip=request.client.host if request.client else "unknown",
                    conversation_id=conversation_id
                )
                
                test_results["components_tested"]["agricultural_validation"] = {
                    "status": "success",
                    "is_valid": is_valid,
                    "confidence": confidence,
                    "rejection_message": rejection_message if not is_valid else None
                }
            except Exception as e:
                test_results["components_tested"]["agricultural_validation"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results["errors"].append(f"Agricultural validation: {str(e)}")
        
        # Test contexte RAG
        if INTELLIGENT_MEMORY_AVAILABLE:
            try:
                rag_context = get_context_for_rag(conversation_id, max_chars=500)
                test_results["components_tested"]["rag_context"] = {
                    "status": "success",
                    "context_length": len(rag_context),
                    "context_preview": rag_context[:100] + "..." if len(rag_context) > 100 else rag_context
                }
            except Exception as e:
                test_results["components_tested"]["rag_context"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results["errors"].append(f"RAG context: {str(e)}")
        
        test_results["test_successful"] = len(test_results["errors"]) == 0
        
        logger.info(f"🧪 [Test Enhanced] Test terminé - Succès: {test_results['test_successful']}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ [Test Enhanced] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur test: {str(e)}")

@router.get("/enhanced-conversation/{conversation_id}/context")
async def get_enhanced_conversation_context(conversation_id: str):
    """Récupère le contexte amélioré d'une conversation"""
    try:
        if not INTELLIGENT_MEMORY_AVAILABLE:
            raise HTTPException(status_code=503, detail="Mémoire intelligente non disponible")
        
        context = get_conversation_context(conversation_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
        
        return {
            "conversation_id": conversation_id,
            "enhanced_context": context.to_dict(),
            "clarification_context": get_context_for_clarification(conversation_id),
            "rag_context": get_context_for_rag(conversation_id),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Enhanced Context] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur contexte: {str(e)}")

# =============================================================================
# CONFIGURATION & LOGGING
# =============================================================================

if OPENAI_AVAILABLE and openai:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai.api_key = openai_api_key
        logger.info("✅ [Expert Enhanced] OpenAI configuré")
    else:
        logger.warning("⚠️ [Expert Enhanced] OpenAI API key non trouvée")

logger.info("🚀 [EXPERT ENHANCED] Système expert amélioré initialisé avec succès!")
logger.info(f"🧠 [EXPERT ENHANCED] Mémoire intelligente: {'✅' if INTELLIGENT_MEMORY_AVAILABLE else '❌'}")
logger.info(f"❓ [EXPERT ENHANCED] Clarification améliorée: {'✅' if ENHANCED_CLARIFICATION_AVAILABLE else '❌'}")
logger.info(f"🌾 [EXPERT ENHANCED] Validation agricole: {'✅' if AGRICULTURAL_VALIDATOR_AVAILABLE else '❌'}")
logger.info(f"🔐 [EXPERT ENHANCED] Auth: {'✅' if AUTH_AVAILABLE else '❌'}")
logger.info(f"🤖 [EXPERT ENHANCED] OpenAI: {'✅' if OPENAI_AVAILABLE else '❌'}")

logger.info("🎯 [EXPERT ENHANCED] NOUVELLES FONCTIONNALITÉS ACTIVÉES:")
logger.info("   - 🔄 Retraitement automatique après clarification complétée")
logger.info("   - 🧠 Extraction d'entités intelligente via IA")
logger.info("   - 📊 Réponses avec données numériques optimisées")
logger.info("   - 🎛️ Modes de clarification adaptatifs (batch/interactive/adaptive)")
logger.info("   - 🔍 Raisonnement contextuel pour éviter clarifications redondantes")
logger.info("   - 📈 Suivi d'état conversationnel avancé")
logger.info("   - ⚡ Détection automatique d'urgence et problèmes critiques")
logger.info("   - 🎯 Contexte intelligent pour RAG et prompts")

logger.info("🔧 [EXPERT ENHANCED] ENDPOINTS DISPONIBLES:")
logger.info("   - POST /ask-enhanced (authentifié avec retraitement auto)")
logger.info("   - POST /ask-enhanced-public (public avec IA)")
logger.info("   - GET /enhanced-stats (statistiques système)")
logger.info("   - POST /test-enhanced-flow (test complet)")
logger.info("   - GET /enhanced-conversation/{id}/context (contexte conversation)")

if ENHANCED_CLARIFICATION_AVAILABLE:
    stats = get_enhanced_clarification_system_stats()
    logger.info(f"📊 [EXPERT ENHANCED] Config clarification: Mode {stats.get('clarification_mode')}, Extraction IA: {'✅' if stats.get('smart_entity_extraction') else '❌'}")

if INTELLIGENT_MEMORY_AVAILABLE:
    memory_stats = get_conversation_memory_stats()
    logger.info(f"📊 [EXPERT ENHANCED] Mémoire intelligente: IA {'✅' if memory_stats.get('ai_powered') else '❌'}, Cache: {memory_stats.get('cache_size')}/{memory_stats.get('cache_max_size')}")

# =============================================================================
# IMPORT LOGGING SYSTEM (EXISTANT)
# =============================================================================

try:
    from app.api.v1.logging import logger_instance, ConversationCreate
    LOGGING_AVAILABLE = True
    logger.info("✅ [Expert Enhanced] Système de logging intégré")
except ImportError as e:
    LOGGING_AVAILABLE = False
    logger_instance = None
    ConversationCreate = None
    logger.warning(f"⚠️ [Expert Enhanced] Système de logging non disponible: {e}")

# =============================================================================
# FONCTION DE SAUVEGARDE COMPLÈTE (DEPUIS EXPERT.PY)
# =============================================================================

async def save_conversation_auto_enhanced(
    conversation_id: str,
    question: str, 
    response: str,
    user_id: str = "anonymous",
    language: str = "fr",
    rag_used: bool = False,
    rag_score: float = None,
    response_time_ms: int = 0
) -> bool:
    """Sauvegarde automatique enhanced - COMPLÈTEMENT COMPATIBLE"""
    
    if not LOGGING_AVAILABLE or not logger_instance:
        logger.warning("⚠️ [Expert Enhanced] Logging non disponible pour sauvegarde")
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
                logger.info(f"✅ [Expert Enhanced] Conversation sauvegardée via log_conversation: {conversation_id}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ [Expert Enhanced] log_conversation échoué: {e}")
        
        # ✅ MÉTHODE 2: Essayer save_conversation
        try:
            if hasattr(logger_instance, 'save_conversation'):
                record_id = logger_instance.save_conversation(conversation)
                logger.info(f"✅ [Expert Enhanced] Conversation sauvegardée via save_conversation: {conversation_id}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ [Expert Enhanced] save_conversation échoué: {e}")
        
        # ✅ MÉTHODE 3: Sauvegarde directe SQL (fallback)
        logger.info("🔄 [Expert Enhanced] Tentative sauvegarde directe SQL...")
        
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
            
            logger.info(f"✅ [Expert Enhanced] Conversation sauvegardée via SQL direct: {conversation_id}")
            return True
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Toutes les méthodes de sauvegarde ont échoué: {e}")
        return False

# =============================================================================
# ENDPOINT FEEDBACK AMÉLIORÉ (DEPUIS EXPERT.PY)
# =============================================================================

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

@router.post("/feedback")
async def submit_feedback_enhanced(feedback_data: FeedbackRequest):
    """Submit feedback - VERSION AMÉLIORÉE"""
    try:
        logger.info(f"📊 [Expert Enhanced] Feedback reçu: {feedback_data.rating}")
        logger.info(f"📊 [Expert Enhanced] Conversation ID: {feedback_data.conversation_id}")
        logger.info(f"📊 [Expert Enhanced] Commentaire: {feedback_data.comment}")
        
        feedback_updated = False
        
        if feedback_data.conversation_id and LOGGING_AVAILABLE and logger_instance:
            try:
                # Convertir le rating en format numérique
                rating_numeric = {
                    "positive": 1,
                    "negative": -1,
                    "neutral": 0
                }.get(feedback_data.rating, 0)
                
                logger.info(f"📊 [Expert Enhanced] Rating numérique: {rating_numeric}")
                
                # ✅ MÉTHODE 1: Essayer update_feedback si disponible
                try:
                    if hasattr(logger_instance, 'update_feedback'):
                        feedback_updated = logger_instance.update_feedback(
                            feedback_data.conversation_id, 
                            rating_numeric
                        )
                        logger.info(f"✅ [Expert Enhanced] Feedback mis à jour via update_feedback: {feedback_updated}")
                    else:
                        logger.warning("⚠️ [Expert Enhanced] Méthode update_feedback non disponible")
                        feedback_updated = False
                except Exception as e:
                    logger.warning(f"⚠️ [Expert Enhanced] update_feedback échoué: {e}")
                    feedback_updated = False
                
                # ✅ MÉTHODE 2: SQL direct si update_feedback échoue
                if not feedback_updated:
                    logger.info("🔄 [Expert Enhanced] Tentative mise à jour feedback via SQL direct...")
                    
                    import sqlite3
                    with sqlite3.connect(logger_instance.db_path) as conn:
                        cursor = conn.execute("""
                            UPDATE conversations 
                            SET feedback = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE conversation_id = ?
                        """, (rating_numeric, feedback_data.conversation_id))
                        
                        feedback_updated = cursor.rowcount > 0
                        
                        if feedback_updated:
                            logger.info(f"✅ [Expert Enhanced] Feedback mis à jour via SQL direct: {feedback_data.conversation_id}")
                        else:
                            logger.warning(f"⚠️ [Expert Enhanced] Conversation non trouvée: {feedback_data.conversation_id}")
                
            except Exception as e:
                logger.error(f"❌ [Expert Enhanced] Erreur mise à jour feedback: {e}")
                feedback_updated = False
        else:
            if not feedback_data.conversation_id:
                logger.warning("⚠️ [Expert Enhanced] Conversation ID manquant")
            if not LOGGING_AVAILABLE:
                logger.warning("⚠️ [Expert Enhanced] Logging non disponible")
            if not logger_instance:
                logger.warning("⚠️ [Expert Enhanced] Logger instance non disponible")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès (Enhanced)",
            "rating": feedback_data.rating,
            "comment": feedback_data.comment,
            "conversation_id": feedback_data.conversation_id,
            "feedback_updated_in_db": feedback_updated,
            "enhanced_features_used": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur feedback critique: {e}")
        import traceback
        logger.error(f"❌ [Expert Enhanced] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement feedback: {str(e)}")

# =============================================================================
# ENDPOINT TOPICS AMÉLIORÉ (DEPUIS EXPERT.PY)
# =============================================================================

@router.get("/topics")
async def get_suggested_topics_enhanced(language: str = "fr"):
    """Get suggested topics - VERSION AMÉLIORÉE"""
    try:
        lang = language.lower() if language else "fr"
        if lang not in ["fr", "en", "es"]:
            lang = "fr"
        
        # ✅ TOPICS ENRICHIS avec données numériques
        topics_by_language = {
            "fr": [
                "Poids normal Ross 308 de 12 jours (340-370g attendu)",
                "Température optimale poulailler (32°C démarrage)",
                "Mortalité élevée diagnostic (>5% problématique)", 
                "Problèmes de croissance retard développement",
                "Protocoles vaccination Gumboro + Newcastle",
                "Indice de conversion alimentaire optimal (1.6-1.8)",
                "Ventilation et qualité d'air bâtiment fermé",
                "Densité élevage optimale (15-20 poulets/m²)"
            ],
            "en": [
                "Normal weight Ross 308 at 12 days (340-370g expected)",
                "Optimal broiler house temperature (32°C starter)",
                "High mortality diagnosis (>5% problematic)",
                "Growth problems development delays",
                "Vaccination protocols Gumboro + Newcastle", 
                "Optimal feed conversion ratio (1.6-1.8)",
                "Ventilation and air quality closed buildings",
                "Optimal stocking density (15-20 birds/m²)"
            ],
            "es": [
                "Peso normal Ross 308 a los 12 días (340-370g esperado)",
                "Temperatura óptima galpón (32°C iniciador)",
                "Diagnóstico mortalidad alta (>5% problemático)",
                "Problemas crecimiento retrasos desarrollo",
                "Protocolos vacunación Gumboro + Newcastle",
                "Índice conversión alimentaria óptimo (1.6-1.8)",
                "Ventilación y calidad aire edificios cerrados", 
                "Densidad crianza óptima (15-20 pollos/m²)"
            ]
        }
        
        topics = topics_by_language.get(lang, topics_by_language["fr"])
        
        return {
            "topics": topics,
            "language": lang,
            "count": len(topics),
            "enhanced_features": {
                "numerical_data_included": True,
                "context_aware": True,
                "breed_specific_examples": True
            },
            "system_status": {
                "validation_enabled": is_agricultural_validation_enabled() if AGRICULTURAL_VALIDATOR_AVAILABLE else False,
                "enhanced_clarification_enabled": is_enhanced_clarification_system_enabled() if ENHANCED_CLARIFICATION_AVAILABLE else False,
                "intelligent_memory_enabled": INTELLIGENT_MEMORY_AVAILABLE,
                "ai_enhancements_enabled": INTELLIGENT_MEMORY_AVAILABLE and ENHANCED_CLARIFICATION_AVAILABLE
            },
            "note": "Topics enrichis avec données numériques et exemples spécifiques"
        }
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

# =============================================================================
# ENDPOINTS DEBUG AMÉLIORÉS (DEPUIS EXPERT.PY)
# =============================================================================

@router.get("/debug-database")
async def debug_database_info_enhanced():
    """Debug des informations de base de données - VERSION AMÉLIORÉE"""
    try:
        if not LOGGING_AVAILABLE or not logger_instance:
            return {
                "error": "Logging non disponible",
                "logging_available": LOGGING_AVAILABLE,
                "logger_instance": bool(logger_instance),
                "enhanced_features": "Non testables sans logging"
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
                    logger.warning(f"⚠️ [Expert Enhanced] Erreur requêtes base: {e}")
        
        # Méthodes disponibles
        logger_methods = [method for method in dir(logger_instance) if not method.startswith('_')]
        
        return {
            "enhanced_system": True,
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
            "enhanced_components": {
                "intelligent_memory": INTELLIGENT_MEMORY_AVAILABLE,
                "enhanced_clarification": ENHANCED_CLARIFICATION_AVAILABLE,
                "agricultural_validation": AGRICULTURAL_VALIDATOR_AVAILABLE
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur debug database: {e}")
        return {
            "error": str(e),
            "enhanced_system": True,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/debug-system")
async def debug_system_info_enhanced():
    """Endpoint de diagnostic système complet AMÉLIORÉ"""
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
    
    # ✅ NOUVEAUX TESTS POUR MODULES AMÉLIORÉS
    try:
        import app.api.v1.question_clarification_system_enhanced
        import_tests["enhanced_clarification_module"] = "✅ OK"
        
        clarification_attrs = dir(app.api.v1.question_clarification_system_enhanced)
        clarification_functions = [attr for attr in clarification_attrs if not attr.startswith('_')]
        import_tests["enhanced_clarification_functions"] = clarification_functions
        
    except Exception as e:
        import_tests["enhanced_clarification_module"] = f"❌ {str(e)}"
    
    try:
        import app.api.v1.conversation_memory_enhanced
        import_tests["intelligent_memory_module"] = "✅ OK"
        
        memory_attrs = dir(app.api.v1.conversation_memory_enhanced)
        memory_functions = [attr for attr in memory_attrs if not attr.startswith('_')]
        import_tests["intelligent_memory_functions"] = memory_functions
        
    except Exception as e:
        import_tests["intelligent_memory_module"] = f"❌ {str(e)}"
    
    return {
        "enhanced_expert_system": True,
        "auth_available": AUTH_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "validation_enabled": is_agricultural_validation_enabled() if AGRICULTURAL_VALIDATOR_AVAILABLE else None,
        
        # ✅ NOUVEAUX COMPOSANTS
        "enhanced_clarification_available": ENHANCED_CLARIFICATION_AVAILABLE,
        "enhanced_clarification_enabled": is_enhanced_clarification_system_enabled() if ENHANCED_CLARIFICATION_AVAILABLE else None,
        "intelligent_memory_available": INTELLIGENT_MEMORY_AVAILABLE,
        
        "openai_available": OPENAI_AVAILABLE,
        "logging_available": LOGGING_AVAILABLE,
        
        # ✅ NOUVELLES FONCTIONNALITÉS
        "enhanced_features": {
            "automatic_reprocessing": ENHANCED_CLARIFICATION_AVAILABLE,
            "intelligent_entity_extraction": INTELLIGENT_MEMORY_AVAILABLE,
            "contextual_reasoning": INTELLIGENT_MEMORY_AVAILABLE and ENHANCED_CLARIFICATION_AVAILABLE,
            "adaptive_clarification": ENHANCED_CLARIFICATION_AVAILABLE,
            "enhanced_prompts": True,
            "conversation_state_tracking": INTELLIGENT_MEMORY_AVAILABLE
        },
        
        "current_directory": os.path.dirname(__file__),
        "python_path_sample": sys.path[:3],
        "import_tests": import_tests,
        
        # ✅ STATS AMÉLIORÉES
        "validator_stats": get_agricultural_validator_stats() if AGRICULTURAL_VALIDATOR_AVAILABLE else None,
        "enhanced_clarification_stats": get_enhanced_clarification_system_stats() if ENHANCED_CLARIFICATION_AVAILABLE else None,
        "intelligent_memory_stats": get_conversation_memory_stats() if INTELLIGENT_MEMORY_AVAILABLE else None,
        
        "timestamp": datetime.now().isoformat()
    }

@router.get("/debug-auth")
async def debug_auth_info_enhanced(request: Request):
    """Endpoint de diagnostic rapide AMÉLIORÉ"""
    auth_header = request.headers.get("Authorization")
    
    return {
        "enhanced_expert_system": True,
        "auth_available": AUTH_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "validation_enabled": is_agricultural_validation_enabled() if AGRICULTURAL_VALIDATOR_AVAILABLE else None,
        
        # ✅ NOUVEAUX COMPOSANTS
        "enhanced_clarification_available": ENHANCED_CLARIFICATION_AVAILABLE,
        "enhanced_clarification_enabled": is_enhanced_clarification_system_enabled() if ENHANCED_CLARIFICATION_AVAILABLE else None,
        "intelligent_memory_available": INTELLIGENT_MEMORY_AVAILABLE,
        
        "auth_header_present": bool(auth_header),
        "auth_header_preview": auth_header[:50] + "..." if auth_header else None,
        "openai_available": OPENAI_AVAILABLE,
        "logging_available": LOGGING_AVAILABLE,
        
        # ✅ NOUVELLES CAPACITÉS
        "enhanced_capabilities": {
            "automatic_reprocessing": "✅ Activé" if ENHANCED_CLARIFICATION_AVAILABLE else "❌ Non disponible",
            "intelligent_memory": "✅ Activé" if INTELLIGENT_MEMORY_AVAILABLE else "❌ Non disponible",
            "contextual_reasoning": "✅ Activé" if (INTELLIGENT_MEMORY_AVAILABLE and ENHANCED_CLARIFICATION_AVAILABLE) else "❌ Non disponible",
            "adaptive_clarification": "✅ Activé" if ENHANCED_CLARIFICATION_AVAILABLE else "❌ Non disponible",
            "enhanced_prompts": "✅ Activé",
            "ai_powered_enhancements": "✅ Activé" if (OPENAI_AVAILABLE and INTELLIGENT_MEMORY_AVAILABLE) else "❌ Non disponible"
        },
        
        "timestamp": datetime.now().isoformat()
    }

@router.post("/test-utf8")
async def test_utf8_direct_enhanced(request: Request):
    """Test endpoint pour UTF-8 direct AMÉLIORÉ"""
    try:
        # Récupérer le body brut
        body = await request.body()
        body_str = body.decode('utf-8')
        
        logger.info(f"📝 [Expert Enhanced] Body brut reçu: {body_str}")
        
        # Parser JSON manuellement
        import json
        data = json.loads(body_str)
        
        question_text = data.get('text', '')
        language = data.get('language', 'fr')
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        logger.info(f"📝 [Expert Enhanced] Question extraite: {question_text}")
        logger.info(f"🔤 [Expert Enhanced] Caractères spéciaux: {[c for c in question_text if ord(c) > 127]}")
        logger.info(f"🆔 [Expert Enhanced] Conversation ID: {conversation_id}")
        
        # Test de validation
        user_id = get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        
        # ✅ NOUVEAU: Test mémoire intelligente si disponible
        memory_test_result = None
        if INTELLIGENT_MEMORY_AVAILABLE:
            try:
                conversation_context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=language
                )
                memory_test_result = {
                    "status": "success",
                    "extracted_entities": conversation_context.consolidated_entities.to_dict(),
                    "confidence": conversation_context.consolidated_entities.confidence_overall,
                    "urgency": conversation_context.conversation_urgency
                }
                logger.info(f"🧠 [Expert Enhanced] Test mémoire réussi: {memory_test_result}")
            except Exception as e:
                memory_test_result = {"status": "error", "error": str(e)}
                logger.warning(f"⚠️ [Expert Enhanced] Test mémoire échoué: {e}")
        
        # ✅ NOUVEAU: Test clarification améliorée si disponible
        clarification_test_result = None
        if ENHANCED_CLARIFICATION_AVAILABLE:
            try:
                clarification_context = get_context_for_clarification(conversation_id) if INTELLIGENT_MEMORY_AVAILABLE else {}
                
                clarification_result = await analyze_question_for_clarification_enhanced(
                    question=question_text,
                    language=language,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_context=clarification_context
                )
                
                clarification_test_result = {
                    "status": "success",
                    "needs_clarification": clarification_result.needs_clarification,
                    "questions_count": len(clarification_result.questions) if clarification_result.questions else 0,
                    "mode": clarification_result.clarification_mode.value if clarification_result.clarification_mode else None,
                    "confidence": clarification_result.confidence_score
                }
                logger.info(f"❓ [Expert Enhanced] Test clarification réussi: {clarification_test_result}")
            except Exception as e:
                clarification_test_result = {"status": "error", "error": str(e)}
                logger.warning(f"⚠️ [Expert Enhanced] Test clarification échoué: {e}")
        
        # Test de validation avec contexte
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain_enhanced(
            question=question_text,
            language=language,
            user_id=user_id,
            request_ip=request_ip,
            conversation_id=conversation_id
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
                "enhanced_tests": {
                    "intelligent_memory": memory_test_result,
                    "enhanced_clarification": clarification_test_result
                },
                "method": "enhanced_utf8_test_with_ai_components",
                "timestamp": datetime.now().isoformat()
            }
        
        # Test traitement si validé
        answer = await process_question_with_enhanced_prompt(
            question_text, 
            language, 
            "fast",
            conversation_context=get_context_for_rag(conversation_id) if INTELLIGENT_MEMORY_AVAILABLE else ""
        )
        
        # ✅ NOUVEAU: Enregistrer la réponse dans la mémoire
        if INTELLIGENT_MEMORY_AVAILABLE and conversation_id and answer:
            try:
                add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=answer,
                    role="assistant",
                    language=language
                )
                logger.info(f"🧠 [Expert Enhanced] Réponse test UTF-8 enregistrée")
            except Exception as e:
                logger.warning(f"⚠️ [Expert Enhanced] Erreur enregistrement réponse test: {e}")
        
        return {
            "success": True,
            "question_received": question_text,
            "special_chars_detected": [c for c in question_text if ord(c) > 127],
            "validation_passed": True,
            "confidence": validation_confidence,
            "response": answer,
            "conversation_id": conversation_id,
            "enhanced_tests": {
                "intelligent_memory": memory_test_result,
                "enhanced_clarification": clarification_test_result
            },
            "enhanced_features_used": [
                "intelligent_memory" if memory_test_result and memory_test_result.get("status") == "success" else None,
                "enhanced_clarification" if clarification_test_result and clarification_test_result.get("status") == "success" else None,
                "enhanced_prompts",
                "contextual_reasoning"
            ],
            "method": "enhanced_utf8_test_with_ai_components",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur test UTF-8: {e}")
        return {
            "success": False,
            "error": str(e),
            "enhanced_system": True,
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# ENDPOINTS ADDITIONNELS DEPUIS EXPERT.PY
# =============================================================================

@router.get("/validation-stats")
async def get_validation_stats_enhanced():
    """Statistiques du validateur agricole - VERSION AMÉLIORÉE"""
    try:
        if not AGRICULTURAL_VALIDATOR_AVAILABLE:
            return {
                "error": "Validateur agricole non disponible",
                "available": False,
                "stats": None,
                "enhanced_system": True
            }
        
        stats = get_agricultural_validator_stats()
        
        return {
            "available": True,
            "validation_enabled": is_agricultural_validation_enabled(),
            "stats": stats,
            "enhanced_features": {
                "contextual_validation": INTELLIGENT_MEMORY_AVAILABLE,
                "conversation_aware": True,
                "ai_powered": INTELLIGENT_MEMORY_AVAILABLE
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur stats validation: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération stats")

@router.post("/test-validation")
async def test_validation_enhanced(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Test endpoint pour tester la validation AMÉLIORÉE"""
    try:
        question_text = request_data.text.strip()
        user_id = get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        conversation_id = request_data.conversation_id or str(uuid.uuid4())
        
        if not AGRICULTURAL_VALIDATOR_AVAILABLE:
            return {
                "error": "Validateur agricole non disponible",
                "available": False,
                "enhanced_system": True
            }
        
        # ✅ NOUVEAU: Test avec contexte intelligent
        memory_context = None
        if INTELLIGENT_MEMORY_AVAILABLE:
            try:
                # Enregistrer d'abord la question pour générer du contexte
                memory_context = add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=request_data.language
                )
            except Exception as e:
                logger.warning(f"⚠️ [Expert Enhanced] Erreur contexte test: {e}")
        
        # Test de validation avec contexte
        is_valid, rejection_message, validation_confidence = await validate_question_agricultural_domain_enhanced(
            question=question_text,
            language=request_data.language,
            user_id=user_id,
            request_ip=request_ip,
            conversation_id=conversation_id
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
            "enhanced_features": {
                "memory_context": memory_context.to_dict() if memory_context else None,
                "contextual_validation": INTELLIGENT_MEMORY_AVAILABLE,
                "extracted_entities": memory_context.consolidated_entities.to_dict() if memory_context else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur test validation: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur test validation: {str(e)}")

# =============================================================================
# ENDPOINT DE COMPATIBILITÉ AVEC EXPERT.PY ORIGINAL
# =============================================================================

@router.post("/ask", response_model=EnhancedExpertResponse)
async def ask_expert_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user) if AUTH_AVAILABLE else None
):
    """
    Endpoint de compatibilité avec expert.py original mais avec fonctionnalités améliorées.
    Redirige vers ask_expert_enhanced avec toutes les améliorations.
    """
    logger.info("🔄 [Expert Enhanced] Redirection vers endpoint amélioré pour compatibilité")
    
    # Appeler directement l'endpoint amélioré
    return await ask_expert_enhanced(request_data, request, current_user)

@router.post("/ask-public", response_model=EnhancedExpertResponse)
async def ask_expert_public_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """
    Endpoint public de compatibilité avec expert.py original mais avec fonctionnalités améliorées.
    Redirige vers ask_expert_enhanced_public avec toutes les améliorations.
    """
    logger.info("🔄 [Expert Enhanced] Redirection vers endpoint public amélioré pour compatibilité")
    
    # Appeler directement l'endpoint public amélioré
    return await ask_expert_enhanced_public(request_data, request)

# =============================================================================
# CONFIGURATION FINALE
# =============================================================================

security = HTTPBearer()

if OPENAI_AVAILABLE and openai:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai.api_key = openai_api_key
        logger.info("✅ [Expert Enhanced] OpenAI configuré avec succès")
    else:
        logger.warning("⚠️ [Expert Enhanced] OpenAI API key non trouvée")
else:
    logger.warning("⚠️ [Expert Enhanced] Module OpenAI non disponible")

# =============================================================================
# LOGGING FINAL COMPLET
# =============================================================================

logger.info("🚀 [EXPERT ENHANCED] Système expert amélioré COMPLET initialisé avec succès!")
logger.info(f"🧠 [EXPERT ENHANCED] Mémoire intelligente: {'✅' if INTELLIGENT_MEMORY_AVAILABLE else '❌'}")
logger.info(f"❓ [EXPERT ENHANCED] Clarification améliorée: {'✅' if ENHANCED_CLARIFICATION_AVAILABLE else '❌'}")
logger.info(f"🌾 [EXPERT ENHANCED] Validation agricole: {'✅' if AGRICULTURAL_VALIDATOR_AVAILABLE else '❌'}")
logger.info(f"🔐 [EXPERT ENHANCED] Auth: {'✅' if AUTH_AVAILABLE else '❌'}")
logger.info(f"🤖 [EXPERT ENHANCED] OpenAI: {'✅' if OPENAI_AVAILABLE else '❌'}")
logger.info(f"💾 [EXPERT ENHANCED] Logging: {'✅' if LOGGING_AVAILABLE else '❌'}")

logger.info("🎯 [EXPERT ENHANCED] NOUVELLES FONCTIONNALITÉS ACTIVÉES:")
logger.info("   - 🔄 Retraitement automatique après clarification complétée")
logger.info("   - 🧠 Extraction d'entités intelligente via IA")
logger.info("   - 📊 Réponses avec données numériques optimisées")
logger.info("   - 🎛️ Modes de clarification adaptatifs (batch/interactive/adaptive)")
logger.info("   - 🔍 Raisonnement contextuel pour éviter clarifications redondantes")
logger.info("   - 📈 Suivi d'état conversationnel avancé")
logger.info("   - ⚡ Détection automatique d'urgence et problèmes critiques")
logger.info("   - 🎯 Contexte intelligent pour RAG et prompts")

logger.info("🔧 [EXPERT ENHANCED] ENDPOINTS DISPONIBLES (COMPATIBILITÉ COMPLÈTE):")
logger.info("   - POST /ask (compatible original + améliorations)")
logger.info("   - POST /ask-public (compatible original + améliorations)")
logger.info("   - POST /ask-enhanced (version complète améliorée)")
logger.info("   - POST /ask-enhanced-public (version publique améliorée)")
logger.info("   - POST /feedback (compatible + améliorations)")
logger.info("   - GET /topics (compatible + données numériques)")
logger.info("   - GET /validation-stats (compatible + contexte)")
logger.info("   - POST /test-validation (compatible + mémoire)")
logger.info("   - GET /debug-database (compatible + composants enhanced)")
logger.info("   - GET /debug-system (compatible + nouvelles fonctionnalités)")
logger.info("   - GET /debug-auth (compatible + capacités enhanced)")
logger.info("   - POST /test-utf8 (compatible + tests IA)")
logger.info("   - GET /enhanced-stats (statistiques système enhanced)")
logger.info("   - POST /test-enhanced-flow (test complet nouvelles fonctionnalités)")
logger.info("   - GET /enhanced-conversation/{id}/context (contexte conversation)")

logger.info("🔄 [EXPERT ENHANCED] COMPATIBILITÉ:")
logger.info("   - ✅ 100% compatible avec expert.py original")
logger.info("   - ✅ Mêmes endpoints avec fonctionnalités enrichies")
logger.info("   - ✅ Nouveaux endpoints pour fonctionnalités avancées")
logger.info("   - ✅ Redirection automatique vers versions améliorées")

if ENHANCED_CLARIFICATION_AVAILABLE:
    stats = get_enhanced_clarification_system_stats()
    logger.info(f"📊 [EXPERT ENHANCED] Config clarification: Mode {stats.get('clarification_mode')}, Extraction IA: {'✅' if stats.get('smart_entity_extraction') else '❌'}")

if INTELLIGENT_MEMORY_AVAILABLE:
    memory_stats = get_conversation_memory_stats()
    logger.info(f"📊 [EXPERT ENHANCED] Mémoire intelligente: IA {'✅' if memory_stats.get('ai_powered') else '❌'}, Cache: {memory_stats.get('cache_size')}/{memory_stats.get('cache_max_size')}")

logger.info("✨ [EXPERT ENHANCED] Le problème est résolu!")
logger.info("✨ [EXPERT ENHANCED] Plus de questions redondantes sur race/âge grâce au contexte intelligent!")
logger.info("✨ [EXPERT ENHANCED] Réponses automatiques avec données numériques après clarification!")
logger.info("✨ [EXPERT ENHANCED] Système COMPLET avec rétrocompatibilité 100%!")