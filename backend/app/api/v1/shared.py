# app/api/v1/shared.py
"""
Router pour l'accès public aux conversations partagées.
Pas d'authentification requise pour consulter une conversation partagée.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
from datetime import datetime, timezone
import re

logger = logging.getLogger("app.api.v1.shared")
router = APIRouter()


def anonymize_text(text: str) -> str:
    """
    Anonymise les données sensibles dans un texte.
    - Emails
    - Numéros de téléphone
    - Noms d'entreprise potentiels (patterns simples)
    """
    if not text:
        return text

    # Anonymiser les emails
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[email protégé]',
        text
    )

    # Anonymiser les numéros de téléphone (formats variés)
    text = re.sub(
        r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        '[téléphone]',
        text
    )
    text = re.sub(
        r'(\+?\d{1,3}[-.\s]?)?(\d{2}[-.\s]?){5}',
        '[téléphone]',
        text
    )

    return text


def anonymize_message(message: Dict[str, Any], anonymize: bool) -> Dict[str, Any]:
    """
    Anonymise un message si nécessaire.
    """
    if not anonymize:
        return message

    # Copier le message pour ne pas modifier l'original
    anonymized = message.copy()

    # Anonymiser le contenu
    if anonymized.get("content"):
        anonymized["content"] = anonymize_text(anonymized["content"])

    return anonymized


@router.get("/{share_token}")
async def get_shared_conversation(share_token: str) -> Dict[str, Any]:
    """
    Récupère une conversation partagée publiquement (sans authentification).
    Vérifie que le partage existe, n'est pas expiré, et anonymise si nécessaire.
    """
    try:
        logger.info(f"get_shared_conversation: token={share_token[:8]}...")

        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer les informations du partage
                cur.execute(
                    """
                    SELECT
                        cs.id as share_id,
                        cs.conversation_id,
                        cs.share_type,
                        cs.anonymize,
                        cs.expires_at,
                        cs.view_count,
                        cs.created_by,
                        c.language,
                        c.created_at as conversation_created_at
                    FROM conversation_shares cs
                    JOIN conversations c ON cs.conversation_id = c.id
                    WHERE cs.share_token = %s
                    AND c.status != 'deleted'
                    """,
                    (share_token,)
                )

                share = cur.fetchone()

                if not share:
                    raise HTTPException(
                        status_code=404,
                        detail="Partage non trouvé ou conversation supprimée"
                    )

                # Vérifier l'expiration
                if share["expires_at"] and share["expires_at"] < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=410,
                        detail="Ce partage a expiré"
                    )

                conversation_id = share["conversation_id"]
                anonymize = share["anonymize"]

                # Récupérer tous les messages de la conversation
                cur.execute(
                    """
                    SELECT
                        id,
                        role,
                        content,
                        sequence_number,
                        created_at
                    FROM messages
                    WHERE conversation_id = %s
                    ORDER BY sequence_number ASC
                    """,
                    (conversation_id,)
                )

                messages = cur.fetchall()

                # Incrémenter le compteur de vues
                cur.execute(
                    """
                    UPDATE conversation_shares
                    SET view_count = view_count + 1,
                        last_viewed_at = NOW()
                    WHERE id = %s
                    """,
                    (share["share_id"],)
                )

                # Récupérer le nom du créateur (si pas anonymisé)
                shared_by = None
                if not anonymize:
                    cur.execute(
                        """
                        SELECT first_name, last_name, full_name
                        FROM users
                        WHERE user_id = %s
                        """,
                        (share["created_by"],)
                    )
                    creator = cur.fetchone()
                    if creator:
                        shared_by = (
                            creator.get("first_name") or
                            creator.get("full_name", "").split()[0] if creator.get("full_name") else
                            "Un utilisateur"
                        )

        # Anonymiser les messages si nécessaire
        messages_list = [
            anonymize_message(
                {
                    "id": str(msg["id"]),
                    "role": msg["role"],
                    "content": msg["content"],
                    "sequence_number": msg["sequence_number"],
                    "created_at": msg["created_at"].isoformat(),
                },
                anonymize
            )
            for msg in messages
        ]

        logger.info(
            f"Conversation partagée récupérée: "
            f"conversation_id={conversation_id}, messages={len(messages_list)}, "
            f"anonymize={anonymize}, views={share['view_count'] + 1}"
        )

        return {
            "status": "success",
            "conversation": {
                "id": str(conversation_id),
                "language": share["language"],
                "created_at": share["conversation_created_at"].isoformat(),
                "messages": messages_list,
                "message_count": len(messages_list),
            },
            "share_info": {
                "anonymized": anonymize,
                "shared_by": shared_by if not anonymize else "Un utilisateur",
                "view_count": share["view_count"] + 1,  # Inclure la vue actuelle
                "expires_at": share["expires_at"].isoformat() if share["expires_at"] else None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur récupération conversation partagée: {share_token[:8]}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de la conversation: {str(e)}",
        )


@router.get("/{share_token}/health")
async def check_share_health(share_token: str) -> Dict[str, Any]:
    """
    Vérifie rapidement si un partage existe et est valide (sans incrémenter les vues).
    Utile pour le frontend pour vérifier un lien avant de l'afficher.
    """
    try:
        from app.core.database import get_pg_connection
        from psycopg2.extras import RealDictCursor

        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        cs.expires_at,
                        c.status
                    FROM conversation_shares cs
                    JOIN conversations c ON cs.conversation_id = c.id
                    WHERE cs.share_token = %s
                    """,
                    (share_token,)
                )

                share = cur.fetchone()

                if not share:
                    return {
                        "status": "not_found",
                        "valid": False,
                        "message": "Partage non trouvé"
                    }

                if share["status"] == "deleted":
                    return {
                        "status": "deleted",
                        "valid": False,
                        "message": "Conversation supprimée"
                    }

                if share["expires_at"] and share["expires_at"] < datetime.now(timezone.utc):
                    return {
                        "status": "expired",
                        "valid": False,
                        "message": "Partage expiré",
                        "expired_at": share["expires_at"].isoformat()
                    }

                return {
                    "status": "valid",
                    "valid": True,
                    "message": "Partage actif",
                    "expires_at": share["expires_at"].isoformat() if share["expires_at"] else None
                }

    except Exception as e:
        logger.exception(f"Erreur health check partage: {share_token[:8]}")
        return {
            "status": "error",
            "valid": False,
            "message": f"Erreur: {str(e)}"
        }
