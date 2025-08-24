# app/api/v1/stats_fast.py
# -*- coding: utf-8 -*-
"""
🔬 STATS FAST - VERSION DEBUG MINIMALE
🚨 EMERGENCY: Version ultra-simple pour identifier la cause du problème mémoire
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

# ⚠️ IMPORTS MINIMAUX - Tester un par un
try:
    from app.api.v1.auth import get_current_user
    auth_import_ok = True
except Exception as e:
    auth_import_ok = False
    auth_error = str(e)

try:
    from app.api.v1.logging import has_permission, Permission
    permissions_import_ok = True
except Exception as e:
    permissions_import_ok = False
    permissions_error = str(e)

# ❌ DÉSACTIVER TEMPORAIREMENT - Suspect principal
# from app.api.v1.stats_cache import get_stats_cache

router = APIRouter(tags=["statistics-fast"])
logger = logging.getLogger(__name__)

# ==================== DEBUG ENDPOINT ====================

@router.get("/debug/memory")
async def debug_memory_usage() -> Dict[str, Any]:
    """🔬 Debug: État mémoire et imports"""
    import psutil
    import os
    
    try:
        # Mémoire du processus actuel
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            "status": "debug_active",
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": process.memory_percent()
            },
            "imports": {
                "auth_import_ok": auth_import_ok,
                "auth_error": auth_error if not auth_import_ok else None,
                "permissions_import_ok": permissions_import_ok,
                "permissions_error": permissions_error if not permissions_import_ok else None,
                "stats_cache_disabled": True
            },
            "system": {
                "available_memory_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2),
                "total_memory_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2)
            }
        }
    except Exception as e:
        return {
            "status": "debug_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== ENDPOINTS MINIMAUX ====================

@router.get("/health")
async def minimal_health() -> Dict[str, Any]:
    """🏥 Health check ultra-simple"""
    return {
        "status": "minimal_healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Stats fast running in debug mode",
        "memory_safe": True
    }

@router.get("/dashboard")
async def minimal_dashboard(
    current_user: dict = Depends(get_current_user) if auth_import_ok else None
) -> Dict[str, Any]:
    """📊 Dashboard ultra-minimal"""
    
    # Si pas d'auth, données publiques
    if not auth_import_ok or not current_user:
        user_info = "no_auth"
    else:
        user_info = current_user.get("email", "unknown")
    
    # Données statiques minimales (pas de cache, pas de DB)
    return {
        "cache_info": {
            "is_available": False,
            "last_update": None,
            "cache_age_minutes": 0,
            "performance_gain": "0%",
            "next_update": None,
            "debug_mode": True,
            "message": "Mode debug - pas de cache actif"
        },
        "systemStats": {
            "system_health": {
                "uptime_hours": 0,
                "total_requests": 0,
                "error_rate": 0.0,
                "rag_status": {"global": False, "broiler": False, "layer": False}
            },
            "debug_info": {
                "memory_safe_mode": True,
                "cache_disabled": True,
                "user": user_info
            }
        },
        "usageStats": {
            "unique_users": 0,
            "total_questions": 0,
            "questions_today": 0,
            "questions_this_month": 0,
            "source_distribution": {},
            "debug": "Données temporaires"
        },
        "billingStats": {"plans": {}, "total_revenue": 0.0, "top_users": []},
        "performanceStats": {
            "avg_response_time": 0.0,
            "median_response_time": 0.0,
            "openai_costs": 0.0,
            "cache_hit_rate": 0.0,
            "debug_mode": True
        },
        "meta": {
            "debug": True,
            "timestamp": datetime.now().isoformat(),
            "data_source": "minimal_static"
        }
    }

@router.get("/invitations")
async def minimal_invitations(
    current_user: dict = Depends(get_current_user) if auth_import_ok else None
) -> Dict[str, Any]:
    """📧 Invitations ultra-minimal"""
    
    return {
        "cache_info": {
            "is_available": False,
            "debug_mode": True,
            "message": "Mode debug - utilisez /api/v1/invitations/stats"
        },
        "invitation_stats": {
            "total_invitations_sent": 0,
            "total_invitations_accepted": 0,
            "acceptance_rate": 0.0,
            "unique_inviters": 0,
            "top_inviters": [],
            "top_accepted": [],
            "debug": "Endpoint en mode debug"
        }
    }

@router.get("/invitations/stats")
async def minimal_invitations_stats(
    current_user: dict = Depends(get_current_user) if auth_import_ok else None
) -> Dict[str, Any]:
    """📧 Invitations stats ultra-minimal"""
    return await minimal_invitations(current_user)

@router.get("/questions")
async def minimal_questions(
    current_user: dict = Depends(get_current_user) if auth_import_ok else None
) -> Dict[str, Any]:
    """📋 Questions ultra-minimal"""
    
    return {
        "cache_info": {
            "is_available": False,
            "debug_mode": True,
            "message": "Mode debug - pas de données"
        },
        "questions": [],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 0,
            "pages": 0,
            "has_next": False,
            "has_prev": False
        },
        "meta": {
            "retrieved": 0,
            "debug": True,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.get("/performance")
async def minimal_performance(
    current_user: dict = Depends(get_current_user) if auth_import_ok else None
) -> Dict[str, Any]:
    """⚡ Performance ultra-minimal"""
    
    return {
        "period_hours": 24,
        "current_status": {
            "overall_health": "debug",
            "avg_response_time_ms": 0,
            "error_rate_percent": 0
        },
        "global_stats": {},
        "debug": {
            "mode": "minimal",
            "cache_disabled": True,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.get("/openai-costs/current")
async def minimal_openai_costs(
    current_user: dict = Depends(get_current_user) if auth_import_ok else None
) -> Dict[str, Any]:
    """💰 OpenAI costs ultra-minimal"""
    
    return {
        "total_cost": 0.0,
        "total_tokens": 0,
        "api_calls": 0,
        "models_usage": {},
        "debug": {
            "mode": "minimal",
            "cache_disabled": True,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.get("/my-analytics")
async def minimal_my_analytics(
    current_user: dict = Depends(get_current_user) if auth_import_ok else None
) -> Dict[str, Any]:
    """📈 Analytics ultra-minimal"""
    
    user_email = "debug_user"
    if current_user:
        user_email = current_user.get("email", "unknown")
    
    return {
        "user_email": user_email,
        "period_days": 30,
        "questions": {
            "total_questions": 0,
            "successful_questions": 0,
            "failed_questions": 0,
            "avg_processing_time": 0,
            "avg_confidence": 0
        },
        "openai_costs": {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0,
            "avg_cost_per_call": 0
        },
        "cost_by_purpose": [],
        "debug": {
            "mode": "minimal",
            "timestamp": datetime.now().isoformat()
        }
    }

# ==================== ENDPOINTS DE TEST ====================

@router.get("/test/imports")
async def test_imports() -> Dict[str, Any]:
    """🧪 Test des imports pour identifier la cause"""
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "imports": {}
    }
    
    # Test import auth
    try:
        from app.api.v1.auth import get_current_user
        results["imports"]["auth"] = {"status": "ok", "module": "app.api.v1.auth"}
    except Exception as e:
        results["imports"]["auth"] = {"status": "error", "error": str(e)}
    
    # Test import permissions
    try:
        from app.api.v1.logging import has_permission, Permission
        results["imports"]["logging"] = {"status": "ok", "module": "app.api.v1.logging"}
    except Exception as e:
        results["imports"]["logging"] = {"status": "error", "error": str(e)}
    
    # Test import stats_cache (SUSPECT PRINCIPAL)
    try:
        from app.api.v1.stats_cache import get_stats_cache
        cache = get_stats_cache()
        results["imports"]["stats_cache"] = {
            "status": "ok", 
            "module": "app.api.v1.stats_cache",
            "cache_available": cache is not None
        }
    except Exception as e:
        results["imports"]["stats_cache"] = {"status": "error", "error": str(e)}
    
    # Test import stats_updater
    try:
        from app.api.v1.stats_updater import get_stats_updater
        results["imports"]["stats_updater"] = {"status": "ok", "module": "app.api.v1.stats_updater"}
    except Exception as e:
        results["imports"]["stats_updater"] = {"status": "error", "error": str(e)}
    
    return results

@router.get("/test/memory-stress")
async def test_memory_stress() -> Dict[str, Any]:
    """🧪 Test de stress mémoire contrôlé"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    try:
        # Test création liste en mémoire (contrôlé)
        test_data = []
        for i in range(1000):  # Petit test
            test_data.append({"id": i, "data": f"test_{i}"})
        
        final_memory = process.memory_info().rss
        memory_diff = final_memory - initial_memory
        
        # Nettoyer
        del test_data
        
        return {
            "status": "completed",
            "initial_memory_mb": round(initial_memory / 1024 / 1024, 2),
            "final_memory_mb": round(final_memory / 1024 / 1024, 2),
            "memory_diff_mb": round(memory_diff / 1024 / 1024, 2),
            "test_size": 1000,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }