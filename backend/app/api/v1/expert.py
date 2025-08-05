"""
expert.py - POINT D'ENTRÉE PRINCIPAL SIMPLIFIÉ

🎯 NOUVEAU SYSTÈME UNIFIÉ - Plus de conflits, plus de complexité excessive !
🚀 ARCHITECTURE: Entities → Classifier → Generator → Response
✨ SIMPLE: Un seul flux de traitement, des règles claires

Endpoints conservés pour compatibilité:
- POST /ask : Endpoint principal
- POST /ask-public : Version publique
- POST /ask-enhanced : Redirige vers le nouveau système
- POST /ask-enhanced-public : Redirige vers le nouveau système
- POST /feedback : Feedback utilisateur
- GET /topics : Topics disponibles

FINI:
❌ expert_legacy.py (supprimé)
❌ question_clarification_system.py (supprimé) 
❌ expert_services_clarification.py (supprimé)
❌ Tous les systèmes contradictoires

NOUVEAU:
✅ smart_classifier.py
✅ unified_response_generator.py
✅ entities_extractor.py
✅ expert_services.py (simplifié)
"""

import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

# Imports des nouveaux modules unifiés
from .expert_services import ExpertService, ProcessingResult
from .expert_models import EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest
from .intelligent_system_config import INTELLIGENT_SYSTEM_CONFIG

# Import pour récupérer l'utilisateur (si système d'auth disponible)
try:
    from .expert_utils import get_user_id_from_request
    UTILS_AVAILABLE = True
except ImportError:
    def get_user_id_from_request(request):
        return None
    UTILS_AVAILABLE = False

router = APIRouter(tags=["expert"])
logger = logging.getLogger(__name__)

# Service principal unifié - UNE SEULE instance
expert_service = ExpertService()

# =============================================================================
# ENDPOINTS PRINCIPAUX - NOUVEAU SYSTÈME UNIFIÉ
# =============================================================================

@router.post("/ask", response_model=EnhancedExpertResponse)
async def ask_expert(request: EnhancedQuestionRequest, http_request: Request = None):
    """
    🎯 ENDPOINT PRINCIPAL - Nouveau système unifié intelligent
    
    Plus besoin de multiples endpoints ! Un seul endpoint intelligent qui :
    - Extrait automatiquement les entités
    - Classifie intelligemment la question  
    - Génère la réponse adaptée (précise/générale/clarification)
    - Offre la précision quand pertinent
    
    Fini les conflits entre systèmes !
    """
    try:
        logger.info(f"🚀 [Expert API] Question reçue: '{request.text[:50]}...'")
        
        # Validation de base
        if not request.text or len(request.text.strip()) < 2:
            raise HTTPException(
                status_code=400, 
                detail="Question trop courte. Veuillez préciser votre demande."
            )
        
        # Traitement unifié via le service principal
        result = await expert_service.process_question(
            question=request.text,
            context={
                "conversation_id": request.conversation_id,
                "user_id": get_user_id_from_request(http_request) if http_request else None,
                "is_clarification_response": getattr(request, 'is_clarification_response', False),
                "original_question": getattr(request, 'original_question', None)
            },
            language=getattr(request, 'language', 'fr')
        )
        
        # Conversion vers le format de réponse attendu
        response = _convert_processing_result_to_response(request, result)
        
        logger.info(f"✅ [Expert API] Réponse générée: {result.response_type} en {result.processing_time_ms}ms")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Expert API] Erreur ask_expert: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de traitement: {str(e)}")

@router.post("/ask-public", response_model=EnhancedExpertResponse)
async def ask_expert_public(request: EnhancedQuestionRequest):
    """
    🌐 VERSION PUBLIQUE - Même logique que /ask mais sans authentification
    
    Point d'entrée pour les utilisateurs non connectés
    """
    # Utiliser la même logique que ask_expert mais sans récupération d'utilisateur
    return await ask_expert(request, http_request=None)

# =============================================================================
# ENDPOINTS DE COMPATIBILITÉ - REDIRECTION VERS NOUVEAU SYSTÈME
# =============================================================================

