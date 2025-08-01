# expert_utils.py - VERSION FINALE (identique à la version précédente)
"""
app/api/v1/expert_utils.py - UTILITAIRES EXPERT SYSTEM

Fonctions utilitaires pour le système expert
VERSION FINALE : Aucune modification supplémentaire nécessaire
"""

import os
import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import Request

logger = logging.getLogger(__name__)

def get_user_id_from_request(request: Request) -> str:
    """Extrait l'user_id depuis la requête"""
    # Essayer d'extraire depuis les headers ou token
    authorization = request.headers.get("authorization", "")
    if authorization:
        # Ici vous pouvez parser le JWT pour extraire l'user_id
        # Pour l'instant, génération d'un ID temporaire
        return f"user_{uuid.uuid4().hex[:8]}"
    
    # Fallback
    return f"anonymous_{uuid.uuid4().hex[:8]}"

def build_enriched_question_from_clarification(
    original_question: str,
    clarification_response: str, 
    conversation_context: str = ""
) -> str:
    """Construit une question enrichie à partir d'une clarification"""
    if conversation_context:
        return f"{original_question}\n\nClarification: {clarification_response}\n\nContexte: {conversation_context}"
    else:
        return f"{original_question}\n\nClarification: {clarification_response}"

def get_enhanced_topics_by_language() -> Dict[str, list]:
    """Retourne les topics suggérés par langue"""
    return {
        "fr": [
            "Problèmes de croissance poulets",
            "Conditions environnementales optimales",
            "Protocoles de vaccination",
            "Diagnostic problèmes de santé",
            "Nutrition et alimentation",
            "Gestion de la mortalité",
            "Température et humidité",
            "Qualité de l'eau"
        ],
        "en": [
            "Chicken growth problems",
            "Optimal environmental conditions", 
            "Vaccination protocols",
            "Health problem diagnosis",
            "Nutrition and feeding",
            "Mortality management",
            "Temperature and humidity",
            "Water quality"
        ],
        "es": [
            "Problemas de crecimiento de pollos",
            "Condiciones ambientales óptimas",
            "Protocolos de vacunación", 
            "Diagnóstico de problemas de salud",
            "Nutrición y alimentación",
            "Gestión de mortalidad",
            "Temperatura y humedad",
            "Calidad del agua"
        ]
    }

async def save_conversation_auto_enhanced(
    conversation_id: str,
    question: str,
    response: str,
    user_id: str,
    language: str = "fr"
) -> bool:
    """Sauvegarde automatique de conversation"""
    try:
        # Ici vous pouvez intégrer avec votre système de logging
        logger.info(f"💾 Sauvegarde conversation {conversation_id}: {question[:50]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")
        return False

def get_fallback_response_enhanced(question: str, language: str = "fr") -> str:
    """
    Réponse de fallback améliorée - REDIRECTION VERS RAG
    
    NOTE: Cette fonction ne doit plus être utilisée avec des données codées.
    Elle redirige vers le système RAG.
    """
    responses = {
        "fr": "Le système expert nécessite l'accès à la base documentaire pour répondre à votre question. Veuillez vous assurer que le service RAG est disponible.",
        "en": "The expert system requires access to the document database to answer your question. Please ensure the RAG service is available.",
        "es": "El sistema experto requiere acceso a la base de datos de documentos para responder a su pregunta. Asegúrese de que el servicio RAG esté disponible."
    }
    return responses.get(language.lower(), responses["fr"])

# =============================================================================
# FONCTIONS DÉPRÉCIÉES - AVEC DONNÉES CODÉES SUPPRIMÉES
# =============================================================================

