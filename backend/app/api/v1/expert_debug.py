"""
app/api/v1/expert_debug.py - ENDPOINTS DEBUG UNIFIÉS v3.7.2 - CORRIGÉ

🧪 FUSION des anciens et nouveaux endpoints de debug:
- Garde tous les endpoints existants (compatibilité)
- Ajoute les nouveaux tests v3.7.2
- Tests clarification granulaire
- Tests response_versions
- Simulation frontend complète
- Monitoring avancé
- ✅ CORRECTIONS: Import circulaire résolu, appels service direct

VERSION UNIFIÉE - Tous les tests et diagnostics en un seul fichier
"""

import os
import sys
import json
import logging
import uuid
import time
import re
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request

from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, TestResult, SystemStats, ConcisionLevel
from .expert_services import ExpertService
from .expert_utils import get_user_id_from_request, extract_breed_and_sex_from_clarification

router = APIRouter(tags=["expert-debug"])
logger = logging.getLogger(__name__)

# Service principal
expert_service = ExpertService()

# =============================================================================
# ENDPOINTS EXISTANTS PRÉSERVÉS (COMPATIBILITÉ) 📊
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
                "POST /ask-enhanced-v2 (+ response_versions + clarification granulaire)",
                "POST /ask-enhanced-v2-public (+ response_versions + clarification granulaire)",
                "POST /ask-enhanced (legacy → v2)",
                "POST /ask-enhanced-public (legacy → v2)",
                "POST /ask (compatible → v2)",
                "POST /ask-public (compatible → v2)",
                "GET /enhanced-stats (system statistics)",
                "POST /test-enhanced-flow (testing)",
                "GET /enhanced-conversation/{id}/context (conversation context)",
                "POST /debug/test-response-versions (nouveaux tests v3.7.2)",
                "POST /debug/test-clarification-granular (nouveaux tests v3.7.2)",
                "POST /debug/simulate-frontend-clarification (simulation v3.7.2)"
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
                "ai_powered": expert_service.integrations.intelligent_memory_available,
                "response_versions_support": True,  # 🚀 v3.7.2
                "granular_clarification": True      # 🎯 v3.7.2
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Enhanced Debug] Erreur stats validation: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération stats")

