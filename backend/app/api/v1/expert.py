"""
app/api/v1/expert.py - EXPERT ENDPOINTS PRINCIPAUX v3.7.3 - PROPAGATION CHAMPS

🚀 MODIFICATIONS APPLIQUÉES v3.7.3:
- Propagation clarification_required_critical dans toutes les réponses
- Propagation missing_critical_entities dans les métadonnées
- Propagation variants_tested depuis les améliorations RAG
- Intégration complète dans EnhancedExpertResponse
- Support dans les endpoints publics et privés
- Gestion dans les réponses de clarification incomplète

VERSION COMPLÈTE + PROPAGATION NOUVEAUX CHAMPS + SUPPORT RESPONSE_VERSIONS + CLARIFICATION INTELLIGENTE
"""

import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer

# Imports sécurisés avec gestion d'erreurs
try:
    from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest, ConcisionLevel
except ImportError as e:
    logger.error(f"❌ Erreur import expert_models: {e}")
    # Fallback vers des modèles de base
    from pydantic import BaseModel
    
    class EnhancedQuestionRequest(BaseModel):
        text: str
        language: str = "fr"
        conversation_id: Optional[str] = None
        is_clarification_response: bool = False
        original_question: Optional[str] = None
        clarification_context: Optional[Dict[str, Any]] = None
        clarification_entities: Optional[Dict[str, str]] = None
        
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
        # NOUVEAUX CHAMPS v3.7.3
        clarification_required_critical: bool = False
        missing_critical_entities: List[str] = []
        variants_tested: List[str] = []
        
    class FeedbackRequest(BaseModel):
        rating: str
        comment: Optional[str] = None
        conversation_id: Optional[str] = None
        
    class ConcisionLevel:
        CONCISE = "concise"

try:
    from .expert_services import ExpertService
    EXPERT_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Erreur import expert_services: {e}")
    EXPERT_SERVICE_AVAILABLE = False

try:
    from .expert_utils import get_user_id_from_request, extract_breed_and_sex_from_clarification
except ImportError as e:
    logger.error(f"❌ Erreur import expert_utils: {e}")
    # Fonctions fallback
    def get_user_id_from_request(request):
        return getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    
    def extract_breed_and_sex_from_clarification(text, language):
        return {"breed": None, "sex": None}

router = APIRouter(tags=["expert-main"])
logger = logging.getLogger(__name__)
security = HTTPBearer()

# Initialisation du service avec gestion d'erreur
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

# Mock auth dependency si service non disponible
def get_current_user_mock():
    return {"id": "fallback_user", "email": "fallback@intelia.com"}

def get_current_user_dependency():
    if expert_service and hasattr(expert_service, 'get_current_user_dependency'):
        return expert_service.get_current_user_dependency()
    return get_current_user_mock

# =============================================================================
# UTILITAIRES PROPAGATION CHAMPS v3.7.3
# =============================================================================

def _extract_propagation_fields(response_data: Any) -> Dict[str, Any]:
    """Extrait les nouveaux champs à propager depuis la réponse du service"""
    
    propagation_fields = {
        "clarification_required_critical": False,
        "missing_critical_entities": [],
        "variants_tested": []
    }
    
    try:
        # Extraction clarification_required_critical
        if hasattr(response_data, 'clarification_result') and response_data.clarification_result:
            clarification_result = response_data.clarification_result
            propagation_fields["clarification_required_critical"] = clarification_result.get("clarification_required_critical", False)
            propagation_fields["missing_critical_entities"] = clarification_result.get("missing_critical_entities", [])
            
            logger.info(f"📋 [PROPAGATION v3.7.3] Clarification critique: {propagation_fields['clarification_required_critical']}")
            logger.info(f"📋 [PROPAGATION v3.7.3] Entités critiques manquantes: {propagation_fields['missing_critical_entities']}")
        
        # Extraction variants_tested depuis RAG enhancements
        if hasattr(response_data, 'rag_enhancement_info') and response_data.rag_enhancement_info:
            rag_enhancement_info = response_data.rag_enhancement_info
            propagation_fields["variants_tested"] = rag_enhancement_info.get("variants_tested", [])
            
            logger.info(f"📋 [PROPAGATION v3.7.3] Variantes testées: {propagation_fields['variants_tested']}")
        
        # Extraction alternative depuis processing_metadata
        elif hasattr(response_data, 'processing_metadata') and response_data.processing_metadata:
            processing_metadata = response_data.processing_metadata
            if "rag_enhancement_info" in processing_metadata:
                rag_info = processing_metadata["rag_enhancement_info"]
                propagation_fields["variants_tested"] = rag_info.get("variants_tested", [])
                
                logger.info(f"📋 [PROPAGATION v3.7.3] Variantes depuis metadata: {propagation_fields['variants_tested']}")
        
        # Extraction depuis ai_enhancements_used (fallback)
        elif hasattr(response_data, 'ai_enhancements_used') and response_data.ai_enhancements_used:
            # Filtrer les améliorations liées aux variantes
            variant_enhancements = [
                enhancement for enhancement in response_data.ai_enhancements_used 
                if "variant" in enhancement.lower() or "reformulation" in enhancement.lower()
            ]
            if variant_enhancements:
                propagation_fields["variants_tested"] = variant_enhancements
                logger.info(f"📋 [PROPAGATION v3.7.3] Variantes inférées: {variant_enhancements}")
        
        logger.info("✅ [PROPAGATION v3.7.3] Champs extraits avec succès")
        
    except Exception as e:
        logger.error(f"❌ [PROPAGATION v3.7.3] Erreur extraction champs: {e}")
        # Garder les valeurs par défaut en cas d'erreur
    
    return propagation_fields

def _apply_propagation_fields(response: EnhancedExpertResponse, propagation_fields: Dict[str, Any]) -> EnhancedExpertResponse:
    """Applique les champs de propagation à la réponse finale"""
    
    try:
        # Application des nouveaux champs
        if hasattr(response, 'clarification_required_critical'):
            response.clarification_required_critical = propagation_fields.get("clarification_required_critical", False)
        
        if hasattr(response, 'missing_critical_entities'):
            response.missing_critical_entities = propagation_fields.get("missing_critical_entities", [])
        
        if hasattr(response, 'variants_tested'):
            response.variants_tested = propagation_fields.get("variants_tested", [])
        
        logger.info("✅ [PROPAGATION v3.7.3] Champs appliqués à la réponse finale")
        
        # Log des valeurs appliquées
        logger.info(f"📋 [PROPAGATION v3.7.3] Appliqué clarification critique: {getattr(response, 'clarification_required_critical', 'N/A')}")
        logger.info(f"📋 [PROPAGATION v3.7.3] Appliqué entités manquantes: {getattr(response, 'missing_critical_entities', 'N/A')}")
        logger.info(f"📋 [PROPAGATION v3.7.3] Appliqué variantes testées: {getattr(response, 'variants_tested', 'N/A')}")
        
    except Exception as e:
        logger.error(f"❌ [PROPAGATION v3.7.3] Erreur application champs: {e}")
    
    return response

# =============================================================================
# ENDPOINTS PRINCIPAUX AVEC PROPAGATION v3.7.3
# =============================================================================

