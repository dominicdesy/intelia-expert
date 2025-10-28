"""
Monitoring API Routes - Endpoints pour le monitoring des services
Version: 1.0.1 - Fixed deprecation warnings
"""

import asyncio
import logging
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional

from monitoring.log_collector import get_log_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# Task de background pour le health checking périodique
_health_check_task = None
_health_check_running = False


async def periodic_health_check():
    """Vérifie périodiquement la santé des services"""
    global _health_check_running

    collector = get_log_collector()

    # Services à surveiller
    services = [
        ("ai-service", "http://localhost:8000", "/health"),
        ("llm-service", "http://localhost:8081", "/health"),
    ]

    logger.info("[MONITORING] Starting periodic health checks...")

    while _health_check_running:
        for service_name, base_url, endpoint in services:
            try:
                await collector.check_service_health(service_name, base_url, endpoint)
            except Exception as e:
                logger.error(f"[MONITORING] Health check error for {service_name}: {e}")
                collector.add_log(
                    service=service_name,
                    level="ERROR",
                    message=f"Health check exception: {str(e)}",
                    context={}
                )

        # Attendre 30 secondes avant le prochain check
        await asyncio.sleep(30)


async def start_health_checks():
    """Démarre les health checks périodiques au démarrage"""
    global _health_check_task, _health_check_running

    if not _health_check_running:
        _health_check_running = True
        _health_check_task = asyncio.create_task(periodic_health_check())
        logger.info("[MONITORING] Health check task started")


async def stop_health_checks():
    """Arrête les health checks au shutdown"""
    global _health_check_task, _health_check_running

    if _health_check_running:
        _health_check_running = False
        if _health_check_task:
            _health_check_task.cancel()
            try:
                await _health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("[MONITORING] Health check task stopped")


@router.get("/logs")
async def get_logs(
    limit: Optional[int] = Query(100, description="Maximum number of logs to return"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR)")
):
    """
    Récupère les logs de monitoring

    Args:
        limit: Nombre maximum de logs (default: 100)
        service: Filtrer par service (ai-service, llm-service)
        level: Filtrer par niveau (INFO, WARNING, ERROR)

    Returns:
        Liste des logs
    """
    try:
        collector = get_log_collector()
        logs = collector.get_logs(limit=limit, service=service, level=level)

        return JSONResponse(content={
            "logs": logs,
            "count": len(logs),
            "filters": {
                "service": service,
                "level": level,
                "limit": limit
            }
        })

    except Exception as e:
        logger.error(f"[MONITORING] Error getting logs: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/services")
async def get_services_health():
    """
    Récupère l'état de santé de tous les services

    Returns:
        Liste des services avec leur état
    """
    try:
        collector = get_log_collector()
        services = collector.get_services_health()

        return JSONResponse(content={
            "services": services,
            "count": len(services)
        })

    except Exception as e:
        logger.error(f"[MONITORING] Error getting services health: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/summary")
async def get_monitoring_summary():
    """
    Récupère un résumé du monitoring

    Returns:
        Résumé avec statistiques globales
    """
    try:
        collector = get_log_collector()
        summary = collector.get_summary()

        return JSONResponse(content=summary)

    except Exception as e:
        logger.error(f"[MONITORING] Error getting summary: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/log")
async def add_manual_log(
    service: str,
    level: str,
    message: str,
    context: Optional[dict] = None
):
    """
    Ajoute manuellement un log (pour testing ou intégration externe)

    Args:
        service: Nom du service
        level: Niveau (INFO, WARNING, ERROR)
        message: Message du log
        context: Contexte additionnel (optionnel)
    """
    try:
        collector = get_log_collector()
        collector.add_log(
            service=service,
            level=level,
            message=message,
            context=context
        )

        return JSONResponse(content={
            "success": True,
            "message": "Log added successfully"
        })

    except Exception as e:
        logger.error(f"[MONITORING] Error adding log: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