@router.post("/ask-enhanced", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_legacy(request: EnhancedQuestionRequest, http_request: Request = None):
    """
    🔄 COMPATIBILITÉ - Redirige vers le nouveau système unifié
    
    Ancien endpoint "enhanced" qui utilisait de multiples systèmes contradictoires.
    Maintenant redirige vers le nouveau système intelligent unique.
    """
    logger.info("🔄 [Legacy Redirect] ask-enhanced → nouveau système unifié")
    return await ask_expert(request, http_request)

@router.post("/ask-enhanced-public", response_model=EnhancedExpertResponse)
async def ask_expert_enhanced_public_legacy(request: EnhancedQuestionRequest):
    """
    🔄 COMPATIBILITÉ - Version publique de l'ancien enhanced
    """
    logger.info("🔄 [Legacy Redirect] ask-enhanced-public → nouveau système unifié")
    return await ask_expert_public(request)

# =============================================================================
# ENDPOINTS UTILITAIRES
# =============================================================================

@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    📝 FEEDBACK UTILISATEUR - Collecte des retours
    
    Permet aux utilisateurs de donner leur avis sur les réponses
    """
    try:
        logger.info(f"📝 [Feedback] Reçu: {feedback.rating}/5 - {feedback.comment[:50] if feedback.comment else 'Sans commentaire'}")
        
        # Ici on pourrait sauvegarder en base de données
        # Pour l'instant, on logue simplement
        
        return {
            "status": "success",
            "message": "Merci pour votre retour !",
            "feedback_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [Feedback] Erreur: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la soumission du feedback")

@router.get("/topics")
async def get_available_topics():
    """
    📚 TOPICS DISPONIBLES - Liste des sujets que le système peut traiter
    """
    return {
        "topics": [
            {
                "category": "Performance",
                "subjects": ["Poids", "Croissance", "Gain de poids", "Standards de race"],
                "examples": [
                    "Quel est le poids normal d'un Ross 308 à 21 jours ?",
                    "Croissance normale pour Cobb 500 mâles ?"
                ]
            },
            {
                "category": "Santé",
                "subjects": ["Symptômes", "Maladies", "Prévention", "Traitement"],
                "examples": [
                    "Mes poules font de la diarrhée depuis 2 jours",
                    "Poulets apathiques et refus alimentaire"
                ]
            },
            {
                "category": "Alimentation",
                "subjects": ["Nutrition", "Aliments", "Besoins par âge", "Problèmes alimentaires"],
                "examples": [
                    "Quel aliment pour Ross 308 de 3 semaines ?",
                    "Besoins nutritionnels pondeuses 25 semaines"
                ]
            },
            {
                "category": "Élevage",
                "subjects": ["Conditions", "Température", "Densité", "Équipements"],
                "examples": [
                    "Température optimale poulets 15 jours",
                    "Densité recommandée Cobb 500 ?"
                ]
            }
        ],
        "supported_breeds": [
            "Ross 308", "Cobb 500", "Hubbard", "Arbor Acres",
            "ISA Brown", "Lohmann Brown", "Hy-Line", "Bovans"
        ],
        "supported_languages": ["fr", "en", "es"],
        "response_types": [
            "Réponse précise (données spécifiques)",
            "Réponse générale + offre de précision", 
            "Clarification ciblée (si vraiment nécessaire)"
        ]
    }

# =============================================================================
# ENDPOINTS DE MONITORING ET DEBUG
# =============================================================================

@router.get("/system-status")
async def get_system_status():
    """
    🔍 STATUT SYSTÈME - Informations sur le nouveau système unifié
    """
    try:
        stats = expert_service.get_system_stats()
        
        return {
            "system": "Expert System Unified v1.0",
            "architecture": "Entities → Classifier → Generator → Response",
            "status": "active",
            "components": {
                "entities_extractor": "✅ Active",
                "smart_classifier": "✅ Active", 
                "response_generator": "✅ Active",
                "expert_service": "✅ Active"
            },
            "legacy_systems": {
                "expert_legacy": "❌ Supprimé",
                "question_clarification_system": "❌ Supprimé",
                "expert_services_clarification": "❌ Supprimé",
                "multiple_contradictory_rules": "❌ Éliminés"
            },
            "performance": stats,
            "configuration": {
                "always_provide_useful_answer": INTELLIGENT_SYSTEM_CONFIG["behavior"].ALWAYS_PROVIDE_USEFUL_ANSWER,
                "precision_offers_enabled": INTELLIGENT_SYSTEM_CONFIG["behavior"].PRECISION_OFFERS_ENABLED,
                "clarification_only_if_needed": INTELLIGENT_SYSTEM_CONFIG["behavior"].CLARIFICATION_ONLY_IF_REALLY_NEEDED
            },
            "endpoints": {
                "main": "/api/v1/expert/ask",
                "public": "/api/v1/expert/ask-public", 
                "legacy_enhanced": "/api/v1/expert/ask-enhanced (→ redirected)",
                "legacy_enhanced_public": "/api/v1/expert/ask-enhanced-public (→ redirected)",
                "feedback": "/api/v1/expert/feedback",
                "topics": "/api/v1/expert/topics",
                "status": "/api/v1/expert/system-status"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [System Status] Erreur: {e}")
        return {
            "system": "Expert System Unified v1.0",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/reset-stats")
async def reset_system_stats():
    """
    🔄 RESET STATS - Remet à zéro les statistiques (pour debugging)
    """
    try:
        expert_service.reset_stats()
        return {
            "status": "success",
            "message": "Statistiques remises à zéro",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ [Reset Stats] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def _convert_processing_result_to_response(request: EnhancedQuestionRequest, 
                                         result: ProcessingResult) -> EnhancedExpertResponse:
    """
    Convertit le résultat du nouveau système vers le format de réponse attendu
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())
    language = getattr(request, 'language', 'fr')
    
    # Déterminer le mode basé sur le type de réponse
    mode_mapping = {
        "precise_answer": "intelligent_precise",
        "general_answer": "intelligent_general_with_offer",
        "general_with_offer": "intelligent_general_with_offer", 
        "needs_clarification": "intelligent_clarification",
        "clarification_performance": "intelligent_clarification_targeted",
        "clarification_health": "intelligent_clarification_health",
        "clarification_feeding": "intelligent_clarification_feeding",
        "error_fallback": "intelligent_fallback"
    }
    
    mode = mode_mapping.get(result.response_type, "intelligent_unified")
    
    # Construire la réponse
    response_data = {
        "question": request.text,
        "response": result.response,
        "conversation_id": conversation_id,
        "rag_used": False,  # Le nouveau système n'utilise plus RAG
        "timestamp": result.timestamp,
        "language": language,
        "response_time_ms": result.processing_time_ms,
        "mode": mode,
        "user": getattr(request, 'user_id', None),
        "logged": True,
        "validation_passed": result.success
    }
    
    # Informations de traitement pour debugging
    processing_info = {
        "entities_extracted": expert_service._entities_to_dict(result.entities),
        "response_type": result.response_type,
        "confidence": result.confidence,
        "processing_steps": [
            "entities_extraction_v1",
            "smart_classification_v1",
            "unified_response_generation_v1"
        ],
        "system_version": "unified_intelligent_v1.0.0"
    }
    
    # Ajouter les informations de processing
    response_data["processing_info"] = processing_info
    
    # Gestion des erreurs
    if not result.success:
        response_data["error_details"] = {
            "error": result.error,
            "fallback_used": True,
            "system": "unified_expert_service"
        }
    
    return EnhancedExpertResponse(**response_data)

