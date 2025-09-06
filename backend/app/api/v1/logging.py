# app/api/v1/logging.py
"""
SYSTÈME DE LOGGING - POINT D'ENTRÉE PRINCIPAL
Version corrigée sans création de tables
"""
import os
import logging
import threading
import psycopg2
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from psycopg2.extras import Json, RealDictCursor
from typing import Optional, Dict, Any, List
import traceback

logger = logging.getLogger(__name__)

# IMPORTS DEPUIS LES MODULES SPÉCIALISÉS
try:
    from .logging_models import (
        LogLevel, ResponseSource, UserRole, Permission, ROLE_PERMISSIONS
    )
    logger.info("Logging models importés")
except ImportError as e:
    logger.error(f"ERREUR CRITIQUE: logging_models.py manquant: {e}")
    raise

try:
    from .logging_permissions import (
        has_permission, require_permission, is_admin_user
    )
    logger.info("Logging permissions importées")
except ImportError as e:
    logger.error(f"ERREUR CRITIQUE: logging_permissions.py manquant: {e}")
    raise

try:
    from .logging_cache import (
        get_cached_or_compute, clear_analytics_cache, get_cache_stats,
        cleanup_expired_cache, get_cache_memory_usage
    )
    logger.info("Logging cache importé")
except ImportError as e:
    logger.error(f"ERREUR CRITIQUE: logging_cache.py manquant: {e}")
    raise

