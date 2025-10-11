"""
API Stats Fast - CORRIGÉ pour nouvelle architecture
====================================================
PostgreSQL: conversations, feedback, invitations
Supabase: users (via helper function)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from psycopg2.extras import RealDictCursor

# Import du nouveau module database
from app.core.database import (
    get_pg_connection,
    get_user_from_supabase,
    check_databases_health
)

logger = logging.getLogger(__name__)
logger.info("STATS_FAST.PY VERSION FIXÉE - Architecture PostgreSQL + Supabase")

# Import auth
try:
    from app.api.v1.auth import get_current_user
    AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Auth module non disponible: {e}")
    get_current_user = None
    AUTH_AVAILABLE = False

router = APIRouter(prefix="/stats-fast", tags=["statistics-fast"])

# Cache local
_local_cache = {}
_cache_timestamps = {}


def set_local_cache(key: str, data: Any, ttl_minutes: int = 5):
    """Stocke dans le cache local avec TTL"""
    _local_cache[key] = data
    _cache_timestamps[key] = datetime.now()


def get_local_cache(key: str) -> Optional[Any]:
    """Récupère du cache local si valide"""
    if key not in _local_cache or key not in _cache_timestamps:
        return None
    if datetime.now() - _cache_timestamps[key] > timedelta(minutes=5):
        _local_cache.pop(key, None)
        _cache_timestamps.pop(key, None)
        return None
    return _local_cache[key]


# ============================================================================
# HELPER: Enrichir les données utilisateur avec Supabase
# ============================================================================

def enrich_users_data(user_ids: list[str]) -> Dict[str, Dict]:
    """
    Récupère les infos utilisateurs depuis Supabase pour une liste d'IDs.

    Returns:
        Dict[user_id, {email, first_name, last_name, plan}]
    """
    logger.info(f"🔍 [ENRICHMENT] Starting enrichment for {len(user_ids)} user IDs: {user_ids}")
    users_data = {}

    for user_id in user_ids:
        logger.info(f"🔍 [ENRICHMENT] Fetching user data for user_id: {user_id}")
        user = get_user_from_supabase(user_id)

        if user:
            logger.info(f"✅ [ENRICHMENT] User found: {user}")
            users_data[user_id] = {
                "email": user.get("email", ""),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "plan": user.get("plan", "free"),
                "user_type": user.get("user_type", "user")
            }
            logger.info(f"✅ [ENRICHMENT] Enriched data for {user_id}: {users_data[user_id]}")
        else:
            logger.warning(f"❌ [ENRICHMENT] User NOT found in Supabase for user_id: {user_id}")
            users_data[user_id] = {
                "email": user_id,  # Fallback: utiliser l'ID
                "first_name": "",
                "last_name": "",
                "plan": "free",
                "user_type": "user"
            }
            logger.warning(f"⚠️ [ENRICHMENT] Using fallback data for {user_id}: {users_data[user_id]}")

    logger.info(f"🔍 [ENRICHMENT] Enrichment complete. Returning {len(users_data)} users")
    return users_data


# ============================================================================
# BILLING & TOP USERS
# ============================================================================

async def get_billing_plans_data() -> Dict[str, Any]:
    """
    Récupère les top users depuis PostgreSQL
    et enrichit avec données Supabase
    """
    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Top utilisateurs depuis PostgreSQL (conversations uniquement)
                cur.execute(
                    """
                    SELECT
                        user_id,
                        COUNT(*) as question_count
                    FROM conversations
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                        AND user_id IS NOT NULL
                        AND question IS NOT NULL
                        AND response IS NOT NULL
                        AND status = 'active'
                    GROUP BY user_id
                    ORDER BY question_count DESC
                    LIMIT 10
                    """
                )

                top_users_raw = cur.fetchall()

                # Extraire les user_ids
                user_ids = [str(row["user_id"]) for row in top_users_raw]

                # Enrichir avec données Supabase
                users_info = enrich_users_data(user_ids)

                # Combiner les données
                top_users = []
                for row in top_users_raw:
                    user_id = str(row["user_id"])
                    user_info = users_info.get(user_id, {})

                    top_users.append({
                        "email": user_info.get("email", user_id)[:50],
                        "first_name": user_info.get("first_name", "")[:50],
                        "last_name": user_info.get("last_name", "")[:50],
                        "question_count": row["question_count"],
                        "plan": user_info.get("plan", "free")
                    })

                # Distribution des plans
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) as user_count
                    FROM conversations
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                        AND user_id IS NOT NULL
                    """
                )

                result = cur.fetchone()
                user_count = result["user_count"] if result else 0

                return {
                    "plans": {"free": {"user_count": user_count, "revenue": 0}},
                    "total_revenue": 0.0,
                    "top_users": top_users
                }

    except Exception as e:
        logger.error(f"Erreur récupération billing plans: {e}")
        return {
            "plans": {"free": {"user_count": 0, "revenue": 0}},
            "total_revenue": 0.0,
            "top_users": []
        }


# ============================================================================
# USAGE STATS
# ============================================================================

