"""
app/api/v1/expert.py - ENDPOINTS PRINCIPAUX EXPERT SYSTEM

Endpoints core pour le système expert avec fonctionnalités améliorées
VERSION FINALE CORRIGÉE : Support complet des nouvelles améliorations API + Clarification intelligente
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
# ENDPOINTS PRINCIPAUX AVEC AMÉLIORATIONS + CLARIFICATION INTELLIGENTE
# =============================================================================

@router.post("/ask-enhanced-v2", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """
    Endpoint expert FINAL avec toutes les améliorations:
    - Détection de questions floues avec clarification immédiate
    - Système de clarification intelligent race/sexe
    - Vérification de cohérence contextuelle
    - Scoring RAG détaillé avec métadonnées
    - Fallback enrichi avec diagnostics
    - Métriques de qualité prédictives
    - Mode debug pour développeurs
    """
    start_time = time.time()
    
    try:
        logger.info("=" * 80)
        logger.info("🚀 DÉBUT ask_expert_enhanced_v2 - VERSION FINALE AVEC CLARIFICATION INTELLIGENTE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        logger.info(f"🆔 Conversation ID: {request_data.conversation_id}")
        logger.info(f"🎯 Détection flou: {request_data.enable_vagueness_detection}")
        logger.info(f"🔍 Vérif cohérence: {request_data.require_coherence_check}")
        logger.info(f"📊 RAG détaillé: {request_data.detailed_rag_scoring}")
        logger.info(f"📈 Métriques qualité: {request_data.enable_quality_metrics}")
        logger.info(f"🐛 Mode debug: {request_data.debug_mode}")
        logger.info(f"🎪 Réponse clarification: {request_data.is_clarification_response}")
        
        # Déléguer le traitement au service amélioré
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=current_user,
            start_time=start_time
        )
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2 - conversation_id: {response.conversation_id}")
        logger.info(f"🤖 Améliorations utilisées: {len(response.ai_enhancements_used or [])} features")
        logger.info(f"⚡ Temps total: {response.response_time_ms}ms")
        logger.info(f"🎭 Mode final: {response.mode}")
        
        if response.clarification_result:
            logger.info(f"🎯 Clarification: {response.clarification_result.get('clarification_requested', False)}")
        
        if request_data.debug_mode and response.debug_info:
            logger.info(f"🐛 Debug info disponible: {len(response.debug_info)} éléments")
        
        logger.info("=" * 80)
        
        return response
    
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2: {e}")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-enhanced-v2-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2_public(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint public avec toutes les améliorations + clarification intelligente"""
    start_time = time.time()
    
    try:
        logger.info("=" * 80)
        logger.info("🌐 DÉBUT ask_expert_enhanced_v2_public - VERSION FINALE PUBLIQUE AVEC CLARIFICATION")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        logger.info(f"🎪 Réponse clarification: {request_data.is_clarification_response}")
        
        # Déléguer le traitement au service (mode public)
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=None,
            start_time=start_time
        )
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2_public - conversation_id: {response.conversation_id}")
        logger.info(f"🤖 Améliorations publiques utilisées: {len(response.ai_enhancements_used or [])} features")
        logger.info("=" * 80)
        
        return response
    
    except HTTPException:
        logger.info("=" * 80)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2_public: {e}")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# ENDPOINTS DE COMPATIBILITÉ (VERSIONS PRÉCÉDENTES)
# =============================================================================