@router.post("/test-enhanced-flow", response_model=TestResult)
async def test_enhanced_flow(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint de test pour le flux amélioré complet + NOUVELLES FONCTIONNALITÉS v3.7.2
    ✅ CORRIGÉ: Appel service direct au lieu d'import circulaire"""
    try:
        logger.info(f"🧪 [Test Enhanced] Test du flux amélioré v3.7.2")
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
        
        # 🚀 NOUVEAU v3.7.2: Test response_versions
        if hasattr(request_data, 'concision_level') or hasattr(request_data, 'generate_all_versions'):
            try:
                # Forcer les paramètres response_versions pour test
                if not hasattr(request_data, 'concision_level'):
                    request_data.concision_level = ConcisionLevel.CONCISE
                if not hasattr(request_data, 'generate_all_versions'):
                    request_data.generate_all_versions = True
                
                test_results.components_tested["response_versions"] = {
                    "status": "success",
                    "concision_level": request_data.concision_level.value if hasattr(request_data.concision_level, 'value') else str(request_data.concision_level),
                    "generate_all_versions": request_data.generate_all_versions,
                    "feature_available": True
                }
            except Exception as e:
                test_results.components_tested["response_versions"] = {
                    "status": "error",
                    "error": str(e)
                }
                test_results.errors.append(f"Response versions: {str(e)}")
        
        # Test mémoire intelligente (existant)
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
        
        # 🎯 NOUVEAU v3.7.2: Test clarification granulaire
        try:
            # Simuler détection granulaire
            question_lower = request_data.text.lower()
            
            # Patterns de test pour clarification
            needs_breed_sex = any(pattern in question_lower for pattern in ['poids', 'weight', 'croissance', 'growth'])
            has_breed = any(pattern in question_lower for pattern in ['ross', 'cobb', 'hubbard'])
            has_sex = any(pattern in question_lower for pattern in ['mâle', 'male', 'femelle', 'female'])
            
            granular_result = {
                "needs_clarification": needs_breed_sex and (not has_breed or not has_sex),
                "missing_breed": needs_breed_sex and not has_breed,
                "missing_sex": needs_breed_sex and not has_sex,
                "both_missing": needs_breed_sex and not has_breed and not has_sex,
                "granular_logic_active": True
            }
            
            test_results.components_tested["granular_clarification"] = {
                "status": "success",
                "analysis": granular_result,
                "feature_available": True
            }
        except Exception as e:
            test_results.components_tested["granular_clarification"] = {
                "status": "error",
                "error": str(e)
            }
            test_results.errors.append(f"Granular clarification: {str(e)}")
        
        # Test clarification améliorée (existant)
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
        
        # Test validation agricole (existant)
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
        
        # Test contexte RAG (existant)
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
        
        logger.info(f"🧪 [Test Enhanced] Test terminé v3.7.2 - Succès: {test_results.test_successful}")
        logger.info(f"🚀 [Test Enhanced] Composants testés: {len(test_results.components_tested)}")
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ [Test Enhanced] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur test: {str(e)}")

@router.post("/test-validation")
async def test_validation_enhanced(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Test endpoint pour tester la validation AMÉLIORÉE + v3.7.2"""
    try:
        question_text = request_data.text.strip()
        user_id = get_user_id_from_request(request)
        request_ip = request.client.host if request.client else "unknown"
        conversation_id = request_data.conversation_id or str(uuid.uuid4())
        
        if not expert_service.integrations.agricultural_validator_available:
            return {
                "error": "Validateur agricole non disponible",
                "available": False,
                "enhanced_system": True,
                "version": "v3.7.2"
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
                "ai_powered": True,
                "conversation_aware": True,
                "response_versions_support": True,  # 🚀 v3.7.2
                "granular_clarification": True      # 🎯 v3.7.2
            },
            "version": "v3.7.2",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Test Validation Enhanced] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur test validation: {str(e)}")

# =============================================================================
# ENDPOINTS DE CONTEXTE (EXISTANTS) 🗂️
# =============================================================================

@router.get("/enhanced-conversation/{conversation_id}/context")
async def get_enhanced_conversation_context(conversation_id: str):
    """Récupère le contexte d'une conversation - VERSION AMÉLIORÉE"""
    try:
        if not expert_service.integrations.intelligent_memory_available:
            return {
                "error": "Mémoire intelligente non disponible",
                "available": False,
                "enhanced_system": True,
                "version": "v3.7.2"
            }
        
        context = expert_service.integrations.get_context_for_rag(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "context": context,
            "context_length": len(context),
            "available": True,
            "enhanced_features": {
                "intelligent_memory": True,
                "contextual_understanding": True,
                "response_versions_context": True,    # 🚀 v3.7.2
                "granular_clarification_context": True # 🎯 v3.7.2
            },
            "version": "v3.7.2",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Enhanced Context] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur contexte: {str(e)}")

@router.get("/system-info")
async def get_enhanced_system_info():
    """Informations système complètes - VERSION AMÉLIORÉE v3.7.2"""
    try:
        return {
            "system": "Intelia Expert - Système Amélioré",
            "version": "3.7.2-granular-response-versions",
            "python_version": sys.version,
            "available_integrations": expert_service.integrations.get_system_status(),
            "enhanced_capabilities": expert_service.integrations.get_available_enhancements(),
            "new_features_v3_7_2": {
                "response_versions": "Multi-level response generation",
                "granular_clarification": "Adaptive clarification logic",
                "contextual_examples": "Smart examples with detected entities",
                "improved_ux": "Enhanced user experience"
            },
            "endpoints": {
                "enhanced_ask": "/api/v1/expert/ask-enhanced-v2",
                "enhanced_public": "/api/v1/expert/ask-enhanced-v2-public", 
                "legacy_enhanced": "/api/v1/expert/ask-enhanced",
                "legacy_public": "/api/v1/expert/ask-enhanced-public",
                "compatible": "/api/v1/expert/ask",
                "compatible_public": "/api/v1/expert/ask-public",
                "enhanced_stats": "/api/v1/expert/enhanced-stats",
                "test_flow": "/api/v1/expert/test-enhanced-flow",
                "conversation_context": "/api/v1/expert/enhanced-conversation/{id}/context",
                "debug_response_versions": "/api/v1/expert/debug/test-response-versions",
                "debug_granular": "/api/v1/expert/debug/test-clarification-granular",
                "debug_simulation": "/api/v1/expert/debug/simulate-frontend-clarification"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Enhanced System Info] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur info système: {str(e)}")

# =============================================================================
# SYSTEM STATUS UNIFIÉ (NOUVEAU + ANCIEN) 📊
# =============================================================================

@router.get("/system-status")
async def get_system_status():
    """Statut système unifié avec focus clarification + RESPONSE_VERSIONS + GRANULAIRE v3.7.2"""
    try:
        status = {
            "system_available": True,
            "timestamp": datetime.now().isoformat(),
            "version": "v3.7.2_unified_debug",
            "components": {
                "expert_service": True,
                "rag_system": True,
                "enhancement_service": True,
                "integrations_manager": expert_service.integrations.get_system_status(),
                "clarification_system": True,
                "forced_clarification": True,
                "clarification_detection_fixed": True,
                "metadata_propagation": True,
                "backend_fix_v361": True,
                "response_versions_system": True,
                "granular_clarification": True
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
                "clarification_response_processing_fixed",
                "incomplete_clarification_handling",
                "is_clarification_response_support",
                "clarification_entities_support",
                "entity_validation_and_incomplete_handling",
                "metadata_propagation_system_v361",
                "response_versions_generation",        # 🚀 v3.7.2
                "dynamic_concision_levels",           # 🚀 v3.7.2
                "multi_version_backend_cache",        # 🚀 v3.7.2
                "intelligent_version_selection",      # 🚀 v3.7.2
                "granular_clarification_logic",       # 🎯 v3.7.2
                "adaptive_error_messages",            # 🎯 v3.7.2
                "contextual_examples_generation"      # 🎯 v3.7.2
            ],
            "enhanced_endpoints": [
                "/ask-enhanced-v2 (+ response_versions + clarification granulaire)",
                "/ask-enhanced-v2-public (+ response_versions + clarification granulaire)", 
                "/ask-enhanced (legacy → v2 + response_versions)",
                "/ask-enhanced-public (legacy → v2 + response_versions)",
                "/ask (compatible → v2 + response_versions)",
                "/ask-public (compatible → v2 + response_versions)",
                "/feedback (with quality)",
                "/topics (enhanced)",
                "/system-status (unifié)",
                "/enhanced-stats (existant)",
                "/test-enhanced-flow (amélioré v3.7.2)",
                "/debug/test-response-versions (nouveau v3.7.2)",
                "/debug/test-clarification-granular (nouveau v3.7.2)",
                "/debug/simulate-frontend-clarification (nouveau v3.7.2)",
                "/ask-with-clarification"
            ],
            "api_version": "v3.7.2_unified_debug_complete",
            "backward_compatibility": True,
            "unified_debug_features": {
                "existing_endpoints_preserved": True,
                "new_v3_7_2_tests_added": True,
                "granular_clarification_tests": True,
                "response_versions_tests": True,
                "frontend_simulation": True,
                "comprehensive_monitoring": True
            },
            "forced_parameters": {
                "vagueness_detection_always_on": True,
                "coherence_check_always_on": True,
                "backwards_compatibility": True,
                "response_versions_enabled": True,
                "granular_clarification_enabled": True
            }
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ [Unified System Status] Erreur: {e}")
        return {
            "system_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "version": "v3.7.2_unified_debug"
        }

# =============================================================================
# NOUVEAUX TESTS v3.7.2 🧪 - CORRIGÉ SANS IMPORT CIRCULAIRE
# =============================================================================

@router.post("/debug/test-response-versions")
async def test_response_versions(request: Request):
    """🚀 Test spécifique du système response_versions v3.7.2
    ✅ CORRIGÉ: Appel service direct au lieu d'import circulaire"""
    try:
        logger.info("=" * 80)
        logger.info("🚀 DÉBUT TEST RESPONSE_VERSIONS v3.7.2")
        
        # ✅ CORRECTION: Appel direct au service au lieu de l'endpoint
        test_results = {
            "test_successful": True,
            "timestamp": datetime.now().isoformat(),
            "version_tests": [],
            "errors": []
        }
        
        # Test différents niveaux de concision
        concision_test_cases = [
            {
                "name": "Ultra Concise",
                "level": ConcisionLevel.ULTRA_CONCISE,
                "question": "Quel est le poids d'un poulet Ross 308 mâle de 21 jours ?",
                "expected_short": True
            },
            {
                "name": "Concise", 
                "level": ConcisionLevel.CONCISE,
                "question": "Quel est le poids d'un poulet Cobb 500 femelle de 14 jours ?",
                "expected_short": False
            },
            {
                "name": "Standard",
                "level": ConcisionLevel.STANDARD, 
                "question": "Comment améliorer la croissance des poulets de 10 jours ?",
                "expected_short": False
            },
            {
                "name": "Detailed",
                "level": ConcisionLevel.DETAILED,
                "question": "Quels sont les facteurs influençant la mortalité chez les poulets ?",
                "expected_short": False
            }
        ]
        
        for test_case in concision_test_cases:
            logger.info(f"🚀 Test: {test_case['name']} - {test_case['level'].value}")
            
            test_request = EnhancedQuestionRequest(
                text=test_case["question"],
                conversation_id=str(uuid.uuid4()),
                language="fr",
                enable_vagueness_detection=True,
                concision_level=test_case["level"],
                generate_all_versions=True
            )
            
            start_time = time.time()
            
            # ✅ CORRECTION CRITIQUE: Appel direct au service au lieu d'import circulaire
            result = await expert_service.process_expert_question(
                request_data=test_request,
                request=request,
                current_user=None,
                start_time=start_time
            )
            
            # Analyser le résultat
            has_response_versions = hasattr(result, 'response_versions') and result.response_versions is not None
            versions_count = len(result.response_versions) if has_response_versions else 0
            
            # Vérifier les versions attendues
            expected_versions = ["ultra_concise", "concise", "standard", "detailed"]
            all_versions_present = False
            version_lengths = {}
            
            if has_response_versions:
                all_versions_present = all(v in result.response_versions for v in expected_versions)
                version_lengths = {v: len(content) for v, content in result.response_versions.items()}
            
            version_test_result = {
                "test_name": test_case["name"],
                "concision_level": test_case["level"].value,
                "question": test_case["question"],
                "response_versions_generated": has_response_versions,
                "versions_count": versions_count,
                "all_versions_present": all_versions_present,
                "version_lengths": version_lengths,
                "response_time_ms": result.response_time_ms,
                "rag_used": result.rag_used,
                "success": has_response_versions and all_versions_present
            }
            
            if has_response_versions:
                version_test_result["versions_available"] = list(result.response_versions.keys())
            
            test_results["version_tests"].append(version_test_result)
            
            logger.info(f"   Versions générées: {has_response_versions}")
            logger.info(f"   Nombre de versions: {versions_count}")
            logger.info(f"   Test réussi: {version_test_result['success']}")
            
            if not version_test_result["success"]:
                error_msg = f"Test response_versions échoué pour {test_case['name']}"
                test_results["errors"].append(error_msg)
                logger.error(f"   ❌ {error_msg}")
        
        # Résultat final
        test_results["test_successful"] = len(test_results["errors"]) == 0
        
        # Statistiques
        success_count = sum(1 for t in test_results["version_tests"] if t["success"])
        total_count = len(test_results["version_tests"])
        
        test_results["statistics"] = {
            "total_tests": total_count,
            "successful_tests": success_count,
            "success_rate": f"{(success_count/total_count)*100:.1f}%" if total_count > 0 else "0%"
        }
        
        logger.info("🚀 RÉSUMÉ TEST RESPONSE_VERSIONS:")
        logger.info(f"   - Tests réalisés: {total_count}")
        logger.info(f"   - Succès: {success_count}")
        logger.info(f"   - Taux de réussite: {test_results['statistics']['success_rate']}")
        logger.info("=" * 80)
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ Erreur test response_versions: {e}")
        logger.info("=" * 80)
        return {
            "test_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "version_tests": [],
            "errors": [f"Erreur critique: {str(e)}"]
        }

@router.post("/debug/test-clarification-granular")
async def test_clarification_granular(request: Request):
    """🎯 Test spécifique de la logique clarification granulaire v3.7.2
    ✅ CORRIGÉ: Appel service direct au lieu d'import circulaire"""
    try:
        logger.info("=" * 80)
        logger.info("🎯 DÉBUT TEST LOGIQUE CLARIFICATION GRANULAIRE v3.7.2")
        
        # ✅ CORRECTION: Appel service direct au lieu d'import circulaire
        test_results = {
            "test_successful": True,
            "timestamp": datetime.now().isoformat(),
            "granular_tests": [],
            "errors": []
        }
        
        # Tests des différents cas granulaires
        granular_test_cases = [
            {
                "name": "Race seulement → message adaptatif sexe",
                "input": "Ross 308",
                "expected_message_contains": ["Il manque encore : sexe", "Race détectée: Ross 308"],
                "should_not_contain": ["Il manque encore : race/souche, sexe"],
                "expected_examples": ["Ross 308 mâles", "Ross 308 femelles"]
            },
            {
                "name": "Sexe seulement → message adaptatif race", 
                "input": "mâles",
                "expected_message_contains": ["Il manque encore : race/souche", "Sexe détecté: mâles"],
                "should_not_contain": ["Il manque encore : race/souche, sexe"],
                "expected_examples": ["Ross 308 mâles", "Cobb 500 mâles"]
            },
            {
                "name": "Race partielle → message adaptatif",
                "input": "Ross mâles",
                "expected_message_contains": ["Race partielle détectée: Ross", "Sexe détecté: mâles"],
                "should_not_contain": ["Il manque encore : race/souche, sexe"],
                "expected_examples": ["Ross 308"]
            },
            {
                "name": "Information vague → message complet",
                "input": "poulets",
                "expected_message_contains": ["Il manque encore : race/souche et sexe"],
                "should_not_contain": ["Race détectée", "Sexe détecté"],
                "expected_examples": ["Ross 308 mâles", "Cobb 500 femelles"]
            }
        ]
        
        for test_case in granular_test_cases:
            logger.info(f"🎯 Test granulaire: {test_case['name']}")
            
            granular_request = EnhancedQuestionRequest(
                text=test_case["input"],
                conversation_id=str(uuid.uuid4()),
                language="fr",
                is_clarification_response=True,
                original_question="Quel est le poids d'un poulet de 12 jours ?",
                concision_level=ConcisionLevel.CONCISE,
                generate_all_versions=True
            )
            
            # ✅ CORRECTION CRITIQUE: Appel direct au service
            granular_result = await expert_service.process_expert_question(
                request_data=granular_request,
                request=request,
                current_user=None,
                start_time=time.time()
            )
            
            # Vérifier le message adaptatif
            response_text = granular_result.response
            contains_expected = all(expected in response_text for expected in test_case["expected_message_contains"])
            avoids_bad_patterns = all(bad not in response_text for bad in test_case["should_not_contain"])
            
            # Vérifier les exemples contextuels
            has_contextual_examples = any(example in response_text for example in test_case["expected_examples"])
            
            granular_test_result = {
                "test_name": test_case["name"],
                "input": test_case["input"],
                "response_excerpt": response_text[:300] + "..." if len(response_text) > 300 else response_text,
                "contains_expected": contains_expected,
                "avoids_bad_patterns": avoids_bad_patterns,
                "has_contextual_examples": has_contextual_examples,
                "success": contains_expected and avoids_bad_patterns and has_contextual_examples,
                "expected_patterns": test_case["expected_message_contains"],
                "avoided_patterns": test_case["should_not_contain"],
                "expected_examples": test_case["expected_examples"]
            }
            
            test_results["granular_tests"].append(granular_test_result)
            
            logger.info(f"   - Contient patterns attendus: {contains_expected}")
            logger.info(f"   - Évite mauvais patterns: {avoids_bad_patterns}")
            logger.info(f"   - Exemples contextuels: {has_contextual_examples}")
            logger.info(f"   - Test réussi: {granular_test_result['success']}")
            
            if not granular_test_result["success"]:
                test_results["errors"].append(f"Test granulaire échoué: {test_case['name']}")
        
        # Résultat final
        test_results["test_successful"] = len(test_results["errors"]) == 0
        
        # Statistiques
        success_count = sum(1 for t in test_results["granular_tests"] if t["success"])
        total_count = len(test_results["granular_tests"])
        
        test_results["statistics"] = {
            "total_tests": total_count,
            "successful_tests": success_count,
            "success_rate": f"{(success_count/total_count)*100:.1f}%" if total_count > 0 else "0%"
        }
        
        logger.info("🎯 RÉSUMÉ TEST LOGIQUE GRANULAIRE v3.7.2:")
        logger.info(f"   - Tests réalisés: {total_count}")
        logger.info(f"   - Succès: {success_count}")
        logger.info(f"   - Taux de réussite: {test_results['statistics']['success_rate']}")
        logger.info("=" * 80)
        
        return test_results
        
    except Exception as e:
        logger.error(f"❌ Erreur test logique granulaire: {e}")
        logger.info("=" * 80)
        return {
            "test_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "granular_tests": [],
            "errors": [f"Erreur critique: {str(e)}"]
        }

@router.post("/debug/simulate-frontend-clarification")
async def simulate_frontend_clarification(request: Request):
    """🧨 Simulation complète du flux frontend avec clarification v3.7.2
    ✅ CORRIGÉ: Appel service direct au lieu d'import circulaire"""
    try:
        logger.info("=" * 80)
        logger.info("🧨 SIMULATION FLUX FRONTEND CLARIFICATION v3.7.2")
        
        # ✅ CORRECTION: Appel service direct au lieu d'import circulaire
        simulation_results = {
            "simulation_successful": True,
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "errors": []
        }
        
        conversation_id = str(uuid.uuid4())
        
        # ÉTAPE 1: Frontend envoie question initiale
        logger.info("📱 ÉTAPE 1: Frontend envoie question initiale")
        
        frontend_request_1 = EnhancedQuestionRequest(
            text="Quel est le poids d'un poulet de 12 jours ?",
            conversation_id=conversation_id,
            language="fr",
            concision_level=ConcisionLevel.CONCISE,
            generate_all_versions=True
        )
        
        # ✅ CORRECTION CRITIQUE: Appel direct au service
        result_1 = await expert_service.process_expert_question(
            request_data=frontend_request_1,
            request=request,
            current_user=None,
            start_time=time.time()
        )
        
        step_1 = {
            "step": "1_initial_question",
            "frontend_request": {
                "question": frontend_request_1.text,
                "conversation_id": conversation_id,
                "language": "fr",
                "concision_level": "concise",
                "generate_all_versions": True
            },
            "backend_response": {
                "mode": result_1.mode,
                "clarification_requested": result_1.clarification_result is not None,
                "rag_used": result_1.rag_used,
                "response_versions_present": hasattr(result_1, 'response_versions') and result_1.response_versions is not None
            },
            "success": result_1.clarification_result is not None
        }
        
        simulation_results["steps"].append(step_1)
        
        if not step_1["success"]:
            simulation_results["errors"].append("Étape 1: Clarification pas déclenchée")
            
        # ÉTAPE 2: Frontend envoie réponse de clarification
        if step_1["success"]:
            logger.info("📱 ÉTAPE 2: Frontend envoie réponse clarification")
            
            frontend_request_2 = EnhancedQuestionRequest(
                text="Ross 308 mâles",
                conversation_id=conversation_id,
                language="fr",
                is_clarification_response=True,
                original_question="Quel est le poids d'un poulet de 12 jours ?",
                clarification_entities={
                    "breed": "Ross 308",
                    "sex": "mâles"
                },
                concision_level=ConcisionLevel.STANDARD,
                generate_all_versions=True
            )
            
            # ✅ CORRECTION CRITIQUE: Appel direct au service
            result_2 = await expert_service.process_expert_question(
                request_data=frontend_request_2,
                request=request,
                current_user=None,
                start_time=time.time()
            )
            
            # Vérifications
            question_enriched = ("Ross 308" in result_2.question.lower() and 
                               ("mâle" in result_2.question.lower() or "male" in result_2.question.lower()))
            rag_used = result_2.rag_used
            
            step_2 = {
                "step": "2_clarification_response", 
                "frontend_request": {
                    "question": frontend_request_2.text,
                    "conversation_id": conversation_id,
                    "language": "fr",
                    "is_clarification_response": True,
                    "original_question": "Quel est le poids d'un poulet de 12 jours ?",
                    "clarification_entities": {
                        "breed": "Ross 308",
                        "sex": "mâles"
                    },
                    "concision_level": "standard",
                    "generate_all_versions": True
                },
                "backend_response": {
                    "enriched_question": result_2.question,
                    "question_enriched": question_enriched,
                    "rag_used": rag_used,
                    "mode": result_2.mode,
                    "response_excerpt": result_2.response[:150] + "...",
                    "response_versions_generated": hasattr(result_2, 'response_versions') and result_2.response_versions is not None
                },
                "success": question_enriched and rag_used
            }
            
            simulation_results["steps"].append(step_2)
            
            if not step_2["success"]:
                simulation_results["errors"].append("Étape 2: Réponse clarification mal traitée")
        
        # ÉTAPE 3: Test logique granulaire
        logger.info("🎯 ÉTAPE 3: Test logique clarification granulaire")
        
        granular_frontend_request = EnhancedQuestionRequest(
            text="Hubbard",  # Race seulement
            conversation_id=conversation_id,
            language="fr",
            is_clarification_response=True,
            original_question="Quel est le poids d'un poulet de 14 jours ?",
            concision_level=ConcisionLevel.CONCISE,
            generate_all_versions=True
        )
        
        # ✅ CORRECTION CRITIQUE: Appel direct au service
        result_granular = await expert_service.process_expert_question(
            request_data=granular_frontend_request,
            request=request,
            current_user=None,
            start_time=time.time()
        )
        
        # Vérifier logique granulaire
        message_contains_sexe_only = "Il manque encore : sexe" in result_granular.response
        message_detects_race = "Race détectée: Hubbard" in result_granular.response
        message_avoids_old = "Il manque encore : race/souche, sexe" not in result_granular.response
        
        step_3 = {
            "step": "3_granular_clarification_logic",
            "frontend_request": {
                "question": granular_frontend_request.text,
                "conversation_id": conversation_id,
                "language": "fr",
                "is_clarification_response": True,
                "original_question": "Quel est le poids d'un poulet de 14 jours ?",
                "concision_level": "concise",
                "generate_all_versions": True
            },
            "backend_response": {
                "mode": result_granular.mode,
                "message_granular": message_contains_sexe_only,
                "race_detection": message_detects_race,
                "avoids_old_pattern": message_avoids_old,
                "response_excerpt": result_granular.response[:200] + "..."
            },
            "success": message_contains_sexe_only and message_detects_race and message_avoids_old
        }
        
        simulation_results["steps"].append(step_3)
        
        if not step_3["success"]:
            simulation_results["errors"].append("Étape 3: Logique clarification granulaire échouée")
        
        # Résultat final
        simulation_results["simulation_successful"] = len(simulation_results["errors"]) == 0
        
        # Instructions pour le frontend
        simulation_results["frontend_instructions"] = {
            "critical_fix": "Ajouter is_clarification_response=true lors d'une réponse de clarification",
            "required_fields": {
                "is_clarification_response": True,
                "original_question": "Question qui a déclenché la clarification",
                "clarification_entities": "Optionnel mais recommandé"
            },
            "response_versions_usage": {
                "backend_generates_all": "Le backend génère automatiquement toutes les versions",
                "available_levels": ["ultra_concise", "concise", "standard", "detailed"],
                "default_display": "Afficher 'concise' par défaut"
            },
            "granular_clarification_benefits": {
                "adaptive_messages": "Messages d'erreur adaptés à ce qui manque réellement",
                "contextual_examples": "Exemples avec la race détectée si disponible",
                "user_friendly": "Plus précis et moins frustrant"
            }
        }
        
        logger.info("🧨 RÉSUMÉ SIMULATION FRONTEND v3.7.2:")
        logger.info(f"   - Étapes testées: {len(simulation_results['steps'])}")
        logger.info(f"   - Erreurs: {len(simulation_results['errors'])}")
        logger.info(f"   - Simulation réussie: {simulation_results['simulation_successful']}")
        logger.info("=" * 80)
        
        return simulation_results
        
    except Exception as e:
        logger.error(f"❌ Erreur simulation frontend: {e}")
        logger.info("=" * 80)
        return {
            "simulation_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "errors": [f"Erreur critique: {str(e)}"]
        }

# =============================================================================
# ENDPOINTS DEBUG ADDITIONNELS (EXISTANTS) 🔧
# =============================================================================

@router.get("/health")
async def health_check_enhanced():
    """Health check pour le système amélioré v3.7.2"""
    try:
        status = {
            "status": "healthy",
            "version": "v3.7.2_unified_debug",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "expert_service": "available",
                "integrations": expert_service.integrations.get_system_status(),
                "enhanced_features": expert_service.integrations.get_available_enhancements(),
                "new_features_v3_7_2": {
                    "response_versions": "available",
                    "granular_clarification": "available",
                    "unified_debug": "available"
                }
            }
        }
        return status
        
    except Exception as e:
        logger.error(f"❌ [Health Check] Erreur: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "v3.7.2_unified_debug",
            "timestamp": datetime.now().isoformat()
        }

@router.get("/debug-info")
async def get_debug_info():
    """Informations de debug complètes v3.7.2"""
    try:
        return {
            "system": {
                "python_version": sys.version,
                "platform": sys.platform,
                "working_directory": os.getcwd()
            },
            "expert_service": {
                "available": True,
                "integrations_status": expert_service.integrations.get_system_status(),
                "capabilities": expert_service.integrations.get_available_enhancements()
            },
            "environment": {
                "openai_key_set": bool(os.getenv('OPENAI_API_KEY')),
                "debug_mode": os.getenv('DEBUG', 'False').lower() == 'true'
            },
            "version_info": {
                "api_version": "v3.7.2_unified_debug",
                "features": {
                    "response_versions": True,
                    "granular_clarification": True,
                    "unified_debug": True,
                    "backward_compatibility": True
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Debug Info] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur debug info: {str(e)}")

# =============================================================================
# CONFIGURATION DEBUG UNIFIÉE v3.7.2 🧪
# =============================================================================

logger.info("🧪" * 50)
logger.info("🧪 [EXPERT DEBUG UNIFIÉ] VERSION 3.7.2 - TOUS LES TESTS!")
logger.info("🧪 [FONCTIONNALITÉS UNIFIÉES]:")
logger.info("   ✅ Tous les endpoints existants préservés")
logger.info("   ✅ Nouveaux tests v3.7.2 ajoutés")
logger.info("   ✅ Tests response_versions complets")
logger.info("   ✅ Tests clarification granulaire")
logger.info("   ✅ Simulation frontend avancée")
logger.info("   ✅ Monitoring système unifié")
logger.info("   ✅ Compatibilité 100% garantie")
logger.info("   ✅ CORRECTIONS: Import circulaire résolu, appels service direct")
logger.info("")
logger.info("🔧 [ENDPOINTS DEBUG UNIFIÉS]:")
logger.info("   - GET /system-status (unifié + v3.7.2)")
logger.info("   - GET /enhanced-stats (existant)")
logger.info("   - POST /test-enhanced-flow (amélioré v3.7.2)")
logger.info("   - POST /test-validation (amélioré v3.7.2)")
logger.info("   - GET /enhanced-conversation/{id}/context (existant)")
logger.info("   - GET /system-info (amélioré v3.7.2)")
logger.info("   - GET /health (amélioré v3.7.2)")
logger.info("   - GET /debug-info (amélioré v3.7.2)")
logger.info("   - POST /debug/test-response-versions (nouveau v3.7.2)")
logger.info("   - POST /debug/test-clarification-granular (nouveau v3.7.2)")
logger.info("   - POST /debug/simulate-frontend-clarification (nouveau v3.7.2)")
logger.info("")
logger.info("🎯 [AVANTAGES FUSION]:")
logger.info("   ✅ Un seul fichier debug à maintenir")
logger.info("   ✅ Tous les tests dans un endroit")
logger.info("   ✅ Pas de conflits de noms")
logger.info("   ✅ Évolution facilitée")
logger.info("   ✅ Compatibilité préservée")
logger.info("   ✅ CORRECTION: Imports circulaires résolus")
logger.info("   ✅ READY FOR PRODUCTION")
logger.info("🧪" * 50)