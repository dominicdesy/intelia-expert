# app/api/v1/satisfaction.py
"""
Router pour les sondages de satisfaction globale
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger("app.api.v1.satisfaction")
router = APIRouter()


# ============================================================================
# MODELS
# ============================================================================

class SatisfactionSurveyCreate(BaseModel):
    """Modèle pour créer un sondage de satisfaction"""
    conversation_id: str = Field(..., description="ID de la conversation")
    user_id: str = Field(..., description="ID de l'utilisateur")
    rating: str = Field(..., description="Note: satisfied, neutral, unsatisfied")
    comment: Optional[str] = Field(None, description="Commentaire optionnel")
    message_count: int = Field(..., description="Nombre de messages au moment du sondage")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                "user_id": "user_123",
                "rating": "satisfied",
                "comment": "Super rapide et précis !",
                "message_count": 27
            }
        }


class SatisfactionSurveyResponse(BaseModel):
    """Modèle de réponse après création du sondage"""
    status: str
    survey_id: str
    message: str
    created_at: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/submit", response_model=SatisfactionSurveyResponse)
async def submit_satisfaction_survey(survey: SatisfactionSurveyCreate):
    """
    Enregistre un sondage de satisfaction globale

    Args:
        survey: Données du sondage

    Returns:
        Confirmation d'enregistrement
    """
    try:
        logger.info(
            f"submit_satisfaction_survey: conversation_id={survey.conversation_id}, "
            f"rating={survey.rating}, message_count={survey.message_count}"
        )

        # Validation du rating
        if survey.rating not in ['satisfied', 'neutral', 'unsatisfied']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rating: {survey.rating}. Must be: satisfied, neutral, or unsatisfied"
            )

        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Vérifier que la conversation existe
                cur.execute(
                    "SELECT id, user_id FROM conversations WHERE id = %s",
                    (survey.conversation_id,)
                )
                conversation = cur.fetchone()

                if not conversation:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Conversation {survey.conversation_id} not found"
                    )

                # Vérifier que l'utilisateur est le propriétaire de la conversation
                if conversation['user_id'] != survey.user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="User does not own this conversation"
                    )

                # Insérer le sondage
                cur.execute(
                    """
                    INSERT INTO conversation_satisfaction_surveys (
                        conversation_id,
                        user_id,
                        rating,
                        comment,
                        message_count_at_survey
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (
                        survey.conversation_id,
                        survey.user_id,
                        survey.rating,
                        survey.comment,
                        survey.message_count
                    )
                )

                result = cur.fetchone()
                survey_id = str(result['id'])
                created_at = result['created_at'].isoformat()

        logger.info(
            f"✅ Satisfaction survey saved: survey_id={survey_id}, "
            f"rating={survey.rating}, message_count={survey.message_count}"
        )

        return SatisfactionSurveyResponse(
            status="success",
            survey_id=survey_id,
            message="Thank you for your feedback!",
            created_at=created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error saving satisfaction survey: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error saving satisfaction survey: {str(e)}"
        )


@router.get("/stats")
async def get_satisfaction_stats(days: int = 30):
    """
    Récupère les statistiques de satisfaction

    Args:
        days: Nombre de jours à analyser (défaut: 30)

    Returns:
        Statistiques de satisfaction par jour
    """
    try:
        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Utiliser la fonction SQL helper
                cur.execute(
                    "SELECT * FROM get_satisfaction_stats(%s)",
                    (days,)
                )
                stats = cur.fetchall()

        return {
            "status": "success",
            "days_analyzed": days,
            "stats": [dict(row) for row in stats]
        }

    except Exception as e:
        logger.exception(f"Error fetching satisfaction stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )


@router.get("/conversation/{conversation_id}")
async def get_conversation_surveys(conversation_id: str):
    """
    Récupère tous les sondages d'une conversation

    Args:
        conversation_id: ID de la conversation

    Returns:
        Liste des sondages de cette conversation
    """
    try:
        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        rating,
                        comment,
                        message_count_at_survey,
                        created_at
                    FROM conversation_satisfaction_surveys
                    WHERE conversation_id = %s
                    ORDER BY created_at DESC
                    """,
                    (conversation_id,)
                )
                surveys = cur.fetchall()

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "surveys": [
                {
                    "id": str(survey['id']),
                    "rating": survey['rating'],
                    "comment": survey['comment'],
                    "message_count": survey['message_count_at_survey'],
                    "created_at": survey['created_at'].isoformat()
                }
                for survey in surveys
            ]
        }

    except Exception as e:
        logger.exception(f"Error fetching conversation surveys: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching surveys: {str(e)}"
        )
