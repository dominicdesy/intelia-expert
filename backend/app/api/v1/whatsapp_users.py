# app/api/v1/whatsapp_users.py
# -*- coding: utf-8 -*-
"""
WhatsApp User Management
Permet aux utilisateurs d'ajouter/vérifier leur numéro WhatsApp
Version: 1.0
"""

import os
import logging
import psycopg2
import random
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from twilio.rest import Client

from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/whatsapp/user", tags=["whatsapp-users"])
logger = logging.getLogger(__name__)

# Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+15075195932")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialiser Twilio
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    logger.info("✅ Twilio client initialized for user management")


# ==================== MODELS ====================

class AddWhatsAppNumberRequest(BaseModel):
    whatsapp_number: str  # Format: +1234567890


class VerifyWhatsAppCodeRequest(BaseModel):
    verification_code: str


class WhatsAppStatusResponse(BaseModel):
    has_whatsapp: bool
    whatsapp_number: Optional[str] = None
    whatsapp_verified: bool = False
    verified_at: Optional[str] = None


# ==================== HELPERS ====================

def get_db_connection():
    """Créer une connexion à la base de données"""
    return psycopg2.connect(DATABASE_URL)


def normalize_phone_number(phone: str) -> str:
    """
    Normalise un numéro de téléphone
    Entrée: +1234567890 ou 1234567890 ou (123) 456-7890
    Sortie: +1234567890
    """
    # Enlever tous les caractères non-numériques sauf le +
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

    # Ajouter + si manquant
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned

    return cleaned


def generate_verification_code() -> str:
    """Génère un code de vérification à 6 chiffres"""
    return str(random.randint(100000, 999999))


def send_verification_code(whatsapp_number: str, code: str) -> bool:
    """
    Envoie un code de vérification par WhatsApp

    Args:
        whatsapp_number: Numéro WhatsApp (format: +1234567890)
        code: Code de vérification à 6 chiffres

    Returns:
        True si envoyé avec succès
    """
    try:
        if not twilio_client:
            logger.error("❌ Twilio client not initialized")
            return False

        # Format Twilio
        to_number = f"whatsapp:{whatsapp_number}"

        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number,
            body=f"""🔐 Code de vérification Intelia Cognito

Votre code : {code}

Ce code expire dans 10 minutes.

Si vous n'avez pas demandé ce code, ignorez ce message."""
        )

        logger.info(f"✅ Verification code sent to {whatsapp_number}: {message.sid}")
        return True

    except Exception as e:
        logger.error(f"❌ Error sending verification code: {e}")
        return False


# ==================== ENDPOINTS ====================

@router.get("/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupère le statut WhatsApp de l'utilisateur
    """
    try:
        user_email = current_user.get("email")

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT whatsapp_number, whatsapp_verified, verified_at
                    FROM user_whatsapp_info
                    WHERE user_email = %s
                    """,
                    (user_email,)
                )
                result = cur.fetchone()

                if not result:
                    return WhatsAppStatusResponse(has_whatsapp=False)

                return WhatsAppStatusResponse(
                    has_whatsapp=True,
                    whatsapp_number=result["whatsapp_number"],
                    whatsapp_verified=result["whatsapp_verified"],
                    verified_at=result["verified_at"].isoformat() if result["verified_at"] else None
                )

    except Exception as e:
        logger.error(f"❌ Error getting WhatsApp status: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du statut")