async def get_enhanced_usage_stats() -> Dict[str, Any]:
    """Statistiques d'usage depuis PostgreSQL"""
    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Stats principales
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_questions,
                        COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as questions_today,
                        COUNT(*) FILTER (WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)) as questions_this_month,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM conversations
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                        AND status = 'active'
                    """
                )

                main_result = cur.fetchone()

                # Distribution des sources
                cur.execute(
                    """
                    SELECT
                        response_source,
                        COUNT(*) as count
                    FROM conversations
                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                        AND response_source IS NOT NULL
                        AND status = 'active'
                    GROUP BY response_source
                    ORDER BY count DESC
                    """
                )

                source_distribution = {}
                for row in cur.fetchall():
                    source = row["response_source"] or "unknown"
                    if source == "rag":
                        source_distribution["rag_retriever"] = row["count"]
                    elif source == "openai_fallback":
                        source_distribution["openai_fallback"] = row["count"]
                    elif source in ["table_lookup", "perfstore"]:
                        source_distribution["perfstore"] = source_distribution.get("perfstore", 0) + row["count"]
                    else:
                        source_distribution[source] = row["count"]

                # Monthly breakdown
                cur.execute(
                    """
                    SELECT
                        TO_CHAR(created_at, 'YYYY-MM') as month,
                        COUNT(*) as count
                    FROM conversations
                    WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
                        AND status = 'active'
                    GROUP BY TO_CHAR(created_at, 'YYYY-MM')
                    ORDER BY month DESC
                    """
                )

                monthly_breakdown = {row["month"]: row["count"] for row in cur.fetchall()}

                return {
                    "unique_users": main_result["unique_users"] or 0,
                    "total_questions": main_result["total_questions"] or 0,
                    "questions_today": main_result["questions_today"] or 0,
                    "questions_this_month": main_result["questions_this_month"] or 0,
                    "source_distribution": source_distribution,
                    "monthly_breakdown": monthly_breakdown
                }

    except Exception as e:
        logger.error(f"Erreur récupération usage stats: {e}")
        return {
            "unique_users": 0,
            "total_questions": 0,
            "questions_today": 0,
            "questions_this_month": 0,
            "source_distribution": {},
            "monthly_breakdown": {}
        }


# ============================================================================
# PERFORMANCE STATS
# ============================================================================

async def get_performance_stats() -> Dict[str, Any]:
    """Statistiques de performance depuis PostgreSQL"""
    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                cur.execute(
                    """
                    SELECT
                        AVG(processing_time_ms / 1000.0) as avg_response_time,
                        MIN(processing_time_ms / 1000.0) as min_response_time,
                        MAX(processing_time_ms / 1000.0) as max_response_time,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY processing_time_ms / 1000.0) as median_response_time,
                        COUNT(*) as response_time_count
                    FROM conversations
                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                        AND processing_time_ms IS NOT NULL
                        AND status = 'active'
                    """
                )

                perf_result = cur.fetchone()

                return {
                    "avg_response_time": float(perf_result["avg_response_time"] or 0),
                    "median_response_time": float(perf_result["median_response_time"] or 0),
                    "min_response_time": float(perf_result["min_response_time"] or 0),
                    "max_response_time": float(perf_result["max_response_time"] or 0),
                    "response_time_count": perf_result["response_time_count"] or 0,
                    "openai_costs": 0.0,  # TODO: intégrer billing OpenAI
                    "error_count": 0,
                    "cache_hit_rate": 85.0
                }

    except Exception as e:
        logger.error(f"Erreur récupération performance stats: {e}")
        return {
            "avg_response_time": 0.0,
            "median_response_time": 0.0,
            "min_response_time": 0.0,
            "max_response_time": 0.0,
            "response_time_count": 0,
            "openai_costs": 0.0,
            "error_count": 0,
            "cache_hit_rate": 0.0
        }


# ============================================================================
# DASHBOARD ENDPOINT
# ============================================================================

@router.get("/dashboard")
async def get_dashboard_fast(
    current_user: dict = Depends(get_current_user) if AUTH_AVAILABLE else None,
) -> Dict[str, Any]:
    """DASHBOARD COMPLET avec architecture corrigée"""

    cache_key = f"dashboard:{current_user.get('email') if current_user else 'anon'}"
    cached = get_local_cache(cache_key)
    if cached:
        logger.info("Dashboard cache HIT")
        return cached

    try:
        # Récupérer données en parallèle
        usage_stats, performance_stats, billing_plans = await asyncio.gather(
            get_enhanced_usage_stats(),
            get_performance_stats(),
            get_billing_plans_data(),
            return_exceptions=True
        )

        # Gérer les erreurs
        if isinstance(usage_stats, Exception):
            usage_stats = {"unique_users": 0, "total_questions": 0}
        if isinstance(performance_stats, Exception):
            performance_stats = {"avg_response_time": 0.0}
        if isinstance(billing_plans, Exception):
            billing_plans = {"plans": {}, "total_revenue": 0.0, "top_users": []}

        response = {
            "cache_info": {
                "is_available": True,
                "last_update": datetime.now().isoformat(),
                "cache_age_minutes": 0,
                "performance_gain": "95%",
                "next_update": (datetime.now() + timedelta(hours=1)).isoformat()
            },
            "system_stats": {
                "system_health": {
                    "uptime_hours": 24,
                    "total_requests": usage_stats.get("total_questions", 0),
                    "error_rate": 0,
                    "rag_status": {"global": True, "broiler": True, "layer": True}
                },
                "billing_stats": {
                    "plans_available": len(billing_plans.get("plans", {})),
                    "plan_names": list(billing_plans.get("plans", {}).keys())
                },
                "features_enabled": {
                    "analytics": True,
                    "billing": True,
                    "authentication": AUTH_AVAILABLE,
                    "openai_fallback": True
                }
            },
            "usage_stats": usage_stats,
            "billing_stats": billing_plans,
            "performance_stats": performance_stats
        }

        set_local_cache(cache_key, response, ttl_minutes=5)
        logger.info(f"Dashboard généré: {usage_stats.get('unique_users', 0)} users")
        return response

    except Exception as e:
        logger.error(f"Erreur dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur dashboard: {str(e)}")


# ============================================================================
# QUESTIONS ENDPOINT - Pour l'onglet Q&A
# ============================================================================

@router.get("/questions")
async def get_questions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user) if AUTH_AVAILABLE else None,
) -> Dict[str, Any]:
    """
    Récupère l'historique des questions pour l'utilisateur connecté

    Args:
        page: Numéro de page (commence à 1)
        limit: Nombre de résultats par page
        current_user: Utilisateur authentifié (injecté par dependency)

    Returns:
        {
            "questions": [...],
            "total": int,
            "page": int,
            "limit": int,
            "has_more": bool
        }
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentification requise")

    # Essayer plusieurs clés possibles pour user_id
    user_id = (
        current_user.get("user_id") or  # Clé utilisée par get_current_user
        current_user.get("sub") or      # Clé standard JWT
        current_user.get("id")          # Fallback
    )
    if not user_id:
        logger.error(f"❌ [QUESTIONS] User ID manquant. current_user keys: {list(current_user.keys())}")
        raise HTTPException(status_code=400, detail="User ID manquant")

    logger.info(f"🔍 [QUESTIONS] Fetching questions for user_id: {user_id}")
    logger.info(f"🔍 [QUESTIONS] Current user data: {current_user}")

    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Calculer l'offset
                offset = (page - 1) * limit

                # Compter le total
                logger.info(f"🔍 [QUESTIONS] Counting conversations for user_id: {user_id}")
                cur.execute(
                    """
                    SELECT COUNT(*) as total
                    FROM conversations
                    WHERE user_id = %s
                        AND status = 'active'
                    """,
                    (user_id,)
                )

                total_result = cur.fetchone()
                total = total_result["total"] if total_result else 0
                logger.info(f"✅ [QUESTIONS] Found {total} total conversations for user_id: {user_id}")

                # Récupérer les questions paginées
                logger.info(f"🔍 [QUESTIONS] Fetching paginated questions (page={page}, limit={limit}, offset={offset})")
                cur.execute(
                    """
                    SELECT
                        id::text as id,
                        session_id,
                        user_id::text as user_email,
                        question,
                        response as response_text,
                        response_source,
                        response_confidence,
                        COALESCE(processing_time_ms, 1000.0) as processing_time_ms,
                        sources,
                        mode,
                        title,
                        preview,
                        last_message_preview,
                        message_count,
                        language,
                        feedback,
                        feedback_comment,
                        created_at,
                        updated_at
                    FROM conversations
                    WHERE user_id = %s
                        AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset)
                )

                questions = []
                for row in cur.fetchall():
                    questions.append({
                        "id": row["id"],
                        "session_id": str(row["session_id"]),
                        "user_email": row["user_email"],
                        "question": row["question"],
                        "response_text": row["response_text"],
                        "response_source": row["response_source"],
                        "response_confidence": float(row["response_confidence"] or 0.85),
                        "processing_time_ms": float(row["processing_time_ms"] or 1000.0),
                        "sources": row["sources"] or [],
                        "mode": row["mode"] or "broiler",
                        "title": row["title"],
                        "preview": row["preview"],
                        "last_message_preview": row["last_message_preview"],
                        "message_count": row["message_count"] or 1,
                        "language": row["language"] or "fr",
                        "feedback": row["feedback"],
                        "feedback_comment": row["feedback_comment"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                    })

                logger.info(f"Questions récupérées pour {user_id}: {len(questions)}/{total}")

                return {
                    "questions": questions,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "has_more": (offset + limit) < total
                }

    except Exception as e:
        logger.error(f"Erreur récupération questions: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur récupération questions: {str(e)}")


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def stats_health() -> Dict[str, Any]:
    """Health check des bases de données"""
    try:
        db_health = check_databases_health()

        return {
            "status": "healthy" if all(
                db["status"] == "healthy" for db in db_health.values()
            ) else "degraded",
            "databases": db_health,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return {
            "status": "error",
            "error": str(e)[:100],
            "timestamp": datetime.now().isoformat()
        }


logger.info("✅ stats_fast.py chargé - Architecture PostgreSQL + Supabase")
