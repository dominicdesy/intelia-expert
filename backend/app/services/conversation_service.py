"""
Service de gestion des conversations et messages
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Service de gestion des conversations et messages

Architecture: conversations + messages séparés
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from psycopg2.extras import RealDictCursor

from app.core.database import get_pg_connection

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
        processing_time_ms: int = None,
        user_media_url: str = None,
        user_media_type: str = None
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle conversation avec le premier échange Q&R

        Args:
            user_media_url: URL du média attaché au message utilisateur (optionnel)
            user_media_type: Type de média: 'audio', 'image', 'video', 'document' (optionnel)

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
                    # Create conversation with user message first
                    cur.execute(
                        """
                        INSERT INTO conversations (session_id, user_id, language)
                        VALUES (%s::uuid, %s, %s)
                        RETURNING id
                        """,
                        (session_id, user_id, language)
                    )

                    conversation_id = cur.fetchone()["id"]

                    # Add user message (sequence 1)
                    cur.execute(
                        """
                        INSERT INTO messages (
                            conversation_id, role, content, sequence_number,
                            media_url, media_type
                        )
                        VALUES (%s, 'user', %s, 1, %s, %s)
                        """,
                        (conversation_id, user_message, user_media_url, user_media_type)
                    )

                    # Add assistant message (sequence 2)
                    cur.execute(
                        """
                        INSERT INTO messages (
                            conversation_id, role, content, sequence_number,
                            response_source, response_confidence, processing_time_ms
                        ) VALUES (
                            %s, 'assistant', %s, 2,
                            %s, %s, %s
                        )
                        """,
                        (
                            conversation_id,
                            assistant_response,
                            response_source,
                            response_confidence,
                            processing_time_ms
                        )
                    )

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
        processing_time_ms: int = None,
        media_url: str = None,
        media_type: str = None
    ) -> Dict[str, Any]:
        """
        Ajoute un message à une conversation existante

        Args:
            conversation_id: UUID de la conversation
            role: 'user' ou 'assistant'
            content: Contenu du message
            media_url: URL du média attaché (optionnel)
            media_type: Type de média: 'audio', 'image', 'video', 'document' (optionnel)

        Returns:
            {
                "message_id": UUID,
                "sequence_number": int
            }
        """
        try:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Insert message directly
                    cur.execute(
                        """
                        INSERT INTO messages (
                            conversation_id, role, content,
                            response_source, response_confidence, processing_time_ms,
                            media_url, media_type,
                            sequence_number
                        )
                        VALUES (
                            %s::uuid, %s, %s, %s, %s, %s, %s, %s,
                            (SELECT COALESCE(MAX(sequence_number), 0) + 1
                             FROM messages
                             WHERE conversation_id = %s::uuid)
                        )
                        RETURNING id, sequence_number
                        """,
                        (
                            conversation_id,
                            role,
                            content,
                            response_source,
                            response_confidence,
                            processing_time_ms,
                            media_url,
                            media_type,
                            conversation_id
                        )
                    )

                    result = cur.fetchone()
                    message_id = result["id"]
                    sequence = result["sequence_number"]

                    logger.info(
                        f"Message ajouté: {message_id} "
                        f"(conversation: {conversation_id}, sequence: {sequence})"
                    )

                    return {
                        "message_id": str(message_id),
                        "sequence_number": sequence
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
        status: str = "active",
        days_back: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Récupère les conversations d'un utilisateur

        Args:
            days_back: Si spécifié, ne retourne que les conversations des X derniers jours (pour plan Essentiel)

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
                    # Construire la clause WHERE avec filtre de date si nécessaire
                    where_clause = "WHERE user_id = %s AND status = %s"
                    params = [user_id, status]

                    if days_back is not None:
                        where_clause += " AND created_at >= NOW() - INTERVAL '%s days'"
                        params.append(days_back)

                    # Compter le total
                    cur.execute(
                        f"""
                        SELECT COUNT(*) as total
                        FROM conversations
                        {where_clause}
                        """,
                        tuple(params)
                    )

                    total = cur.fetchone()["total"]

                    # Récupérer les conversations
                    params.extend([limit, offset])
                    cur.execute(
                        f"""
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
                        {where_clause}
                        ORDER BY last_activity_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        tuple(params)
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
    def search_conversations(
        user_id: str,
        search_query: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Recherche des conversations par contenu (questions et réponses)

        Utilise PostgreSQL full-text search pour chercher dans:
        - Le titre de la conversation
        - Le contenu des messages (questions et réponses)

        Args:
            user_id: ID de l'utilisateur
            search_query: Terme de recherche
            limit: Nombre maximum de résultats
            offset: Offset pour pagination

        Returns:
            {
                "conversations": [...],
                "total": int,
                "query": str,
                "limit": int,
                "offset": int
            }
        """
        try:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Nettoyer et préparer le terme de recherche
                    # Remplacer les espaces par & pour recherche AND
                    search_term = ' & '.join(search_query.strip().split())

                    # Recherche full-text dans les conversations et messages
                    cur.execute(
                        """
                        WITH matching_conversations AS (
                            SELECT DISTINCT
                                c.id,
                                c.session_id,
                                c.user_id,
                                c.title,
                                c.language,
                                c.message_count,
                                c.first_message_preview,
                                c.last_message_preview,
                                c.status,
                                c.created_at,
                                c.updated_at,
                                c.last_activity_at,
                                -- Score de pertinence: recherche dans titre + messages
                                GREATEST(
                                    ts_rank(to_tsvector('simple', COALESCE(c.title, '')), to_tsquery('simple', %s)),
                                    MAX(ts_rank(to_tsvector('simple', COALESCE(m.content, '')), to_tsquery('simple', %s)))
                                ) as relevance_score
                            FROM conversations c
                            LEFT JOIN messages m ON m.conversation_id = c.id
                            WHERE c.user_id = %s
                                AND c.status = 'active'
                                AND (
                                    to_tsvector('simple', COALESCE(c.title, '')) @@ to_tsquery('simple', %s)
                                    OR to_tsvector('simple', COALESCE(m.content, '')) @@ to_tsquery('simple', %s)
                                )
                            GROUP BY c.id
                        )
                        SELECT
                            id::text,
                            session_id::text,
                            user_id,
                            title,
                            language,
                            message_count,
                            first_message_preview,
                            last_message_preview,
                            status,
                            created_at,
                            updated_at,
                            last_activity_at,
                            relevance_score
                        FROM matching_conversations
                        ORDER BY relevance_score DESC, last_activity_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (search_term, search_term, user_id, search_term, search_term, limit, offset)
                    )

                    rows = cur.fetchall()

                    # Compter le total de résultats
                    cur.execute(
                        """
                        SELECT COUNT(DISTINCT c.id) as total
                        FROM conversations c
                        LEFT JOIN messages m ON m.conversation_id = c.id
                        WHERE c.user_id = %s
                            AND c.status = 'active'
                            AND (
                                to_tsvector('simple', COALESCE(c.title, '')) @@ to_tsquery('simple', %s)
                                OR to_tsvector('simple', COALESCE(m.content, '')) @@ to_tsquery('simple', %s)
                            )
                        """,
                        (user_id, search_term, search_term)
                    )

                    total = cur.fetchone()["total"]

                    conversations = []
                    for row in rows:
                        conversations.append({
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "user_id": row["user_id"],
                            "title": row["title"],
                            "language": row["language"],
                            "message_count": row["message_count"],
                            "first_message_preview": row["first_message_preview"],
                            "preview": row["first_message_preview"],  # Alias pour compatibilité
                            "last_message_preview": row["last_message_preview"],
                            "status": row["status"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                            "last_activity_at": row["last_activity_at"].isoformat() if row["last_activity_at"] else None,
                            "relevance_score": float(row["relevance_score"])
                        })

                    logger.info(f"Recherche '{search_query}' pour {user_id}: {total} résultats")

                    return {
                        "conversations": conversations,
                        "total": total,
                        "query": search_query,
                        "limit": limit,
                        "offset": offset
                    }

        except Exception as e:
            logger.error(f"Erreur recherche conversations: {e}")
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
