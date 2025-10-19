"""
Service de gestion des conversations et messages

Architecture: conversations + messages séparés
Includes Chain-of-Thought parsing and storage for assistant messages
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from psycopg2.extras import RealDictCursor

from app.core.database import get_pg_connection
from app.utils.cot_parser import parse_cot_response

logger = logging.getLogger(__name__)


class ConversationService:
    """Service pour gérer les conversations et messages"""

    @staticmethod
    def create_conversation(
        session_id: str,
        user_id: str,
        user_message: str,
        assistant_response: str,
        language: str = "fr",
        response_source: str = "rag",
        response_confidence: float = 0.85,
        processing_time_ms: int = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle conversation avec le premier échange Q&R

        Returns:
            {
                "conversation_id": UUID,
                "session_id": UUID,
                "message_count": 2
            }
        """
        try:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Utiliser la fonction SQL helper
                    cur.execute(
                        """
                        SELECT create_conversation_with_messages(
                            %s::uuid, %s, %s, %s, %s, %s, %s, %s
                        ) as conversation_id
                        """,
                        (
                            session_id,
                            user_id,
                            user_message,
                            assistant_response,
                            language,
                            response_source,
                            response_confidence,
                            processing_time_ms
                        )
                    )

                    result = cur.fetchone()
                    conversation_id = result["conversation_id"]

                    logger.info(
                        f"Conversation créée: {conversation_id} "
                        f"(session: {session_id}, user: {user_id})"
                    )

                    return {
                        "conversation_id": str(conversation_id),
                        "session_id": session_id,
                        "message_count": 2
                    }

        except Exception as e:
            logger.error(f"Erreur création conversation: {e}")
            raise

    @staticmethod
    def add_message(
        conversation_id: str,
        role: str,
        content: str,
        response_source: str = None,
        response_confidence: float = None,
        processing_time_ms: int = None
    ) -> Dict[str, Any]:
        """
        Ajoute un message à une conversation existante

        For assistant messages: Parses Chain-of-Thought structure and saves
        thinking/analysis to database for analytics while displaying only
        the final answer to users.

        Args:
            conversation_id: UUID de la conversation
            role: 'user' ou 'assistant'
            content: Contenu du message (avec ou sans structure CoT)

        Returns:
            {
                "message_id": UUID,
                "sequence_number": int,
                "has_cot_structure": bool (for assistant messages)
            }
        """
        try:
            # Parse CoT structure for assistant messages
            cot_thinking = None
            cot_analysis = None
            has_cot_structure = False
            final_content = content

            if role == 'assistant':
                parsed = parse_cot_response(content)
                cot_thinking = parsed['thinking']
                cot_analysis = parsed['analysis']
                has_cot_structure = parsed['has_structure']
                final_content = parsed['answer']  # Only save answer in content field

                if has_cot_structure:
                    logger.info(
                        f"🧠 CoT detected in assistant message - "
                        f"thinking: {len(cot_thinking or '')} chars, "
                        f"analysis: {len(cot_analysis or '')} chars"
                    )

            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Utiliser la fonction SQL helper avec paramètres CoT
                    cur.execute(
                        """
                        SELECT add_message_to_conversation(
                            %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s
                        ) as message_id
                        """,
                        (
                            conversation_id,
                            role,
                            final_content,  # Only answer for assistant, full content for user
                            response_source,
                            response_confidence,
                            processing_time_ms,
                            cot_thinking,
                            cot_analysis,
                            has_cot_structure
                        )
                    )

                    result = cur.fetchone()
                    message_id = result["message_id"]

                    # Récupérer le sequence_number
                    cur.execute(
                        """
                        SELECT sequence_number
                        FROM messages
                        WHERE id = %s
                        """,
                        (message_id,)
                    )

                    sequence = cur.fetchone()["sequence_number"]

                    logger.info(
                        f"Message ajouté: {message_id} "
                        f"(conversation: {conversation_id}, sequence: {sequence}, CoT: {has_cot_structure})"
                    )

                    return {
                        "message_id": str(message_id),
                        "sequence_number": sequence,
                        "has_cot_structure": has_cot_structure
                    }

        except Exception as e:
            logger.error(f"Erreur ajout message: {e}")
            raise

    @staticmethod
    def get_conversation_messages(conversation_id: str) -> List[Dict[str, Any]]:
        """
        Récupère tous les messages d'une conversation

        Returns:
            Liste de messages triés par sequence_number
        """
        try:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM get_conversation_messages(%s::uuid)
                        """,
                        (conversation_id,)
                    )

                    messages = []
                    for row in cur.fetchall():
                        messages.append({
                            "id": str(row["id"]),
                            "role": row["role"],
                            "content": row["content"],
                            "response_source": row["response_source"],
                            "response_confidence": row["response_confidence"],
                            "processing_time_ms": row["processing_time_ms"],
                            "sequence_number": row["sequence_number"],
                            "feedback": row["feedback"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None
                        })

                    logger.info(
                        f"Messages récupérés: {len(messages)} "
                        f"(conversation: {conversation_id})"
                    )

                    return messages

        except Exception as e:
            logger.error(f"Erreur récupération messages: {e}")
            raise

    @staticmethod
    def get_user_conversations(
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Récupère les conversations d'un utilisateur

        Returns:
            {
                "conversations": [...],
                "total": int,
                "limit": int,
                "offset": int
            }
        """
        try:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Compter le total
                    cur.execute(
                        """
                        SELECT COUNT(*) as total
                        FROM conversations
                        WHERE user_id = %s AND status = %s
                        """,
                        (user_id, status)
                    )

                    total = cur.fetchone()["total"]

                    # Récupérer les conversations
                    cur.execute(
                        """
                        SELECT
                            id::text as id,
                            session_id::text as session_id,
                            user_id,
                            title,
                            language,
                            message_count,
                            first_message_preview,
                            last_message_preview,
                            status,
                            created_at,
                            updated_at,
                            last_activity_at
                        FROM conversations
                        WHERE user_id = %s AND status = %s
                        ORDER BY last_activity_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (user_id, status, limit, offset)
                    )

                    conversations = []
                    for row in cur.fetchall():
                        conversations.append({
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "user_id": row["user_id"],
                            "title": row["title"],
                            "language": row["language"],
                            "message_count": row["message_count"],
                            "first_message_preview": row["first_message_preview"],
                            "preview": row["first_message_preview"],  # Alias pour compatibilité frontend
                            "last_message_preview": row["last_message_preview"],
                            "status": row["status"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                            "last_activity_at": row["last_activity_at"].isoformat() if row["last_activity_at"] else None
                        })

                    logger.info(
                        f"Conversations récupérées: {len(conversations)}/{total} "
                        f"(user: {user_id})"
                    )

                    return {
                        "conversations": conversations,
                        "total": total,
                        "limit": limit,
                        "offset": offset
                    }

        except Exception as e:
            logger.error(f"Erreur récupération conversations: {e}")
            raise

    @staticmethod
    def get_conversation_by_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une conversation par session_id

        Returns:
            Conversation ou None
        """
        try:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            id::text as id,
                            session_id::text as session_id,
                            user_id,
                            title,
                            language,
                            message_count,
                            status,
                            created_at,
                            updated_at
                        FROM conversations
                        WHERE session_id = %s
                        """,
                        (session_id,)
                    )

                    row = cur.fetchone()

                    if row:
                        return {
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "user_id": row["user_id"],
                            "title": row["title"],
                            "language": row["language"],
                            "message_count": row["message_count"],
                            "status": row["status"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                        }

                    return None

        except Exception as e:
            logger.error(f"Erreur récupération conversation: {e}")
            raise

    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        """
        Supprime (archive) une conversation

        Returns:
            True si succès
        """
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE conversations
                        SET status = 'deleted', updated_at = NOW()
                        WHERE id = %s
                        """,
                        (conversation_id,)
                    )

                    logger.info(f"Conversation supprimée: {conversation_id}")
                    return True

        except Exception as e:
            logger.error(f"Erreur suppression conversation: {e}")
            raise


# Instance singleton
conversation_service = ConversationService()
