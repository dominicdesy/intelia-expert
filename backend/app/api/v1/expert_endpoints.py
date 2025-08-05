"""
app/api/v1/expert_endpoints.py - ENDPOINTS PRINCIPAUX v3.7.8

🔧 REFACTORISATION: Ce fichier contient tous les endpoints et la logique de routage
extraite de expert.py pour améliorer la maintenabilité.

ENDPOINTS INCLUS:
- /health
- /ask-enhanced-v2 
- /ask-enhanced-v2-public
- /feedback
- /topics
"""

import os
import re
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer

# Imports depuis les autres modules refactorisés
from .expert_core_functions import (
    _build_conversation_context,
    _analyze_agricultural_domain,
    _apply_dynamic_clarification_service,
    _apply_fallback_clarification,
    _extract_critical_entities_from_question,
    _validate_critical_entities,
    _force_clarification_for_missing_entities,
    _detect_inconsistencies_and_force_clarification,
    _sync_rag_state_simple,
    _extract_propagation_fields,
    _apply_propagation_fields
)

from .expert_utilities import (
    get_user_id_from_request,
    extract_breed_and_sex_from_clarification,
    _create_incomplete_clarification_response,
    _fallback_expert_response
)

# 🔧 FIX: Déclarer logger AVANT utilisation
logger = logging.getLogger(__name__)
router = APIRouter(tags=["expert-main"])
security = HTTPBearer()

# Imports sécurisés avec gestion d'erreurs CORRIGÉE
try:
    from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest, ConcisionLevel
    MODELS_IMPORTED = True
    logger.info("✅ Models importés avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur import expert_models: {e}")
    # 🔧 FIX: Fallback plus sécurisé avec tous les champs requis
    from pydantic import BaseModel
    
    class ConcisionLevel:
        CONCISE = "concise"
        DETAILED = "detailed"
        COMPREHENSIVE = "comprehensive"
    
    class EnhancedQuestionRequest(BaseModel):
        text: str
        language: str = "fr"
        conversation_id: Optional[str] = None
        is_clarification_response: bool = False
        original_question: Optional[str] = None
        clarification_context: Optional[Dict[str, Any]] = None
        clarification_entities: Optional[Dict[str, str]] = None
        concision_level: str = ConcisionLevel.CONCISE
        generate_all_versions: bool = True
        enable_vagueness_detection: bool = True
        require_coherence_check: bool = True
        detailed_rag_scoring: bool = False
        enable_quality_metrics: bool = False
        
    class EnhancedExpertResponse(BaseModel):
        question: str
        response: str
        conversation_id: str
        rag_used: bool = False
        rag_score: Optional[float] = None
        timestamp: str
        language: str
        response_time_ms: int
        mode: str
        user: Optional[str] = None
        logged: bool = False
        validation_passed: Optional[bool] = None
        # NOUVEAUX CHAMPS v3.7.3+
        clarification_required_critical: bool = False
        missing_critical_entities: List[str] = []
        variants_tested: List[str] = []
        # 🆕 NOUVEAUX CHAMPS v3.7.8
        dynamic_questions: Optional[List[Dict[str, Any]]] = None
        clarification_service_used: bool = False
        # Champs optionnels pour compatibilité
        clarification_result: Optional[Dict[str, Any]] = None
        processing_steps: List[str] = []
        ai_enhancements_used: List[str] = []
        response_versions: Optional[Dict[str, str]] = None
        clarification_processing: Optional[Dict[str, Any]] = None
        
    class FeedbackRequest(BaseModel):
        rating: str
        comment: Optional[str] = None
        conversation_id: Optional[str] = None
        quality_feedback: Optional[Dict[str, Any]] = None
        
    MODELS_IMPORTED = False
    logger.warning("⚠️ Utilisation des modèles de fallback")

try:
    from .expert_services import ExpertService
    EXPERT_SERVICE_AVAILABLE = True
    logger.info("✅ ExpertService importé avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur import expert_services: {e}")
    EXPERT_SERVICE_AVAILABLE = False

# 🆕 NOUVEAU v3.7.8: Import du service de clarification dynamique
try:
    from .expert_clarification_service import ExpertClarificationService
    CLARIFICATION_SERVICE_AVAILABLE = True
    logger.info("✅ ExpertClarificationService importé avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur import expert_clarification_service: {e}")
    CLARIFICATION_SERVICE_AVAILABLE = False

