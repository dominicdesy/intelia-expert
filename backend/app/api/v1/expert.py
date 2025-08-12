# app/api/v1/expert.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder  # [PATCH] JSON-safe responses
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# ===== Import Dialogue Manager (préserve le code original) =====
try:
    from .pipeline.dialogue_manager import handle  # type: ignore
    DIALOGUE_AVAILABLE = True
    logger.info("✅ DialogueManager handle function imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import dialogue_manager.handle: {e}")
    DIALOGUE_AVAILABLE = False

    # Fallback minimal, signature d'origine conservée
    def handle(session_id: str, question: str, lang: str = "fr", **kwargs) -> Dict[str, Any]:
        return {
            "type": "error",
            "message": "Dialogue service temporarily unavailable",
            "session_id": session_id,
        }

# ===== Schémas =====
class AskPayload(BaseModel):
    # (code original)
    session_id: Optional[str] = "default"
    question: str
    lang: Optional[str] = "fr"
    # (déjà présents dans certaines branches)
    debug: Optional[bool] = False
    force_perfstore: Optional[bool] = False
    intent_hint: Optional[str] = None
    # [PATCH] pass-through des entités
    entities: Dict[str, Any] = Field(default_factory=dict)

    # rétro‑compat : accepter des champs inconnus
    model_config = {"extra": "allow"}

# ===== Endpoints =====
@router.post("/ask")
def ask(payload: AskPayload, request: Request) -> Dict[str, Any]:
    """
    Endpoint principal pour poser des questions (préserve la logique existante).
    """
    try:
        logger.info(f"📝 Question reçue: {payload.question[:120]}")

        # [PATCH] support du flag via query string (?force_perfstore=1)
        fp_qs = request.query_params.get("force_perfstore")
        force_perf = bool(payload.force_perfstore) or (fp_qs in ("1", "true", "True", "yes"))

        if DIALOGUE_AVAILABLE:
            result = handle(
                session_id=payload.session_id or "default",
                question=payload.question,
                lang=payload.lang or "fr",
                debug=bool(payload.debug),
                force_perfstore=force_perf,
                intent_hint=(payload.intent_hint or None),
                entities=(payload.entities or {}),
            )
        else:
            logger.warning("⚠️ Dialogue manager not available, using fallback")
            result = handle(payload.session_id or "default", payload.question, payload.lang or "fr")

        logger.info(f"✅ Réponse générée: type={result.get('type')}")
        return result
    except Exception as e:
        logger.exception("❌ Erreur dans /ask")
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

@router.post("/ask-public")
def ask_public(payload: AskPayload, request: Request) -> Dict[str, Any]:
    """
    Endpoint public (même logique que /ask).
    """
    return ask(payload, request)

@router.get("/system-status")
def system_status() -> Dict[str, Any]:
    """
    État synthétique du service.
    """
    return {
        "status": "ok" if DIALOGUE_AVAILABLE else "degraded",
        "dialogue_manager_available": DIALOGUE_AVAILABLE,
        "service": "expert_api",
    }

