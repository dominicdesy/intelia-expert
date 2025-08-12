# app/api/v1/conversations.py
# -*- coding: utf-8 -*-
"""
Router pour la gestion des conversations stockées en PostgreSQL.
Permet de récupérer, lister et gérer l'historique des conversations.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any, Optional
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

# Import du système de mémoire PostgreSQL existant
try:
    from .postgres_memory import PostgresMemory
    memory = PostgresMemory(dsn=os.getenv("DATABASE_URL"))
    MEMORY_AVAILABLE = True
    logger.info("✅ PostgresMemory initialized for conversations")
except Exception as e:
    logger.error(f"❌ Failed to initialize PostgresMemory: {e}")
    MEMORY_AVAILABLE = False
    memory = None

# ===== ENDPOINT DE TEST PUBLIC (AJOUTÉ) =====

@router.get("/test-public")
async def test_public_endpoint():
    """Endpoint de test public pour vérifier que le router fonctionne"""
    return {
        "status": "success",
        "message": "🎉 Le router conversations fonctionne parfaitement !",
        "timestamp": datetime.utcnow().isoformat(),
        "router": "conversations",
        "auth_required": False,
        "memory_available": MEMORY_AVAILABLE
    }

@router.post("/test-public-post")
async def test_public_post(data: dict = {}):
    """Test POST public"""
    return {
        "status": "success", 
        "message": "🚀 POST fonctionne aussi !",
        "received_data": data,
        "router": "conversations",
        "timestamp": datetime.utcnow().isoformat()
    }

# ===== Endpoints pour les conversations (CODE ORIGINAL) =====

@router.get("/{session_id}")
def get_conversation(session_id: str) -> Dict[str, Any]:
    """
    Récupère l'historique complet d'une conversation par session_id.
    
    Args:
        session_id: Identifiant unique de la session de conversation
        
    Returns:
        Dict contenant la conversation avec métadonnées
    """
    if not MEMORY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Conversation memory service unavailable")
    
    try:
        logger.info(f"📖 Récupération conversation session_id={session_id}")
        
        # Récupération du contexte depuis PostgreSQL
        context = memory.get(session_id)
        
        if not context:
            # Session existe mais pas de contexte = conversation vide
            return {
                "session_id": session_id,
                "exists": False,
                "context": {},
                "messages": [],
                "message_count": 0,
                "last_activity": None,
                "summary": "No conversation data found"
            }
        
        # Extraction des messages si ils existent dans le contexte
        messages = context.get("messages", [])
        last_message = messages[-1] if messages else None
        
        result = {
            "session_id": session_id,
            "exists": True,
            "context": context,
            "messages": messages,
            "message_count": len(messages),
            "last_activity": last_message.get("timestamp") if last_message else None,
            "summary": f"{len(messages)} messages in conversation"
        }
        
        logger.info(f"✅ Conversation récupérée: {len(messages)} messages")
        return jsonable_encoder(result)
        
    except Exception as e:
        logger.exception(f"❌ Erreur récupération conversation {session_id}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")

@router.get("/user/{user_id}")
def get_user_conversations(
    user_id: str, 
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
) -> Dict[str, Any]:
    """
    Récupère toutes les conversations d'un utilisateur.
    Note: Nécessite une structure de données qui lie user_id à session_id.
    
    Args:
        user_id: Identifiant de l'utilisateur
        limit: Nombre max de conversations à retourner (1-100)
        offset: Décalage pour pagination
        
    Returns:
        Liste des conversations de l'utilisateur
    """
    if not MEMORY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Conversation memory service unavailable")
    
    try:
        logger.info(f"👤 Récupération conversations user_id={user_id}")
        
        # Pour l'instant, retourne les stats générales
        # TODO: Implémenter le mapping user_id -> session_ids si nécessaire
        stats = memory.get_stats()
        
        # Placeholder - à adapter selon votre structure de données
        result = {
            "user_id": user_id,
            "conversations": [],  # TODO: Implémenter la récupération par user
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "message": "User conversation mapping not yet implemented",
            "system_stats": stats
        }
        
        logger.warning(f"⚠️ User conversation mapping non implémenté pour user_id={user_id}")
        return jsonable_encoder(result)
        
    except Exception as e:
        logger.exception(f"❌ Erreur récupération conversations user {user_id}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user conversations: {str(e)}")

@router.delete("/{session_id}")
def delete_conversation(session_id: str) -> Dict[str, Any]:
    """
    Supprime une conversation complètement.
    
    Args:
        session_id: Identifiant de la session à supprimer
        
    Returns:
        Confirmation de suppression
    """
    if not MEMORY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Conversation memory service unavailable")
    
    try:
        logger.info(f"🗑️ Suppression conversation session_id={session_id}")
        
        # Vérifier si la conversation existe avant suppression
        context = memory.get(session_id)
        existed = bool(context)
        
        # Suppression
        memory.clear(session_id)
        
        result = {
            "session_id": session_id,
            "deleted": True,
            "existed": existed,
            "message": f"Conversation {'deleted' if existed else 'did not exist'}"
        }
        
        status = 'supprimée' if existed else "n'existait pas"
        logger.info(f"✅ Conversation {session_id} {status}")        
        return jsonable_encoder(result)
        
    except Exception as e:
        logger.exception(f"❌ Erreur suppression conversation {session_id}")
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

@router.get("/")
def list_recent_conversations(
    limit: int = Query(default=10, ge=1, le=50),
    hours: int = Query(default=24, ge=1, le=168)  # Max 1 semaine
) -> Dict[str, Any]:
    """
    Liste les conversations récentes (nécessite des métadonnées étendues).
    Pour l'instant, retourne les statistiques système.
    
    Args:
        limit: Nombre de conversations à retourner
        hours: Période en heures pour "récent"
        
    Returns:
        Liste des conversations récentes ou stats système
    """
    if not MEMORY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Conversation memory service unavailable")
    
    try:
        logger.info(f"📋 Liste conversations récentes (limit={limit}, hours={hours})")
        
        # Récupération des statistiques système
        stats = memory.get_stats()
        
        # TODO: Pour une vraie implémentation, il faudrait :
        # 1. Une table avec session_id, user_id, created_at, updated_at
        # 2. Ou étendre PostgresMemory pour stocker ces métadonnées
        
        result = {
            "conversations": [],  # TODO: Implémenter la liste avec métadonnées
            "total_found": 0,
            "limit": limit,
            "time_window_hours": hours,
            "message": "Recent conversations listing not yet implemented",
            "system_stats": stats,
            "note": "Use GET /conversations/{session_id} to retrieve specific conversations"
        }
        
        logger.info("✅ Stats système récupérées (liste détaillée non implémentée)")
        return jsonable_encoder(result)
        
    except Exception as e:
        logger.exception("❌ Erreur récupération conversations récentes")
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")

@router.post("/{session_id}/clear")
def clear_conversation(session_id: str) -> Dict[str, Any]:
    """
    Vide le contenu d'une conversation (équivalent à reset).
    
    Args:
        session_id: Identifiant de la session à vider
        
    Returns:
        Confirmation de vidage
    """
    if not MEMORY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Conversation memory service unavailable")
    
    try:
        logger.info(f"🧹 Vidage conversation session_id={session_id}")
        
        # Vérifier si elle existe
        context = memory.get(session_id)
        existed = bool(context)
        message_count = len(context.get("messages", [])) if context else 0
        
        # Vider en mettant un contexte vide
        memory.update(session_id, {})
        
        result = {
            "session_id": session_id,
            "cleared": True,
            "existed": existed,
            "previous_message_count": message_count,
            "message": f"Conversation cleared ({message_count} messages removed)"
        }
        
        logger.info(f"✅ Conversation {session_id} vidée ({message_count} messages supprimés)")
        return jsonable_encoder(result)
        
    except Exception as e:
        logger.exception(f"❌ Erreur vidage conversation {session_id}")
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")

@router.get("/stats")
def get_conversation_stats() -> Dict[str, Any]:
    """
    Récupère les statistiques globales des conversations.
    
    Returns:
        Statistiques détaillées du système de conversations
    """
    if not MEMORY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Conversation memory service unavailable")
    
    try:
        logger.info("📊 Récupération statistiques conversations")
        
        stats = memory.get_stats()
        
        # Enrichissement avec des infos supplémentaires
        enhanced_stats = {
            **stats,
            "service_status": "operational",
            "memory_backend": "PostgreSQL",
            "features": {
                "get_conversation": True,
                "delete_conversation": True,
                "clear_conversation": True,
                "list_by_user": False,  # Non implémenté
                "search_conversations": False,  # Non implémenté
                "conversation_export": False   # Non implémenté
            }
        }
        
        logger.info("✅ Statistiques conversations récupérées")
        return jsonable_encoder(enhanced_stats)
        
    except Exception as e:
        logger.exception("❌ Erreur récupération statistiques")
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")

@router.post("/cleanup")
def cleanup_old_conversations(
    days_old: int = Query(default=7, ge=1, le=30),
    dry_run: bool = Query(default=True)
) -> Dict[str, Any]:
    """
    Nettoie les conversations anciennes.
    
    Args:
        days_old: Age minimum en jours pour la suppression
        dry_run: Si True, ne supprime pas vraiment (simulation)
        
    Returns:
        Résultat du nettoyage
    """
    if not MEMORY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Conversation memory service unavailable")
    
    try:
        logger.info(f"🧹 Nettoyage conversations anciennes (days_old={days_old}, dry_run={dry_run})")
        
        if dry_run:
            # Simulation - ne supprime pas vraiment
            stats = memory.get_stats()
            result = {
                "dry_run": True,
                "days_old": days_old,
                "would_delete": "unknown",  # PostgresMemory ne permet pas de compter sans supprimer
                "current_stats": stats,
                "message": "Dry run completed. Use dry_run=false to actually delete."
            }
        else:
            # Vraie suppression
            deleted_count = memory.cleanup_old_sessions(days_old)
            result = {
                "dry_run": False,
                "days_old": days_old,
                "deleted_count": deleted_count,
                "message": f"Cleanup completed. {deleted_count} old conversations deleted."
            }
        
        logger.info(f"✅ Nettoyage {'simulé' if dry_run else 'effectué'}")
        return jsonable_encoder(result)
        
    except Exception as e:
        logger.exception("❌ Erreur nettoyage conversations")
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

# ===== Endpoint de santé (CORRIGÉ) =====

@router.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Vérification de santé du service de conversations.
    
    Returns:
        Status de santé du service
    """
    try:
        if not MEMORY_AVAILABLE:
            return {
                "status": "unhealthy",
                "error": "PostgreSQL memory backend not available",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Test basique de connectivité
        stats = memory.get_stats()
        
        return {
            "status": "healthy",
            "backend": "PostgreSQL",
            "total_conversations": stats.get("total_sessions", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception("❌ Health check failed")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }