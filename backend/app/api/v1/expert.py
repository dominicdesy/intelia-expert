# app/api/v1/expert.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.encoders import jsonable_encoder  # [PATCH] JSON-safe responses
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
import logging
import os
import re
import math
import time  # NOUVEAU: Ajouté pour les endpoints de test

# 🔐 Import authentification
from app.api.v1.auth import get_current_user

# 🌾 Import validateur agricole
try:
    from app.api.v1.pipeline.agricultural_domain_validator import (
        validate_agricultural_question,
        get_agricultural_validator_stats,
        is_agricultural_validation_enabled,
        ValidationResult
    )
    AGRICULTURAL_VALIDATOR_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Agricultural domain validator imported successfully")
except ImportError as e:
    AGRICULTURAL_VALIDATOR_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Failed to import agricultural validator: {e}")

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

# ===== Import numpy sécurisé =====
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

# ===== Cache simple pour PerfStore =====
_store_cache = {}

def get_cached_store(species: str):
    """Cache simple pour éviter de recharger le même store"""
    if species not in _store_cache:
        try:
            from .pipeline.perf_store import PerfStore  # type: ignore
            _store_cache[species] = PerfStore(root=os.environ.get("RAG_INDEX_ROOT", "./rag_index"), species=species)
        except Exception as e:
            logger.error(f"Failed to create PerfStore for {species}: {e}")
            return None
    return _store_cache[species]

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

# ===== Fonction de validation agricole =====
def _validate_agricultural_question(question: str, lang: str = "fr", user_id: str = "unknown", request_ip: str = "unknown") -> ValidationResult:
    """Valide qu'une question concerne le domaine agricole"""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        logger.warning("⚠️ Agricultural validator not available, allowing all questions")
        return ValidationResult(is_valid=True, confidence=100.0, reason="Validator unavailable")
    
    try:
        return validate_agricultural_question(question, lang, user_id, request_ip)
    except Exception as e:
        logger.error(f"❌ Error in agricultural validation: {e}")
        # En cas d'erreur, permettre la question avec un avertissement
        return ValidationResult(is_valid=True, confidence=50.0, reason=f"Validation error: {str(e)}")