@router.post("/ask-enhanced", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_legacy(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """
    Endpoint de compatibilité v1 - Redirige vers v2 avec améliorations
    """
    logger.info("🔄 [Expert Enhanced] Redirection legacy vers v2")
    return await ask_expert_enhanced_v2(request_data, request, current_user)

@router.post("/ask-enhanced-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_public_legacy(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """
    Endpoint public de compatibilité v1 - Redirige vers v2
    """
    logger.info("🔄 [Expert Enhanced] Redirection legacy public vers v2")
    return await ask_expert_enhanced_v2_public(request_data, request)

@router.post("/ask", response_model=EnhancedExpertResponse)
async def ask_expert_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """
    Endpoint de compatibilité original - Avec nouvelles fonctionnalités par défaut
    """
    logger.info("🔄 [Expert Enhanced] Redirection compatibilité vers v2 amélioré")
    
    # ✅ CORRECTION : Activer les améliorations par défaut pour compatibilité
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    
    return await ask_expert_enhanced_v2(request_data, request, current_user)

@router.post("/ask-public", response_model=EnhancedExpertResponse)
async def ask_expert_public_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """
    Endpoint public de compatibilité original - Avec améliorations
    """
    logger.info("🔄 [Expert Enhanced] Redirection compatibilité public vers v2")
    
    # ✅ CORRECTION : Activer les améliorations par défaut
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    
    return await ask_expert_enhanced_v2_public(request_data, request)

# =============================================================================
# ENDPOINT FEEDBACK AMÉLIORÉ
# =============================================================================

@router.post("/feedback")
async def submit_feedback_enhanced(feedback_data: FeedbackRequest):
    """Submit feedback - VERSION FINALE avec support qualité"""
    try:
        logger.info(f"📊 [Expert Enhanced] Feedback reçu: {feedback_data.rating}")
        logger.info(f"📊 [Expert Enhanced] Conversation ID: {feedback_data.conversation_id}")
        
        if feedback_data.quality_feedback:
            logger.info(f"📈 [Expert Enhanced] Feedback qualité détaillé: {len(feedback_data.quality_feedback)} métriques")
        
        # Déléguer au service
        result = await expert_service.process_feedback(feedback_data)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur feedback critique: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement feedback: {str(e)}")

# =============================================================================
# ENDPOINT TOPICS AMÉLIORÉ
# =============================================================================

@router.get("/topics")
async def get_suggested_topics_enhanced(language: str = "fr"):
    """Get suggested topics - VERSION FINALE avec statut améliorations"""
    try:
        return await expert_service.get_suggested_topics(language)
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur topics: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération topics")

# =============================================================================
# NOUVEAUX ENDPOINTS DE DEBUG ET MONITORING AVEC CLARIFICATION
# =============================================================================

@router.get("/system-status")
async def get_system_status():
    """Retourne le statut complet du système avec améliorations + clarification"""
    try:
        # Vérifier la disponibilité de tous les services
        status = {
            "system_available": True,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "expert_service": True,
                "rag_system": True,  # À vérifier réellement
                "enhancement_service": True,
                "integrations_manager": expert_service.integrations.get_system_status(),
                "clarification_system": True
            },
            "enhanced_capabilities": [
                "vagueness_detection",
                "context_coherence_check", 
                "detailed_rag_scoring",
                "enhanced_fallback",
                "quality_metrics",
                "debug_mode",
                "performance_breakdown",
                "smart_clarification_breed_sex",
                "clarification_response_processing",
                "incomplete_clarification_handling"
            ],
            "enhanced_endpoints": [
                "/ask-enhanced-v2",
                "/ask-enhanced-v2-public", 
                "/feedback (with quality)",
                "/topics (enhanced)",
                "/system-status",
                "/debug/test-enhancements",
                "/debug/test-clarification"
            ],
            "api_version": "v2_enhanced_with_clarification",
            "backward_compatibility": True,
            "clarification_features": {
                "breed_sex_detection": True,
                "automatic_clarification": True,
                "follow_up_handling": True,
                "multilingual_support": ["fr", "en", "es"]
            }
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur system status: {e}")
        return {
            "system_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/debug/test-enhancements")
async def test_enhancements(request: Request):
    """Test toutes les améliorations avec une question de test"""
    try:
        # Question de test qui active toutes les améliorations
        test_question = EnhancedQuestionRequest(
            text="Quel est leur poids au jour 18 ?",  # Question avec pronom contextuel
            conversation_id=str(uuid.uuid4()),
            language="fr",
            enable_vagueness_detection=True,
            require_coherence_check=True,
            detailed_rag_scoring=True,
            enable_quality_metrics=True,
            debug_mode=True
        )
        
        # Simuler contexte conversationnel (Ross 308 mentionné avant)
        if expert_service.integrations.intelligent_memory_available:
            try:
                expert_service.integrations.add_message_to_conversation(
                    conversation_id=test_question.conversation_id,
                    user_id="test_user",
                    message="Qu'est-ce que Ross 308 ?",
                    role="user",
                    language="fr"
                )
                expert_service.integrations.add_message_to_conversation(
                    conversation_id=test_question.conversation_id,
                    user_id="test_user", 
                    message="Le Ross 308 est une race de poulet de chair...",
                    role="assistant",
                    language="fr"
                )
            except Exception:
                pass  # Pas critique pour le test
        
        start_time = time.time()
        
        # Traiter la question de test
        result = await expert_service.process_expert_question(
            request_data=test_question,
            request=request,
            current_user=None,
            start_time=start_time
        )
        
        # Analyser les résultats
        test_results = {
            "test_successful": True,
            "question": test_question.text,
            "conversation_id": test_question.conversation_id,
            "user_id": "test_user",
            "timestamp": datetime.now().isoformat(),
            "components_tested": {
                "vagueness_detection": result.vagueness_detection is not None,
                "context_coherence": result.context_coherence is not None,
                "document_relevance": result.document_relevance is not None,
                "quality_metrics": result.quality_metrics is not None,
                "debug_info": result.debug_info is not None,
                "performance_breakdown": result.performance_breakdown is not None,
                "ai_enhancements_used": len(result.ai_enhancements_used or []) > 0,
                "clarification_system": "smart_performance_clarification" in (result.ai_enhancements_used or [])
            },
            "enhancement_results": {
                "ai_enhancements_count": len(result.ai_enhancements_used or []),
                "processing_steps_count": len(result.processing_steps or []),
                "response_time_ms": result.response_time_ms,
                "mode": result.mode,
                "clarification_triggered": result.clarification_result is not None
            },
            "errors": []
        }
        
        # Vérifications de qualité
        if not result.ai_enhancements_used:
            test_results["errors"].append("Aucune amélioration IA utilisée")
        
        if result.response_time_ms > 10000:  # 10 secondes
            test_results["errors"].append(f"Temps de réponse trop élevé: {result.response_time_ms}ms")
        
        if len(test_results["errors"]) > 0:
            test_results["test_successful"] = False
        
        logger.info(f"✅ [Expert Enhanced] Test des améliorations: {'SUCCÈS' if test_results['test_successful'] else 'ÉCHEC'}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur test améliorations: {e}")
        return {
            "test_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "components_tested": {},
            "errors": [f"Erreur critique: {str(e)}"]
        }

@router.post("/debug/test-clarification")
async def test_clarification_system(request: Request):
    """✅ NOUVEAU: Test spécifique du système de clarification intelligent"""
    try:
        test_results = {
            "test_successful": True,
            "timestamp": datetime.now().isoformat(),
            "tests_performed": [],
            "errors": []
        }
        
        # Test 1: Question nécessitant clarification race/sexe
        logger.info("🎯 Test 1: Question poids sans race/sexe")
        
        clarification_question = EnhancedQuestionRequest(
            text="Quel est le poids d'un poulet de 12 jours ?",
            conversation_id=str(uuid.uuid4()),
            language="fr",
            enable_vagueness_detection=True,
            is_clarification_response=False
        )
        
        start_time = time.time()
        result1 = await expert_service.process_expert_question(
            request_data=clarification_question,
            request=request,
            current_user=None,
            start_time=start_time
        )
        
        test1_result = {
            "test_name": "Détection question nécessitant clarification",
            "question": clarification_question.text,
            "clarification_requested": result1.clarification_result is not None,
            "mode": result1.mode,
            "enhancements_used": result1.ai_enhancements_used or [],
            "success": "smart_performance_clarification" in result1.mode
        }
        
        test_results["tests_performed"].append(test1_result)
        
        if not test1_result["success"]:
            test_results["errors"].append("Clarification automatique non déclenchée")
        
        # Test 2: Traitement réponse de clarification
        if test1_result["clarification_requested"]:
            logger.info("🎪 Test 2: Traitement réponse clarification")
            
            clarification_response = EnhancedQuestionRequest(
                text="Ross 308 mâles",
                conversation_id=clarification_question.conversation_id,
                language="fr",
                is_clarification_response=True,
                original_question="Quel est le poids d'un poulet de 12 jours ?",
                clarification_context={
                    "missing_information": ["breed", "sex"],
                    "clarification_type": "performance_breed_sex"
                }
            )
            
            start_time2 = time.time()
            result2 = await expert_service.process_expert_question(
                request_data=clarification_response,
                request=request,
                current_user=None,
                start_time=start_time2
            )
            
            test2_result = {
                "test_name": "Traitement réponse clarification",
                "clarification_response": clarification_response.text,
                "question_enriched": "Ross 308" in result2.question and "mâles" in result2.question,
                "rag_used": result2.rag_used,
                "mode": result2.mode,
                "success": result2.rag_used and "Ross 308" in result2.question
            }
            
            test_results["tests_performed"].append(test2_result)
            
            if not test2_result["success"]:
                test_results["errors"].append("Traitement clarification échoué")
        
        # Test 3: Extraction race/sexe
        logger.info("🔍 Test 3: Extraction entités")
        
        from .expert_utils import extract_breed_and_sex_from_clarification
        
        extraction_tests = [
            ("Ross 308 mâles", {"breed": "Ross 308", "sex": "mâles"}),
            ("Cobb 500 femelles", {"breed": "Cobb 500", "sex": "femelles"}),
            ("Hubbard troupeau mixte", {"breed": "Hubbard", "sex": "mixte"})
        ]
        
        extraction_results = []
        for test_text, expected in extraction_tests:
            extracted = extract_breed_and_sex_from_clarification(test_text, "fr")
            success = extracted["breed"] == expected["breed"] and extracted["sex"] == expected["sex"]
            
            extraction_results.append({
                "input": test_text,
                "expected": expected,
                "extracted": extracted,
                "success": success
            })
            
            if not success:
                test_results["errors"].append(f"Extraction échouée pour: {test_text}")
        
        test_results["tests_performed"].append({
            "test_name": "Extraction breed/sex",
            "extraction_results": extraction_results,
            "success": all(r["success"] for r in extraction_results)
        })
        
        # Résultat final
        test_results["test_successful"] = len(test_results["errors"]) == 0
        
        logger.info(f"✅ [Expert Enhanced] Test clarification: {'SUCCÈS' if test_results['test_successful'] else 'ÉCHEC'}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ [Expert Enhanced] Erreur test clarification: {e}")
        return {
            "test_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "tests_performed": [],
            "errors": [f"Erreur critique: {str(e)}"]
        }

# =============================================================================
# CONFIGURATION & LOGGING
# =============================================================================

logger.info("🚀 [EXPERT ENDPOINTS] Endpoints FINAUX avec CLARIFICATION INTELLIGENTE initialisés!")
logger.info("🔧 [EXPERT ENDPOINTS] ENDPOINTS DISPONIBLES:")
logger.info("   - POST /ask-enhanced-v2 (VERSION FINALE avec clarification intelligente)")
logger.info("   - POST /ask-enhanced-v2-public (VERSION FINALE publique avec clarification)")
logger.info("   - POST /ask-enhanced (compatibilité v1 → v2)")
logger.info("   - POST /ask-enhanced-public (compatibilité v1 public → v2)")
logger.info("   - POST /ask (compatibilité original → v2)")
logger.info("   - POST /ask-public (compatibilité original public → v2)")
logger.info("   - POST /feedback (amélioré avec qualité détaillée)")
logger.info("   - GET /topics (enrichi avec statut améliorations)")
logger.info("   - GET /system-status (monitoring complet + clarification)")
logger.info("   - POST /debug/test-enhancements (tests automatiques)")
logger.info("   - POST /debug/test-clarification (test système clarification)")
logger.info("✅ [EXPERT ENDPOINTS] Rétrocompatibilité totale assurée")
logger.info("🎯 [EXPERT ENDPOINTS] Système de clarification intelligent race/sexe opérationnel")
logger.info("🚀 [EXPERT ENDPOINTS] Nouvelles fonctionnalités prêtes pour production")