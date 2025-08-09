# app/api/v1/pipeline/dialogue_manager.py
from __future__ import annotations

import os
import logging
import threading
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime

try:
    import anyio  # pour offloader sync -> thread
except Exception:  # fallback léger si anyio n'est pas dispo
    anyio = None  # type: ignore

from ..utils.config import COMPLETENESS_THRESHOLD as _THRESHOLD  # peut lever si absent
from ..utils.response_generator import format_response
from .context_extractor import ContextExtractor
from .clarification_manager import ClarificationManager
from .postgres_memory import PostgresMemory as ConversationMemory
from .rag_engine import RAGEngine

logger = logging.getLogger(__name__)

# --- Sécuriser un défaut si l'import du seuil échoue dans certains environnements
COMPLETENESS_THRESHOLD: float = 0.6
try:
    COMPLETENESS_THRESHOLD = float(_THRESHOLD)
except Exception:
    logger.warning("COMPLETENESS_THRESHOLD non défini, utilisation du défaut 0.6")


def _utc_iso() -> str:
    return datetime.utcnow().isoformat()


def _normalize_sources(raw: Any) -> List[Dict[str, Any]]:
    """
    Normalise différentes formes de 'sources' en une liste de dicts.
    Accepte:
      - list[dict|str]
      - str|dict (unique)
      - None
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        out: List[Dict[str, Any]] = []
        for s in raw:
            if isinstance(s, dict):
                out.append(s)
            else:
                out.append({"source": str(s)})
        return out
    if isinstance(raw, dict):
        return [raw]
    return [{"source": str(raw)}]


class DialogueManager:
    """
    Orchestrateur:
      1) Extraction de contexte
      2) Clarification si score << seuil, sinon fallback avec avertissement
      3) Appel RAG et mise en forme de la réponse (dict: {'answer', 'sources'})
      4) Persistance légère du contexte (mémoire Postgres)

    Compatible avec expert.py:
      - @classmethod get_instance()
      - async handle(session_id, question, language=None, user_id=None)
      - async system_status()
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
        # Dépendances "légères" (pas de heavy load à l'import du module)
        self.extractor = ContextExtractor()
        self.clarifier = ClarificationManager()
        self.memory = ConversationMemory(dsn=os.getenv("DATABASE_URL"))
        self.rag = RAGEngine()

        # Optionnel: démarrage d’une tâche de nettoyage si la mémoire l’expose
        # (aucun crash si non supporté)
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
        # Session
        sid = session_id or str(uuid4())

        # Charger contexte existant (robuste)
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

        logger.info("Q: %s", question[:120])
        logger.info("Completeness=%.2f / seuil=%.2f", score, COMPLETENESS_THRESHOLD)
        if missing:
            logger.info("Champs manquants: %s", missing)

        # 2) Clarification si score très bas
        if score < COMPLETENESS_THRESHOLD:
            if score < 0.2:
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

            # 3) Fallback avec avertissement
            answer_text, sources = await self._generate_with_rag(question, context)
            context["completed_at"] = _utc_iso()
            context["last_interaction"] = _utc_iso()
            self._safe_mem_update(sid, context)
            warn = (
                f"Réponse générale — précisez {', '.join(missing[:2])} pour plus de précision"
                if missing else "Réponse générale"
            )
            return {
                "type": "answer",
                "response": {"answer": format_response(answer_text), "sources": sources},
                "session_id": sid,
                "completeness_score": score,
                "missing_fields": missing,
                "metadata": {"warning": warn},
            }

        # 4) Réponse complète
        answer_text, sources = await self._generate_with_rag(question, context)
        context["completed_at"] = _utc_iso()
        context["last_interaction"] = _utc_iso()
        self._safe_mem_update(sid, context)
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
                "details": {
                    "cleanup_enabled": bool(getattr(self, "_cleanup_enabled", False)),
                },
            }
        except Exception as e:
            logger.exception("system_status error: %s", e)
            return {"status": "error", "rag_ready": False, "details": {"error": str(e)}}

    # -----------------------
    #       INTERNALS
    # -----------------------

    async def _generate_with_rag(self, question: str, context: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        """
        Appelle le moteur RAG. Tolère les deux formats:
          - str (ancien)
          - dict {"response": str, "sources": list|dict|str}
        Offload en thread si anyio est dispo, pour ne pas bloquer l’event loop.
        """
        def _call() -> Any:
            return self.rag.generate_answer(question, context)

        try:
            raw = await anyio.to_thread.run_sync(_call) if anyio else _call()
        except Exception as e:
            logger.exception("RAG generate_answer error: %s", e)
            return ("Désolé, une erreur est survenue lors de la génération de la réponse.", [])

        if isinstance(raw, dict):
            answer_text = str(raw.get("response", "")).strip()
            sources = _normalize_sources(raw.get("sources") or raw.get("source"))
        else:
            answer_text = str(raw).strip()
            sources = []

        return (answer_text, sources)

    def _safe_mem_update(self, session_id: str, context: Dict[str, Any]) -> None:
        try:
            self.memory.update(session_id, context)
        except Exception as e:
            logger.warning("Échec update mémoire (sid=%s): %s", session_id, e)

    def _maybe_start_cleanup(self) -> None:
        """
        Démarre un thread léger de nettoyage **uniquement** si la mémoire expose une API sûre.
        On évite psycopg2 direct ici pour ne pas lier le DM à une implémentation précise.
        """
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
                    cleanup_fn()  # la classe mémoire décide quoi purger
                except Exception as e:
                    logger.debug("Cleanup mémoire: %s", e)
                time.sleep(max(300, interval_min * 60))  # au moins 5 min

        t = threading.Thread(target=_loop, daemon=True)
        t.start()
