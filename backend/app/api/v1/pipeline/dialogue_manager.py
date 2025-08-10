# app/api/v1/pipeline/dialogue_manager.py
from __future__ import annotations

import os
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime

try:
    import anyio
except Exception:
    anyio = None  # type: ignore

from ..utils.response_generator import format_response, build_card
from .context_extractor import ContextExtractor
from .clarification_manager import ClarificationManager
from .postgres_memory import PostgresMemory as ConversationMemory
from .rag_engine import RAGEngine
from .intent_registry import infer_intent, required_slots, derive_answer_mode, looks_numeric_first

# Compute utils (optionnels)
try:
    from app.api.v1.utils.formulas import (
        estimate_water_intake_l_per_1000,
        min_ventilation_m3h_per_kg,
        iep_broiler,
        cout_aliment_par_kg_vif,
        dimension_mangeoires,
        dimension_abreuvoirs,
        debit_tunnel_m3h,
        chaleur_a_extraire_w,
    )
except Exception:
    def estimate_water_intake_l_per_1000(*args, **kwargs): return (None, {})
    def min_ventilation_m3h_per_kg(*args, **kwargs): return (None, {})
    def iep_broiler(*args, **kwargs): return (None, {})
    def cout_aliment_par_kg_vif(*args, **kwargs): return (None, {})
    def dimension_mangeoires(*args, **kwargs): return (None, {})
    def dimension_abreuvoirs(*args, **kwargs): return (None, {})
    def debit_tunnel_m3h(*args, **kwargs): return (None, {})
    def chaleur_a_extraire_w(*args, **kwargs): return (None, {})

# Safety policy
try:
    from .policy.safety_rules import requires_vet_redirect
except Exception:
    def requires_vet_redirect(text: str) -> Optional[str]: return None

logger = logging.getLogger(__name__)
COMPLETENESS_THRESHOLD: float = float(os.getenv("COMPLETENESS_THRESHOLD", "0.60"))

def _utc_iso() -> str:
    return datetime.utcnow().isoformat()

