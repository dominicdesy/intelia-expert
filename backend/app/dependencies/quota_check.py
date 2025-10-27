"""
Dépendance FastAPI pour vérification automatique des quotas
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Dépendance FastAPI pour vérification automatique des quotas
"""
from fastapi import Depends, HTTPException, WebSocket, status
from typing import Dict, Any, Optional
import logging
import jwt

from app.api.v1.auth import get_current_user, JWT_SECRETS, JWT_ALGORITHM
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


async def get_current_user_from_websocket(
    websocket: WebSocket
) -> Dict[str, Any]:
    """
    Authentification JWT pour WebSocket connections.

    Le client doit envoyer le token via query parameter:
    ws://backend.com/api/v1/ws/voice?token=JWT_HERE

    Utilise la même logique multi-compatible que get_current_user
    pour supporter auth-temp ET Supabase tokens.

    Args:
        websocket: WebSocket connection

    Returns:
        Dict avec user_id, email, et autres infos utilisateur

    Raises:
        WebSocketException: Si token invalide ou manquant
    """
    # Extraire token depuis query params
    token = websocket.query_params.get("token")

    if not token or not isinstance(token, str):
        logger.warning("[WebSocket Auth] Token manquant ou invalide")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token missing or invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing or invalid"
        )

    # ESSAYER TOUS LES SECRETS CONFIGURÉS (même logique que get_current_user)
    for secret_name, secret_value in JWT_SECRETS:
        if not secret_value:
            continue

        try:
            logger.debug(f"[WebSocket Auth] Tentative décodage avec {secret_name}")

            # DÉCODER AVEC PLUSIEURS OPTIONS
            decode_options = [
                {"options": {"verify_aud": False}},  # Sans vérifier audience (auth-temp)
                {"audience": "authenticated"},  # Standard Supabase
                {},  # Sans options spéciales
            ]

            payload = None
            for option_set in decode_options:
                try:
                    if "options" in option_set:
                        payload = jwt.decode(
                            token,
                            secret_value,
                            algorithms=[JWT_ALGORITHM],
                            **option_set,
                        )
                    elif "audience" in option_set:
                        payload = jwt.decode(
                            token,
                            secret_value,
                            algorithms=[JWT_ALGORITHM],
                            audience=option_set["audience"],
                        )
                    else:
                        payload = jwt.decode(
                            token, secret_value, algorithms=[JWT_ALGORITHM]
                        )
                    break  # Succès
                except jwt.InvalidAudienceError:
                    continue
                except Exception:
                    continue

            if not payload:
                continue  # Essayer le secret suivant

            logger.debug(f"[WebSocket Auth] Token décodé avec succès avec {secret_name}")

            # EXTRACTION DES INFORMATIONS UTILISATEUR
            user_id = payload.get("sub") or payload.get("user_id")
            email = payload.get("email")
            session_id = payload.get("session_id")

            # Vérifications de base
            if not user_id:
                logger.warning("[WebSocket Auth] Token sans user_id valide")
                continue

            if not email:
                logger.warning("[WebSocket Auth] Token sans email valide")
                continue

            # CONSTRUIRE LA RÉPONSE
            user_data = {
                "user_id": user_id,
                "email": email,
                "session_id": session_id,
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "exp": payload.get("exp"),
                "jwt_secret_used": secret_name,
            }

            logger.info(f"✅ [WebSocket Auth] Authenticated user: {email} (id: {user_id})")
            return user_data

        except jwt.ExpiredSignatureError:
            logger.warning(f"[WebSocket Auth] Token expiré ({secret_name})")
            continue
        except jwt.InvalidTokenError as e:
            logger.warning(f"[WebSocket Auth] Token invalide ({secret_name}): {e}")
            continue
        except Exception as e:
            logger.error(f"[WebSocket Auth] Erreur décodage avec {secret_name}: {e}")
            continue

    # Aucun secret n'a fonctionné
    logger.error("[WebSocket Auth] Échec authentification - aucun secret valide")
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token"
    )