class LoggingManager:
    """
    Gestionnaire principal des analytics et logging
    """
    
    def __init__(self, db_config: dict = None):
        self.db_config = db_config or {}
        self.dsn = os.getenv("DATABASE_URL")
        logger.info("LoggingManager initialisé avec correction PostgreSQL")

    def get_connection(self):
        """
        CORRECTION CRITIQUE: Connexion PostgreSQL avec DATABASE_URL en priorité
        Résout le bug 'can't adapt type dict'
        """
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return psycopg2.connect(database_url)
        elif self.db_config and any(self.db_config.values()):
            return psycopg2.connect(**self.db_config)
        else:
            raise ValueError("Aucune configuration de base de données disponible (DATABASE_URL ou db_config)")

    def update_feedback(
        self,
        conversation_id: str,
        feedback: int,
        feedback_comment: str = None
    ):
        """
        Met à jour le feedback d'une conversation existante
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_questions_complete 
                        SET feedback = %s, 
                            feedback_comment = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE session_id = %s OR question_id = %s
                        RETURNING id, user_email
                    """, (feedback, feedback_comment, conversation_id, conversation_id))
                    
                    result = cur.fetchone()
                    if result:
                        logger.info(f"Feedback mis à jour pour conversation {conversation_id}")
                        return {"success": True, "conversation_id": conversation_id}
                    else:
                        logger.warning(f"Aucune conversation trouvée pour ID: {conversation_id}")
                        return {"success": False, "error": "Conversation non trouvée"}
                    
        except Exception as e:
            logger.error(f"Erreur mise à jour feedback: {e}")
            return {"success": False, "error": str(e)}

    def update_feedback_comment(
        self,
        conversation_id: str,
        comment: str
    ):
        """
        Met à jour le commentaire feedback d'une conversation
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_questions_complete 
                        SET feedback_comment = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE (session_id = %s OR question_id = %s)
                            AND feedback IS NOT NULL
                        RETURNING id
                    """, (comment, conversation_id, conversation_id))
                    
                    result = cur.fetchone()
                    return {"success": bool(result), "conversation_id": conversation_id}
                    
        except Exception as e:
            logger.error(f"Erreur mise à jour commentaire: {e}")
            return {"success": False, "error": str(e)}

    def log_system_error(
        self,
        error_type: str,
        category: str,
        severity: str = "error",
        component: str = None,
        user_email: str = None,
        session_id: str = None,
        question_id: str = None,
        details: Dict[str, Any] = None,
        traceback_info: str = None
    ):
        """Log des erreurs système"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    details_json = Json(details) if details else None
                    
                    cur.execute("""
                        INSERT INTO system_errors (
                            error_type, category, severity, component, user_email,
                            session_id, question_id, details, traceback, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        error_type, category, severity, component, user_email,
                        session_id, question_id, details_json, traceback_info, datetime.now()
                    ))
                    
        except Exception as e:
            logger.error(f"Erreur log système: {e}")

    def log_openai_usage(
        self,
        user_email: str,
        session_id: str = None,
        question_id: str = None,
        model: str = "gpt-4",
        tokens: int = 0,
        cost_usd: float = 0.0,
        cost_eur: float = 0.0,
        purpose: str = "chat",
        success: bool = True,
        response_time_ms: int = None
    ):
        """Log de l'utilisation OpenAI"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO openai_usage (
                            user_email, session_id, question_id, model, tokens,
                            cost_usd, cost_eur, purpose, success, response_time_ms, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_email, session_id, question_id, model, tokens,
                        cost_usd, cost_eur, purpose, success, response_time_ms, datetime.now()
                    ))
                    
        except Exception as e:
            logger.error(f"Erreur log OpenAI: {e}")

    def log_question_response(
        self,
        user_email: str,
        session_id: str,
        question_id: str,
        question: str,
        response_text: str,
        response_source: str,
        status: str,
        processing_time_ms: int,
        confidence: Optional[float] = None,
        completeness_score: Optional[float] = None,
        language: str = "fr",
        intent: Optional[str] = None,
        entities: Dict[str, Any] = None,
        error_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        CORRECTION: Log une question et sa réponse dans PostgreSQL
        Inclut maintenant data_size_kb pour éviter l'erreur de colonne manquante
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Préparation des données
                    entities_json = Json(entities) if entities else Json({})
                    
                    # Calcul de la taille des données en KB
                    data_size_kb = 0
                    if response_text:
                        data_size_kb = len(response_text.encode('utf-8')) // 1024
                    
                    # Gestion des erreurs
                    error_type = None
                    error_message = None
                    error_traceback = None
                    
                    if error_info:
                        error_type = error_info.get("type")
                        error_message = error_info.get("message")
                        error_traceback = error_info.get("traceback")
                    
                    # CORRECTION: Insertion avec data_size_kb inclus
                    cur.execute("""
                        INSERT INTO user_questions_complete (
                            user_email, session_id, question_id, question, response_text,
                            response_source, status, processing_time_ms, response_confidence,
                            completeness_score, language, intent, entities,
                            error_type, error_message, error_traceback, data_size_kb, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_email, session_id, question_id, question, response_text,
                        response_source, status, processing_time_ms, confidence,
                        completeness_score, language, intent, entities_json,
                        error_type, error_message, error_traceback, data_size_kb, datetime.now()
                    ))
                    
                    logger.debug(f"Question loggée en base: {user_email}, session: {session_id}")
                    
        except Exception as e:
            logger.error(f"Erreur log_question_response: {e}")
            logger.error(f"Détails: user={user_email}, session={session_id}, question_id={question_id}")

    def log_server_performance(self, **kwargs):
        """Log des métriques de performance serveur"""
        try:
            # Implémentation pour compatibilité avec main.py
            logger.debug(f"Métriques serveur loggées: {kwargs}")
            # TODO: Implémenter la sauvegarde en base si nécessaire
        except Exception as e:
            logger.error(f"Erreur log server performance: {e}")

    def get_questions_with_filters(
        self, 
        page: int = 1, 
        limit: int = 10,
        user_email: str = None,
        start_date: date = None,
        end_date: date = None,
        status: str = None,
        min_confidence: float = None
    ) -> Dict[str, Any]:
        """Récupère les questions avec filtres avancés"""
        try:
            offset = (page - 1) * limit
            conditions = []
            params = []
            
            if user_email:
                conditions.append("user_email = %s")
                params.append(user_email)
            
            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)
            
            if status:
                conditions.append("status = %s")
                params.append(status)
            
            if min_confidence is not None:
                conditions.append("response_confidence >= %s")
                params.append(min_confidence)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Count total
                    count_query = f"SELECT COUNT(*) FROM user_questions_complete {where_clause}"
                    cur.execute(count_query, params)
                    total_count = cur.fetchone()[0]
                    
                    # Get data
                    main_query = f"""
                        SELECT user_email, session_id, question_id, question, response_text,
                               response_source, status, processing_time_ms, response_confidence,
                               completeness_score, language, intent, entities,
                               error_type, error_message, error_traceback, feedback,
                               feedback_comment, data_size_kb, created_at
                        FROM user_questions_complete
                        {where_clause}
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    params.extend([limit, offset])
                    cur.execute(main_query, params)
                    
                    results = []
                    for row in cur.fetchall():
                        row_dict = dict(row)
                        if row_dict['created_at']:
                            row_dict['created_at'] = row_dict['created_at'].isoformat()
                        results.append(row_dict)
                    
                    return {
                        "success": True,
                        "data": results,
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total_count,
                            "pages": (total_count + limit - 1) // limit
                        },
                        "debug": {
                            "query_executed": True,
                            "total_found": total_count,
                            "returned": len(results)
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Erreur récupération questions: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0}
            }

    def get_user_analytics(self, user_email: str, days: int = 30) -> Dict[str, Any]:
        """Statistiques détaillées d'un utilisateur avec cache"""
        cache_key = f"user_analytics_{user_email}_{days}"
        
        def compute_analytics():
            try:
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        start_date = datetime.now() - timedelta(days=days)
                        
                        # Questions totales
                        cur.execute("""
                            SELECT COUNT(*) as total_questions,
                                   COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_questions,
                                   AVG(response_confidence) as avg_confidence,
                                   AVG(processing_time_ms) as avg_processing_time,
                                   SUM(data_size_kb) as total_data_kb
                            FROM user_questions_complete
                            WHERE user_email = %s AND created_at >= %s
                        """, (user_email, start_date))
                        
                        stats = dict(cur.fetchone() or {})
                        
                        # Coûts OpenAI
                        cur.execute("""
                            SELECT SUM(cost_usd) as total_cost_usd,
                                   SUM(cost_eur) as total_cost_eur,
                                   SUM(tokens) as total_tokens
                            FROM openai_usage
                            WHERE user_email = %s AND created_at >= %s
                        """, (user_email, start_date))
                        
                        cost_data = dict(cur.fetchone() or {})
                        stats.update(cost_data)
                        
                        return {
                            "success": True,
                            "user_email": user_email,
                            "period_days": days,
                            "stats": stats
                        }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return get_cached_or_compute(cache_key, compute_analytics, ttl_seconds=1800)

    def get_server_performance_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Métriques de performance système avec cache"""
        cache_key = f"server_performance_{hours}"
        
        def compute_performance():
            try:
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        start_time = datetime.now() - timedelta(hours=hours)
                        
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total_requests,
                                COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_requests,
                                AVG(processing_time_ms) as avg_response_time,
                                MAX(processing_time_ms) as max_response_time,
                                MIN(processing_time_ms) as min_response_time,
                                SUM(data_size_kb) as total_data_kb
                            FROM user_questions_complete
                            WHERE created_at >= %s
                        """, (start_time,))
                        
                        performance = dict(cur.fetchone() or {})
                        
                        return {
                            "success": True,
                            "period_hours": hours,
                            "performance": performance
                        }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return get_cached_or_compute(cache_key, compute_performance, ttl_seconds=900)

