# app/api/v1/pipeline/dialogue_manager.py
from __future__ import annotations

import os
import re
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime

try:
    import anyio
except Exception:
    anyio = None  # type: ignore

from ..utils.config import COMPLETENESS_THRESHOLD as _THRESHOLD
from ..utils.response_generator import format_response
from .context_extractor import ContextExtractor
from .clarification_manager import ClarificationManager
from .postgres_memory import PostgresMemory as ConversationMemory
from .rag_engine import RAGEngine

logger = logging.getLogger(__name__)

# Seuil par défaut si non défini via config
COMPLETENESS_THRESHOLD: float = 0.6
try:
    COMPLETENESS_THRESHOLD = float(_THRESHOLD)
except Exception:
    logger.warning("COMPLETENESS_THRESHOLD non défini, utilisation du défaut 0.6")

# Champs critiques (utilisés conditionnellement selon l’intention)
BASE_CRITICAL_FIELDS = {"race", "sexe"}

# --- Helpers temps ---
def _utc_iso() -> str:
    return datetime.utcnow().isoformat()

# --- Normalisation sources (tolérante) ---
def _normalize_sources(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [s if isinstance(s, dict) else {"source": str(s)} for s in raw]
    if isinstance(raw, dict):
        return [raw]
    return [{"source": str(raw)}]

# --- Intention ---
_WEIGHT_RX = re.compile(r"\b(poids|weight|body\s*weight|bw|cible|id[ée]al)\b", re.I)

def _infer_intent(text: str) -> str:
    t = (text or "").lower()
    return "weight" if _WEIGHT_RX.search(t) else "general"


class DialogueManager:
    """
    Orchestrateur principal (extraction -> clarification -> RAG -> mémoire)
    Compatible expert.py
    """
    _instance: Optional["DialogueManager"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "DialogueManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.extractor = ContextExtractor()
        self.clarifier = ClarificationManager()
        self.memory = ConversationMemory(dsn=os.getenv("DATABASE_URL"))
        self.rag = RAGEngine()
        try:
            self._maybe_start_cleanup()
        except Exception as e:
            logger.warning("Nettoyage de sessions non démarré: %s", e)

    # -----------------------
    #         PUBLIC
    # -----------------------
    async def handle(
        self,
        session_id: Optional[str],
        question: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sid = session_id or str(uuid4())
        logger.info("🟦 DM.handle start | sid=%s | Q=%s", sid, question[:120])

        # 0) mémoire (tolérante)
        try:
            context: Dict[str, Any] = self.memory.get(sid) or {}
        except Exception as e:
            logger.warning("Lecture mémoire échouée (sid=%s): %s", sid, e)
            context = {}

        if language:
            context.setdefault("language", language)
        if user_id:
            context.setdefault("user_id", user_id)

        # 1) Extraction
        extracted, score, missing = self.extractor.extract(question)
        context.update(extracted)

        # 1b) Intention
        intent = _infer_intent(question)
        context["last_intent"] = intent

        # 1c) Champs critiques dynamiques
        critical_fields = set(BASE_CRITICAL_FIELDS)
        if intent == "weight":
            # Pour l’intention poids, l’âge est critique
            critical_fields.add("age")
            # Si pas d’âge explicite, déclarer manquant et forcer la clarification/hybride
            has_age = bool(
                context.get("age_jours")
                or context.get("age")
                or context.get("age_days")
            )
            if not has_age:
                if "age" not in missing and "age_jours" not in missing:
                    missing = list(missing) + ["age"]
                score = min(score, 0.2)

        logger.info("🟩 DM.extract | score=%.2f (seuil=%.2f) | missing=%s", score, COMPLETENESS_THRESHOLD, missing)

        # 1d) Réutilisation mémoire (âge) si intention poids et âge manquant
        if intent == "weight":
            age_present = bool(context.get("age_jours") or context.get("age") or context.get("age_days"))
            if not age_present:
                try:
                    prev_ctx = self.memory.get(sid) or {}
                except Exception:
                    prev_ctx = {}
                last_age = prev_ctx.get("age_jours") or prev_ctx.get("age_days") or prev_ctx.get("age")
                if last_age:
                    context.setdefault("age_jours", last_age)
                    # si on a pu récupérer un âge, on peut remonter un peu le score
                    score = max(score, 0.35)

        # 1e) Hints UI pour RAG (force le rendu)
        context.setdefault("ui_style", {})
        if intent == "weight":
            context["ui_style"].update({"style": "minimal", "format": "bullets", "weight_only": True})
        else:
            context["ui_style"].update({"style": "standard", "format": "auto", "weight_only": False})

        # 2) Clarification si score très bas
        if score < COMPLETENESS_THRESHOLD:
            # Cas très bas : on ne tente pas d’inférer, on clarifie d’abord
            if score < 0.2:
                # Clarification ciblée (si poids → demander explicitement l’âge)
                if intent == "weight" and ("age" in missing or "age_jours" in missing):
                    questions = ["À quel âge (en jours) souhaites-tu la cible ? (ex. 12 j)"]
                else:
                    questions = self.clarifier.generate(missing)

                context["last_interaction"] = _utc_iso()
                self._safe_mem_update(sid, context)
                return {
                    "type": "clarification",
                    "questions": questions,
                    "session_id": sid,
                    "completeness_score": score,
                    "missing_fields": missing,
                }

            # ✅ MODE HYBRIDE : réponse courte + questions critiques
            answer_text, sources = await self._generate_with_rag(question, context)

            follow_up: List[str] = []
            # ne demander que l’essentiel
            to_check = {"race", "sexe"}
            if intent == "weight":
                to_check.add("age")
            critical_missing = [f for f in missing if (f in to_check or f in {"age_jours"})]
            if critical_missing:
                if intent == "weight" and ("age" in critical_missing or "age_jours" in critical_missing):
                    follow_up = ["À quel âge (en jours) souhaites-tu la cible ? (ex. 12 j)"]
                else:
                    follow_up = self.clarifier.generate(critical_missing, round_number=1)
                if follow_up:
                    if answer_text:
                        answer_text = (
                            f"{answer_text}\n\n"
                            "❓ Pour être précis :\n"
                            + "\n".join(f"- {q}" for q in follow_up)
                        )
                    else:
                        answer_text = "❓ Pour être précis :\n" + "\n".join(f"- {q}" for q in follow_up)

            context["completed_at"] = _utc_iso()
            context["last_interaction"] = _utc_iso()
            self._safe_mem_update(sid, context)
            warn = (
                f"Réponse générale — précisez {', '.join(missing[:2])} pour plus de précision"
                if missing else "Réponse générale"
            )
            logger.info("🟨 DM.flow=hybrid | text_len=%s | sources=%s | followups=%s",
                        len(answer_text or ""), len(sources or []), len(follow_up))
            return {
                "type": "answer",
                "response": {"answer": format_response(answer_text), "sources": sources},
                "session_id": sid,
                "completeness_score": score,
                "missing_fields": missing,
                "follow_up_questions": follow_up,
                "metadata": {"warning": warn},
            }

        # 3) Réponse complète
        answer_text, sources = await self._generate_with_rag(question, context)
        context["completed_at"] = _utc_iso()
        context["last_interaction"] = _utc_iso()
        self._safe_mem_update(sid, context)
        logger.info("🟦 DM.flow=final | text_len=%s | sources=%s", len(answer_text or ""), len(sources or []))
        return {
            "type": "answer",
            "response": {"answer": format_response(answer_text), "sources": sources},
            "session_id": sid,
            "completeness_score": score,
            "missing_fields": missing,
        }

    async def system_status(self) -> Dict[str, Any]:
        try:
            rag_ready = True
            if hasattr(self.rag, "is_ready"):
                rag_ready = bool(self.rag.is_ready())
            return {
                "status": "ok" if rag_ready else "degraded",
                "rag_ready": rag_ready,
                "details": {"cleanup_enabled": bool(getattr(self, "_cleanup_enabled", False))},
            }
        except Exception as e:
            logger.exception("system_status error: %s", e)
            return {"status": "error", "rag_ready": False, "details": {"error": str(e)}}

    # -----------------------
    #       INTERNALS
    # -----------------------
    async def _generate_with_rag(self, question: str, context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        def _call() -> Any:
            return self.rag.generate_answer(question, context)

        try:
            raw = await anyio.to_thread.run_sync(_call) if anyio else _call()
        except Exception as e:
            logger.exception("RAG generate_answer error: %s", e)
            return ("Désolé, une erreur est survenue lors de la génération de la réponse.", [])

        if isinstance(raw, dict):
            answer_text = (raw.get("response") or "").strip()
            if not answer_text:
                # garde‑fou pour éviter “réponse vide”
                answer_text = "Désolé, je n’ai pas pu formater la réponse. Peux-tu reformuler en précisant la lignée et l’âge ?"
            sources = _normalize_sources(raw.get("sources") or raw.get("citations") or raw.get("source"))
        else:
            answer_text = str(raw).strip() or "Désolé, je n’ai pas pu formater la réponse."
            sources = []
        return (answer_text, sources)

    def _safe_mem_update(self, session_id: str, context: Dict[str, Any]) -> None:
        try:
            self.memory.update(session_id, context)
        except Exception as e:
            logger.warning("Échec update mémoire (sid=%s): %s", session_id, e)

    def _maybe_start_cleanup(self) -> None:
        cleanup_fn = getattr(self.memory, "cleanup_expired", None)
        if not callable(cleanup_fn):
            self._cleanup_enabled = False
            return
        interval_min = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "30"))
        self._cleanup_enabled = True

        def _loop():
            import time
            while True:
                try:
                    cleanup_fn()
                except Exception as e:
                    logger.debug("Cleanup mémoire: %s", e)
                time.sleep(max(300, interval_min * 60))

        threading.Thread(target=_loop, daemon=True).start()
