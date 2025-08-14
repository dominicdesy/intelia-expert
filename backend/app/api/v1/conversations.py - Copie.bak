# app/api/v1/conversations.py
"""
Router pour la gestion des conversations avec intégration PostgreSQL.
Version complète intégrée avec le système existant.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime

# Logger de l'app
logger = logging.getLogger("app.api.v1.conversations")
router = APIRouter()

# Import du système PostgreSQL
MEMORY_AVAILABLE = False
memory = None

try:
    from .pipeline.postgres_memory import PostgresMemory
    memory = PostgresMemory(dsn=os.getenv("DATABASE_URL"))
    MEMORY_AVAILABLE = True
    logger.info("✅ PostgresMemory initialized for conversations")
except ImportError as e:
    logger.warning(f"⚠️ PostgresMemory import failed: {e}")
except Exception as e:
    logger.error(f"❌ PostgresMemory initialization failed: {e}")

# Fallback vers le système de logging existant
conversation_tracker = None
if not MEMORY_AVAILABLE:
    try:
        from .utils.conversation_tracker import ConversationTracker
        conversation_tracker = ConversationTracker()
        logger.info("✅ Fallback: ConversationTracker loaded")
    except Exception as e:
        logger.warning(f"⚠️ ConversationTracker unavailable: {e}")

# ===== ENDPOINTS SPÉCIFIQUES (AVANT les routes génériques) =====

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Vérification de santé du service.
    """
    try:
        if MEMORY_AVAILABLE and memory:
            stats = memory.get_stats()
            return {
                "status": "healthy",
                "backend": "postgresql",
                "total_conversations": stats.get("total_sessions", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        elif conversation_tracker:
            return {
                "status": "healthy",
                "backend": "conversation_tracker",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "limited",
                "backend": "none",
                "message": "No conversation backend available",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.exception("❌ Health check failed")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Statistiques du service de conversations.
    """
    try:
        if MEMORY_AVAILABLE and memory:
            stats = memory.get_stats()
            enhanced_stats = {
                **stats,
                "service_status": "operational",
                "backend": "postgresql",
                "timestamp": datetime.utcnow().isoformat()
            }
            return enhanced_stats
        else:
            return {
                "total_sessions": 0,
                "service_status": "limited",
                "backend": "none",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.exception("❌ Error getting stats")
        return {
            "error": str(e),
            "service_status": "error",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test-public")
async def test_public() -> Dict[str, Any]:
    """
    Test public endpoint.
    """
    return {
        "status": "success",
        "message": "🎉 Conversations router fully functional!",
        "router": "conversations",
        "backend_available": MEMORY_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/user/{user_id}")
async def get_user_conversations(
    user_id: str, 
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
) -> Dict[str, Any]:
    """
    Récupère toutes les conversations d'un utilisateur.
    """
    try:
        logger.info(f"📋 get_user_conversations: user_id={user_id}, limit={limit}")
        
        if MEMORY_AVAILABLE and memory:
            # Utiliser PostgreSQL
            try:
                stats = memory.get_stats()
                
                # 🔧 NOUVEAU: Implémenter le mapping user_id -> sessions
                try:
                    import psycopg2
                    import json
                    from datetime import datetime
                    
                    # Connexion PostgreSQL pour récupérer les sessions utilisateur
                    with psycopg2.connect(memory.dsn) as conn:
                        with conn.cursor() as cur:
                            # Requête pour trouver les sessions qui contiennent cet user_id
                            cur.execute("""
                                SELECT session_id, context, created_at, updated_at 
                                FROM conversation_memory 
                                WHERE context::text LIKE %s
                                ORDER BY updated_at DESC
                                LIMIT %s OFFSET %s
                            """, (f'%{user_id}%', limit, offset))
                            
                            sessions = cur.fetchall()
                            
                            # Compter le total
                            cur.execute("""
                                SELECT COUNT(*) 
                                FROM conversation_memory 
                                WHERE context::text LIKE %s
                            """, (f'%{user_id}%',))
                            
                            total_count = cur.fetchone()[0]
                            
                            # Transformer en format conversations
                            conversations = []
                            for session_id, context, created_at, updated_at in sessions:
                                try:
                                    # Parser le contexte JSON
                                    ctx = json.loads(context) if isinstance(context, str) else context
                                    messages = ctx.get("messages", [])
                                    
                                    # Créer une conversation formatée
                                    conversation = {
                                        "id": session_id,
                                        "title": f"Conversation {session_id[:8]}...",
                                        "preview": "Conversation utilisateur",
                                        "message_count": len(messages),
                                        "created_at": created_at.isoformat() if created_at else datetime.utcnow().isoformat(),
                                        "updated_at": updated_at.isoformat() if updated_at else datetime.utcnow().isoformat(),
                                        "language": "fr",
                                        "status": "active"
                                    }
                                    
                                    # Extraire le titre et preview des messages si possible
                                    if messages:
                                        # Premier message utilisateur comme titre potentiel
                                        user_messages = [m for m in messages if m.get("isUser", False)]
                                        if user_messages:
                                            first_msg = user_messages[0].get("content", "")
                                            conversation["title"] = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
                                            conversation["preview"] = first_msg[:100] + "..." if len(first_msg) > 100 else first_msg
                                    
                                    conversations.append(conversation)
                                    
                                except Exception as parse_error:
                                    logger.warning(f"⚠️ Erreur parsing session {session_id}: {parse_error}")
                                    continue
                
                    result = {
                        "status": "success",
                        "user_id": user_id,
                        "conversations": conversations,
                        "total_count": total_count,
                        "limit": limit,
                        "offset": offset,
                        "source": "postgresql",
                        "timestamp": datetime.utcnow().isoformat(),
                        "system_stats": stats
                    }
                    
                    logger.info(f"✅ PostgreSQL: {total_count} conversations found for user {user_id}")
                    return result
                    
                except Exception as db_error:
                    logger.error(f"❌ PostgreSQL query error: {db_error}")
                    # Fallback vers le comportement précédent
                    result = {
                        "status": "success",
                        "user_id": user_id,
                        "conversations": [],
                        "total_count": 0,
                        "limit": limit,
                        "offset": offset,
                        "source": "postgresql_fallback",
                        "timestamp": datetime.utcnow().isoformat(),
                        "system_stats": stats,
                        "error": f"Database query failed: {str(db_error)}"
                    }
                    return result
                
            except Exception as e:
                logger.error(f"❌ PostgreSQL error for user {user_id}: {e}")
                # Fallback ci-dessous
                
            except Exception as e:
                logger.error(f"❌ PostgreSQL error for user {user_id}: {e}")
                # Fallback ci-dessous
        
        # Fallback vers ConversationTracker
        if conversation_tracker:
            try:
                conversations = conversation_tracker.get_user_conversations(user_id, limit)
                result = {
                    "status": "success",
                    "user_id": user_id,
                    "conversations": conversations,
                    "total_count": len(conversations),
                    "limit": limit,
                    "offset": offset,
                    "source": "conversation_tracker",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.info(f"✅ ConversationTracker: {len(conversations)} conversations for user {user_id}")
                return result
                
            except Exception as e:
                logger.error(f"❌ ConversationTracker error for user {user_id}: {e}")
        
        # Fallback final : réponse vide mais structurée
        result = {
            "status": "success",
            "user_id": user_id,
            "conversations": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "source": "fallback",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "No conversation backend available, returning empty result"
        }
        
        logger.warning(f"⚠️ Fallback: empty result for user {user_id}")
        return result
        
    except Exception as e:
        logger.exception(f"❌ Unexpected error for user {user_id}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving conversations for user {user_id}: {str(e)}"
        )

# ===== ROUTES GÉNÉRIQUES (APRÈS les routes spécifiques) =====

@router.get("/{session_id}")
async def get_conversation(session_id: str) -> Dict[str, Any]:
    """
    Récupère une conversation par session_id.
    """
    try:
        logger.info(f"📖 get_conversation: session_id={session_id}")
        
        if MEMORY_AVAILABLE and memory:
            context = memory.get(session_id)
            
            if not context:
                return {
                    "session_id": session_id,
                    "exists": False,
                    "context": {},
                    "messages": [],
                    "message_count": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            messages = context.get("messages", [])
            result = {
                "session_id": session_id,
                "exists": True,
                "context": context,
                "messages": messages,
                "message_count": len(messages),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Conversation retrieved: {len(messages)} messages")
            return result
        
        # Fallback
        raise HTTPException(status_code=503, detail="Conversation service unavailable")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error retrieving conversation {session_id}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")

@router.delete("/{session_id}")
async def delete_conversation(session_id: str) -> Dict[str, Any]:
    """
    Supprime une conversation.
    """
    try:
        logger.info(f"🗑️ delete_conversation: session_id={session_id}")
        
        if MEMORY_AVAILABLE and memory:
            # Vérifier existence
            context = memory.get(session_id)
            existed = bool(context)
            
            # Supprimer
            memory.clear(session_id)
            
            result = {
                "session_id": session_id,
                "deleted": True,
                "existed": existed,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"✅ Conversation {session_id} deleted (existed: {existed})")
            return result
        
        raise HTTPException(status_code=503, detail="Conversation service unavailable")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error deleting conversation {session_id}")
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")