"""
app/api/v1/expert.py - ENDPOINTS PRINCIPAUX EXPERT SYSTEM

Endpoints core pour le système expert avec fonctionnalités améliorées
Fichier principal maintenant modulaire et facile à maintenir
"""

import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer

from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest
from .expert_services import ExpertService
from .expert_utils import get_user_id_from_request

router = APIRouter(tags=["expert-enhanced"])
logger = logging.getLogger(__name__)
security = HTTPBearer()

# Service principal
expert_service = ExpertService()

# =============================================================================
# ENDPOINTS PRINCIPAUX
# =============================================================================

@router.post("/ask-enhanced", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """
    Endpoint expert amélioré avec:
    - Retraitement automatique après clarification
    - Gestion intelligente du contexte conversationnel  
    - Réponses avec données numériques optimisées
    - Suivi d'état conversationnel avancé
    """
    start_time = time.time()
    
    try:
        logger.info("=" * 80)
        logger.info("🚀 DÉBUT ask_expert_enhanced - VERSION INTELLIGENTE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        logger.info(f"🆔 Conversation ID: {request_data.conversation_id}")
        logger.info(f"🔄 Is clarification response: {request_data.is_clarification_response}")
        
        # Déléguer le traitement au service
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=current_user,
            start_time=start_time
        )
        
        logger.info(f"✅ FIN ask_expert_enhanced - conversation_id: {response.conversation_id}")
        logger.info(f"🤖 IA enhancements utilisés: {response.ai_enhancements_used}")
        logger.info("=" * 80)
        
        return response
    
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced: {e}")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-enhanced-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_public(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint public avec fonctionnalités améliorées"""
    start_time = time.time()
    
    try:
        logger.info("=" * 80)
        logger.info("🌐 DÉBUT ask_expert_enhanced_public - VERSION INTELLIGENTE PUBLIQUE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        
        # Déléguer le traitement au service (mode public)
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=None,
            start_time=start_time
        )
        
        logger.info(f"✅ FIN ask_expert_enhanced_public - conversation_id: {response.conversation_id}")
        logger.info(f"🤖 IA enhancements publics utilisés: {response.ai_enhancements_used}")
        logger.info("=" * 80)
        
        return response
    
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_public: {e}")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/feedback")
async def submit_feedback_enhanced(feedback_data: FeedbackRequest):
    """Submit feedback - VERSION AMÉLIORÉE"""
    try:
        logger.info(f"📊 [Expert Enhanced] Feedback reçu: {feedback_data.rating}")
        logger.info(f"📊 [Expert Enhanced] Conversation ID: {feedback_data.conversation_id}")
        
        # Déléguer au service
        result = await expert_service.process_feedback(feedback_data)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur feedback critique: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement feedback: {str(e)}")

# =============================================================================
# ENDPOINTS DE COMPATIBILITÉ
# =============================================================================

@router.post("/ask", response_model=EnhancedExpertResponse)
async def ask_expert_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """
    Endpoint de compatibilité avec expert.py original mais avec fonctionnalités améliorées.
    Redirige vers ask_expert_enhanced avec toutes les améliorations.
    """
    logger.info("🔄 [Expert Enhanced] Redirection vers endpoint amélioré pour compatibilité")
    
    # Appeler directement l'endpoint amélioré
    return await ask_expert_enhanced(request_data, request, current_user)

@router.post("/ask-public", response_model=EnhancedExpertResponse)
async def ask_expert_public_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """
    Endpoint public de compatibilité avec expert.py original mais avec fonctionnalités améliorées.
    Redirige vers ask_expert_enhanced_public avec toutes les améliorations.
    """
    logger.info("🔄 [Expert Enhanced] Redirection vers endpoint public amélioré pour compatibilité")
    
    # Appeler directement l'endpoint public amélioré
    return await ask_expert_enhanced_public(request_data, request)

# =============================================================================
# ENDPOINT TOPICS
# =============================================================================

@router.get("/topics")
async def get_suggested_topics_enhanced(language: str = "fr"):
    """Get suggested topics - VERSION AMÉLIORÉE"""
    try:
        return await expert_service.get_suggested_topics(language)
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

# =============================================================================
# CONFIGURATION & LOGGING
# =============================================================================

logger.info("🚀 [EXPERT MAIN] Endpoints principaux initialisés avec succès!")
logger.info("🔧 [EXPERT MAIN] ENDPOINTS DISPONIBLES:")
logger.info("   - POST /ask-enhanced (authentifié avec retraitement auto)")
logger.info("   - POST /ask-enhanced-public (public avec IA)")
logger.info("   - POST /feedback (feedback amélioré)")
logger.info("   - POST /ask (compatible original)")
logger.info("   - POST /ask-public (compatible original public)")
logger.info("   - GET /topics (topics enrichis)")