# =============================================================================
# INITIALISATION ET LOGGING
# =============================================================================

logger.info("🚀" * 50)
logger.info("🚀 [EXPERT SYSTEM] NOUVEAU SYSTÈME UNIFIÉ ACTIVÉ!")
logger.info("🚀" * 50)
logger.info("")
logger.info("✅ [ARCHITECTURE SIMPLIFIÉE]:")
logger.info("   📥 Question → Entities Extractor")
logger.info("   🧠 Entities → Smart Classifier") 
logger.info("   🎨 Classification → Unified Response Generator")
logger.info("   📤 Response → User")
logger.info("")
logger.info("✅ [FINI LES PROBLÈMES]:")
logger.info("   ❌ Plus de conflits entre systèmes")
logger.info("   ❌ Plus de règles contradictoires") 
logger.info("   ❌ Plus d'import circulaires")
logger.info("   ❌ Plus de 50 fichiers à maintenir")
logger.info("")
logger.info("✅ [NOUVEAU COMPORTEMENT]:")
logger.info("   🎯 Toujours une réponse utile")
logger.info("   💡 Offres de précision intelligentes")
logger.info("   🔄 Clarification seulement si vraiment nécessaire")
logger.info("   ⚡ Performance optimisée")
logger.info("")
logger.info("🎯 [ENDPOINTS DISPONIBLES]:")
logger.info("   POST /api/v1/expert/ask (principal)")
logger.info("   POST /api/v1/expert/ask-public (public)")
logger.info("   POST /api/v1/expert/ask-enhanced (legacy → redirect)")
logger.info("   POST /api/v1/expert/ask-enhanced-public (legacy → redirect)")
logger.info("   POST /api/v1/expert/feedback")
logger.info("   GET  /api/v1/expert/topics")
logger.info("   GET  /api/v1/expert/system-status")
logger.info("")
logger.info("🎉 [RÉSULTAT]: Système simple, intelligent et maintenable!")
logger.info("🚀" * 50)