# app/api/v1/conversations.py
"""
Router pour la gestion des conversations avec nouvelle architecture.
Architecture: conversations (metadata) + messages (individual messages)
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging
from datetime import datetime
from uuid import uuid4

# Import conversation service
from app.services.conversation_service import conversation_service

# Import authentification
from app.api.v1.auth import get_current_user

logger = logging.getLogger("app.api.v1.conversations")
router = APIRouter()


# ===== Modèles Pydantic pour validation =====
class ConversationSaveRequest(BaseModel):
    """Requête pour sauvegarder une nouvelle conversation"""
    conversation_id: str  # session_id
    question: str
    response: str
    user_id: str
    timestamp: Optional[str] = None
    source: Optional[str] = "rag"
    confidence: Optional[float] = 0.85
    processing_time_ms: Optional[int] = None
    language: Optional[str] = "fr"
    metadata: Optional[Dict[str, Any]] = {}


class ShareConversationRequest(BaseModel):
    """Requête pour partager une conversation"""
    share_type: str = "public"  # 'public' or 'private'
    anonymize: bool = True
    expires_in_days: Optional[int] = None  # None = permanent


class MessageAddRequest(BaseModel):
    """Requête pour ajouter un message à une conversation existante"""
    conversation_id: str
    role: str  # 'user' or 'assistant'
    content: str
    response_source: Optional[str] = None
    response_confidence: Optional[float] = None
    processing_time_ms: Optional[int] = None


class FeedbackRequest(BaseModel):
    """Requête pour ajouter un feedback à un message"""
    feedback: int  # 1 (positive), -1 (negative), 0 (neutral)
    feedback_comment: Optional[str] = None


# ===== ENDPOINTS PUBLICS =====

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check de santé du service conversations."""
    try:
        from app.core.database import check_databases_health
        health = check_databases_health()

        return {
            "status": "healthy" if health["postgresql"]["status"] == "healthy" else "unhealthy",
            "backend": "postgresql",
            "architecture": "conversations + messages",
            "databases": health,
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
        "message": "Conversations router with new architecture!",
        "router": "conversations",
        "architecture": "conversations + messages",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ===== ENDPOINT SAVE - NOUVELLE ARCHITECTURE =====

@router.post("/save")
async def save_conversation(
    conversation_data: ConversationSaveRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Sauvegarde une conversation dans la nouvelle architecture.
    Crée une conversation avec le premier échange Q&R ou ajoute des messages.
    """
    try:
        logger.info(
            f"save_conversation: user={current_user.get('email', 'unknown')}, "
            f"session_id={conversation_data.conversation_id[:8]}..."
        )

        # Vérification sécurité - Comparer les UUID
        requester_id = current_user.get("user_id", "")
        if conversation_data.user_id != requester_id and not current_user.get("is_admin", False):
            logger.warning(
                f"Tentative sauvegarde non autorisée: {requester_id} ({current_user.get('email')}) → {conversation_data.user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez sauvegarder que vos propres conversations",
            )

        # Vérifier si la conversation existe déjà par session_id
        existing_conv = conversation_service.get_conversation_by_session(
            conversation_data.conversation_id
        )

        if existing_conv:
            # Conversation existante - ajouter les nouveaux messages
            logger.info(f"Conversation existante trouvée: {existing_conv['id']}")

            # Ajouter le message user
            user_msg = conversation_service.add_message(
                conversation_id=existing_conv["id"],
                role="user",
                content=conversation_data.question
            )

            # Ajouter la réponse assistant
            assistant_msg = conversation_service.add_message(
                conversation_id=existing_conv["id"],
                role="assistant",
                content=conversation_data.response,
                response_source=conversation_data.source,
                response_confidence=conversation_data.confidence,
                processing_time_ms=conversation_data.processing_time_ms
            )

            logger.info(
                f"Messages ajoutés: user={user_msg['sequence_number']}, "
                f"assistant={assistant_msg['sequence_number']}"
            )

            return {
                "status": "updated",
                "conversation_id": existing_conv["id"],
                "session_id": conversation_data.conversation_id,
                "user_id": conversation_data.user_id,
                "message_count": existing_conv["message_count"] + 2,
                "action": "messages_added",
                "timestamp": datetime.utcnow().isoformat(),
            }

        else:
            # Nouvelle conversation - créer avec le premier échange
            logger.info("Création d'une nouvelle conversation")

            result = conversation_service.create_conversation(
                session_id=conversation_data.conversation_id,
                user_id=conversation_data.user_id,
                user_message=conversation_data.question,
                assistant_response=conversation_data.response,
                language=conversation_data.language or "fr",
                response_source=conversation_data.source,
                response_confidence=conversation_data.confidence,
                processing_time_ms=conversation_data.processing_time_ms
            )

            logger.info(f"Nouvelle conversation créée: {result['conversation_id']}")

            return {
                "status": "created",
                "conversation_id": result["conversation_id"],
                "session_id": result["session_id"],
                "user_id": conversation_data.user_id,
                "message_count": result["message_count"],
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
            status_code=500,
            detail=f"Erreur interne lors de la sauvegarde: {str(e)}"
        )


# ===== ENDPOINT LECTURE - NOUVELLE ARCHITECTURE =====

@router.get("/user/{user_id}")
async def get_user_conversations_endpoint(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=999),
    offset: int = Query(default=0, ge=0),
    status: str = Query(default="active"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Récupère les conversations d'un utilisateur depuis la nouvelle architecture.
    """
    try:
        logger.info(
            f"get_user_conversations: user_id={user_id}, limit={limit}, "
            f"requester={current_user.get('email', 'unknown')}"
        )

        # Vérification sécurité - comparer les user_id (UUID)
        requester_id = current_user.get("user_id", "")
        is_admin = current_user.get("user_type") == "admin" or current_user.get("is_admin", False)

        if user_id != requester_id and not is_admin:
            logger.warning(
                f"Tentative d'accès non autorisé: {requester_id} ({current_user.get('email')}) → {user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez accéder qu'à vos propres conversations",
            )

        # Récupérer les conversations via le service
        result = conversation_service.get_user_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status=status
        )

        logger.info(f"Conversations trouvées pour {user_id}: {result['total']}")

        return {
            "status": "success",
            "user_id": user_id,
            "conversations": result["conversations"],
            "total_count": result["total"],
            "limit": result["limit"],
            "offset": result["offset"],
            "source": "postgresql_conversations_messages",
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


# ===== ENDPOINT RÉCUPÉRATION MESSAGES D'UNE CONVERSATION =====

@router.get("/{conversation_id}/messages")
async def get_conversation_messages_endpoint(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Récupère tous les messages d'une conversation.
    """
    try:
        logger.info(
            f"get_conversation_messages: conversation_id={conversation_id}, "
            f"requester={current_user.get('email', 'unknown')}"
        )

        # Récupérer les messages
        messages = conversation_service.get_conversation_messages(conversation_id)

        if not messages:
            raise HTTPException(
                status_code=404,
                detail="Conversation non trouvée"
            )

        logger.info(f"Messages récupérés: {len(messages)}")

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "messages": messages,
            "message_count": len(messages),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur récupération messages pour {conversation_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}",
        )


# ===== ENDPOINT AJOUT MESSAGE =====

@router.post("/{conversation_id}/messages")
async def add_message_endpoint(
    conversation_id: str,
    message_data: MessageAddRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Ajoute un message à une conversation existante.
    """
    try:
        logger.info(
            f"add_message: conversation_id={conversation_id}, "
            f"role={message_data.role}, requester={current_user.get('email', 'unknown')}"
        )

        # Ajouter le message
        result = conversation_service.add_message(
            conversation_id=conversation_id,
            role=message_data.role,
            content=message_data.content,
            response_source=message_data.response_source,
            response_confidence=message_data.response_confidence,
            processing_time_ms=message_data.processing_time_ms
        )

        logger.info(f"Message ajouté: {result['message_id']}, sequence: {result['sequence_number']}")

        return {
            "status": "success",
            "message_id": result["message_id"],
            "sequence_number": result["sequence_number"],
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur ajout message pour {conversation_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'ajout: {str(e)}",
        )


# ===== ENDPOINT FEEDBACK =====

@router.patch("/{conversation_id}/feedback")
async def add_conversation_feedback(
    conversation_id: str,
    feedback_data: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Ajoute un feedback à la dernière réponse assistant d'une conversation.
    Compatible avec l'ancien endpoint frontend qui envoie le feedback par conversation_id.
    """
    try:
        logger.info(
            f"add_feedback: conversation_id={conversation_id}, "
            f"feedback={feedback_data.feedback}"
        )

        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Trouver le dernier message assistant de cette conversation
                cur.execute(
                    """
                    SELECT id
                    FROM messages
                    WHERE conversation_id = %s AND role = 'assistant'
                    ORDER BY sequence_number DESC
                    LIMIT 1
                    """,
                    (conversation_id,)
                )

                result = cur.fetchone()

                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Aucun message assistant trouvé pour cette conversation"
                    )

                message_id = result["id"]

                # Mettre à jour le feedback du message
                # Map 1 -> 'positive', -1 -> 'negative', 0 -> 'neutral'
                if feedback_data.feedback == 1:
                    feedback_value = "positive"
                elif feedback_data.feedback == -1:
                    feedback_value = "negative"
                else:
                    feedback_value = "neutral"

                cur.execute(
                    """
                    UPDATE messages
                    SET feedback = %s, feedback_comment = %s
                    WHERE id = %s
                    """,
                    (
                        feedback_value,
                        feedback_data.feedback_comment,
                        message_id
                    )
                )

        logger.info(f"Feedback ajouté au dernier message de conversation: {conversation_id}")

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "message_id": str(message_id),
            "feedback": feedback_value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur ajout feedback pour {conversation_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'ajout du feedback: {str(e)}",
        )


@router.patch("/{conversation_id}/messages/{message_id}/feedback")
async def add_message_feedback(
    conversation_id: str,
    message_id: str,
    feedback_data: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Ajoute un feedback à un message spécifique.
    """
    try:
        logger.info(
            f"add_feedback: message_id={message_id}, "
            f"feedback={feedback_data.feedback}"
        )

        from app.core.database import get_pg_connection

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE messages
                    SET feedback = %s, feedback_comment = %s
                    WHERE id = %s AND conversation_id = %s
                    """,
                    (
                        feedback_data.feedback,
                        feedback_data.feedback_comment,
                        message_id,
                        conversation_id
                    )
                )

                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=404,
                        detail="Message non trouvé"
                    )

        logger.info(f"Feedback ajouté au message: {message_id}")

        return {
            "status": "success",
            "message_id": message_id,
            "feedback": feedback_data.feedback,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur ajout feedback pour {message_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'ajout du feedback: {str(e)}",
        )


# ===== ENDPOINT SUPPRESSION =====

@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Supprime (archive) une conversation spécifique.
    """
    try:
        logger.info(f"delete_conversation: conversation_id={conversation_id}")

        # Supprimer via le service
        success = conversation_service.delete_conversation(conversation_id)

        if success:
            return {
                "status": "success",
                "conversation_id": conversation_id,
                "message": "Conversation supprimée avec succès",
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Conversation non trouvée"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur suppression pour {conversation_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression: {str(e)}",
        )


# ===== ENDPOINTS DE PARTAGE =====

@router.post("/{conversation_id}/share")
async def share_conversation(
    conversation_id: str,
    share_request: ShareConversationRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Crée un lien de partage pour une conversation.
    Seul le propriétaire de la conversation peut la partager.
    """
    try:
        logger.info(
            f"share_conversation: conversation_id={conversation_id}, "
            f"user={current_user.get('email', 'unknown')}"
        )

        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor
        import secrets

        requester_id = current_user.get("user_id", "")

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Vérifier que la conversation existe et appartient à l'utilisateur
                cur.execute(
                    """
                    SELECT user_id, status
                    FROM conversations
                    WHERE id = %s
                    """,
                    (conversation_id,)
                )

                conversation = cur.fetchone()

                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversation non trouvée")

                if conversation["user_id"] != requester_id and not current_user.get("is_admin", False):
                    raise HTTPException(
                        status_code=403,
                        detail="Vous ne pouvez partager que vos propres conversations"
                    )

                if conversation["status"] == "deleted":
                    raise HTTPException(
                        status_code=400,
                        detail="Impossible de partager une conversation supprimée"
                    )

                # Générer un token de partage cryptographique
                share_token = secrets.token_urlsafe(48)  # 64 caractères

                # Calculer la date d'expiration
                expires_at = None
                if share_request.expires_in_days:
                    from datetime import timedelta
                    expires_at = datetime.utcnow() + timedelta(days=share_request.expires_in_days)

                # Créer le partage
                cur.execute(
                    """
                    INSERT INTO conversation_shares
                    (conversation_id, share_token, created_by, share_type, anonymize, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, share_token, expires_at, created_at
                    """,
                    (
                        conversation_id,
                        share_token,
                        requester_id,
                        share_request.share_type,
                        share_request.anonymize,
                        expires_at
                    )
                )

                share = cur.fetchone()

        logger.info(f"Partage créé: share_id={share['id']}, token={share_token[:8]}...")

        # Construire l'URL de partage
        share_url = f"https://expert.intelia.com/shared/{share_token}"

        return {
            "status": "success",
            "share_id": str(share["id"]),
            "share_url": share_url,
            "share_token": share_token,
            "anonymize": share_request.anonymize,
            "expires_at": share["expires_at"].isoformat() if share["expires_at"] else None,
            "created_at": share["created_at"].isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur création partage pour {conversation_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création du partage: {str(e)}",
        )


@router.get("/{conversation_id}/shares")
async def get_conversation_shares(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Liste tous les partages actifs d'une conversation.
    """
    try:
        logger.info(f"get_conversation_shares: conversation_id={conversation_id}")

        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        requester_id = current_user.get("user_id", "")

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Vérifier la propriété
                cur.execute(
                    "SELECT user_id FROM conversations WHERE id = %s",
                    (conversation_id,)
                )
                conversation = cur.fetchone()

                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversation non trouvée")

                if conversation["user_id"] != requester_id and not current_user.get("is_admin", False):
                    raise HTTPException(status_code=403, detail="Accès non autorisé")

                # Récupérer les partages actifs
                cur.execute(
                    """
                    SELECT
                        id, share_token, share_type, anonymize,
                        expires_at, view_count, last_viewed_at, created_at
                    FROM conversation_shares
                    WHERE conversation_id = %s
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC
                    """,
                    (conversation_id,)
                )

                shares = cur.fetchall()

        shares_list = [
            {
                "id": str(share["id"]),
                "share_url": f"https://expert.intelia.com/shared/{share['share_token']}",
                "share_type": share["share_type"],
                "anonymize": share["anonymize"],
                "expires_at": share["expires_at"].isoformat() if share["expires_at"] else None,
                "view_count": share["view_count"],
                "last_viewed_at": share["last_viewed_at"].isoformat() if share["last_viewed_at"] else None,
                "created_at": share["created_at"].isoformat(),
            }
            for share in shares
        ]

        logger.info(f"Partages trouvés: {len(shares_list)}")

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "shares": shares_list,
            "count": len(shares_list),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur récupération partages pour {conversation_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(e)}",
        )


@router.delete("/shares/{share_id}")
async def revoke_share(
    share_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Révoque un partage (le supprime).
    """
    try:
        logger.info(f"revoke_share: share_id={share_id}")

        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        requester_id = current_user.get("user_id", "")

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Vérifier que le partage existe et appartient à l'utilisateur
                cur.execute(
                    """
                    SELECT cs.id, cs.created_by, c.user_id as conversation_owner
                    FROM conversation_shares cs
                    JOIN conversations c ON cs.conversation_id = c.id
                    WHERE cs.id = %s
                    """,
                    (share_id,)
                )

                share = cur.fetchone()

                if not share:
                    raise HTTPException(status_code=404, detail="Partage non trouvé")

                # Vérifier que l'utilisateur est soit le créateur du partage, soit le propriétaire de la conversation
                if (share["created_by"] != requester_id and
                    share["conversation_owner"] != requester_id and
                    not current_user.get("is_admin", False)):
                    raise HTTPException(status_code=403, detail="Accès non autorisé")

                # Supprimer le partage
                cur.execute("DELETE FROM conversation_shares WHERE id = %s", (share_id,))

        logger.info(f"Partage révoqué: {share_id}")

        return {
            "status": "success",
            "share_id": share_id,
            "message": "Partage révoqué avec succès",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur révocation partage {share_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la révocation: {str(e)}",
        )


# ===== ENDPOINT SUPPRESSION =====

@router.delete("/user/{user_id}")
async def delete_all_user_conversations(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Supprime toutes les conversations d'un utilisateur.
    """
    try:
        logger.info(f"delete_all_user_conversations: user_id={user_id}")

        # Vérification sécurité - Comparer les UUID
        requester_id = current_user.get("user_id", "")
        if user_id != requester_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez supprimer que vos propres conversations",
            )

        from app.core.database import get_pg_connection

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                # Compter avant suppression
                cur.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = %s AND status != 'deleted'",
                    (user_id,)
                )
                total_found = cur.fetchone()[0]

                # Supprimer (marquer comme supprimé)
                cur.execute(
                    "UPDATE conversations SET status = 'deleted', updated_at = NOW() WHERE user_id = %s AND status != 'deleted'",
                    (user_id,)
                )
                deleted_count = cur.rowcount

        logger.info(f"Toutes les conversations supprimées pour user: {user_id}, count: {deleted_count}")

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
