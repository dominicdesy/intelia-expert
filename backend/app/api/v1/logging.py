# app/api/v1/logging.py
# -*- coding: utf-8 -*-
"""
Système complet de logging et analytics séparé du système de facturation
Tracking des questions/réponses, erreurs, performance et coûts OpenAI
"""
import json
import time
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Depends, Query, HTTPException
from enum import Enum

# Import authentification
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/logging", tags=["logging"])
logger = logging.getLogger(__name__)

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

class AnalyticsManager:
    """
    Gestionnaire complet d'analytics et logging
    """
    
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("❌ DATABASE_URL manquant - stockage persistant requis")
        self._ensure_analytics_tables()
    
    def _ensure_analytics_tables(self):
        """Crée toutes les tables d'analytics et logging"""
        try:
            with psycopg2.connect(self.dsn) as conn:
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
                            status VARCHAR(20) DEFAULT 'success', -- success/error/timeout
                            processing_time_ms INTEGER,
                            response_confidence DECIMAL(5,2),
                            completeness_score DECIMAL(5,2),
                            
                            -- Metadata
                            language VARCHAR(10) DEFAULT 'fr',
                            intent VARCHAR(50),
                            entities JSONB DEFAULT '{}',
                            
                            -- Erreurs
                            error_type VARCHAR(100),
                            error_message TEXT,
                            error_traceback TEXT,
                            
                            -- Timestamps
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Table des erreurs système détaillées
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS system_errors (
                            id SERIAL PRIMARY KEY,
                            error_type VARCHAR(100) NOT NULL,
                            category VARCHAR(50) NOT NULL, -- rag_failure, openai_error, validation_error, etc.
                            severity VARCHAR(20) DEFAULT 'error', -- info, warning, error, critical
                            component VARCHAR(100), -- dialogue_manager, rag_engine, etc.
                            user_email VARCHAR(255),
                            session_id VARCHAR(255),
                            question_id VARCHAR(255),
                            
                            -- Détails erreur
                            error_message TEXT,
                            error_traceback TEXT,
                            context_data JSONB DEFAULT '{}',
                            
                            -- Status résolution
                            resolved BOOLEAN DEFAULT FALSE,
                            resolution_notes TEXT,
                            resolved_at TIMESTAMP,
                            
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Table de tracking des appels OpenAI
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS openai_api_calls (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255),
                            session_id VARCHAR(255),
                            question_id VARCHAR(255),
                            
                            -- Détails appel OpenAI
                            call_type VARCHAR(50), -- completion, embedding, etc.
                            model VARCHAR(100),
                            prompt_tokens INTEGER,
                            completion_tokens INTEGER,
                            total_tokens INTEGER,
                            
                            -- Coûts (tarifs OpenAI)
                            cost_usd DECIMAL(10,6),
                            cost_eur DECIMAL(10,6),
                            
                            -- Contexte
                            purpose VARCHAR(100), -- fallback, language_detection, rag_adaptation, etc.
                            prompt_preview TEXT, -- Premier 200 chars du prompt
                            response_preview TEXT, -- Premier 200 chars de la réponse
                            
                            -- Performance
                            response_time_ms INTEGER,
                            success BOOLEAN DEFAULT TRUE,
                            error_message TEXT,
                            
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Table de résumés quotidiens OpenAI
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS daily_openai_summary (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(255),
                            date_only DATE NOT NULL,
                            
                            -- Compteurs
                            total_calls INTEGER DEFAULT 0,
                            successful_calls INTEGER DEFAULT 0,
                            failed_calls INTEGER DEFAULT 0,
                            total_tokens INTEGER DEFAULT 0,
                            
                            -- Coûts
                            total_cost_usd DECIMAL(10,6) DEFAULT 0,
                            total_cost_eur DECIMAL(10,6) DEFAULT 0,
                            
                            -- Breakdown par purpose
                            cost_by_purpose JSONB DEFAULT '{}',
                            
                            -- Performance
                            avg_response_time_ms INTEGER,
                            
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            UNIQUE(user_email, date_only)
                        );
                    """)
                    
                    # Table de métriques de performance serveur
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS server_performance_metrics (
                            id SERIAL PRIMARY KEY,
                            timestamp_hour TIMESTAMP NOT NULL, -- Heure tronquée
                            
                            -- Métriques générales
                            total_requests INTEGER DEFAULT 0,
                            successful_requests INTEGER DEFAULT 0,
                            failed_requests INTEGER DEFAULT 0,
                            avg_response_time_ms INTEGER,
                            max_response_time_ms INTEGER,
                            
                            -- Métriques par type
                            rag_requests INTEGER DEFAULT 0,
                            openai_requests INTEGER DEFAULT 0,
                            validation_rejections INTEGER DEFAULT 0,
                            quota_blocks INTEGER DEFAULT 0,
                            
                            -- Status de santé
                            health_status VARCHAR(20) DEFAULT 'healthy', -- healthy, degraded, critical
                            error_rate_percent DECIMAL(5,2) DEFAULT 0,
                            
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            UNIQUE(timestamp_hour)
                        );
                    """)
                    
                    # Indexes pour performance
                    indexes = [
                        "CREATE INDEX IF NOT EXISTS idx_questions_user_created ON user_questions_complete(user_email, created_at DESC);",
                        "CREATE INDEX IF NOT EXISTS idx_questions_status ON user_questions_complete(status, created_at);",
                        "CREATE INDEX IF NOT EXISTS idx_errors_category ON system_errors(category, severity, created_at);",
                        "CREATE INDEX IF NOT EXISTS idx_errors_resolved ON system_errors(resolved, created_at);",
                        "CREATE INDEX IF NOT EXISTS idx_openai_user_date ON openai_api_calls(user_email, created_at);",
                        "CREATE INDEX IF NOT EXISTS idx_openai_cost ON openai_api_calls(cost_usd, created_at);",
                        "CREATE INDEX IF NOT EXISTS idx_daily_summary_user ON daily_openai_summary(user_email, date_only);",
                        "CREATE INDEX IF NOT EXISTS idx_performance_hour ON server_performance_metrics(timestamp_hour);",
                    ]
                    
                    for index_sql in indexes:
                        cur.execute(index_sql)
                    
                    conn.commit()
                    logger.info("✅ Tables d'analytics et logging créées")
                    
        except Exception as e:
            logger.error(f"❌ Erreur création tables analytics: {e}")
            raise
    
    def log_question_response(
        self, 
        user_email: Optional[str],
        session_id: str,
        question: str,
        response_text: str = "",
        response_source: str = "unknown",
        status: str = "success",
        processing_time_ms: int = 0,
        confidence: float = None,
        completeness_score: float = None,
        language: str = "fr",
        intent: str = None,
        entities: Dict[str, Any] = None,
        error_info: Dict[str, Any] = None
    ) -> str:
        """Log une question/réponse complète"""
        try:
            question_id = f"{session_id}_{int(time.time() * 1000)}"
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_questions_complete (
                            user_email, session_id, question_id, question, response_text,
                            response_source, status, processing_time_ms, response_confidence,
                            completeness_score, language, intent, entities,
                            error_type, error_message, error_traceback
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_email, session_id, question_id, question[:2000], response_text[:5000],
                        response_source, status, processing_time_ms, confidence,
                        completeness_score, language, intent, json.dumps(entities or {}),
                        error_info.get("type") if error_info else None,
                        error_info.get("message") if error_info else None,
                        error_info.get("traceback") if error_info else None
                    ))
                    conn.commit()
                    
            return question_id
            
        except Exception as e:
            logger.error(f"❌ Erreur log question/réponse: {e}")
            return "error"
    
    def log_system_error(
        self,
        error_type: str,
        category: str,
        severity: str = "error",
        component: str = None,
        user_email: str = None,
        session_id: str = None,
        question_id: str = None,
        error_message: str = None,
        error_traceback: str = None,
        context_data: Dict[str, Any] = None
    ) -> None:
        """Log une erreur système"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO system_errors (
                            error_type, category, severity, component, user_email,
                            session_id, question_id, error_message, error_traceback, context_data
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        error_type, category, severity, component, user_email,
                        session_id, question_id, error_message, error_traceback,
                        json.dumps(context_data or {})
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"❌ Erreur log system error: {e}")
    
    def track_openai_call(
        self,
        user_email: str = None,
        session_id: str = None,
        question_id: str = None,
        call_type: str = "completion",
        model: str = "gpt-3.5-turbo",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        purpose: str = "fallback",
        prompt_preview: str = "",
        response_preview: str = "",
        response_time_ms: int = 0,
        success: bool = True,
        error_message: str = None
    ) -> None:
        """Track un appel OpenAI avec calcul des coûts"""
        try:
            # Calcul des coûts (tarifs OpenAI approximatifs)
            total_tokens = prompt_tokens + completion_tokens
            
            # Tarifs approximatifs GPT-3.5-turbo (USD pour 1K tokens)
            if "gpt-4" in model.lower():
                cost_per_1k_prompt = 0.03
                cost_per_1k_completion = 0.06
            else:  # GPT-3.5-turbo
                cost_per_1k_prompt = 0.0015
                cost_per_1k_completion = 0.002
            
            cost_usd = (prompt_tokens / 1000 * cost_per_1k_prompt) + (completion_tokens / 1000 * cost_per_1k_completion)
            cost_eur = cost_usd * 0.92  # Approximation EUR
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO openai_api_calls (
                            user_email, session_id, question_id, call_type, model,
                            prompt_tokens, completion_tokens, total_tokens, cost_usd, cost_eur,
                            purpose, prompt_preview, response_preview, response_time_ms,
                            success, error_message
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_email, session_id, question_id, call_type, model,
                        prompt_tokens, completion_tokens, total_tokens, cost_usd, cost_eur,
                        purpose, prompt_preview[:200], response_preview[:200], response_time_ms,
                        success, error_message
                    ))
                    
                    # Mise à jour du résumé quotidien
                    self._update_daily_openai_summary(cur, user_email, cost_usd, cost_eur, total_tokens, purpose, success, response_time_ms)
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"❌ Erreur track OpenAI call: {e}")
    
    def _update_daily_openai_summary(self, cur, user_email, cost_usd, cost_eur, tokens, purpose, success, response_time_ms):
        """Met à jour le résumé quotidien OpenAI"""
        try:
            today = datetime.now().date()
            
            # Upsert du résumé quotidien
            cur.execute("""
                INSERT INTO daily_openai_summary (
                    user_email, date_only, total_calls, successful_calls, failed_calls,
                    total_tokens, total_cost_usd, total_cost_eur, cost_by_purpose, avg_response_time_ms
                ) VALUES (%s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_email, date_only)
                DO UPDATE SET 
                    total_calls = daily_openai_summary.total_calls + 1,
                    successful_calls = daily_openai_summary.successful_calls + %s,
                    failed_calls = daily_openai_summary.failed_calls + %s,
                    total_tokens = daily_openai_summary.total_tokens + %s,
                    total_cost_usd = daily_openai_summary.total_cost_usd + %s,
                    total_cost_eur = daily_openai_summary.total_cost_eur + %s,
                    avg_response_time_ms = (daily_openai_summary.avg_response_time_ms * daily_openai_summary.total_calls + %s) / (daily_openai_summary.total_calls + 1),
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_email, today, 1 if success else 0, 0 if success else 1, tokens, cost_usd, cost_eur,
                json.dumps({purpose: float(cost_usd)}), response_time_ms,
                1 if success else 0, 0 if success else 1, tokens, cost_usd, cost_eur, response_time_ms
            ))
            
        except Exception as e:
            logger.error(f"❌ Erreur update daily summary: {e}")
    
    def get_user_analytics(self, user_email: str, days: int = 30) -> Dict[str, Any]:
        """Analytics complètes pour un utilisateur"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Questions/réponses
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_questions,
                            COUNT(*) FILTER (WHERE status = 'success') as successful_questions,
                            COUNT(*) FILTER (WHERE status = 'error') as failed_questions,
                            AVG(processing_time_ms) as avg_processing_time,
                            AVG(response_confidence) as avg_confidence
                        FROM user_questions_complete 
                        WHERE user_email = %s AND created_at >= %s
                    """, (user_email, start_date))
                    
                    questions_stats = dict(cur.fetchone() or {})
                    
                    # Coûts OpenAI
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_calls,
                            SUM(total_tokens) as total_tokens,
                            SUM(cost_usd) as total_cost_usd,
                            SUM(cost_eur) as total_cost_eur,
                            AVG(cost_usd) as avg_cost_per_call
                        FROM openai_api_calls 
                        WHERE user_email = %s AND created_at >= %s
                    """, (user_email, start_date))
                    
                    openai_stats = dict(cur.fetchone() or {})
                    
                    # Breakdown par purpose
                    cur.execute("""
                        SELECT 
                            purpose,
                            COUNT(*) as calls,
                            SUM(cost_usd) as cost_usd
                        FROM openai_api_calls 
                        WHERE user_email = %s AND created_at >= %s
                        GROUP BY purpose
                        ORDER BY cost_usd DESC
                    """, (user_email, start_date))
                    
                    cost_by_purpose = [dict(row) for row in cur.fetchall()]
                    
                    return {
                        "user_email": user_email,
                        "period_days": days,
                        "questions": questions_stats,
                        "openai_costs": openai_stats,
                        "cost_by_purpose": cost_by_purpose
                    }
                    
        except Exception as e:
            logger.error(f"❌ Erreur get user analytics: {e}")
            return {"error": str(e)}
    
    def log_server_performance(
        self,
        timestamp_hour: datetime,
        total_requests: int = 0,
        successful_requests: int = 0,
        failed_requests: int = 0,
        avg_response_time_ms: int = 0,
        max_response_time_ms: int = 0,
        health_status: str = "healthy",
        error_rate_percent: float = 0.0,
        rag_requests: int = 0,
        openai_requests: int = 0,
        validation_rejections: int = 0,
        quota_blocks: int = 0
    ) -> None:
        """Log des métriques de performance serveur par heure"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO server_performance_metrics (
                            timestamp_hour, total_requests, successful_requests, 
                            failed_requests, avg_response_time_ms, max_response_time_ms,
                            rag_requests, openai_requests, validation_rejections, quota_blocks,
                            health_status, error_rate_percent
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (timestamp_hour) 
                        DO UPDATE SET 
                            total_requests = EXCLUDED.total_requests,
                            successful_requests = EXCLUDED.successful_requests,
                            failed_requests = EXCLUDED.failed_requests,
                            avg_response_time_ms = EXCLUDED.avg_response_time_ms,
                            max_response_time_ms = EXCLUDED.max_response_time_ms,
                            rag_requests = EXCLUDED.rag_requests,
                            openai_requests = EXCLUDED.openai_requests,
                            validation_rejections = EXCLUDED.validation_rejections,
                            quota_blocks = EXCLUDED.quota_blocks,
                            health_status = EXCLUDED.health_status,
                            error_rate_percent = EXCLUDED.error_rate_percent
                    """, (
                        timestamp_hour, total_requests, successful_requests, failed_requests,
                        avg_response_time_ms, max_response_time_ms, rag_requests, openai_requests,
                        validation_rejections, quota_blocks, health_status, error_rate_percent
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"❌ Erreur log server performance: {e}")
    
    def get_server_performance_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Analytics de performance serveur sur les dernières heures"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Métriques globales
                    cur.execute("""
                        SELECT 
                            AVG(avg_response_time_ms) as avg_response_time,
                            AVG(error_rate_percent) as avg_error_rate,
                            SUM(total_requests) as total_requests,
                            SUM(failed_requests) as total_failures,
                            COUNT(*) FILTER (WHERE health_status = 'healthy') as healthy_hours,
                            COUNT(*) FILTER (WHERE health_status = 'degraded') as degraded_hours,
                            COUNT(*) FILTER (WHERE health_status = 'critical') as critical_hours
                        FROM server_performance_metrics 
                        WHERE timestamp_hour >= %s
                    """, (start_time,))
                    
                    global_stats = dict(cur.fetchone() or {})
                    
                    # Patterns par heure
                    cur.execute("""
                        SELECT 
                            EXTRACT(HOUR FROM timestamp_hour) as hour_of_day,
                            AVG(total_requests) as avg_requests,
                            MAX(total_requests) as peak_requests,
                            AVG(avg_response_time_ms) as avg_response_time
                        FROM server_performance_metrics 
                        WHERE timestamp_hour >= %s
                        GROUP BY EXTRACT(HOUR FROM timestamp_hour)
                        ORDER BY hour_of_day
                    """, (start_time,))
                    
                    hourly_patterns = [dict(row) for row in cur.fetchall()]
                    
                    # Déterminer le statut de santé actuel
                    current_health = "healthy"
                    if global_stats.get("avg_error_rate", 0) > 10:
                        current_health = "critical"
                    elif global_stats.get("avg_error_rate", 0) > 5:
                        current_health = "degraded"
                    
                    return {
                        "period_hours": hours,
                        "current_status": {
                            "overall_health": current_health,
                            "avg_response_time_ms": int(global_stats.get("avg_response_time", 0) or 0),
                            "error_rate_percent": round(global_stats.get("avg_error_rate", 0) or 0, 2)
                        },
                        "global_stats": global_stats,
                        "hourly_usage_patterns": hourly_patterns
                    }
                    
        except Exception as e:
            logger.error(f"❌ Erreur get server performance analytics: {e}")
            return {"error": str(e)}

# Singleton
_analytics_manager = None

def get_analytics_manager() -> AnalyticsManager:
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = AnalyticsManager()
    return _analytics_manager

# ========== FONCTION POUR MAIN.PY ==========

def get_analytics():
    """Fonction analytics pour compatibilité avec main.py"""
    try:
        analytics = get_analytics_manager()
        return {
            "status": "analytics_available",
            "tables_created": True,
            "dsn_configured": bool(analytics.dsn)
        }
    except Exception as e:
        return {
            "status": "analytics_error",
            "error": str(e)
        }

# ========== FONCTIONS HELPER POUR MAIN.PY ==========

def log_server_performance(**kwargs) -> None:
    """Fonction helper pour logger les performances serveur depuis main.py"""
    try:
        analytics = get_analytics_manager()
        analytics.log_server_performance(**kwargs)
    except Exception as e:
        logger.error(f"❌ Erreur log server performance helper: {e}")

def get_server_analytics(hours: int = 24) -> Dict[str, Any]:
    """Fonction helper pour récupérer les analytics serveur depuis main.py"""
    try:
        analytics = get_analytics_manager()
        return analytics.get_server_performance_analytics(hours)
    except Exception as e:
        logger.error(f"❌ Erreur get server analytics: {e}")
        return {"error": str(e)}

# ========== FONCTIONS MIDDLEWARE POUR EXPERT.PY ==========

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
        logger.error(f"❌ Erreur log question to analytics: {e}")

def track_openai_call(
    user_email: str = None,
    session_id: str = None,
    question_id: str = None,
    call_type: str = "completion",
    model: str = "gpt-3.5-turbo",
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
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            purpose=purpose,
            response_time_ms=response_time_ms,
            success=success
        )
    except Exception as e:
        logger.error(f"❌ Erreur track OpenAI call: {e}")

# ========== ENDPOINTS ANALYTICS ==========

@router.get("/analytics/dashboard")
def analytics_dashboard(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dashboard analytics (admin only)"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        analytics = get_analytics_manager()
        # Implémentation du dashboard admin
        return {
            "status": "dashboard_available",
            "message": "Dashboard analytics à implémenter"
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/analytics/my-usage")
def my_usage_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics personnelles de l'utilisateur"""
    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")
    
    try:
        analytics = get_analytics_manager()
        return analytics.get_user_analytics(user_email, days)
    except Exception as e:
        return {"error": str(e)}

@router.get("/analytics/openai-costs")
def openai_costs_analytics(
    days: int = Query(30, ge=1, le=365),
    user_email: str = Query(None),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics des coûts OpenAI"""
    
    # Si user_email spécifié, vérifier les permissions
    if user_email:
        if current_user.get("email") != user_email and not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        user_email = current_user.get("email")
    
    if not user_email:
        raise HTTPException(status_code=400, detail="User email required")
    
    try:
        analytics = get_analytics_manager()
        return analytics.get_user_analytics(user_email, days)
    except Exception as e:
        return {"error": str(e)}

@router.get("/analytics/performance")
def server_performance_analytics(
    hours: int = Query(24, ge=1, le=168),  # Max 7 jours
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics de performance serveur (admin only)"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        analytics = get_analytics_manager()
        return analytics.get_server_performance_analytics(hours)
    except Exception as e:
        return {"error": str(e)}

@router.get("/health-check")
def analytics_health_check() -> Dict[str, Any]:
    """Health check du système analytics"""
    try:
        analytics = get_analytics_manager()
        return {
            "status": "healthy",
            "analytics_available": True,
            "database_connected": bool(analytics.dsn),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "analytics_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }