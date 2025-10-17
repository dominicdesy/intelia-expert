"""
WebAuthn API - Biometric Authentication (Face ID, Touch ID, Fingerprint)
=========================================================================
Endpoints pour l'authentification biométrique via WebAuthn/Passkeys
"""

import os
import logging
import secrets
import base64
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    PublicKeyCredentialDescriptor,
)

from app.core.database import get_supabase_client
from app.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/webauthn", tags=["WebAuthn"])
logger = logging.getLogger(__name__)

# Configuration WebAuthn
RP_ID = os.getenv("WEBAUTHN_RP_ID", "expert.intelia.com")  # Relying Party ID (votre domaine)
RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "Intelia Expert")
ORIGIN = os.getenv("WEBAUTHN_ORIGIN", "https://expert.intelia.com")

# Cache temporaire pour les challenges (en production, utiliser Redis)
# Format: {user_id: {challenge: bytes, expires_at: datetime}}
registration_challenges = {}
authentication_challenges = {}

# ============================================================================
# MODELS PYDANTIC
# ============================================================================

class RegistrationStartRequest(BaseModel):
    device_name: Optional[str] = None  # "iPhone 15", "MacBook Pro", etc.


class RegistrationStartResponse(BaseModel):
    options: dict  # PublicKeyCredentialCreationOptions en JSON


class RegistrationVerifyRequest(BaseModel):
    credential: dict  # PublicKeyCredential from navigator.credentials.create()
    device_name: Optional[str] = None


class RegistrationVerifyResponse(BaseModel):
    success: bool
    message: str
    credential_id: Optional[str] = None


class AuthenticationStartRequest(BaseModel):
    pass  # Pas de paramètres nécessaires


class AuthenticationStartResponse(BaseModel):
    options: dict  # PublicKeyCredentialRequestOptions en JSON


class AuthenticationVerifyRequest(BaseModel):
    credential: dict  # PublicKeyCredential from navigator.credentials.get()


class AuthenticationVerifyResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None  # JWT token si authentification réussie


class PasskeyInfo(BaseModel):
    id: str
    credential_id: str
    device_name: Optional[str]
    device_type: Optional[str]
    created_at: str
    last_used_at: Optional[str]
    backup_eligible: bool
    backup_state: bool


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clean_expired_challenges():
    """Nettoie les challenges expirés (appelé avant chaque création)"""
    now = datetime.now()

    global registration_challenges
    registration_challenges = {
        uid: data for uid, data in registration_challenges.items()
        if data.get("expires_at", now) > now
    }

    global authentication_challenges
    authentication_challenges = {
        uid: data for uid, data in authentication_challenges.items()
        if data.get("expires_at", now) > now
    }


def get_user_credentials(user_id: str) -> list:
    """Récupère les credentials WebAuthn de l'utilisateur depuis Supabase"""
    try:
        supabase = get_supabase_client()
        response = supabase.table("webauthn_credentials").select("*").eq("user_id", user_id).execute()

        if response.data:
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error fetching user credentials: {e}")
        return []


def save_credential(user_id: str, credential_data: dict) -> bool:
    """Sauvegarde un nouveau credential dans Supabase"""
    try:
        supabase = get_supabase_client()

        data = {
            "user_id": user_id,
            "credential_id": credential_data["credential_id"],
            "public_key": credential_data["public_key"],
            "counter": credential_data["counter"],
            "device_type": credential_data.get("device_type"),
            "device_name": credential_data.get("device_name"),
            "transports": credential_data.get("transports", []),
            "backup_eligible": credential_data.get("backup_eligible", False),
            "backup_state": credential_data.get("backup_state", False),
            "created_at": datetime.now().isoformat(),
        }

        response = supabase.table("webauthn_credentials").insert(data).execute()
        logger.info(f"✅ Credential saved for user {user_id}: {credential_data['credential_id'][:20]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving credential: {e}")
        return False


def update_credential_usage(credential_id: str, new_counter: int) -> bool:
    """Met à jour le compteur et last_used_at après authentification"""
    try:
        supabase = get_supabase_client()

        data = {
            "counter": new_counter,
            "last_used_at": datetime.now().isoformat(),
        }

        response = supabase.table("webauthn_credentials").update(data).eq("credential_id", credential_id).execute()
        logger.info(f"✅ Credential usage updated: {credential_id[:20]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating credential: {e}")
        return False


# ============================================================================
# ENDPOINTS - REGISTRATION (Setup Passkey)
# ============================================================================

