# app/api/v1/pipeline/dialogue_manager.py
from __future__ import annotations

import os
import re
import logging
import threading
from typing import Any, Dict, List, Optional
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

COMPLETENESS_THRESHOLD: float = 0.6
try:
    COMPLETENESS_THRESHOLD = float(_THRESHOLD)
except Exception:
    logger.warning("COMPLETENESS_THRESHOLD non défini, utilisation du défaut 0.6")

CRITICAL_FIELDS = {"race", "sexe"}  # ✅ utilisé par le mode hybride

# 🔧 Nouveau : paramètres de concision pour le mode hybride
HYBRID_CONCISE = {
    "enabled": True,
    "max_sentences": 2,   # 1–2 phrases max
    "max_chars": 300,     # et ~300 caractères
}

def _utc_iso() -> str:
    return datetime.utcnow().isoformat()

def _normalize_sources(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [s if isinstance(s, dict) else {"source": str(s)} for s in raw]
    if isinstance(raw, dict):
        return [raw]
    return [{"source": str(raw)}]

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

        # mémoire (tolérante)
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

        # ✅ BONUS : heuristique “fallback broiler”
        self._apply_broiler_fallback(question, context)

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

            # ✅ MODE HYBRIDE : réponse générale + questions ciblées (race/sexe prioritaire)
            answer_text, sources = await self._generate_with_rag(question, context)

            # 🔹 NOUVEAU : rendre le texte concis si des champs critiques manquent
            critical_missing = [f for f in missing if f in CRITICAL_FIELDS]
            if HYBRID_CONCISE.get("enabled") and critical_missing:
                answer_text = self._to_concise_hybrid(
                    original=answer_text,
                    question=question,
                    context=context,
                    max_sentences=int(HYBRID_CONCISE["max_sentences"]),
                    max_chars=int(HYBRID_CONCISE["max_chars"]),
                )

            follow_up: List[str] = []
            if critical_missing:
                follow_up = self.clarifier.generate(critical_missing, round_number=1)
                if follow_up:
                    answer_text = (
                        f"{answer_text}\n\n"
                        "Pour affiner :\n"
                        + "\n".join(f"- {q}" for q in follow_up)
                    )

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
                "follow_up_questions": follow_up,  # ✅ exposé à l’API
                "metadata": {"warning": warn},
            }

        # 3) Réponse complète
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
                "details": {"cleanup_enabled": bool(getattr(self, "_cleanup_enabled", False))},
            }
        except Exception as e:
            logger.exception("system_status error: %s", e)
            return {"status": "error", "rag_ready": False, "details": {"error": str(e)}}

    # -----------------------
    #       INTERNALS
    # -----------------------

    def _apply_broiler_fallback(self, question: str, context: Dict[str, Any]) -> None:
        """
        ✅ BONUS : Si la question concerne le poids et qu'on est <30 jours, 
        et qu'aucune espèce/production_type n'est fournie, on force l'index Broiler.
        """
        prod = (context.get("production_type") or context.get("species") or "").lower()
        has_species = prod in {"broiler", "layer", "breeder", "pullet"}

        # détecter notion de poids
        text = f"{question} {context}".lower()
        weight_like = bool(re.search(r"\b(poids|weight|body\s*weight)\b", text))

        age_days = None
        try:
            if "age_jours" in context:
                age_days = int(float(str(context["age_jours"]).replace(",", ".")))
        except Exception:
            age_days = None

        if not has_species and weight_like and (age_days is not None and age_days < 30):
            context["production_type"] = "broiler"
            context["species"] = "broiler"
            context.setdefault("hints", {})["species_inferred"] = "broiler"
            logger.debug("🐤 BONUS: species fallback → broiler (poids + <30j)")

    async def _generate_with_rag(self, question: str, context: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
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

    # 🔧 Nouveau : filtre “réponse courte” pour le mode hybride
    def _to_concise_hybrid(
        self,
        original: str,
        question: str,
        context: Dict[str, Any],
        max_sentences: int = 2,
        max_chars: int = 300,
    ) -> str:
        """
        Condense une réponse RAG en 1–2 phrases lisibles.
        - Supprime les titres/listes/sections
        - Garde les 1ères phrases informatives
        - Coupe proprement à ~max_chars
        """
        text = original or ""
        # 1) retirer markdown/sections lourdes
        text = re.sub(r"^#{1,6}\s.*$", "", text, flags=re.MULTILINE)               # titres
        text = re.sub(r"^\s*[-•*]\s+.*$", "", text, flags=re.MULTILINE)            # listes
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)                     # blocs code
        text = re.sub(r"\n{2,}", "\n", text).strip()

        # 2) extraire phrases
        # split grossier sur . ! ? suivi d'espace/nouvelle ligne
        parts = re.split(r"(?<=[\.\!\?])\s+", text)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            return original

        concise = " ".join(parts[:max_sentences]).strip()

        # 3) si trop long, couper à une limite douce (sans casser un mot)
        if len(concise) > max_chars:
            cut = concise[:max_chars].rsplit(" ", 1)[0].rstrip(",;:")
            concise = f"{cut}…"

        return concise

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