class DialogueManager:
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
            logger.debug("Cleanup not started: %s", e)

    # ---------------- PUBLIC ---------------- #
    async def handle(
        self,
        session_id: Optional[str],
        question: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sid = session_id or str(uuid4())
        logger.info("🟦 DM.handle | sid=%s | Q=%s", sid, (question or "")[:160])

        # mémoire
        try:
            context: Dict[str, Any] = self.memory.get(sid) or {}
        except Exception:
            context = {}

        if language:
            context.setdefault("language", language)
        if user_id:
            context.setdefault("user_id", user_id)

        # policy
        vet_msg = requires_vet_redirect(question)
        if vet_msg:
            return {
                "type": "policy_redirect",
                "response": format_response(vet_msg),
                "session_id": sid,
                "completeness_score": 1.0,
                "missing_fields": [],
            }

        # extraction slots
        extracted, score, missing = self.extractor.extract(question)
        context.update(extracted)

        # intention universelle
        intent = infer_intent(question)
        context["last_intent"] = intent
        answer_mode = derive_answer_mode(intent)
        need_numeric = looks_numeric_first(intent)

        # champs requis dynamiques
        criticals = set(required_slots(intent))
        # défauts universels utiles
        if "sex" not in criticals:  # la plupart des réponses tolèrent 'sex' manquant
            criticals |= {"race"}  # lignée aide beaucoup
        if "age_days" in criticals and not any(context.get(k) for k in ["age_days", "age_jours"]):
            missing = list(set(list(missing) + ["age_days"]))
            score = min(score, 0.25)

        logger.info("🟩 DM.extract | intent=%s | score=%.2f | missing=%s", intent, score, missing)

        # forcing UI hints
        context.setdefault("ui_style", {})
        context["ui_style"].update({
            "style": "minimal" if need_numeric else "standard",
            "format": "bullets" if need_numeric else "auto",
            "weight_only": (intent == "targets.weight"),
        })
        context["prefer_tables"] = any(x in answer_mode for x in ["numeric", "numbers", "table"])

        # si complétude faible → clarifications
        if score < COMPLETENESS_THRESHOLD and score < 0.25:
            questions = self._clarifications_for(intent, missing)
            self._persist_context(sid, context)
            return {
                "type": "clarification",
                "questions": questions,
                "session_id": sid,
                "completeness_score": score,
                "missing_fields": missing,
            }

        # réponse hybride si incomplet mais exploitable
        if score < COMPLETENESS_THRESHOLD:
            answer_text, sources, metrics = await self._answer(question, context, intent)
            followups = self._clarifications_for(intent, missing, short=True)
            if followups:
                appendix = "\n".join(f"- {q}" for q in followups)
                answer_text = (answer_text + "\n\n❓ Pour être précis :\n" + appendix) if answer_text else ("❓ Pour être précis :\n" + appendix)
            self._persist_context(sid, context)
            return {
                "type": "answer",
                "response": {"answer": format_response(answer_text), "sources": sources},
                "session_id": sid,
                "completeness_score": score,
                "missing_fields": missing,
                "follow_up_questions": followups,
                "metadata": {"warning": "Réponse générale — informations partielles", **metrics},
            }

        # réponse complète
        answer_text, sources, metrics = await self._answer(question, context, intent)
        self._persist_context(sid, context)
        return {
            "type": "answer",
            "response": {"answer": format_response(answer_text), "sources": sources},
            "session_id": sid,
            "completeness_score": score,
            "missing_fields": missing,
            "metadata": metrics,
        }

    # -------------- internals -------------- #
    async def _answer(self, question: str, context: Dict[str, Any], intent: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        # Compute-first pour certaines intentions
        try:
            if intent == "water.intake":
                age = context.get("age_days") or context.get("age_jours")
                amb = context.get("ambient_c") or context.get("temperature")
                val, _ = estimate_water_intake_l_per_1000(age_days=age, ambient_c=amb, species=context.get("species"))
                if val is not None:
                    return (f"~{int(round(val))} L/j/1000 oiseaux\n- Âge: {age or 'n/a'} j\n- T° amb.: {amb if amb is not None else '20'}°C",
                            [], {"documents_used": 0, "inferred_species": context.get("species")})

            if intent == "environment.min_vent":
                age = context.get("age_days") or context.get("age_jours")
                avg_bw_g = context.get("poids_moyen_g")
                per_kg, _ = min_ventilation_m3h_per_kg(age_days=age, avg_bw_g=avg_bw_g)
                if per_kg is not None:
                    return (f"Ventilation minimale estimée: ~{per_kg:.2f} m³/h/kg (ajuster selon T°, NH₃/CO₂).",
                            [], {"documents_used": 0, "inferred_species": context.get("species")})

            if intent == "kpi.iep":
                liv = context.get("livability_pct")
                bwkg = (context.get("poids_moyen_g") or 0) / 1000.0 if context.get("poids_moyen_g") else context.get("avg_weight_kg")
                fcr = context.get("fcr")
                age = context.get("age_days") or context.get("age_jours")
                val, _ = iep_broiler(livability_pct=liv, avg_weight_kg=bwkg, fcr=fcr, age_days=age)
                if val is not None:
                    return (f"IEP ≈ {val:.2f}\n- Âge: {age} j\n- BW: {bwkg or 'n/a'} kg\n- FCR: {fcr or 'n/a'}\n- Survie: {liv if liv is not None else 'n/a'}%",
                            [], {"documents_used": 0, "inferred_species": "broiler"})

            if intent == "cost.feed":
                price = context.get("prix_aliment_tonne_eur")
                fcr = context.get("fcr")
                val, _ = cout_aliment_par_kg_vif(prix_aliment_tonne_eur=price, fcr=fcr)
                if val is not None:
                    return (f"Coût aliment estimé: ~{val:.3f} €/kg vif (FCR={fcr}, prix={price} €/t).",
                            [], {"documents_used": 0, "inferred_species": context.get("species")})

            if intent == "feeding.chain.calibration":
                eff = context.get("effectif")
                age = context.get("age_days") or context.get("age_jours")
                typ = context.get("type_mangeoire") or "chaine"
                res, _ = dimension_mangeoires(effectif=eff, age_days=age, type_=typ)
                if res:
                    if res["type"] == "chaine":
                        txt = f"Mangeoires chaîne: {res['cm_per_bird']} cm/oiseau → total ~{int(round(res['total_cm_required']))} cm."
                    else:
                        txt = f"Assiettes: {res['birds_per_pan']} oiseaux/assiette → ~{res['pans_required']} assiettes."
                    return (txt, [], {"documents_used": 0, "inferred_species": context.get("species")})

            if intent == "equipment.nipples.setup":
                eff = context.get("effectif")
                age = context.get("age_days") or context.get("age_jours")
                typ = context.get("type_abreuvoir") or "nipple"
                res, _ = dimension_abreuvoirs(effectif=eff, age_days=age, type_=typ)
                if res:
                    if res["type"] == "nipple":
                        txt = f"Nipples: {res['birds_per_point']} oiseaux/point → ~{res['points_required']} points d’eau."
                    else:
                        txt = f"Cloches: {res['birds_per_bell']} oiseaux/cloche → ~{res['bells_required']} cloches."
                    return (txt, [], {"documents_used": 0, "inferred_species": context.get("species")})

            if intent == "stocking.density":
                # se repose sur RAG (règles/labels). Pas de compute ici.
                pass
        except Exception as e:
            logger.debug("compute-first error: %s", e)

        # sinon RAG
        def _call() -> Any:
            return self.rag.generate_answer(question, context)

        try:
            raw = await anyio.to_thread.run_sync(_call) if anyio else _call()
        except Exception as e:
            logger.exception("RAG generate_answer error: %s", e)
            return ("Désolé, une erreur est survenue.", [], {"documents_used": 0})

        if isinstance(raw, dict):
            answer_text = (raw.get("response") or "").strip() or "Désolé, je n’ai pas pu formater la réponse."
            sources = self._normalize_sources(raw.get("sources") or raw.get("citations") or raw.get("source"))
            meta = {
                "documents_used": int(raw.get("documents_used") or 0),
                "inferred_species": raw.get("inferred_species"),
            }
        else:
            answer_text = str(raw).strip() or "Désolé, je n’ai pas pu formater la réponse."
            sources, meta = [], {"documents_used": 0}

        return (answer_text, sources, meta)

    def _clarifications_for(self, intent: str, missing: List[str], short: bool = False) -> List[str]:
        # Clarifications minimales génériques
        q: List[str] = []
        req = set(required_slots(intent))
        # mapping simple FR
        label = {
            "species": "espèce (broiler, pondeuse)",
            "line": "lignée/génétique (Ross, Cobb, Hubbard…)",
            "sex": "sexe (mâle, femelle, mixte)",
            "age_days": "âge en jours",
            "phase": "phase (starter, grower, finisher)",
            "temp_outside": "température extérieure (°C)",
            "effectif": "effectif du lot",
            "jurisdiction": "zone (FR/UE/…)",
            "label": "label (Label Rouge, Bio…)",
        }
        for k in missing:
            if k in req or (not short and k in label):
                q.append(f"Quelle est {label.get(k, k)} ?")
        return q[:2] if short else q[:4]

    def _normalize_sources(self, raw: Any) -> List[Dict[str, Any]]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [s if isinstance(s, dict) else {"source": str(s)} for s in raw]
        if isinstance(raw, dict):
            return [raw]
        return [{"source": str(raw)}]

    def _persist_context(self, sid: str, ctx: Dict[str, Any]) -> None:
        try:
            ctx["last_interaction"] = _utc_iso()
            self.memory.update(sid, ctx)
        except Exception as e:
            logger.debug("Mem update failed: %s", e)

    def _maybe_start_cleanup(self) -> None:
        cleanup_fn = getattr(self.memory, "cleanup_expired", None)
        if not callable(cleanup_fn):
            return
        import time
        def _loop():
            while True:
                try:
                    cleanup_fn()
                except Exception as e:
                    logger.debug("Cleanup mémoire: %s", e)
                time.sleep(max(300, int(os.getenv("CLEANUP_INTERVAL_MINUTES", "30")) * 60))
        threading.Thread(target=_loop, daemon=True).start()
