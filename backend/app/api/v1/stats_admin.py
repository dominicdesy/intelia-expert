# app/api/v1/stats_admin.py
"""
VERSION SIMPLE ET DIRECTE - ADMINISTRATION BASIQUE
Contrôles essentiels sans complexité
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

logger = logging.getLogger(__name__)

# Imports conditionnels simples
try:
    from app.api.v1.auth import get_current_user

    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    get_current_user = None

try:
    from app.api.v1.stats_cache import get_stats_cache

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    get_stats_cache = None

try:
    from app.api.v1.stats_updater import get_stats_updater, force_update_all

    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False
    get_stats_updater = None
    force_update_all = None

router = APIRouter(tags=["statistics-admin"])

logger.debug("STATS_ADMIN VERSION SIMPLE V1.0 chargé")
logger.debug(
    f"Imports: AUTH={AUTH_AVAILABLE}, CACHE={CACHE_AVAILABLE}, UPDATER={UPDATER_AVAILABLE}"
)


def check_admin_permission(current_user: dict = None):
    """Vérification simple des permissions admin"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    if current_user.get("user_type") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")

    return True


@router.post("/force-update")
async def force_update_stats(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user) if AUTH_AVAILABLE else None,
):
    """Force une mise à jour des statistiques"""
    check_admin_permission(current_user)

    if not UPDATER_AVAILABLE:
        raise HTTPException(status_code=500, detail="Stats updater not available")

    try:
        logger.info(f"Force update demandé par: {current_user.get('email')}")

        # Lancer en arrière-plan
        background_tasks.add_task(force_update_all)

        return {
            "status": "initiated",
            "message": "Mise à jour lancée en arrière-plan",
            "initiated_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erreur force update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache(
    current_user: dict = Depends(get_current_user) if AUTH_AVAILABLE else None,
):
    """Vide le cache"""
    check_admin_permission(current_user)

    if not CACHE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Cache not available")

    try:
        cache = get_stats_cache()
        deleted_count = cache.invalidate_cache()

        logger.info(
            f"Cache vidé par {current_user.get('email')}: {deleted_count} entrées"
        )

        return {
            "status": "success",
            "entries_deleted": deleted_count,
            "cleared_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Erreur clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_system_status(
    current_user: dict = Depends(get_current_user) if AUTH_AVAILABLE else None,
):
    """Statut simple du système"""
    check_admin_permission(current_user)

    try:
        status = {
            "overall_health": "healthy",
            "components": {
                "auth": AUTH_AVAILABLE,
                "cache": CACHE_AVAILABLE,
                "updater": UPDATER_AVAILABLE,
            },
            "timestamp": datetime.now().isoformat(),
        }

        # Stats du cache si disponible
        if CACHE_AVAILABLE:
            try:
                cache = get_stats_cache()
                status["cache_stats"] = cache.get_cache_stats()
            except Exception as cache_error:
                logger.warning(f"Erreur stats cache: {cache_error}")
                status["cache_stats"] = {"error": str(cache_error)}

        # Stats de l'updater si disponible
        if UPDATER_AVAILABLE:
            try:
                updater = get_stats_updater()
                status["updater_info"] = {
                    "last_update": (
                        updater.last_update.isoformat() if updater.last_update else None
                    ),
                    "update_in_progress": updater.update_in_progress,
                }
            except Exception as updater_error:
                logger.warning(f"Erreur stats updater: {updater_error}")
                status["updater_info"] = {"error": str(updater_error)}

        return status

    except Exception as e:
        logger.error(f"Erreur system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_components(
    current_user: dict = Depends(get_current_user) if AUTH_AVAILABLE else None,
):
    """Test simple de tous les composants"""
    check_admin_permission(current_user)

    results = {
        "auth": {
            "available": AUTH_AVAILABLE,
            "status": "ok" if AUTH_AVAILABLE else "missing",
        },
        "cache": {"available": CACHE_AVAILABLE},
        "updater": {"available": UPDATER_AVAILABLE},
    }

    # Test cache
    if CACHE_AVAILABLE:
        try:
            cache = get_stats_cache()
            test_key = "admin:test"
            test_data = {"test": True, "timestamp": datetime.now().isoformat()}

            write_ok = cache.set_cache(test_key, test_data, ttl_hours=1)
            read_result = cache.get_cache(test_key)
            read_ok = read_result is not None
            cache.delete_cache(test_key)

            results["cache"].update(
                {
                    "status": "ok" if (write_ok and read_ok) else "failed",
                    "write": write_ok,
                    "read": read_ok,
                }
            )

        except Exception as e:
            results["cache"]["status"] = "error"
            results["cache"]["error"] = str(e)

    # Test updater
    if UPDATER_AVAILABLE:
        try:
            updater = get_stats_updater()
            stats = updater.get_stats()

            results["updater"].update(
                {
                    "status": "ok" if stats else "failed",
                    "stats_available": stats is not None,
                    "total_questions": (
                        stats.get("usageStats", {}).get("total_questions", 0)
                        if stats
                        else 0
                    ),
                }
            )

        except Exception as e:
            results["updater"]["status"] = "error"
            results["updater"]["error"] = str(e)

    overall_ok = all(r.get("status") in ["ok", "missing"] for r in results.values())

    return {
        "overall_status": "ok" if overall_ok else "issues",
        "components": results,
        "tested_by": current_user.get("email"),
        "timestamp": datetime.now().isoformat(),
    }
