# app/api/v1/expert.py
# -*- coding: utf-8 -*-
"""
API Expert - Endpoints principaux
Fichier principal conservant la compatibilité complète
Utilise les modules expert_core, expert_confidence et expert_utils
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import logging
import time
import asyncio

# 🔒 Import authentification
from app.api.v1.auth import get_current_user

# Import des modules refactorisés
from .expert_core import (
    ask_internal_async,
    get_system_status,
    get_agricultural_validation_status,
    validate_agricultural_question_safe,
    DIALOGUE_AVAILABLE,
    AGRICULTURAL_VALIDATOR_AVAILABLE
)

from .expert_utils import (
    get_cached_store,
    normalize_entities_soft_local,
    extract_age_from_text,
    clean_dict_for_json,
    jsonable_encoder
)

from .expert_confidence import (
    test_confidence_system_async,
    get_confidence_examples,
    get_perfstore_confidence,
    CONFIDENCE_SYSTEM_AVAILABLE
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ===== Schémas =====
class AskPayload(BaseModel):
    session_id: Optional[str] = "default"
    question: str
    lang: Optional[str] = "fr"
    debug: Optional[bool] = False
    force_perfstore: Optional[bool] = False
    intent_hint: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    bypass_validation: Optional[bool] = False
    model_config = {"extra": "allow"}

# ===== Endpoints principaux =====

@router.post("/ask")
async def ask(
    payload: AskPayload, 
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🚀 ENDPOINT OPTIMISÉ + CONFIDENCE UNIFIÉ
    Poser des questions avec validation agricole, quota, persistance et confidence score.
    """
    return await ask_internal_async(payload, request, current_user)

@router.post("/ask-public")
async def ask_public(payload: AskPayload, request: Request) -> Dict[str, Any]:
    """
    🚀 ENDPOINT PUBLIC OPTIMISÉ + CONFIDENCE UNIFIÉ
    Pas d'authentification requise
    """
    return await ask_internal_async(payload, request, None)

@router.get("/system-status")
def system_status() -> Dict[str, Any]:
    """État synthétique du service avec info persistance et confidence."""
    return get_system_status()

# ===== 🎯 Endpoints Confidence System =====

