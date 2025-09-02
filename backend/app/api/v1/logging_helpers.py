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
    🚀 SINGLETON SÉCURISÉ - Version corrigée avec DATABASE_URL
    CORRECTION: Utilise DATABASE_URL au lieu de localhost par défaut
    """
    global _analytics_manager
    
    if _analytics_manager is None:
        with _initialization_lock:
            # Double vérification avec lock
            if _analytics_manager is None:
                logger.info("🔧 Création du gestionnaire analytics...")
                
                # CORRECTION CRITIQUE: Configuration avec DATABASE_URL
                database_url = os.getenv("DATABASE_URL")
                
                if database_url:
                    # Utiliser DATABASE_URL de Digital Ocean
                    try:
                        import psycopg2
                        db_config = psycopg2.extensions.parse_dsn(database_url)
                        logger.info("✅ Configuration PostgreSQL depuis DATABASE_URL")
                    except Exception as e:
                        logger.error(f"❌ Erreur parsing DATABASE_URL: {e}")
                        # Fallback vers config manuelle
                        db_config = {
                            "host": os.getenv("POSTGRES_HOST", "localhost"),
                            "port": int(os.getenv("POSTGRES_PORT", 5432)),
                            "database": os.getenv("POSTGRES_DB", "postgres"),
                            "user": os.getenv("POSTGRES_USER", "postgres"),
                            "password": os.getenv("POSTGRES_PASSWORD", "")
                        }
                        logger.warning("⚠️ Utilisation config fallback PostgreSQL")
                else:
                    # Configuration par défaut (développement)
                    db_config = {
                        "host": os.getenv("POSTGRES_HOST", "localhost"),
                        "port": int(os.getenv("POSTGRES_PORT", 5432)),
                        "database": os.getenv("POSTGRES_DB", "postgres"),
                        "user": os.getenv("POSTGRES_USER", "postgres"),
                        "password": os.getenv("POSTGRES_PASSWORD", "")
                    }
                    logger.warning("⚠️ DATABASE_URL manquante, utilisation config par défaut")
                
                # Créer le manager avec la bonne configuration
                _analytics_manager = AnalyticsManager(db_config)
                logger.info("✅ Gestionnaire analytics créé avec configuration corrigée")
    
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
            "dsn_configured": bool(getattr(analytics, 'db_config', None)),
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
        if hasattr(analytics, 'log_server_performance'):
            analytics.log_server_performance(**kwargs)
        else:
            logger.warning("⚠️ log_server_performance non disponible sur analytics manager")
    except Exception as e:
        logger.error(f"⛔ Erreur log server performance helper: {e}")


def get_server_analytics(hours: int = 24) -> Dict[str, Any]:
    """Fonction helper pour récupérer les analytics serveur depuis main.py"""
    try:
        analytics = get_analytics_manager()
        if hasattr(analytics, 'get_server_performance_analytics'):
            return analytics.get_server_performance_analytics(hours)
        else:
            logger.warning("⚠️ get_server_performance_analytics non disponible")
            return {"error": "Method not available"}
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
    """Fonction helper pour logger depuis expert.py - VERSION CORRIGÉE"""
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
        
        # Extraire la confidence correctement
        confidence = None
        confidence_data = result.get("confidence", {})
        if isinstance(confidence_data, dict):
            confidence = confidence_data.get("score")
        elif isinstance(confidence_data, (int, float)):
            confidence = confidence_data
        
        # Appel avec tous les paramètres requis
        analytics.log_question_response(
            user_email=user_email,
            session_id=session_id,
            question_id=f"{session_id}_{int(__import__('time').time())}", # ID unique
            question=question,
            response_text=response_text[:5000],  # Limite selon schéma
            response_source=source,
            status=status,
            processing_time_ms=processing_time_ms,
            confidence=confidence,
            completeness_score=None,
            language=getattr(payload, 'lang', 'fr') or 'fr',
            intent=None,
            entities=getattr(payload, 'entities', {}) or {},
            error_info=error_info
        )
        
        logger.info(f"✅ Question loggée PostgreSQL: {user_email or 'anonymous'}")
        
    except Exception as e:
        logger.error(f"⛔ Erreur log question to analytics: {e}")
        logger.error(f"⛔ Détails erreur: user={user_email}, session={session_id}")


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
        if hasattr(analytics, 'log_openai_usage'):
            analytics.log_openai_usage(
                user_email=user_email,
                session_id=session_id,
                question_id=question_id,
                model=model or os.getenv('DEFAULT_MODEL', 'gpt-4'),
                tokens=prompt_tokens + completion_tokens,
                cost_usd=0.0,  # À calculer si nécessaire
                cost_eur=0.0,  # À calculer si nécessaire
                purpose=purpose,
                success=success,
                response_time_ms=response_time_ms
            )
        else:
            logger.warning("⚠️ log_openai_usage non disponible sur analytics manager")
    except Exception as e:
        logger.error(f"⛔ Erreur track OpenAI call: {e}")