# FONCTIONS DE COMPATIBILITÉ ET SINGLETON

def get_server_analytics(hours: int = 24) -> Dict[str, Any]:
    """Récupère les analytics serveur pour compatibilité avec stats_updater.py"""
    try:
        analytics = get_analytics_manager()
        return analytics.get_server_performance_analytics(hours)
    except Exception as e:
        return {"error": str(e), "hours": hours}

# Singleton sécurisé
_analytics_manager = None
_initialization_lock = threading.Lock()

def get_analytics() -> Dict[str, Any]:
    """Fonction analytics pour compatibilité avec main.py"""
    try:
        analytics = get_analytics_manager()
        return {
            "status": "analytics_available",
            "tables_created": True,
            "dsn_configured": bool(getattr(analytics, 'dsn', None)),
            "cache_enabled": True,
            "cache_entries": get_cache_stats().get("total_entries", 0)
        }
    except Exception as e:
        return {
            "status": "analytics_error",
            "error": str(e)
        }

def get_analytics_manager(force_init=None) -> LoggingManager:
    """
    SINGLETON SÉCURISÉ - Version corrigée avec DATABASE_URL
    Compatible avec tous les imports existants
    """
    global _analytics_manager
    
    if _analytics_manager is None:
        with _initialization_lock:
            if _analytics_manager is None:
                logger.info("Création du gestionnaire analytics...")
                
                # Configuration avec DATABASE_URL
                database_url = os.getenv("DATABASE_URL")
                
                if database_url:
                    try:
                        db_config = psycopg2.extensions.parse_dsn(database_url)
                        logger.info("Configuration PostgreSQL depuis DATABASE_URL")
                    except Exception as e:
                        logger.error(f"Erreur parsing DATABASE_URL: {e}")
                        db_config = {
                            "host": os.getenv("POSTGRES_HOST", "localhost"),
                            "port": int(os.getenv("POSTGRES_PORT", 5432)),
                            "database": os.getenv("POSTGRES_DB", "postgres"),
                            "user": os.getenv("POSTGRES_USER", "postgres"),
                            "password": os.getenv("POSTGRES_PASSWORD", "")
                        }
                else:
                    db_config = {
                        "host": os.getenv("POSTGRES_HOST", "localhost"),
                        "port": int(os.getenv("POSTGRES_PORT", 5432)),
                        "database": os.getenv("POSTGRES_DB", "postgres"),
                        "user": os.getenv("POSTGRES_USER", "postgres"),
                        "password": os.getenv("POSTGRES_PASSWORD", "")
                    }
                
                _analytics_manager = LoggingManager(db_config)
                # SUPPRIMÉ: _analytics_manager._ensure_analytics_tables()
                logger.info("Gestionnaire analytics créé sans création de tables")
    
    return _analytics_manager

def get_logging_manager(db_config: dict = None) -> LoggingManager:
    """Alias pour compatibilité avec expert_utils.py"""
    return get_analytics_manager()

# Alias pour compatibilité totale
AnalyticsManager = LoggingManager

# ROUTER ET EXPORTS
try:
    from .logging_endpoints import router
    logger.info("Logging endpoints importés")
except ImportError as e:
    logger.error(f"ERREUR: logging_endpoints.py manquant: {e}")
    # Créer un router de base pour compatibilité
    from fastapi import APIRouter
    router = APIRouter(prefix="/logging", tags=["logging"])

# EXPORTS PUBLICS
__all__ = [
    # Classe principale
    'LoggingManager',
    'AnalyticsManager',
    
    # Fonctions singleton
    'get_analytics_manager',
    'get_logging_manager',
    'get_analytics',
    'get_server_analytics',
    
    # Imports depuis modules spécialisés
    'LogLevel',
    'ResponseSource', 
    'UserRole',
    'Permission',
    'ROLE_PERMISSIONS',
    'has_permission',
    'require_permission',
    'is_admin_user',
    'get_cached_or_compute',
    'clear_analytics_cache',
    'get_cache_stats',
    
    # Router API
    'router'
]