"""
app/api/v1/expert_debug.py - ENDPOINTS DE DEBUGGING

Tous les endpoints de diagnostic et de test pour le système expert
"""

import os
import sys
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request

from .expert_models import EnhancedQuestionRequest, TestResult, SystemStats
from .expert_services import ExpertService
from .expert_utils import get_user_id_from_request

router = APIRouter(tags=["expert-debug"])
logger = logging.getLogger(__name__)

# Service pour les tests
expert_service = ExpertService()

# =============================================================================
# ENDPOINTS DE STATISTIQUES
# =============================================================================

@router.get("/enhanced-stats", response_model=SystemStats)
async def get_enhanced_system_stats():
    """Statistiques du système expert amélioré"""
    try:
        integrations_status = expert_service.integrations.get_system_status()
        available_enhancements = expert_service.integrations.get_available_enhancements()
        
        stats = SystemStats(
            system_available=True,
            timestamp=datetime.now().isoformat(),
            components=integrations_status,
            enhanced_capabilities=available_enhancements,
            enhanced_endpoints=[
                "POST /ask-enhanced (authenticated)",
                "POST /ask-enhanced-public (public)",
                "GET /enhanced-stats (system statistics)",
                "POST /test-enhanced-flow (testing)",
                "GET /enhanced-conversation/{id}/context (conversation context)"
            ]
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ [Enhanced Stats] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur stats: {str(e)}")

@router.get("/validation-stats")
async def get_validation_stats_enhanced():
    """Statistiques du validateur agricole - VERSION AMÉLIORÉE"""
    try:
        if not expert_service.integrations.agricultural_validator_available:
            return {
                "error": "Validateur agricole non disponible",
                "available": False,
                "stats": None,
                "enhanced_system": True
            }
        
        stats = expert_service.integrations.get_agricultural_validator_stats()
        
        return {
            "available": True,
            "validation_enabled": expert_service.integrations.is_agricultural_validation_enabled(),
            "stats": stats,
            "enhanced_features": {
                "contextual_validation": expert_service.integrations.intelligent_memory_available,
                "conversation_aware": True,
                "ai_powered": expert_service.integrations.intelligent_memory_available
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Enhanced Debug] Erreur stats validation: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération stats")

# =============================================================================
# ENDPOINTS DE TEST
# =============================================================================

@router.post("/test-enhanced-flow", response_model=TestResult)
async def test_enhanced_flow(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint de test pour le flux amélioré complet"""
    try:
        logger.info(f"🧪 [Test Enhanced] Test du flux amélioré")
        logger.info(f"📝 Question: {request_data.text}")
        
        user_id = get_user_id_from_request(request)
        conversation_id = request_data.conversation_id or str(uuid.uuid4())
        
        test_results = TestResult(
            question=request_data.text,
            conversation_id=conversation_id,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            components_tested={},
            test_successful=True,
            errors=[]
        )
        
        # Test mémoire intelligente
        if expert_service.integrations.intelligent_memory_available:
            try:
                context = expert_service.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=request_data.text,
                    role="user",
                    language=request_data.language
                )
                test_results.components_tested["intelligent_memory"] = {
                    "status": "success",
                    "extracted_entities": context.consolidated_entities.to_dict() if context and hasattr(context, 'consolidated_entities') else {},
                    "confidence": context.consolidated_entities.confidence_overall if context and hasattr(context, 'consolidated_entities') else 0,
                    "urgency": context.conversation_urgency if context and hasattr(context, 'conversation_urgency') else "normal"
                }
            except Exception as e:
                test_results.components_tested["intelligent_memory"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results.errors.append(f"Intelligent memory: {str(e)}")
        
        # Test clarification améliorée
        if expert_service.integrations.enhanced_clarification_available:
            try:
                clarification_context = expert_service.integrations.get_context_for_clarification(conversation_id)
                
                clarification_result = await expert_service.integrations.analyze_question_for_clarification_enhanced(
                    question=request_data.text,
                    language=request_data.language,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_context=clarification_context
                )
                
                test_results.components_tested["enhanced_clarification"] = {
                    "status": "success",
                    "needs_clarification": clarification_result.needs_clarification,
                    "questions_count": len(clarification_result.questions) if clarification_result.questions else 0,
                    "clarification_mode": clarification_result.clarification_mode.value if clarification_result.clarification_mode else None,
                    "confidence": clarification_result.confidence_score,
                    "extracted_entities": clarification_result.extracted_entities.to_dict() if clarification_result.extracted_entities else None
                }
            except Exception as e:
                test_results.components_tested["enhanced_clarification"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results.errors.append(f"Enhanced clarification: {str(e)}")
        
        # Test validation agricole
        if expert_service.integrations.agricultural_validator_available:
            try:
                validation_result = expert_service.integrations.validate_agricultural_question(
                    question=request_data.text,
                    language=request_data.language,
                    user_id=user_id,
                    request_ip=request.client.host if request.client else "unknown"
                )
                
                test_results.components_tested["agricultural_validation"] = {
                    "status": "success",
                    "is_valid": validation_result.is_valid,
                    "confidence": validation_result.confidence,
                    "rejection_message": validation_result.reason if not validation_result.is_valid else None
                }
            except Exception as e:
                test_results.components_tested["agricultural_validation"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results.errors.append(f"Agricultural validation: {str(e)}")
        
        # Test contexte RAG
        if expert_service.integrations.intelligent_memory_available:
            try:
                rag_context = expert_service.integrations.get_context_for_rag(conversation_id, max_chars=500)
                test_results.components_tested["rag_context"] = {
                    "status": "success",
                    "context_length": len(rag_context),
                    "context_preview": rag_context[:100] + "..." if len(rag_context) > 100 else rag_context
                }
            except Exception as e:
                test_results.components_tested["rag_context"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results.errors.append(f"RAG context: {str(e)}")
        
        test_results.test_successful = len(test_results.errors) == 0
        
        logger.info(f"🧪 [Test Enhanced] Test terminé - Succès: {test_results.test_successful}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ [Test Enhanced] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur test: {str(e)}")

@router.post("/test-validation")
async def test_validation_enhanced(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Test endpoint pour tester la validation AMÉLIORÉE"""
    try:
        question_text = request_data.text.strip()
        user_id = get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        conversation_id = request_data.conversation_id or str(uuid.uuid4())
        
        if not expert_service.integrations.agricultural_validator_available:
            return {
                "error": "Validateur agricole non disponible",
                "available": False,
                "enhanced_system": True
            }
        
        # Test avec contexte intelligent
        memory_context = None
        if expert_service.integrations.intelligent_memory_available:
            try:
                memory_context = expert_service.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=request_data.language
                )
            except Exception as e:
                logger.warning(f"⚠️ [Test Validation] Erreur contexte test: {e}")
        
        # Test de validation
        validation_result = expert_service.integrations.validate_agricultural_question(
            question=question_text,
            language=request_data.language,
            user_id=user_id,
            request_ip=request_ip
        )
        
        return {
            "question": question_text,
            "language": request_data.language,
            "validation_passed": validation_result.is_valid,
            "confidence": validation_result.confidence,
            "rejection_message": validation_result.reason if not validation_result.is_valid else None,
            "validator_available": True,
            "validation_enabled": expert_service.integrations.is_agricultural_validation_enabled(),
            "conversation_id": conversation_id,
            "enhanced_features": {
                "memory_context": memory_context.to_dict() if memory_context and hasattr(memory_context, 'to_dict') else None,
                "contextual_validation": expert_service.integrations.intelligent_memory_available,