@router.get("/confidence-status")
def confidence_status() -> Dict[str, Any]:
    """Status détaillé du système de confidence unifié."""
    try:
        from .pipeline.dialogue_manager import get_fallback_status
        dialogue_status = get_fallback_status()
        
        return {
            "ok": True,
            "root": str(root) if root is not None else None,
            "species": species,
            "tables_dir": tables_dir,
            "lines": lines,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/test-basic")
def test_basic():
    """Test ultra-basique sans aucune dépendance"""
    return {"status": "ok", "message": "Basic endpoint works", "modular_architecture": True}

# ===== PerfStore Probe (endpoint conservé) =====

@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    """
    Version fusionnée complète:
    - Extraction automatique des entités depuis la question
    - Nettoyage JSON des valeurs NaN/inf 
    - Diagnostics complets avec fallbacks
    - Messages d'erreur informatifs
    - Confidence score intégré
    """
    try:
        # [STEP 1] Import PerfStore protégé
        try:
            from .pipeline.perf_store import PerfStore
        except ImportError as e:
            return jsonable_encoder({
                "error": "import_failed", 
                "message": f"Failed to import PerfStore: {str(e)}",
                "entities": (payload.entities or {}) if payload else {},
                "confidence": get_perfstore_confidence(False)
            })

        # [STEP 2] Parsing de la question et des entités
        q = (payload.question or "") if payload else ""
        ql = q.lower()
        entities_in = (payload.entities or {}) if (payload and payload.entities is not None) else {}
        
        # Species
        species = (entities_in.get("species") or "broiler").lower()
        
        # Line (avec extraction automatique)
        line = entities_in.get("line")
        if not line:
            if "cobb" in ql:
                line = "cobb500"
            elif "ross" in ql:
                line = "ross308"

        # Sex (avec extraction automatique)
        sex = entities_in.get("sex")
        if not sex:
            if ("as hatched" in ql) or ("as-hatched" in ql) or ("mixte" in ql) or (" ah " in ql):
                sex = "as_hatched"
            elif ("male" in ql) or ("mâle" in ql):
                sex = "male"
            elif ("female" in ql) or ("femelle" in ql):
                sex = "female"

        # Unit (avec extraction automatique)
        unit = entities_in.get("unit")
        if not unit:
            if ("metric" in ql) or ("métrique" in ql):
                unit = "metric"
            elif "imperial" in ql:
                unit = "imperial"

        # Age (avec extraction améliorée)
        age_days = entities_in.get("age_days")
        if age_days is None:
            age_days = extract_age_from_text(ql)

        # [STEP 3] Validation des paramètres
        if age_days and (age_days < 1 or age_days > 70):
            return jsonable_encoder({
                "error": "invalid_age", 
                "message": f"Age must be between 1-70 days, got {age_days}",
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "confidence": get_perfstore_confidence(False)
            })

        # [STEP 4] Normalisation des entités
        norm = normalize_entities_soft_local(
            {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}
        )

        # [STEP 5] Instanciation PerfStore (avec cache)
        try:
            store = get_cached_store(norm["species"])
            if not store:
                return jsonable_encoder({
                    "error": "perfstore_init_failed",
                    "message": "Failed to initialize PerfStore",
                    "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                    "norm": norm,
                    "confidence": get_perfstore_confidence(False)
                })
            available = store.available_lines()
        except Exception as e:
            return jsonable_encoder({
                "error": "perfstore_init_failed",
                "message": f"Failed to initialize PerfStore: {str(e)}",
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "confidence": get_perfstore_confidence(False)
            })

        # [STEP 6] Vérification ligne disponible
        if not norm.get("line"):
            return jsonable_encoder({
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "missing_line",
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                    "message": f"Line not specified. Available: {', '.join(available)}"
                },
                "confidence": get_perfstore_confidence(False)
            })

        # [STEP 7] Chargement DataFrame
        try:
            df = store._load_df(norm["line"])
        except Exception as e:
            return jsonable_encoder({
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "load_df_failed",
                    "message": str(e),
                    "line": norm.get("line"),
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                },
                "confidence": get_perfstore_confidence(False)
            })

        if df is None:
            return jsonable_encoder({
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "rec": None,
                "debug": {
                    "error": "table_missing",
                    "line": norm.get("line"),
                    "available_lines": available,
                    "tables_dir": str(getattr(store, "dir_tables", "")),
                    "message": f"No data table found for line {norm.get('line')}"
                },
                "confidence": get_perfstore_confidence(False)
            })

        # [STEP 8] Récupération des données avec nettoyage JSON
        try:
            rec = store.get(
                line=norm["line"],
                sex=norm["sex"],
                unit=norm["unit"],
                age_days=int(norm.get("age_days") or 21),
            )
            
            # Nettoyage JSON des valeurs
            rec_clean = clean_dict_for_json(rec) if rec else None
            
        except Exception as e:
            return jsonable_encoder({
                "error": "store_get_failed",
                "message": str(e),
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
                "debug": {
                    "rows": int(len(df)),
                    "columns": [str(c) for c in df.columns],
                    "available_lines": available,
                },
                "confidence": get_perfstore_confidence(False)
            })

        # [SUCCESS] Résultat final avec message informatif + confidence
        success_message = "Performance data found"
        has_data = bool(rec_clean)
        
        if not rec_clean:
            line_name = norm.get("line", "unknown")
            sex_name = norm.get("sex", "unknown") 
            age_val = norm.get("age_days", "unknown")
            success_message = f"No data found for {line_name}, {sex_name}, {age_val} days. Try: male/female/as_hatched, ages 1-49"

        result = {
            "success": has_data,
            "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
            "norm": norm,
            "rec": rec_clean,
            "debug": {
                "rows": int(len(df)),
                "columns": [str(c) for c in df.columns],
                "available_lines": available,
                "tables_dir": str(getattr(store, "dir_tables", "")),
            },
            "message": success_message,
            "confidence": get_perfstore_confidence(has_data)
        }
        
        return jsonable_encoder(result)

    except Exception as e:
        # Catch-all final avec informations de debug + confidence
        return jsonable_encoder({
            "error": "internal_error",
            "message": str(e),
            "entities": (payload.entities or {}) if payload else {},
            "debug": {"step": "unknown", "error_type": type(e).__name__},
            "confidence": get_perfstore_confidence(False)
                    "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,
            "unified_confidence_module": CONFIDENCE_SYSTEM_AVAILABLE,
            "dialogue_manager_confidence_integration": dialogue_status.get("unified_confidence_system") == "integrated",
            "components": {
                "agricultural_validator": AGRICULTURAL_VALIDATOR_AVAILABLE,
                "intent_confidence": dialogue_status.get("modules", {}).get("cot_fallback_processor", {}).get("openai_fallback_available", False),
                "completeness_scoring": True,
                "source_reliability": True
            },
            "confidence_levels": ["very_high", "high", "medium", "low", "very_low"],
            "score_range": {"min": 0.0, "max": 100.0},
            "features": {
                "adaptive_weighting": True,
                "contextual_adjustments": True,
                "debug_mode_available": True,
                "explanation_generation": True
            }
        }
    except Exception as e:
        return {
            "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,
            "error": f"Could not get detailed status: {str(e)}",
            "basic_status": "partial" if CONFIDENCE_SYSTEM_AVAILABLE else "unavailable"
        }

@router.post("/test-confidence-system")
async def test_confidence_system(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Teste le système de confidence unifié avec différents scénarios."""
    return await test_confidence_system_async()

@router.get("/confidence-examples")
def confidence_examples() -> Dict[str, Any]:
    """Exemples de scores de confidence selon différents scénarios."""
    return get_confidence_examples()

# ===== Endpoints Fallback OpenAI =====

@router.get("/fallback-status")
def fallback_status() -> Dict[str, Any]:
    """Status détaillé du système de fallback OpenAI + persistance + confidence."""
    try:
        from .pipeline.dialogue_manager import get_fallback_status
        return get_fallback_status()
    except Exception as e:
        return {
            "error": "Could not get fallback status",
            "message": str(e),
            "openai_fallback_available": False
        }

@router.post("/test-openai-fallback")
async def test_openai_fallback(
    test_question: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Teste le fallback OpenAI directement (bypass RAG) avec confidence."""
    try:
        from .pipeline.dialogue_manager import generate_openai_fallback_response
        from .pipeline.utils.question_classifier import Intention
        
        test_entities = {
            "species": "broiler",
            "line": "ross308", 
            "sex": "as_hatched",
            "age_days": 21
        }
        
        result = await asyncio.to_thread(
            generate_openai_fallback_response,
            question=test_question,
            entities=test_entities,
            intent=Intention.PerfTargets,
            rag_context="Contexte RAG non disponible (test)"
        )
        
        confidence_info = {}
        if result and isinstance(result, dict):
            confidence_info = {
                "source_confidence": result.get("confidence", "N/A"),
                "source_type": result.get("source", "unknown")
            }
        
        return {
            "test_question": test_question,
            "openai_response": result,
            "confidence_info": confidence_info,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Test OpenAI fallback failed: {str(e)}",
            "test_question": test_question
        }

@router.post("/test-fallback-integration")
async def test_fallback_integration(
    test_question: str = "Quel est le poids à 21 jours pour des Ross 308 mâles ?",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Teste l'intégration complète RAG → Fallback OpenAI + persistance + confidence."""
    try:
        payload = AskPayload(
            session_id="test_fallback",
            question=test_question,
            lang="fr",
            debug=True,
            entities={"species": "broiler", "line": "ross308", "sex": "male", "age_days": 21}
        )
        
        class MockRequest:
            def __init__(self):
                self.query_params = {}
                self.client = type('obj', (object,), {'host': 'localhost'})
                self.headers = {}
        
        mock_request = MockRequest()
        result = await ask_internal_async(payload, mock_request, current_user)
        
        answer = result.get("answer", {})
        source = answer.get("source", "unknown")
        meta = answer.get("meta", {})
        confidence = result.get("confidence", {})
        
        return {
            "test_question": test_question,
            "result_source": source,
            "fallback_activated": source == "openai_fallback",
            "rag_attempted": meta.get("rag_attempted", False),
            "result_preview": answer.get("text", "")[:200] + "..." if answer.get("text") else None,
            "persistence_metadata": result.get("persistence_metadata", {}),
            "confidence_metadata": result.get("confidence_metadata", {}),
            "unified_confidence": confidence,
            "full_result": result,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Integration test failed: {str(e)}",
            "test_question": test_question
        }

# ===== Endpoints Persistance =====

@router.post("/test-conversation-persistence")
async def test_conversation_persistence(
    test_question: str = "Test de persistance des conversations avec confidence",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Teste la persistance des conversations directement avec tracking confidence."""
    try:
        from .pipeline.dialogue_manager import _persist_conversation
        from .expert_utils import extract_user_id_for_persistence
        
        test_session_id = f"test_persistence_{int(time.time())}"
        test_answer = "Réponse de test pour vérifier la persistance avec confidence"
        user_id = extract_user_id_for_persistence(current_user)
        
        persistence_success = await asyncio.to_thread(
            _persist_conversation,
            session_id=test_session_id,
            question=test_question,
            answer_text=test_answer,
            language="fr",
            user_id=user_id,
            additional_context={
                "test": True,
                "intent": "test_persistence",
                "route": "test_endpoint",
                "confidence_score": 85.0,
                "confidence_level": "high"
            }
        )
        
        return {
            "status": "success" if persistence_success else "failed",
            "test_session_id": test_session_id,
            "test_question": test_question,
            "test_answer": test_answer,
            "user_id": user_id,
            "persistence_success": persistence_success,
            "confidence_tracking": True,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Persistence test failed: {str(e)}",
            "test_question": test_question
        }

@router.get("/conversation-persistence-status")
def conversation_persistence_status() -> Dict[str, Any]:
    """Status détaillé de la persistance des conversations avec confidence tracking."""
    try:
        from .pipeline.dialogue_manager import (
            POSTGRES_AVAILABLE, 
            PERSIST_CONVERSATIONS, 
            CLEAR_CONTEXT_AFTER_ASK,
            _POSTGRES_MEMORY
        )
        
        return {
            "postgres_available": POSTGRES_AVAILABLE,
            "persist_conversations": PERSIST_CONVERSATIONS,
            "clear_context_after_ask": CLEAR_CONTEXT_AFTER_ASK,
            "postgres_memory_initialized": _POSTGRES_MEMORY is not None,
            "database_url_configured": bool(os.getenv("DATABASE_URL")),
            "confidence_tracking_enabled": CONFIDENCE_SYSTEM_AVAILABLE,
            "status": "operational" if (POSTGRES_AVAILABLE and PERSIST_CONVERSATIONS) else "limited"
        }
        
    except ImportError as e:
        return {
            "error": "Could not import persistence modules",
            "message": str(e),
            "status": "unavailable"
        }

# ===== Endpoints Validation Agricole =====

@router.get("/agricultural-validation-status")
def agricultural_validation_status() -> Dict[str, Any]:
    """Status détaillé du validateur agricole."""
    return get_agricultural_validation_status()

@router.post("/test-agricultural-validation")
async def test_agricultural_validation(
    test_question: str,
    lang: str = "fr",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Teste la validation agricole sur une question donnée avec confidence."""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        return {
            "error": "Agricultural validator not available"
        }
    
    user_id = current_user.get('email', current_user.get('user_id', 'test_user'))
    
    try:
        validation_result = await asyncio.to_thread(
            validate_agricultural_question_safe,
            question=test_question,
            lang=lang,
            user_id=str(user_id),
            request_ip="test_ip"
        )
        
        validation_confidence = {
            "score": validation_result.confidence,
            "level": "high" if validation_result.confidence > 80 else "medium" if validation_result.confidence > 50 else "low",
            "explanation": f"Validation agricole: {validation_result.confidence}% de confiance"
        }
        
        return {
            "question": test_question,
            "lang": lang,
            "validation": {
                "is_valid": validation_result.is_valid,
                "confidence": validation_result.confidence,
                "reason": validation_result.reason
            },
            "validation_confidence": validation_confidence,
            "tester": user_id
        }
    except Exception as e:
        return {
            "error": f"Validation test failed: {str(e)}",
            "question": test_question
        }

# ===== Endpoints Quota =====

@router.get("/quota-status")
async def quota_status(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Récupère le statut du quota pour l'utilisateur connecté."""
    user_email = current_user.get('email')
    if not user_email:
        raise HTTPException(status_code=400, detail="Email utilisateur non trouvé")
    
    try:
        from app.api.v1.billing import check_quota_middleware
        quota_allowed, quota_details = await asyncio.to_thread(
            check_quota_middleware, user_email
        )
        return {
            "user_email": user_email,
            "quota_allowed": quota_allowed,
            "quota_details": quota_details,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"❌ Erreur récupération quota pour {user_email}: {e}")
        return {
            "error": f"Failed to get quota status: {str(e)}",
            "user_email": user_email
        }

@router.post("/test-quota-increment")
async def test_quota_increment(
    success: bool = True,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Teste l'incrémentation du quota (pour debug)."""
    user_email = current_user.get('email')
    if not user_email:
        raise HTTPException(status_code=400, detail="Email utilisateur non trouvé")
    
    try:
        from app.api.v1.billing import increment_quota_usage, check_quota_middleware
        
        if success:
            from .expert_utils import increment_quota_async
            await increment_quota_async(user_email)
        else:
            await asyncio.to_thread(increment_quota_usage, user_email, success=False)
        
        quota_allowed, quota_details = await asyncio.to_thread(
            check_quota_middleware, user_email
        )
        
        return {
            "message": f"Quota incrémenté (success={success})",
            "user_email": user_email,
            "updated_quota": quota_details,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": f"Failed to increment quota: {str(e)}",
            "user_email": user_email
        }

# ===== Endpoints Debug =====

@router.get("/debug")
def debug_imports() -> Dict[str, Any]:
    """Vérifie quelques imports utiles."""
    debug_info: Dict[str, Any] = {
        "dialogue_available": DIALOGUE_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "billing_system_available": True,
        "analytics_system_available": True,
        "performance_optimizations_enabled": True,
        "confidence_system_available": CONFIDENCE_SYSTEM_AVAILABLE,
        "modular_architecture": True,
        "imports_tested": []
    }
    
    try:
        from .pipeline.dialogue_manager import POSTGRES_AVAILABLE, PERSIST_CONVERSATIONS
        debug_info["conversation_persistence_available"] = POSTGRES_AVAILABLE and PERSIST_CONVERSATIONS
    except ImportError:
        debug_info["conversation_persistence_available"] = False
    
    imports_to_test: List[str] = [
        "app.api.v1.utils.question_classifier",
        "app.api.v1.pipeline.context_extractor",
        "app.api.v1.pipeline.clarification_manager",
        "app.api.v1.pipeline.rag_engine",
        "app.api.v1.utils.formulas",
        "app.api.v1.pipeline.intent_registry",
        "app.api.v1.agricultural_domain_validator",
        "app.api.v1.billing",
        "app.api.v1.logging",
        "app.api.v1.pipeline.postgres_memory",
        "app.api.v1.pipeline.unified_confidence",
        "app.api.v1.expert_core",
        "app.api.v1.expert_confidence",
        "app.api.v1.expert_utils",
    ]
    
    for import_path in imports_to_test:
        try:
            __import__(import_path)
            debug_info["imports_tested"].append({"path": import_path, "status": "✅ OK"})
        except Exception as e:
            debug_info["imports_tested"].append({"path": import_path, "status": f"❌ Error: {e}"})
    
    return debug_info

@router.post("/force-import-test")
async def force_import_test():
    """Teste l'import et un appel basique de handle() sans casser l'API."""
    import traceback
    try:
        from .pipeline.dialogue_manager import handle as _handle
        test_result = await asyncio.to_thread(
            _handle, "test", "test question", "fr", debug=True, user_id="test_user"
        )
        
        has_confidence = "confidence" in test_result
        confidence_info = test_result.get("confidence", {}) if has_confidence else {}
        
        return {
            "status": "✅ SUCCESS", 
            "result": test_result, 
            "import_successful": True,
            "confidence_included": has_confidence,
            "confidence_score": confidence_info.get("score"),
            "confidence_level": confidence_info.get("level"),
            "modular_architecture": True
        }
    except Exception as e:
        return {
            "status": "❌ FAILED",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "import_successful": False,
        }

@router.get("/perfstore-status")
def perfstore_status():
    """Expose quelques infos sur le PerfStore."""
    try:
        from .pipeline.dialogue_manager import _get_perf_store
        store = _get_perf_store("broiler")
        if not store:
            return {"ok": False, "reason": "PerfStore None"}
        root = getattr(store, "root", None)
        species = getattr(store, "species", None)
        tables_dir = str(getattr(store, "dir_tables", "")) if getattr(store, "dir_tables", None) else None

        lines = []
        for ln in ["ross308", "cobb500"]:
            try:
                df = store._load_df(ln)
                lines.append({"line": ln, "rows": 0 if df is None else int(len(df))})
            except Exception as e:
                lines.append({"line": ln, "error": str(e)})

        return {
            "