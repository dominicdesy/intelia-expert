# -*- coding: utf-8 -*-
"""
Dialogue Persistence - Gestion de la persistance des conversations
Contient: PostgreSQL, persistance et extraction de texte
"""

from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# ========== NOUVEAU: PERSISTANCE CONVERSATIONS ==========
PERSIST_CONVERSATIONS = str(os.getenv("PERSIST_CONVERSATIONS", "1")).lower() in ("1", "true", "yes", "on")
CLEAR_CONTEXT_AFTER_ASK = str(os.getenv("CLEAR_CONTEXT_AFTER_ASK", "0")).lower() in ("1", "true", "yes", "on")

# Import PostgresMemory pour la persistance
_POSTGRES_MEMORY = None
try:
    from .postgres_memory import PostgresMemory
    _POSTGRES_MEMORY = PostgresMemory(dsn=os.getenv("DATABASE_URL"))
    POSTGRES_AVAILABLE = True
    logger.info("✅ PostgresMemory initialized for conversation persistence")
except Exception as e:
    POSTGRES_AVAILABLE = False
    logger.warning(f"⚠️ PostgresMemory unavailable for persistence: {e}")

def _persist_conversation(
    session_id: str, 
    question: str, 
    answer_text: str,
    language: Optional[str] = None, 
    user_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Persiste une conversation (question + réponse) dans PostgreSQL
    
    Args:
        session_id: ID de la session
        question: Question de l'utilisateur
        answer_text: Réponse générée
        language: Langue détectée/utilisée
        user_id: ID utilisateur (peut être None pour public)
        additional_context: Context additionnel (intent, route, etc.)
    
    Returns:
        bool: True si persistance réussie, False sinon
    """
    if not PERSIST_CONVERSATIONS:
        logger.debug("🔒 Persistance conversations désactivée (PERSIST_CONVERSATIONS=0)")
        return False
        
    if not POSTGRES_AVAILABLE or _POSTGRES_MEMORY is None:
        logger.warning("⚠️ PostgreSQL indisponible pour persistance")
        return False
    
    try:
        # Récupérer le contexte existant ou créer nouveau
        ctx = _POSTGRES_MEMORY.get(session_id) or {}
        msgs = list(ctx.get("messages", []))
        now = datetime.utcnow().isoformat()
        
        # Ajouter le message utilisateur
        user_message = {
            "role": "user",
            "content": question,
            "timestamp": now,
            "user_id": user_id or "anonymous"
        }
        msgs.append(user_message)
        
        # Ajouter la réponse assistant
        assistant_message = {
            "role": "assistant", 
            "content": answer_text,
            "timestamp": now
        }
        
        # Enrichir avec contexte additionnel si fourni
        if additional_context:
            assistant_message["metadata"] = additional_context
            
        msgs.append(assistant_message)
        
        # Mettre à jour le contexte complet
        ctx.update({
            "user_id": user_id or "anonymous",
            "language": language or ctx.get("language") or "fr",
            "messages": msgs,
            "updated_at": now,
            "message_count": len(msgs)
        })
        
        # Si nouveau contexte, ajouter created_at
        if "created_at" not in ctx:
            ctx["created_at"] = now
            
        # Sauvegarder
        _POSTGRES_MEMORY.update(session_id, ctx)
        
        logger.info(f"💾 Conversation persistée: session={session_id}, user={user_id or 'anonymous'}, msgs={len(msgs)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur persistance conversation {session_id}: {e}")
        return False

def _extract_answer_text(response: Dict[str, Any]) -> str:
    """
    Extrait le texte de réponse de façon robuste depuis la structure de réponse
    """
    if not response:
        return ""
        
    # Cas 1: réponse directe avec answer.text
    answer = response.get("answer", {})
    if isinstance(answer, dict) and answer.get("text"):
        return str(answer["text"])
    
    # Cas 2: réponse avec general_answer.text (mode hybride)
    general_answer = response.get("general_answer", {})
    if isinstance(general_answer, dict) and general_answer.get("text"):
        return str(general_answer["text"])
    
    # Cas 3: message direct
    if response.get("message"):
        return str(response["message"])
        
    # Cas 4: fallback sur la structure complète convertie en string
    return str(response.get("answer", response.get("general_answer", "")))

# Exports pour faciliter les imports
__all__ = [
    "PERSIST_CONVERSATIONS",
    "CLEAR_CONTEXT_AFTER_ASK", 
    "POSTGRES_AVAILABLE",
    "_persist_conversation",
    "_extract_answer_text"
]
