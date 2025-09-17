# AMÉLIORATION RECOMMANDÉE pour admin.py - VERSION CORRIGÉE

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)  # CORRECTION: Import HTTPException
from typing import Any, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/kpis")
def kpis() -> Dict[str, Any]:
    return {"status": "ok", "version": "ready-patch"}


@router.get("/stats")
async def admin_stats(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    🆕 ENDPOINT ADMIN STATS COMPLET
    Récupère les vraies statistiques système pour le dashboard
    """
    # Vérifier les permissions admin
    if (
        not current_user.get("is_admin", False)
        and current_user.get("user_type") != "super_admin"
    ):
        raise HTTPException(
            status_code=403, detail="Admin access required"
        )  # CORRECTION: HTTPException maintenant importé

    try:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            return {"error": "Database not configured"}

        with psycopg2.connect(dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # 1. STATS GÉNÉRALES DU SYSTÈME
                cur.execute(
                    """
                    SELECT 
                        COUNT(DISTINCT user_email) as total_users,
                        COUNT(*) as total_questions,
                        COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE) as questions_today,
                        COUNT(*) FILTER (WHERE created_at >= date_trunc('month', CURRENT_DATE)) as questions_this_month,
                        AVG(processing_time_ms) as avg_response_time_ms
                    FROM user_questions_complete
                """
                )
                system_stats = dict(cur.fetchone() or {})

                # 2. DISTRIBUTION DES SOURCES
                cur.execute(
                    """
                    SELECT 
                        response_source,
                        COUNT(*) as count,
                        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                    FROM user_questions_complete
                    WHERE response_source IS NOT NULL
                    GROUP BY response_source
                    ORDER BY count DESC
                """
                )
                source_distribution = [dict(row) for row in cur.fetchall()]

                # 3. TOP UTILISATEURS
                cur.execute(
                    """
                    SELECT 
                        user_email,
                        COUNT(*) as question_count,
                        MAX(created_at) as last_activity
                    FROM user_questions_complete
                    WHERE user_email IS NOT NULL AND user_email != ''
                    GROUP BY user_email
                    ORDER BY question_count DESC
                    LIMIT 10
                """
                )
                top_users = [dict(row) for row in cur.fetchall()]

                # 4. ACTIVITÉ PAR JOUR (7 derniers jours)
                cur.execute(
                    """
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as questions,
                        COUNT(DISTINCT user_email) as unique_users
                    FROM user_questions_complete
                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """
                )
                daily_activity = [dict(row) for row in cur.fetchall()]

                # 5. STATS DE PERFORMANCE
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'success') as successful_requests,
                        COUNT(*) FILTER (WHERE status = 'error') as failed_requests,
                        COUNT(*) as total_requests,
                        ROUND(
                            COUNT(*) FILTER (WHERE status = 'error') * 100.0 / NULLIF(COUNT(*), 0), 
                            2
                        ) as error_rate_percent
                    FROM user_questions_complete
                    WHERE created_at >= CURRENT_DATE - INTERVAL '24 hours'
                """
                )
                performance_stats = dict(cur.fetchone() or {})

                # 6. FEEDBACK STATS
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) FILTER (WHERE feedback = 1) as positive_feedback,
                        COUNT(*) FILTER (WHERE feedback = -1) as negative_feedback,
                        COUNT(*) FILTER (WHERE feedback IS NOT NULL) as total_feedback,
                        COUNT(*) FILTER (WHERE feedback_comment IS NOT NULL) as feedback_with_comments
                    FROM user_questions_complete
                """
                )
                feedback_stats = dict(cur.fetchone() or {})

                # Calculer le taux de satisfaction
                total_feedback = feedback_stats.get("total_feedback", 0)
                satisfaction_rate = 0
                if total_feedback > 0:
                    satisfaction_rate = round(
                        (feedback_stats.get("positive_feedback", 0) / total_feedback)
                        * 100,
                        1,
                    )

                return {
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "system_overview": {
                        "total_users": system_stats.get("total_users", 0),
                        "total_questions": system_stats.get("total_questions", 0),
                        "questions_today": system_stats.get("questions_today", 0),
                        "questions_this_month": system_stats.get(
                            "questions_this_month", 0
                        ),
                        "avg_response_time_ms": float(
                            system_stats.get("avg_response_time_ms", 0) or 0
                        ),
                    },
                    "source_distribution": source_distribution,
                    "top_users": top_users,
                    "daily_activity": daily_activity,
                    "performance": {
                        **performance_stats,
                        "uptime_hours": 24 * 7,  # TODO: Calculer le vrai uptime
                        "health_status": (
                            "healthy"
                            if performance_stats.get("error_rate_percent", 0) < 5
                            else "degraded"
                        ),
                    },
                    "feedback": {
                        **feedback_stats,
                        "satisfaction_rate": satisfaction_rate,
                    },
                }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
