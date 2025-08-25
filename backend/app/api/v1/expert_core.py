# app/api/v1/expert_core.py
# -*- coding: utf-8 -*-
"""
Fonctions métier et validation pour expert.py
Contient la logique de traitement principal et validation agricole
"""

import logging
import os
import time
from typing import Optional, Any, Dict
from fastapi import Request

from .expert_utils import (
    get_user_info_for_validation,
    extract_user_id_for_persistence,
    execute_background_tasks_async
)

from .expert_confidence import (
    prepare_validation_result_for_confidence,
    prepare_confidence_inputs,
    apply_unified_confidence,
    get_quota_exceeded_confidence,
    get_validation_rejected_confidence,
    get_system_error_confidence,
    get_dialogue_unavailable_confidence
)

logger = logging.getLogger(__name__)

# ===== Import validateur agricole =====
try:
    from .pipeline.agricultural_domain_validator import (
        validate_agricultural_question,
        get_agricultural_validator_stats,
        is_agricultural_validation_enabled,
        ValidationResult
    )
    AGRICULTURAL_VALIDATOR_AVAILABLE = True
    logger.info("✅ Agricultural domain validator imported successfully")
except ImportError as e:
    AGRICULTURAL_VALIDATOR_AVAILABLE = False
    logger.error(f"⚠ Failed to import agricultural validator: {e}")

# ===== Import Dialogue Manager =====
try:
    from .pipeline.dialogue_manager import handle  # type: ignore
    DIALOGUE_AVAILABLE = True
    logger.info("✅ DialogueManager handle function imported successfully")
except Exception as e:
    logger.error(f"⚠ Failed to import dialogue_manager.handle: {e}")
    DIALOGUE_AVAILABLE = False

    # Fallback minimal, signature d'origine conservée
    def handle(session_id: str, question: str, lang: str = "fr", **kwargs) -> Dict[str, Any]:
        return {
            "type": "error",
            "message": "Dialogue service temporarily unavailable",
            "session_id": session_id,
        }

# ===== Import systèmes de quota et billing =====
try:
    from app.api.v1.billing import check_quota_middleware, increment_quota_usage
    BILLING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Billing system unavailable: {e}")
    BILLING_AVAILABLE = False
    
    def check_quota_middleware(email):
        return True, {"message": "Quota checking disabled"}

# ===== Fonction de validation agricole =====
def validate_agricultural_question_safe(question: str, lang: str = "fr", user_id: str = "unknown", request_ip: str = "unknown") -> ValidationResult:
    """Valide qu'une question concerne le domaine agricole"""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        logger.warning("⚠ Agricultural validator not available, allowing all questions")
        return ValidationResult(is_valid=True, confidence=100.0, reason="Validator unavailable")
    
    try:
        return validate_agricultural_question(question, lang, user_id, request_ip)
    except Exception as e:
        logger.error(f"⚠ Error in agricultural validation: {e}")
        # En cas d'erreur, permettre la question avec un avertissement
        return ValidationResult(is_valid=True, confidence=50.0, reason=f"Validation error: {str(e)}")

