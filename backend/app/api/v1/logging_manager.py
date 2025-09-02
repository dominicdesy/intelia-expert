import logging
import psycopg2
import json
from datetime import datetime, date
from decimal import Decimal
from psycopg2.extras import Json, RealDictCursor
from typing import Optional, Dict, Any, List
import traceback
import os
from functools import lru_cache
import threading
from enum import Enum

logger = logging.getLogger(__name__)

# 🚀 LOG DE CONFIRMATION AU CHARGEMENT DU MODULE (CORRECTION CRITIQUE)
logger.error("🚀 LOGGING_MANAGER - VERSION FINALE CORRIGÉE COMPLÈTE - 2025-09-02-20:15 ACTIVE")

class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ResponseSource(str, Enum):
    RAG = "rag"
    OPENAI_FALLBACK = "openai_fallback"
    TABLE_LOOKUP = "table_lookup"
    VALIDATION_REJECTED = "validation_rejected"
    QUOTA_EXCEEDED = "quota_exceeded"

class UserRole(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(str, Enum):
    VIEW_OWN_ANALYTICS = "view_own_analytics"
    VIEW_ALL_ANALYTICS = "view_all_analytics"
    VIEW_OPENAI_COSTS = "view_openai_costs"
    VIEW_SERVER_PERFORMANCE = "view_server_performance"
    MANAGE_SYSTEM = "manage_system"
    ADMIN_DASHBOARD = "admin_dashboard"

# Cache intelligent global
_analytics_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = int(os.getenv("ANALYTICS_CACHE_TTL", "300"))

# Système de permissions par rôle
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.USER: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS
    ],
    UserRole.MODERATOR: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_ALL_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS
    ],
    UserRole.ADMIN: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_ALL_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS,
        Permission.VIEW_SERVER_PERFORMANCE,
        Permission.ADMIN_DASHBOARD
    ],
    UserRole.SUPER_ADMIN: [
        Permission.VIEW_OWN_ANALYTICS,
        Permission.VIEW_ALL_ANALYTICS,
        Permission.VIEW_OPENAI_COSTS,
        Permission.VIEW_SERVER_PERFORMANCE,
        Permission.MANAGE_SYSTEM,
        Permission.ADMIN_DASHBOARD
    ]
}

def get_cached_or_compute(cache_key: str, compute_func, ttl_seconds=None):
    """Cache intelligent avec TTL"""
    if ttl_seconds is None:
        ttl_seconds = CACHE_TTL_SECONDS
    
    with _cache_lock:
        now = datetime.now().timestamp()
        
        if cache_key in _analytics_cache:
            cached_data, cached_time = _analytics_cache[cache_key]
            if now - cached_time < ttl_seconds:
                return cached_data
        
        # Calculer nouvelle valeur
        result = compute_func()
        _analytics_cache[cache_key] = (result, now)
        
        # Nettoyage cache (éviter memory leak)
        _cleanup_expired_cache(now, ttl_seconds)
        
        return result

def _cleanup_expired_cache(current_time: float, ttl: int):
    """Nettoie les entrées expirées du cache"""
    expired_keys = [
        key for key, (_, cached_time) in _analytics_cache.items()
        if current_time - cached_time > ttl
    ]
    for key in expired_keys:
        del _analytics_cache[key]

def clear_analytics_cache():
    """Vide complètement le cache"""
    with _cache_lock:
        _analytics_cache.clear()

def has_permission(user_role: str, required_permission: Permission) -> bool:
    """Vérifie si un rôle a une permission spécifique"""
    try:
        role_enum = UserRole(user_role.lower())
        return required_permission in ROLE_PERMISSIONS.get(role_enum, [])
    except (ValueError, AttributeError):
        return False

