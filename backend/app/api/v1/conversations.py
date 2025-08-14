# app/api/v1/conversations.py
"""
Router pour la gestion des conversations avec intégration PostgreSQL optimisée.
Version avec requêtes JSONB fiables + retour messages + index de performance.
VERSION MISE À JOUR pour support persistance conversations complète.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
import logging
import os
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# 🔒 Import authentification pour certains endpoints protégés
from app.api.v1.auth import get_current_user

logger = logging.getLogger("app.api.v1.conversations")
router = APIRouter()

# ===== Initialisation PostgresMemory =====
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

# ===== Fallback ConversationTracker =====
conversation_tracker = None
if not MEMORY_AVAILABLE:
    try:
        from .utils.conversation_tracker import ConversationTracker
        conversation_tracker = ConversationTracker()
        logger.info("✅ Fallback: ConversationTracker loaded")
    except Exception as e:
        logger.warning(f"⚠️ ConversationTracker unavailable: {e}")

# ===== Fonction utilitaire pour créer l'index JSONB =====
def ensure_user_id_index():
    """
    Crée l'index JSONB sur user_id si il n'existe pas déjà.
    Fonction idempotente et safe.
    """
    if not MEMORY_AVAILABLE or not memory:
        return False
    
    try:
        with psycopg2.connect(memory.dsn) as conn:
            with conn.cursor() as cur:
                # Vérifier si l'index existe déjà
                cur.execute("""
                    SELECT 1 FROM pg_indexes 
                    WHERE tablename = 'conversation_memory' 
                    AND indexname = 'ix_conv_user_id'
                """)
                
                if not cur.fetchone():
                    # Créer l'index si il n'existe pas
                    cur.execute("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_conv_user_id
                        ON conversation_memory ((context->>'user_id'))
                    """)
                    logger.info("✅ Index JSONB ix_conv_user_id créé avec succès")
                else:
                    logger.debug("ℹ️ Index JSONB ix_conv_user_id déjà existant")
                    
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Impossible de créer l'index JSONB: {e}")
        return False

# ===== Fonction utilitaire pour parsing contexte =====
def parse_conversation_context(context_data: Any) -> Dict[str, Any]:
    """
    Parse le contexte de conversation de façon robuste.
    Supporte JSON string ou dict directement.
    """
    if isinstance(context_data, dict):
        return context_data
    elif isinstance(context_data, str):
        try:
            return json.loads(context_data)
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Impossible de parser le contexte JSON: {context_data[:100]}...")
            return {}
    else:
        return {}

