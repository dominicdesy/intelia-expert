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

# --- format_response + build_card (avec secours si build_card absent) ---
try:
    from ..utils.response_generator import format_response, build_card  # type: ignore
except Exception:
    from ..utils.response_generator import format_response  # type: ignore

    def build_card(
        headline: str,
        bullets: List[str],
        footnote: Optional[str] = None,
        followups: Optional[List[str]] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return {
            "headline": headline,
            "bullets": bullets,
            "footnote": footnote,
            "followups": followups or [],
            "sources": sources or [],
        }

from .context_extractor import ContextExtractor
from .clarification_manager import ClarificationManager
from .postgres_memory import PostgresMemory as ConversationMemory
from .rag_engine import RAGEngine

logger = logging.getLogger(__name__)

# --------- Configuration ---------
COMPLETENESS_THRESHOLD: float = 0.6
try:
    COMPLETENESS_THRESHOLD = float(_THRESHOLD)
except Exception:
    logger.warning("COMPLETENESS_THRESHOLD non défini, utilisation du défaut 0.6")

# Champs critiques pour la clarification ciblée
CRITICAL_FIELDS = {"race", "sexe"}

# Présentation UI
MAX_BULLET_LEN = 220  # coupe douce pour l’UI card
CLARIF_QUESTION = "Peux-tu préciser la lignée (Ross, Cobb, Hubbard…) et le sexe du lot (mâles, femelles, mixte) ?"

# --------- Utils locaux ---------
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

def _short(txt: Any, n: int = 160) -> str:
    s = str(txt or "")
    return s if len(s) <= n else (s[: n - 1] + "…")

def _mk_bullets_from_text(text: str, limit: int = MAX_BULLET_LEN, max_items: int = 3) -> List[str]:
    if not text:
        return []
    lines = [l.strip("•- ").strip() for l in text.split("\n") if l.strip()]
    bullets: List[str] = []
    for l in lines:
        bullets.append(l if len(l) <= limit else (l[:limit] + "…"))
        if len(bullets) >= max_items:
            break
    if not bullets:
        bullets = [text if len(text) <= limit else (text[:limit] + "…")]
    return bullets

def _compose_markdown(answer_core: str, context_note: Optional[str], clarif_lines: List[str]) -> str:
    """
    Construit une réponse Markdown en 3 blocs :
    - Réponse actuelle
    - Contexte / hypothèses
    - Pour être plus précis (si clarifications)
    """
    parts: List[str] = []
    # Bloc 1 — Réponse actuelle
    core = answer_core.strip() if answer_core else ""
    if not core:
        core = "Je n’ai pas pu formuler une réponse exploitable pour l’instant."
    parts.append("### 📌 Réponse actuelle\n" + core)

    # Bloc 2 — Contexte / hypothèses
    if context_note:
        parts.append("### 🧭 Contexte / hypothèses\n" + context_note.strip())

    # Bloc 3 — Clarification demandée
    if clarif_lines:
        ask = "\n".join(f"- {l}" for l in clarif_lines)
        parts.append("### ❓ Pour être plus précis\n" + ask)

    return "\n\n".join(parts)


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

        # Récup mémoire (tolérante)
        try:
            context: Dict[str, Any] = self.memory.get(sid) or {}
        except Exception as e:
            logger.warning("Lecture mémoire échouée (sid=%s): %s", sid, e)
            context = {}

        if language:
            context.setdefault("language", language)
        if user_id:
            context.setdefault("user_id", user_id)

        logger.info("🟦 DM.handle start | sid=%s | Q=%s", sid, _short(question, 260))

        # 1) Extraction de contexte
        extracted, score, missing = self.extractor.extract(question)
        context.update(extracted)

        # Déterminer si la question parle de poids → format en puces utile
        ui = context.setdefault("ui_prefs", {})
        ui["weight_only"] = bool(re.search(r"\b(poids|weight|body\s*weight)\b", (question or "").lower()))
        ui["format"] = "bullets" if ui["weight_only"] else ui.get("format", "auto")

        # BONUS : heuristique “broiler” si <30j & question poids (conserve comportement)
        self._apply_broiler_fallback(question, context)

        logger.info(
            "🟩 DM.extract | score=%.2f (seuil=%.2f) | missing=%s",
            score, COMPLETENESS_THRESHOLD, missing,
        )
        logger.debug("🟩 DM.context=%s", _short(context, 900))
        logger.debug("🟩 DM.ui_prefs=%s", ui)

        # 2) Très incomplet → demander directement des clarifications
        if score < 0.2:
            # Questions de clarification (toutes les manquantes)
            questions = self.clarifier.generate(missing)
            context["last_interaction"] = _utc_iso()
            self._safe_mem_update(sid, context)
            logger.info("🟨 DM.flow=clarification | questions=%d", len(questions or []))
            return {
                "type": "clarification",
                "questions": questions,
                "session_id": sid,
                "completeness_score": score,
                "missing_fields": missing,
            }

        # 3) Partiel (< seuil) → réponse générale courte + questions ciblées
        if score < COMPLETENESS_THRESHOLD:
            answer_text, sources = await self._generate_with_rag(
                question, context, style="minimal"
            )

            # Clarifications prioritaires (race/sexe)
            follow_up: List[str] = []
            critical_missing = [f for f in missing if f in CRITICAL_FIELDS]
            if critical_missing:
                # On force un wording unique et clair
                follow_up = [CLARIF_QUESTION]

            # Contexte / hypothèses résumé
            context_note = None
            if missing:
                human_missing = ", ".join(missing)
                context_note = f"Estimation générale (informations manquantes : {human_missing})."

            # Markdown structuré
            md = _compose_markdown(answer_text, context_note, follow_up)

            # UI card compacte
            bullets = _mk_bullets_from_text(answer_text or "", MAX_BULLET_LEN, max_items=3)
            card = build_card(
                headline="Réponse générale (à affiner)",
                bullets=bullets,
                footnote="Ajoute les précisions demandées pour une cible plus précise.",
                followups=follow_up,
                sources=sources,
            )

            # Payload classique + card
            resp_payload = format_response(md, sources)

            context["completed_at"] = _utc_iso()
            context["last_interaction"] = _utc_iso()
            self._safe_mem_update(sid, context)

            logger.info(
                "🟨 DM.flow=hybrid | text_len=%d | sources=%d | followups=%d",
                len(md or ""), len(sources or []), len(follow_up or []),
            )
            logger.debug("🟨 DM.ui_card.bullets=%s", bullets)

            return {
                "type": "answer",
                "response": resp_payload,    # ← markdown structuré
                "ui_card": card,             # ← card UI
                "session_id": sid,
                "completeness_score": score,
                "missing_fields": missing,
                "follow_up_questions": follow_up,
                "metadata": {"warning": "Réponse générale — précisions requises"},
            }

        # 4) Complet → réponse précise (RAG si possible), compacte
        answer_text, sources = await self._generate_with_rag(
            question, context, style="standard"
        )

        # Contexte/hypothèses (optionnel)
        context_note = None
        if extracted:
            # Petit résumé contextuel humain
            snippets = []
            if context.get("race") or context.get("breed"):
                snippets.append(f"lignée : {context.get('race') or context.get('breed')}")
            if context.get("sexe"):
                snippets.append(f"sexe : {context.get('sexe')}")
            if context.get("age_jours"):
                snippets.append(f"âge : {context.get('age_jours')} j")
            if snippets:
                context_note = "Contexte pris en compte : " + ", ".join(snippets) + "."

        # Markdown final (sans bloc “clarification”)
        md = _compose_markdown(answer_text, context_note, [])

        # UI card
        headline = (answer_text.split("\n", 1)[0] if answer_text else "Réponse").strip()[:90]
        bullets = _mk_bullets_from_text(answer_text or "", MAX_BULLET_LEN, max_items=3)
        card = build_card(
            headline=headline or "Réponse",
            bullets=bullets,
            footnote=None,
            followups=[],
            sources=sources,
        )

        resp_payload = format_response(md, sources)

        context["completed_at"] = _utc_iso()
        context["last_interaction"] = _utc_iso()
        self._safe_mem_update(sid, context)

        logger.info(
            "🟦 DM.flow=final | text_len=%d | sources=%d",
            len(md or ""), len(sources or []),
        )
        logger.debug("🟦 DM.ui_card.bullets=%s", bullets)

        return {
            "type": "answer",
            "response": resp_payload,  # ← markdown structuré
            "ui_card": card,           # ← card UI
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
        BONUS : Si la question concerne le poids et qu'on est <30 jours,
        et qu'aucune espèce/production_type n'est fournie, on force l'index Broiler.
        (Conserve le comportement antérieur.)
        """
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

    async def _generate_with_rag(self, question: str, context: Dict[str, Any], style: str = "standard") -> Tuple[str, List[Dict[str, Any]]]:
        def _call() -> Any:
            ui = (context or {}).get("ui_prefs") or {}
            logger.debug(
                "🔧 RAG.call | style=%s | output_format=%s | weight_only=%s",
                style, ui.get("format", "auto"), bool(ui.get("weight_only", False))
            )
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
            logger.debug(
                "🔧 RAG.ok | text_len=%d | sources=%d | source_flag=%s",
                len(answer_text or ""), len(sources or []), raw.get("source"),
            )
        else:
            answer_text = str(raw).strip()
            sources = []
            logger.debug("🔧 RAG.ok(simple) | text_len=%d", len(answer_text or ""))

        if not answer_text:
            answer_text = "Je n’ai pas pu formuler une réponse exploitable pour l’instant."
            logger.warning("⚠️ RAG réponse vide — fallback message injecté.")

        return (answer_text, sources)

    def _safe_mem_update(self, session_id: str, context: Dict[str, Any]) -> None:
        try:
            self.memory.update(session_id, context)
            logger.debug("💾 Mémoire mise à jour | sid=%s", session_id)
        except Exception as e:
            logger.warning("Échec update mémoire (sid=%s): %s", session_id, e)

    def _maybe_start_cleanup(self) -> None:
        cleanup_fn = getattr(self.memory, "cleanup_expired", None)
        if not callable(cleanup_fn):
            self._cleanup_enabled = False
            logger.debug("♻️ Cleanup mémoire désactivé (no-op).")
            return
        interval_min = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "30"))
        self._cleanup_enabled = True

        def _loop():
            import time
            logger.debug("♻️ Cleanup mémoire démarré | interval=%d min", interval_min)
            while True:
                try:
                    cleanup_fn()
                except Exception as e:
                    logger.debug("Cleanup mémoire: %s", e)
                time.sleep(max(300, interval_min * 60))

        threading.Thread(target=_loop, daemon=True).start()
