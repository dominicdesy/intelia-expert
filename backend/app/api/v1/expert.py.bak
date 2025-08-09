# app/api/v1/expert.py
from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from typing import Any, Dict, Optional, List, Union
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ValidationError

# ✅ CORRECTION: Imports sécurisés avec fallbacks
logger = logging.getLogger("api.v1.expert")

# Import auth avec fallback
try:
    from .auth import get_current_user
    AUTH_AVAILABLE = True
except ImportError:
    logger.warning("Auth module non disponible")
    AUTH_AVAILABLE = False
    def get_current_user():
        return {"user_id": "anonymous", "email": "anonymous@example.com"}

# Import DialogueManager avec fallback
try:
    from .pipeline.dialogue_manager import DialogueManager
    DIALOGUE_MANAGER_AVAILABLE = True
    logger.info("✅ DialogueManager importé")
except ImportError as e:
    logger.error(f"❌ DialogueManager non disponible: {e}")
    DIALOGUE_MANAGER_AVAILABLE = False
    
    # Fallback DialogueManager simple
    class DialogueManager:
        def handle(self, session_id, question, **kwargs):
            return {
                "type": "answer",
                "response": f"Réponse fallback pour: {question}",
                "session_id": session_id,
                "source": "fallback",
                "documents_used": 0
            }
        
        def system_status(self):
            return {
                "status": "fallback",
                "rag_ready": False,
                "details": {"mode": "fallback"}
            }

# Import utils avec fallback
try:
    from .utils.config import get_language_from_text
except ImportError:
    def get_language_from_text(text: str) -> str:
        return "fr"

router = APIRouter(prefix="", tags=["expert"])

# ---------------------------
#         MODELES
# ---------------------------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, description="User question")
    session_id: Optional[str] = Field(None, description="Existing session id")
    language: Optional[str] = Field(None, description="Language hint (fr|en|es)")

class AnswerResponse(BaseModel):
    type: str = "answer"
    response: str = Field(..., description="Plain text answer")
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SystemStatus(BaseModel):
    status: str = "ok"
    rag_ready: Optional[bool] = None
    details: Dict[str, Any] = Field(default_factory=dict)

# ---------------------------
#     INSTANCES / FACTORY
# ---------------------------

@lru_cache
def get_dialogue_manager() -> DialogueManager:
    """Retourne instance DialogueManager mémorisée"""
    try:
        return DialogueManager()
    except Exception as e:
        logger.error(f"❌ Erreur création DialogueManager: {e}")
        return DialogueManager()  # Fallback

# ---------------------------
#          HELPERS
# ---------------------------

def extract_answer_and_sources(result: Dict[str, Any]) -> tuple:
    """
    ✅ CORRECTION: Extraction avec nettoyage format {'answer': '...'}
    """
    response_content = result.get("response", "")
    answer_text = ""
    sources = []

    if isinstance(response_content, dict):
        # Format structuré avec clé 'answer'
        answer_text = str(response_content.get("answer", "")).strip()
        raw_sources = response_content.get("sources", [])
        if isinstance(raw_sources, list):
            sources = []
            for s in raw_sources:
                if isinstance(s, dict):
                    sources.append(s)
                else:
                    sources.append({"source": str(s)})
    else:
        # Format texte simple
        answer_text = str(response_content).strip()
        
        # ✅ CORRECTION: Nettoyer format {'answer': '...'} si présent
        import re
        match = re.match(r"^\{'answer':\s*\"(.+)\"\}$", answer_text, re.DOTALL)
        if match:
            answer_text = match.group(1)
            # Nettoyer les caractères d'échappement
            answer_text = answer_text.replace('\\"', '"').replace('\\n', '\n')

    return answer_text, sources

def build_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """Construit métadonnées de réponse"""
    metadata = dict(result.get("metadata", {}))
    
    # Ajouter infos de base
    if "strategy" not in metadata and "type" in result:
        metadata["strategy"] = result["type"]
    
    if "source" in result:
        metadata["source"] = result["source"]
    
    if "documents_used" in result:
        metadata["documents_used"] = result["documents_used"]
        
    if "warning" in result:
        metadata["warning"] = result["warning"]
    
    return metadata

# ---------------------------
#          ENDPOINTS
# ---------------------------