# ===== Fonction utilitaire pour formater les conversations =====
def format_conversation_summary(session_id: str, context: Dict[str, Any], created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Formate une conversation pour l'affichage dans la liste.
    Extrait titre, preview et métadonnées importantes.
    """
    messages = context.get("messages", [])
    
    # Générer titre intelligent
    title = f"Conversation {session_id[:8]}..."
    preview = "Conversation utilisateur"
    
    if messages:
        # Chercher le premier message utilisateur
        user_messages = [m for m in messages if m.get("role") == "user"]
        if user_messages:
            first_question = user_messages[0].get("content", "")
            if first_question:
                title = first_question[:50] + ("..." if len(first_question) > 50 else "")
                preview = first_question[:100] + ("..." if len(first_question) > 100 else "")
    
    # Compter les types de messages
    user_message_count = len([m for m in messages if m.get("role") == "user"])
    assistant_message_count = len([m for m in messages if m.get("role") == "assistant"])
    
    # Extraire langue et autres métadonnées
    language = context.get("language", "fr")
    user_id = context.get("user_id", "unknown")
    
    # Timestamps
    created_iso = created_at.isoformat() if created_at else datetime.utcnow().isoformat()
    updated_iso = updated_at.isoformat() if updated_at else datetime.utcnow().isoformat()
    
    return {
        "id": session_id,
        "title": title,
        "preview": preview,
        "message_count": len(messages),
        "user_message_count": user_message_count,
        "assistant_message_count": assistant_message_count,
        "created_at": created_iso,
        "updated_at": updated_iso,
        "language": language,
        "user_id": user_id,
        "status": "active"
    }

# ===== Fonction utilitaire pour requêtes JSONB robustes =====
def query_conversations_by_user(user_id: str, limit: int = 20, offset: int = 0) -> tuple[List[tuple], int]:
    """
    Requête optimisée pour récupérer les conversations d'un utilisateur.
    Utilise JSONB avec fallback LIKE si nécessaire.
    Retourne: (conversations_rows, total_count)
    """
    if not MEMORY_AVAILABLE or not memory:
        raise Exception("PostgreSQL memory not available")
    
    conversations = []
    total_count = 0
    
    try:
        with psycopg2.connect(memory.dsn) as conn:
            with conn.cursor() as cur:
                # ✅ Tentative JSONB optimisée (avec index)
                try:
                    cur.execute("""
                        SELECT session_id, context, created_at, updated_at
                        FROM conversation_memory
                        WHERE context->>'user_id' = %s
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s
                    """, (user_id, limit, offset))
                    conversations = cur.fetchall()

                    cur.execute("""
                        SELECT COUNT(*) FROM conversation_memory
                        WHERE context->>'user_id' = %s
                    """, (user_id,))
                    total_count = cur.fetchone()[0]
                    
                    logger.debug(f"✅ Requête JSONB réussie pour {user_id}: {total_count} conversations")
                    
                except Exception as jsonb_err:
                    logger.warning(f"⚠️ Requête JSONB échouée, fallback LIKE: {jsonb_err}")
                    
                    # 🔄 Fallback avec LIKE (moins performant mais fonctionne toujours)
                    cur.execute("""
                        SELECT session_id, context, created_at, updated_at
                        FROM conversation_memory
                        WHERE context::text LIKE %s
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s
                    """, (f'%"user_id":"{user_id}"%', limit, offset))
                    conversations = cur.fetchall()
                    
                    cur.execute("""
                        SELECT COUNT(*) FROM conversation_memory
                        WHERE context::text LIKE %s
                    """, (f'%"user_id":"{user_id}"%',))
                    total_count = cur.fetchone()[0]
                    
                    logger.debug(f"✅ Requête LIKE réussie pour {user_id}: {total_count} conversations")
                    
    except Exception as e:
        logger.error(f"❌ Erreur requête conversations pour {user_id}: {e}")
        raise
    
    return conversations, total_count

# ===== ENDPOINTS PUBLICS =====

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Check de santé du service conversations avec info persistance."""
    try:
        if MEMORY_AVAILABLE and memory:
            stats = memory.get_stats()
            
            # Vérifier l'index JSONB
            index_status = "unknown"
            try:
                with psycopg2.connect(memory.dsn) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT 1 FROM pg_indexes 
                            WHERE tablename = 'conversation_memory' 
                            AND indexname = 'ix_conv_user_id'
                        """)
                        index_status = "exists" if cur.fetchone() else "missing"
            except:
                index_status = "error"
            
            return {
                "status": "healthy",
                "backend": "postgresql",
                "total_conversations": stats.get("total_sessions", 0),
                "index_jsonb_status": index_status,
                "persistence_enabled": True,
                "timestamp": datetime.utcnow().isoformat()
            }
        elif conversation_tracker:
            return {
                "status": "healthy",
                "backend": "conversation_tracker",
                "persistence_enabled": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "limited",
                "backend": "none",
                "message": "No conversation backend available",
                "persistence_enabled": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.exception("❌ Health check failed")
        return {
            "status": "unhealthy",
            "error": str(e),
            "persistence_enabled": False,
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Statistiques globales du système conversations."""
    try:
        if MEMORY_AVAILABLE and memory:
            stats = memory.get_stats()
            
            # Statistiques étendues avec PostgreSQL
            extended_stats = {}
            try:
                with psycopg2.connect(memory.dsn) as conn:
                    with conn.cursor() as cur:
                        # Messages par type
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total_conversations,
                                COUNT(CASE WHEN context->>'user_id' != 'anonymous' THEN 1 END) as authenticated_conversations,
                                COUNT(CASE WHEN context->>'user_id' = 'anonymous' THEN 1 END) as anonymous_conversations
                            FROM conversation_memory
                        """)
                        row = cur.fetchone()
                        if row:
                            extended_stats.update({
                                "total_conversations": row[0],
                                "authenticated_conversations": row[1],
                                "anonymous_conversations": row[2]
                            })
                        
                        # Top langues
                        cur.execute("""
                            SELECT context->>'language' as lang, COUNT(*) as count
                            FROM conversation_memory
                            WHERE context->>'language' IS NOT NULL
                            GROUP BY context->>'language'
                            ORDER BY count DESC
                            LIMIT 5
                        """)
                        extended_stats["top_languages"] = [{"language": row[0], "count": row[1]} for row in cur.fetchall()]
                        
            except Exception as e:
                logger.warning(f"⚠️ Impossible de récupérer les stats étendues: {e}")
            
            return {
                **stats,
                **extended_stats,
                "service_status": "operational",
                "backend": "postgresql",
                "timestamp": datetime.utcnow().isoformat()
            }
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
    """Test endpoint public pour vérifier le fonctionnement."""
    return {
        "status": "success",
        "message": "🎉 Conversations router fully functional!",
        "router": "conversations",
        "backend_available": MEMORY_AVAILABLE,
        "persistence_optimized": True,
        "timestamp": datetime.utcnow().isoformat()
    }

# ===== ENDPOINTS PROTÉGÉS (nécessitent authentification) =====

@router.get("/user/{user_id}")
async def get_user_conversations(
    user_id: str, 
    limit: int = Query(default=20, ge=1, le=100), 
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)  # 🔒 Auth requise
) -> Dict[str, Any]:
    """
    Récupère les conversations d'un utilisateur spécifique.
    VERSION OPTIMISÉE avec requêtes JSONB et formatage amélioré.
    Authentification requise pour protéger les données utilisateur.
    """
    try:
        logger.info(f"🔍 get_user_conversations: user_id={user_id}, limit={limit}, requester={current_user.get('email', 'unknown')}")
        
        # Vérification sécurité: l'utilisateur ne peut voir que ses propres conversations
        requester_id = current_user.get('email', current_user.get('user_id', ''))
        if user_id != requester_id and not current_user.get('is_admin', False):
            logger.warning(f"🚫 Tentative d'accès non autorisé: {requester_id} → {user_id}")
            raise HTTPException(
                status_code=403, 
                detail="Vous ne pouvez accéder qu'à vos propres conversations"
            )
        
        if MEMORY_AVAILABLE and memory:
            try:
                # S'assurer que l'index existe
                ensure_user_id_index()
                
                # Récupérer les conversations
                conversations_rows, total_count = query_conversations_by_user(user_id, limit, offset)
                
                # Formater les conversations
                conversations = []
                for session_id, context_data, created_at, updated_at in conversations_rows:
                    try:
                        context = parse_conversation_context(context_data)
                        formatted_conv = format_conversation_summary(session_id, context, created_at, updated_at)
                        conversations.append(formatted_conv)
                    except Exception as parse_error:
                        logger.warning(f"⚠️ Erreur parsing session {session_id}: {parse_error}")
                        continue

                # Statistiques utilisateur
                stats = memory.get_stats()
                
                result = {
                    "status": "success",
                    "user_id": user_id,
                    "conversations": conversations,
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "source": "postgresql_optimized",
                    "timestamp": datetime.utcnow().isoformat(),
                    "system_stats": stats
                }
                
                logger.info(f"✅ PostgreSQL optimisé: {total_count} conversations trouvées pour {user_id}")
                return result

            except Exception as db_error:
                logger.error(f"❌ Erreur PostgreSQL pour {user_id}: {db_error}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Erreur base de données: {str(db_error)}"
                )

        # Fallback ConversationTracker
        if conversation_tracker:
            try:
                conversations = conversation_tracker.get_user_conversations(user_id, limit)
                return {
                    "status": "success",
                    "user_id": user_id,
                    "conversations": conversations,
                    "total_count": len(conversations),
                    "limit": limit,
                    "offset": offset,
                    "source": "conversation_tracker",
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ ConversationTracker error for user {user_id}: {e}")

        # Fallback final: résultat vide
        logger.warning(f"⚠️ Fallback: empty result for user {user_id}")
        return {
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

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Unexpected error for user {user_id}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving conversations for user {user_id}: {str(e)}"
        )

@router.get("/{session_id}")
async def get_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user)  # 🔒 Auth requise
) -> Dict[str, Any]:
    """
    Récupère une conversation spécifique par son session_id.
    VERSION OPTIMISÉE avec messages formatés et sécurité.
    Authentification requise pour protéger les données.
    """
    try:
        logger.info(f"📖 get_conversation: session_id={session_id}, requester={current_user.get('email', 'unknown')}")
        
        if MEMORY_AVAILABLE and memory:
            context = memory.get(session_id)
            
            if not context:
                return {
                    "session_id": session_id,
                    "exists": False,
                    "context": {},
                    "messages": [],
                    "message_count": 0,
                    "reason": "conversation_not_found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Vérification sécurité: l'utilisateur ne peut voir que ses propres conversations
            conversation_user_id = context.get("user_id", "anonymous")
            requester_id = current_user.get('email', current_user.get('user_id', ''))
            
            if conversation_user_id != requester_id and conversation_user_id != "anonymous" and not current_user.get('is_admin', False):
                logger.warning(f"🚫 Tentative d'accès non autorisé à conversation {session_id}: {requester_id} → {conversation_user_id}")
                raise HTTPException(
                    status_code=403,
                    detail="Vous ne pouvez accéder qu'à vos propres conversations"
                )
            
            # Formater les messages de façon cohérente
            messages = context.get("messages", [])
            formatted_messages = []
            
            for msg in messages:
                formatted_msg = {
                    "role": msg.get("role", "unknown"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp", msg.get("ts", datetime.utcnow().isoformat())),
                }
                
                # Ajouter métadonnées si disponibles
                if msg.get("metadata"):
                    formatted_msg["metadata"] = msg["metadata"]
                if msg.get("user_id"):
                    formatted_msg["user_id"] = msg["user_id"]
                    
                formatted_messages.append(formatted_msg)
            
            return {
                "session_id": session_id,
                "exists": True,
                "context": {
                    "user_id": conversation_user_id,
                    "language": context.get("language", "fr"),
                    "created_at": context.get("created_at"),
                    "updated_at": context.get("updated_at"),
                    "message_count": len(messages)
                },
                "messages": formatted_messages,
                "message_count": len(formatted_messages),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        raise HTTPException(status_code=503, detail="Conversation service unavailable")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error retrieving conversation {session_id}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving conversation: {str(e)}"
        )

@router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user)  # 🔒 Auth requise
) -> Dict[str, Any]:
    """
    Supprime une conversation spécifique.
    Authentification requise et vérification propriétaire.
    """
    try:
        logger.info(f"🗑️ delete_conversation: session_id={session_id}, requester={current_user.get('email', 'unknown')}")
        
        if MEMORY_AVAILABLE and memory:
            # Vérifier que la conversation existe et appartient à l'utilisateur
            context = memory.get(session_id)
            
            if context:
                conversation_user_id = context.get("user_id", "anonymous")
                requester_id = current_user.get('email', current_user.get('user_id', ''))
                
                # Vérification sécurité
                if conversation_user_id != requester_id and conversation_user_id != "anonymous" and not current_user.get('is_admin', False):
                    logger.warning(f"🚫 Tentative suppression non autorisée {session_id}: {requester_id} → {conversation_user_id}")
                    raise HTTPException(
                        status_code=403,
                        detail="Vous ne pouvez supprimer que vos propres conversations"
                    )
            
            # Supprimer la conversation
            memory.clear(session_id)
            
            return {
                "session_id": session_id,
                "deleted": True,
                "existed": bool(context),
                "requester": requester_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        raise HTTPException(status_code=503, detail="Conversation service unavailable")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error deleting conversation {session_id}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error deleting conversation: {str(e)}"
        )

# ===== ENDPOINTS D'ADMINISTRATION (super utilisateurs) =====

@router.post("/admin/ensure-index")
async def admin_ensure_index(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Force la création de l'index JSONB pour optimiser les performances.
    Réservé aux administrateurs.
    """
    # Vérification admin
    if not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    
    try:
        success = ensure_user_id_index()
        
        return {
            "status": "success" if success else "failed",
            "index_created": success,
            "admin": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création index: {e}")
        return {
            "status": "error",
            "error": str(e),
            "admin": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/admin/database-info")
async def admin_database_info(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Informations détaillées sur la base de données conversations.
    Réservé aux administrateurs.
    """
    # Vérification admin
    if not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    
    try:
        if not MEMORY_AVAILABLE or not memory:
            return {
                "status": "unavailable",
                "message": "PostgreSQL memory not available"
            }
        
        db_info = {}
        
        with psycopg2.connect(memory.dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Info table
                cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        attname as column_name,
                        typname as data_type
                    FROM pg_stats 
                    JOIN pg_type ON pg_stats.staattnum = pg_type.oid 
                    WHERE tablename = 'conversation_memory'
                    LIMIT 10
                """)
                db_info["table_columns"] = [dict(row) for row in cur.fetchall()]
                
                # Index info
                cur.execute("""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = 'conversation_memory'
                """)
                db_info["indexes"] = [dict(row) for row in cur.fetchall()]
                
                # Stats de taille
                cur.execute("""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('conversation_memory')) as total_size,
                        pg_size_pretty(pg_relation_size('conversation_memory')) as table_size
                """)
                size_info = cur.fetchone()
                if size_info:
                    db_info["size_info"] = dict(size_info)
        
        return {
            "status": "success",
            "database_info": db_info,
            "admin": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur info database: {e}")
        return {
            "status": "error",
            "error": str(e),
            "admin": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }

# ===== ENDPOINTS DE TEST =====

@router.post("/test/create-sample-conversation")
async def test_create_sample_conversation(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Crée une conversation de test pour vérifier la persistance.
    """
    try:
        if not MEMORY_AVAILABLE or not memory:
            raise HTTPException(status_code=503, detail="PostgreSQL memory not available")
        
        # Générer session de test
        test_session_id = f"test_{current_user.get('email', 'unknown')}_{int(datetime.utcnow().timestamp())}"
        user_id = current_user.get('email', current_user.get('user_id', 'test_user'))
        
        # Créer contexte de test
        test_context = {
            "user_id": str(user_id),
            "language": "fr",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "messages": [
                {
                    "role": "user",
                    "content": "Question de test pour vérifier la persistance",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": str(user_id)
                },
                {
                    "role": "assistant",
                    "content": "Réponse de test confirmant que la persistance fonctionne",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "intent": "test",
                        "route": "test_endpoint",
                        "test": True
                    }
                }
            ],
            "message_count": 2
        }
        
        # Sauvegarder
        memory.set(test_session_id, test_context)
        
        return {
            "status": "success",
            "test_session_id": test_session_id,
            "user_id": user_id,
            "message_count": 2,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur création conversation test: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tester": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/test/query-performance")
async def test_query_performance(
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Teste les performances des requêtes JSONB vs LIKE.
    """
    # Vérification admin ou propriétaire
    requester_id = current_user.get('email', current_user.get('user_id', ''))
    if user_id != requester_id and not current_user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    try:
        if not MEMORY_AVAILABLE or not memory:
            raise HTTPException(status_code=503, detail="PostgreSQL memory not available")
        
        import time
        
        performance_results = {}
        
        with psycopg2.connect(memory.dsn) as conn:
            with conn.cursor() as cur:
                # Test requête JSONB
                start_time = time.time()
                try:
                    cur.execute("""
                        SELECT COUNT(*) FROM conversation_memory
                        WHERE context->>'user_id' = %s
                    """, (user_id,))
                    jsonb_count = cur.fetchone()[0]
                    jsonb_time = (time.time() - start_time) * 1000
                    performance_results["jsonb"] = {
                        "count": jsonb_count,
                        "time_ms": round(jsonb_time, 2),
                        "status": "success"
                    }
                except Exception as e:
                    performance_results["jsonb"] = {
                        "status": "error",
                        "error": str(e)
                    }
                
                # Test requête LIKE
                start_time = time.time()
                try:
                    cur.execute("""
                        SELECT COUNT(*) FROM conversation_memory
                        WHERE context::text LIKE %s
                    """, (f'%"user_id":"{user_id}"%',))
                    like_count = cur.fetchone()[0]
                    like_time = (time.time() - start_time) * 1000
                    performance_results["like"] = {
                        "count": like_count,
                        "time_ms": round(like_time, 2),
                        "status": "success"
                    }
                except Exception as e:
                    performance_results["like"] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        return {
            "status": "success",
            "user_id": user_id,
            "performance_results": performance_results,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur test performance: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": datetime.utcnow().isoformat()
        }