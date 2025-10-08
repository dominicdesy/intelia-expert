# app/api/v1/webhooks.py
"""
Endpoints webhook pour recevoir les événements d'authentification de Supabase
Version 1.0 - Support des Auth Hooks
"""

import os
import logging
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, EmailStr

from app.services.email_service import get_email_service, EmailType

router = APIRouter(prefix="/webhooks")
logger = logging.getLogger(__name__)


# === MODÈLES PYDANTIC POUR LES WEBHOOKS ===


class SupabaseUserMetadata(BaseModel):
    """Métadonnées utilisateur Supabase"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    preferred_language: Optional[str] = "en"
    company: Optional[str] = None
    phone: Optional[str] = None


class SupabaseUser(BaseModel):
    """Utilisateur Supabase"""
    id: str
    email: EmailStr
    email_confirmed_at: Optional[str] = None
    user_metadata: Optional[SupabaseUserMetadata] = None
    created_at: str
    updated_at: Optional[str] = None


class SupabaseAuthEvent(BaseModel):
    """Événement d'authentification Supabase"""
    event: str  # signup, login, password_reset, etc.
    user: SupabaseUser
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SupabaseWebhookPayload(BaseModel):
    """Payload complet du webhook Supabase"""
    type: str  # Type d'événement
    table: Optional[str] = None
    record: Optional[Dict[str, Any]] = None
    schema: Optional[str] = None
    old_record: Optional[Dict[str, Any]] = None


class SupabaseAuthHookPayload(BaseModel):
    """
    Payload des Auth Hooks Supabase
    Documentation: https://supabase.com/docs/guides/auth/auth-hooks
    """
    event: str  # "user.created", "user.updated", "user.deleted", etc.
    user_id: str
    email: EmailStr
    email_confirmed: bool
    user_metadata: Optional[Dict[str, Any]] = None
    app_metadata: Optional[Dict[str, Any]] = None
    created_at: str
    # Champs spécifiques aux événements
    confirmation_token: Optional[str] = None
    confirmation_url: Optional[str] = None
    recovery_token: Optional[str] = None
    recovery_url: Optional[str] = None
    email_change_token: Optional[str] = None
    email_change_url: Optional[str] = None
    invite_token: Optional[str] = None
    invite_url: Optional[str] = None


# === FONCTIONS HELPER ===


def verify_supabase_webhook_signature(
    payload: bytes,
    signature: Optional[str],
    secret: str,
) -> bool:
    """
    Vérifie la signature du webhook Supabase pour sécuriser l'endpoint
    """
    if not signature or not secret:
        logger.warning("Missing signature or secret for webhook verification")
        return False

    try:
        # Supabase utilise HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


def get_user_language(user_metadata: Optional[Dict[str, Any]]) -> str:
    """Extrait la langue préférée de l'utilisateur depuis les metadata"""
    if not user_metadata:
        return "en"

    return user_metadata.get("preferred_language", "en")


