# app/api/v1/expert.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder  # [PATCH] JSON-safe responses
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import logging
import os
import re

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

# ===== Fonction locale pour normalisation des entités =====
def _normalize_entities_soft_local(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Version locale de normalisation des entités"""
    result = {}
    
    # Species
    species = (entities.get("species") or "broiler").lower()
    result["species"] = species
    
    # Line
    line = entities.get("line")
    if line:
        line = re.sub(r"[-_\s]+", "", str(line).lower())
    result["line"] = line
    
    # Sex
    sex = entities.get("sex")
    if sex:
        sex_mapping = {
            "male": "male", "m": "male", "♂": "male",
            "female": "female", "f": "female", "♀": "female", 
            "as_hatched": "as_hatched", "ah": "as_hatched", 
            "mixte": "as_hatched", "mixed": "as_hatched",
            "as hatched": "as_hatched", "as-hatched": "as_hatched"
        }
        sex = sex_mapping.get(str(sex).lower().replace(" ", "_"), sex)
    result["sex"] = sex
    
    # Unit
    unit = entities.get("unit")
    if unit and str(unit).lower() in ["imperial", "imp", "us", "lb", "lbs"]:
        unit = "imperial"
    else:
        unit = "metric"
    result["unit"] = unit
    
    # Age
    age_days = entities.get("age_days")
    if age_days is not None:
        try:
            result["age_days"] = int(age_days)
        except:
            result["age_days"] = None
    else:
        result["age_days"] = None
    
    return result

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
# [PATCH] /perf-probe robuste & JSON-safe avec imports protégés
# ============================
@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    """
    Version ultra-défensive pour diagnostiquer exactement où ça plante
    """
    try:
        # [STEP 1] Imports protégés
        try:
            from .pipeline.perf_store import PerfStore  # type: ignore
            step1_ok = True
        except Exception as e:
            return jsonable_encoder({
                "error": "step1_import_failed", 
                "message": str(e),
                "step": "import PerfStore"
            })

        # [STEP 2] Parsing payload
        try:
            q = (payload.question or "") if payload else ""
            entities_in = (payload.entities or {}) if (payload and payload.entities is not None) else {}
            step2_ok = True
        except Exception as e:
            return jsonable_encoder({
                "error": "step2_payload_failed",
                "message": str(e),
                "step": "parse payload"
            })

        # [STEP 3] Normalisation locale des entités
        try:
            norm = _normalize_entities_soft_local(
                {"species": "broiler", "line": "cobb500", "sex": "male", "age_days": 21, "unit": "metric"}
            )
            step3_ok = True
        except Exception as e:
            return jsonable_encoder({
                "error": "step3_normalize_failed",
                "message": str(e),
                "step": "normalize entities"
            })

        # [STEP 4] Instanciation PerfStore
        try:
            store = PerfStore(root=os.environ.get("RAG_INDEX_ROOT", "./rag_index"), species="broiler")
            step4_ok = True
        except Exception as e:
            return jsonable_encoder({
                "error": "step4_perfstore_init_failed",
                "message": str(e),
                "step": "PerfStore init",
                "rag_root": os.environ.get("RAG_INDEX_ROOT", "./rag_index")
            })

        # [STEP 5] available_lines
        try:
            available = store.available_lines()
            step5_ok = True
        except Exception as e:
            return jsonable_encoder({
                "error": "step5_available_lines_failed",
                "message": str(e),
                "step": "available_lines"
            })

        # [STEP 6] _load_df avec protection maximale
        try:
            df = store._load_df("cobb500")
            if df is None:
                return jsonable_encoder({
                    "error": "step6_load_df_returned_none",
                    "step": "load_df returned None",
                    "available_lines": available
                })
            step6_ok = True
            df_info = {
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
            }
        except Exception as e:
            return jsonable_encoder({
                "error": "step6_load_df_failed",
                "message": str(e),
                "step": "_load_df('cobb500')",
                "available_lines": available
            })

        # [STEP 7] store.get avec protection
        try:
            rec = store.get(line="cobb500", sex="male", unit="metric", age_days=21)
            step7_ok = True
        except Exception as e:
            return jsonable_encoder({
                "error": "step7_store_get_failed",
                "message": str(e),
                "step": "store.get",
                "df_info": df_info
            })

        # [SUCCESS] Tout a marché
        return jsonable_encoder({
            "status": "success",
            "steps_completed": [
                "import", "payload", "normalize", 
                "perfstore_init", "available_lines", 
                "load_df", "store_get"
            ],
            "available_lines": available,
            "df_info": df_info,
            "rec": rec,
            "message": "All steps completed successfully"
        })

    except Exception as e:
        # Catch-all final
        return jsonable_encoder({
            "error": "unexpected_error",
            "message": str(e),
            "step": "unknown"
        })