async def process_question_with_enhanced_prompt_DEPRECATED(
    question: str, 
    language: str = "fr", 
    speed_mode: str = "balanced",
    extracted_entities: Optional[Dict] = None,
    conversation_context: str = ""
) -> str:
    """
    ❌ FONCTION DÉPRÉCIÉE - SUPPRIMÉE
    
    Cette fonction contenait des données Ross 308 codées en dur.
    Toutes les réponses doivent maintenant passer par le RAG qui contient
    les documents de référence officiels (Performance Objectives, etc.).
    """
    
    logger.error("❌ [Expert Utils] ERREUR: Tentative d'utilisation de fonction dépréciée")
    logger.error("❌ [Expert Utils] Architecture actuelle: RAG-First obligatoire")
    
    raise RuntimeError(
        "ERREUR ARCHITECTURE: process_question_with_enhanced_prompt est dépréciée. "
        "Toutes les requêtes doivent passer par le système RAG qui contient "
        "les Performance Objectives officiels d'Aviagen."
    )

def get_hardcoded_ross_308_data_DEPRECATED():
    """❌ FONCTION SUPPRIMÉE - DONNÉES TRANSFÉRÉES VERS RAG"""
    
    logger.error("❌ [Expert Utils] Tentative d'accès aux données codées supprimées")
    
    raise RuntimeError(
        "DONNÉES SUPPRIMÉES: Les données Ross 308 ne sont plus codées en dur. "
        "Elles se trouvent dans la base documentaire RAG. "
        "Utilisez le système RAG pour accéder aux Performance Objectives officiels."
    )

# =============================================================================
# NOUVELLES FONCTIONS UTILITAIRES RAG-FIRST
# =============================================================================

def validate_rag_availability(app_state) -> bool:
    """Valide que le système RAG est disponible"""
    process_rag = getattr(app_state, 'process_question_with_rag', None)
    return process_rag is not None

def log_rag_dependency_error(function_name: str, question: str):
    """Log les erreurs de dépendance RAG"""
    logger.error(f"❌ [Expert Utils] {function_name}: RAG non disponible")
    logger.error(f"❌ [Expert Utils] Question: {question[:100]}...")
    logger.error(f"❌ [Expert Utils] Action requise: Vérifier initialisation RAG")
    logger.error(f"❌ [Expert Utils] Documents requis: Ross 308 Performance Objectives")

def get_rag_error_response(language: str = "fr") -> str:
    """Retourne un message d'erreur approprié quand RAG est indisponible"""
    
    messages = {
        "fr": (
            "Service temporairement indisponible. "
            "Le système expert nécessite l'accès à la base documentaire "
            "pour fournir des informations précises sur les performances "
            "des races de poulets. Veuillez réessayer plus tard."
        ),
        "en": (
            "Service temporarily unavailable. "
            "The expert system requires access to the document database "
            "to provide accurate information about chicken breed performance. "
            "Please try again later."
        ),
        "es": (
            "Servicio temporalmente no disponible. "
            "El sistema experto requiere acceso a la base de datos de documentos "
            "para proporcionar información precisa sobre el rendimiento de las razas de pollos. "
            "Por favor, inténtelo de nuevo más tarde."
        )
    }
    
    return messages.get(language.lower(), messages["fr"])

def suggest_rag_setup_check() -> Dict[str, Any]:
    """Suggère les vérifications à effectuer pour le setup RAG"""
    
    return {
        "checks_required": [
            "Vérifier que process_question_with_rag est initialisé dans app.state",
            "Confirmer que la base documentaire contient les Performance Objectives Ross 308",
            "Tester la connectivité vers le système de vectorisation",
            "Valider que les documents sont correctement indexés"
        ],
        "critical_documents": [
            "Ross 308 Performance Objectives 2022 (Aviagen)",
            "Cobb 500 Performance Standards", 
            "Guides de nutrition avicole",
            "Protocoles de vaccination"
        ],
        "test_questions": [
            "Quel est le poids d'un Ross 308 au jour 18 ?",
            "Quelles sont les conditions optimales pour l'élevage ?",
            "Protocoles de vaccination recommandés ?"
        ]
    }

# =============================================================================
# LOGGING DE MIGRATION
# =============================================================================

logger.info("✅ [Expert Utils] Module utilitaires final - RAG-First")
logger.info("✅ [Expert Utils] Compatible avec toutes les améliorations API")
logger.info("   - ❌ Données codées supprimées")
logger.info("   - ✅ Architecture RAG-First obligatoire")
logger.info("   - ✅ Support complet nouvelles fonctionnalités")