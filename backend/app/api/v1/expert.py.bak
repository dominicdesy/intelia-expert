# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)

# Import avec gestion d'erreurs robuste (code original conservé)
try:
    from .pipeline.dialogue_manager import handle
    DIALOGUE_AVAILABLE = True
    logger.info("✅ DialogueManager handle function imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import dialogue_manager.handle: {e}")
    DIALOGUE_AVAILABLE = False

    # Fonction fallback (code original conservé)
    def handle(session_id: str, question: str, lang: str = "fr") -> Dict[str, Any]:
        return {
            "type": "error",
            "message": "Dialogue service temporarily unavailable",
            "session_id": session_id
        }

router = APIRouter()

class AskPayload(BaseModel):
    # (code original) —
    session_id: Optional[str] = "default"
    question: str
    lang: Optional[str] = "fr"
    # ▼▼▼ NEW: overrides de test & debug (backward-compatible) ▼▼▼
    debug: Optional[bool] = False
    force_perfstore: Optional[bool] = False
    intent_hint: Optional[str] = None  # ex: "PerfTargets"

@router.post("/ask")
def ask(payload: AskPayload) -> Dict[str, Any]:
    """
    Endpoint principal pour poser des questions
    """
    try:
        logger.info(f"📝 Question reçue: {payload.question[:50]}...")

        # Appeler la fonction handle (code original + NEW kwargs)
        if DIALOGUE_AVAILABLE:
            result = handle(
                session_id=payload.session_id or "default",
                question=payload.question,
                lang=payload.lang or "fr",
                # ▼▼▼ NEW: propagation vers dialogue_manager ▼▼▼
                debug=bool(payload.debug),
                force_perfstore=bool(payload.force_perfstore),
                intent_hint=(payload.intent_hint or None),
            )
        else:
            # Fallback strict à la signature minimale (évite TypeError)
            logger.warning("⚠️ Dialogue manager not available, using fallback")
            result = handle(
                payload.session_id or "default",
                payload.question,
                payload.lang or "fr",
            )

        logger.info(f"✅ Réponse générée: type={result.get('type')}")
        return result

    except Exception as e:
        logger.exception(f"❌ Erreur dans /ask: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.post("/ask-public")
def ask_public(payload: AskPayload) -> Dict[str, Any]:
    """
    Endpoint public (même logique que /ask)
    """
    return ask(payload)

@router.get("/system-status")
def system_status() -> Dict[str, Any]:
    """
    Status du système dialogue
    """
    return {
        "status": "ok" if DIALOGUE_AVAILABLE else "degraded",
        "dialogue_manager_available": DIALOGUE_AVAILABLE,
        "service": "expert_api",
        "version": "1.0"
    }

@router.get("/debug")
def debug_imports() -> Dict[str, Any]:
    """
    Debug des imports pour diagnostiquer les problèmes
    """
    debug_info = {
        "dialogue_available": DIALOGUE_AVAILABLE,
        "imports_tested": []
    }

    # Test des imports individuels - CHEMINS CORRIGÉS (code original conservé)
    imports_to_test = [
        "app.api.v1.utils.question_classifier",
        "app.api.v1.pipeline.context_extractor",
        "app.api.v1.pipeline.clarification_manager",
        "app.api.v1.pipeline.rag_engine",
        "app.api.v1.utils.formulas",
        "app.api.v1.pipeline.intent_registry"
    ]

    for import_path in imports_to_test:
        try:
            __import__(import_path)
            debug_info["imports_tested"].append({"path": import_path, "status": "✅ OK"})
        except Exception as e:
            debug_info["imports_tested"].append({"path": import_path, "status": f"❌ Error: {e}"})

    return debug_info

@router.post("/force-import-test")
def force_import_test():
    """Test d'urgence pour diagnostiquer l'import dialogue_manager"""
    import traceback

    try:
        from .pipeline.dialogue_manager import handle
        test_result = handle("test", "test question", "fr", debug=True)
        return {
            "status": "✅ SUCCESS",
            "result": test_result,
            "import_successful": True
        }
    except Exception as e:
        return {
            "status": "❌ FAILED",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "import_successful": False
        }

@router.get("/perfstore-status")
def perfstore_status():
    try:
        from .pipeline.dialogue_manager import _get_perf_store  # type: ignore
        store = _get_perf_store("broiler")
        if not store:
            return {"ok": False, "reason": "PerfStore None"}
        root = getattr(store, "root", None); species = getattr(store, "species", None)
        lines = []
        for ln in ["ross308", "cobb500"]:
            try:
                df = store._load_df(ln)  # type: ignore
                lines.append({"line": ln, "rows": 0 if df is None else int(len(df))})
            except Exception as e:
                lines.append({"line": ln, "error": str(e)})
        return {"ok": True, "root": root, "species": species, "lines": lines}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    try:
        from .pipeline.dialogue_manager import _normalize_entities_soft, _get_perf_store, _perf_lookup_exact_or_nearest  # type: ignore
        q = (payload.question or "")
        # mini extraction d'âge pour debug
        import re
        m = re.search(r'(\d+)\s*(?:jour|jours|day|days)\b', q.lower())
        entities = {"species":"broiler"}
        if "ross" in q.lower(): entities["line"] = "ross308"
        if "cobb" in q.lower(): entities["line"] = "cobb500"
        if "male" in q.lower() or "mâle" in q.lower(): entities["sex"] = "male"
        if "female" in q.lower() or "femelle" in q.lower(): entities["sex"] = "female"
        if "as hatched" in q.lower() or "mixte" in q.lower(): entities["sex"] = "as_hatched"
        if m: entities["age_days"] = int(m.group(1))
        if "imperial" in q.lower(): entities["unit"] = "imperial"
        if "metric" in q.lower() or "métrique" in q.lower(): entities["unit"] = "metric"
        norm = _normalize_entities_soft(entities)
        store = _get_perf_store(norm["species"])
        if not store:
            return {"entities": entities, "norm": norm, "rec": None, "debug": {"note":"store=None"}}
        rec, dbg = _perf_lookup_exact_or_nearest(store, norm)
        return {"entities": entities, "norm": norm, "rec": rec, "debug": dbg}
    except Exception as e:
        return {"error": str(e)}
