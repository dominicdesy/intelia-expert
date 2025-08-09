# app/api/v1/expert.py
from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from typing import Any, Dict, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("api.v1.expert")

# ---------- Auth (fallback sûr) ----------
try:
    from .auth import get_current_user
    AUTH_AVAILABLE = True
except ImportError:
    logger.warning("Auth module non disponible (fallback anonyme)")
    AUTH_AVAILABLE = False
    def get_current_user():
        return {"user_id": "anonymous", "email": "anonymous@example.com"}

# ---------- DialogueManager (fallback sûr) ----------
try:
    from .pipeline.dialogue_manager import DialogueManager
    DIALOGUE_MANAGER_AVAILABLE = True
    logger.info("✅ DialogueManager importé")
except ImportError as e:
    logger.error(f"❌ DialogueManager non disponible: {e}")
    DIALOGUE_MANAGER_AVAILABLE = False
    class DialogueManager:  # fallback minimal
        def handle(self, session_id, question, **kwargs):
            return {
                "type": "answer",
                "response": f"Réponse fallback pour: {question}",
                "session_id": session_id,
                "source": "fallback",
                "documents_used": 0
            }
        def system_status(self):
            return {"status": "fallback", "rag_ready": False, "details": {"mode": "fallback"}}

# ---------- utils ----------
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
    # ✅ NOUVEAU: on expose les champs de complétude et les questions de suivi
    completeness_score: Optional[float] = None
    missing_fields: Optional[List[str]] = None
    follow_up_questions: Optional[List[str]] = None

class SystemStatus(BaseModel):
    status: str = "ok"
    rag_ready: Optional[bool] = None
    details: Dict[str, Any] = Field(default_factory=dict)

# ---------------------------
#     INSTANCES / FACTORY
# ---------------------------

@lru_cache
def get_dialogue_manager() -> DialogueManager:
    try:
        return DialogueManager()
    except Exception as e:
        logger.error(f"❌ Erreur création DialogueManager: {e}")
        return DialogueManager()  # fallback

# ---------------------------
#          HELPERS
# ---------------------------

def extract_answer_and_sources(result: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
    """Extraction robuste du texte de réponse et des sources (si présentes)"""
    response_content = result.get("response", "")
    answer_text = ""
    sources: List[Dict[str, Any]] = []

    if isinstance(response_content, dict):
        answer_text = str(response_content.get("answer", "")).strip()
        raw_sources = response_content.get("sources", [])
        if isinstance(raw_sources, list):
            for s in raw_sources:
                sources.append(s if isinstance(s, dict) else {"source": str(s)})
    else:
        answer_text = str(response_content).strip()
        # nettoyage éventuel d'un format {'answer': "..."}
        import re
        m = re.match(r"^\{'answer':\s*\"(.+)\"\}$", answer_text, re.DOTALL)
        if m:
            answer_text = m.group(1).replace('\\"', '"').replace('\\n', '\n')

    return answer_text, sources

def build_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    metadata = dict(result.get("metadata", {}))
    if "strategy" not in metadata and "type" in result:
        metadata["strategy"] = result["type"]
    for k in ("source", "documents_used", "warning"):
        if k in result:
            metadata[k] = result[k]
    return metadata

# ---------------------------
#          ENDPOINTS
# ---------------------------

@router.post("/ask", response_model=AnswerResponse)
async def ask(payload: AskRequest, user=Depends(get_current_user)):
    logger.info(f"📝 Réception question: {payload.question[:50]}...")

    try:
        question = (payload.question or "").strip()
        if not question or len(question) < 2:
            raise HTTPException(status_code=400, detail="Question trop courte")

        lang = payload.language or get_language_from_text(question) or "fr"
        session_id = payload.session_id or f"session_{uuid.uuid4().hex[:12]}"

        user_id = None
        if isinstance(user, dict):
            user_id = user.get("user_id")
        elif hasattr(user, "id"):
            user_id = getattr(user, "id")

        logger.info(f"🔍 Traitement: session={session_id[:8]}..., user={user_id}, lang={lang}")

        dlg = get_dialogue_manager()

        import asyncio
        if hasattr(dlg, "handle") and asyncio.iscoroutinefunction(dlg.handle):
            result = await dlg.handle(session_id=session_id, question=question, language=lang, user_id=user_id)
        else:
            result = dlg.handle(session_id=session_id, question=question, language=lang, user_id=user_id)

        logger.info(f"✅ DialogueManager réponse: type={result.get('type')}")

        # extraction texte + sources
        try:
            answer_text, sources = extract_answer_and_sources(result)
        except Exception as e:
            logger.error(f"❌ Erreur extraction réponse: {e}")
            answer_text, sources = str(result.get("response", "")), []

        metadata = build_metadata(result)
        if sources:
            metadata["sources"] = sources

        # ✅ NOUVEAU: propager complétude & follow-ups si présents
        response_data: Dict[str, Any] = {
            "type": str(result.get("type", "answer")),
            "response": answer_text or "Réponse vide",
            "session_id": session_id,
            "metadata": metadata,
        }
        for k in ("completeness_score", "missing_fields", "follow_up_questions"):
            if k in result and result[k]:
                response_data[k] = result[k]

        logger.info(f"📤 Envoi réponse: {len(answer_text)} caractères")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Erreur inattendue dans /ask: {e}")
        return {
            "type": "error",
            "response": "Une erreur inattendue s'est produite. Veuillez réessayer.",
            "session_id": payload.session_id or f"error_{uuid.uuid4().hex[:8]}",
            "metadata": {"error": "unexpected_error", "timestamp": datetime.utcnow().isoformat()},
        }

@router.post("/ask-public", response_model=AnswerResponse)
async def ask_public(payload: AskRequest):
    logger.info(f"🌐 Requête publique: {payload.question[:50]}...")
    return await ask(payload, {"user_id": "anonymous", "email": "anonymous@example.com"})

@router.get("/system-status", response_model=SystemStatus)
async def system_status():
    try:
        dlg = get_dialogue_manager()
        import asyncio
        if hasattr(dlg, "system_status") and asyncio.iscoroutinefunction(dlg.system_status):
            raw = await dlg.system_status()
        else:
            raw = dlg.system_status() if hasattr(dlg, "system_status") else {}
        if isinstance(raw, dict):
            return {
                "status": str(raw.get("status", "ok")),
                "rag_ready": bool(raw.get("rag_ready", False)),
                "details": {k: v for k, v in raw.items() if k not in {"status", "rag_ready"}},
            }
        return {"status": "ok", "rag_ready": DIALOGUE_MANAGER_AVAILABLE, "details": {"dialogue_manager": DIALOGUE_MANAGER_AVAILABLE}}
    except Exception as e:
        logger.exception(f"❌ system-status error: {e}")
        return {"status": "error", "rag_ready": False, "details": {"error": str(e)}}