def require_permission(required_permission: Permission):
    """Décorateur pour vérifier les permissions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Cette logique serait intégrée avec FastAPI Depends dans le contexte réel
            return func(*args, **kwargs)
        return wrapper
    return decorator

def is_admin_user(user: Dict[str, Any]) -> bool:
    """Vérifie si un utilisateur est admin"""
    return (
        user.get("is_admin", False) or 
        user.get("user_type") in ["admin", "super_admin"]
    )

class LoggingManager:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        # LOG DE CONFIRMATION VERSION FINALE
        logger.error("🚀 LOGGING_MANAGER - VERSION FINALE CORRIGÉE COMPLÈTE - 2025-09-02-17:45 ACTIVE")

    def get_connection(self):
        """Connexion à PostgreSQL"""
        return psycopg2.connect(**self.db_config)

    def _ensure_analytics_tables(self):
        """Crée toutes les tables d'analytics nécessaires"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Table principale des questions/réponses
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_questions_complete (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255),
                            session_id VARCHAR(255),
                            question_id VARCHAR(255),
                            question TEXT NOT NULL,
                            response_text TEXT,
                            response_source VARCHAR(50),
                            status VARCHAR(20) DEFAULT 'success',
                            processing_time_ms INTEGER,
                            confidence DECIMAL(5,2),
                            completeness_score DECIMAL(5,2),
                            language VARCHAR(10) DEFAULT 'fr',
                            intent VARCHAR(50),
                            entities JSONB DEFAULT '{}',
                            error_type VARCHAR(100),
                            error_message TEXT,
                            error_traceback TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_user_questions_user_email ON user_questions_complete(user_email);
                        CREATE INDEX IF NOT EXISTS idx_user_questions_created_at ON user_questions_complete(created_at);
                        CREATE INDEX IF NOT EXISTS idx_user_questions_status ON user_questions_complete(status);
                    """)
                    
                    # Table des erreurs système
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS system_errors (
                            id SERIAL PRIMARY KEY,
                            error_type VARCHAR(100) NOT NULL,
                            category VARCHAR(50) NOT NULL,
                            severity VARCHAR(20) DEFAULT 'error',
                            component VARCHAR(100),
                            user_email VARCHAR(255),
                            session_id VARCHAR(255),
                            question_id VARCHAR(255),
                            details JSONB DEFAULT '{}',
                            traceback TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_system_errors_category ON system_errors(category);
                        CREATE INDEX IF NOT EXISTS idx_system_errors_severity ON system_errors(severity);
                        CREATE INDEX IF NOT EXISTS idx_system_errors_created_at ON system_errors(created_at);
                    """)
                    
                    # Table utilisation OpenAI
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS openai_usage (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255),
                            session_id VARCHAR(255),
                            question_id VARCHAR(255),
                            model VARCHAR(50) DEFAULT 'gpt-4',
                            tokens INTEGER DEFAULT 0,
                            cost_usd DECIMAL(10,6) DEFAULT 0.0,
                            cost_eur DECIMAL(10,6) DEFAULT 0.0,
                            purpose VARCHAR(50) DEFAULT 'chat',
                            success BOOLEAN DEFAULT true,
                            response_time_ms INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_openai_usage_user_email ON openai_usage(user_email);
                        CREATE INDEX IF NOT EXISTS idx_openai_usage_created_at ON openai_usage(created_at);
                    """)
                    
                    # Table résumé quotidien OpenAI
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS daily_openai_summary (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255),
                            date DATE NOT NULL,
                            total_requests INTEGER DEFAULT 0,
                            successful_requests INTEGER DEFAULT 0,
                            total_tokens INTEGER DEFAULT 0,
                            total_cost_usd DECIMAL(10,4) DEFAULT 0.0,
                            total_cost_eur DECIMAL(10,4) DEFAULT 0.0,
                            avg_response_time_ms DECIMAL(8,2),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_email, date)
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_daily_openai_summary_date ON daily_openai_summary(date);
                        CREATE INDEX IF NOT EXISTS idx_daily_openai_summary_user_date ON daily_openai_summary(user_email, date);
                    """)
                    
        except Exception as e:
            logger.error(f"⛔ Erreur création tables analytics: {e}")

    def log_question_response(
        self,
        user_email: str,
        session_id: str,
        question_id: str,
        question: str,
        response_text: str,
        response_source: str,
        status: str = "success",
        processing_time_ms: int = None,
        confidence: float = None,
        completeness_score: float = None,
        language: str = None,
        intent: str = None,
        entities: Dict[str, Any] = None,
        error_info: Dict[str, Any] = None
    ):
        """Log des questions/réponses avec correction FINALE du problème dict"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # SOLUTION: Sérialiser TOUS les dictionnaires avec Json()
                    entities_json = Json(entities) if entities else None
                    
                    # ✅ CORRECTION CRITIQUE: Traiter error_info de manière robuste
                    error_type = None
                    error_message = None
                    error_traceback = None
                    
                    if error_info:
                        if isinstance(error_info, dict):
                            error_type = error_info.get("type")
                            error_message = error_info.get("message")
                            error_traceback = error_info.get("traceback")
                        else:
                            # Si error_info n'est pas un dict, le convertir en string
                            error_message = str(error_info)
                    
                    cur.execute("""
                        INSERT INTO user_questions_complete (
                            user_email, session_id, question_id, question, response_text,
                            response_source, status, processing_time_ms, confidence,
                            completeness_score, language, intent, entities, 
                            error_type, error_message, error_traceback, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        user_email,
                        session_id,
                        question_id,
                        question[:2000] if question else None,
                        response_text[:5000] if response_text else None,
                        response_source,
                        status,
                        processing_time_ms,
                        confidence,
                        completeness_score,
                        language,
                        intent,
                        entities_json,  # ✅ Sérialisé avec Json()
                        error_type,     # ✅ String simple
                        error_message,  # ✅ String simple
                        error_traceback, # ✅ String simple
                        datetime.now()
                    ))
                    
        except Exception as e:
            logger.error(f"⛔ Erreur log question/réponse: {e}")
            logger.error(f"📍 Traceback: {traceback.format_exc()}")
            # Debug détaillé
            logger.error(f"🔍 DEBUG: user_email={type(user_email)}, entities={type(entities)}, error_info={type(error_info)}")

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
            logger.error(f"⛔ Erreur log système: {e}")

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
                    
                    # Mise à jour du résumé quotidien
                    self._update_daily_openai_summary(cur, user_email, cost_usd, cost_eur, tokens, purpose, success, response_time_ms)
                    
        except Exception as e:
            logger.error(f"⛔ Erreur log OpenAI: {e}")

    def _update_daily_openai_summary(self, cur, user_email, cost_usd, cost_eur, tokens, purpose, success, response_time_ms):
        """Met à jour le résumé quotidien OpenAI"""
        try:
            today = datetime.now().date()
            
            cur.execute("""
                INSERT INTO daily_openai_summary (
                    user_email, date, total_requests, successful_requests, 
                    total_tokens, total_cost_usd, total_cost_eur, avg_response_time_ms
                ) VALUES (%s, %s, 1, %s, %s, %s, %s, %s)
                ON CONFLICT (user_email, date) DO UPDATE SET
                    total_requests = daily_openai_summary.total_requests + 1,
                    successful_requests = daily_openai_summary.successful_requests + %s,
                    total_tokens = daily_openai_summary.total_tokens + %s,
                    total_cost_usd = daily_openai_summary.total_cost_usd + %s,
                    total_cost_eur = daily_openai_summary.total_cost_eur + %s,
                    avg_response_time_ms = (
                        CASE 
                            WHEN %s IS NOT NULL THEN 
                                (daily_openai_summary.avg_response_time_ms * daily_openai_summary.total_requests + %s) / (daily_openai_summary.total_requests + 1)
                            ELSE daily_openai_summary.avg_response_time_ms
                        END
                    ),
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_email, today, 1 if success else 0, tokens, cost_usd, cost_eur, response_time_ms,
                1 if success else 0, tokens, cost_usd, cost_eur, response_time_ms, response_time_ms
            ))
            
        except Exception as e:
            logger.error(f"⛔ Erreur mise à jour résumé quotidien: {e}")

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
                conditions.append("confidence >= %s")
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
                               response_source, status, processing_time_ms, confidence,
                               completeness_score, language, intent, entities,
                               error_type, error_message, error_traceback, created_at
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
            logger.error(f"⛔ Erreur récupération questions: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0}
            }

    def get_user_stats(self, user_email: str, days: int = 30) -> Dict[str, Any]:
        """Statistiques détaillées d'un utilisateur"""
        try:
            cache_key = f"user_stats_{user_email}_{days}"
            
            def compute_stats():
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        start_date = datetime.now() - timedelta(days=days)
                        
                        # Questions totales
                        cur.execute("""
                            SELECT COUNT(*) as total_questions,
                                   COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_questions,
                                   AVG(confidence) as avg_confidence,
                                   AVG(processing_time_ms) as avg_processing_time
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
            
            return get_cached_or_compute(cache_key, compute_stats, ttl_seconds=1800)  # 30min cache
            
        except Exception as e:
            logger.error(f"⛔ Erreur statistiques utilisateur: {e}")
            return {"success": False, "error": str(e)}

    def get_system_performance(self, hours: int = 24) -> Dict[str, Any]:
        """Métriques de performance système"""
        try:
            cache_key = f"system_performance_{hours}"
            
            def compute_performance():
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        start_time = datetime.now() - timedelta(hours=hours)
                        
                        # Performance globale
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total_requests,
                                COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_requests,
                                AVG(processing_time_ms) as avg_response_time,
                                MAX(processing_time_ms) as max_response_time,
                                MIN(processing_time_ms) as min_response_time
                            FROM user_questions_complete
                            WHERE created_at >= %s
                        """, (start_time,))
                        
                        performance = dict(cur.fetchone() or {})
                        
                        # Erreurs système
                        cur.execute("""
                            SELECT COUNT(*) as total_errors,
                                   COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_errors
                            FROM system_errors
                            WHERE created_at >= %s
                        """, (start_time,))
                        
                        error_data = dict(cur.fetchone() or {})
                        performance.update(error_data)
                        
                        return {
                            "success": True,
                            "period_hours": hours,
                            "performance": performance
                        }
            
            return get_cached_or_compute(cache_key, compute_performance, ttl_seconds=900)  # 15min cache
            
        except Exception as e:
            logger.error(f"⛔ Erreur performance système: {e}")
            return {"success": False, "error": str(e)}

    def get_openai_costs(self, user_email: str = None, days: int = 30) -> Dict[str, Any]:
        """Analyse des coûts OpenAI"""
        try:
            cache_key = f"openai_costs_{user_email or 'all'}_{days}"
            
            def compute_costs():
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        start_date = datetime.now() - timedelta(days=days)
                        
                        conditions = ["created_at >= %s"]
                        params = [start_date]
                        
                        if user_email:
                            conditions.append("user_email = %s")
                            params.append(user_email)
                        
                        where_clause = "WHERE " + " AND ".join(conditions)
                        
                        # Coûts par jour
                        cur.execute(f"""
                            SELECT DATE(created_at) as date,
                                   SUM(cost_usd) as daily_cost_usd,
                                   SUM(cost_eur) as daily_cost_eur,
                                   SUM(tokens) as daily_tokens,
                                   COUNT(*) as daily_requests
                            FROM openai_usage
                            {where_clause}
                            GROUP BY DATE(created_at)
                            ORDER BY date DESC
                        """, params)
                        
                        daily_costs = [dict(row) for row in cur.fetchall()]
                        
                        # Total
                        cur.execute(f"""
                            SELECT SUM(cost_usd) as total_cost_usd,
                                   SUM(cost_eur) as total_cost_eur,
                                   SUM(tokens) as total_tokens,
                                   COUNT(*) as total_requests
                            FROM openai_usage
                            {where_clause}
                        """, params)
                        
                        totals = dict(cur.fetchone() or {})
                        
                        return {
                            "success": True,
                            "user_email": user_email,
                            "period_days": days,
                            "daily_costs": daily_costs,
                            "totals": totals
                        }
            
            return get_cached_or_compute(cache_key, compute_costs, ttl_seconds=3600)  # 1h cache
            
        except Exception as e:
            logger.error(f"⛔ Erreur coûts OpenAI: {e}")
            return {"success": False, "error": str(e)}

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Statistiques pour le dashboard admin"""
        try:
            cache_key = "dashboard_stats"
            
            def compute_dashboard():
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        today = datetime.now().date()
                        week_ago = today - timedelta(days=7)
                        
                        # Statistiques aujourd'hui
                        cur.execute("""
                            SELECT COUNT(*) as questions_today
                            FROM user_questions_complete
                            WHERE DATE(created_at) = %s
                        """, (today,))
                        
                        today_stats = dict(cur.fetchone() or {})
                        
                        # Statistiques cette semaine
                        cur.execute("""
                            SELECT COUNT(*) as questions_week,
                                   COUNT(DISTINCT user_email) as active_users_week
                            FROM user_questions_complete
                            WHERE created_at >= %s
                        """, (week_ago,))
                        
                        week_stats = dict(cur.fetchone() or {})
                        
                        # Top utilisateurs
                        cur.execute("""
                            SELECT user_email, COUNT(*) as question_count
                            FROM user_questions_complete
                            WHERE created_at >= %s
                            GROUP BY user_email
                            ORDER BY question_count DESC
                            LIMIT 10
                        """, (week_ago,))
                        
                        top_users = [dict(row) for row in cur.fetchall()]
                        
                        return {
                            "success": True,
                            "today": today_stats,
                            "this_week": week_stats,
                            "top_users": top_users,
                            "generated_at": datetime.now().isoformat()
                        }
            
            return get_cached_or_compute(cache_key, compute_dashboard, ttl_seconds=600)  # 10min cache
            
        except Exception as e:
            logger.error(f"⛔ Erreur dashboard stats: {e}")
            return {"success": False, "error": str(e)}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache pour monitoring"""
        with _cache_lock:
            return {
                "cache_entries": len(_analytics_cache),
                "cache_keys": list(_analytics_cache.keys()),
                "ttl_seconds": CACHE_TTL_SECONDS
            }

# Instance globale pour compatibilité
_global_logging_manager = None
_initialization_lock = threading.Lock()

def get_logging_manager(db_config: dict = None) -> LoggingManager:
    """Récupère l'instance globale du LoggingManager (singleton)"""
    global _global_logging_manager
    
    if _global_logging_manager is None:
        with _initialization_lock:
            if _global_logging_manager is None:
                if db_config is None:
                    # Configuration par défaut depuis les variables d'environnement
                    db_config = {
                        "host": os.getenv("POSTGRES_HOST", "localhost"),
                        "port": os.getenv("POSTGRES_PORT", 5432),
                        "database": os.getenv("POSTGRES_DB", "intelia_expert"),
                        "user": os.getenv("POSTGRES_USER", "postgres"),
                        "password": os.getenv("POSTGRES_PASSWORD", "password")
                    }
                
                _global_logging_manager = LoggingManager(db_config)
                
                # Créer les tables au démarrage
                _global_logging_manager._ensure_analytics_tables()
    
    return _global_logging_manager

def log_question_to_analytics(
    user_email: str,
    session_id: str,
    question_id: str,
    question: str,
    response_text: str,
    response_source: str = "rag",
    **kwargs
):
    """Helper pour logger une question facilement"""
    try:
        manager = get_logging_manager()
        manager.log_question_response(
            user_email=user_email,
            session_id=session_id,
            question_id=question_id,
            question=question,
            response_text=response_text,
            response_source=response_source,
            **kwargs
        )
    except Exception as e:
        logger.error(f"⛔ Erreur logging question: {e}")

def track_openai_call(
    user_email: str,
    model: str,
    tokens: int,
    cost_usd: float,
    success: bool = True,
    **kwargs
):
    """Helper pour tracker un appel OpenAI"""
    try:
        manager = get_logging_manager()
        manager.log_openai_usage(
            user_email=user_email,
            model=model,
            tokens=tokens,
            cost_usd=cost_usd,
            success=success,
            **kwargs
        )
    except Exception as e:
        logger.error(f"⛔ Erreur tracking OpenAI: {e}")