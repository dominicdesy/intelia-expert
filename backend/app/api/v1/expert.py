"""
app/api/v1/expert.py - EXPERT ENDPOINTS PRINCIPAUX v3.7.2 - CORRIGÉ

🚀 FICHIER PRINCIPAL MAINTENU POUR COMPATIBILITÉ:
- Garde le nom expert.py pour éviter les changements de liens
- Endpoints principaux avec clarification granulaire
- Support response_versions complet
- Code allégé et maintenable
- ✅ CORRECTIONS: Variables initialisées, vérifications robustes

VERSION COMPLÈTE + SYNTAXE 100% CORRIGÉE + SUPPORT RESPONSE_VERSIONS + CLARIFICATION INTELLIGENTE
"""

import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer

from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest, ConcisionLevel
from .expert_services import ExpertService
from .expert_utils import get_user_id_from_request, extract_breed_and_sex_from_clarification

router = APIRouter(tags=["expert-main"])
logger = logging.getLogger(__name__)
security = HTTPBearer()

# Service principal
expert_service = ExpertService()

# =============================================================================
# ENDPOINTS PRINCIPAUX AVEC CLARIFICATION GRANULAIRE v3.7.2 🚀
# =============================================================================

@router.post("/ask-enhanced-v2", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """
    🧨 ENDPOINT EXPERT FINAL avec DÉTECTION CLARIFICATION GRANULAIRE v3.7.2:
    - Support explicite du flag is_clarification_response
    - Logique clarification granulaire et adaptative
    - Métadonnées propagées correctement
    - Génération multi-versions des réponses
    - Messages de clarification adaptatifs selon ce qui manque réellement
    ✅ CORRIGÉ: Variables initialisées, vérifications robustes
    """
    start_time = time.time()
    
    try:
        logger.info("=" * 100)
        logger.info("🚀 DÉBUT ask_expert_enhanced_v2 v3.7.2 - SUPPORT RESPONSE_VERSIONS + CLARIFICATION INTELLIGENTE")
        logger.info(f"📝 Question/Réponse: '{request_data.text}'")
        logger.info(f"🆔 Conversation ID: {request_data.conversation_id}")
        
        # ✅ CORRECTION: Vérification robuste des paramètres concision
        concision_level = ConcisionLevel.CONCISE
        generate_all_versions = True
        
        if request_data and hasattr(request_data, 'concision_level') and request_data.concision_level is not None:
            concision_level = request_data.concision_level
        if request_data and hasattr(request_data, 'generate_all_versions') and request_data.generate_all_versions is not None:
            generate_all_versions = request_data.generate_all_versions
        
        logger.info("🚀 [RESPONSE_VERSIONS v3.7.2] Paramètres concision:")
        logger.info(f"   - concision_level: {concision_level}")
        logger.info(f"   - generate_all_versions: {generate_all_versions}")
        
        # DÉTECTION EXPLICITE MODE CLARIFICATION
        is_clarification = False
        original_question = None
        clarification_entities = None
        
        if request_data:
            is_clarification = getattr(request_data, 'is_clarification_response', False)
            original_question = getattr(request_data, 'original_question', None)
            clarification_entities = getattr(request_data, 'clarification_entities', None)
        
        logger.info("🧨 [DÉTECTION CLARIFICATION v3.7.2] Analyse du mode:")
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
            
            # TRAITEMENT SPÉCIALISÉ RÉPONSE CLARIFICATION
            if clarification_entities:
                logger.info(f"   - Entités pré-extraites: {clarification_entities}")
                breed = clarification_entities.get('breed')
                sex = clarification_entities.get('sex')
            else:
                # Extraction automatique si pas fournie
                logger.info("   - Extraction automatique entités depuis réponse")
                try:
                    extracted = extract_breed_and_sex_from_clarification(request_data.text, request_data.language)
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
            
            # 🎯 NOUVELLE LOGIQUE GRANULAIRE v3.7.2: Validation granulaire breed vs sex
            if not breed or not sex:
                # ✅ CORRECTION: Protection contre None dans le logging
                breed_safe = breed or "None"
                sex_safe = sex or "None"
                logger.warning(f"⚠️ [FLUX CLARIFICATION] Entités incomplètes: breed='{breed_safe}', sex='{sex_safe}'")
                
                # Validation granulaire des informations manquantes
                missing_info = []
                missing_details = []
                provided_parts = []
                
                # Vérification breed avec plus de nuances
                if not breed:
                    missing_info.append("race/souche")
                    missing_details.append("la race/souche (Ross 308, Cobb 500, Hubbard, etc.)")
                elif len(breed.strip()) < 3:  # Breed trop court/vague
                    missing_info.append("race/souche complète")
                    missing_details.append("la race/souche complète (ex: 'Ross' → 'Ross 308')")
                    provided_parts.append(f"Race partielle détectée: {breed}")
                else:
                    provided_parts.append(f"Race détectée: {breed}")
                
                # Vérification sex
                if not sex:
                    missing_info.append("sexe")
                    missing_details.append("le sexe (mâles, femelles, ou mixte)")
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
                
                # Retourner erreur clarification incomplète GRANULAIRE
                incomplete_clarification_response = EnhancedExpertResponse(
                    question=request_data.text,
                    response=error_message,
                    conversation_id=request_data.conversation_id or str(uuid.uuid4()),
                    rag_used=False,
                    rag_score=None,
                    timestamp=datetime.now().isoformat(),
                    language=request_data.language,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    mode="incomplete_clarification_response",
                    user=current_user.get("email") if current_user else None,
                    logged=True,
                    validation_passed=False,
                    clarification_result={
                        "clarification_requested": True,
                        "clarification_type": "incomplete_entities_retry",
                        "missing_information": missing_info,
                        "provided_entities": clarified_entities,
                        "provided_parts": provided_parts,
                        "missing_details": missing_details,
                        "retry_required": True,
                        "confidence": 0.3
                    },
                    processing_steps=["incomplete_clarification_detected", "retry_requested"],
                    ai_enhancements_used=["incomplete_clarification_handling"],
                    response_versions=None  # Pas de response_versions pour erreurs
                )
                
                logger.info(f"❌ [FLUX CLARIFICATION v3.7.2] Retour erreur entités incomplètes: {missing_info}")
                logger.info(f"💡 [FLUX CLARIFICATION v3.7.2] Parties détectées: {provided_parts}")
                return incomplete_clarification_response
            
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
                request_data.is_clarification_response = False
                
                logger.info("🎯 [FLUX CLARIFICATION] Question enrichie, passage au traitement RAG")
            else:
                logger.warning("⚠️ [FLUX CLARIFICATION] Question originale manquante - impossible enrichir")
        else:
            logger.info("🎯 [FLUX CLARIFICATION] Mode QUESTION INITIALE - détection vagueness active")
        
        # ✅ CORRECTION: Validation et défauts concision robuste
        if not hasattr(request_data, 'concision_level') or request_data.concision_level is None:
            request_data.concision_level = ConcisionLevel.CONCISE
            logger.info("🚀 [CONCISION] Niveau par défaut appliqué: CONCISE")
        
        if not hasattr(request_data, 'generate_all_versions') or request_data.generate_all_versions is None:
            request_data.generate_all_versions = True
            logger.info("🚀 [CONCISION] generate_all_versions activé par défaut")
        
        # FORÇAGE SYSTÉMATIQUE DES AMÉLIORATIONS
        original_vagueness = getattr(request_data, 'enable_vagueness_detection', None)
        original_coherence = getattr(request_data, 'require_coherence_check', None)
        
        # FORCER l'activation - AUCUNE EXCEPTION
        request_data.enable_vagueness_detection = True
        request_data.require_coherence_check = True
        
        logger.info("🔥 [CLARIFICATION FORCÉE v3.7.2] Paramètres forcés:")
        logger.info(f"   - enable_vagueness_detection: {original_vagueness} → TRUE (FORCÉ)")
        logger.info(f"   - require_coherence_check: {original_coherence} → TRUE (FORCÉ)")
        
        # DÉLÉGUER AU SERVICE
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=current_user,
            start_time=start_time
        )
        
        # AJOUT MÉTADONNÉES CLARIFICATION dans response
        if clarification_metadata:
            response.clarification_processing = clarification_metadata
            logger.info("💡 [MÉTADONNÉES v3.7.2] Clarification metadata ajoutées à response")
        
        # Log response_versions si présentes
        if hasattr(response, 'response_versions') and response.response_versions:
            logger.info("🚀 [RESPONSE_VERSIONS] Versions générées:")
            for level, content in response.response_versions.items():
                logger.info(f"   - {level}: {len(content)} caractères")
        
        # LOGGING RÉSULTATS CLARIFICATION DÉTAILLÉ
        logger.info("🧨 [RÉSULTATS CLARIFICATION v3.7.2]:")
        logger.info(f"   - Mode final: {response.mode}")
        logger.info(f"   - Clarification déclenchée: {response.clarification_result is not None}")
        logger.info(f"   - RAG utilisé: {response.rag_used}")
        logger.info(f"   - Question finale traitée: '{response.question[:100]}...'")
        
        if response.clarification_result:
            clarif = response.clarification_result
            logger.info(f"   - Type clarification: {clarif.get('clarification_type', 'N/A')}")
            logger.info(f"   - Infos manquantes: {clarif.get('missing_information', [])}")
            logger.info(f"   - Confiance: {clarif.get('confidence', 0)}")
            if 'provided_parts' in clarif:
                logger.info(f"   - Parties détectées: {clarif.get('provided_parts', [])}")
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2 v3.7.2 - Temps: {response.response_time_ms}ms")
        logger.info(f"🤖 Améliorations: {len(response.ai_enhancements_used or [])} features")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2 v3.7.2: {e}")
        logger.info("=" * 100)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@router.post("/ask-enhanced-v2-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_v2_public(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """🧨 ENDPOINT PUBLIC avec DÉTECTION CLARIFICATION GRANULAIRE v3.7.2
    ✅ CORRIGÉ: Variables initialisées, vérifications robustes"""
    start_time = time.time()
    
    try:
        logger.info("=" * 100)
        logger.info("🌐 DÉBUT ask_expert_enhanced_v2_public v3.7.2 - SUPPORT RESPONSE_VERSIONS + CLARIFICATION INTELLIGENTE")
        logger.info(f"📝 Question/Réponse: '{request_data.text}'")
        
        # ✅ CORRECTION: Paramètres concision pour endpoint public avec vérifications
        concision_level = ConcisionLevel.CONCISE
        generate_all_versions = True
        
        if request_data and hasattr(request_data, 'concision_level') and request_data.concision_level is not None:
            concision_level = request_data.concision_level
        if request_data and hasattr(request_data, 'generate_all_versions') and request_data.generate_all_versions is not None:
            generate_all_versions = request_data.generate_all_versions
        
        logger.info("🚀 [RESPONSE_VERSIONS PUBLIC] Paramètres concision:")
        logger.info(f"   - concision_level: {concision_level}")
        logger.info(f"   - generate_all_versions: {generate_all_versions}")
        
        # DÉTECTION PUBLIQUE CLARIFICATION
        is_clarification = False
        clarification_metadata = {}
        
        if request_data:
            is_clarification = getattr(request_data, 'is_clarification_response', False)
        
        logger.info("🧨 [DÉTECTION PUBLIQUE v3.7.2] Analyse mode clarification:")
        logger.info(f"   - is_clarification_response: {is_clarification}")
        logger.info(f"   - conversation_id: {request_data.conversation_id}")
        
        if is_clarification:
            logger.info("🎪 [FLUX PUBLIC] Traitement réponse clarification")
            
            # Logique similaire à l'endpoint privé
            original_question = getattr(request_data, 'original_question', None)
            clarification_entities = getattr(request_data, 'clarification_entities', None)
            
            logger.info(f"   - Question originale: '{original_question}'")
            logger.info(f"   - Entités fournies: {clarification_entities}")
            
            # ✅ CORRECTION: Initialisation sécurisée des variables breed/sex
            breed = None
            sex = None
            
            if clarification_entities:
                breed = clarification_entities.get('breed')
                sex = clarification_entities.get('sex')
                logger.info(f"   - Utilisation entités pré-extraites: breed='{breed}', sex='{sex}'")
            else:
                # Extraction automatique
                try:
                    extracted = extract_breed_and_sex_from_clarification(request_data.text, request_data.language)
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
            
            # 🎯 LOGIQUE GRANULAIRE PUBLIQUE v3.7.2
            if not breed or not sex:
                breed_safe = breed or "None"
                sex_safe = sex or "None"
                logger.warning(f"⚠️ [FLUX PUBLIC] Entités incomplètes: breed='{breed_safe}', sex='{sex_safe}'")
                
                # Validation granulaire des informations manquantes
                missing_info = []
                missing_details = []
                provided_parts = []
                
                # Vérification breed avec plus de nuances
                if not breed:
                    missing_info.append("race/souche")
                    missing_details.append("la race/souche (Ross 308, Cobb 500, Hubbard, etc.)")
                elif len(breed.strip()) < 3:
                    missing_info.append("race/souche complète")
                    missing_details.append("la race/souche complète (ex: 'Ross' → 'Ross 308')")
                    provided_parts.append(f"Race partielle détectée: {breed}")
                else:
                    provided_parts.append(f"Race détectée: {breed}")
                
                # Vérification sex
                if not sex:
                    missing_info.append("sexe")
                    missing_details.append("le sexe (mâles, femelles, ou mixte)")
                else:
                    provided_parts.append(f"Sexe détecté: {sex}")
                
                # MESSAGE ADAPTATIF selon ce qui manque réellement
                if len(missing_info) == 2:
                    error_message = f"Information incomplète. Il manque encore : {' et '.join(missing_info)}.\n\n"
                elif len(missing_info) == 1:
                    error_message = f"Information incomplète. Il manque encore : {missing_info[0]}.\n\n"
                else:
                    error_message = "Information incomplète.\n\n"
                
                # Ajouter contexte
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
                    if breed and len(breed.strip()) >= 3:
                        error_message += f"• '{breed} mâles'\n"
                        error_message += f"• '{breed} femelles'\n"
                        error_message += f"• '{breed} troupeau mixte'\n\n"
                    else:
                        error_message += "• 'Ross 308 mâles'\n"
                        error_message += "• 'Cobb 500 femelles'\n"
                        error_message += "• 'Hubbard troupeau mixte'\n\n"
                
                error_message += "Pouvez-vous préciser les informations manquantes ?"
                
                # Retourner erreur clarification incomplète publique
                return EnhancedExpertResponse(
                    question=request_data.text,
                    response=error_message,
                    conversation_id=request_data.conversation_id or str(uuid.uuid4()),
                    rag_used=False,
                    rag_score=None,
                    timestamp=datetime.now().isoformat(),
                    language=request_data.language,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    mode="incomplete_clarification_response_public",
                    user=None,
                    logged=True,
                    validation_passed=False,
                    clarification_result={
                        "clarification_requested": True,
                        "clarification_type": "incomplete_entities_retry_public",
                        "missing_information": missing_info,
                        "provided_entities": clarified_entities,
                        "provided_parts": provided_parts,
                        "missing_details": missing_details,
                        "retry_required": True,
                        "confidence": 0.3
                    },
                    processing_steps=["incomplete_clarification_detected_public", "retry_requested"],
                    ai_enhancements_used=["incomplete_clarification_handling_public"],
                    response_versions=None
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
                request_data.is_clarification_response = False  # Éviter boucle
                
                logger.info(f"   - Question enrichie publique: '{enriched_question}'")
                logger.info(f"   - Métadonnées sauvegardées: {clarification_metadata}")
        else:
            logger.info("🎯 [FLUX PUBLIC] Question initiale - détection vagueness")
        
        # ✅ CORRECTION: Validation et défauts concision pour public
        if not hasattr(request_data, 'concision_level') or request_data.concision_level is None:
            request_data.concision_level = ConcisionLevel.CONCISE
        
        if not hasattr(request_data, 'generate_all_versions') or request_data.generate_all_versions is None:
            request_data.generate_all_versions = True
        
        # FORÇAGE MAXIMAL pour endpoint public
        logger.info("🔥 [PUBLIC ENDPOINT v3.7.2] Activation FORCÉE des améliorations:")
        
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
        
        logger.info("🔥 [FORÇAGE PUBLIC v3.7.2] Changements appliqués:")
        for key, (old_val, new_val) in {
            'vagueness_detection': (original_settings['vagueness'], True),
            'coherence_check': (original_settings['coherence'], True),
            'detailed_rag': (original_settings['detailed_rag'], True),
            'quality_metrics': (original_settings['quality_metrics'], True)
        }.items():
            logger.info(f"   - {key}: {old_val} → {new_val} (FORCÉ)")
        
        # DÉLÉGUER AU SERVICE avec support response_versions
        response = await expert_service.process_expert_question(
            request_data=request_data,
            request=request,
            current_user=None,  # Mode public
            start_time=start_time
        )
        
        # Ajout métadonnées clarification
        if clarification_metadata:
            response.clarification_processing = clarification_metadata
            logger.info("💡 [MÉTADONNÉES PUBLIC v3.7.2] Clarification metadata ajoutées")
        
        # Log response_versions si présentes
        if hasattr(response, 'response_versions') and response.response_versions:
            logger.info("🚀 [RESPONSE_VERSIONS PUBLIC] Versions générées:")
            for level, content in response.response_versions.items():
                logger.info(f"   - {level}: {len(content)} caractères")
        
        # VALIDATION RÉSULTATS CLARIFICATION PUBLIQUE
        logger.info("🧨 [VALIDATION PUBLIQUE v3.7.2]:")
        logger.info(f"   - Clarification système actif: {'clarification' in response.mode}")
        logger.info(f"   - Améliorations appliquées: {response.ai_enhancements_used}")
        logger.info(f"   - Mode final: {response.mode}")
        logger.info(f"   - RAG utilisé: {response.rag_used}")
        
        # Vérification critique
        if not response.ai_enhancements_used:
            logger.warning("⚠️ [ALERTE] Aucune amélioration détectée - possible problème!")
        
        if response.enable_vagueness_detection is False:
            logger.warning("⚠️ [ALERTE] Vagueness detection non activée - vérifier forçage!")
        
        logger.info(f"✅ FIN ask_expert_enhanced_v2_public v3.7.2 - Mode: {response.mode}")
        logger.info("=" * 100)
        
        return response
    
    except HTTPException:
        logger.info("=" * 100)
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique ask_expert_enhanced_v2_public v3.7.2: {e}")
        logger.info("=" * 100)
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

# =============================================================================
# ENDPOINT FEEDBACK ET TOPICS
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

@router.get("/topics")
async def get_suggested_topics_enhanced(language: str = "fr"):
    """Get suggested topics - VERSION FINALE"""
    try:
        return await expert_service.get_suggested_topics(language)
    except Exception as e:
        logger.error(f"❌ [Topics] Erreur: {e}")
        raise HTTPException(status_code=500, detail="Erreur topics")

# =============================================================================
# CONFIGURATION FINALE v3.7.2 🚀
# =============================================================================

logger.info("🚀" * 50)
logger.info("🚀 [EXPERT ENDPOINTS MAIN] VERSION 3.7.2 - LOGIQUE CLARIFICATION GRANULAIRE!")
logger.info("🚀 [FONCTIONNALITÉS PRINCIPALES]:")
logger.info("   ✅ Support concision_level et generate_all_versions")
logger.info("   ✅ response_versions dans les réponses")
logger.info("   ✅ Logique clarification GRANULAIRE et adaptative")
logger.info("   ✅ Messages adaptatifs selon ce qui manque réellement")
logger.info("   ✅ Exemples contextuels avec race détectée")
logger.info("   ✅ Métadonnées enrichies (provided_parts, missing_details)")
logger.info("   ✅ Validation granulaire breed vs sex")
logger.info("   ✅ UX clarification grandement améliorée")
logger.info("   ✅ CORRECTIONS: Variables initialisées, vérifications robustes")
logger.info("")
logger.info("🔧 [ENDPOINTS PRINCIPAUX]:")
logger.info("   - POST /ask-enhanced-v2 (privé + auth)")
logger.info("   - POST /ask-enhanced-v2-public (public)")
logger.info("   - POST /feedback (qualité détaillée)")
logger.info("   - GET /topics (suggestions enrichies)")
logger.info("")
logger.info("🎯 [FICHIER ALLÉGÉ ET MAINTENABLE]:")
logger.info("   ✅ Endpoints principaux uniquement")
logger.info("   ✅ Code propre et commenté")
logger.info("   ✅ Logique clarification granulaire v3.7.2")
logger.info("   ✅ Support response_versions complet")
logger.info("   ✅ CORRECTIONS APPLIQUÉES - Variables, vérifications")
logger.info("   ✅ READY FOR PRODUCTION")
logger.info("🚀" * 50)