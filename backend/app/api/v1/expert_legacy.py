"""
app/api/v1/expert_legacy.py - ENDPOINTS DE COMPATIBILITÉ v3.7.2 - CORRIGÉ

🔄 ENDPOINTS DE COMPATIBILITÉ BACKWARD:
- Maintien des anciens endpoints avec redirection
- Forçage automatique des améliorations
- Support response_versions ajouté
- Garantie de compatibilité 100%
- ✅ CORRECTIONS: Import circulaire résolu, vérifications ajoutées

✅ CORRECTION IMPORTS CIRCULAIRES:
- Import dynamique dans les fonctions pour éviter les dépendances circulaires
- Solution recommandée par les best practices FastAPI/Python
"""

import logging
import time
import re
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException

from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, ConcisionLevel
from .expert_services import ExpertService

router = APIRouter(tags=["expert-legacy"])
logger = logging.getLogger(__name__)

# Service principal
expert_service = ExpertService()

# =============================================================================
# ENDPOINTS DE COMPATIBILITÉ AVEC FORÇAGE MAINTENU + RESPONSE_VERSIONS 🔄
# =============================================================================

@router.post("/ask-enhanced", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_legacy(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """Endpoint de compatibilité v1 - FORÇAGE APPLIQUÉ + CLARIFICATION SUPPORT + RESPONSE_VERSIONS
    ✅ CORRIGÉ: Vérifications robustes"""
    logger.info("🔄 [LEGACY] Redirection avec FORÇAGE + clarification + response_versions vers v2")
    
    # ✅ CORRECTION: Vérification existence request_data
    if not request_data:
        raise HTTPException(status_code=400, detail="Request data manquant")
    
    # 🔥 FORÇAGE LEGACY
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    
    # 🚀 v3.7.2: Support concision par défaut avec vérifications
    if not hasattr(request_data, 'concision_level') or request_data.concision_level is None:
        request_data.concision_level = ConcisionLevel.CONCISE
    if not hasattr(request_data, 'generate_all_versions') or request_data.generate_all_versions is None:
        request_data.generate_all_versions = True
    
    # ✅ CORRECTION: Import dynamique pour éviter import circulaire
    from .expert import ask_expert_enhanced_v2
    return await ask_expert_enhanced_v2(request_data, request, current_user)

@router.post("/ask-enhanced-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_public_legacy(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint public de compatibilité v1 - FORÇAGE APPLIQUÉ + CLARIFICATION SUPPORT + RESPONSE_VERSIONS
    ✅ CORRIGÉ: Vérifications robustes"""
    logger.info("🔄 [LEGACY PUBLIC] Redirection avec FORÇAGE + clarification + response_versions vers v2")
    
    # ✅ CORRECTION: Vérification existence request_data
    if not request_data:
        raise HTTPException(status_code=400, detail="Request data manquant")
    
    # 🔥 FORÇAGE LEGACY PUBLIC
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    
    # 🚀 v3.7.2: Support concision par défaut avec vérifications
    if not hasattr(request_data, 'concision_level') or request_data.concision_level is None:
        request_data.concision_level = ConcisionLevel.CONCISE
    if not hasattr(request_data, 'generate_all_versions') or request_data.generate_all_versions is None:
        request_data.generate_all_versions = True
    
    # ✅ CORRECTION: Import dynamique pour éviter import circulaire
    from .expert import ask_expert_enhanced_v2_public
    return await ask_expert_enhanced_v2_public(request_data, request)

@router.post("/ask", response_model=EnhancedExpertResponse)
async def ask_expert_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(expert_service.get_current_user_dependency())
):
    """Endpoint de compatibilité original - FORÇAGE TOTAL + CLARIFICATION SUPPORT + RESPONSE_VERSIONS
    ✅ CORRIGÉ: Vérifications robustes"""
    logger.info("🔄 [COMPATIBLE] Redirection avec FORÇAGE TOTAL + clarification + response_versions vers v2")
    
    # ✅ CORRECTION: Vérification existence request_data
    if not request_data:
        raise HTTPException(status_code=400, detail="Request data manquant")
    
    # 🔥 FORÇAGE COMPATIBILITÉ TOTALE
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    request_data.detailed_rag_scoring = True
    request_data.enable_quality_metrics = True
    
    # 🚀 v3.7.2: Support concision par défaut avec vérifications
    if not hasattr(request_data, 'concision_level') or request_data.concision_level is None:
        request_data.concision_level = ConcisionLevel.CONCISE
    if not hasattr(request_data, 'generate_all_versions') or request_data.generate_all_versions is None:
        request_data.generate_all_versions = True
    
    # ✅ CORRECTION: Import dynamique pour éviter import circulaire
    from .expert import ask_expert_enhanced_v2
    return await ask_expert_enhanced_v2(request_data, request, current_user)

@router.post("/ask-public", response_model=EnhancedExpertResponse)
async def ask_expert_public_compatible(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """Endpoint public de compatibilité original - FORÇAGE TOTAL + CLARIFICATION SUPPORT + RESPONSE_VERSIONS
    ✅ CORRIGÉ: Vérifications robustes"""
    logger.info("🔄 [COMPATIBLE PUBLIC] Redirection avec FORÇAGE TOTAL + clarification + response_versions vers v2")
    
    # ✅ CORRECTION: Vérification existence request_data
    if not request_data:
        raise HTTPException(status_code=400, detail="Request data manquant")
    
    # 🔥 FORÇAGE COMPATIBILITÉ PUBLIQUE TOTALE
    request_data.enable_vagueness_detection = True
    request_data.require_coherence_check = True
    request_data.detailed_rag_scoring = True
    request_data.enable_quality_metrics = True
    
    # 🚀 v3.7.2: Support concision par défaut avec vérifications
    if not hasattr(request_data, 'concision_level') or request_data.concision_level is None:
        request_data.concision_level = ConcisionLevel.CONCISE
    if not hasattr(request_data, 'generate_all_versions') or request_data.generate_all_versions is None:
        request_data.generate_all_versions = True
    
    # ✅ CORRECTION: Import dynamique pour éviter import circulaire
    from .expert import ask_expert_enhanced_v2_public
    return await ask_expert_enhanced_v2_public(request_data, request)

@router.post("/ask-with-clarification", response_model=EnhancedExpertResponse)
async def ask_with_forced_clarification(
    request_data: EnhancedQuestionRequest,
    request: Request
):
    """🎯 Endpoint avec clarification GARANTIE pour questions techniques
    🚀 v3.7.2: Support response_versions + logique clarification granulaire
    ✅ CORRIGÉ: Import manquant résolu, vérifications ajoutées"""
    
    start_time = time.time()
    
    try:
        logger.info("🎯 DÉBUT ask_with_forced_clarification v3.7.2")
        
        # ✅ CORRECTION: Vérification existence request_data
        if not request_data or not request_data.text:
            raise HTTPException(status_code=400, detail="Question manquante")
        
        logger.info(f"📝 Question: {request_data.text}")
        
        # ✅ CORRECTION: Support concision par défaut avec vérifications robustes
        if not hasattr(request_data, 'concision_level') or request_data.concision_level is None:
            request_data.concision_level = ConcisionLevel.CONCISE
        if not hasattr(request_data, 'generate_all_versions') or request_data.generate_all_versions is None:
            request_data.generate_all_versions = True
        
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
                ai_enhancements_used=["forced_performance_clarification"],
                response_versions=None  # Pas de response_versions pour clarifications
            )
        
        logger.info("📋 Pas de clarification nécessaire, traitement normal")
        
        # Si pas besoin de clarification, traitement normal avec améliorations forcées
        request_data.enable_vagueness_detection = True
        request_data.require_coherence_check = True
        
        # ✅ CORRECTION CRITIQUE: Import dynamique pour éviter import circulaire
        from .expert import ask_expert_enhanced_v2_public
        return await ask_expert_enhanced_v2_public(request_data, request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur ask_with_forced_clarification: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# =============================================================================
# CONFIGURATION LEGACY 🔄
# =============================================================================

logger.info("🔄" * 50)
logger.info("🔄 [EXPERT LEGACY] VERSION 3.7.2 - ENDPOINTS DE COMPATIBILITÉ!")
logger.info("🔄 [FONCTIONNALITÉS LEGACY]:")
logger.info("   ✅ Redirection automatique vers endpoints v2")
logger.info("   ✅ Forçage automatique des améliorations")
logger.info("   ✅ Support response_versions ajouté")
logger.info("   ✅ Compatibilité backward 100% garantie")
logger.info("   ✅ CORRECTIONS: Import circulaire résolu, vérifications ajoutées")
logger.info("")
logger.info("🔧 [ENDPOINTS LEGACY]:")
logger.info("   - POST /ask-enhanced (legacy → v2)")
logger.info("   - POST /ask-enhanced-public (legacy → v2)")
logger.info("   - POST /ask (compatible → v2)")
logger.info("   - POST /ask-public (compatible → v2)")
logger.info("   - POST /ask-with-clarification (clarification forcée)")
logger.info("")
logger.info("🎯 [AVANTAGES SÉPARATION]:")
logger.info("   ✅ Code principal allégé")
logger.info("   ✅ Legacy isolé et maintenable")
logger.info("   ✅ Évolution facilitée")
logger.info("   ✅ Compatibilité préservée")
logger.info("   ✅ CORRECTION: Imports circulaires résolus")
logger.info("🔄" * 50)