def _get_user_info_for_validation(request: Request, current_user: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """Extrait les informations utilisateur pour la validation"""
    if current_user:
        user_id = current_user.get('email', current_user.get('user_id', 'authenticated_user'))
    else:
        user_id = "anonymous_user"
    
    # Extraire l'IP de la requête
    request_ip = getattr(request.client, 'host', 'unknown') if hasattr(request, 'client') else 'unknown'
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        request_ip = forwarded_for.split(',')[0].strip()
    
    return str(user_id), str(request_ip)

# ===== Fonction de nettoyage JSON améliorée =====
def clean_for_json(value):
    """Nettoie seulement les valeurs problématiques pour JSON avec protection robuste"""
    if value is None:
        return None
    if isinstance(value, (int, str, bool)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    
    # Protection numpy robuste
    if HAS_NUMPY and hasattr(value, 'item'):
        try:
            val = value.item()
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return None
            return val
        except:
            return str(value)  # Fallback si .item() échoue
    
    return str(value)  # Fallback général

def clean_dict_for_json(obj):
    """Nettoie récursivement seulement les valeurs problématiques"""
    if isinstance(obj, dict):
        return {k: clean_dict_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict_for_json(v) for v in obj]
    else:
        return clean_for_json(obj)

# ===== Parsing d'âge amélioré =====
def extract_age_from_text(text: str) -> Optional[int]:
    """Extraction d'âge plus robuste avec support semaines/années"""
    text_lower = text.lower()
    
    # Patterns par ordre de priorité
    age_patterns = [
        (r"(\d+)\s*(?:j|jour|jours|d|day|days)\b", 1),      # jours (x1)
        (r"(\d+)\s*(?:w|week|weeks|semaine|semaines)\b", 7), # semaines (x7)
        (r"age\s*(\d+)", 1),                                 # "age 21" (jours)
        (r"(\d+)\s*(?:ans|years?)\b", 365),                 # années (x365)
    ]
    
    for pattern, multiplier in age_patterns:
        m = re.search(pattern, text_lower)
        if m:
            try:
                age_value = int(m.group(1)) * multiplier
                # Validation raisonnable pour les volailles
                if 1 <= age_value <= 70:
                    return age_value
            except:
                continue
    return None

# ===== Schémas =====
class AskPayload(BaseModel):
    session_id: Optional[str] = "default"
    question: str
    lang: Optional[str] = "fr"
    debug: Optional[bool] = False
    force_perfstore: Optional[bool] = False
    intent_hint: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    bypass_validation: Optional[bool] = False  # 🌾 NOUVEAU: pour bypass administrateur
    model_config = {"extra": "allow"}

# ===== Fonction interne partagée avec validation =====
def _ask_internal(payload: AskPayload, request: Request, current_user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Logique interne pour traiter les questions (avec ou sans auth) + validation agricole."""
    try:
        # Extraction des infos utilisateur pour la validation
        user_id, request_ip = _get_user_info_for_validation(request, current_user)
        
        # Log différencié selon l'authentification
        if current_user:
            user_email = current_user.get('email', 'unknown')
            logger.info(f"🔐 Question authentifiée de {user_email}: {payload.question[:120]}")
        else:
            logger.info(f"🌐 Question publique: {payload.question[:120]}")

        # 🌾 VALIDATION AGRICOLE (sauf si bypass autorisé)
        validation_bypassed = False
        if not payload.bypass_validation:
            validation_result = _validate_agricultural_question(
                question=payload.question,
                lang=payload.lang or "fr",
                user_id=user_id,
                request_ip=request_ip
            )
            
            if not validation_result.is_valid:
                logger.warning(f"🚫 Question rejetée par validation agricole: {validation_result.reason}")
                return {
                    "type": "validation_rejected",
                    "message": validation_result.reason,
                    "session_id": payload.session_id or "default",
                    "validation": {
                        "is_valid": False,
                        "confidence": validation_result.confidence,
                        "suggested_topics": validation_result.suggested_topics,
                        "detected_keywords": validation_result.detected_keywords,
                        "rejected_keywords": validation_result.rejected_keywords
                    },
                    "user": {
                        "email": current_user.get('email') if current_user else None,
                        "user_id": current_user.get('user_id') if current_user else None
                    } if current_user else None
                }
            else:
                logger.info(f"✅ Question validée (confiance: {validation_result.confidence:.1f}%)")
        else:
            validation_bypassed = True
            logger.info("⚠️ Validation agricole bypassée par l'utilisateur")

        # Traitement normal de la question
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

        # Ajouter les infos utilisateur et de validation dans la réponse
        if current_user:
            result["user"] = {
                "email": current_user.get('email'),
                "user_id": current_user.get('user_id')
            }
        
        # Ajouter les métadonnées de validation
        result["validation_metadata"] = {
            "agricultural_validation_enabled": AGRICULTURAL_VALIDATOR_AVAILABLE and is_agricultural_validation_enabled(),
            "validation_bypassed": validation_bypassed
        }

        logger.info(f"✅ Réponse générée: type={result.get('type')}")
        return result
        
    except Exception as e:
        logger.exception("❌ Erreur dans le traitement de la question")
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

# ===== Endpoints principaux (code original conservé) =====
@router.post("/ask")
def ask(
    payload: AskPayload, 
    request: Request,
    current_user: dict = Depends(get_current_user)  # 🔐 Auth requise
) -> Dict[str, Any]:
    """Endpoint principal SÉCURISÉ pour poser des questions avec validation agricole."""
    return _ask_internal(payload, request, current_user)

@router.post("/ask-public")
def ask_public(payload: AskPayload, request: Request) -> Dict[str, Any]:
    """Endpoint public (pas d'authentification requise) avec validation agricole."""
    return _ask_internal(payload, request, None)

@router.get("/system-status")
def system_status() -> Dict[str, Any]:
    """État synthétique du service."""
    return {
        "status": "ok" if DIALOGUE_AVAILABLE else "degraded",
        "dialogue_manager_available": DIALOGUE_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "agricultural_validation_enabled": AGRICULTURAL_VALIDATOR_AVAILABLE and is_agricultural_validation_enabled(),
        "service": "expert_api",
    }

# ===== NOUVEAUX ENDPOINTS: Fallback OpenAI =====

@router.get("/fallback-status")
def fallback_status() -> Dict[str, Any]:
    """
    Status détaillé du système de fallback OpenAI.
    """
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
def test_openai_fallback(
    test_question: str,
    current_user: dict = Depends(get_current_user)  # 🔐 Auth requise
) -> Dict[str, Any]:
    """
    Teste le fallback OpenAI directement (bypass RAG).
    """
    try:
        # Import correct de la fonction et de l'Intention
        from .pipeline.dialogue_manager import _generate_openai_fallback_response
        from .utils.question_classifier import Intention  # Import correct
        
        # Entités de test basiques
        test_entities = {
            "species": "broiler",
            "line": "ross308", 
            "sex": "as_hatched",
            "age_days": 21
        }
        
        result = _generate_openai_fallback_response(
            question=test_question,
            entities=test_entities,
            intent=Intention.PerfTargets,  # Intent par défaut pour test
            rag_context="Contexte RAG non disponible (test)"
        )
        
        return {
            "test_question": test_question,
            "openai_response": result,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Test OpenAI fallback failed: {str(e)}",
            "test_question": test_question
        }

@router.post("/test-fallback-integration")
def test_fallback_integration(
    test_question: str = "Quel est le poids à 21 jours pour des Ross 308 mâles ?",
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Teste l'intégration complète RAG → Fallback OpenAI
    """
    try:
        # Test avec une question qui devrait déclencher le fallback
        payload = AskPayload(
            session_id="test_fallback",
            question=test_question,
            lang="fr",
            debug=True,
            entities={"species": "broiler", "line": "ross308", "sex": "male", "age_days": 21}
        )
        
        # Simulation d'une request basique
        class MockRequest:
            def __init__(self):
                self.query_params = {}
                self.client = type('obj', (object,), {'host': 'localhost'})
                self.headers = {}
        
        mock_request = MockRequest()
        
        # Appel du système complet
        result = _ask_internal(payload, mock_request, current_user)
        
        # Analyse du résultat pour vérifier si fallback activé
        answer = result.get("answer", {})
        source = answer.get("source", "unknown")
        meta = answer.get("meta", {})
        
        return {
            "test_question": test_question,
            "result_source": source,
            "fallback_activated": source == "openai_fallback",
            "rag_attempted": meta.get("rag_attempted", False),
            "result_preview": answer.get("text", "")[:200] + "..." if answer.get("text") else None,
            "full_result": result,
            "tester": current_user.get('email', 'unknown'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "error": f"Integration test failed: {str(e)}",
            "test_question": test_question
        }

# ===== Endpoints existants (code original conservé) =====

@router.get("/agricultural-validation-status")
def agricultural_validation_status() -> Dict[str, Any]:
    """Status détaillé du validateur agricole."""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        return {
            "available": False,
            "reason": "Module not imported or not available"
        }
    
    try:
        stats = get_agricultural_validator_stats()
        return {
            "available": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }

@router.post("/test-agricultural-validation")
def test_agricultural_validation(
    test_question: str,
    lang: str = "fr",
    current_user: dict = Depends(get_current_user)  # 🔐 Auth requise pour les tests
) -> Dict[str, Any]:
    """Teste la validation agricole sur une question donnée."""
    if not AGRICULTURAL_VALIDATOR_AVAILABLE:
        return {
            "error": "Agricultural validator not available"
        }
    
    user_id = current_user.get('email', current_user.get('user_id', 'test_user'))
    
    try:
        validation_result = validate_agricultural_question(
            question=test_question,
            language=lang,
            user_id=str(user_id),
            request_ip="test_ip"
        )
        
        return {
            "question": test_question,
            "lang": lang,
            "validation": validation_result.to_dict(),
            "tester": user_id
        }
    except Exception as e:
        return {
            "error": f"Validation test failed: {str(e)}",
            "question": test_question
        }

@router.get("/debug")
def debug_imports() -> Dict[str, Any]:
    """Vérifie quelques imports utiles (préserve le comportement original)."""
    debug_info: Dict[str, Any] = {
        "dialogue_available": DIALOGUE_AVAILABLE,
        "agricultural_validator_available": AGRICULTURAL_VALIDATOR_AVAILABLE,
        "imports_tested": []
    }
    
    imports_to_test: List[str] = [
        "app.api.v1.utils.question_classifier",
        "app.api.v1.pipeline.context_extractor",
        "app.api.v1.pipeline.clarification_manager",
        "app.api.v1.pipeline.rag_engine",
        "app.api.v1.utils.formulas",
        "app.api.v1.pipeline.intent_registry",
        "app.api.v1.agricultural_domain_validator",  # 🌾 NOUVEAU
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
    """Teste l'import et un appel basique de handle() sans casser l'API."""
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
    """Expose quelques infos sur le PerfStore (ne jette pas d'exception)."""
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
    return {"status": "ok", "message": "Basic endpoint works"}

# ============================
# [FUSION] /perf-probe complet avec extraction + nettoyage JSON (INCHANGÉ)
# ============================
@router.post("/perf-probe")
def perf_probe(payload: AskPayload):
    """
    Version fusionnée complète:
    - Extraction automatique des entités depuis la question
    - Nettoyage JSON des valeurs NaN/inf 
    - Diagnostics complets avec fallbacks
    - Messages d'erreur informatifs
    """
    try:
        # [STEP 1] Import PerfStore protégé
        try:
            from .pipeline.perf_store import PerfStore  # type: ignore
        except ImportError as e:
            return jsonable_encoder({
                "error": "import_failed", 
                "message": f"Failed to import PerfStore: {str(e)}",
                "entities": (payload.entities or {}) if payload else {},
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
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit}
            })

        # [STEP 4] Normalisation des entités
        norm = _normalize_entities_soft_local(
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
                })
            available = store.available_lines()
        except Exception as e:
            return jsonable_encoder({
                "error": "perfstore_init_failed",
                "message": f"Failed to initialize PerfStore: {str(e)}",
                "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
                "norm": norm,
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
                }
            })

        # [SUCCESS] Résultat final avec message informatif
        success_message = "Performance data found"
        if not rec_clean:
            line_name = norm.get("line", "unknown")
            sex_name = norm.get("sex", "unknown") 
            age_val = norm.get("age_days", "unknown")
            success_message = f"No data found for {line_name}, {sex_name}, {age_val} days. Try: male/female/as_hatched, ages 1-49"

        result = {
            "success": bool(rec_clean),
            "entities": {"species": species, "line": line, "sex": sex, "age_days": age_days, "unit": unit},
            "norm": norm,
            "rec": rec_clean,
            "debug": {
                "rows": int(len(df)),
                "columns": [str(c) for c in df.columns],
                "available_lines": available,
                "tables_dir": str(getattr(store, "dir_tables", "")),
            },
            "message": success_message
        }
        
        return jsonable_encoder(result)

    except Exception as e:
        # Catch-all final avec informations de debug
        return jsonable_encoder({
            "error": "internal_error",
            "message": str(e),
            "entities": (payload.entities or {}) if payload else {},
            "debug": {"step": "unknown", "has_numpy": HAS_NUMPY}
        })