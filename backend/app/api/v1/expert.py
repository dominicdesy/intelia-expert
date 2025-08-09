# app/api/v1/expert.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List, Literal

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ValidationError

# ✅ Imports RELATIFS (robustes entre dev local et DO)
from .pipeline.dialogue_manager import DialogueManager
from .auth import get_current_user
try:
    # si tu as bien cette utilitaire
    from .utils.config import get_language_from_text  # type: ignore
except Exception:
    # fallback si la fonction n'existe pas
    def get_language_from_text(_: str) -> str:
        return "fr"

logger = logging.getLogger("api.v1.expert")

# NOTE:
# - Dans main.py tu fais probablement: app.include_router(expert_router, prefix="/v1/expert")
# - Ici on garde prefix="" pour obtenir les routes /v1/expert/...
router = APIRouter(prefix="", tags=["expert"])


# ---------------------------
#         MODELES
# ---------------------------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, description="User question")
    session_id: Optional[str] = Field(None, description="Existing session id to continue a conversation")
    language: Optional[str] = Field(None, description="Language hint (fr|en|es)")


class AnswerResponse(BaseModel):
    type: Literal["answer", "answer_with_warning", "clarification", "error"] = "answer"
    response: str = Field(..., description="Plain text answer rendered to the user")
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemStatus(BaseModel):
    status: Literal["ok", "degraded", "error"] = "ok"
    rag_ready: Optional[bool] = None
    details: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------
#     INSTANCES / SINGLETONS
# ---------------------------

# DialogueManager doit être initialisé au startup dans main.py
dlg: DialogueManager = DialogueManager.get_instance()


# ---------------------------
#          HELPERS
# ---------------------------

def _extract_answer_and_sources(result: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
    """
    Normalise le format renvoyé par DialogueManager:
      - result["response"] peut être str OU dict {"answer": str, "sources": [...]}
    Retourne (answer_text, sources[])
    """
    response_content = result.get("response", "")
    answer_text = ""
    sources: List[Dict[str, Any]] = []

    if isinstance(response_content, dict):
        # format structuré
        answer_text = str(response_content.get("answer", "")).strip()
        raw_sources = response_content.get("sources", [])
        if isinstance(raw_sources, list):
            normalized: List[Dict[str, Any]] = []
            for s in raw_sources:
                if isinstance(s, dict):
                    normalized.append(s)
                else:
                    normalized.append({"source": str(s)})
            sources = normalized
    else:
        # format texte simple
        answer_text = str(response_content).strip()

    return answer_text, sources


def _default_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    md = dict(result.get("metadata") or {})
    if "strategy" not in md and "type" in result:
        md["strategy"] = result["type"]
    return md


# ---------------------------
#          ENDPOINTS
# ---------------------------

@router.post("/ask", response_model=AnswerResponse)
async def ask(payload: AskRequest, user=Depends(get_current_user)):
    """
    Route principale — renvoie TOUJOURS un AnswerResponse JSON-valid.
    Garantit que 'response' est une string (évite les ValidationError).
    """
    try:
        # Validation & langue
        question = (payload.question or "").strip()
        if not question or len(question) < 2:
            raise HTTPException(status_code=400, detail="Question invalide")

        lang = payload.language or get_language_from_text(question) or "fr"

        # Laisser le DialogueManager orchestrer
        result = await dlg.handle(
            session_id=payload.session_id,
            question=question,
            language=lang,
            user_id=(user.get("user_id") if isinstance(user, dict) else None),
        )
        # result attendu: dict avec au minimum {"type": "...", "response": str|dict}

        # Normalisation pour Pydantic (response: str)
        answer_text, sources = _extract_answer_and_sources(result)
        metadata = _default_metadata(result)

        # Exposer les sources (si fournies par le pipeline)
        if sources:
            metadata["sources"] = sources

        # Champs utiles de debug/transparence
        if "completeness_score" in result:
            metadata.setdefault("scores", {})["completeness"] = result["completeness_score"]
        if "missing_fields" in result:
            metadata["missing_fields"] = result["missing_fields"]

        # id de session retourné par le DM si géré côté serveur
        session_id = result.get("session_id") or payload.session_id

        # Construction de la réponse finale (string only)
        resp = AnswerResponse(
            type=str(result.get("type") or "answer"),
            response=answer_text or "Réponse vide.",
            session_id=session_id,
            metadata=metadata,
        )
        # Pydantic v2: model_dump()
        return resp.model_dump()

    except ValidationError as ve:
        logger.error("❌ Validation error in AnswerResponse: %s", ve)
        raise HTTPException(status_code=500, detail="unexpected_error")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ Erreur inattendue dans /ask: %s", e)
        # Fallback d'urgence – format *valide* pour le front
        return AnswerResponse(
            type="answer_with_warning",
            response=("Réponse générée en mode fallback d'urgence. "
                      "Nous avons rencontré une erreur inattendue, réessayez plus tard."),
            session_id=payload.session_id,
            metadata={"reason": "unexpected_error", "sources": []},
        ).model_dump()


@router.get("/system-status", response_model=SystemStatus)
async def system_status():
    """
    Renvoie l’état du pipeline / RAG. On tolère un dict brut,
    mais on le re-map dans SystemStatus si possible.
    """
    try:
        raw = await dlg.system_status()
        if isinstance(raw, dict):
            return SystemStatus(
                status=str(raw.get("status", "ok")),
                rag_ready=bool(raw.get("rag_ready")) if "rag_ready" in raw else None,
                details={k: v for k, v in raw.items() if k not in {"status", "rag_ready"}},
            ).model_dump()
        return SystemStatus().model_dump()
    except Exception as e:
        logger.exception("system-status error: %s", e)
        raise HTTPException(status_code=500, detail="status_unavailable")
