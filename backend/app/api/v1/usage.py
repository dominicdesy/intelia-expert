# -*- coding: utf-8 -*-
"""
usage.py - API endpoints pour la consultation de l'usage et des quotas
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
usage.py - API endpoints pour la consultation de l'usage et des quotas

Permet au frontend d'afficher:
- Combien de questions l'utilisateur a utilisées ce mois
- Combien il en reste
- Son plan actuel
- Statut du quota
"""
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any
from datetime import datetime

from pydantic import BaseModel

from app.api.v1.auth import get_current_user
from app.services.usage_limiter import (
    get_user_usage_stats,
    check_user_quota,
    increment_question_count,
    reset_monthly_usage_for_all_users,
    QuotaExceededException
)

logger = logging.getLogger(__name__)
router = APIRouter()


class IncrementRequest(BaseModel):
    """Modèle pour l'incrémentation du quota"""
    success: bool = True
    cost_usd: float = 0.0


@router.post("/increment")
async def increment_usage(
    request: IncrementRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Incrémente le compteur de questions de l'utilisateur.

    Appelé par le service LLM après chaque question posée.

    Body:
    - success: True si la question a réussi, False si échec
    - cost_usd: Coût de la question en USD (optionnel)

    Retourne:
    - questions_used: nouveau total de questions utilisées
    - monthly_quota: limite mensuelle
    - questions_remaining: nombre restant
    - quota_exceeded: boolean indiquant si le quota est dépassé
    """
    try:
        user_email = current_user.get("email")

        if not user_email:
            raise HTTPException(
                status_code=401,
                detail="Email utilisateur non trouvé"
            )

        result = increment_question_count(
            user_email=user_email,
            success=request.success,
            cost_usd=request.cost_usd
        )

        if 'error' in result:
            logger.error(f"Erreur incrémentation pour {user_email}: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de l'incrémentation: {result['error']}"
            )

        return {
            "status": "success",
            "usage": result,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur endpoint /usage/increment")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@router.get("/current")
async def get_current_usage(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Récupère l'usage actuel de l'utilisateur pour le mois en cours.

    Retourne:
    - plan_name: nom du plan (essential, pro, elite)
    - monthly_quota: limite mensuelle (null si illimité)
    - questions_used: nombre de questions utilisées ce mois
    - questions_remaining: nombre de questions restantes (null si illimité)
    - percentage_used: pourcentage d'utilisation
    - current_status: statut (active, quota_exceeded, etc.)
    """
    try:
        user_email = current_user.get("email")

        if not user_email:
            raise HTTPException(
                status_code=401,
                detail="Email utilisateur non trouvé"
            )

        stats = get_user_usage_stats(user_email)

        if 'error' in stats:
            logger.error(f"Erreur récupération usage pour {user_email}: {stats['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de la récupération de l'usage: {stats['error']}"
            )

        return {
            "status": "success",
            "usage": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur endpoint /usage/current")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@router.get("/check")
async def check_quota_availability(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Vérifie si l'utilisateur peut poser une question (sans l'incrémenter).

    Utile pour le frontend pour afficher un avertissement avant que
    l'utilisateur tape sa question.

    Retourne:
    - can_ask: boolean - true si l'utilisateur peut encore poser des questions
    - questions_used: nombre utilisé
    - monthly_quota: limite mensuelle
    - questions_remaining: nombre restant
    - warning_threshold_reached: true si > 80% du quota utilisé
    """
    try:
        user_email = current_user.get("email")

        if not user_email:
            raise HTTPException(
                status_code=401,
                detail="Email utilisateur non trouvé"
            )

        quota_info = check_user_quota(user_email)

        # Ajouter un flag d'avertissement si proche de la limite
        if quota_info.get('monthly_quota') and quota_info.get('questions_remaining') is not None:
            usage_percentage = (quota_info['questions_used'] / quota_info['monthly_quota']) * 100
            quota_info['warning_threshold_reached'] = usage_percentage >= 80
            quota_info['usage_percentage'] = round(usage_percentage, 1)
        else:
            quota_info['warning_threshold_reached'] = False
            quota_info['usage_percentage'] = 0

        return {
            "status": "success",
            "quota": quota_info,
            "timestamp": datetime.utcnow().isoformat()
        }

    except QuotaExceededException as e:
        # Retourner un 200 avec can_ask=false au lieu d'une erreur
        # pour que le frontend puisse afficher un message approprié
        return {
            "status": "quota_exceeded",
            "quota": e.usage_info,
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur endpoint /usage/check")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@router.get("/history")
async def get_usage_history(
    months: int = 6,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Récupère l'historique d'usage des N derniers mois.

    Paramètres:
    - months: nombre de mois d'historique (défaut: 6, max: 12)

    Retourne un tableau avec l'usage de chaque mois.
    """
    try:
        user_email = current_user.get("email")

        if not user_email:
            raise HTTPException(
                status_code=401,
                detail="Email utilisateur non trouvé"
            )

        # Limiter à 12 mois max
        months = min(months, 12)

        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        month_year,
                        questions_used,
                        questions_successful,
                        questions_failed,
                        monthly_quota,
                        total_cost_usd,
                        current_status,
                        quota_exceeded_at
                    FROM monthly_usage_tracking
                    WHERE user_email = %s
                    ORDER BY month_year DESC
                    LIMIT %s
                    """,
                    (user_email, months)
                )

                history = cur.fetchall()

                return {
                    "status": "success",
                    "user_email": user_email,
                    "history": [dict(row) for row in history],
                    "count": len(history),
                    "timestamp": datetime.utcnow().isoformat()
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur endpoint /usage/history")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur: {str(e)}"
        )


@router.get("/health")
async def usage_service_health() -> Dict[str, Any]:
    """Health check pour le service de gestion des quotas"""
    try:
        from app.core.database import get_pg_connection

        # Test de connexion DB
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM monthly_usage_tracking")
                count = cur.fetchone()[0]

        return {
            "status": "healthy",
            "service": "usage_limiter",
            "database": "connected",
            "total_tracking_records": count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.exception("Health check failed for usage service")
        return {
            "status": "unhealthy",
            "service": "usage_limiter",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/cron/reset-monthly")
async def cron_reset_monthly(
    secret: str = Query(None, description="Clé secrète CRON pour authentification")
) -> Dict[str, Any]:
    """
    Reset mensuel des quotas - Endpoint pour service CRON externe (cron-job.org).

    À appeler le 1er de chaque mois à 00:00 UTC.
    Protégé par clé secrète passée en query parameter.

    Usage: POST /v1/usage/cron/reset-monthly?secret=YOUR_SECRET_KEY

    Cette fonction:
    - Crée de nouveaux enregistrements monthly_usage_tracking pour le mois en cours
    - Réinitialise questions_used à 0 pour tous les utilisateurs
    - Préserve l'historique des mois précédents

    Retourne:
    - status: 'success' ou 'error'
    - month_year: Mois créé (YYYY-MM)
    - users_reset: Nombre d'utilisateurs réinitialisés
    """
    try:
        # Vérification clé secrète
        expected_secret = os.getenv("CRON_SECRET_KEY")

        if not expected_secret:
            logger.error("CRON_SECRET_KEY non configurée dans .env")
            raise HTTPException(
                status_code=500,
                detail="Configuration serveur manquante: CRON_SECRET_KEY"
            )

        if not secret:
            logger.warning("Tentative reset mensuel sans clé secrète")
            raise HTTPException(
                status_code=401,
                detail="Clé secrète manquante. Usage: ?secret=YOUR_KEY"
            )

        if secret != expected_secret:
            logger.warning(f"Tentative reset mensuel avec clé invalide: {secret[:8]}...")
            raise HTTPException(
                status_code=401,
                detail="Clé secrète invalide"
            )

        # Exécuter le reset
        logger.info("Démarrage reset mensuel des quotas (déclenché par CRON)")
        result = reset_monthly_usage_for_all_users()

        if result.get("status") == "success":
            logger.info(
                f"✅ Reset mensuel réussi: {result.get('users_reset')} utilisateurs "
                f"réinitialisés pour {result.get('month_year')}"
            )
            return {
                "status": "success",
                "message": "Reset mensuel effectué avec succès",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            logger.error(f"❌ Échec reset mensuel: {result}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors du reset: {result.get('error', 'Unknown')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erreur critique lors du reset mensuel CRON")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur serveur lors du reset: {str(e)}"
        )
