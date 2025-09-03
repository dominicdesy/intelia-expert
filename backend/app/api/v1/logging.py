# app/api/v1/logging.py
# -*- coding: utf-8 -*-
"""
🚀 SYSTÈME DE LOGGING - POINT D'ENTRÉE PRINCIPAL
📊 Architecture modulaire avec classe LoggingManager principale
🔧 CORRECTION: Bug PostgreSQL 'can't adapt type dict' résolu
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

# 🚀 LOG DE CONFIRMATION VERSION DÉPLOYÉE
logger.error("🚀 LOGGING SYSTEM - VERSION RESTRUCTURÉE ACTIVE - 2025-09-02-21:30")
logger.error("🔧 CORRECTION: Bug PostgreSQL résolu avec architecture modulaire")

# ============================================================================
# 📦 IMPORTS DEPUIS LES MODULES SPÉCIALISÉS
# ============================================================================

try:
    from .logging_models import (
        LogLevel, ResponseSource, UserRole, Permission, ROLE_PERMISSIONS
    )
    logger.info("✅ Logging models importés")
except ImportError as e:
    logger.error(f"❌ ERREUR CRITIQUE: logging_models.py manquant: {e}")
    raise

try:
    from .logging_permissions import (
        has_permission, require_permission, is_admin_user
    )
    logger.info("✅ Logging permissions importées")
except ImportError as e:
    logger.error(f"❌ ERREUR CRITIQUE: logging_permissions.py manquant: {e}")
    raise

try:
    from .logging_cache import (
        get_cached_or_compute, clear_analytics_cache, get_cache_stats,
        cleanup_expired_cache, get_cache_memory_usage
    )
    logger.info("✅ Logging cache importé")
except ImportError as e:
    logger.error(f"❌ ERREUR CRITIQUE: logging_cache.py manquant: {e}")
    raise

# ============================================================================
# 🏗️ CLASSE PRINCIPALE LOGGINGMANAGER
# ============================================================================

class LoggingManager:
    """
    Gestionnaire principal des analytics et logging
    CORRECTION CRITIQUE: Bug PostgreSQL 'can't adapt type dict' résolu
    """
    
    def __init__(self, db_config: dict = None):
        self.db_config = db_config or {}
        # Stocker DATABASE_URL pour la méthode get_connection corrigée
        self.dsn = os.getenv("DATABASE_URL")
        logger.info("🚀 LoggingManager initialisé avec correction PostgreSQL")

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
                    """)
                    
        except Exception as e:
            logger.error(f"❌ Erreur création tables analytics: {e}")

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
        """
        CORRECTION CRITIQUE: Log des questions/réponses avec bug PostgreSQL résolu
        Sérialise correctement tous les dictionnaires avec Json()
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # ✅ SOLUTION: Sérialiser TOUS les dictionnaires avec Json()
                    entities_json = Json(entities) if entities else None
                    
                    # ✅ CORRECTION: Traiter error_info de manière robuste
                    error_type = None
                    error_message = None
                    error_traceback = None
                    
                    if error_info:
                        if isinstance(error_info, dict):
                            error_type = error_info.get("type")
                            error_message = error_info.get("message")
                            error_traceback = error_info.get("traceback")
                        else:
                            error_message = str(error_info)
                    
                    cur.execute("""
                        INSERT INTO user_questions_complete (
                            user_email, session_id, question_id, question, response_text,
                            response_source, status, processing_time_ms, response_confidence,
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
            logger.error(f"❌ Erreur log question/réponse: {e}")
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
            logger.error(f"❌ Erreur log système: {e}")

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
            logger.error(f"❌ Erreur log OpenAI: {e}")

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
            logger.error(f"❌ Erreur récupération questions: {e}")
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
                                MIN(processing_time_ms) as min_response_time
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

# ============================================================================
# 🔗 FONCTIONS DE COMPATIBILITÉ ET SINGLETON
# ============================================================================

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
                logger.info("🔧 Création du gestionnaire analytics...")
                
                # Configuration avec DATABASE_URL
                database_url = os.getenv("DATABASE_URL")
                
                if database_url:
                    try:
                        db_config = psycopg2.extensions.parse_dsn(database_url)
                        logger.info("✅ Configuration PostgreSQL depuis DATABASE_URL")
                    except Exception as e:
                        logger.error(f"❌ Erreur parsing DATABASE_URL: {e}")
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
                _analytics_manager._ensure_analytics_tables()
                logger.info("✅ Gestionnaire analytics créé avec correction PostgreSQL")
    
    return _analytics_manager

def get_logging_manager(db_config: dict = None) -> LoggingManager:
    """Alias pour compatibilité avec expert_utils.py"""
    return get_analytics_manager()

# Alias pour compatibilité totale
AnalyticsManager = LoggingManager

# ============================================================================
# 📊 ROUTER ET EXPORTS
# ============================================================================

try:
    from .logging_endpoints import router
    logger.info("✅ Logging endpoints importés")
except ImportError as e:
    logger.error(f"❌ ERREUR: logging_endpoints.py manquant: {e}")
    # Créer un router de base pour compatibilité
    from fastapi import APIRouter
    router = APIRouter(prefix="/logging", tags=["logging"])

# ============================================================================
# 📋 EXPORTS PUBLICS
# ============================================================================

__all__ = [
    # Classe principale
    'LoggingManager',
    'AnalyticsManager',
    
    # Fonctions singleton
    'get_analytics_manager',
    'get_logging_manager',
    'get_analytics',  # ✅ AJOUTÉ pour compatibilité main.py
    
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

logger.info("✅ Système logging restructuré initialisé - Bug PostgreSQL corrigé")
logger.info("📊 Architecture modulaire maintenue avec 6 fichiers spécialisés")