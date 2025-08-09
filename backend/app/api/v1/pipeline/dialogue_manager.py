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
from ..utils.response_generator import format_response, build_card
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

CRITICAL_FIELDS = {"race", "sexe"}

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

    async def handle(
        self,
        session_id: Optional[str],
        question: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sid = session_id or str(uuid4())

        # mémoire
        try:
            context: Dict[str, Any] = self.memory.get(sid) or {}
        except Exception as e:
            logger.warning("Lecture mémoire échouée (sid=%s): %s", sid, e)
            context = {}

        if language:
            context.setdefault("language", language)
        if user_id:
            context.setdefault("user_id", user_id)

        # Extraction
        extracted, score, missing = self.extractor.extract(question)
        context.update(extracted)

        # UI prefs neutres par défaut
        ui = context.setdefault("ui_prefs", {})
        # On force le mode bullets uniquement si l'utilisateur demande explicitement un "poids"
        ui["weight_only"] = bool(re.search(r"\b(poids|weight|body\s*weight)\b", (question or "").lower()))
        ui["format"] = "bullets" if ui["weight_only"] else ui.get("format", "auto")

        # BONUS : heuristique broiler (inchangé)
        self._apply_broiler_fallback(question, context)

        logger.info("Q: %s", question[:120])
        logger.info("Completeness=%.2f / seuil=%.2f", score, COMPLETENESS_THRESHOLD)
        if missing:
            logger.info("Champs manquants: %s", missing)

        # 1) Cas très incomplet → questions de clarification (pures)
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

        # 2) Cas partiel (< seuil) → réponse générale courte + 2 questions ciblées
        if score < COMPLETENESS_THRESHOLD:
            answer_text, sources = await self._generate_with_rag(question, context, style="minimal")
            follow_up = []
            critical_missing = [f for f in missing if f in CRITICAL_FIELDS]
            if critical_missing:
                follow_up = self.clarifier.generate(critical_missing, round_number=1)[:2]

            # Mise en page card (générale)
            headline = "Réponse générale (à affiner)"
            bullets = [
                answer_text.strip()[:180]
            ]
            footnote = None
            if missing:
                footnote = "Précisez les champs manquants pour une cible plus précise."
            card = build_card(
                headline=headline,
                bullets=bullets,
                footnote=footnote,
                followups=follow_up,
                sources=sources,
            )

            context["completed_at"] = _utc_iso()
            context["last_interaction"] = _utc_iso()
            self._safe_mem_update(sid, context)
            return {
                "type": "answer",
                "response": card,  # UI belle
                "legacy": {"answer": format_response(answer_text), "sources": sources},  # compat
                "session_id": sid,
                "completeness_score": score,
                "missing_fields": missing,
                "follow_up_questions": follow_up,
                "metadata": {"warning": "Réponse générale — précisions requises"},
            }

        # 3) Cas complet → réponse précise (RAG si possible), toujours compacte
        answer_text, sources = await self._generate_with_rag(question, context, style="standard")

        # Mise en page card (précise)
        headline = answer_text.split("\n", 1)[0][:90] if answer_text else "Réponse"
        # Essaie d’extraire 2–3 puces courtes ; sinon tronquer la phrase
        raw_lines = [l.strip("-• ").strip() for l in (answer_text or "").split("\n") if l.strip()]
        bullets = []
        for l in raw_lines:
            if len(bullets) >= 3:
                break
            if len(l) > 130:
                bullets.append(l[:127] + "…")
            else:
                bullets.append(l)
        if not bullets:
            bullets = [answer_text[:130] + "…"] if answer_text else []
        footnote = None
        card = build_card(
            headline=headline,
            bullets=bullets,
            footnote=footnote,
            followups=[],
            sources=sources,
        )

        context["completed_at"] = _utc_iso()
        context["last_interaction"] = _utc_iso()
        self._safe_mem_update(sid, context)
        return {
            "type": "answer",
            "response": card,  # UI belle
            "legacy": {"answer": format_response(answer_text), "sources": sources},  # compat
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

    # ---------------- internals ---------------- #

    def _apply_broiler_fallback(self, question: str, context: Dict[str, Any]) -> None:
        prod = (context.get("production_type") or context.get("species") or "").lower()
        has_species = prod in {"broiler", "layer", "breeder", "pullet"}
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

    async def _generate_with_rag(self, question: str, context: Dict[str, Any], style: str = "standard") -> tuple[str, List[Dict[str, Any]]]:
        def _call() -> Any:
            ui = (context or {}).get("ui_prefs") or {}
            return self.rag.generate_answer(
                question,
                context,
                style=style,
                output_format=ui.get("format", "auto"),
                weight_only=bool(ui.get("weight_only", False)),
            )
        try:
            raw = await anyio.to_thread.run_sync(_call) if anyio else _call()
        except Exception as e:
            logger.exception("RAG generate_answer error: %s", e)
            return ("Désolé, une erreur est survenue lors de la génération de la réponse.", [])
        if isinstance(raw, dict):
            answer_text = str(raw.get("response", "")).strip()
            sources = raw.get("sources") or _normalize_sources(raw.get("source"))
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