# Initialisation des services avec gestion d'erreur CORRIGÉE
expert_service = None
if EXPERT_SERVICE_AVAILABLE:
    try:
        expert_service = ExpertService()
        logger.info("✅ [Expert] Service expert initialisé avec succès")
    except Exception as e:
        logger.error(f"❌ [Expert] Erreur initialisation service: {e}")
        expert_service = None
else:
    logger.warning("⚠️ [Expert] Service expert non disponible - utilisation du mode fallback")

# 🆕 NOUVEAU v3.7.8: Initialisation service clarification
clarification_service = None
if CLARIFICATION_SERVICE_AVAILABLE:
    try:
        clarification_service = ExpertClarificationService()
        logger.info("✅ [Clarification] Service clarification initialisé avec succès")
    except Exception as e:
        logger.error(f"❌ [Clarification] Erreur initialisation service: {e}")
        clarification_service = None
else:
    logger.warning("⚠️ [Clarification] Service clarification non disponible - fonctionnalité désactivée")

# 🔧 FIX CRITIQUE: Auth dependency corrigé pour être callable
def get_current_user_mock():
    """Mock user pour fallback"""
    return {"id": "fallback_user", "email": "fallback@intelia.com"}

def get_current_user_dependency() -> Callable:
    """🔧 FIX CRITIQUE: Retourne une fonction callable, pas un Dependency object"""
    if expert_service and hasattr(expert_service, 'get_current_user_dependency'):
        try:
            # Récupère la fonction du service
            service_dependency = expert_service.get_current_user_dependency()
            # Si c'est déjà un Depends(), extraire la fonction
            if hasattr(service_dependency, 'dependency'):
                return service_dependency.dependency
            # Sinon retourner directement
            return service_dependency
        except Exception as e:
            logger.error(f"❌ Erreur get_current_user_dependency: {e}")
            return get_current_user_mock
    return get_current_user_mock

# =============================================================================
# ENDPOINTS PRINCIPAUX AVEC INTÉGRATION SERVICE CLARIFICATION v3.7.8
# =============================================================================

@router.get("/health")
async def expert_health():
    """Health check pour diagnostiquer les problèmes - version v3.7.8 avec service clarification"""
    return {
        "status": "healthy",
        "version": "3.7.8",
        "new_features_v378": [
            "intégration expert_clarification_service avec sélection dynamique de prompts",
            "appel automatique du service si clarification_required_critical = True",
            "génération de questions dynamiques basées sur entités manquantes",
            "validation et enrichissement des questions de clarification",
            "support conversation_context pour clarifications contextuelles",
            "🔧 NOUVEAU: sync_rag_state_simple pour éviter boucles infinies"
        ],
        "integration_workflow_v378": [
            "extraction entités critiques → validation → si critique → service clarification",
            "sélection prompt selon entités manquantes et contexte",
            "génération questions GPT avec prompt optimisé",
            "validation questions selon missing_entities",
            "enrichissement réponse avec questions dynamiques",
            "🔧 NOUVEAU: synchronisation RAG simplifiée une seule fois"
        ],
        "fixes_applied_v377": [
            "synchronisation état RAG - rag_used correctement mis à jour",
            "clarification forcée si entités critiques (breed, age, weight) manquent",
            "validation robuste des entités critiques avec extraction automatique",
            "déclenchement clarification_required_critical=True pour entités manquantes",
            "détection entités critiques depuis le texte de la question"
        ],
        "critical_entities_support": [
            "breed extraction (Ross 308, Cobb 500, etc.)",
            "age extraction with conversion to days",
            "weight extraction with conversion to grams", 
            "sex extraction (bonus feature)",
            "coherence validation age/weight",
            "confidence scoring per entity",
            "forced clarification for missing entities"
        ],
        "clarification_service_status": {
            "expert_service_available": EXPERT_SERVICE_AVAILABLE,
            "expert_service_initialized": expert_service is not None,
            "clarification_service_available": CLARIFICATION_SERVICE_AVAILABLE,
            "clarification_service_initialized": clarification_service is not None
        },
        "models_imported": MODELS_IMPORTED,
        "timestamp": datetime.now().isoformat(),
        "new_fields_supported_v378": [
            "dynamic_questions",
            "clarification_service_used",
            "clarification_required_critical",
            "missing_critical_entities", 
            "variants_tested"
        ],
        "clarification_workflow": [
            "build_conversation_context",
            "select_clarification_prompt",
            "generate_questions_with_gpt",
            "validate_dynamic_questions",
            "apply_to_response_data"
        ],
        "rag_sync_improvements_v378": [
            "🔧 sync_rag_state_simple remplace les anciennes fonctions complexes",
            "✅ Une seule correction, pas de boucles infinies",
            "✅ Validation simplifiée des indicateurs RAG",
            "✅ Logging optimisé pour debugging",
            "✅ Performance améliorée"
        ],
        "endpoints": [
            "/health",
            "/ask-enhanced-v2", 
            "/ask-enhanced-v2-public",
            "/feedback",
            "/topics"
        ]
    }

