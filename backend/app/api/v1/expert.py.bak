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



@router.get("/test-basic")
def test_basic():
    """Test ultra-basique sans aucune dépendance"""
    return {"status": "ok", "message": "Basic endpoint works"}
    
    
    
    
# ============================
# [PATCH] /perf-probe robuste & JSON-safe avec imports protégés
# ============================
@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    """Version qui préserve les bonnes valeurs et nettoie seulement les NaN/inf"""
    import math
    import numpy as np
    
    def clean_for_json(value):
        """Nettoie seulement les valeurs problématiques pour JSON"""
        if value is None:
            return None
        if isinstance(value, (int, str, bool)):
            return value
        if isinstance(value, float):
            # Garde les vraies valeurs float, nettoie seulement NaN/inf
            if math.isnan(value) or math.isinf(value):
                return None
            return float(value)  # Assure que c'est un float Python standard
        if hasattr(value, 'item'):  # numpy scalars
            val = value.item()
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return None
            return val
        return value
    
    def clean_dict_for_json(obj):
        """Nettoie récursivement seulement les valeurs problématiques"""
        if isinstance(obj, dict):
            return {k: clean_dict_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_dict_for_json(v) for v in obj]
        else:
            return clean_for_json(obj)
    
    try:
        from .pipeline.perf_store import PerfStore
        
        # Parse des entités de base
        entities_in = (payload.entities or {}) if payload else {}
        line = entities_in.get("line", "cobb500")
        sex = entities_in.get("sex", "male") 
        unit = entities_in.get("unit", "metric")
        age_days = entities_in.get("age_days", 21)
        
        store = PerfStore(root=os.environ.get("RAG_INDEX_ROOT", "./rag_index"), species="broiler")
        rec = store.get(line=line, sex=sex, unit=unit, age_days=int(age_days))
        
        # Nettoie pour JSON en préservant les vraies valeurs
        result = {
            "success": True,
            "entities": {"line": line, "sex": sex, "unit": unit, "age_days": age_days},
            "rec": clean_dict_for_json(rec) if rec else None,
            "message": "Performance data found" if rec else "No data found for these parameters"
        }
        
        return jsonable_encoder(result)
        
    except Exception as e:
        return jsonable_encoder({
            "success": False,
            "error": str(e),
            "message": "Error retrieving performance data"
        })