@router.post("/add-number")
async def add_whatsapp_number(
    request: AddWhatsAppNumberRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Ajoute un numéro WhatsApp et envoie un code de vérification
    """
    try:
        user_email = current_user.get("email")
        whatsapp_number = normalize_phone_number(request.whatsapp_number)

        # Vérifier que le numéro n'est pas déjà utilisé par un autre utilisateur
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT user_email FROM user_whatsapp_info
                    WHERE whatsapp_number = %s AND user_email != %s
                    """,
                    (whatsapp_number, user_email)
                )
                existing = cur.fetchone()

                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail="Ce numéro WhatsApp est déjà utilisé par un autre compte"
                    )

                # Générer code de vérification
                verification_code = generate_verification_code()

                # Envoyer le code
                if not send_verification_code(whatsapp_number, verification_code):
                    raise HTTPException(
                        status_code=500,
                        detail="Impossible d'envoyer le code de vérification"
                    )

                # Sauvegarder dans la DB (non vérifié)
                cur.execute(
                    """
                    INSERT INTO user_whatsapp_info (
                        user_email, whatsapp_number, whatsapp_verified,
                        verification_code, verification_sent_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_email) DO UPDATE SET
                        whatsapp_number = EXCLUDED.whatsapp_number,
                        whatsapp_verified = FALSE,
                        verification_code = EXCLUDED.verification_code,
                        verification_sent_at = EXCLUDED.verification_sent_at,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (user_email, whatsapp_number, False, verification_code, datetime.utcnow())
                )
                conn.commit()

                logger.info(f"✅ WhatsApp number added for {user_email}: {whatsapp_number}")

                return {
                    "success": True,
                    "message": "Code de vérification envoyé par WhatsApp",
                    "whatsapp_number": whatsapp_number
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error adding WhatsApp number: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du numéro")


@router.post("/verify-code")
async def verify_whatsapp_code(
    request: VerifyWhatsAppCodeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Vérifie le code de vérification WhatsApp
    """
    try:
        user_email = current_user.get("email")

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer les infos de vérification
                cur.execute(
                    """
                    SELECT whatsapp_number, verification_code, verification_sent_at
                    FROM user_whatsapp_info
                    WHERE user_email = %s
                    """,
                    (user_email,)
                )
                result = cur.fetchone()

                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Aucun numéro WhatsApp trouvé. Ajoutez d'abord un numéro."
                    )

                # Vérifier expiration (10 minutes)
                sent_at = result["verification_sent_at"]
                if sent_at and datetime.utcnow() - sent_at > timedelta(minutes=10):
                    raise HTTPException(
                        status_code=400,
                        detail="Code expiré. Demandez un nouveau code."
                    )

                # Vérifier le code
                if result["verification_code"] != request.verification_code:
                    raise HTTPException(
                        status_code=400,
                        detail="Code de vérification incorrect"
                    )

                # Marquer comme vérifié
                cur.execute(
                    """
                    UPDATE user_whatsapp_info
                    SET whatsapp_verified = TRUE,
                        verified_at = CURRENT_TIMESTAMP,
                        verification_code = NULL,
                        verification_sent_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_email = %s
                    """,
                    (user_email,)
                )
                conn.commit()

                logger.info(f"✅ WhatsApp verified for {user_email}")

                return {
                    "success": True,
                    "message": "Numéro WhatsApp vérifié avec succès !",
                    "whatsapp_number": result["whatsapp_number"]
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying code: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification")


@router.post("/resend-code")
async def resend_verification_code(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Renvoie un code de vérification
    """
    try:
        user_email = current_user.get("email")

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT whatsapp_number, whatsapp_verified
                    FROM user_whatsapp_info
                    WHERE user_email = %s
                    """,
                    (user_email,)
                )
                result = cur.fetchone()

                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Aucun numéro WhatsApp trouvé"
                    )

                if result["whatsapp_verified"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Numéro déjà vérifié"
                    )

                # Générer nouveau code
                verification_code = generate_verification_code()

                # Envoyer
                if not send_verification_code(result["whatsapp_number"], verification_code):
                    raise HTTPException(
                        status_code=500,
                        detail="Impossible d'envoyer le code"
                    )

                # Mettre à jour
                cur.execute(
                    """
                    UPDATE user_whatsapp_info
                    SET verification_code = %s,
                        verification_sent_at = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_email = %s
                    """,
                    (verification_code, datetime.utcnow(), user_email)
                )
                conn.commit()

                return {
                    "success": True,
                    "message": "Nouveau code envoyé"
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resending code: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'envoi")


@router.delete("/remove-number")
async def remove_whatsapp_number(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Supprime le numéro WhatsApp de l'utilisateur
    """
    try:
        user_email = current_user.get("email")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_whatsapp_info WHERE user_email = %s",
                    (user_email,)
                )
                conn.commit()

                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=404,
                        detail="Aucun numéro WhatsApp trouvé"
                    )

                logger.info(f"✅ WhatsApp number removed for {user_email}")

                return {
                    "success": True,
                    "message": "Numéro WhatsApp supprimé"
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error removing WhatsApp number: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression")