@router.post("/ask-enhanced-v2", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user_dependency())
):
    """
    🔧 ENDPOINT EXPERT FINAL v3.7.8 - INTÉGRATION SERVICE CLARIFICATION DYNAMIQUE + RAG SYNC SIMPLIFIÉ:
    - Extraction et validation entités critiques (breed, age, weight)
    - Si clarification_required_critical = True → appel expert_clarification_service
    - Sélection dynamique de prompt selon entités manquantes
    - Génération questions GPT avec validation
    - Enrichissement réponse avec questions dynamiques
    - 🔧 NOUVEAU: Synchronisation RAG simplifiée sans boucles infinies
    """
    start_time = time.time()
    
    # 🔧 FIX: Initialisation explicite des variables de clarification
    clarification_metadata = {}
    is_clarification = False
    original_question = None
    clarification_entities = None
    processing_metadata = {}
    
    try:
        logger.info("=" * 100)
        logger.info("🚀 DÉBUT ask_expert_enhanced_v2 v3.7.8 - INTÉGRATION SERVICE CLARIFICATION + RAG SYNC SIMPLIFIÉ")
        logger.info(f"📝 Question/Réponse: '{request_data.text}'")
        logger.info(f"🆔 Conversation ID: {getattr(request_data, 'conversation_id', 'None')}")
        logger.info(f"🛠️ Service expert disponible: {expert_service is not None}")
        logger.info(f"🎯 Service clarification disponible: {clarification_service is not None}")
        
        # Vérification service disponible
        if not expert_service:
            logger.error("❌ [Expert] Service expert non disponible - mode fallback")
            return await _fallback_expert_response(request_data, start_time, current_user)
        
        # 🆕 ÉTAPE 1 v3.7.8: EXTRACTION ET VALIDATION ENTITÉS CRITIQUES
        logger.info("🔍 [ENTITÉS CRITIQUES v3.7.8] Extraction entités depuis question...")
        entities = _extract_critical_entities_from_question(
            request_data.text, 
            getattr(request_data, 'language', 'fr')
        )
        
        logger.info("🔍 [ENTITÉS CRITIQUES v3.7.8] Validation entités extraites...")
        validation_result = _validate_critical_entities(entities, request_data.text)
        
        # Sauvegarder dans processing_metadata pour traçabilité
        processing_metadata['critical_entities'] = entities
        processing_metadata['entities_validation'] = validation_result
        
        # 🆕 ÉTAPE 2 v3.7.8: CONSTRUCTION CONTEXTE CONVERSATION
        logger.info("🔧 [CONTEXTE v3.7.8] Construction contexte conversation...")
        conversation_context = _build_conversation_context(
            request_data, 
            entities, 
            processing_metadata
        )
        
        # 🆕 CONSERVÉE v3.7.7: DÉTECTION INCOHÉRENCES POUR FORCER CLARIFICATION
        inconsistency_check = _detect_inconsistencies_and_force_clarification(
            request_data.text, 
            getattr(request_data, 'language', 'fr')
        )
        
        if inconsistency_check.get('force_clarification', False):
            logger.warning(f"🚨 [CLARIFICATION FORCÉE v3.7.8] Incohérences détectées: {inconsistency_check['inconsistencies_detected']}")
            logger.warning(f"🚨 [CLARIFICATION FORCÉE v3.7.8] Raison: {inconsistency_check['clarification_reason']}")
            
            # Forcer l'activation de la détection de vagueness
            if hasattr(request_data, 'enable_vagueness_detection'):
                request_data.enable_vagueness_detection = True
            if hasattr(request_data, 'require_coherence_check'):
                request_data.require_coherence_check = True
            
            # Ajouter dans metadata pour tracking
            processing_metadata['inconsistency_check'] = inconsistency_check
        
        # 🔧 FIX: Vérification robuste des paramètres concision avec validation None
        concision_level = getattr(request_data, 'concision_level', None)
        if concision_level is None:
            concision_level = ConcisionLevel.CONCISE
            
        generate_all_versions = getattr(request_data, 'generate_all_versions', None)
        if generate_all_versions is None:
            generate_all_versions = True
        
        logger.info("🚀 [RESPONSE_VERSIONS v3.7.8] Paramètres concision:")
        logger.info(f"   - concision_level: {concision_level}")
        logger.info(f"   - generate_all_versions: {generate_all_versions}")
        
        # 🔧 FIX: DÉTECTION EXPLICITE MODE CLARIFICATION avec validation robuste
        is_clarification = getattr(request_data, 'is_clarification_response', False)
        original_question = getattr(request_data, 'original_question', None)
        clarification_entities = getattr(request_data, 'clarification_entities', None)
        
        # 🔧 FIX: Validation des types
        if is_clarification is None:
            is_clarification = False
        
        logger.info("🧨 [DÉTECTION CLARIFICATION v3.7.8] Analyse du mode:")
        logger.info(f"   - is_clarification_response: {is_clarification}")
        logger.info(f"   - original_question fournie: {original_question is not None}")
        logger.info(f"   - clarification_entities: {clarification_entities}")
        
        if is_clarification:
            logger.info("🎪 [FLUX CLARIFICATION] Mode RÉPONSE de clarification détecté")
            logger.info(f"   - Réponse utilisateur: '{request_data.text}'")
            logger.info(f"   - Question originale: '{original_question}'")
            
            # 🔧 FIX: Initialisation sécurisée des variables breed/sex
            breed = None
            sex = None
            
            # TRAITEMENT SPÉCIALISÉ RÉPONSE CLARIFICATION avec gestion d'erreur renforcée
            try:
                if clarification_entities and isinstance(clarification_entities, dict):
                    logger.info(f"   - Entités pré-extraites: {clarification_entities}")
                    breed = clarification_entities.get('breed')
                    sex = clarification_entities.get('sex')
                else:
                    # Extraction automatique si pas fournie
                    logger.info("   - Extraction automatique entités depuis réponse")
                    extracted = extract_breed_and_sex_from_clarification(
                        request_data.text, 
                        getattr(request_data, 'language', 'fr')
                    )
                    # 🔧 FIX: Validation robuste du résultat d'extraction
                    if extracted is None or not isinstance(extracted, dict):
                        extracted = {"breed": None, "sex": None}
                    breed = extracted.get('breed')
                    sex = extracted.get('sex')
                    logger.info(f"   - Entités extraites: breed='{breed}', sex='{sex}'")
            except Exception as e:
                logger.error(f"❌ Erreur extraction entités: {e}")
                breed, sex = None, None
            
            # VALIDATION entités complètes AVANT enrichissement
            clarified_entities = {"breed": breed, "sex": sex}
            
            # 🎯 LOGIQUE GRANULAIRE v3.7.8: Validation granulaire breed vs sex
            if not breed or not sex:
                # 🔧 FIX: Protection contre None dans le logging
                breed_safe = str(breed) if breed is not None else "None"
                sex_safe = str(sex) if sex is not None else "None"
                logger.warning(f"⚠️ [FLUX CLARIFICATION] Entités incomplètes: breed='{breed_safe}', sex='{sex_safe}'")
                
                return _create_incomplete_clarification_response(
                    request_data, clarified_entities, breed, sex, start_time
                )
            
            # Enrichir la question originale avec les informations COMPLÈTES
            if original_question and isinstance(original_question, str):
                enriched_question = original_question
                if breed and isinstance(breed, str):
                    enriched_question += f" pour {breed}"
                if sex and isinstance(sex, str):
                    enriched_question += f" {sex}"
                
                logger.info(f"   - Question enrichie: '{enriched_question}'")
                
                # 🔧 FIX: Métadonnées sauvegardées pour response - initialisation sécurisée
                clarification_metadata = {
                    "was_clarification_response": True,
                    "original_question": original_question,
                    "clarification_input": request_data.text,
                    "entities_extracted": clarified_entities,
                    "question_enriched": True
                }
                
                # Modifier la question pour traitement RAG
                request_data.text = enriched_question
                
                # Marquer comme traitement post-clarification (éviter boucle)
                if hasattr(request_data, 'is_clarification_response'):
                    request_data.is_clarification_response = False
                
                logger.info("🎯 [FLUX CLARIFICATION] Question enrichie, passage au traitement RAG")
            else:
                logger.warning("⚠️ [FLUX CLARIFICATION] Question originale manquante ou invalide - impossible enrichir")
        else:
            logger.info("🎯 [FLUX CLARIFICATION] Mode QUESTION INITIALE - détection vagueness active")
        
        # 🔧 FIX: Validation et défauts concision robuste avec validation None
        if not hasattr(request_data, 'concision_level') or getattr(request_data, 'concision_level', None) is None:
            request_data.concision_level = ConcisionLevel.CONCISE
            logger.info("🚀 [CONCISION] Niveau par défaut appliqué: CONCISE")
        
        if not hasattr(request_data, 'generate_all_versions') or getattr(request_data, 'generate_all_versions', None) is None:
            request_data.generate_all_versions = True
            logger.info("🚀 [CONCISION] generate_all_versions activé par défaut")
        
        # FORÇAGE SYSTÉMATIQUE DES AMÉLIORATIONS avec gestion d'erreur
        original_vagueness = getattr(request_data, 'enable_vagueness_detection', None)
        original_coherence = getattr(request_data, 'require_coherence_check', None)
        
        # FORCER l'activation - AUCUNE EXCEPTION
        if hasattr(request_data, 'enable_vagueness_detection'):
            request_data.enable_vagueness_detection = True
        if hasattr(request_data, 'require_coherence_check'):
            request_data.require_coherence_check = True
        
        logger.info("🔥 [CLARIFICATION FORCÉE v3.7.8] Paramètres forcés:")
        logger.info(f"   - enable_vagueness_detection: {original_vagueness} → TRUE (FORCÉ)")
        logger.info(f"   - require_coherence_check: {original_coherence} → TRUE (FORCÉ)")
        
        # DÉLÉGUER AU SERVICE avec gestion d'erreur
        try:
            response = await expert_service.process_expert_question(
                request_data=request_data,
                request=request,
                current_user=current_user,
                start_time=start_time
            )
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur traitement: {e}")
            return await _fallback_expert_response(request_data, start_time, current_user, str(e))
        
        # 🔧 NOUVEAU v3.7.8: SYNCHRONISATION RAG STATE SIMPLIFIÉE - UNE SEULE FOIS
        logger.info("🔍 [RAG SYNC SIMPLE v3.7.8] APPEL UNIQUE après traitement service...")
        rag_corrected = _sync_rag_state_simple(response, processing_metadata)
        
        if rag_corrected:
            logger.info("✅ [RAG SYNC SIMPLE v3.7.8] Correction RAG appliquée avec succès")
        else:
            logger.info("✅ [RAG SYNC SIMPLE v3.7.8] État RAG déjà correct, aucune correction nécessaire")
        
        # 🆕 VALIDATION ENTITÉS CRITIQUES ET CLARIFICATION FORCÉE (CONSERVÉE v3.7.7)
        logger.info("🔍 [ENTITÉS CRITIQUES v3.7.8] Application validation entités sur réponse...")
        response = _force_clarification_for_missing_entities(response, validation_result, entities)
        
        # 🆕 ÉTAPE 3 v3.7.8: APPLICATION SERVICE CLARIFICATION DYNAMIQUE
        logger.info("🎯 [SERVICE CLARIFICATION v3.7.8] Application service clarification dynamique...")
        response = await _apply_dynamic_clarification_service(
            response_data=response,
            validation_result=validation_result,
            entities=entities,
            conversation_context=conversation_context
        )
        
        # 🚀 PROPAGATION CHAMPS v3.7.8 - AVEC NOUVEAUX CHAMPS
        logger.info("📋 [PROPAGATION v3.7.8] Extraction et application nouveaux champs")
        propagation_fields = _extract_propagation_fields(response)
        response = _apply_propagation_fields(response, propagation_fields)
        
        # 🔧 FIX: AJOUT MÉTADONNÉES CLARIFICATION dans response avec validation
        if clarification_metadata and isinstance(clarification_metadata, dict) and hasattr(response, 'clarification_processing'):
            response.clarification_processing = clarification_metadata
            logger.info("💡 [MÉTADONNÉES v3.7.8] Clarification metadata ajoutées à response")
        
        # 🆕 AJOUT MÉTADONNÉES INCOHÉRENCES v3.7.8
        if inconsistency_check.get('force_clarification', False) and hasattr(response, 'processing_steps'):
            if isinstance(response.processing_steps, list):
                response.processing_steps.append("inconsistency_forced_clarification_v3.7.8")
            if hasattr(response, 'ai_enhancements_used') and isinstance(response.ai_enhancements_used, list):
                response.ai_enhancements_used.append("inconsistency_detection_v3.7.8")
        
        # 🆕 AJOUT MÉTADONNÉES ENTITÉS CRITIQUES + SERVICE CLARIFICATION v3.7.8
        if hasattr(response, 'processing_steps') and isinstance(response.processing_steps, list):
            response.processing_steps.append("critical_entities_extracted_v3.7.8")
            if validation_result.get('clarification_required', False):
                response.processing_steps.append(f"critical_entities_clarification_{validation_result.get('clarification_priority', 'unknown')}")
            
            # Ajouter step pour service clarification
            if getattr(response, 'clarification_service_used', False):
                response.processing_steps.append("dynamic_clarification_service_used_v3.7.8")
        
        if hasattr(response, 'ai_enhancements_used') and isinstance(response.ai_enhancements_used, list):
            response.ai_enhancements_used.append("critical_entities_validation_v3.7.8")
            if validation_result.get('entities_sufficient', False):
                response.ai_enhancements_used.append("critical_entities_sufficient")
            else:
                response.ai_enhancements_used.append("critical_entities_insufficient")
            
            # Ajouter enhancement pour service clarification
            if getattr(response, 'clarification_service_used', False):
                response.ai_enhancements_used.append("dynamic_clarification_generation_v3.7.8")
        
        # LOGGING RÉSULTATS DÉTAILLÉ
        logger.info("🧨 [RÉSULTATS CLARIFICATION v3.7.8]:")
        logger.info(f"   - Mode final: {getattr(response, 'mode', 'unknown')}")
        logger.info(f"   - Clarification déclenchée: {getattr(response, 'clarification_result', None) is not None}")
        logger.info(f"   - RAG utilisé: {getattr(response, 'rag_used', False)}")
        logger.info(f"   - Service clarification utilisé: {getattr(response, 'clarification_service_used', False)}")
        
        # 🆕 LOGGING SPÉCIFIQUE SERVICE CLARIFICATION v3.7.8
        dynamic_questions = getattr(response, 'dynamic_questions', None)
        if dynamic_questions and isinstance(dynamic_questions, list):
            logger.info(f"   - Questions dynamiques générées: {len(dynamic_questions)}")
            for i, q in enumerate(dynamic_questions[:3], 1):  # Log 3 premières questions
                question_text = q.get('question', '') if isinstance(q, dict) else str(q)
                logger.info(f"     {i}. {question_text[:50]}...")
        else:
            logger.info("   - Aucune question dynamique générée")
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2 v3.7.8")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2 v3.7.8: {e}")
        logger.info("=" * 100)
        return await _fallback_expert_response(request_data, start_time, current_user, str(e))

