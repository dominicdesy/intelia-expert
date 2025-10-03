# app/api/v1/conversations.py
"""
Router pour la gestion des conversations avec nouvelle architecture.
VERSION ADAPTÉE pour table conversations avec colonnes enrichies.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Import authentification pour certains endpoints protégés
from app.api.v1.auth import get_current_user

logger = logging.getLogger("app.api.v1.conversations")
router = APIRouter()


# ===== Modèles Pydantic pour validation =====
class ConversationSaveRequest(BaseModel):
    conversation_id: str
    question: str
    response: str
    user_id: str
    timestamp: Optional[str] = None
    source: Optional[str] = "llm_streaming_agent"
    metadata: Optional[Dict[str, Any]] = {}


# ===== Fonctions utilitaires pour formatage =====
def generate_title_from_question(question: str) -> str:
    """Génère un titre à partir de la première ligne de la question."""
    if not question or not question.strip():
        return "Conversation sans titre"

    # Prendre la première ligne ou les premiers 100 caractères
    first_line = question.strip().split("\n")[0]
    if len(first_line) > 100:
        return first_line[:97] + "..."
    return first_line


def generate_preview_from_question(question: str) -> str:
    """Génère un aperçu à partir de la question complète."""
    if not question or not question.strip():
        return "Aucun aperçu disponible"

    if len(question) > 300:
        return question[:297] + "..."
    return question.strip()


def generate_last_message_preview(response: str) -> str:
    """Génère un aperçu du dernier message (réponse)."""
    if not response or not response.strip():
        return "Aucune réponse"

    if len(response) > 300:
        return response[:297] + "..."
    return response.strip()


# ===== ENDPOINTS PUBLICS =====


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check de santé du service conversations avec nouvelle architecture."""
    try:
        # Test de connexion à la base de données
        with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM conversations")
                total_conversations = cur.fetchone()[0]

        return {
            "status": "healthy",
            "backend": "postgresql",
            "total_conversations": total_conversations,
            "architecture": "nouvelle_structure",
            "table": "conversations",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception("Health check failed")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/test-public")
async def test_public() -> Dict[str, Any]:
    """Test endpoint public pour vérifier le fonctionnement."""
    return {
        "status": "success",
        "message": "Conversations router avec nouvelle architecture!",
        "router": "conversations",
        "architecture": "table_conversations_enrichie",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ===== ENDPOINT SAVE MODIFIÉ =====


@router.post("/save")
async def save_conversation(
    conversation_data: ConversationSaveRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Sauvegarde une conversation dans la nouvelle structure de table.
    """
    try:
        logger.info(
            f"save_conversation: user={current_user.get('email', 'unknown')}, "
            f"conv_id={conversation_data.conversation_id[:8]}..."
        )

        # Vérification sécurité
        requester_id = current_user.get("email", current_user.get("user_id", ""))
        if conversation_data.user_id != requester_id and not current_user.get(
            "is_admin", False
        ):
            logger.warning(
                f"Tentative sauvegarde non autorisée: {requester_id} → {conversation_data.user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez sauvegarder que vos propres conversations",
            )

        # Connexion à la base de données
        with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Vérifier si la conversation existe déjà
                cur.execute(
                    "SELECT id FROM conversations WHERE id = %s OR session_id = %s",
                    [
                        conversation_data.conversation_id,
                        conversation_data.conversation_id,
                    ],
                )
                existing = cur.fetchone()

                if existing:
                    # Mettre à jour la conversation existante
                    cur.execute(
                        """
                        UPDATE conversations SET
                            question = %s,
                            response = %s,
                            title = %s,
                            preview = %s,
                            last_message_preview = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s OR session_id = %s
                        """,
                        [
                            conversation_data.question,
                            conversation_data.response,
                            generate_title_from_question(conversation_data.question),
                            generate_preview_from_question(conversation_data.question),
                            generate_last_message_preview(conversation_data.response),
                            conversation_data.conversation_id,
                            conversation_data.conversation_id,
                        ],
                    )

                    logger.info(
                        f"Conversation mise à jour: {conversation_data.conversation_id}"
                    )

                    return {
                        "status": "updated",
                        "conversation_id": conversation_data.conversation_id,
                        "user_id": conversation_data.user_id,
                        "action": "conversation_updated",
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                else:
                    # Créer une nouvelle conversation
                    cur.execute(
                        """
                        INSERT INTO conversations (
                            id, session_id, user_id, question, response, 
                            title, preview, last_message_preview, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            conversation_data.conversation_id,
                            conversation_data.conversation_id,
                            conversation_data.user_id,
                            conversation_data.question,
                            conversation_data.response,
                            generate_title_from_question(conversation_data.question),
                            generate_preview_from_question(conversation_data.question),
                            generate_last_message_preview(conversation_data.response),
                            conversation_data.timestamp
                            or datetime.utcnow().isoformat(),
                        ],
                    )

                    logger.info(
                        f"Nouvelle conversation créée: {conversation_data.conversation_id}"
                    )

                    return {
                        "status": "created",
                        "conversation_id": conversation_data.conversation_id,
                        "user_id": conversation_data.user_id,
                        "action": "conversation_created",
                        "timestamp": datetime.utcnow().isoformat(),
                    }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Erreur sauvegarde conversation {conversation_data.conversation_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Erreur interne lors de la sauvegarde: {str(e)}"
        )


# ===== ENDPOINT LECTURE MODIFIÉ =====


@router.get("/user/{user_id}")
async def get_user_conversations(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=999),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Récupère les conversations d'un utilisateur depuis la nouvelle structure.
    """
    try:
        logger.info(
            f"get_user_conversations: user_id={user_id}, limit={limit}, "
            f"requester={current_user.get('email', 'unknown')}"
        )

        # Vérification sécurité
        requester_id = current_user.get("email", current_user.get("user_id", ""))
        if user_id != requester_id and not current_user.get("is_admin", False):
            logger.warning(
                f"Tentative d'accès non autorisé: {requester_id} → {user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez accéder qu'à vos propres conversations",
            )

        # Connexion à la base de données
        with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Compter le total
                cur.execute(
                    "SELECT COUNT(*) as total FROM conversations WHERE user_id = %s AND status = 'active'",
                    [user_id],
                )
                total_result = cur.fetchone()
                total_count = total_result["total"] if total_result else 0

                # Récupérer les conversations avec pagination
                cur.execute(
                    """
                    SELECT 
                        id,
                        session_id,
                        title,
                        preview,
                        message_count,
                        created_at,
                        updated_at,
                        language,
                        last_message_preview,
                        status,
                        feedback,
                        feedback_comment
                    FROM conversations 
                    WHERE user_id = %s AND status = 'active'
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    [user_id, limit, offset],
                )

                conversations_raw = cur.fetchall()

                # Formater les conversations pour le frontend
                conversations = []
                for row in conversations_raw:
                    conversation = {
                        "id": row["id"],
                        "title": row["title"] or "Conversation",
                        "preview": row["preview"] or "Aucun aperçu",
                        "message_count": row["message_count"] or 2,
                        "created_at": (
                            row["created_at"].isoformat() if row["created_at"] else None
                        ),
                        "updated_at": (
                            row["updated_at"].isoformat() if row["updated_at"] else None
                        ),
                        "language": row["language"] or "fr",
                        "last_message_preview": row["last_message_preview"] or "",
                        "status": row["status"] or "active",
                        "feedback": row["feedback"],
                        "feedback_comment": row["feedback_comment"],
                    }
                    conversations.append(conversation)

                logger.info(f"Conversations trouvées pour {user_id}: {total_count}")

                return {
                    "status": "success",
                    "user_id": user_id,
                    "conversations": conversations,
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "source": "postgresql_nouvelle_architecture",
                    "timestamp": datetime.utcnow().isoformat(),
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur récupération conversations pour {user_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}",
        )


# ===== ENDPOINT SUPPRESSION =====


@router.delete("/user/{user_id}")
async def delete_all_user_conversations(
    user_id: str, current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Supprime toutes les conversations d'un utilisateur.
    """
    try:
        logger.info(f"delete_all_user_conversations: user_id={user_id}")

        # Vérification sécurité
        requester_id = current_user.get("email", current_user.get("user_id", ""))
        if user_id != requester_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez supprimer que vos propres conversations",
            )

        with psycopg2.connect(os.getenv("DATABASE_URL")) as conn:
            with conn.cursor() as cur:

                # Compter avant suppression
                cur.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = %s", [user_id]
                )
                total_found = cur.fetchone()[0]

                # Supprimer (marquer comme supprimé)
                cur.execute(
                    "UPDATE conversations SET status = 'deleted' WHERE user_id = %s",
                    [user_id],
                )
                deleted_count = cur.rowcount

                return {
                    "status": "success",
                    "user_id": user_id,
                    "deleted_count": deleted_count,
                    "total_found": total_found,
                    "message": f"{deleted_count} conversations supprimées avec succès",
                    "timestamp": datetime.utcnow().isoformat(),
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur suppression pour {user_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression: {str(e)}",
        )
