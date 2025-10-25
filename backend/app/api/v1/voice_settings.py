"""
Voice Settings API
==================

Endpoints pour gérer les préférences vocales utilisateur
(voix et vitesse de l'assistant vocal)

Accès: Plans Elite et Intelia uniquement
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from pydantic import BaseModel, Field, validator
import logging

from app.api.v1.auth import get_current_user
from app.core.database import get_pg_connection, get_supabase_client
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice-settings", tags=["voice-settings"])

# ============================================================
# MODELS
# ============================================================

VALID_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


class VoiceSettings(BaseModel):
    """Modèle des préférences vocales"""
    voice_preference: str = Field(
        default="alloy",
        description="Voix OpenAI TTS (alloy, echo, fable, onyx, nova, shimmer)"
    )
    voice_speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Vitesse de parole (0.25-4.0, recommandé: 0.8-1.5)"
    )

    @validator('voice_preference')
    def validate_voice(cls, v):
        if v not in VALID_VOICES:
            raise ValueError(f"Voice must be one of: {', '.join(VALID_VOICES)}")
        return v

    @validator('voice_speed')
    def validate_speed(cls, v):
        if not (0.8 <= v <= 1.5):
            logger.warning(f"Voice speed {v} outside recommended range (0.8-1.5)")
        return round(v, 2)  # Arrondir à 2 décimales


class VoiceSettingsResponse(BaseModel):
    """Réponse avec préférences vocales"""
    voice_preference: str
    voice_speed: float
    can_use_voice: bool
    plan: str


# ============================================================
# HELPERS
# ============================================================

def check_voice_access(user: Dict[str, Any]) -> bool:
    """
    Vérifie si l'utilisateur a accès au mode vocal

    Accès: Elite ou Intelia uniquement
    """
    plan = user.get("plan", "")
    is_admin = user.get("is_admin", False)

    # Super admins ont toujours accès
    if is_admin:
        return True

    # Plans avec accès vocal
    return plan in ["elite", "intelia"]


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("", response_model=VoiceSettingsResponse)
async def get_voice_settings(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> VoiceSettingsResponse:
    """
    Récupère les préférences vocales de l'utilisateur connecté

    Returns:
        - voice_preference: Voix sélectionnée
        - voice_speed: Vitesse de parole
        - can_use_voice: L'utilisateur a-t-il accès au mode vocal
        - plan: Plan de l'utilisateur
    """
    user_id = current_user.get("user_id") or current_user.get("sub") or current_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    try:
        # 1. Récupérer préférences vocales depuis Supabase
        supabase = get_supabase_client()
        supabase_response = supabase.table("users").select(
            "email, voice_preference, voice_speed"
        ).eq("id", user_id).execute()

        if not supabase_response.data or len(supabase_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in Supabase"
            )

        user_data = supabase_response.data[0]
        user_email = user_data.get("email")
        voice_preference = user_data.get("voice_preference") or "alloy"
        voice_speed = float(user_data.get("voice_speed") or 1.0)

        # 2. Récupérer plan depuis backend PostgreSQL
        plan = "essential"  # Valeur par défaut
        if user_email:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT plan_name
                        FROM user_billing_info
                        WHERE user_email = %s
                    """, (user_email,))

                    billing_result = cur.fetchone()
                    if billing_result:
                        plan = billing_result.get("plan_name") or "essential"

        # 3. Vérifier accès vocal
        can_use = check_voice_access({
            "plan": plan,
            "is_admin": current_user.get("is_admin", False)
        })

        logger.info(
            f"[VoiceSettings] GET for user {user_id} ({user_email}): "
            f"voice={voice_preference}, speed={voice_speed}, plan={plan}"
        )

        return VoiceSettingsResponse(
            voice_preference=voice_preference,
            voice_speed=voice_speed,
            can_use_voice=can_use,
            plan=plan
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VoiceSettings] GET error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve voice settings"
        )


@router.put("", response_model=VoiceSettingsResponse)
async def update_voice_settings(
    settings: VoiceSettings,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> VoiceSettingsResponse:
    """
    Met à jour les préférences vocales de l'utilisateur

    Restrictions:
    - Accès réservé aux plans Elite et Intelia
    - Voix: alloy, echo, fable, onyx, nova, shimmer
    - Vitesse: 0.25-4.0 (recommandé: 0.8-1.5)

    Args:
        settings: Nouvelles préférences (voice_preference, voice_speed)

    Returns:
        Préférences mises à jour
    """
    user_id = current_user.get("user_id") or current_user.get("sub") or current_user.get("id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    # Vérifier accès vocal
    if not check_voice_access(current_user):
        plan = current_user.get("plan", "unknown")
        logger.warning(
            f"[VoiceSettings] PUT denied for user {user_id} (plan: {plan})"
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "voice_feature_not_available",
                "message": "Voice settings are only available for Elite and Intelia plans. Please upgrade your plan.",
                "current_plan": plan,
                "required_plan": "elite",
                "upgrade_url": "/billing/plans"
            }
        )

    try:
        # Mettre à jour les préférences dans Supabase
        supabase = get_supabase_client()
        update_response = supabase.table("users").update({
            "voice_preference": settings.voice_preference,
            "voice_speed": settings.voice_speed
        }).eq("id", user_id).execute()

        if not update_response.data or len(update_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        updated_data = update_response.data[0]

        logger.info(
            f"[VoiceSettings] PUT success for user {user_id}: "
            f"voice={settings.voice_preference}, speed={settings.voice_speed}"
        )

        # Récupérer le plan pour la réponse
        plan = current_user.get("plan", "elite")

        return VoiceSettingsResponse(
            voice_preference=updated_data["voice_preference"],
            voice_speed=float(updated_data["voice_speed"]),
            can_use_voice=True,
            plan=plan
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VoiceSettings] PUT error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update voice settings"
        )


@router.get("/voices")
async def get_available_voices() -> Dict[str, Any]:
    """
    Liste des voix disponibles avec descriptions

    Returns:
        Liste des voix OpenAI TTS avec métadonnées
    """
    voices = [
        {
            "id": "alloy",
            "name": "Alloy",
            "description": "Neutre et équilibré",
            "gender": "neutral",
            "preview_url": "/audio/voice-previews/alloy.mp3"
        },
        {
            "id": "echo",
            "name": "Echo",
            "description": "Voix masculine claire",
            "gender": "male",
            "preview_url": "/audio/voice-previews/echo.mp3"
        },
        {
            "id": "fable",
            "name": "Fable",
            "description": "Accent britannique chaleureux",
            "gender": "neutral",
            "preview_url": "/audio/voice-previews/fable.mp3"
        },
        {
            "id": "onyx",
            "name": "Onyx",
            "description": "Voix grave et masculine",
            "gender": "male",
            "preview_url": "/audio/voice-previews/onyx.mp3"
        },
        {
            "id": "nova",
            "name": "Nova",
            "description": "Voix féminine énergique",
            "gender": "female",
            "preview_url": "/audio/voice-previews/nova.mp3"
        },
        {
            "id": "shimmer",
            "name": "Shimmer",
            "description": "Voix féminine douce",
            "gender": "female",
            "preview_url": "/audio/voice-previews/shimmer.mp3"
        }
    ]

    return {
        "voices": voices,
        "default": "alloy",
        "recommended_speed_range": {"min": 0.8, "max": 1.5},
        "speed_range": {"min": 0.25, "max": 4.0}
    }


logger.info("voice_settings.py loaded")
