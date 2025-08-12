# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
import logging
import os  # [PATCH]

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
    # (code original)
    session_id: Optional[str] = "default"
    question: str
    lang: Optional[str] = "fr"
    # NEW: debug & overrides (déjà présents dans certaines branches)
    debug: Optional[bool] = False
    force_perfstore: Optional[bool] = False
    intent_hint: Optional[str] = None  # ex: "PerfTargets"
    # [PATCH] NEW: entities pass-through (facultatif)
    entities: Dict[str, Any] = Field(default_factory=dict)

    # Tolérance aux champs inconnus (retro-compat)
    model_config = {"extra": "allow"}

@router.post("/ask")
def ask(payload: AskPayload, request: Request) -> Dict[str, Any]:
    """
    Endpoint principal pour poser des questions
    """
    try:
        logger.info(f"📝 Question reçue: {payload.question[:80]}...")

        # Prise en charge optionnelle du flag via query string (?force_perfstore=1)
        fp_qs = request.query_params.get("force_perfstore")
        force_perf = bool(payload.force_perfstore) or (fp_qs in ("1", "true", "True", "yes"))

        # Appeler la fonction handle (code original + propagation des nouveaux kwargs)
        if DIALOGUE_AVAILABLE:
            result = handle(
                session_id=payload.session_id or "default",
                question=payload.question,
                lang=payload.lang or "fr",
                debug=bool(payload.debug),
                force_perfstore=force_perf,
                intent_hint=(payload.intent_hint or None),
                entities=(payload.entities or {}),  # [PATCH] pass-through
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
def ask_public(payload: AskPayload, request: Request) -> Dict[str, Any]:
    """
    Endpoint public (même logique que /ask)
    """
    return ask(payload, request)

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
        return {
            "ok": True,
            "root": str(root) if root else None,
            "species": species,
            "tables_dir": str(getattr(store, "dir_tables", "")),
            "lines": lines
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================
# [PATCH] /perf-probe robuste
# ============================
@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    """
    Debug léger PerfStore: renvoie toujours un JSON sérialisable (pas d'exception 500).
    Donne la normalisation, la ligne détectée, les colonnes, le nombre de lignes,
    les lignes disponibles et la table_dir effective.
    """
    import traceback
    import re as _re
    try:
        # Imports locaux pour éviter d'échouer au chargement du module
        from .pipeline.dialogue_manager import _normalize_entities_soft  # reuse de la normalisation existante
        from .pipeline.perf_store import PerfStore  # classe PerfStore

        q = (payload.question or "") if payload else ""
        ql = q.lower()

        # Détecter espèces/ligne depuis payload.entities puis question
        entities_in = (payload.entities or {}) if payload and payload.entities is not None else {}
        species = (entities_in.get("species") or "broiler").lower()
        line = entities_in.get("line")
        if not line:
            if "cobb" in ql: line = "cobb500"
            elif "ross" in ql: line = "ross308"

        # Détection légère du sexe / unité / âge depuis la question si absent
        sex = entities_in.get("sex")
        if not sex:
            if ("as hatched" in ql) or ("as-hatched" in ql) or ("mixte" in ql) or (" ah " in ql):
                sex = "as_hatched"
            elif ("male" in ql) or ("mâle" in ql):
                sex = "male"
            elif ("female" in ql) or ("femelle" in ql):
                sex = "female"

        unit = entities_in.get("unit")
        if not unit:
            if ("metric" in ql) or ("métrique" in ql):
                unit = "metric"
            elif "imperial" in ql:
                unit = "imperial"

        age_days = entities_in.get("age_days")
        if age_days is None:
            m = _re.search(r"(\d+)\s*(?:j|jour|jours|d|day|days)\b", ql)
            if m:
                try: age_days = int(m.group(1))
                except Exception: age_days = None

        # Normalisation canonique
        norm = _normalize_entities_soft({
            "species": species,
            "line": line,
            "sex": sex,
            "age_days": age_days,
            "unit": unit,
        })

        # Instanciation du store (avec autodétection de tables_dir dans PerfStore)
        store = PerfStore(root=os.environ.get("RAG_INDEX_ROOT","./rag_index"), species=norm["species"])
        try:
            available = store.available_lines()
        except Exception:
            available = []

        # Si la lignée n'est pas déterminée, retourne l'info utile
        if not norm.get("line"):
            return {
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "missing_line",
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                }
            }

        # Charger la table ligne → DataFrame (pas de retour non sérialisable)
        df = store._load_df(norm["line"])
        if df is None:
            return {
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "table_missing",
                    "line": norm.get("line"),
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                }
            }

        # Lookup via PerfStore.get (exact puis nearest côté store)
        try:
            rec = store.get(
                line=norm["line"],
                sex=norm["sex"],
                unit=norm["unit"],
                age_days=int(norm.get("age_days") or 0)
            )
        except Exception as e:
            rec = None

        # Debug sérialisable seulement
        dbg = {
            "rows": int(len(df)),
            "columns": [str(c) for c in df.columns],
            "available_lines": available,
            "tables_dir": str(getattr(store, "dir_tables", "")),
        }

        return {
            "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
            "norm": norm,
            "rec": rec,
            "debug": dbg
        }

    except Exception as e:
        # Jamais de 500: on renvoie un JSON explicite
        return {
            "error": "internal",
            "message": str(e),
            "trace": traceback.format_exc()[:2000]
        }
