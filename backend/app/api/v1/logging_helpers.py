# app/api/v1/logging_helpers.py
# -*- coding: utf-8 -*-
"""
🔧 FONCTIONS HELPER ET SINGLETON POUR LE SYSTÈME DE LOGGING
🚀 Gestionnaire singleton, fonctions d'aide pour l'intégration avec main.py et expert.py
"""
import os
import logging
import threading
from typing import Dict, Any, Optional

from .logging_manager import LoggingManager
AnalyticsManager = LoggingManager  # Alias pour compatibilité

from .logging_cache import clear_analytics_cache, get_cache_stats

logger = logging.getLogger(__name__)

# 🔒 Singleton sécurisé
_analytics_manager = None
_initialization_lock = threading.Lock()


def get_analytics_manager(force_init=None) -> AnalyticsManager:
    """
    🚀 SINGLETON SÉCURISÉ - Version améliorée
    - force_init=None : Utilise les variables d'environnement
    - force_init=True : Force l'initialisation (admin/tests)
    - force_init=False : Pas d'initialisation automatique
    """
    global _analytics_manager
    
    if _analytics_manager is None:
        with _initialization_lock:
            # Double vérification avec lock
            if _analytics_manager is None:
                logger.info("🔧 Création du gestionnaire analytics...")
                _analytics_manager = AnalyticsManager(auto_init=force_init)
                logger.info("✅ Gestionnaire analytics créé")
    
    return _analytics_manager


def reset_analytics_manager():
    """🆕 NOUVELLE FONCTION - Reset pour tests/redémarrage"""
    global _analytics_manager
    with _initialization_lock:
        _analytics_manager = None
        clear_analytics_cache()
        logger.info("🔄 Gestionnaire analytics reset")


def get_analytics():
    """Fonction analytics pour compatibilité avec main.py"""
    try:
        analytics = get_analytics_manager()
        return {
            "status": "analytics_available",
            "tables_created": True,
            "dsn_configured": bool(analytics.dsn),
            "cache_enabled": True,
            "cache_entries": get_cache_stats()["total_entries"]
        }
    except Exception as e:
        return {
            "status": "analytics_error",
            "error": str(e)
        }


def log_server_performance(**kwargs) -> None:
    """Fonction helper pour logger les performances serveur depuis main.py"""
    try:
        analytics = get_analytics_manager()
        analytics.log_server_performance(**kwargs)
    except Exception as e:
        logger.error(f"⛔ Erreur log server performance helper: {e}")


def get_server_analytics(hours: int = 24) -> Dict[str, Any]:
    """Fonction helper pour récupérer les analytics serveur depuis main.py"""
    try:
        analytics = get_analytics_manager()
        return analytics.get_server_performance_analytics(hours)
    except Exception as e:
        logger.error(f"⛔ Erreur get server analytics: {e}")
        return {"error": str(e)}


def log_question_to_analytics(
    current_user: Optional[Dict[str, Any]],
    payload: Any,
    result: Dict[str, Any],
    response_text: str = "",
    processing_time_ms: int = 0,
    error_info: Dict[str, Any] = None
) -> None:
    """Fonction helper pour logger depuis expert.py"""
    try:
        analytics = get_analytics_manager()
        
        user_email = current_user.get('email') if current_user else None
        session_id = getattr(payload, 'session_id', 'unknown')
        question = getattr(payload, 'question', '')
        
        # Déterminer la source et le statut
        if error_info:
            status = "error"
            source = "error"
        elif result.get("type") == "quota_exceeded":
            status = "quota_exceeded"
            source = "quota_exceeded"
        elif result.get("type") == "validation_rejected":
            status = "validation_rejected" 
            source = "validation_rejected"
        else:
            status = "success"
            answer = result.get("answer", {})
            source = answer.get("source", "unknown")
        
        analytics.log_question_response(
            user_email=user_email,
            session_id=session_id,
            question=question,
            response_text=response_text,
            response_source=source,
            status=status,
            processing_time_ms=processing_time_ms,
            confidence=result.get("confidence"),
            entities=getattr(payload, 'entities', {}),
            error_info=error_info
        )
        
    except Exception as e:
        logger.error(f"⛔ Erreur log question to analytics: {e}")


def track_openai_call(
    user_email: str = None,
    session_id: str = None,
    question_id: str = None,
    call_type: str = "completion",
    model: str = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    purpose: str = "fallback",
    response_time_ms: int = 0,
    success: bool = True
) -> None:
    """Fonction helper pour tracker les appels OpenAI"""
    try:
        analytics = get_analytics_manager()
        analytics.track_openai_call(
            user_email=user_email,
            session_id=session_id,
            question_id=question_id,
            call_type=call_type,
            model=model or os.getenv('DEFAULT_MODEL', 'gpt-5'),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            purpose=purpose,
            response_time_ms=response_time_ms,
            success=success
        )
    except Exception as e:
        logger.error(f"⛔ Erreur track OpenAI call: {e}")