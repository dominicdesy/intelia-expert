"""
Expert Router - Version corrigée avec fallback RAG
CONSERVE: Structure originale + DialogueManager
CORRIGE: Ajoute fallback vers système RAG quand clarification demandée
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from pydantic import BaseModel
import uuid
import logging
from app.api.v1.pipeline.dialogue_manager import DialogueManager

router = APIRouter(prefix="", tags=["expert"])
logger = logging.getLogger(__name__)

# ==================== CONSERVATION: Instances originales ====================
dlg = DialogueManager()

# ==================== CONSERVATION: Modèles Pydantic originaux ====================
class AskRequest(BaseModel):
    question: str

class ClarificationResponse(BaseModel):
    type: str
    questions: List[str]

class AnswerResponse(BaseModel):
    type: str
    response: str

# Generic response model for Swagger
ResponseModel = Dict[str, Any]

# ==================== CONSERVATION: Fonction session originale ====================
def get_session_id(request: Request) -> str:
    """
    Retrieves or initializes a session ID from the request headers.
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
    return session_id

# ==================== CORRECTION: Endpoint principal avec fallback ====================
@router.post("/ask", response_model=ResponseModel)
async def ask(
    payload: AskRequest = Body(...),
    request: Request,  # AJOUTÉ pour accès au système RAG
    session_id: str = Depends(get_session_id)
) -> ResponseModel:
    """
    Handle user questions via the DialogueManager pipeline.
    NOUVEAU: Si clarification demandée, essaie RAG direct en fallback.
    Returns either clarification questions or a final answer.
    """
    try:
        logger.info(f"Question reçue: {payload.question[:50]}...")
        
        # CONSERVATION: Utiliser DialogueManager original
        result = dlg.handle(session_id, payload.question)
        resp_type = result.get("type")
        
        logger.info(f"DialogueManager retourne: {resp_type}")

        if resp_type == "clarification":
            logger.info("Clarification demandée, tentative fallback RAG...")
            
            # ✅ CORRECTION: Fallback vers système RAG si clarification
            try:
                if hasattr(request.app.state, 'process_question_with_rag'):
                    process_question_func = request.app.state.process_question_with_rag
                    
                    # Appeler le système RAG de main.py
                    rag_result = await process_question_func(
                        question=payload.question,
                        user=None,
                        language="fr",
                        speed_mode="balanced"
                    )
                    
                    logger.info("Fallback RAG réussi, retour réponse directe")
                    
                    # Retourner réponse RAG avec note sur manque d'infos
                    enhanced_response = rag_result["response"]
                    if rag_result.get("mode") == "fallback_openai":
                        enhanced_response += "\n\n💡 *Pour une réponse plus précise, précisez la race, l'âge exact, ou le contexte d'élevage.*"
                    
                    return AnswerResponse(
                        type="answer",
                        response=enhanced_response
                    ).dict()
                    
                else:
                    logger.warning("Système RAG non disponible dans app.state")
                    
            except Exception as rag_error:
                logger.error(f"Erreur fallback RAG: {rag_error}")
                # Continuer avec clarification si RAG échoue
            
            # Si fallback RAG échoue, retourner clarification originale
            logger.info("Fallback RAG échoué, retour clarifications")
            return ClarificationResponse(
                type="clarification",
                questions=result.get("questions", [])
            ).dict()

        if resp_type == "answer":
            logger.info("Réponse directe du DialogueManager")
            return AnswerResponse(
                type="answer",
                response=result.get("response", "")
            ).dict()

        # CONSERVATION: Gestion erreur originale
        raise HTTPException(status_code=500, detail="Unexpected response type")
        
    except HTTPException:
        # Re-raise HTTPException sans modification
        raise
        
    except Exception as e:
        logger.error(f"Erreur critique dans ask(): {e}")
        
        # ✅ CORRECTION: Fallback ultime vers RAG en cas d'erreur
        try:
            logger.info("Tentative fallback ultime vers RAG...")
            
            if hasattr(request.app.state, 'process_question_with_rag'):
                process_question_func = request.app.state.process_question_with_rag
                rag_result = await process_question_func(
                    question=payload.question,
                    user=None,
                    language="fr",
                    speed_mode="balanced"
                )
                
                logger.info("Fallback ultime RAG réussi")
                
                return AnswerResponse(
                    type="answer",
                    response=rag_result["response"] + "\n\n⚠️ *Réponse générée en mode fallback.*"
                ).dict()
                
        except Exception as rag_error:
            logger.error(f"Fallback ultime RAG échoué: {rag_error}")
            
        # Si tout échoue, retourner erreur
        raise HTTPException(status_code=500, detail=f"Erreur traitement: {str(e)}")

# ==================== CONSERVATION: Ajout d'endpoints compatibilité ====================

@router.post("/ask-public", response_model=ResponseModel)
async def ask_public(
    payload: AskRequest = Body(...),
    request: Request
) -> ResponseModel:
    """
    Version publique - même logique que ask() mais sans session
    """
    public_session = f"public_{uuid.uuid4().hex[:8]}"
    return await ask(payload, request, public_session)

@router.get("/status")
async def expert_status():
    """
    Status du système expert
    """
    return {
        "status": "active",
        "dialogue_manager": "initialized",
        "fallback_rag": "available",
        "endpoints": ["/ask", "/ask-public", "/status"]
    }