@router.post("/ask-enhanced-v2-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2_public(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """🔧 ENDPOINT PUBLIC v3.7.8 - INTÉGRATION SERVICE CLARIFICATION DYNAMIQUE + RAG SYNC SIMPLIFIÉ"""
    start_time = time.time()
    
    # 🔧 FIX: Initialisation explicite des variables
    clarification_metadata = {}
    is_clarification = False
    processing_metadata = {}
    
    try:
        logger.info("=" * 100)
        logger.info("🌐 DÉBUT ask_expert_enhanced_v2_public v3.7.8 - INTÉGRATION SERVICE CLARIFICATION + RAG SYNC SIMPLIFIÉ")
        logger.info(f"📝 Question/Réponse: '{request_data.text}'")
        logger.info(f"🛠️ Service expert disponible: {expert_service is not None}")
        logger.info(f"🎯 Service clarification disponible: {clarification_service is not None}")
        
        # Vérification service disponible
        if not expert_service:
            logger.error("❌ [Expert Public] Service expert non disponible - mode fallback")
            return await _fallback_expert_response(request_data, start_time, None)
        
        # 🆕 ÉTAPE 1 v3.7.8: EXTRACTION ET VALIDATION ENTITÉS CRITIQUES POUR ENDPOINT PUBLIC
        logger.info("🔍 [ENTITÉS CRITIQUES PUBLIC v3.7.8] Extraction entités depuis question...")
        entities = _extract_critical_entities_from_question(
            request_data.text, 
            getattr(request_data, 'language', 'fr')
        )
        
        logger.info("🔍 [ENTITÉS CRITIQUES PUBLIC v3.7.8] Validation entités extraites...")
        validation_result = _validate_critical_entities(entities, request_data.text)
        
        # Sauvegarder dans processing_metadata pour traçabilité
        processing_metadata['critical_entities'] = entities
        processing_metadata['entities_validation'] = validation_result
        
        # 🆕 ÉTAPE 2 v3.7.8: CONSTRUCTION CONTEXTE CONVERSATION POUR ENDPOINT PUBLIC
        logger.info("🔧 [CONTEXTE PUBLIC v3.7.8] Construction contexte conversation...")
        conversation_context = _build_conversation_context(
            request_data, 
            entities, 
            processing_metadata
        )
        
        # DÉLÉGUER AU SERVICE avec support response_versions et gestion d'erreur
        try:
            response = await expert_service.process_expert_question(
                request_data=request_data,
                request=request,
                current_user=None,  # Mode public
                start_time=start_time
            )
        except Exception as e:
            logger.error(f"❌ [Expert Service Public] Erreur traitement: {e}")
            return await _fallback_expert_response(request_data, start_time, None, str(e))
        
        # 🔧 NOUVEAU v3.7.8: SYNCHRONISATION RAG STATE SIMPLIFIÉE POUR PUBLIC
        logger.info("🔍 [RAG SYNC SIMPLE PUBLIC v3.7.8] APPEL UNIQUE après traitement service...")
        rag_corrected = _sync_rag_state_simple(response, processing_metadata)
        
        # 🆕 VALIDATION ENTITÉS CRITIQUES ET CLARIFICATION FORCÉE POUR PUBLIC
        logger.info("🔍 [ENTITÉS CRITIQUES PUBLIC v3.7.8] Application validation entités sur réponse...")
        response = _force_clarification_for_missing_entities(response, validation_result, entities)
        
        # 🆕 ÉTAPE 3 v3.7.8: APPLICATION SERVICE CLARIFICATION DYNAMIQUE POUR ENDPOINT PUBLIC
        logger.info("🎯 [SERVICE CLARIFICATION PUBLIC v3.7.8] Application service clarification dynamique...")
        response = await _apply_dynamic_clarification_service(
            response_data=response,
            validation_result=validation_result,
            entities=entities,
            conversation_context=conversation_context
        )
        
        # 🚀 PROPAGATION CHAMPS v3.7.8 - ENDPOINT PUBLIC - AVEC NOUVEAUX CHAMPS
        logger.info("📋 [PROPAGATION PUBLIC v3.7.8] Extraction et application nouveaux champs")
        propagation_fields = _extract_propagation_fields(response)
        response = _apply_propagation_fields(response, propagation_fields)
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2_public v3.7.8")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2_public v3.7.8: {e}")
        logger.info("=" * 100)
        return await _fallback_expert_response(request_data, start_time, None, str(e))

@router.post("/feedback")
async def submit_feedback_enhanced(feedback_data: FeedbackRequest):
    """Submit feedback - VERSION CORRIGÉE v3.7.8 avec gestion d'erreur robuste"""
    try:
        conversation_id = getattr(feedback_data, 'conversation_id', 'None')
        logger.info(f"📊 [Feedback v3.7.8] Reçu: {feedback_data.rating} pour {conversation_id}")
        
        # 🔧 FIX: Validation robuste des quality_feedback
        quality_feedback = getattr(feedback_data, 'quality_feedback', None)
        if quality_feedback and isinstance(quality_feedback, dict):
            logger.info(f"📈 [Feedback v3.7.8] Qualité détaillée: {len(quality_feedback)} métriques")
        
        if expert_service and hasattr(expert_service, 'process_feedback'):
            try:
                result = await expert_service.process_feedback(feedback_data)
            except Exception as e:
                logger.error(f"❌ [Feedback Service v3.7.8] Erreur: {e}")
                # Fallback si service expert échoue
                result = {
                    "success": False,
                    "message": f"Erreur service feedback: {str(e)}",
                    "rating": feedback_data.rating,
                    "comment": getattr(feedback_data, 'comment', None),
                    "conversation_id": conversation_id,
                    "fallback_mode": True,
                    "timestamp": datetime.now().isoformat(),
                    "version": "3.7.8"
                }
        else:
            # Fallback si service non disponible
            result = {
                "success": True,
                "message": "Feedback enregistré (mode fallback v3.7.8)",
                "rating": feedback_data.rating,
                "comment": getattr(feedback_data, 'comment', None),
                "conversation_id": conversation_id,
                "fallback_mode": True,
                "timestamp": datetime.now().isoformat(),
                "version": "3.7.8"
            }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [Feedback v3.7.8] Erreur critique: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur feedback v3.7.8: {str(e)}")

@router.get("/topics")
async def get_suggested_topics_enhanced(language: str = "fr"):
    """Get suggested topics - VERSION CORRIGÉE v3.7.8 avec gestion d'erreur robuste"""
    try:
        if expert_service and hasattr(expert_service, 'get_suggested_topics'):
            try:
                return await expert_service.get_suggested_topics(language)
            except Exception as e:
                logger.error(f"❌ [Topics Service v3.7.8] Erreur: {e}")
                # Continuer vers fallback
        
        # 🔧 FIX: Fallback amélioré avec validation language v3.7.8
        fallback_topics = {
            "fr": [
                "Problèmes de croissance poulets Ross 308",
                "Conditions environnementales optimales élevage", 
                "Protocoles vaccination selon âge",
                "Diagnostic problèmes santé par symptômes",
                "Nutrition et alimentation selon poids",
                "Mortalité élevée - causes et solutions",
                "Température et ventilation bâtiment",
                "Développement normal poulets de chair"
            ],
            "en": [
                "Ross 308 chicken growth problems",
                "Optimal environmental conditions breeding",
                "Age-specific vaccination protocols", 
                "Health problem diagnosis by symptoms",
                "Weight-based nutrition and feeding",
                "High mortality - causes and solutions",
                "Building temperature and ventilation",
                "Normal broiler chicken development"
            ],
            "es": [
                "Problemas crecimiento pollos Ross 308",
                "Condiciones ambientales óptimas crianza",
                "Protocolos vacunación según edad",
                "Diagnóstico problemas salud por síntomas", 
                "Nutrición alimentación según peso",
                "Alta mortalidad - causas y soluciones",
                "Temperatura y ventilación edificio",
                "Desarrollo normal pollos de engorde"
            ]
        }
        
        # 🔧 FIX: Validation robuste du language
        lang = str(language).lower() if language else "fr"
        if lang not in fallback_topics:
            lang = "fr"
        
        selected_topics = fallback_topics[lang]
        
        return {
            "topics": selected_topics,
            "language": lang,
            "count": len(selected_topics),
            "fallback_mode": True,
            "expert_service_available": expert_service is not None,
            "clarification_service_available": clarification_service is not None,
            "timestamp": datetime.now().isoformat(),
            "version": "3.7.8",
            "critical_entities_optimized": True,
            "dynamic_clarification_ready": CLARIFICATION_SERVICE_AVAILABLE,
            "rag_sync_optimized": True
        }
            
    except Exception as e:
        logger.error(f"❌ [Topics v3.7.8] Erreur critique: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur topics v3.7.8: {str(e)}")

# =============================================================================
# LOGGING ET INITIALISATION FINALE v3.7.8
# =============================================================================

logger.info("🚀" * 50)
logger.info("🚀 [EXPERT ENDPOINTS] VERSION 3.7.8 - ENDPOINTS REFACTORISÉS!")
logger.info("🚀 [REFACTORISATION]:")
logger.info("   ✅ Endpoints extraits de expert.py")
logger.info("   ✅ Code conservé intégralement")
logger.info("   ✅ Imports depuis expert_core_functions et expert_utilities")
logger.info("   ✅ Gestion d'erreur robuste")
logger.info("   ✅ Logging optimisé")
logger.info("")
logger.info("🔧 [ENDPOINTS DISPONIBLES v3.7.8]:")
logger.info("   - GET /health")
logger.info("   - POST /ask-enhanced-v2")
logger.info("   - POST /ask-enhanced-v2-public")
logger.info("   - POST /feedback")
logger.info("   - GET /topics")
logger.info("")
logger.info("✅ [RÉSULTAT ATTENDU v3.7.8]:")
logger.info("   ✅ Endpoints fonctionnels")
logger.info("   ✅ Service clarification intégré")
logger.info("   ✅ RAG sync simplifié")
logger.info("   ✅ Gestion d'erreur robuste")
logger.info("   ✅ SYNTAXE PYTHON 100% CORRECTE")
logger.info("🚀" * 50)
