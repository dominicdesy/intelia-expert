"""
Dépendance FastAPI pour vérification automatique des quotas
"""
from fastapi import Depends, HTTPException
from typing import Dict, Any
import logging

from app.api.v1.auth import get_current_user
from app.services.usage_limiter import check_user_quota, QuotaExceededException

logger = logging.getLogger(__name__)


async def check_user_quota_dependency(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dépendance FastAPI qui vérifie automatiquement les quotas.

    À utiliser sur les endpoints qui génèrent des questions/réponses.

    Raises:
        HTTPException(429): Si le quota est dépassé

    Returns:
        Dict contenant les infos de quota pour usage ultérieur
    """
    user_email = current_user.get("email")

    if not user_email:
        raise HTTPException(
            status_code=401,
            detail="Email utilisateur non trouvé"
        )

    try:
        # Vérifier le quota AVANT de permettre la requête
        quota_info = check_user_quota(user_email)

        logger.info(
            f"[QuotaCheck] {user_email}: {quota_info['questions_used']}/{quota_info['monthly_quota']} questions"
        )

        return {
            "user_email": user_email,
            "quota_info": quota_info,
            "current_user": current_user
        }

    except QuotaExceededException as e:
        logger.warning(
            f"[QuotaCheck] Quota dépassé pour {user_email}: {e.usage_info}"
        )

        # Retourner une erreur HTTP 429 (Too Many Requests)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": str(e),
                "quota_info": e.usage_info
            }
        )
    except Exception as e:
        logger.error(f"[QuotaCheck] Erreur vérification quota pour {user_email}: {e}")
        # En cas d'erreur, on laisse passer (fail-open) pour ne pas bloquer le service
        # Mais on log l'erreur
        return {
            "user_email": user_email,
            "quota_info": None,
            "current_user": current_user,
            "error": str(e)
        }
