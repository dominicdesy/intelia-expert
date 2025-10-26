# -*- coding: utf-8 -*-
"""
Widget API - Endpoints pour intégration chat sur sites externes
VERSION 1.0.0
"""

import logging
import time
import uuid
import httpx
import os
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import jwt

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget")

# Configuration JWT
JWT_SECRET = os.getenv("WIDGET_JWT_SECRET", os.getenv("JWT_SECRET", ""))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

# LLM API URL
LLM_API_URL = os.getenv("LLM_API_URL", "http://llm:8000/api/v1")


# ============================================
# MODELS
# ============================================

class WidgetChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None  # ID utilisateur du client (pas Intelia)
    user_email: Optional[str] = None
    metadata: Optional[dict] = None  # Métadonnées additionnelles du client


class WidgetTokenPayload(BaseModel):
    client_id: str  # ID du client (l'entreprise qui utilise le widget)
    user_id: Optional[str] = None  # ID utilisateur dans le système du client
    user_email: Optional[str] = None
    exp: datetime


# ============================================
# JWT AUTHENTICATION
# ============================================

def verify_widget_token(token: str) -> dict:
    """
    Vérifie et décode le JWT token du widget

    Le token doit contenir:
    - client_id: ID du client (l'entreprise)
    - user_id: ID utilisateur dans leur système (optionnel)
    - user_email: Email utilisateur (optionnel)
    - exp: Expiration timestamp

    Raises:
        HTTPException: Si token invalide ou expiré
    """
    if not JWT_SECRET:
        logger.error("JWT_SECRET non configuré pour le widget")
        raise HTTPException(
            status_code=500,
            detail="Configuration serveur invalide"
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Vérifier expiration
        exp = payload.get("exp")
        if exp:
            exp_dt = datetime.fromtimestamp(exp)
            if exp_dt < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Token expiré")

        # Vérifier client_id présent
        if not payload.get("client_id"):
            raise HTTPException(status_code=401, detail="client_id manquant dans le token")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token JWT invalide: {e}")
        raise HTTPException(status_code=401, detail="Token invalide")


async def get_widget_auth(authorization: str = Header(...)) -> dict:
    """
    Dependency pour vérifier l'authentification widget
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Format Authorization invalide")

    token = authorization.replace("Bearer ", "")
    return verify_widget_token(token)


# ============================================
# HELPER FUNCTIONS
# ============================================

async def check_client_quota(client_id: str) -> dict:
    """
    Vérifie le quota du client (entreprise qui utilise le widget)

    Returns:
        Dict avec can_use, requests_used, monthly_limit, etc.
    """
    try:
        supabase = get_supabase_client()

        # Récupérer les infos du client dans la table widget_clients
        response = supabase.table("widget_clients").select("*").eq("client_id", client_id).execute()

        if not response.data:
            logger.warning(f"Client widget inconnu: {client_id}")
            # Par défaut, autoriser (fail-open)
            return {
                "can_use": True,
                "quota_enforcement": False,
                "error": "client_not_found"
            }

        client_data = response.data[0]
        monthly_limit = client_data.get("monthly_limit", 1000)
        is_active = client_data.get("is_active", True)

        if not is_active:
            return {
                "can_use": False,
                "error": "client_disabled",
                "message": "Votre accès au widget a été désactivé"
            }

        # Compter les requêtes du mois en cours
        # TODO: Implémenter compteur dans widget_usage table
        # Pour l'instant, autoriser

        return {
            "can_use": True,
            "quota_enforcement": True,
            "monthly_limit": monthly_limit,
            "requests_used": 0  # TODO: Calculer depuis widget_usage
        }

    except Exception as e:
        logger.error(f"Erreur check quota client: {e}")
        # Fail-open: ne pas bloquer en cas d'erreur
        return {
            "can_use": True,
            "quota_enforcement": False,
            "error": str(e)
        }


async def increment_client_usage(client_id: str, user_id: Optional[str] = None) -> None:
    """
    Incrémente le compteur d'utilisation du client
    """
    try:
        supabase = get_supabase_client()

        # Enregistrer l'utilisation dans widget_usage
        supabase.table("widget_usage").insert({
            "client_id": client_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "request_type": "chat"
        }).execute()

        logger.info(f"Usage enregistré pour client {client_id}")

    except Exception as e:
        logger.error(f"Erreur incrémentation usage client: {e}")
        # Non-bloquant


# ============================================
# ENDPOINTS
# ============================================

@router.post("/chat")
async def widget_chat(
    request_body: WidgetChatRequest,
    auth: dict = Depends(get_widget_auth)
):
    """
    Endpoint de chat pour le widget

    Authentification: JWT Bearer token requis
    Le token doit être généré côté serveur du client avec le secret partagé

    Flow:
    1. Valider JWT token
    2. Vérifier quota client
    3. Appeler le LLM API
    4. Streamer la réponse
    5. Incrémenter compteur usage
    """
    start_time = time.time()
    client_id = auth.get("client_id")

    logger.info(f"Widget chat request - client_id: {client_id}, message: {request_body.message[:50]}...")

    try:
        # 1. Vérifier quota client
        quota_info = await check_client_quota(client_id)
        if not quota_info.get("can_use", True):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "quota_exceeded",
                    "message": quota_info.get("message", "Limite d'utilisation atteinte"),
                    "quota": quota_info
                }
            )

        # 2. Construire tenant_id unique pour ce client
        tenant_id = f"widget_{client_id}"
        conversation_id = request_body.conversation_id or str(uuid.uuid4())

        # 3. Appeler le LLM API
        async with httpx.AsyncClient(timeout=60.0) as client:
            llm_payload = {
                "message": request_body.message,
                "tenant_id": tenant_id,
                "conversation_id": conversation_id,
                "use_json_search": True,
                # On ne passe pas user_email pour éviter quota check utilisateur
                # Le quota est géré au niveau client (entreprise)
            }

            logger.info(f"Appel LLM API: {LLM_API_URL}/chat")

            response = await client.post(
                f"{LLM_API_URL}/chat",
                json=llm_payload,
                headers={
                    "Content-Type": "application/json",
                }
            )

            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Erreur LLM API: {response.text}"
                )

            # 4. Incrémenter usage (fire-and-forget)
            try:
                await increment_client_usage(
                    client_id=client_id,
                    user_id=request_body.user_id or auth.get("user_id")
                )
            except Exception as inc_error:
                logger.error(f"Erreur incrémentation usage (non-bloquante): {inc_error}")

            # 5. Retourner la réponse du LLM
            # Si c'est du streaming, on le transmet tel quel
            if response.headers.get("content-type", "").startswith("text/"):
                async def stream_response():
                    async for chunk in response.aiter_bytes():
                        yield chunk

                return StreamingResponse(
                    stream_response(),
                    media_type="text/plain"
                )
            else:
                # Réponse JSON standard
                return JSONResponse(content=response.json())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur widget chat: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur traitement: {str(e)}"}
        )


class GenerateTokenRequest(BaseModel):
    client_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    expiration_minutes: int = JWT_EXPIRATION_MINUTES


@router.post("/generate-token")
async def generate_widget_token(request: GenerateTokenRequest):
    """
    ENDPOINT ADMINISTRATIF - Générer un JWT token pour le widget

    Cet endpoint est utilisé côté serveur du client pour générer des tokens
    Il doit être protégé (pas exposé publiquement)

    Args:
        request: Contient client_id, user_id (optionnel), user_email (optionnel), expiration_minutes

    Returns:
        JWT token signé
    """
    if not JWT_SECRET:
        logger.error("JWT_SECRET non configuré")
        raise HTTPException(status_code=500, detail="Configuration serveur invalide")

    try:
        # Créer le payload
        exp = datetime.utcnow() + timedelta(minutes=request.expiration_minutes)
        payload = {
            "client_id": request.client_id,
            "user_id": request.user_id,
            "user_email": request.user_email,
            "exp": exp,
            "iat": datetime.utcnow()
        }

        # Signer le token
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        logger.info(f"Token généré pour client: {request.client_id}, user: {request.user_id}")

        return {
            "token": token,
            "expires_at": exp.isoformat(),
            "expires_in_seconds": request.expiration_minutes * 60
        }

    except Exception as e:
        logger.error(f"Erreur génération token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur génération token: {str(e)}")


@router.get("/health")
async def widget_health():
    """
    Health check pour le widget API
    """
    return {
        "status": "ok",
        "service": "widget",
        "version": "1.0.0",
        "jwt_configured": bool(JWT_SECRET),
        "llm_api_url": LLM_API_URL
    }
