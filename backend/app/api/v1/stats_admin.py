# app/api/v1/stats_admin.py
# -*- coding: utf-8 -*-
"""
🔧 ADMINISTRATION DU SYSTÈME DE CACHE STATISTIQUES
Contrôle, monitoring, debug et maintenance du cache
SAFE: Admin uniquement, n'interfère pas avec les systèmes existants
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from app.api.v1.auth import get_current_user

# Imports des systèmes de cache (SAFE)
from app.api.v1.stats_cache import get_stats_cache, force_cache_refresh
from app.api.v1.stats_updater import get_stats_updater, run_update_cycle, force_update_all

# Import des permissions
from app.api.v1.logging import has_permission, Permission

router = APIRouter(prefix="/stats-admin", tags=["statistics-admin"])
logger = logging.getLogger(__name__)

# ==================== ENDPOINTS DE CONTRÔLE ====================

@router.post("/force-update/all")
async def force_update_all_stats(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """🔄 Force une mise à jour complète de toutes les statistiques"""
    if not has_permission(current_user, Permission.MANAGE_SYSTEM):
        raise HTTPException(status_code=403, detail="System management permission required")
    
    try:
        logger.info(f"🔄 Force update ALL demandé par: {current_user.get('email')}")
        
        # Lancer la mise à jour en arrière-plan
        background_tasks.add_task(force_update_all)
        
        return {
            "status": "initiated",
            "message": "Mise à jour complète lancée en arrière-plan",
            "initiated_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat(),
            "estimated_duration": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur force update all: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/force-update/{component}")
async def force_update_component(
    component: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """🎯 Force la mise à jour d'un composant spécifique"""
    if not has_permission(current_user, Permission.MANAGE_SYSTEM):
        raise HTTPException(status_code=403, detail="System management permission required")
    
    valid_components = ["dashboard", "openai", "invitations", "performance"]
    if component not in valid_components:
        raise HTTPException(
            status_code=400, 
            detail=f"Composant invalide. Valides: {', '.join(valid_components)}"
        )
    
    try:
        updater = get_stats_updater()
        
        logger.info(f"🎯 Force update {component} demandé par: {current_user.get('email')}")
        
        # Lancer en arrière-plan
        background_tasks.add_task(updater.force_update_specific, component)
        
        return {
            "status": "initiated",
            "component": component,
            "message": f"Mise à jour {component} lancée en arrière-plan",
            "initiated_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur force update {component}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache(
    pattern: str = Query(None, description="Pattern à supprimer (ex: 'dashboard_*')"),
    key: str = Query(None, description="Clé exacte à supprimer"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """🗑️ Vide le cache (pattern ou clé spécifique)"""
    if not has_permission(current_user, Permission.MANAGE_SYSTEM):
        raise HTTPException(status_code=403, detail="System management permission required")
    
    try:
        cache = get_stats_cache()
        
        if key:
            deleted_count = cache.invalidate_cache(key=key)
            action = f"Clé '{key}' supprimée"
        elif pattern:
            deleted_count = cache.invalidate_cache(pattern=pattern)
            action = f"Pattern '{pattern}' supprimé"
        else:
            deleted_count = cache.invalidate_cache()
            action = "Cache expiré nettoyé"
        
        logger.info(f"🗑️ Cache clear par {current_user.get('email')}: {action} ({deleted_count} entrées)")
        
        return {
            "status": "success",
            "action": action,
            "entries_deleted": deleted_count,
            "cleared_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/refresh")
async def refresh_cache(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """♻️ Actualisation complète du cache"""
    if not has_permission(current_user, Permission.MANAGE_SYSTEM):
        raise HTTPException(status_code=403, detail="System management permission required")
    
    try:
        logger.info(f"♻️ Cache refresh demandé par: {current_user.get('email')}")
        
        result = force_cache_refresh()
        result["refreshed_by"] = current_user.get("email")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur refresh cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE MONITORING ====================

@router.get("/status")
async def get_system_status(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """📊 Statut complet du système de statistiques"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin dashboard access required")
    
    try:
        cache = get_stats_cache()
        updater = get_stats_updater()
        
        # Statistiques du cache
        cache_stats = cache.get_cache_stats()
        
        # Statut de la dernière mise à jour
        update_status = updater.get_update_status()
        
        # Vérifications de santé
        health_checks = {
            "cache_available": True,
            "database_connected": bool(cache.dsn),
            "updater_active": not updater.update_in_progress,
            "last_update_recent": False
        }
        
        if updater.last_update:
            time_since_update = datetime.now() - updater.last_update
            health_checks["last_update_recent"] = time_since_update < timedelta(hours=2)
        
        # Statut global
        overall_health = "healthy"
        if not health_checks["cache_available"] or not health_checks["database_connected"]:
            overall_health = "critical"
        elif not health_checks["last_update_recent"]:
            overall_health = "warning"
        
        return {
            "overall_health": overall_health,
            "health_checks": health_checks,
            "cache_statistics": cache_stats,
            "update_status": update_status,
            "system_info": {
                "update_in_progress": updater.update_in_progress,
                "last_update": updater.last_update.isoformat() if updater.last_update else None,
                "next_scheduled_update": "Automatique toutes les heures"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/inspect/{cache_key}")
async def inspect_cache_key(
    cache_key: str,
    include_expired: bool = Query(False, description="Inclure données expirées"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """🔍 Inspecte une clé de cache spécifique"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin dashboard access required")
    
    try:
        cache = get_stats_cache()
        
        # Récupérer les données du cache
        cached_data = cache.get_cache(cache_key, include_expired=include_expired)
        
        if not cached_data:
            return {
                "status": "not_found",
                "cache_key": cache_key,
                "message": "Clé de cache non trouvée",
                "inspected_by": current_user.get("email"),
                "timestamp": datetime.now().isoformat()
            }
        
        # Analyser les données
        data_size = len(str(cached_data["data"]))
        is_expired = cached_data.get("is_expired", False)
        
        analysis = {
            "cache_key": cache_key,
            "status": "expired" if is_expired else "valid",
            "metadata": {
                "created_at": cached_data.get("cached_at"),
                "updated_at": cached_data.get("updated_at"),
                "expires_at": cached_data.get("expires_at"),
                "source": cached_data.get("source"),
                "data_size_bytes": data_size,
                "is_expired": is_expired
            },
            "data_preview": {
                "type": type(cached_data["data"]).__name__,
                "keys": list(cached_data["data"].keys()) if isinstance(cached_data["data"], dict) else "N/A",
                "length": len(cached_data["data"]) if hasattr(cached_data["data"], '__len__') else "N/A"
            },
            "full_data": cached_data["data"] if data_size < 10000 else "Données trop volumineuses (>10KB)",
            "inspected_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🔍 Cache inspect {cache_key} par {current_user.get('email')}")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Erreur inspect cache {cache_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/keys")
async def list_cache_keys(
    pattern: str = Query("*", description="Pattern de recherche"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """📝 Liste les clés de cache disponibles"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin dashboard access required")
    
    try:
        cache = get_stats_cache()
        
        # Requête SQL pour récupérer les clés
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        with psycopg2.connect(cache.dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                # Construire la requête selon le pattern
                if pattern == "*":
                    cur.execute("""
                        SELECT cache_key, created_at, updated_at, expires_at, source
                        FROM statistics_cache 
                        ORDER BY updated_at DESC 
                        LIMIT %s
                    """, (limit,))
                else:
                    cur.execute("""
                        SELECT cache_key, created_at, updated_at, expires_at, source
                        FROM statistics_cache 
                        WHERE cache_key LIKE %s
                        ORDER BY updated_at DESC 
                        LIMIT %s
                    """, (pattern.replace("*", "%"), limit))
                
                keys_data = []
                for row in cur.fetchall():
                    keys_data.append({
                        "cache_key": row["cache_key"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat(),
                        "expires_at": row["expires_at"].isoformat(),
                        "source": row["source"],
                        "is_expired": row["expires_at"] <= datetime.now()
                    })
        
        return {
            "status": "success",
            "pattern": pattern,
            "keys_found": len(keys_data),
            "keys": keys_data,
            "listed_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur list cache keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE DEBUG ====================

@router.get("/debug/update-log")
async def get_update_log(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """🐛 Log des mises à jour récentes"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin dashboard access required")
    
    try:
        # Récupérer l'historique des mises à jour depuis le cache
        cache = get_stats_cache()
        
        update_history = []
        
        # Vérifier plusieurs clés d'historique
        for i in range(min(hours, 24)):  # Limiter à 24 entrées max
            history_key = f"system:update_history:{i}"
            history_entry = cache.get_cache(history_key, include_expired=True)
            
            if history_entry:
                update_history.append(history_entry["data"])
        
        # Si pas d'historique, récupérer le dernier statut
        if not update_history:
            updater = get_stats_updater()
            last_status = updater.get_update_status()
            if last_status.get("status") != "never_updated":
                update_history.append(last_status)
        
        return {
            "status": "success",
            "period_hours": hours,
            "updates_found": len(update_history),
            "update_history": sorted(update_history, key=lambda x: x.get("timestamp", ""), reverse=True),
            "requested_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur update log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug/test-components")
async def test_all_components(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """🧪 Test de tous les composants du système"""
    if not has_permission(current_user, Permission.MANAGE_SYSTEM):
        raise HTTPException(status_code=403, detail="System management permission required")
    
    try:
        logger.info(f"🧪 Test composants demandé par: {current_user.get('email')}")
        
        results = {}
        
        # Test 1: Cache
        try:
            cache = get_stats_cache()
            test_key = "admin:test:cache"
            test_data = {"test": True, "timestamp": datetime.now().isoformat()}
            
            write_ok = cache.set_cache(test_key, test_data, ttl_hours=1, source="admin_test")
            read_result = cache.get_cache(test_key)
            read_ok = read_result is not None
            cache.invalidate_cache(key=test_key)
            
            results["cache"] = {
                "status": "ok" if write_ok and read_ok else "failed",
                "write": write_ok,
                "read": read_ok
            }
            
        except Exception as cache_error:
            results["cache"] = {"status": "error", "error": str(cache_error)}
        
        # Test 2: Updater
        try:
            updater = get_stats_updater()
            updater_status = updater.get_update_status()
            
            results["updater"] = {
                "status": "ok" if updater_status else "failed",
                "last_update": updater.last_update.isoformat() if updater.last_update else None,
                "in_progress": updater.update_in_progress
            }
            
        except Exception as updater_error:
            results["updater"] = {"status": "error", "error": str(updater_error)}
        
        # Test 3: Base de données
        try:
            cache = get_stats_cache()
            import psycopg2
            
            with psycopg2.connect(cache.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 as test")
                    db_result = cur.fetchone()
            
            results["database"] = {
                "status": "ok" if db_result and db_result[0] == 1 else "failed",
                "connection": "ok"
            }
            
        except Exception as db_error:
            results["database"] = {"status": "error", "error": str(db_error)}
        
        # Test 4: Permissions et authentification
        try:
            has_admin = has_permission(current_user, Permission.ADMIN_DASHBOARD)
            has_manage = has_permission(current_user, Permission.MANAGE_SYSTEM)
            
            results["permissions"] = {
                "status": "ok",
                "admin_dashboard": has_admin,
                "manage_system": has_manage,
                "user_type": current_user.get("user_type")
            }
            
        except Exception as perm_error:
            results["permissions"] = {"status": "error", "error": str(perm_error)}
        
        # Résumé global
        all_ok = all(r.get("status") == "ok" for r in results.values())
        
        return {
            "overall_status": "all_ok" if all_ok else "some_issues",
            "test_results": results,
            "tested_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur test components: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE MAINTENANCE ====================

@router.post("/maintenance/cleanup")
async def maintenance_cleanup(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """🧹 Nettoyage de maintenance du cache"""
    if not has_permission(current_user, Permission.MANAGE_SYSTEM):
        raise HTTPException(status_code=403, detail="System management permission required")
    
    try:
        cache = get_stats_cache()
        
        # Nettoyage automatique
        cleaned_count = cache.cleanup_expired_cache()
        
        # Statistiques après nettoyage
        cache_stats = cache.get_cache_stats()
        
        logger.info(f"🧹 Maintenance cleanup par {current_user.get('email')}: {cleaned_count} entrées supprimées")
        
        return {
            "status": "completed",
            "entries_cleaned": cleaned_count,
            "cache_stats_after": cache_stats,
            "cleaned_by": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur maintenance cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance/recommendations")
async def get_maintenance_recommendations(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """💡 Recommandations de maintenance"""
    if not has_permission(current_user, Permission.ADMIN_DASHBOARD):
        raise HTTPException(status_code=403, detail="Admin dashboard access required")
    
    try:
        cache = get_stats_cache()
        updater = get_stats_updater()
        
        recommendations = []
        
        # Vérifier l'âge de la dernière mise à jour
        if updater.last_update:
            time_since_update = datetime.now() - updater.last_update
            if time_since_update > timedelta(hours=2):
                recommendations.append({
                    "priority": "medium",
                    "category": "update",
                    "message": f"Dernière mise à jour il y a {time_since_update}",
                    "action": "Considérer une mise à jour forcée"
                })
        else:
            recommendations.append({
                "priority": "high",
                "category": "update",
                "message": "Aucune mise à jour détectée",
                "action": "Lancer une première mise à jour"
            })
        
        # Vérifier la taille du cache
        cache_stats = cache.get_cache_stats()
        total_cache_entries = sum(
            stats.get('total', 0) 
            for stats in cache_stats.values() 
            if isinstance(stats, dict)
        )
        
        if total_cache_entries > 1000:
            recommendations.append({
                "priority": "low",
                "category": "cleanup",
                "message": f"Cache volumineux: {total_cache_entries} entrées",
                "action": "Envisager un nettoyage"
            })
        
        # Vérifier les erreurs récentes
        recent_errors = []  # TODO: Implémenter un log d'erreurs
        
        if recent_errors:
            recommendations.append({
                "priority": "high",
                "category": "errors",
                "message": f"{len(recent_errors)} erreurs récentes détectées",
                "action": "Vérifier les logs et corriger les problèmes"
            })
        
        return {
            "status": "success",
            "recommendations_count": len(recommendations),
            "recommendations": recommendations,
            "generated_for": current_user.get("email"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur maintenance recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
