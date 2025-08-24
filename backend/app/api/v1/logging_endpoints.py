# app/api/v1/logging_endpoints.py
# -*- coding: utf-8 -*-
"""
🌐 ENDPOINTS API POUR LE SYSTÈME DE LOGGING
📊 Tous les endpoints FastAPI pour analytics, debugging et administration
"""
import os
import logging
from typing import Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.v1.auth import get_current_user
from .logging_models import Permission
from .logging_permissions import has_permission
from .logging_helpers import get_analytics_manager
from .logging_cache import clear_analytics_cache, get_cache_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logging", tags=["logging"])


# ============================================================================
# 📊 ENDPOINTS PRINCIPAUX D'ANALYTICS
# ============================================================================

@router.get("/analytics/dashboard")
async def analytics_dashboard(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dashboard analytics (admin+ only)"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(
            status_code=403, 
            detail=f"Admin dashboard access required. Your role: {current_user.get('user_type', 'user')}"
        )
    
    try:
        analytics = get_analytics_manager()
        return {
            "status": "dashboard_available",
            "message": "Dashboard analytics à implémenter",
            "user_role": current_user.get("user_type"),
            "permissions": [p.value for p in has_permission.__globals__['ROLE_PERMISSIONS'].get(
                has_permission.__globals__['UserRole'](current_user.get("user_type", "user")), []
            )],
            "cache_stats": get_cache_stats()
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/analytics/my-usage")
async def my_usage_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics personnelles de l'utilisateur"""
    if not has_permission(current_user, Permission.VIEW_OWN_ANALYTICS):
        raise HTTPException(status_code=403, detail="View analytics permission required")
    
    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")
    
    try:
        analytics = get_analytics_manager()
        result = analytics.get_user_analytics(user_email, days)
        result["user_role"] = current_user.get("user_type")
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/analytics/openai-costs")
async def openai_costs_analytics(
    days: int = Query(30, ge=1, le=365),
    user_email: str = Query(None),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics des coûts OpenAI"""
    
    # Si user_email spécifié, vérifier les permissions
    if user_email:
        if (current_user.get("email") != user_email and 
            not has_permission(current_user, Permission.VIEW_ALL_ANALYTICS)):
            raise HTTPException(
                status_code=403, 
                detail="Permission to view other users' analytics required"
            )
    else:
        user_email = current_user.get("email")
    
    if not has_permission(current_user, Permission.VIEW_OPENAI_COSTS):
        raise HTTPException(status_code=403, detail="View OpenAI costs permission required")
    
    if not user_email:
        raise HTTPException(status_code=400, detail="User email required")
    
    try:
        analytics = get_analytics_manager()
        result = analytics.get_user_analytics(user_email, days)
        result["user_role"] = current_user.get("user_type")
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/analytics/performance")
async def server_performance_analytics(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics de performance serveur (admin+ only)"""
    if not has_permission(current_user, Permission.VIEW_SERVER_PERFORMANCE):
        raise HTTPException(
            status_code=403, 
            detail=f"Server performance access required. Your role: {current_user.get('user_type', 'user')}"
        )
    
    try:
        analytics = get_analytics_manager()
        result = analytics.get_server_performance_analytics(hours)
        result["requested_by_role"] = current_user.get("user_type")
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/my-permissions")
async def get_my_permissions(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Récupère les permissions de l'utilisateur connecté"""
    from .logging_models import UserRole, ROLE_PERMISSIONS
    
    user_type = current_user.get("user_type", "user")
    
    try:
        role = UserRole(user_type)
        permissions = ROLE_PERMISSIONS.get(role, [])
    except ValueError:
        permissions = ROLE_PERMISSIONS.get(UserRole.USER, [])
    
    return {
        "user_email": current_user.get("email"),
        "user_type": user_type,
        "is_admin": current_user.get("is_admin", False),
        "permissions": [p.value for p in permissions],
        "available_endpoints": {
            "analytics_dashboard": has_permission(current_user, Permission.ADMIN_DASHBOARD),
            "my_usage": has_permission(current_user, Permission.VIEW_OWN_ANALYTICS),
            "openai_costs": has_permission(current_user, Permission.VIEW_OPENAI_COSTS),
            "server_performance": has_permission(current_user, Permission.VIEW_SERVER_PERFORMANCE)
        }
    }


@router.get("/health-check")
def analytics_health_check() -> Dict[str, Any]:
    """Health check du système analytics"""
    try:
        analytics = get_analytics_manager()
        cache_stats = get_cache_stats()
        
        return {
            "status": "healthy",
            "analytics_available": True,
            "database_connected": bool(analytics.dsn),
            "tables_ready": os.getenv("ANALYTICS_TABLES_READY", "false").lower() == "true",
            "cache_enabled": True,
            "cache_stats": cache_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "analytics_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# 🛠️ ENDPOINTS D'ADMINISTRATION
# ============================================================================

@router.post("/admin/initialize-tables")
async def initialize_analytics_tables(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Initialisation manuelle sécurisée des tables (super_admin only)"""
    if current_user.get("user_type") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin required")
    
    try:
        analytics = get_analytics_manager(force_init=True)
        success = analytics.ensure_tables_if_needed()
        
        return {
            "status": "success" if success else "error",
            "message": "Tables d'analytics créées et initialisées",
            "tables_ready": os.getenv("ANALYTICS_TABLES_READY", "false").lower() == "true",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/admin/clear-cache")
async def clear_analytics_cache_endpoint(
    pattern: str = Query(None, description="Pattern optionnel pour nettoyer seulement certaines entrées"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Nettoyage manuel du cache (admin+)"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        stats_before = get_cache_stats()
        clear_analytics_cache(pattern)
        stats_after = get_cache_stats()
        
        return {
            "status": "success",
            "message": f"Cache nettoyé (pattern: {pattern or 'all'})",
            "entries_before": stats_before["total_entries"],
            "entries_after": stats_after["total_entries"],
            "entries_removed": stats_before["total_entries"] - stats_after["total_entries"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/admin/cache-stats")
async def get_cache_statistics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Statistiques du cache (admin+)"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        from .logging_cache import _analytics_cache, _cache_lock, CACHE_TTL_SECONDS
        
        stats = get_cache_stats()
        
        # Détails des clés en cache
        with _cache_lock:
            cache_keys = list(_analytics_cache.keys())
            cache_details = {}
            for key in cache_keys:
                cached_time, _ = _analytics_cache[key]
                age_seconds = (datetime.now() - cached_time).total_seconds()
                cache_details[key] = {
                    "age_seconds": round(age_seconds, 1),
                    "expired": age_seconds > CACHE_TTL_SECONDS
                }
        
        return {
            "status": "success",
            "cache_stats": stats,
            "cache_details": cache_details,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/system-info")
async def get_system_info(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Informations système pour debugging et monitoring"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        analytics = get_analytics_manager()
        cache_stats = get_cache_stats()
        
        # Variables d'environnement importantes
        env_vars = {
            "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
            "ANALYTICS_TABLES_READY": os.getenv("ANALYTICS_TABLES_READY", "false"),
            "ANALYTICS_CACHE_TTL": os.getenv("ANALYTICS_CACHE_TTL", "300"),
            "FORCE_ANALYTICS_INIT": os.getenv("FORCE_ANALYTICS_INIT", "false"),
            "DISABLE_ANALYTICS_AUTO_INIT": os.getenv("DISABLE_ANALYTICS_AUTO_INIT", "false"),
            "DEFAULT_MODEL": os.getenv("DEFAULT_MODEL", "gpt-5")
        }
        
        # Status des tables
        table_status = {}
        try:
            with psycopg2.connect(analytics.dsn) as conn:
                with conn.cursor() as cur:
                    tables = [
                        "user_questions_complete",
                        "system_errors", 
                        "openai_api_calls",
                        "daily_openai_summary",
                        "server_performance_metrics"
                    ]
                    
                    for table in tables:
                        try:
                            cur.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cur.fetchone()[0]
                            table_status[table] = {"exists": True, "rows": count}
                        except:
                            table_status[table] = {"exists": False, "rows": 0}
        except Exception as e:
            table_status["error"] = str(e)
        
        return {
            "status": "success",
            "analytics_manager": {
                "initialized": analytics is not None,
                "dsn_configured": bool(analytics.dsn) if analytics else False
            },
            "cache_system": cache_stats,
            "environment_variables": env_vars,
            "database_tables": table_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# 📊 ENDPOINT DES QUESTIONS
# ============================================================================

@router.get("/questions")
async def get_questions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Récupère les questions avec pagination"""
    
    # Log de debug
    logger.info(f"Endpoint /questions appelé par {current_user.get('email')} (page={page}, limit={limit})")
    
    if not has_permission(current_user, Permission.VIEW_ALL_ANALYTICS):
        logger.warning(f"Permission refusée pour {current_user.get('email')}")
        raise HTTPException(status_code=403, detail="Permission VIEW_ALL_ANALYTICS required")
    
    try:
        analytics = get_analytics_manager()
        
        with psycopg2.connect(analytics.dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                # Compter le total avec gestion d'erreur
                try:
                    cur.execute("SELECT COUNT(*) as total FROM user_questions_complete")
                    count_result = cur.fetchone()
                    total_count = count_result["total"] if count_result else 0
                    logger.info(f"Total questions trouvées: {total_count}")
                except Exception as count_error:
                    logger.error(f"Erreur count: {count_error}")
                    return {
                        "error": f"Count failed: {str(count_error)}",
                        "questions": [],
                        "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0}
                    }
                
                if total_count == 0:
                    return {
                        "questions": [],
                        "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0},
                        "message": "Aucune question trouvée"
                    }
                
                # Récupérer les questions avec gestion d'erreur
                try:
                    offset = (page - 1) * limit
                    cur.execute("""
                        SELECT 
                            id,
                            user_email,
                            question,
                            response_text,
                            response_source,
                            response_confidence,
                            processing_time_ms,
                            language,
                            session_id,
                            created_at,
                            status
                        FROM user_questions_complete 
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (