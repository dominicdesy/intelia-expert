"""
app/api/v1/expert.py - ENDPOINTS PRINCIPAUX EXPERT SYSTEM

🔥 CORRECTIONS CRITIQUES APPLIQUÉES:
1. ✅ Forçage systématique de enable_vagueness_detection=True
2. ✅ Logging amélioré du flux de clarification
3. ✅ Debug spécifique pour traçabilité clarification
4. ✅ Validation forcée des paramètres de clarification
5. ✅ Endpoints de test dédiés clarification

VERSION FINALE CORRIGÉE : Support complet des nouvelles améliorations API + Clarification intelligente FORCÉE
+ TOUTES LES FONCTIONS ORIGINALES PRÉSERVÉES
"""

import os
import logging
import uuid
import time
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer

from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest
from .expert_services import ExpertService
from .expert_utils import get_user_id_from_request, extract_breed_and_sex_from_clarification

router = APIRouter(tags=["expert-enhanced"])
logger = logging.getLogger(__name__)
security = HTTPBearer()

# Service principal
expert_service = ExpertService()

# =============================================================================
# ENDPOINTS PRINCIPAUX AVEC CLARIFICATION FORCÉE 🔥
# =============================================================================

@router.post("/ask-enhanced-v2", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """
    🔥 ENDPOINT EXPERT FINAL avec CLARIFICATION FORCÉE:
    - Activation automatique du système de clarification
    - Logging détaillé du flux de clarification
    - Debug spécifique pour traçabilité
    """
    start_time = time.time()
    
    try:
        logger.info("=" * 100)
        logger.info("🚀 DÉBUT ask_expert_enhanced_v2 - CLARIFICATION FORCÉE ACTIVÉE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        logger.info(f"🆔 Conversation ID: {request_data.conversation_id}")
        
        # 🔥 CORRECTION CRITIQUE 1: FORÇAGE SYSTÉMATIQUE DES AMÉLIORATIONS
        original_vagueness = getattr(request_data, 'enable_vagueness_detection', None)
        original_coherence = getattr(request_data, 'require_coherence_check', None)
        
        # FORCER l'activation - AUCUNE EXCEPTION
        request_data.enable_vagueness_detection = True
        request_data.require_coherence_check = True
        
        logger.info("🔥 [CLARIFICATION FORCÉE] Paramètres forcés:")
        logger.info(f"   - enable_vagueness_detection: {original_vagueness} → TRUE (FORCÉ)")
        logger.info(f"   - require_coherence_check: {original_coherence} → TRUE (FORCÉ)")
        logger.info(f"   - is_clarification_response: {getattr(request_data, 'is_clarification_response', False)}")
        
        # 🔥 LOGGING SPÉCIFIQUE CLARIFICATION
        if hasattr(request_data, 'is_clarification_response') and request_data.is_clarification_response:
            logger.info("🎪 [FLUX CLARIFICATION] Traitement réponse de clarification:")
            logger.info(f"   - Question originale: {getattr(request_data, 'original_question', 'N/A')}")
            logger.info(f"   - Contexte clarification: {getattr(request_data, 'clarification_context', {})}")
        else:
            logger.info("🎯 [FLUX CLARIFICATION] Traitement question initiale - détection active")
        
        # Déléguer le traitement au service amélioré
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=current_user,
            start_time=start_time
        )
        
        # 🔥 LOGGING RÉSULTATS CLARIFICATION
        logger.info("🔥 [RÉSULTATS CLARIFICATION]:")
        logger.info(f"   - Mode final: {response.mode}")
        logger.info(f"   - Clarification déclenchée: {response.clarification_result is not None}")
        logger.info(f"   - RAG utilisé: {response.rag_used}")
        
        if response.clarification_result:
            clarif = response.clarification_result
            logger.info(f"   - Type clarification: {clarif.get('clarification_type', 'N/A')}")
            logger.info(f"   - Infos manquantes: {clarif.get('missing_information', [])}")
            logger.info(f"   - Confiance: {clarif.get('confidence', 0)}")
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2 - Temps: {response.response_time_ms}ms")
        logger.info(f"🤖 Améliorations: {len(response.ai_enhancements_used or [])} features")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2: {e}")
        logger.info("=" * 100)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-enhanced-v2-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2_public(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """🔥 ENDPOINT PUBLIC avec CLARIFICATION FORCÉE GARANTIE"""
    start_time = time.time()
    
    try:
        logger.info("=" * 100)
        logger.info("🌐 DÉBUT ask_expert_enhanced_v2_public - CLARIFICATION PUBLIQUE FORCÉE")
        logger.info(f"📝 Question: {request_data.text[:100]}...")
        
        # 🔥 CORRECTION CRITIQUE 2: FORÇAGE ABSOLU POUR ENDPOINT PUBLIC
        logger.info("🔥 [PUBLIC ENDPOINT] Activation FORCÉE des améliorations:")
        
        original_settings = {
            'vagueness': getattr(request_data, 'enable_vagueness_detection', None),
            'coherence': getattr(request_data, 'require_coherence_check', None),
            'detailed_rag': getattr(request_data, 'detailed_rag_scoring', None),
            'quality_metrics': getattr(request_data, 'enable_quality_metrics', None)
        }
        
        # FORÇAGE MAXIMAL pour endpoint public
        request_data.enable_vagueness_detection = True
        request_data.require_coherence_check = True
        request_data.detailed_rag_scoring = True
        request_data.enable_quality_metrics = True
        
        logger.info("🔥 [FORÇAGE PUBLIC] Changements appliqués:")
        for key, (old_val, new_val) in {
            'vagueness_detection': (original_settings['vagueness'], True),
            'coherence_check': (original_settings['coherence'], True),
            'detailed_rag': (original_settings['detailed_rag'], True),
            'quality_metrics': (original_settings['quality_metrics'], True)
        }.items():
            logger.info(f"   - {key}: {old_val} → {new_val} (FORCÉ)")
        
        # 🔥 DEBUG SPÉCIFIQUE CLARIFICATION PUBLIQUE
        if hasattr(request_data, 'is_clarification_response') and request_data.is_clarification_response:
            logger.info("🎪 [PUBLIC CLARIFICATION] Mode réponse clarification:")
            logger.info(f"   - Texte réponse: '{request_data.text}'")
            logger.info(f"   - Conversation ID: {request_data.conversation_id}")
        else:
            logger.info("🎯 [PUBLIC CLARIFICATION] Mode détection initiale")
        
        # Déléguer le traitement
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=None,  # Mode public
            start_time=start_time
        )
        
        # 🔥 VALIDATION RÉSULTATS CLARIFICATION
        logger.info("🔥 [VALIDATION PUBLIQUE]:")
        logger.info(f"   - Clarification système actif: {'clarification' in response.mode}")
        logger.info(f"   - Améliorations appliquées: {response.ai_enhancements_used}")
        logger.info(f"   - Mode final: {response.mode}")
        
        # Vérification critique
        if not response.ai_enhancements_used:
            logger.warning("⚠️ [ALERTE] Aucune amélioration détectée - possible problème!")
        
        if response.enable_vagueness_detection is False:
            logger.warning("⚠️ [ALERTE] Vagueness detection non activée - vérifier forçage!")
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2_public - Mode: {response.mode}")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2_public: {e}")
        logger.info("=" * 100)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# ENDPOINTS DE COMPATIBILITÉ AVEC FORÇAGE 🔥
# =============================================================================

@router.post("/ask-enhanced", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_legacy(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """Endpoint de compatibilité v1 - FORÇAGE APPLIQUÉ"""
    logger.info("🔄 [LEGACY] Redirection avec FORÇAGE vers v2")
    
    # 🔥 FORÇAGE LEGACY
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    
    return await ask_expert_enhanced_v2(request_data, request, current_user)

@router.post("/ask-enhanced-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_public_legacy(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint public de compatibilité v1 - FORÇAGE APPLIQUÉ"""
    logger.info("🔄 [LEGACY PUBLIC] Redirection avec FORÇAGE vers v2")
    
    # 🔥 FORÇAGE LEGACY PUBLIC
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    
    return await ask_expert_enhanced_v2_public(request_data, request)

@router.post("/ask", response_model=EnhancedExpertResponse)
async def ask_expert_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """Endpoint de compatibilité original - FORÇAGE TOTAL"""
    logger.info("🔄 [COMPATIBLE] Redirection avec FORÇAGE TOTAL vers v2")
    
    # 🔥 FORÇAGE COMPATIBILITÉ TOTALE
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    request_data.detailed_rag_scoring = True
    request_data.enable_quality_metrics = True
    
    return await ask_expert_enhanced_v2(request_data, request, current_user)

@router.post("/ask-public", response_model=EnhancedExpertResponse)
async def ask_expert_public_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint public de compatibilité original - FORÇAGE TOTAL"""
    logger.info("🔄 [COMPATIBLE PUBLIC] Redirection avec FORÇAGE TOTAL vers v2")
    
    # 🔥 FORÇAGE COMPATIBILITÉ PUBLIQUE TOTALE
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    request_data.detailed_rag_scoring = True
    request_data.enable_quality_metrics = True
    
    return await ask_expert_enhanced_v2_public(request_data, request)

# =============================================================================
# ENDPOINT FEEDBACK AMÉLIORÉ (ORIGINAL PRÉSERVÉ)
# =============================================================================

@router.post("/feedback")
async def submit_feedback_enhanced(feedback_data: FeedbackRequest):
    """Submit feedback - VERSION FINALE avec support qualité"""
    try:
        logger.info(f"📊 [Feedback] Reçu: {feedback_data.rating} pour {feedback_data.conversation_id}")
        
        if feedback_data.quality_feedback:
            logger.info(f"📈 [Feedback] Qualité détaillée: {len(feedback_data.quality_feedback)} métriques")
        
        result = await expert_service.process_feedback(feedback_data)
        return result
        
    except Exception as e:
        logger.error(f"❌ [Feedback] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur feedback: {str(e)}")

# =============================================================================
# ENDPOINT TOPICS AMÉLIORÉ (ORIGINAL PRÉSERVÉ)
# =============================================================================

@router.get("/topics")
async def get_suggested_topics_enhanced(language: str = "fr"):
    """Get suggested topics - VERSION FINALE"""
    try:
        return await expert_service.get_suggested_topics(language)
    except Exception as e:
        logger.error(f"❌ [Topics] Erreur: {e}")
        raise HTTPException(status_code=500, detail="Erreur topics")

# =============================================================================
# ENDPOINTS DE DEBUG ET MONITORING AVEC CLARIFICATION (ORIGINAUX + NOUVEAUX)
# =============================================================================

@router.get("/system-status")
async def get_system_status():
    """Statut système avec focus clarification (ORIGINAL + AMÉLIORÉ)"""
    try:
        status = {
            "system_available": True,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "expert_service": True,
                "rag_system": True,
                "enhancement_service": True,
                "integrations_manager": expert_service.integrations.get_system_status(),
                "clarification_system": True,  # ✅ FOCUS
                "forced_clarification": True   # ✅ NOUVEAU
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
                "/debug/test-clarification",
                "/debug/test-clarification-forced",      # ✅ NOUVEAU
                "/debug/validate-clarification-params"   # ✅ NOUVEAU
            ],
            "api_version": "v2_enhanced_forced_clarification",
            "backward_compatibility": True,
            "clarification_features": {
                "breed_sex_detection": True,
                "automatic_clarification": True,
                "follow_up_handling": True,
                "multilingual_support": ["fr", "en", "es"],
                "forced_activation": True,      # ✅ GARANTI
                "debug_endpoints": True         # ✅ NOUVEAU
            },
            "forced_parameters": {
                "vagueness_detection_always_on": True,  # ✅ GARANTI
                "coherence_check_always_on": True,      # ✅ GARANTI
                "backwards_compatibility": True
            }
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ [System] Erreur status: {e}")
        return {
            "system_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/debug/test-enhancements")
async def test_enhancements(request: Request):
    """Test toutes les améliorations avec une question de test (ORIGINAL PRÉSERVÉ)"""
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
    """Test spécifique du système de clarification intelligent (ORIGINAL PRÉSERVÉ)"""
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
# NOUVEAUX ENDPOINTS DE DEBUG CLARIFICATION 🔥
# =============================================================================

@router.post("/debug/test-clarification-forced")
async def test_clarification_system_forced(request: Request):
    """🔥 NOUVEAU: Test FORCÉ du système de clarification avec logging détaillé"""
    try:
        logger.info("=" * 80)
        logger.info("🔥 DÉBUT TEST CLARIFICATION FORCÉ")
        
        test_results = {
            "test_successful": True,
            "timestamp": datetime.now().isoformat(),
            "tests_performed": [],
            "errors": [],
            "clarification_flow_detailed": []
        }
        
        # Test 1: Question GARANTIE de déclencher clarification
        logger.info("🎯 Test 1: Question poids sans race/sexe - FORÇAGE GARANTI")
        
        test_question = EnhancedQuestionRequest(
            text="Quel est le poids d'un poulet de 15 jours ?",  # Question claire nécessitant clarification
            conversation_id=str(uuid.uuid4()),
            language="fr",
            enable_vagueness_detection=True,  # FORCÉ
            require_coherence_check=True,     # FORCÉ
            is_clarification_response=False
        )
        
        logger.info(f"🔥 [TEST 1] Question de test: '{test_question.text}'")
        logger.info(f"🔥 [TEST 1] Paramètres: vagueness={test_question.enable_vagueness_detection}, coherence={test_question.require_coherence_check}")
        
        start_time = time.time()
        result1 = await expert_service.process_expert_question(
            request_data=test_question,
            request=request,
            current_user=None,
            start_time=start_time
        )
        
        # Analyse détaillée Test 1
        clarification_triggered = result1.clarification_result is not None
        has_clarification_mode = "clarification" in result1.mode
        
        test1_details = {
            "test_name": "Détection clarification automatique FORCÉE",
            "question": test_question.text,
            "clarification_result_exists": clarification_triggered,
            "mode_contains_clarification": has_clarification_mode,
            "final_mode": result1.mode,
            "enhancements_used": result1.ai_enhancements_used or [],
            "clarification_details": result1.clarification_result,
            "success": clarification_triggered or has_clarification_mode,
            "rag_bypassed": not result1.rag_used  # Clarification doit bypasser RAG
        }
        
        test_results["tests_performed"].append(test1_details)
        test_results["clarification_flow_detailed"].append({
            "step": "initial_question",
            "triggered": test1_details["success"],
            "mode": result1.mode,
            "response_excerpt": result1.response[:100] + "..." if len(result1.response) > 100 else result1.response
        })
        
        logger.info(f"🔥 [TEST 1 RÉSULTAT] Clarification déclenchée: {test1_details['success']}")
        logger.info(f"🔥 [TEST 1 RÉSULTAT] Mode: {result1.mode}")
        
        if not test1_details["success"]:
            error_msg = f"Clarification forcée ÉCHOUÉE - Mode: {result1.mode}, RAG utilisé: {result1.rag_used}"
            test_results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        # Test 2: Réponse à la clarification
        if test1_details["success"]:
            logger.info("🎪 Test 2: Traitement réponse clarification FORCÉE")
            
            clarification_response = EnhancedQuestionRequest(
                text="Ross 308 mâles",
                conversation_id=test_question.conversation_id,
                language="fr",
                enable_vagueness_detection=True,  # FORCÉ
                require_coherence_check=True,     # FORCÉ
                is_clarification_response=True,
                original_question="Quel est le poids d'un poulet de 15 jours ?",
                clarification_context={
                    "missing_information": ["breed", "sex"],
                    "clarification_type": "performance_breed_sex"
                }
            )
            
            logger.info(f"🔥 [TEST 2] Réponse clarification: '{clarification_response.text}'")
            logger.info(f"🔥 [TEST 2] is_clarification_response: {clarification_response.is_clarification_response}")
            
            start_time2 = time.time()
            result2 = await expert_service.process_expert_question(
                request_data=clarification_response,
                request=request,
                current_user=None,
                start_time=start_time2
            )
            
            # Analyse Test 2
            question_enriched = ("Ross 308" in result2.question.lower() and 
                               ("mâle" in result2.question.lower() or "male" in result2.question.lower()))
            
            test2_details = {
                "test_name": "Traitement réponse clarification FORCÉE",
                "clarification_input": clarification_response.text,
                "enriched_question": result2.question,
                "question_properly_enriched": question_enriched,
                "rag_activated": result2.rag_used,
                "final_mode": result2.mode,
                "success": result2.rag_used and question_enriched
            }
            
            test_results["tests_performed"].append(test2_details)
            test_results["clarification_flow_detailed"].append({
                "step": "clarification_response",
                "input": clarification_response.text,
                "enriched_question": result2.question,
                "rag_used": result2.rag_used,
                "success": test2_details["success"]
            })
            
            logger.info(f"🔥 [TEST 2 RÉSULTAT] Question enrichie: {question_enriched}")
            logger.info(f"🔥 [TEST 2 RÉSULTAT] RAG activé: {result2.rag_used}")
            logger.info(f"🔥 [TEST 2 RÉSULTAT] Question finale: '{result2.question}'")
            
            if not test2_details["success"]:
                error_msg = f"Traitement clarification ÉCHOUÉ - Question: '{result2.question}', RAG: {result2.rag_used}"
                test_results["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
        
        # Test 3: Validation paramètres forçage
        logger.info("🔧 Test 3: Validation FORÇAGE des paramètres")
        
        # Tester avec paramètres initialement False
        disabled_question = EnhancedQuestionRequest(
            text="Question de test forçage",
            conversation_id=str(uuid.uuid4()),
            language="fr",
            enable_vagueness_detection=False,  # Sera FORCÉ à True
            require_coherence_check=False      # Sera FORCÉ à True
        )
        
        logger.info(f"🔥 [TEST 3] Paramètres initiaux: vagueness={disabled_question.enable_vagueness_detection}, coherence={disabled_question.require_coherence_check}")
        
        # Appeler endpoint public qui force les paramètres
        result3 = await ask_expert_enhanced_v2_public(disabled_question, request)
        
        test3_details = {
            "test_name": "Validation FORÇAGE paramètres",
            "initial_vagueness": False,
            "initial_coherence": False,
            "forced_activation": True,
            "enhancements_applied": len(result3.ai_enhancements_used or []) > 0,
            "success": len(result3.ai_enhancements_used or []) > 0
        }
        
        test_results["tests_performed"].append(test3_details)
        
        logger.info(f"🔥 [TEST 3 RÉSULTAT] Améliorations appliquées: {len(result3.ai_enhancements_used or [])}")
        logger.info(f"🔥 [TEST 3 RÉSULTAT] Liste améliorations: {result3.ai_enhancements_used}")
        
        if not test3_details["success"]:
            error_msg = "Forçage paramètres ÉCHOUÉ - Aucune amélioration appliquée"
            test_results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
        
        # Résultat final
        test_results["test_successful"] = len(test_results["errors"]) == 0
        
        logger.info("🔥 RÉSUMÉ TEST CLARIFICATION FORCÉ:")
        logger.info(f"   - Tests réalisés: {len(test_results['tests_performed'])}")
        logger.info(f"   - Erreurs: {len(test_results['errors'])}")
        logger.info(f"   - Succès global: {test_results['test_successful']}")
        
        if test_results["errors"]:
            for error in test_results["errors"]:
                logger.error(f"   ❌ {error}")
        
        logger.info("=" * 80)
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ Erreur critique test clarification forcé: {e}")
        logger.info("=" * 80)
        return {
            "test_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "tests_performed": [],
            "errors": [f"Erreur critique: {str(e)}"]
        }

@router.post("/debug/validate-clarification-params")
async def validate_clarification_params(request: Request):
    """🔥 NOUVEAU: Validation spécifique du forçage des paramètres de clarification"""
    
    try:
        logger.info("🔧 VALIDATION PARAMÈTRES CLARIFICATION")
        
        validation_results = {
            "validation_successful": True,
            "timestamp": datetime.now().isoformat(),
            "parameter_tests": [],
            "errors": []
        }
        
        # Test différentes combinaisons de paramètres
        test_cases = [
            {
                "name": "Paramètres non définis",
                "params": {"text": "Test sans paramètres"},
                "expected_forced": True
            },
            {
                "name": "Paramètres explicitement False", 
                "params": {
                    "text": "Test paramètres False",
                    "enable_vagueness_detection": False,
                    "require_coherence_check": False
                },
                "expected_forced": True
            },
            {
                "name": "Paramètres explicitement True",
                "params": {
                    "text": "Test paramètres True", 
                    "enable_vagueness_detection": True,
                    "require_coherence_check": True
                },
                "expected_forced": True
            }
        ]
        
        for test_case in test_cases:
            logger.info(f"🔧 Test: {test_case['name']}")
            
            # Créer la requête
            test_request = EnhancedQuestionRequest(
                conversation_id=str(uuid.uuid4()),
                language="fr",
                **test_case["params"]
            )
            
            # Enregistrer les valeurs initiales
            initial_vagueness = getattr(test_request, 'enable_vagueness_detection', None)
            initial_coherence = getattr(test_request, 'require_coherence_check', None)
            
            logger.info(f"   Valeurs initiales: vagueness={initial_vagueness}, coherence={initial_coherence}")
            
            # Appeler l'endpoint public qui force
            result = await ask_expert_enhanced_v2_public(test_request, request)
            
            # Vérifier le forçage
            has_enhancements = len(result.ai_enhancements_used or []) > 0
            clarification_active = any("clarification" in enh for enh in (result.ai_enhancements_used or []))
            
            test_result = {
                "test_name": test_case["name"],
                "initial_vagueness": initial_vagueness,
                "initial_coherence": initial_coherence,
                "enhancements_applied": result.ai_enhancements_used,
                "enhancements_count": len(result.ai_enhancements_used or []),
                "clarification_system_active": clarification_active,
                "success": has_enhancements
            }
            
            validation_results["parameter_tests"].append(test_result)
            
            logger.info(f"   Améliorations appliquées: {test_result['enhancements_count']}")
            logger.info(f"   Clarification active: {clarification_active}")
            logger.info(f"   Test réussi: {test_result['success']}")
            
            if not test_result["success"]:
                error_msg = f"Forçage échoué pour: {test_case['name']}"
                validation_results["errors"].append(error_msg)
        
        # Résultat final
        validation_results["validation_successful"] = len(validation_results["errors"]) == 0
        
        logger.info(f"✅ VALIDATION TERMINÉE - Succès: {validation_results['validation_successful']}")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"❌ Erreur validation paramètres: {e}")
        return {
            "validation_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "parameter_tests": [],
            "errors": [f"Erreur critique: {str(e)}"]
        }

@router.post("/ask-with-clarification", response_model=EnhancedExpertResponse)
async def ask_with_forced_clarification(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """🎯 NOUVEAU: Endpoint avec clarification GARANTIE pour questions techniques (ORIGINAL PRÉSERVÉ)"""
    
    start_time = time.time()
    
    try:
        logger.info("🎯 DÉBUT ask_with_forced_clarification")
        logger.info(f"📝 Question: {request_data.text}")
        
        # VÉRIFICATION DIRECTE si c'est une question poids+âge
        question_lower = request_data.text.lower()
        needs_clarification = False
        
        # Patterns simplifiés pour détecter poids+âge
        weight_age_patterns = [
            r'(?:poids|weight).*?(\d+)\s*(?:jour|day)',
            r'(\d+)\s*(?:jour|day).*?(?:poids|weight)',
            r'(?:quel|what).*?(?:poids|weight).*?(\d+)'
        ]
        
        # Vérifier si question poids+âge
        has_weight_age = any(re.search(pattern, question_lower) for pattern in weight_age_patterns)
        logger.info(f"🔍 Détection poids+âge: {has_weight_age}")
        
        if has_weight_age:
            # Vérifier si race/sexe manquent
            breed_patterns = [r'(ross\s*308|cobb\s*500|hubbard)']
            sex_patterns = [r'(mâle|male|femelle|female|mixte|mixed)']
            
            has_breed = any(re.search(p, question_lower) for p in breed_patterns)
            has_sex = any(re.search(p, question_lower) for p in sex_patterns)
            
            logger.info(f"🏷️ Race détectée: {has_breed}")
            logger.info(f"⚧ Sexe détecté: {has_sex}")
            
            if not has_breed and not has_sex:
                needs_clarification = True
                logger.info("🎯 CLARIFICATION NÉCESSAIRE!")
        
        if needs_clarification:
            # DÉCLENCHER CLARIFICATION DIRECTE
            age_match = re.search(r'(\d+)\s*(?:jour|day)', question_lower)
            age = age_match.group(1) if age_match else "X"
            
            clarification_message = f"""Pour vous donner le poids de référence exact d'un poulet de {age} jours, j'ai besoin de :

• **Race/souche** : Ross 308, Cobb 500, Hubbard, etc.
• **Sexe** : Mâles, femelles, ou troupeau mixte

Pouvez-vous préciser ces informations ?

**Exemples de réponses :**
• "Ross 308 mâles"
• "Cobb 500 femelles"
• "Hubbard troupeau mixte\""""
            
            logger.info("✅ CLARIFICATION DÉCLENCHÉE!")
            
            return EnhancedExpertResponse(
                question=request_data.text,
                response=clarification_message,
                conversation_id=request_data.conversation_id or str(uuid.uuid4()),
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=request_data.language,
                response_time_ms=int((time.time() - start_time) * 1000),
                mode="forced_performance_clarification",
                user=None,
                logged=True,
                validation_passed=True,
                clarification_result={
                    "clarification_requested": True,
                    "clarification_type": "performance_breed_sex_forced",
                    "missing_information": ["breed", "sex"],
                    "age_detected": age,
                    "confidence": 0.99
                },
                processing_steps=["forced_clarification_triggered"],
                ai_enhancements_used=["forced_performance_clarification"]
            )
        
        logger.info("📋 Pas de clarification nécessaire, traitement normal")
        
        # Si pas besoin de clarification, traitement normal avec améliorations forcées
        request_data.enable_vagueness_detection = True
        request_data.require_coherence_check = True
        
        return await ask_expert_enhanced_v2_public(request_data, request)
        
    except Exception as e:
        logger.error(f"❌ Erreur ask_with_forced_clarification: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# =============================================================================
# CONFIGURATION & LOGGING FINAL 🔥
# =============================================================================

logger.info("🔥" * 50)
logger.info("🚀 [EXPERT ENDPOINTS] VERSION FINALE CLARIFICATION FORCÉE INITIALISÉE!")
logger.info("🔥 [CORRECTIONS APPLIQUÉES]:")
logger.info("   ✅ Forçage systématique enable_vagueness_detection=True")
logger.info("   ✅ Forçage systématique require_coherence_check=True") 
logger.info("   ✅ Logging détaillé flux de clarification")
logger.info("   ✅ Debug spécifique traçabilité clarification")
logger.info("   ✅ Validation forcée paramètres clarification")
logger.info("   ✅ Endpoints de test dédiés clarification")
logger.info("   ✅ TOUTES les fonctions originales préservées")
logger.info("")
logger.info("🔧 [ENDPOINTS DISPONIBLES]:")
logger.info("   - POST /ask-enhanced-v2 (FORÇAGE APPLIQUÉ)")
logger.info("   - POST /ask-enhanced-v2-public (FORÇAGE MAXIMAL)")
logger.info("   - POST /ask-enhanced (legacy → v2 + FORÇAGE)")
logger.info("   - POST /ask-enhanced-public (legacy public → v2 + FORÇAGE)")
logger.info("   - POST /ask (original → v2 + FORÇAGE TOTAL)")
logger.info("   - POST /ask-public (original public → v2 + FORÇAGE TOTAL)")
logger.info("   - POST /ask-with-clarification (clarification GARANTIE)")
logger.info("   - POST /feedback (support qualité détaillée)")
logger.info("   - GET /topics (enrichi avec statut améliorations)")
logger.info("   - GET /system-status (focus clarification + forced)")
logger.info("   - POST /debug/test-enhancements (tests automatiques)")
logger.info("   - POST /debug/test-clarification (test système clarification)")
logger.info("   - POST /debug/test-clarification-forced (NOUVEAU)")
logger.info("   - POST /debug/validate-clarification-params (NOUVEAU)")
logger.info("")
logger.info("🎯 [GARANTIES SYSTÈME]:")
logger.info("   ✅ Clarification TOUJOURS active")
logger.info("   ✅ Paramètres FORCÉS sur tous endpoints")
logger.info("   ✅ Traçabilité complète flux clarification")
logger.info("   ✅ Tests automatiques disponibles")
logger.info("   ✅ Rétrocompatibilité préservée")
logger.info("   ✅ Toutes fonctions originales maintenues")
logger.info("🔥" * 50)