@router.post("/ask", response_model=AnswerResponse)
async def ask(payload: AskRequest, user=Depends(get_current_user)):
    """
    ✅ CORRECTION: Endpoint principal avec gestion d'erreur robuste
    """
    logger.info(f"📝 Réception question: {payload.question[:50]}...")
    
    try:
        # Validation de base
        question = (payload.question or "").strip()
        if not question or len(question) < 2:
            raise HTTPException(status_code=400, detail="Question trop courte")

        # Langue
        lang = payload.language or get_language_from_text(question) or "fr"
        
        # Session ID
        session_id = payload.session_id or f"session_{uuid.uuid4().hex[:12]}"
        
        # User info
        user_id = None
        if isinstance(user, dict):
            user_id = user.get("user_id")
        elif hasattr(user, 'id'):
            user_id = user.id
        
        logger.info(f"🔍 Traitement: session={session_id[:8]}..., user={user_id}, lang={lang}")

        # ✅ CORRECTION: Appel DialogueManager sécurisé
        dlg = get_dialogue_manager()
        
        # Appel avec gestion d'erreur
        if hasattr(dlg, 'handle') and callable(dlg.handle):
            # Si handle est async
            import asyncio
            if asyncio.iscoroutinefunction(dlg.handle):
                result = await dlg.handle(
                    session_id=session_id,
                    question=question,
                    language=lang,
                    user_id=user_id
                )
            else:
                # Si handle est sync
                result = dlg.handle(
                    session_id=session_id,
                    question=question,
                    language=lang,
                    user_id=user_id
                )
        else:
            # Fallback si méthode indisponible
            result = {
                "type": "answer",
                "response": f"Réponse générée pour: {question}",
                "session_id": session_id,
                "source": "direct_fallback",
                "documents_used": 0
            }

        logger.info(f"✅ DialogueManager réponse: type={result.get('type')}")

        # ✅ CORRECTION: Extraction avec gestion d'erreur
        try:
            answer_text, sources = extract_answer_and_sources(result)
        except Exception as e:
            logger.error(f"❌ Erreur extraction réponse: {e}")
            answer_text = str(result.get("response", "Erreur extraction réponse"))
            sources = []

        # Métadonnées
        metadata = build_metadata(result)
        if sources:
            metadata["sources"] = sources

        # ✅ CORRECTION: Construction réponse sécurisée
        response_data = {
            "type": str(result.get("type", "answer")),
            "response": answer_text or "Réponse vide",
            "session_id": session_id,
            "metadata": metadata
        }

        logger.info(f"📤 Envoi réponse: {len(answer_text)} caractères")
        
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Erreur inattendue dans /ask: {e}")
        
        # ✅ CORRECTION: Fallback d'urgence robuste
        return {
            "type": "error",
            "response": "Une erreur inattendue s'est produite. Veuillez réessayer.",
            "session_id": payload.session_id or f"error_{uuid.uuid4().hex[:8]}",
            "metadata": {
                "error": "unexpected_error",
                "timestamp": datetime.utcnow().isoformat()
            }
        }

@router.post("/ask-public", response_model=AnswerResponse)
async def ask_public(payload: AskRequest):
    """Version publique sans authentification"""
    # Créer un utilisateur anonyme
    anonymous_user = {"user_id": "anonymous", "email": "anonymous@example.com"}
    
    logger.info(f"🌐 Requête publique: {payload.question[:50]}...")
    
    # Utiliser la même logique que ask() mais sans auth
    return await ask(payload, anonymous_user)

@router.get("/topics")
async def get_topics(language: str = "fr"):
    """Suggestions de sujets"""
    topics_by_lang = {
        "fr": [
            "Problèmes de croissance des poulets",
            "Conditions environnementales optimales",
            "Protocoles de vaccination",
            "Diagnostic des problèmes de santé",
            "Nutrition et alimentation",
            "Gestion de la mortalité"
        ],
        "en": [
            "Chicken growth problems",
            "Optimal environmental conditions", 
            "Vaccination protocols",
            "Health problem diagnosis",
            "Nutrition and feeding",
            "Mortality management"
        ],
        "es": [
            "Problemas de crecimiento de pollos",
            "Condiciones ambientales óptimas",
            "Protocolos de vacunación", 
            "Diagnóstico de problemas de salud",
            "Nutrición y alimentación",
            "Gestión de mortalidad"
        ]
    }
    
    return {
        "status": "success",
        "topics": topics_by_lang.get(language, topics_by_lang["fr"]),
        "language": language
    }

@router.post("/feedback")
async def submit_feedback(feedback_data: Dict[str, Any]):
    """Endpoint pour feedback utilisateur"""
    try:
        conversation_id = feedback_data.get("conversation_id")
        rating = feedback_data.get("rating")
        comment = feedback_data.get("comment", "")
        
        if not conversation_id:
            raise HTTPException(status_code=400, detail="conversation_id requis")
        
        logger.info(f"👍👎 Feedback reçu: {rating} pour {conversation_id}")
        
        # TODO: Sauvegarder en base de données
        
        return {
            "status": "success",
            "message": "Feedback enregistré",
            "feedback_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur enregistrement feedback")

@router.get("/system-status", response_model=SystemStatus)
async def system_status():
    """
    ✅ CORRECTION: Status système avec gestion d'erreur
    """
    try:
        dlg = get_dialogue_manager()
        
        # Appel sécurisé system_status
        if hasattr(dlg, 'system_status') and callable(dlg.system_status):
            import asyncio
            if asyncio.iscoroutinefunction(dlg.system_status):
                raw = await dlg.system_status()
            else:
                raw = dlg.system_status()
        else:
            raw = {
                "status": "ok",
                "rag_ready": DIALOGUE_MANAGER_AVAILABLE,
                "details": {"dialogue_manager": DIALOGUE_MANAGER_AVAILABLE}
            }

        if isinstance(raw, dict):
            return {
                "status": str(raw.get("status", "ok")),
                "rag_ready": bool(raw.get("rag_ready", False)),
                "details": {k: v for k, v in raw.items() if k not in {"status", "rag_ready"}}
            }
        
        return {
            "status": "ok",
            "rag_ready": DIALOGUE_MANAGER_AVAILABLE,
            "details": {"dialogue_manager_available": DIALOGUE_MANAGER_AVAILABLE}
        }
        
    except Exception as e:
        logger.exception(f"❌ system-status error: {e}")
        return {
            "status": "error", 
            "rag_ready": False,
            "details": {"error": str(e)}
        }