@router.get("/debug")
def debug_imports() -> Dict[str, Any]:
    """
    Vérifie quelques imports utiles (préserve le comportement original).
    """
    debug_info: Dict[str, Any] = {"dialogue_available": DIALOGUE_AVAILABLE, "imports_tested": []}
    imports_to_test: List[str] = [
        "app.api.v1.utils.question_classifier",
        "app.api.v1.pipeline.context_extractor",
        "app.api.v1.pipeline.clarification_manager",
        "app.api.v1.pipeline.rag_engine",
        "app.api.v1.utils.formulas",
        "app.api.v1.pipeline.intent_registry",
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
    """
    Teste l'import et un appel basique de handle() sans casser l'API.
    """
    import traceback
    try:
        from .pipeline.dialogue_manager import handle as _handle  # type: ignore
        test_result = _handle("test", "test question", "fr", debug=True)
        return {"status": "✅ SUCCESS", "result": test_result, "import_successful": True}
    except Exception as e:
        return {
            "status": "❌ FAILED",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "import_successful": False,
        }

@router.get("/perfstore-status")
def perfstore_status():
    """
    Expose quelques infos sur le PerfStore (ne jette pas d'exception).
    """
    try:
        from .pipeline.dialogue_manager import _get_perf_store  # type: ignore
        store = _get_perf_store("broiler")
        if not store:
            return {"ok": False, "reason": "PerfStore None"}
        root = getattr(store, "root", None)
        species = getattr(store, "species", None)
        tables_dir = str(getattr(store, "dir_tables", "")) if getattr(store, "dir_tables", None) else None

        lines = []
        for ln in ["ross308", "cobb500"]:
            try:
                df = store._load_df(ln)  # type: ignore
                lines.append({"line": ln, "rows": 0 if df is None else int(len(df))})
            except Exception as e:
                lines.append({"line": ln, "error": str(e)})

        # [PATCH] stringifier root pour éviter des types non JSON
        return {
            "ok": True,
            "root": str(root) if root is not None else None,  # [PATCH]
            "species": species,
            "tables_dir": tables_dir,
            "lines": lines,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============================
# [PATCH] /perf-probe robuste & JSON-safe
# ============================
@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    """
    Diagnostic PerfStore : renvoie TOUJOURS un JSON sérialisable (pas de 500).
    - Normalisation des entités (species/line/sex/unit/age_days)
    - Lignes disponibles, colonnes, nb de lignes et tables_dir
    - Enregistrement trouvé (rec) avec fallback nearest si nécessaire
    """
    import re as _re
    try:
        # Imports à l'intérieur pour ne pas casser le module si PerfStore est HS
        from .pipeline.dialogue_manager import _normalize_entities_soft  # type: ignore
        from .pipeline.perf_store import PerfStore  # type: ignore

        q = (payload.question or "") if payload else ""
        ql = q.lower()

        entities_in = (payload.entities or {}) if (payload and payload.entities is not None) else {}
        species = (entities_in.get("species") or "broiler").lower()
        line = entities_in.get("line")
        if not line:
            if "cobb" in ql:
                line = "cobb500"
            elif "ross" in ql:
                line = "ross308"

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
                try:
                    age_days = int(m.group(1))
                except Exception:
                    age_days = None

        # Normalisation centralisée (préserve la logique originale)
        norm = _normalize_entities_soft(
            {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}
        )

        # Instanciation PerfStore (autodétection tables_dir dans PerfStore)
        store = PerfStore(root=os.environ.get("RAG_INDEX_ROOT", "./rag_index"), species=norm["species"])
        try:
            available = store.available_lines()
        except Exception:
            available = []

        # Ligne non déterminée → retour explicite (JSON-safe)
        if not norm.get("line"):
            out = {
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "missing_line",
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                },
            }
            return jsonable_encoder(out, exclude_none=True)  # [PATCH]

        # Charge DF de la lignée
        df = store._load_df(norm["line"])
        if df is None:
            out = {
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "table_missing",
                    "line": norm.get("line"),
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                },
            }
            return jsonable_encoder(out, exclude_none=True)  # [PATCH]

        # Lookup exact -> nearest (logique dans PerfStore.get)
        try:
            rec = store.get(
                line=norm["line"],
                sex=norm["sex"],
                unit=norm["unit"],
                age_days=int(norm.get("age_days") or 0),
            )
        except Exception:
            rec = None

        dbg = {
            "rows": int(len(df)),
            "columns": [str(c) for c in df.columns],
            "available_lines": available,
            "tables_dir": str(getattr(store, "dir_tables", "")),
        }

        out = {
            "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
            "norm": norm,
            "rec": rec,
            "debug": dbg,
        }
        return jsonable_encoder(out, exclude_none=True)  # [PATCH]

    except Exception as e:
        # Ne jamais renvoyer une 500 : toujours un JSON sérialisable
        out = {"error": "internal", "message": str(e)}
        return jsonable_encoder(out, exclude_none=True)  # [PATCH]