@router.post("/register/start", response_model=RegistrationStartResponse)
async def registration_start(
    request: RegistrationStartRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Étape 1: Génère les options pour l'enregistrement d'un nouveau passkey

    L'utilisateur doit être connecté (via email/password ou OAuth)
    """
    try:
        user_id = current_user["user_id"]
        user_email = current_user.get("email", "")
        user_name = current_user.get("full_name") or current_user.get("name") or user_email

        logger.info(f"🔐 [WEBAUTHN] Registration start for user: {user_id}")

        # Nettoyer les challenges expirés
        clean_expired_challenges()

        # Récupérer les credentials existants pour les exclure
        existing_credentials = get_user_credentials(user_id)
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred["credential_id"]))
            for cred in existing_credentials
        ]

        # Générer les options d'enregistrement
        registration_options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user_id.encode('utf-8'),  # Convertir UUID en bytes
            user_name=user_email,
            user_display_name=user_name,
            attestation=AttestationConveyancePreference.NONE,  # Pas besoin d'attestation
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,  # Platform = Face ID, Touch ID (built-in)
                resident_key=ResidentKeyRequirement.PREFERRED,  # Synced passkeys
                user_verification=UserVerificationRequirement.REQUIRED,  # Force biometric
            ),
            exclude_credentials=exclude_credentials,  # Éviter les doublons
            timeout=60000,  # 60 secondes
        )

        # Sauvegarder le challenge temporairement
        registration_challenges[user_id] = {
            "challenge": registration_options.challenge,
            "expires_at": datetime.now() + timedelta(minutes=5),
            "device_name": request.device_name,
        }

        # Convertir en dict pour le frontend
        import json
        options_json_str = options_to_json(registration_options)
        options_dict = json.loads(options_json_str)

        logger.info(f"✅ [WEBAUTHN] Registration options generated for user {user_id}")

        return RegistrationStartResponse(options=options_dict)

    except Exception as e:
        logger.error(f"❌ [WEBAUTHN] Registration start error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start registration: {str(e)}")


@router.post("/register/finish", response_model=RegistrationVerifyResponse)
async def registration_finish(
    request: RegistrationVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Étape 2: Vérifie la réponse du navigateur et sauvegarde le credential
    """
    try:
        user_id = current_user["user_id"]

        logger.info(f"🔐 [WEBAUTHN] Registration verify for user: {user_id}")

        # Récupérer le challenge sauvegardé
        challenge_data = registration_challenges.get(user_id)
        if not challenge_data:
            raise HTTPException(status_code=400, detail="No pending registration challenge")

        expected_challenge = challenge_data["challenge"]
        device_name = request.device_name or challenge_data.get("device_name")

        # Vérifier la réponse
        verification = verify_registration_response(
            credential=request.credential,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )

        # Sauvegarder le credential dans la DB
        credential_data = {
            "credential_id": bytes_to_base64url(verification.credential_id),
            "public_key": bytes_to_base64url(verification.credential_public_key),
            "counter": verification.sign_count,
            "device_type": "platform",  # Platform authenticator (Face ID, Touch ID)
            "device_name": device_name,
            "transports": request.credential.get("response", {}).get("transports", []),
            "backup_eligible": verification.credential_backed_up,
            "backup_state": verification.credential_backed_up,
        }

        success = save_credential(user_id, credential_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save credential")

        # Nettoyer le challenge
        del registration_challenges[user_id]

        logger.info(f"✅ [WEBAUTHN] Registration successful for user {user_id}")

        return RegistrationVerifyResponse(
            success=True,
            message="Passkey registered successfully",
            credential_id=credential_data["credential_id"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [WEBAUTHN] Registration verify error: {e}")
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")


# ============================================================================
# ENDPOINTS - AUTHENTICATION (Login with Passkey)
# ============================================================================

@router.post("/authenticate/start", response_model=AuthenticationStartResponse)
async def authentication_start(request: AuthenticationStartRequest):
    """
    Étape 1: Génère les options pour l'authentification via passkey

    Note: Pas besoin d'être connecté (c'est justement pour se connecter!)
    """
    try:
        logger.info(f"🔐 [WEBAUTHN] Authentication start")

        # Nettoyer les challenges expirés
        clean_expired_challenges()

        # Générer un challenge unique
        challenge = secrets.token_bytes(32)
        challenge_id = secrets.token_urlsafe(32)

        # Sauvegarder temporairement (sans user_id car on ne sait pas encore qui se connecte)
        authentication_challenges[challenge_id] = {
            "challenge": challenge,
            "expires_at": datetime.now() + timedelta(minutes=5),
        }

        # Générer les options d'authentification
        # Note: On ne spécifie pas allowCredentials pour permettre n'importe quel passkey
        authentication_options = generate_authentication_options(
            rp_id=RP_ID,
            challenge=challenge,
            user_verification=UserVerificationRequirement.REQUIRED,
            timeout=60000,  # 60 secondes
        )

        # Convertir en dict
        import json
        options_json_str = options_to_json(authentication_options)
        options_dict = json.loads(options_json_str)

        # Ajouter le challenge_id au response pour le retrouver lors de verify
        options_dict["challenge_id"] = challenge_id

        logger.info(f"✅ [WEBAUTHN] Authentication options generated")

        return AuthenticationStartResponse(options=options_dict)

    except Exception as e:
        logger.error(f"❌ [WEBAUTHN] Authentication start error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start authentication: {str(e)}")


@router.post("/authenticate/finish", response_model=AuthenticationVerifyResponse)
async def authentication_finish(request: AuthenticationVerifyRequest):
    """
    Étape 2: Vérifie la réponse et retourne un JWT token si valide
    """
    try:
        logger.info(f"🔐 [WEBAUTHN] Authentication verify")

        # Récupérer le challenge_id du credential
        challenge_id = request.credential.get("challenge_id")
        if not challenge_id:
            raise HTTPException(status_code=400, detail="Missing challenge_id")

        # Récupérer le challenge sauvegardé
        challenge_data = authentication_challenges.get(challenge_id)
        if not challenge_data:
            raise HTTPException(status_code=400, detail="No pending authentication challenge or challenge expired")

        expected_challenge = challenge_data["challenge"]

        # Récupérer le credential_id de la réponse
        raw_credential_id = request.credential.get("rawId") or request.credential.get("id")
        if not raw_credential_id:
            raise HTTPException(status_code=400, detail="Missing credential ID")

        credential_id_base64 = bytes_to_base64url(base64.b64decode(raw_credential_id))

        # Trouver le credential dans la DB
        supabase = get_supabase_client()
        response = supabase.table("webauthn_credentials").select("*").eq("credential_id", credential_id_base64).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Credential not found")

        credential_record = response.data[0]
        user_id = credential_record["user_id"]

        # Vérifier la réponse d'authentification
        verification = verify_authentication_response(
            credential=request.credential,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=base64url_to_bytes(credential_record["public_key"]),
            credential_current_sign_count=credential_record["counter"],
        )

        # Mettre à jour le compteur d'utilisation
        update_credential_usage(credential_id_base64, verification.new_sign_count)

        # Nettoyer le challenge
        del authentication_challenges[challenge_id]

        # TODO: Générer un JWT token pour l'utilisateur (à implémenter avec votre système existant)
        # Pour l'instant, retourner juste success avec user_id

        logger.info(f"✅ [WEBAUTHN] Authentication successful for user {user_id}")

        return AuthenticationVerifyResponse(
            success=True,
            message="Authentication successful",
            token="TODO_GENERATE_JWT_TOKEN"  # À implémenter
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [WEBAUTHN] Authentication verify error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


# ============================================================================
# ENDPOINTS - MANAGEMENT (List, Delete)
# ============================================================================

@router.get("/credentials", response_model=dict)
async def list_credentials(current_user: dict = Depends(get_current_user)):
    """
    Liste tous les passkeys de l'utilisateur connecté
    """
    try:
        user_id = current_user["user_id"]
        credentials = get_user_credentials(user_id)

        passkeys = [
            PasskeyInfo(
                id=cred["id"],
                credential_id=cred["credential_id"],
                device_name=cred.get("device_name"),
                device_type=cred.get("device_type"),
                created_at=cred["created_at"],
                last_used_at=cred.get("last_used_at"),
                backup_eligible=cred.get("backup_eligible", False),
                backup_state=cred.get("backup_state", False),
            )
            for cred in credentials
        ]

        logger.info(f"✅ [WEBAUTHN] Listed {len(passkeys)} passkeys for user {user_id}")
        return {"credentials": passkeys}

    except Exception as e:
        logger.error(f"❌ [WEBAUTHN] List passkeys error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list passkeys: {str(e)}")


@router.delete("/credentials/{credential_id}")
async def delete_credential(credential_id: str, current_user: dict = Depends(get_current_user)):
    """
    Supprime un passkey spécifique
    """
    try:
        user_id = current_user["user_id"]

        supabase = get_supabase_client()

        # Vérifier que le credential appartient bien à l'utilisateur
        response = supabase.table("webauthn_credentials").select("*").eq("credential_id", credential_id).eq("user_id", user_id).execute()

        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Passkey not found")

        # Supprimer
        supabase.table("webauthn_credentials").delete().eq("credential_id", credential_id).execute()

        logger.info(f"✅ [WEBAUTHN] Deleted passkey {credential_id[:20]}... for user {user_id}")

        return {"success": True, "message": "Passkey deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [WEBAUTHN] Delete passkey error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete passkey: {str(e)}")


@router.get("/support")
async def check_webauthn_support():
    """
    Vérifie si WebAuthn est supporté (info pour le frontend)
    """
    return {
        "rp_id": RP_ID,
        "rp_name": RP_NAME,
        "origin": ORIGIN,
        "supported": True,
        "platform_authenticator_available": True,  # Le frontend devra vérifier via PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
    }
