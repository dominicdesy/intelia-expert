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
    # === NEW: overrides de test & debug (backward-compatible) ===
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

        if not DIALOGUE_AVAILABLE:
            logger.warning("⚠️ Dialogue manager not available, using fallback")

        # Appeler la fonction handle (code original + NEW kwargs)
        result = handle(
            session_id=payload.session_id or "default",
            question=payload.question,
            lang=payload.lang or "fr",
            # === NEW: propage vers dialogue_manager ===
            debug=bool(payload.debug),
            force_perfstore=bool(payload.force_perfstore),
            intent_hint=(payload.intent_hint or None),
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