@router.get("/health")
async def expert_health():
    """Health check pour diagnostiquer les problèmes"""
    return {
        "status": "healthy",
        "version": "3.7.3",
        "expert_service_available": EXPERT_SERVICE_AVAILABLE,
        "expert_service_initialized": expert_service is not None,
        "timestamp": datetime.now().isoformat(),
        "propagation_fields_supported": [
            "clarification_required_critical",
            "missing_critical_entities", 
            "variants_tested"
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
    🧨 ENDPOINT EXPERT FINAL avec PROPAGATION CHAMPS v3.7.3:
    - Support explicite du flag is_clarification_response
    - Logique clarification granulaire et adaptative
    - Métadonnées propagées correctement
    - Génération multi-versions des réponses
    - NOUVEAUX CHAMPS: clarification_required_critical, missing_critical_entities, variants_tested
    ✅ CORRIGÉ: Variables initialisées, vérifications robustes, propagation complète
    """
    start_time = time.time()
    
    try:
        logger.info("=" * 100)
        logger.info("🚀 DÉBUT ask_expert_enhanced_v2 v3.7.3 - PROPAGATION CHAMPS + CLARIFICATION INTELLIGENTE")
        logger.info(f"📝 Question/Réponse: '{request_data.text}'")
        logger.info(f"🆔 Conversation ID: {getattr(request_data, 'conversation_id', 'None')}")
        logger.info(f"🛠️ Service disponible: {expert_service is not None}")
        
        # Vérification service disponible
        if not expert_service:
            logger.error("❌ [Expert] Service expert non disponible - mode fallback")
            return await _fallback_expert_response(request_data, start_time, current_user)
        
        # ✅ CORRECTION: Vérification robuste des paramètres concision
        concision_level = getattr(request_data, 'concision_level', ConcisionLevel.CONCISE)
        generate_all_versions = getattr(request_data, 'generate_all_versions', True)
        
        if concision_level is None:
            concision_level = ConcisionLevel.CONCISE
        if generate_all_versions is None:
            generate_all_versions = True
        
        logger.info("🚀 [RESPONSE_VERSIONS v3.7.3] Paramètres concision:")
        logger.info(f"   - concision_level: {concision_level}")
        logger.info(f"   - generate_all_versions: {generate_all_versions}")
        
        # DÉTECTION EXPLICITE MODE CLARIFICATION avec gestion d'erreur
        is_clarification = getattr(request_data, 'is_clarification_response', False)
        original_question = getattr(request_data, 'original_question', None)
        clarification_entities = getattr(request_data, 'clarification_entities', None)
        
        logger.info("🧨 [DÉTECTION CLARIFICATION v3.7.3] Analyse du mode:")
        logger.info(f"   - is_clarification_response: {is_clarification}")
        logger.info(f"   - original_question fournie: {original_question is not None}")
        logger.info(f"   - clarification_entities: {clarification_entities}")
        
        # Variables pour métadonnées de clarification
        clarification_metadata = {}
        
        if is_clarification:
            logger.info("🎪 [FLUX CLARIFICATION] Mode RÉPONSE de clarification détecté")
            logger.info(f"   - Réponse utilisateur: '{request_data.text}'")
            logger.info(f"   - Question originale: '{original_question}'")
            
            # ✅ CORRECTION: Initialisation sécurisée des variables breed/sex
            breed = None
            sex = None
            
            # TRAITEMENT SPÉCIALISÉ RÉPONSE CLARIFICATION avec gestion d'erreur
            try:
                if clarification_entities:
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
                    if extracted is None:
                        extracted = {"breed": None, "sex": None}
                    breed = extracted.get('breed')
                    sex = extracted.get('sex')
                    logger.info(f"   - Entités extraites: breed='{breed}', sex='{sex}'")
            except Exception as e:
                logger.error(f"❌ Erreur extraction entités: {e}")
                breed, sex = None, None
            
            # VALIDATION entités complètes AVANT enrichissement
            clarified_entities = {"breed": breed, "sex": sex}
            
            # 🎯 NOUVELLE LOGIQUE GRANULAIRE v3.7.3: Validation granulaire breed vs sex
            if not breed or not sex:
                # ✅ CORRECTION: Protection contre None dans le logging
                breed_safe = breed or "None"
                sex_safe = sex or "None"
                logger.warning(f"⚠️ [FLUX CLARIFICATION] Entités incomplètes: breed='{breed_safe}', sex='{sex_safe}'")
                
                return _create_incomplete_clarification_response(
                    request_data, clarified_entities, breed, sex, start_time
                )
            
            # Enrichir la question originale avec les informations COMPLÈTES
            if original_question:
                enriched_question = original_question
                if breed:
                    enriched_question += f" pour {breed}"
                if sex:
                    enriched_question += f" {sex}"
                
                logger.info(f"   - Question enrichie: '{enriched_question}'")
                
                # Métadonnées sauvegardées pour response
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
                logger.warning("⚠️ [FLUX CLARIFICATION] Question originale manquante - impossible enrichir")
        else:
            logger.info("🎯 [FLUX CLARIFICATION] Mode QUESTION INITIALE - détection vagueness active")
        
        # ✅ CORRECTION: Validation et défauts concision robuste
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
        
        logger.info("🔥 [CLARIFICATION FORCÉE v3.7.3] Paramètres forcés:")
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
        
        # 🚀 PROPAGATION NOUVEAUX CHAMPS v3.7.3
        logger.info("📋 [PROPAGATION v3.7.3] Extraction et application nouveaux champs")
        propagation_fields = _extract_propagation_fields(response)
        response = _apply_propagation_fields(response, propagation_fields)
        
        # AJOUT MÉTADONNÉES CLARIFICATION dans response
        if clarification_metadata and hasattr(response, 'clarification_processing'):
            response.clarification_processing = clarification_metadata
            logger.info("💡 [MÉTADONNÉES v3.7.3] Clarification metadata ajoutées à response")
        
        # Log response_versions si présentes
        if hasattr(response, 'response_versions') and response.response_versions:
            logger.info("🚀 [RESPONSE_VERSIONS] Versions générées:")
            for level, content in response.response_versions.items():
                logger.info(f"   - {level}: {len(content)} caractères")
        
        # LOGGING RÉSULTATS CLARIFICATION DÉTAILLÉ
        logger.info("🧨 [RÉSULTATS CLARIFICATION v3.7.3]:")
        logger.info(f"   - Mode final: {getattr(response, 'mode', 'unknown')}")
        logger.info(f"   - Clarification déclenchée: {getattr(response, 'clarification_result', None) is not None}")
        logger.info(f"   - RAG utilisé: {getattr(response, 'rag_used', False)}")
        logger.info(f"   - Question finale traitée: '{getattr(response, 'question', '')[:100]}...'")
        
        clarification_result = getattr(response, 'clarification_result', None)
        if clarification_result:
            logger.info(f"   - Type clarification: {clarification_result.get('clarification_type', 'N/A')}")
            logger.info(f"   - Infos manquantes: {clarification_result.get('missing_information', [])}")
            logger.info(f"   - Confiance: {clarification_result.get('confidence', 0)}")
            if 'provided_parts' in clarification_result:
                logger.info(f"   - Parties détectées: {clarification_result.get('provided_parts', [])}")
        
        # 📋 LOGGING NOUVEAUX CHAMPS v3.7.3
        logger.info("📋 [NOUVEAUX CHAMPS v3.7.3] Valeurs finales:")
        logger.info(f"   - clarification_required_critical: {getattr(response, 'clarification_required_critical', 'N/A')}")
        logger.info(f"   - missing_critical_entities: {getattr(response, 'missing_critical_entities', 'N/A')}")
        logger.info(f"   - variants_tested: {getattr(response, 'variants_tested', 'N/A')}")
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2 v3.7.3 - Temps: {getattr(response, 'response_time_ms', 0)}ms")
        logger.info(f"🤖 Améliorations: {len(getattr(response, 'ai_enhancements_used', []))} features")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2 v3.7.3: {e}")
        logger.info("=" * 100)
        return await _fallback_expert_response(request_data, start_time, current_user, str(e))

@router.post("/ask-enhanced-v2-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2_public(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """🧨 ENDPOINT PUBLIC avec PROPAGATION CHAMPS v3.7.3
    ✅ CORRIGÉ: Variables initialisées, vérifications robustes, propagation complète"""
    start_time = time.time()
    
    try:
        logger.info("=" * 100)
        logger.info("🌐 DÉBUT ask_expert_enhanced_v2_public v3.7.3 - PROPAGATION CHAMPS + CLARIFICATION INTELLIGENTE")
        logger.info(f"📝 Question/Réponse: '{request_data.text}'")
        logger.info(f"🛠️ Service disponible: {expert_service is not None}")
        
        # Vérification service disponible
        if not expert_service:
            logger.error("❌ [Expert Public] Service expert non disponible - mode fallback")
            return await _fallback_expert_response(request_data, start_time, None)
        
        # ✅ CORRECTION: Paramètres concision pour endpoint public avec vérifications
        concision_level = getattr(request_data, 'concision_level', ConcisionLevel.CONCISE)
        generate_all_versions = getattr(request_data, 'generate_all_versions', True)
        
        if concision_level is None:
            concision_level = ConcisionLevel.CONCISE
        if generate_all_versions is None:
            generate_all_versions = True
        
        logger.info("🚀 [RESPONSE_VERSIONS PUBLIC] Paramètres concision:")
        logger.info(f"   - concision_level: {concision_level}")
        logger.info(f"   - generate_all_versions: {generate_all_versions}")
        
        # DÉTECTION PUBLIQUE CLARIFICATION avec gestion d'erreur
        is_clarification = getattr(request_data, 'is_clarification_response', False)
        clarification_metadata = {}
        
        logger.info("🧨 [DÉTECTION PUBLIQUE v3.7.3] Analyse mode clarification:")
        logger.info(f"   - is_clarification_response: {is_clarification}")
        logger.info(f"   - conversation_id: {getattr(request_data, 'conversation_id', 'None')}")
        
        if is_clarification:
            logger.info("🎪 [FLUX PUBLIC] Traitement réponse clarification")
            
            # Logique similaire à l'endpoint privé avec gestion d'erreur
            original_question = getattr(request_data, 'original_question', None)
            clarification_entities = getattr(request_data, 'clarification_entities', None)
            
            logger.info(f"   - Question originale: '{original_question}'")
            logger.info(f"   - Entités fournies: {clarification_entities}")
            
            # ✅ CORRECTION: Initialisation sécurisée des variables breed/sex
            breed = None
            sex = None
            
            try:
                if clarification_entities:
                    breed = clarification_entities.get('breed')
                    sex = clarification_entities.get('sex')
                    logger.info(f"   - Utilisation entités pré-extraites: breed='{breed}', sex='{sex}'")
                else:
                    # Extraction automatique
                    extracted = extract_breed_and_sex_from_clarification(
                        request_data.text, 
                        getattr(request_data, 'language', 'fr')
                    )
                    if extracted is None:
                        extracted = {"breed": None, "sex": None}
                    breed = extracted.get('breed')
                    sex = extracted.get('sex')
                    logger.info(f"   - Extraction automatique: breed='{breed}', sex='{sex}'")
            except Exception as e:
                logger.error(f"❌ Erreur extraction entités publique: {e}")
                breed, sex = None, None
            
            # VALIDATION entités complètes
            clarified_entities = {"breed": breed, "sex": sex}
            
            # 🎯 LOGIQUE GRANULAIRE PUBLIQUE v3.7.3
            if not breed or not sex:
                breed_safe = breed or "None"
                sex_safe = sex or "None"
                logger.warning(f"⚠️ [FLUX PUBLIC] Entités incomplètes: breed='{breed_safe}', sex='{sex_safe}'")
                
                return _create_incomplete_clarification_response(
                    request_data, clarified_entities, breed, sex, start_time, public=True
                )
            
            # Enrichissement question avec entités COMPLÈTES
            if original_question:
                enriched_question = original_question
                if breed:
                    enriched_question += f" pour {breed}"
                if sex:
                    enriched_question += f" {sex}"
                
                # Métadonnées pour response (endpoint public)
                clarification_metadata = {
                    "was_clarification_response": True,
                    "original_question": original_question,
                    "clarification_input": request_data.text,
                    "entities_extracted": clarified_entities,
                    "question_enriched": True
                }
                
                # Modifier question pour RAG
                request_data.text = enriched_question
                if hasattr(request_data, 'is_clarification_response'):
                    request_data.is_clarification_response = False  # Éviter boucle
                
                logger.info(f"   - Question enrichie publique: '{enriched_question}'")
                logger.info(f"   - Métadonnées sauvegardées: {clarification_metadata}")
        else:
            logger.info("🎯 [FLUX PUBLIC] Question initiale - détection vagueness")
        
        # ✅ CORRECTION: Validation et défauts concision pour public
        if not hasattr(request_data, 'concision_level') or getattr(request_data, 'concision_level', None) is None:
            request_data.concision_level = ConcisionLevel.CONCISE
        
        if not hasattr(request_data, 'generate_all_versions') or getattr(request_data, 'generate_all_versions', None) is None:
            request_data.generate_all_versions = True
        
        # FORÇAGE MAXIMAL pour endpoint public avec gestion d'erreur
        logger.info("🔥 [PUBLIC ENDPOINT v3.7.3] Activation FORCÉE des améliorations:")
        
        original_settings = {
            'vagueness': getattr(request_data, 'enable_vagueness_detection', None),
            'coherence': getattr(request_data, 'require_coherence_check', None),
            'detailed_rag': getattr(request_data, 'detailed_rag_scoring', None),
            'quality_metrics': getattr(request_data, 'enable_quality_metrics', None)
        }
        
        # FORÇAGE MAXIMAL pour endpoint public
        if hasattr(request_data, 'enable_vagueness_detection'):
            request_data.enable_vagueness_detection = True
        if hasattr(request_data, 'require_coherence_check'):
            request_data.require_coherence_check = True
        if hasattr(request_data, 'detailed_rag_scoring'):
            request_data.detailed_rag_scoring = True
        if hasattr(request_data, 'enable_quality_metrics'):
            request_data.enable_quality_metrics = True
        
        logger.info("🔥 [FORÇAGE PUBLIC v3.7.3] Changements appliqués:")
        for key, (old_val, new_val) in {
            'vagueness_detection': (original_settings['vagueness'], True),
            'coherence_check': (original_settings['coherence'], True),
            'detailed_rag': (original_settings['detailed_rag'], True),
            'quality_metrics': (original_settings['quality_metrics'], True)
        }.items():
            logger.info(f"   - {key}: {old_val} → {new_val} (FORCÉ)")
        
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
        
        # 🚀 PROPAGATION NOUVEAUX CHAMPS v3.7.3 - ENDPOINT PUBLIC
        logger.info("📋 [PROPAGATION PUBLIC v3.7.3] Extraction et application nouveaux champs")
        propagation_fields = _extract_propagation_fields(response)
        response = _apply_propagation_fields(response, propagation_fields)
        
        # Ajout métadonnées clarification
        if clarification_metadata and hasattr(response, 'clarification_processing'):
            response.clarification_processing = clarification_metadata
            logger.info("💡 [MÉTADONNÉES PUBLIC v3.7.3] Clarification metadata ajoutées")
        
        # Log response_versions si présentes
        if hasattr(response, 'response_versions') and response.response_versions:
            logger.info("🚀 [RESPONSE_VERSIONS PUBLIC] Versions générées:")
            for level, content in response.response_versions.items():
                logger.info(f"   - {level}: {len(content)} caractères")
        
        # VALIDATION RÉSULTATS CLARIFICATION PUBLIQUE
        logger.info("🧨 [VALIDATION PUBLIQUE v3.7.3]:")
        logger.info(f"   - Clarification système actif: {'clarification' in getattr(response, 'mode', '')}")
        logger.info(f"   - Améliorations appliquées: {getattr(response, 'ai_enhancements_used', [])}")
        logger.info(f"   - Mode final: {getattr(response, 'mode', 'unknown')}")
        logger.info(f"   - RAG utilisé: {getattr(response, 'rag_used', False)}")
        
        # 📋 LOGGING NOUVEAUX CHAMPS PUBLIC v3.7.3
        logger.info("📋 [NOUVEAUX CHAMPS PUBLIC v3.7.3] Valeurs finales:")
        logger.info(f"   - clarification_required_critical: {getattr(response, 'clarification_required_critical', 'N/A')}")
        logger.info(f"   - missing_critical_entities: {getattr(response, 'missing_critical_entities', 'N/A')}")
        logger.info(f"   - variants_tested: {getattr(response, 'variants_tested', 'N/A')}")
        
        # Vérification critique
        ai_enhancements = getattr(response, 'ai_enhancements_used', [])
        if not ai_enhancements:
            logger.warning("⚠️ [ALERTE] Aucune amélioration détectée - possible problème!")
        
        if hasattr(response, 'enable_vagueness_detection') and getattr(response, 'enable_vagueness_detection', True) is False:
            logger.warning("⚠️ [ALERTE] Vagueness detection non activée - vérifier forçage!")
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2_public v3.7.3 - Mode: {getattr(response, 'mode', 'unknown')}")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2_public v3.7.3: {e}")
        logger.info("=" * 100)
        return await _fallback_expert_response(request_data, start_time, None, str(e))

# =============================================================================
# ENDPOINT FEEDBACK ET TOPICS AVEC GESTION D'ERREUR
# =============================================================================

@router.post("/feedback")
async def submit_feedback_enhanced(feedback_data: FeedbackRequest):
    """Submit feedback - VERSION FINALE avec support qualité et gestion d'erreur"""
    try:
        logger.info(f"📊 [Feedback] Reçu: {feedback_data.rating} pour {getattr(feedback_data, 'conversation_id', 'None')}")
        
        if hasattr(feedback_data, 'quality_feedback') and feedback_data.quality_feedback:
            logger.info(f"📈 [Feedback] Qualité détaillée: {len(feedback_data.quality_feedback)} métriques")
        
        if expert_service and hasattr(expert_service, 'process_feedback'):
            result = await expert_service.process_feedback(feedback_data)
        else:
            # Fallback si service non disponible
            result = {
                "success": True,
                "message": "Feedback enregistré (mode fallback)",
                "rating": feedback_data.rating,
                "comment": getattr(feedback_data, 'comment', None),
                "conversation_id": getattr(feedback_data, 'conversation_id', None),
                "fallback_mode": True,
                "timestamp": datetime.now().isoformat()
            }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [Feedback] Erreur: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur feedback: {str(e)}")

@router.get("/topics")
async def get_suggested_topics_enhanced(language: str = "fr"):
    """Get suggested topics - VERSION FINALE avec gestion d'erreur"""
    try:
        if expert_service and hasattr(expert_service, 'get_suggested_topics'):
            return await expert_service.get_suggested_topics(language)
        else:
            # Fallback si service non disponible
            fallback_topics = {
                "fr": [
                    "Problèmes de croissance poulets",
                    "Conditions environnementales optimales", 
                    "Protocoles vaccination",
                    "Diagnostic problèmes santé",
                    "Nutrition et alimentation",
                    "Mortalité élevée - causes"
                ],
                "en": [
                    "Chicken growth problems",
                    "Optimal environmental conditions",
                    "Vaccination protocols", 
                    "Health problem diagnosis",
                    "Nutrition and feeding",
                    "High mortality - causes"
                ],
                "es": [
                    "Problemas de crecimiento pollos",
                    "Condiciones ambientales óptimas",
                    "Protocolos de vacunación",
                    "Diagnóstico problemas de salud", 
                    "Nutrición y alimentación",
                    "Alta mortalidad - causas"
                ]
            }
            
            lang = language.lower() if language else "fr"
            if lang not in fallback_topics:
                lang = "fr"
            
            return {
                "topics": fallback_topics[lang],
                "language": lang,
                "count": len(fallback_topics[lang]),
                "fallback_mode": True,
                "expert_service_available": False,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ [Topics] Erreur: {e}")
        raise HTTPException(status_code=500, detail="Erreur topics")

# =============================================================================
# FONCTIONS UTILITAIRES AVEC PROPAGATION v3.7.3
# =============================================================================

def _create_incomplete_clarification_response(
    request_data: EnhancedQuestionRequest, 
    clarified_entities: Dict[str, str], 
    breed: Optional[str], 
    sex: Optional[str], 
    start_time: float,
    public: bool = False
) -> EnhancedExpertResponse:
    """Crée une réponse pour clarification incomplète avec PROPAGATION CHAMPS v3.7.3"""
    
    # Validation granulaire des informations manquantes
    missing_info = []
    missing_details = []
    provided_parts = []
    missing_critical_entities = []  # NOUVEAU CHAMP v3.7.3
    
    # Vérification breed avec plus de nuances
    if not breed:
        missing_info.append("race/souche")
        missing_details.append("la race/souche (Ross 308, Cobb 500, Hubbard, etc.)")
        missing_critical_entities.append("breed")  # NOUVEAU v3.7.3
    elif len(breed.strip()) < 3:  # Breed trop court/vague
        missing_info.append("race/souche complète")
        missing_details.append("la race/souche complète (ex: 'Ross' → 'Ross 308')")
        provided_parts.append(f"Race partielle détectée: {breed}")
        missing_critical_entities.append("breed_complete")  # NOUVEAU v3.7.3
    else:
        provided_parts.append(f"Race détectée: {breed}")
    
    # Vérification sex
    if not sex:
        missing_info.append("sexe")
        missing_details.append("le sexe (mâles, femelles, ou mixte)")
        missing_critical_entities.append("sex")  # NOUVEAU v3.7.3
    else:
        provided_parts.append(f"Sexe détecté: {sex}")
    
    # 🎯 MESSAGE ADAPTATIF selon ce qui manque réellement
    if len(missing_info) == 2:
        error_message = f"Information incomplète. Il manque encore : {' et '.join(missing_info)}.\n\n"
    elif len(missing_info) == 1:
        error_message = f"Information incomplète. Il manque encore : {missing_info[0]}.\n\n"
    else:
        error_message = "Information incomplète.\n\n"
    
    # Ajouter contexte de ce qui a été fourni VS ce qui manque
    if provided_parts:
        error_message += f"Votre réponse '{request_data.text}' contient : {', '.join(provided_parts)}.\n"
        error_message += f"Mais il manque encore : {', '.join(missing_details)}.\n\n"
    else:
        error_message += f"Votre réponse '{request_data.text}' ne contient pas tous les éléments nécessaires.\n\n"
    
    # Exemples contextuels selon ce qui manque
    error_message += "**Exemples complets :**\n"
    
    if "race" in str(missing_info):
        error_message += "• 'Ross 308 mâles'\n"
        error_message += "• 'Cobb 500 femelles'\n" 
        error_message += "• 'Hubbard troupeau mixte'\n\n"
    elif "sexe" in str(missing_info):
        # Si seul le sexe manque, adapter les exemples avec la race détectée
        if breed and len(breed.strip()) >= 3:
            error_message += f"• '{breed} mâles'\n"
            error_message += f"• '{breed} femelles'\n"
            error_message += f"• '{breed} troupeau mixte'\n\n"
        else:
            error_message += "• 'Ross 308 mâles'\n"
            error_message += "• 'Cobb 500 femelles'\n"
            error_message += "• 'Hubbard troupeau mixte'\n\n"
    
    error_message += "Pouvez-vous préciser les informations manquantes ?"
    
    # Retourner erreur clarification incomplète AVEC NOUVEAUX CHAMPS v3.7.3
    mode_suffix = "_public" if public else ""
    
    logger.info(f"📋 [CLARIFICATION INCOMPLÈTE v3.7.3] Entités critiques manquantes: {missing_critical_entities}")
    
    return EnhancedExpertResponse(
        question=request_data.text,
        response=error_message,
        conversation_id=getattr(request_data, 'conversation_id', None) or str(uuid.uuid4()),
        rag_used=False,
        rag_score=None,
        timestamp=datetime.now().isoformat(),
        language=getattr(request_data, 'language', 'fr'),
        response_time_ms=int((time.time() - start_time) * 1000),
        mode=f"incomplete_clarification_response{mode_suffix}",
        user=None,
        logged=True,
        validation_passed=False,
        # 🚀 NOUVEAUX CHAMPS v3.7.3 POUR CLARIFICATION INCOMPLÈTE
        clarification_required_critical=True,  # NOUVEAU v3.7.3
        missing_critical_entities=missing_critical_entities,  # NOUVEAU v3.7.3
        variants_tested=[],  # NOUVEAU v3.7.3 - vide pour clarification incomplète
        clarification_result={
            "clarification_requested": True,
            "clarification_type": f"incomplete_entities_retry{mode_suffix}",
            "missing_information": missing_info,
            "provided_entities": clarified_entities,
            "provided_parts": provided_parts,
            "missing_details": missing_details,
            "retry_required": True,
            "confidence": 0.3,
            # 🚀 NOUVEAUX CHAMPS DANS CLARIFICATION_RESULT v3.7.3
            "clarification_required_critical": True,
            "missing_critical_entities": missing_critical_entities
        },
        processing_steps=[f"incomplete_clarification_detected{mode_suffix}", "retry_requested"],
        ai_enhancements_used=[f"incomplete_clarification_handling{mode_suffix}"],
        response_versions=None  # Pas de response_versions pour erreurs
    )

async def _fallback_expert_response(
    request_data: EnhancedQuestionRequest, 
    start_time: float, 
    current_user: Optional[Dict[str, Any]] = None,
    error_message: str = "Service expert temporairement indisponible"
) -> EnhancedExpertResponse:
    """Réponse de fallback quand le service expert n'est pas disponible AVEC NOUVEAUX CHAMPS v3.7.3"""
    
    logger.info("🔄 [Fallback v3.7.3] Génération réponse de fallback avec nouveaux champs")
    
    fallback_responses = {
        "fr": f"Je m'excuse, {error_message}. Votre question '{request_data.text}' a été reçue mais je ne peux pas la traiter actuellement. Veuillez réessayer dans quelques minutes.",
        "en": f"I apologize, {error_message}. Your question '{request_data.text}' was received but I cannot process it currently. Please try again in a few minutes.",
        "es": f"Me disculpo, {error_message}. Su pregunta '{request_data.text}' fue recibida pero no puedo procesarla actualmente. Por favor intente de nuevo en unos minutos."
    }
    
    language = getattr(request_data, 'language', 'fr')
    response_text = fallback_responses.get(language, fallback_responses['fr'])
    
    return EnhancedExpertResponse(
        question=request_data.text,
        response=response_text,
        conversation_id=getattr(request_data, 'conversation_id', None) or str(uuid.uuid4()),
        rag_used=False,
        rag_score=None,
        timestamp=datetime.now().isoformat(),
        language=language,
        response_time_ms=int((time.time() - start_time) * 1000),
        mode="fallback_service_unavailable",
        user=current_user.get("email") if current_user else None,
        logged=False,
        validation_passed=False,
        # 🚀 NOUVEAUX CHAMPS v3.7.3 POUR FALLBACK
        clarification_required_critical=False,  # NOUVEAU v3.7.3
        missing_critical_entities=[],  # NOUVEAU v3.7.3
        variants_tested=[],  # NOUVEAU v3.7.3
        processing_steps=["service_unavailable", "fallback_response_generated"],
        ai_enhancements_used=["fallback_handling"],
        response_versions=None
    )

# =============================================================================
# CONFIGURATION FINALE v3.7.3 AVEC PROPAGATION NOUVEAUX CHAMPS 🚀
# =============================================================================

logger.info("🚀" * 50)
logger.info("🚀 [EXPERT ENDPOINTS MAIN] VERSION 3.7.3 - PROPAGATION NOUVEAUX CHAMPS + CLARIFICATION GRANULAIRE!")
logger.info("🚀 [NOUVEAUX CHAMPS PROPAGÉS v3.7.3]:")
logger.info("   ✅ clarification_required_critical - Indique si clarification critique requise")
logger.info("   ✅ missing_critical_entities - Liste entités critiques manquantes")
logger.info("   ✅ variants_tested - Liste variantes testées par RAG enhancement")
logger.info("")
logger.info("🚀 [PROPAGATION INTÉGRÉE]:")
logger.info("   ✅ Extraction automatique depuis clarification_result")
logger.info("   ✅ Extraction automatique depuis rag_enhancement_info")
logger.info("   ✅ Application dans toutes les réponses (privé/public)")
logger.info("   ✅ Support dans clarification incomplète")
logger.info("   ✅ Support dans réponses fallback")
logger.info("")
logger.info("🚀 [FONCTIONNALITÉS CONSERVÉES]:")
logger.info("   ✅ Support concision_level et generate_all_versions")
logger.info("   ✅ response_versions dans les réponses")
logger.info("   ✅ Logique clarification GRANULAIRE et adaptative")
logger.info("   ✅ Messages adaptatifs selon ce qui manque réellement")
logger.info("   ✅ Exemples contextuels avec race détectée")
logger.info("   ✅ Métadonnées enrichies (provided_parts, missing_details)")
logger.info("   ✅ Validation granulaire breed vs sex")
logger.info("   ✅ UX clarification grandement améliorée")
logger.info("   ✅ Gestion d'erreur robuste complète")
logger.info("")
logger.info("🔧 [ENDPOINTS DISPONIBLES]:")
logger.info("   - GET /health (diagnostic + version)")
logger.info("   - POST /ask-enhanced-v2 (privé + auth + propagation)")
logger.info("   - POST /ask-enhanced-v2-public (public + propagation)")
logger.info("   - POST /feedback (qualité détaillée)")
logger.info("   - GET /topics (suggestions enrichies)")
logger.info("")
logger.info("🎯 [PROPAGATION PROCESS v3.7.3]:")
logger.info("   1. _extract_propagation_fields() - Extraction depuis response")
logger.info("   2. _apply_propagation_fields() - Application à EnhancedExpertResponse")
logger.info("   3. Logging détaillé des valeurs propagées")
logger.info("   4. Support dans tous les types de réponses")
logger.info("   ✅ READY FOR PRODUCTION - NOUVEAUX CHAMPS PROPAGÉS")
logger.info("🚀" * 50)