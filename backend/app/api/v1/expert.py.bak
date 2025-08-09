# app/api/v1/expert.py
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ValidationError

# ⚠️ conservez vos dépendances/DI existantes
from app.api.v1.pipeline.dialogue_manager import DialogueManager
from app.api.v1.utils.auth import get_current_user_optional  # si vous avez un JWT optionnel
from app.api.v1.utils.config import get_language_from_text  # si vous avez cette util
from app.api.v1.utils.types import SystemStatus  # si défini chez vous

logger = logging.getLogger("api.v1.expert")
router = APIRouter(prefix="", tags=["expert"])

# --- Modèles de requête/réponse (compatibles Pydantic v2) ---

class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, description="User question")
    session_id: Optional[str] = Field(None, description="Existing session id to continue a conversation")
    language: Optional[str] = Field(None, description="Language hint (fr|en|es)")

class AnswerResponse(BaseModel):
    type: str = Field("answer", description="answer | answer_with_warning | clarification | error")
    response: str = Field(..., description="Plain text answer rendered to the user")
    session_id: Optional[str] = Field(None, description="Server-side session id")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ClarificationResponse(BaseModel):
    type: str = Field("clarification", const=True)
    questions: List[str]
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ---- Instances globales (réutilisez vos singletons / DI) ----
# DialogueManager doit être initialisé au startup dans main.py; ici on récupère l’instance
dlg: DialogueManager = DialogueManager.get_instance()

# ---- Helpers internes ----

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
            # on tolère des éléments non-dict, ils seront convertis en str
            normalized = []
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
    # toujours expliciter la stratégie si fournie par le pipeline
    if "strategy" not in md and "type" in result:
        md["strategy"] = result["type"]
    return md

# ---- Endpoints ----

@router.post("/ask", response_model=AnswerResponse)
async def ask(payload: AskRequest, user=Depends(get_current_user_optional)):
    """
    Route principale — renvoie TOUJOURS un AnswerResponse JSON-valid.
    Garantit que 'response' est une string (évite les ValidationError).
    """
    try:
        # Validation & langue
        question = payload.question.strip()
        if not question or len(question) < 2:
            raise HTTPException(status_code=400, detail="Question invalide")
        lang = payload.language or get_language_from_text(question) or "fr"

        # Laisser le DialogueManager orchestrer
        result = await dlg.handle(
            session_id=payload.session_id,
            question=question,
            language=lang,
            user_id=(user["id"] if user else None)
        )
        # result attendu: dict avec au minimum {"type": "...", "response": str|dict}

        # Normalisation pour Pydantic (response: str)
        answer_text, sources = _extract_answer_and_sources(result)
        metadata = _default_metadata(result)

        # exposer les sources (si fourni par le pipeline)
        if sources:
            metadata["sources"] = sources

        # champs utiles de debug/transparence
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
            metadata=metadata
        )
        # Pydantic v2: model_dump() ; v1: dict()
        return resp.model_dump()

    except ValidationError as ve:
        logger.error("❌ Validation error in AnswerResponse: %s", ve)
        raise HTTPException(status_code=500, detail="unexpected_error")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ Erreur inattendue dans /ask: %s", e)
        # Fallback d'urgence – on garde un format *valide* pour le front, pas d’exception crue
        return AnswerResponse(
            type="answer_with_warning",
            response=(
                "Réponse générée en mode fallback d'urgence. "
                "Nous avons rencontré une erreur inattendue, réessayez plus tard."
            ),
            session_id=payload.session_id,
            metadata={"reason": "unexpected_error", "sources": []}
        ).model_dump()


@router.get("/system-status", response_model=SystemStatus)
async def system_status():
    # Conservez votre implémentation, ci-dessous un squelette:
    try:
        status = await dlg.system_status()
        return status
    except Exception as e:
        logger.exception("system-status error: %s", e)
        raise HTTPException(status_code=500, detail="status_unavailable")