def get_user_first_name(user_metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extrait le prénom de l'utilisateur depuis les metadata"""
    if not user_metadata:
        return None

    return user_metadata.get("first_name") or user_metadata.get("full_name")


# === ENDPOINTS WEBHOOK ===


@router.post("/supabase/auth")
async def supabase_auth_webhook(
    request: Request,
    x_supabase_signature: Optional[str] = Header(None),
):
    """
    Endpoint webhook pour recevoir les événements d'authentification de Supabase

    Ce webhook est appelé par Supabase Auth Hooks lors des événements:
    - user.created (signup)
    - password.recovery.requested (reset password)
    - email.change.requested (change email)
    - user.invited (invite)

    Documentation: https://supabase.com/docs/guides/auth/auth-hooks
    """
    logger.info("[Webhook] Received Supabase auth event")

    # Récupérer le body brut pour vérification de signature
    body_bytes = await request.body()

    # Vérifier la signature du webhook (sécurité)
    webhook_secret = os.getenv("SUPABASE_WEBHOOK_SECRET")
    if webhook_secret and x_supabase_signature:
        is_valid = verify_supabase_webhook_signature(
            body_bytes, x_supabase_signature, webhook_secret
        )
        if not is_valid:
            logger.error("[Webhook] Invalid signature")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif webhook_secret:
        logger.warning(
            "[Webhook] No signature provided but secret is configured - rejecting"
        )
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    # Parser le payload
    try:
        import json

        payload_dict = json.loads(body_bytes.decode())
        logger.debug(f"[Webhook] Payload keys: {payload_dict.keys()}")
        logger.debug(f"[Webhook] Event type: {payload_dict.get('type')}")

    except Exception as e:
        logger.error(f"[Webhook] Failed to parse payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extraire les informations selon le format du webhook
    event_type = payload_dict.get("type") or payload_dict.get("event")
    user_data = payload_dict.get("record") or payload_dict

    logger.info(f"[Webhook] Processing event: {event_type}")

    # Traiter selon le type d'événement
    try:
        if event_type in ["INSERT", "user.created", "user.signup"]:
            # Nouveau compte créé - envoyer email de confirmation
            await handle_signup_event(user_data)

        elif event_type in ["password.recovery.requested", "user.password_reset"]:
            # Demande de reset password - envoyer email
            await handle_password_reset_event(user_data)

        elif event_type in ["email.change.requested", "user.email_change"]:
            # Demande de changement d'email - envoyer email
            await handle_email_change_event(user_data)

        elif event_type in ["user.invited", "user.invite"]:
            # Invitation utilisateur - envoyer email
            await handle_invite_event(user_data)

        else:
            logger.warning(f"[Webhook] Unhandled event type: {event_type}")
            return {
                "success": True,
                "message": f"Event type '{event_type}' acknowledged but not processed",
            }

        logger.info(f"[Webhook] Successfully processed event: {event_type}")
        return {"success": True, "message": f"Event '{event_type}' processed"}

    except Exception as e:
        logger.error(f"[Webhook] Error processing event {event_type}: {e}")
        # Ne pas faire échouer le webhook, juste logger
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to process event '{event_type}'",
        }


# === HANDLERS POUR CHAQUE TYPE D'ÉVÉNEMENT ===


async def handle_signup_event(user_data: Dict[str, Any]):
    """Traite l'événement de signup et envoie l'email de confirmation"""
    logger.info("[Webhook/Signup] Processing signup event")

    # Extraire les informations utilisateur
    email = user_data.get("email")
    user_metadata = user_data.get("user_metadata") or user_data.get("raw_user_meta_data") or {}

    # Récupérer le token et l'URL de confirmation
    confirmation_token = user_data.get("confirmation_token") or user_data.get("email_confirmation_token")
    confirmation_url = user_data.get("confirmation_url")

    # Si pas d'URL fournie, construire une URL de base
    if not confirmation_url and confirmation_token:
        frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
        confirmation_url = f"{frontend_url}/auth/confirm?token={confirmation_token}"

    if not email or not confirmation_token:
        logger.error(f"[Webhook/Signup] Missing required fields: email={bool(email)}, token={bool(confirmation_token)}")
        return

    # Extraire les préférences utilisateur
    language = get_user_language(user_metadata)
    first_name = get_user_first_name(user_metadata)

    logger.info(f"[Webhook/Signup] Sending signup email to {email} in language '{language}'")

    # Envoyer l'email via notre service
    email_service = get_email_service()
    success = email_service.send_auth_email(
        email_type=EmailType.SIGNUP_CONFIRMATION,
        to_email=email,
        language=language,
        confirmation_url=confirmation_url,
        otp_token=confirmation_token,
        first_name=first_name,
    )

    if success:
        logger.info(f"[Webhook/Signup] Email sent successfully to {email}")
    else:
        logger.error(f"[Webhook/Signup] Failed to send email to {email}")


async def handle_password_reset_event(user_data: Dict[str, Any]):
    """Traite l'événement de reset password et envoie l'email"""
    logger.info("[Webhook/PasswordReset] Processing password reset event")

    # Extraire les informations
    email = user_data.get("email")
    user_metadata = user_data.get("user_metadata") or user_data.get("raw_user_meta_data") or {}

    recovery_token = user_data.get("recovery_token") or user_data.get("password_reset_token")
    recovery_url = user_data.get("recovery_url")

    if not recovery_url and recovery_token:
        frontend_url = os.getenv("FRONTEND_URL", "https://expert.intelia.com")
        recovery_url = f"{frontend_url}/auth/reset-password?token={recovery_token}"

    if not email or not recovery_token:
        logger.error(f"[Webhook/PasswordReset] Missing required fields: email={bool(email)}, token={bool(recovery_token)}")
        return

    language = get_user_language(user_metadata)
    first_name = get_user_first_name(user_metadata)

    logger.info(f"[Webhook/PasswordReset] Sending reset email to {email} in language '{language}'")

    email_service = get_email_service()
    success = email_service.send_auth_email(
        email_type=EmailType.PASSWORD_RESET,
        to_email=email,
        language=language,
        confirmation_url=recovery_url,
        otp_token=recovery_token,
        first_name=first_name,
    )

    if success:
        logger.info(f"[Webhook/PasswordReset] Email sent successfully to {email}")
    else:
        logger.error(f"[Webhook/PasswordReset] Failed to send email to {email}")


async def handle_email_change_event(user_data: Dict[str, Any]):
    """Traite l'événement de changement d'email"""
    logger.info("[Webhook/EmailChange] Processing email change event")
    # TODO: Implémenter si nécessaire
    logger.warning("[Webhook/EmailChange] Not implemented yet")


async def handle_invite_event(user_data: Dict[str, Any]):
    """Traite l'événement d'invitation utilisateur"""
    logger.info("[Webhook/Invite] Processing invite event")
    # TODO: Implémenter si nécessaire
    logger.warning("[Webhook/Invite] Not implemented yet")


# === ENDPOINT DE TEST ===


@router.post("/supabase/auth/test")
async def test_webhook():
    """Endpoint de test pour vérifier que les webhooks fonctionnent"""
    logger.info("[Webhook/Test] Test endpoint called")
    return {
        "success": True,
        "message": "Webhook endpoint is working",
        "timestamp": datetime.utcnow().isoformat(),
        "email_service_configured": bool(
            os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD")
        ),
        "webhook_secret_configured": bool(os.getenv("SUPABASE_WEBHOOK_SECRET")),
    }


@router.get("/supabase/auth/config")
async def webhook_config():
    """Endpoint de debug pour vérifier la configuration des webhooks"""
    return {
        "webhook_url": f"{os.getenv('BACKEND_URL', 'https://expert-app-cngws.ondigitalocean.app')}/api/v1/webhooks/supabase/auth",
        "smtp_configured": bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD")),
        "webhook_secret_configured": bool(os.getenv("SUPABASE_WEBHOOK_SECRET")),
        "supported_events": [
            "user.created (signup)",
            "password.recovery.requested (reset password)",
            "email.change.requested (change email)",
            "user.invited (invite)",
        ],
        "email_languages_supported": [
            "en", "fr", "es", "de", "pt", "th", "zh", "ru",
            "hi", "id", "it", "nl", "pl",
        ],
    }