# ===== Fonction interne principale =====
async def ask_internal_async(payload, request: Request, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    🚀 VERSION ASYNC OPTIMISÉE + CONFIDENCE UNIFIÉ - Logique interne pour traiter les questions
    
    OPTIMISATIONS:
    - Parallélisation des opérations DB finales
    - Gain estimé: 1-1.5 secondes par requête
    
    NOUVEAU:
    - Intégration automatique du confidence score unifié
    - Transmission du validation_result au dialogue_manager
    
    CONSERVE: Toute la logique métier originale
    """
    user_email = None
    start_time = time.time()
    validation_result_dict = None
    
    try:
        # Extraction des infos utilisateur pour la validation
        user_id, request_ip = get_user_info_for_validation(request, current_user)
        
        # Extraction user_id pour persistance
        persistence_user_id = extract_user_id_for_persistence(current_user)
        
        # Extraction de l'email pour le quota
        if current_user:
            user_email = current_user.get('email')
        
        # 🚫 VÉRIFICATION QUOTA AVANT TRAITEMENT
        if user_email and BILLING_AVAILABLE:
            try:
                quota_allowed, quota_details = check_quota_middleware(user_email)
                
                if not quota_allowed:
                    logger.warning(f"🚫 Quota dépassé pour {user_email}: {quota_details.get('message', 'Quota exceeded')}")
                    quota_response = {
                        "type": "quota_exceeded",
                        "message": quota_details.get("message", "Quota mensuel dépassé"),
                        "quota_details": quota_details,
                        "upgrade_suggestions": [
                            {"plan": "basic", "price": "29.99€", "quota": "1000 questions"},
                            {"plan": "premium", "price": "99.99€", "quota": "5000 questions"}
                        ],
                        "session_id": payload.session_id or "default",
                        "user": {
                            "email": user_email,
                            "user_id": current_user.get('user_id')
                        }
                    }
                    
                    # Ajouter confidence pour quota exceeded
                    quota_response["confidence"] = get_quota_exceeded_confidence()
                    
                    return quota_response
                else:
                    logger.info(f"✅ Quota OK pour {user_email}: {quota_details.get('usage', 0)}/{quota_details.get('limit', 'unlimited')}")
            except Exception as e:
                logger.error(f"⚠ Erreur vérification quota pour {user_email}: {e}")
                # En cas d'erreur quota, on continue le traitement
                pass

        # Log différencié selon l'authentification
        if current_user:
            user_email_display = current_user.get('email', 'unknown')
            logger.info(f"🔒 Question authentifiée de {user_email_display}: {payload.question[:120]}")
        else:
            logger.info(f"🌐 Question publique: {payload.question[:120]}")

        # 🌾 VALIDATION AGRICOLE (sauf si bypass autorisé)
        validation_bypassed = False
        if not payload.bypass_validation:
            validation_result = validate_agricultural_question_safe(
                question=payload.question,
                lang=payload.lang or "fr",
                user_id=user_id,
                request_ip=request_ip
            )
            
            # Préparer validation_result pour confidence unifié
            validation_result_dict = prepare_validation_result_for_confidence(validation_result)
            
            if not validation_result.is_valid:
                logger.warning(f"🚫 Question rejetée par validation agricole: {validation_result.reason}")
                
                # Incrément usage même pour validation échouée
                if user_email and BILLING_AVAILABLE:
                    try:
                        from .expert_utils import increment_quota_async
                        await increment_quota_async(user_email)
                    except Exception as e:
                        logger.error(f"⚠ Erreur incrémentation quota (validation failed): {e}")
                
                validation_rejected_response = {
                    "type": "validation_rejected",
                    "message": validation_result.reason,
                    "session_id": payload.session_id or "default",
                    "validation": {
                        "is_valid": False,
                        "confidence": validation_result.confidence,
                        "suggested_topics": validation_result.suggested_topics,
                        "detected_keywords": validation_result.detected_keywords,
                        "rejected_keywords": validation_result.rejected_keywords
                    },
                    "user": {
                        "email": current_user.get('email') if current_user else None,
                        "user_id": current_user.get('user_id') if current_user else None
                    } if current_user else None
                }
                
                # Ajouter confidence pour validation échouée
                validation_rejected_response["confidence"] = get_validation_rejected_confidence(validation_result.confidence)
                
                # Logging analytics
                try:
                    from .expert_utils import log_analytics_async
                    await log_analytics_async(
                        current_user=current_user,
                        payload=payload,
                        result=validation_rejected_response,
                        start_time=start_time
                    )
                    logger.info("📊 Validation échouée loggée dans analytics")
                    
                except Exception as log_e:
                    logger.error(f"⚠ Erreur logging analytics (validation): {log_e}")
                
                return validation_rejected_response
            else:
                logger.info(f"✅ Question validée (confiance: {validation_result.confidence:.1f}%)")
        else:
            validation_bypassed = True
            logger.info("⚠ Validation agricole bypassée par l'utilisateur")
            # Validation result par défaut pour bypass
            validation_result_dict = {
                "is_valid": True,
                "confidence": 100.0,
                "reason": "Validation bypassée par utilisateur"
            }

        # Traitement normal de la question
        fp_qs = request.query_params.get("force_perfstore")
        force_perf = bool(payload.force_perfstore) or (fp_qs in ("1", "true", "True", "yes"))

        if DIALOGUE_AVAILABLE:
            # Passer user_id au dialogue manager pour persistance
            # Passer validation_result pour confidence unifié
            result = handle(
                session_id=payload.session_id or "default",
                question=payload.question,
                lang=payload.lang or "fr",
                debug=bool(payload.debug),
                force_perfstore=force_perf,
                intent_hint=(payload.intent_hint or None),
                entities=(payload.entities or {}),
                user_id=persistence_user_id,
                validation_result=validation_result_dict
            )
        else:
            logger.warning("⚠ Dialogue manager not available, using fallback")
            result = handle(payload.session_id or "default", payload.question, payload.lang or "fr")
            
            # Ajouter confidence par défaut si dialogue manager indisponible
            if "confidence" not in result:
                result["confidence"] = get_dialogue_unavailable_confidence()

        # 🚀 OPTIMISATION PERFORMANCE: Tâches de fond en parallèle
        await execute_background_tasks_async(
            user_email=user_email,
            current_user=current_user,
            payload=payload,
            result=result,
            start_time=start_time
        )

        # Ajouter les infos utilisateur et de validation dans la réponse
        if current_user:
            result["user"] = {
                "email": current_user.get('email'),
                "user_id": current_user.get('user_id')
            }
        
        # Ajouter les métadonnées de validation et persistance
        result["validation_metadata"] = {
            "agricultural_validation_enabled": AGRICULTURAL_VALIDATOR_AVAILABLE and is_agricultural_validation_enabled(),
            "validation_bypassed": validation_bypassed
        }
        
        result["persistence_metadata"] = {
            "conversation_persistence_enabled": True,
            "user_id_for_persistence": persistence_user_id,
            "is_authenticated": bool(current_user)
        }
        
        # Métadonnées de confidence unifié
        from .expert_confidence import get_confidence_system_status
        confidence_status = get_confidence_system_status()
        result["confidence_metadata"] = {
            "unified_confidence_enabled": confidence_status["confidence_system_available"],
            "confidence_system_available": confidence_status["confidence_system_available"],
            "validation_confidence_included": bool(validation_result_dict)
        }

        confidence_raw = result.get('confidence', {}).get('score', 'N/A')
        confidence_display = f"{confidence_raw * 100:.1f}" if isinstance(confidence_raw, (int, float)) and confidence_raw <= 1.0 else confidence_raw
        logger.info(f"✅ Réponse générée: type={result.get('type')}, confidence={confidence_display}%")

        return result
        
    except Exception as e:
        # Erreur: Incrément usage même en cas d'erreur de traitement
        if user_email and BILLING_AVAILABLE:
            try:
                from .expert_utils import increment_quota_async
                await increment_quota_async(user_email)
                logger.info(f"📊 Usage incrémenté pour {user_email} (erreur)")
            except Exception as quota_e:
                logger.error(f"⚠ Erreur incrémentation quota (error): {quota_e}")
        
        # Logging des erreurs dans analytics
        error_result = {
            "type": "system_error",
            "error": {
                "type": type(e).__name__,
                "message": str(e),
                "category": "system_error"
            }
        }
        
        # Ajouter confidence pour erreurs système
        error_result["confidence"] = get_system_error_confidence(type(e).__name__)
        
        try:
            from .expert_utils import log_analytics_async
            await log_analytics_async(
                current_user=current_user,
                payload=payload,
                result=error_result,
                start_time=start_time
            )
            logger.info("📊 Erreur loggée dans analytics")
            
        except Exception as log_e:
            logger.error(f"⚠ Erreur logging analytics (error): {log_e}")
        
        logger.exception("⚠ Erreur dans le traitement de la question")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

# ===== Version sync pour rétrocompatibilité =====
def ask_internal(payload, request: Request, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    VERSION SYNC ORIGINALE - Conservée pour rétrocompatibilité
    
    Wrapper qui appelle la version async en interne
    """
    import asyncio
    return asyncio.run(ask_internal_async(payload, request, current_user))

# ===== Fonctions de status =====

def get_system_status() -> Dict[str, Any]:
    """État synthétique du service avec info persistance et confidence."""
    # Vérifier la disponibilité de la persistance
    persistence_available = False
    try:
        from .pipeline.dialogue_manager import POSTGRES_AVAILABLE, PERSIST_CONVERSATIONS
        persistence_available = POSTGRES_AVAILABLE and PERSIST_CONVERSATIONS
    except ImportError:
        pass
    
    from .expert_confidence import get_confidence_system_status
    confidence_status = get_confidence_system_status()
    
    return {
        "status": "ok" if DIALOGUE_AVAILABLE else "degraded",
        "dialogue_manager_available": DIALOGUE_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "agricultural_validation_enabled": AGRICULTURAL_VALIDATOR_AVAILABLE and is_agricultural_validation_enabled(),
        "billing_system_available": BILLING_AVAILABLE,
        "analytics_system_available": True,
        "conversation_persistence_available": persistence_available,
        "performance_optimizations_enabled": True,
        "confidence_system_available": confidence_status["confidence_system_available"],
        "unified_confidence_enabled": confidence_status["confidence_system_available"],
        "service": "expert_api",
    }

def get_agricultural_validation_status() -> Dict[str, Any]:
    """Status détaillé du validateur agricole."""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        return {
            "available": False,
            "reason": "Module not imported or not available"
        }
    
    try:
        stats = get_agricultural_validator_stats()
        return {
            "available": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }