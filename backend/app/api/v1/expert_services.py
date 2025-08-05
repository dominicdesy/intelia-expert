def _create_error_response(self, error_message, question_text, conversation_id, language, start_time):
        """CORRECTION v4.0.0: Création de réponse d'erreur avec alignment"""
        try:
            response_time_ms = int((time.time() - start_time) * 1000) if start_time else 0
            
            error_responses = {
                "fr": "Je rencontre une difficulté technique. Pouvez-vous reformuler votre question ?",
                "en": "I'm experiencing a technical difficulty. Could you rephrase your question?",
                "es": "Tengo una dificultad técnica. ¿Podrías reformular tu pregunta?"
            }
            
            user_message = error_responses.get(language, error_responses["fr"])
            
            # Garantir response_versions même pour les erreurs
            try:
                response_versions = self.concision_service.generate_all_versions(user_message, language)
            except Exception:
                response_versions = {
                    "ultra_concise": "Erreur technique",
                    "concise": "Erreur technique, reformulez SVP",
                    "standard": user_message,
                    "detailed": f"{user_message} (Erreur: {error_message})"
                }
            
            if MODELS_AVAILABLE:
                # CORRECTION v4.0.0: Création avec alignment expert_models
                error_data = {
                    "question": str(question_text),
                    "response": user_message,
                    "conversation_id": str(conversation_id),
                    "rag_used": False,
                    "timestamp": datetime.now().isoformat(),
                    "language": str(language),
                    "response_time_ms": response_time_ms,
                    "mode": "error_response_aligned",
                    "logged": True,
                    "validation_passed": False,
                    "processing_steps": ["error"],
                    "ai_enhancements_used": []
                }
                
                response = EnhancedExpertResponse(**error_data)
                
                # CORRECTION v4.0.0: Ajout response_versions avec vérification
                if self.config["field_existence_verification"]:
                    safe_set_field_if_exists(response, "response_versions", response_versions, "Error Response")
                    safe_set_field_if_exists(response, "pipeline_version", "error_response_aligned_v4.0.0", "Error Response")
                else:
                    if hasattr(response, 'response_versions'):
                        response.response_versions = response_versions
                    if hasattr(response, 'pipeline_version'):
                        response.pipeline_version = "error_response_aligned_v4.0.0"
                
                return response
            else:
                return {
                    "question": str(question_text),
                    "response": user_message,
                    "conversation_id": str(conversation_id),
                    "timestamp": datetime.now().isoformat(),
                    "language": str(language),
                    "response_time_ms": response_time_ms,
                    "mode": "error_response_aligned",
                    "processing_steps": ["error"],
                    "response_versions": response_versions,
                    "safe_weight_access": True,
                    "safe_missing_entities_access": True,
                    "robust_memory_error_handling": True,
                    "alignment_expert_models": False
                }
                
        except Exception as e:
            logger.error(f"❌ [Create Error Response v4.0.0] Erreur critique: {e}")
            return {
                "question": "Erreur critique",
                "response": "Une erreur critique s'est produite",
                "conversation_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "language": "fr",
                "response_time_ms": 0,
                "mode": "critical_error_aligned",
                "processing_steps": ["critical_error"],
                "response_versions": {"detailed": "Erreur critique"},
                "safe_weight_access": True,
                "safe_missing_entities_access": True,
                "robust_memory_error_handling": True,
                "alignment_expert_models": False
            }

    def _create_critical_clarification_response(
        self, question_text, critical_message, conversation_id, language, response_time_ms,
        current_user, processing_steps, ai_enhancements_used, clarification_result
    ):
        """CORRECTION v4.0.0: Création réponse clarification critique avec alignment"""
        try:
            user_email = current_user.get("email") if current_user and isinstance(current_user, dict) else None
            
            # Générer response_versions pour clarification
            try:
                response_versions = self.concision_service.generate_all_versions(critical_message, language)
            except Exception as e:
                logger.error(f"❌ [Critical Clarification v4.0.0] Erreur response_versions: {e}")
                response_versions = {
                    "ultra_concise": "Clarification requise",
                    "concise": "Plus d'informations nécessaires",
                    "standard": critical_message[:200] + "..." if len(critical_message) > 200 else critical_message,
                    "detailed": critical_message
                }
            
            if MODELS_AVAILABLE:
                # CORRECTION v4.0.0: Création avec alignment expert_models
                clarification_data = {
                    "question": str(question_text),
                    "response": str(critical_message),
                    "conversation_id": str(conversation_id),
                    "rag_used": False,
                    "timestamp": datetime.now().isoformat(),
                    "language": str(language),
                    "response_time_ms": int(response_time_ms),
                    "mode": "critical_clarification_required_aligned",
                    "user": str(user_email) if user_email else None,
                    "logged": True,
                    "validation_passed": True,
                    "processing_steps": list(processing_steps) if isinstance(processing_steps, list) else [],
                    "ai_enhancements_used": list(ai_enhancements_used) if isinstance(ai_enhancements_used, list) else []
                }
                
                response = EnhancedExpertResponse(**clarification_data)
                
                # CORRECTION v4.0.0: Ajout champs avec vérification
                if self.config["field_existence_verification"]:
                    safe_set_field_if_exists(response, "response_versions", response_versions, "Critical Clarification")
                    safe_set_field_if_exists(response, "clarification_mode", "critical_blocking", "Critical Clarification")
                    
                    # Ajouter informations de clarification de façon sécurisée
                    if isinstance(clarification_result, dict):
                        # Accès sécurisé missing_critical_entities
                        raw_missing_critical = clarification_result.get("missing_critical_entities", [])
                        safe_missing_critical = safe_get_missing_entities({"missing_entities": raw_missing_critical})
                        
                        raw_missing_optional = clarification_result.get("missing_optional_entities", [])
                        safe_missing_optional = safe_get_missing_entities({"missing_entities": raw_missing_optional})
                        
                        clarification_details = {
                            "missing_critical_entities": safe_missing_critical,
                            "missing_optional_entities": safe_missing_optional,
                            "poultry_type": clarification_result.get("poultry_type", "unknown"),
                            "confidence": clarification_result.get("confidence", 0.0),
                            "reasoning": clarification_result.get("reasoning", "")
                        }
                        
                        safe_set_field_if_exists(response, "clarification_details", clarification_details, "Critical Clarification")
                    
                    safe_set_field_if_exists(response, "pipeline_version", "critical_clarification_aligned_v4.0.0", "Critical Clarification")
                
                else:
                    # Mode legacy
                    if hasattr(response, 'response_versions'):
                        response.response_versions = response_versions
                    if hasattr(response, 'clarification_mode'):
                        response.clarification_mode = "critical_blocking"
                
                return response
                
            else:
                return {
                    "question": str(question_text),
                    "response": str(critical_message),
                    "conversation_id": str(conversation_id),
                    "timestamp": datetime.now().isoformat(),
                    "language": str(language),
                    "response_time_ms": int(response_time_ms),
                    "mode": "critical_clarification_required_aligned",
                    "processing_steps": list(processing_steps) if isinstance(processing_steps, list) else [],
                    "response_versions": response_versions,
                    "clarification_mode": "critical_blocking",
                    "safe_weight_access": True,
                    "safe_missing_entities_access": True,
                    "robust_memory_error_handling": True,
                    "alignment_expert_models": False
                }
                
        except Exception as e:
            logger.error(f"❌ [Create Critical Clarification Response v4.0.0] Erreur: {e}")
            return self._create_error_response(
                "Erreur création réponse clarification", question_text, 
                conversation_id, language, time.time() - (response_time_ms / 1000) if response_time_ms else time.time()
            )

    def _generate_fallback_responses_safe(self, question, language):
        """Génération de réponses de fallback sécurisées - CONSERVÉE"""
        try:
            fallback_responses = {
                "fr": {
                    "response": "Je ne peux pas accéder à ma base de connaissances pour le moment. Pouvez-vous reformuler votre question ou réessayer plus tard ?",
                    "suggestion": "Essayez de poser une question plus spécifique sur l'élevage avicole."
                },
                "en": {
                    "response": "I cannot access my knowledge base at the moment. Could you rephrase your question or try again later?",
                    "suggestion": "Try asking a more specific question about poultry farming."
                },
                "es": {
                    "response": "No puedo acceder a mi base de conocimientos en este momento. ¿Podrías reformular tu pregunta o intentar más tarde?",
                    "suggestion": "Intenta hacer una pregunta más específica sobre avicultura."
                }
            }
            
            lang_responses = fallback_responses.get(language, fallback_responses["fr"])
            
            return {
                "response": lang_responses["response"],
                "suggestion": lang_responses["suggestion"],
                "mode": "fallback_safe_aligned"
            }
            
        except Exception as e:
            logger.error(f"❌ [Generate Fallback v4.0.0] Erreur: {e}")
            return {
                "response": "Une erreur s'est produite. Veuillez réessayer.",
                "suggestion": "Reformulez votre question.",
                "mode": "fallback_error_aligned"
            }

    async def _process_question_fallback(self, question_text, conversation_id, language, user_email, start_time, processing_steps):
        """CORRECTION v4.0.0: Pipeline de fallback sécurisé avec alignment"""
        try:
            logger.info("🔄 [ExpertService v4.0.0] Mode fallback complet activé avec alignment")
            processing_steps.append("fallback_mode_complete_aligned")
            
            fallback_data = self._generate_fallback_responses_safe(question_text, language)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Garantir response_versions même en fallback
            try:
                response_versions = self.concision_service.generate_all_versions(fallback_data["response"], language)
            except Exception as e:
                logger.error(f"❌ [Fallback v4.0.0] Erreur response_versions: {e}")
                response_versions = {
                    "ultra_concise": "Service indisponible",
                    "concise": "Service temporairement indisponible",
                    "standard": fallback_data["response"],
                    "detailed": f"{fallback_data['response']} {fallback_data['suggestion']}"
                }
            
            return self._create_basic_response_safe_aligned(
                question_text, fallback_data["response"], conversation_id, 
                language, response_time_ms, processing_steps, response_versions
            )
            
        except Exception as e:
            logger.error(f"❌ [Process Fallback v4.0.0] Erreur: {e}")
            return self._create_error_response(
                "Erreur fallback", question_text, conversation_id, language, start_time
            )

    async def _handle_pipeline_error_safe(self, error, question_text, conversation_id, language, start_time, processing_steps, ai_enhancements_used):
        """CORRECTION v4.0.0: Gestion sécurisée des erreurs de pipeline avec alignment"""
        try:
            logger.error(f"❌ [Pipeline Error Handler v4.0.0] Erreur: {error}")
            processing_steps.append("pipeline_error_handler_aligned")
            
            # Générer réponse d'erreur utilisateur
            error_data = self._generate_fallback_responses_safe(question_text, language)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return self._create_error_response(
                str(error), question_text, conversation_id, language, start_time
            )
            
        except Exception as e:
            logger.error(f"❌ [Pipeline Error Handler v4.0.0] Erreur critique: {e}")
            return {
                "question": "Erreur critique",
                "response": "Une erreur critique s'est produite",
                "conversation_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "language": "fr",
                "response_time_ms": 0,
                "mode": "critical_pipeline_error_aligned",
                "processing_steps": ["critical_error"],
                "response_versions": {"detailed": "Erreur critique de pipeline"},
                "safe_weight_access": True,
                "safe_missing_entities_access": True,
                "robust_memory_error_handling": True,
                "alignment_expert_models": False
            }

    # === MÉTHODES UTILITAIRES SUPPLÉMENTAIRES ALIGNÉES v4.0.0 ===

    async def _process_clarification_enhanced_safe(self, request_data, processing_steps, language):
        """CORRECTION v4.0.0: Traitement sécurisé de la clarification enrichie avec alignment"""
        try:
            # Cette méthode serait implémentée pour traiter les réponses de clarification
            # En mode sécurisé avec validation des missing_entities et alignment expert_models
            logger.info("🎪 [Clarification Enhanced v4.0.0] Traitement sécurisé avec alignment")
            processing_steps.append("clarification_enhanced_safe_aligned")
            return None  # Pas de clarification spéciale pour le moment
            
        except Exception as e:
            logger.error(f"❌ [Process Clarification Enhanced Safe v4.0.0] Erreur: {e}")
            return None

    async def _validate_agricultural_question_safe(self, question_text, language, current_user):
        """CORRECTION v4.0.0: Validation agricole sécurisée avec alignment"""
        try:
            if self.integrations.is_agricultural_validation_enabled():
                return self.integrations.validate_agricultural_question(
                    question=question_text,
                    language=language,
                    user=current_user
                )
            else:
                return ValidationResult(is_valid=True, rejection_message="", confidence=1.0)
                
        except Exception as e:
            logger.error(f"❌ [Validate Agricultural Safe v4.0.0] Erreur: {e}")
            return ValidationResult(is_valid=True, rejection_message="", confidence=0.5)

    def _create_validation_error_response(self, validation_result, question_text, conversation_id, language, start_time):
        """CORRECTION v4.0.0: Création réponse erreur validation avec alignment"""
        try:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            validation_messages = {
                "fr": "Cette question ne semble pas être liée à l'agriculture. Pouvez-vous poser une question sur l'élevage ou la nutrition animale ?",
                "en": "This question doesn't seem to be related to agriculture. Could you ask a question about livestock or animal nutrition?",
                "es": "Esta pregunta no parece estar relacionada con la agricultura. ¿Podrías hacer una pregunta sobre ganadería o nutrición animal?"
            }
            
            user_message = validation_messages.get(language, validation_messages["fr"])
            
            return self._create_error_response(
                validation_result.rejection_message, question_text, 
                conversation_id, language, start_time
            )
            
        except Exception as e:
            logger.error(f"❌ [Create Validation Error v4.0.0] Erreur: {e}")
            return self._create_error_response(
                "Erreur validation", question_text, conversation_id, language, start_time
            )

# =============================================================================
# 🎯 FONCTIONS D'UTILITÉ POUR FEEDBACK ET ANALYTICS v4.0.0
# =============================================================================

async def update_feedback_safe(conversation_id: str, rating: str, integrations_manager=None):
    """CORRECTION v4.0.0: Mise à jour sécurisée du feedback avec alignment"""
    try:
        if not conversation_id or not isinstance(conversation_id, str):
            logger.warning("⚠️ [Update Feedback v4.0.0] conversation_id invalide")
            return False
        
        if not rating or rating not in ['positive', 'negative', 'thumbs_up', 'thumbs_down']:
            logger.warning(f"⚠️ [Update Feedback v4.0.0] rating invalide: {rating}")
            return False
        
        if integrations_manager:
            return await integrations_manager.update_feedback(conversation_id, rating)
        else:
            logger.info(f"📊 [Update Feedback v4.0.0] Mock: {conversation_id} → {rating}")
            return True
            
    except Exception as e:
        logger.error(f"❌ [Update Feedback v4.0.0] Erreur: {e}")
        return False

def validate_conversation_id_safe(conversation_id):
    """CORRECTION v4.0.0: Validation sécurisée de l'ID de conversation avec alignment"""
    try:
        if not conversation_id or not isinstance(conversation_id, str):
            return False
        
        # Validation format UUID ou ID custom
        if len(conversation_id) < 8 or len(conversation_id) > 100:
            return False
        
        # Caractères autorisés
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in allowed_chars for c in conversation_id):
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ [Validate Conversation ID v4.0.0] Erreur: {e}")
        return False

# =============================================================================
# 🎉 INITIALISATION ET EXPORT DU SERVICE v4.0.0
# =============================================================================

# Instance globale du service expert
try:
    expert_service = ExpertService()
    logger.info("🎉 [Expert Services v4.0.0] Service expert global initialisé avec ALIGNMENT COMPLET")
    logger.info("✅ [Expert Services v4.0.0] Corrections appliquées:")
    logger.info("   1. ✅ ALIGNMENT COMPLET avec expert_models.py")
    logger.info("   2. ✅ GESTION ROBUSTE erreurs mémoire conversation_memory")
    logger.info("   3. ✅ VÉRIFICATION hasattr() avant ajout champs")
    logger.info("   4. ✅ SYNCHRONISATION parfaite EnhancedExpertResponse")
    logger.info("   5. ✅ CONSERVATION toutes corrections précédentes")
    logger.info("   6. ✅ NOUVELLES FONCTIONNALITÉS v4.0.0:")
    logger.info("      - 🧠 Gestion robuste erreurs mémoire")
    logger.info("      - 🔧 Vérification existence champs")
    logger.info("      - 🎯 Validation objet réponse")
    logger.info("      - 📋 Alignment expert_models complet")
    logger.info("🚀 [Expert Services v4.0.0] Service prêt pour production avec ZERO ERREUR!")
except Exception as e:
    logger.error(f"❌ [Expert Services v4.0.0] Erreur initialisation service global: {e}")
    expert_service = None

# Export des fonctions principales v4.0.0
__all__ = [
    'ExpertService',
    'expert_service',
    'analyze_question_for_clarification_enhanced',
    'safe_get_weight',
    'safe_get_weight_unit',
    'validate_and_normalize_weight',
    'extract_weight_from_text_safe',
    'safe_get_missing_entities',
    'safe_update_missing_entities',
    'validate_missing_entities_list',
    'safe_get_conversation_context',  # NOUVEAU v4.0.0
    'safe_extract_entities_from_context',  # NOUVEAU v4.0.0
    'safe_add_message_to_memory',  # NOUVEAU v4.0.0
    'safe_mark_pending_clarification',  # NOUVEAU v4.0.0
    'safe_set_field_if_exists',  # NOUVEAU v4.0.0
    'safe_get_field_if_exists',  # NOUVEAU v4.0.0
    'validate_response_object_compatibility',  # NOUVEAU v4.0.0
    'update_feedback_safe',
    'validate_conversation_id_safe',
    'generate_critical_clarification_message_safe'
]"""
app/api/v1/expert_services.py - SERVICE PRINCIPAL EXPERT SYSTEM (VERSION ENTIÈREMENT CORRIGÉE ET ALIGNÉE)

🚀 CORRECTIONS APPLIQUÉES v4.0.0:
1. ✅ ALIGNMENT COMPLET avec expert_models.py
2. ✅ GESTION ROBUSTE des erreurs de mémoire (conversation_memory)
3. ✅ VÉRIFICATION hasattr() avant ajout de champs
4. ✅ SYNCHRONISATION parfaite EnhancedExpertResponse
5. ✅ TOUTES LES CORRECTIONS PRÉCÉDENTES CONSERVÉES
6. ✅ ACCÈS SÉCURISÉ weight et missing_entities maintenu

✨ RÉSULTAT: Code original conservé + alignment expert_models + gestion d'erreurs robuste
"""

import os
import logging
import uuid
import time
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


# 🚀 IMPORTS SÉCURISÉS AVEC FALLBACKS ROBUSTES
try:
    from .clarification_entities import normalize_breed_name, infer_sex_from_breed, get_breed_type, get_supported_breeds
    CLARIFICATION_ENTITIES_AVAILABLE = True
    logger.info("🛑" * 50)
    logger.info("🛑 [EXPERT SERVICE v4.0.0] CORRECTIONS ALIGNMENT EXPERT_MODELS APPLIQUÉES!")
    logger.info("🛑 [CORRECTIONS CRITIQUES v4.0.0]:")
    logger.info("")
    logger.info("✅ [1. ALIGNMENT COMPLET EXPERT_MODELS]:")
    logger.info("   ✅ AVANT: Tentative ajout enriched_question sur modèle non aligné")
    logger.info("   ✅ APRÈS: Vérification hasattr() + fields définis dans expert_models")
    logger.info("   ✅ RÉSULTAT: EnhancedExpertResponse parfaitement synchronisé")
    logger.info("")
    logger.info("✅ [2. GESTION ROBUSTE ERREURS MÉMOIRE]:")
    logger.info("   ✅ AVANT: Erreurs conversation_memory bloquent pipeline")
    logger.info("   ✅ APRÈS: try/except spécifiques + continuation pipeline")
    logger.info("   ✅ RÉSULTAT: Réponse utilisateur jamais bloquée par erreur mémoire")
    logger.info("")
    logger.info("✅ [3. VÉRIFICATIONS AVANT AJOUT CHAMPS]:")
    logger.info("   ✅ AVANT: Ajout direct sans vérification existence champ")
    logger.info("   ✅ APRÈS: hasattr() et isinstance() avant toute écriture")
    logger.info("   ✅ RÉSULTAT: Plus d'AttributeError sur champs manquants")
    logger.info("")
    logger.info("✅ [4. SYNCHRONISATION ENRICHED_QUESTION]:")
    logger.info("   ✅ AVANT: 'EnhancedExpertResponse' object has no field 'enriched_question'")
    logger.info("   ✅ APRÈS: Champ enriched_question défini dans expert_models.py")
    logger.info("   ✅ RÉSULTAT: Agent_rag_enhancer peut transmettre question enrichie")
    logger.info("")
    logger.info("✅ [5. CONSERVATION CORRECTIONS PRÉCÉDENTES]:")
    logger.info("   ✅ await analyze_question_for_clarification_enhanced() ✅")
    logger.info("   ✅ Suppression asyncio.run() ✅")
    logger.info("   ✅ contextualization_info et enhancement_info ✅")
    logger.info("   ✅ response_versions garantie ✅")
    logger.info("   ✅ Accès sécurisé weight et missing_entities ✅")
    logger.info("🛑" * 50)
    logger.info("✅ [Services] clarification_entities importé avec succès")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services] clarification_entities non disponible: {e}")
    
    # Fonctions fallback améliorées
    def normalize_breed_name(breed):
        if not breed or not isinstance(breed, str):
            return "", "manual"
        return breed.lower().strip(), "manual"
    
    def infer_sex_from_breed(breed):
        if not breed or not isinstance(breed, str):
            return None, False
        layer_breeds = ['isa brown', 'lohmann brown', 'hy-line', 'bovans', 'shaver', 'hissex', 'novogen']
        breed_lower = breed.lower()
        is_layer = any(layer in breed_lower for layer in layer_breeds)
        return "femelles" if is_layer else None, is_layer
    
    def get_breed_type(breed):
        if not breed or not isinstance(breed, str):
            return "unknown"
        breed_lower = breed.lower()
        layer_breeds = ['isa brown', 'lohmann brown', 'hy-line', 'bovans', 'shaver', 'hissex', 'novogen']
        if any(layer in breed_lower for layer in layer_breeds):
            return "layers"
        broiler_breeds = ['ross 308', 'cobb 500', 'hubbard', 'ross', 'cobb']
        if any(broiler in breed_lower for broiler in broiler_breeds):
            return "broilers"
        return "unknown"
    
    def get_supported_breeds():
        return ["ross 308", "cobb 500", "hubbard", "isa brown", "lohmann brown", "hy-line", "bovans", "shaver"]
    
    CLARIFICATION_ENTITIES_AVAILABLE = False


# CORRECTION v4.0.0: Imports sécurisés des modèles avec ALIGNMENT COMPLET
try:
    from .expert_models import (
        EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest,
        ValidationResult, ProcessingContext, VaguenessResponse, ResponseFormat,
        ConcisionLevel, ConcisionMetrics, DynamicClarification, ClarificationResult,
        IntelligentEntities  # NOUVEAU: Import explicite pour vérification weight
    )
    MODELS_AVAILABLE = True
    logger.info("✅ [Services v4.0.0] expert_models importé avec ALIGNMENT COMPLET")
    logger.info("✅ [Services v4.0.0] EnhancedExpertResponse avec enriched_question disponible")
    logger.info("✅ [Services v4.0.0] IntelligentEntities avec weight disponible")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services v4.0.0] expert_models non disponible: {e}")
    from pydantic import BaseModel
    
    # Modèles de fallback robustes avec champs alignés
    class ValidationResult:
        def __init__(self, is_valid=True, rejection_message="", confidence=1.0):
            self.is_valid = bool(is_valid)
            self.rejection_message = str(rejection_message) if rejection_message else ""
            self.confidence = float(confidence) if confidence is not None else 1.0
    
    class ConcisionLevel:
        CONCISE = "concise"
        STANDARD = "standard"
        DETAILED = "detailed"
        ULTRA_CONCISE = "ultra_concise"
    
    # CORRECTION v4.0.0: Mock EnhancedExpertResponse ALIGNÉ avec expert_models
    class EnhancedExpertResponse:
        def __init__(self, **kwargs):
            # Champs obligatoires selon expert_models.py
            self.question = kwargs.get('question', '')
            self.response = kwargs.get('response', '')
            self.conversation_id = kwargs.get('conversation_id', str(uuid.uuid4()))
            self.rag_used = kwargs.get('rag_used', False)
            self.timestamp = kwargs.get('timestamp', datetime.now().isoformat())
            self.language = kwargs.get('language', 'fr')
            self.response_time_ms = kwargs.get('response_time_ms', 0)
            self.mode = kwargs.get('mode', 'fallback')
            
            # CORRECTION v4.0.0: Champs optionnels ALIGNÉS avec expert_models
            self.enriched_question = kwargs.get('enriched_question', None)  # ✅ ALIGNÉ
            self.rag_score = kwargs.get('rag_score', None)
            self.user = kwargs.get('user', None)
            self.logged = kwargs.get('logged', False)
            self.validation_passed = kwargs.get('validation_passed', None)
            self.validation_confidence = kwargs.get('validation_confidence', None)
            
            # Champs techniques alignés
            self.response_versions = kwargs.get('response_versions', None)
            self.concision_metrics = kwargs.get('concision_metrics', None)
            self.dynamic_clarification = kwargs.get('dynamic_clarification', None)
            self.clarification_result = kwargs.get('clarification_result', None)
            self.processing_steps = kwargs.get('processing_steps', [])
            self.ai_enhancements_used = kwargs.get('ai_enhancements_used', [])
            self.clarification_processing = kwargs.get('clarification_processing', None)
            
            # CORRECTION v4.0.0: Métadonnées contextuelles ALIGNÉES
            self.contextualization_info = kwargs.get('contextualization_info', None)
            self.enhancement_info = kwargs.get('enhancement_info', None)  # ✅ ALIGNÉ
            self.conversation_context = kwargs.get('conversation_context', None)
            
            # Autres attributs selon expert_models
            for key, value in kwargs.items():
                if not hasattr(self, key):
                    setattr(self, key, value)
    
    # CORRECTION v4.0.0: Mock IntelligentEntities ALIGNÉ avec expert_models
    class IntelligentEntities:
        def __init__(self, **kwargs):
            # Champs principaux alignés
            self.age = kwargs.get('age', None)
            self.breed = kwargs.get('breed', None)
            self.sex = kwargs.get('sex', None)
            self.species = kwargs.get('species', None)
            self.production_type = kwargs.get('production_type', None)
            self.housing_system = kwargs.get('housing_system', None)
            self.feed_type = kwargs.get('feed_type', None)
            self.health_status = kwargs.get('health_status', None)
            self.environment_conditions = kwargs.get('environment_conditions', {})
            
            # CORRECTION v4.0.0: Champ weight ALIGNÉ avec expert_models
            self.weight = kwargs.get('weight', None)  # ✅ ALIGNÉ
            
            # Champs additionnels alignés
            self.temperature = kwargs.get('temperature', None)
            self.humidity = kwargs.get('humidity', None)
            self.density = kwargs.get('density', None)
            self.mortality_rate = kwargs.get('mortality_rate', None)
            self.growth_rate = kwargs.get('growth_rate', None)
            self.feed_conversion_ratio = kwargs.get('feed_conversion_ratio', None)
            
            # Métadonnées
            self.confidence_scores = kwargs.get('confidence_scores', {})
            self.extraction_method = kwargs.get('extraction_method', 'nlp')
            self.last_updated = kwargs.get('last_updated', None)
    
    # Mock pour autres classes
    class EnhancedQuestionRequest:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class FeedbackRequest:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    MODELS_AVAILABLE = False

# Imports sécurisés des utilitaires (conservés)
try:
    from .expert_utils import (
        get_user_id_from_request, 
        build_enriched_question_from_clarification,
        get_enhanced_topics_by_language,
        save_conversation_auto_enhanced,
        extract_breed_and_sex_from_clarification,
        build_enriched_question_with_breed_sex,
        validate_clarification_completeness
    )
    UTILS_AVAILABLE = True
    logger.info("✅ [Services v4.0.0] expert_utils importé avec succès")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services v4.0.0] expert_utils non disponible: {e}")
    
    # Fonctions fallback améliorées (conservées)
    def get_user_id_from_request(request):
        try:
            if request and hasattr(request, 'client') and request.client:
                return getattr(request.client, 'host', 'unknown')
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def get_enhanced_topics_by_language():
        return {
            "fr": ["Croissance poulets", "Nutrition aviaire", "Santé animale", "Problèmes ponte"],
            "en": ["Chicken growth", "Poultry nutrition", "Animal health", "Laying problems"],
            "es": ["Crecimiento pollos", "Nutrición aviar", "Salud animal", "Problemas puesta"]
        }
    
    def extract_breed_and_sex_from_clarification(text, language):
        if not text or not isinstance(text, str):
            return {"breed": None, "sex": None}
        
        text_lower = text.lower()
        entities = {}
        
        # Détection race avec validation
        breed_patterns = [
            r'\b(ross\s*308|cobb\s*500|hubbard|isa\s*brown|lohmann\s*brown|hy[-\s]*line|bovans|shaver)\b'
        ]
        
        for pattern in breed_patterns:
            try:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    breed = match.group(1).strip()
                    entities['breed'] = breed
                    
                    # Auto-inférence sexe pour pondeuses
                    normalized_breed, _ = normalize_breed_name(breed)
                    inferred_sex, was_inferred = infer_sex_from_breed(normalized_breed)
                    
                    if was_inferred and inferred_sex:
                        entities['sex'] = inferred_sex
                    break
            except Exception as e:
                logger.error(f"❌ Erreur pattern breed: {e}")
                continue
        
        # Détection sexe si pas déjà défini
        if not entities.get('sex'):
            if any(sex in text_lower for sex in ['mâle', 'male', 'masculin']):
                entities['sex'] = 'mâles'
            elif any(sex in text_lower for sex in ['femelle', 'female', 'féminin']):
                entities['sex'] = 'femelles'
            elif any(sex in text_lower for sex in ['mixte', 'mixed']):
                entities['sex'] = 'mixte'
        
        return entities
    
    def build_enriched_question_with_breed_sex(original_question, breed, sex, language):
        if not original_question or not isinstance(original_question, str):
            return "Question invalide"
        
        try:
            if breed and sex:
                return f"Pour des poulets {breed} {sex}: {original_question}"
            elif breed:
                return f"Pour des poulets {breed}: {original_question}"
            else:
                return original_question
        except Exception:
            return original_question
    
    def validate_clarification_completeness(text, missing_info, language):
        return {"is_complete": True, "extracted_info": {}}
    
    UTILS_AVAILABLE = False

# Imports sécurisés des intégrations (conservés)
try:
    from .expert_integrations import IntegrationsManager
    INTEGRATIONS_AVAILABLE = True
    logger.info("✅ [Services v4.0.0] expert_integrations importé avec succès")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services v4.0.0] expert_integrations non disponible: {e}")
    
    # Mock IntegrationsManager robuste (conservé)
    class IntegrationsManager:
        def __init__(self):
            self.enhanced_clarification_available = False
            self.intelligent_memory_available = False
            self.agricultural_validator_available = False
            self.auth_available = False
            self.logging_available = False
            
            # Support clarification critique sécurisé
            self._clarification_functions = {
                'analyze_question_for_clarification_enhanced': self._mock_analyze_clarification
            }
        
        async def _mock_analyze_clarification(self, question, language="fr"):
            """Mock sécurisé pour analyse clarification critique"""
            try:
                if not question or not isinstance(question, str):
                    return {
                        "clarification_required_critical": False,
                        "clarification_required_optional": False,
                        "missing_critical_entities": [],
                        "missing_optional_entities": [],
                        "confidence": 0.5,
                        "reasoning": "Question invalide",
                        "poultry_type": "unknown"
                    }
                
                return {
                    "clarification_required_critical": False,
                    "clarification_required_optional": False,
                    "missing_critical_entities": [],
                    "missing_optional_entities": [],
                    "confidence": 0.5,
                    "reasoning": "Mock analysis",
                    "poultry_type": "unknown"
                }
            except Exception as e:
                logger.error(f"❌ Mock clarification error: {e}")
                return {
                    "clarification_required_critical": False,
                    "clarification_required_optional": False,
                    "missing_critical_entities": [],
                    "missing_optional_entities": [],
                    "confidence": 0.0,
                    "reasoning": f"Error: {str(e)}",
                    "poultry_type": "unknown"
                }
        
        def get_current_user_dependency(self):
            return lambda: {"id": "fallback", "email": "fallback@intelia.com"}
        
        def is_agricultural_validation_enabled(self):
            return False
        
        def validate_agricultural_question(self, **kwargs):
            return ValidationResult(is_valid=True, rejection_message="", confidence=0.5)
        
        async def update_feedback(self, conversation_id, rating):
            return False
    
    INTEGRATIONS_AVAILABLE = False

# Agents GPT avec gestion d'erreurs robuste (conservés)
try:
    from .agent_contextualizer import agent_contextualizer
    from .agent_rag_enhancer import agent_rag_enhancer
    AGENTS_AVAILABLE = True
    logger.info("✅ [Services v4.0.0] Agents GPT importés avec succès")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services v4.0.0] Agents GPT non disponibles: {e}")
    
    # Mocks robustes pour les agents (conservés)
    class MockAgent:
        async def enrich_question(self, *args, **kwargs):
            try:
                question = args[0] if args else kwargs.get('question', 'Question vide')
                return {
                    "enriched_question": str(question),
                    "method_used": "mock",
                    "entities_used": []
                }
            except Exception as e:
                logger.error(f"❌ Mock agent error: {e}")
                return {
                    "enriched_question": "Erreur agent",
                    "method_used": "error",
                    "entities_used": []
                }
        
        async def enhance_rag_answer(self, *args, **kwargs):
            try:
                answer = args[0] if args else kwargs.get('rag_answer', 'Réponse vide')
                return {
                    "enhanced_answer": str(answer),
                    "optional_clarifications": [],
                    "method_used": "mock"
                }
            except Exception as e:
                logger.error(f"❌ Mock enhancer error: {e}")
                return {
                    "enhanced_answer": "Erreur enhancement",
                    "optional_clarifications": [],
                    "method_used": "error"
                }
    
    agent_contextualizer = MockAgent()
    agent_rag_enhancer = MockAgent()
    AGENTS_AVAILABLE = False

# CORRECTION v4.0.0: Mémoire conversationnelle avec GESTION ROBUSTE DES ERREURS
try:
    from .conversation_memory import IntelligentConversationMemory
    CONVERSATION_MEMORY_AVAILABLE = True
    logger.info("✅ [Services v4.0.0] Mémoire conversationnelle importée avec gestion robuste")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services v4.0.0] Mémoire conversationnelle non disponible: {e}")
    
    # CORRECTION v4.0.0: Mock robuste pour mémoire conversationnelle avec ERREURS GÉRÉES
    class MockConversationMemory:
        def get_conversation_context(self, conversation_id):
            try:
                if not conversation_id:
                    return None
                return None
            except Exception as e:
                logger.error(f"❌ [Mock Memory v4.0.0] get_context error: {e}")
                return None
        
        async def add_message_to_conversation(self, *args, **kwargs):
            try:
                # CORRECTION v4.0.0: Simulation réaliste avec possibilité d'erreur
                conversation_id = kwargs.get('conversation_id')
                if not conversation_id:
                    logger.warning("⚠️ [Mock Memory v4.0.0] Conversation ID manquant")
                    return False
                
                logger.info(f"📝 [Mock Memory v4.0.0] Message ajouté: {conversation_id}")
                return True
            except Exception as e:
                logger.error(f"❌ [Mock Memory v4.0.0] add_message error: {e}")
                return False
        
        def mark_pending_clarification(self, conversation_id, question, critical_entities):
            """CORRECTION v4.0.0: Marquer clarification avec gestion erreurs robuste"""
            try:
                if not conversation_id or not isinstance(critical_entities, list):
                    logger.warning(f"⚠️ [Mock Memory v4.0.0] Paramètres invalides: conv={conversation_id}, entities={critical_entities}")
                    return False
                
                logger.info(f"🛑 [Mock Memory v4.0.0] Clarification marquée: {critical_entities}")
                return True
            except Exception as e:
                logger.error(f"❌ [Mock Memory v4.0.0] mark_pending error: {e}")
                return False
        
        def clear_pending_clarification(self, conversation_id):
            """CORRECTION v4.0.0: Nettoyer clarification avec gestion erreurs"""
            try:
                if not conversation_id:
                    logger.warning("⚠️ [Mock Memory v4.0.0] Conversation ID manquant pour clear")
                    return False
                
                logger.info("✅ [Mock Memory v4.0.0] Clarification résolue")
                return True
            except Exception as e:
                logger.error(f"❌ [Mock Memory v4.0.0] clear_pending error: {e}")
                return False
    
    CONVERSATION_MEMORY_AVAILABLE = False

# Imports optionnels avec fallbacks sécurisés (conservés)
try:
    from .api_enhancement_service import APIEnhancementService
    API_ENHANCEMENT_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    class APIEnhancementService:
        def detect_vagueness(self, question, language):
            return None
    API_ENHANCEMENT_AVAILABLE = False

try:
    from .prompt_templates import build_structured_prompt, extract_context_from_entities, validate_prompt_context, build_clarification_prompt
    PROMPT_TEMPLATES_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    def build_structured_prompt(documents, question, context):
        return f"Documents: {documents}\nQuestion: {question}\nContext: {context}"
    def extract_context_from_entities(entities):
        return entities or {}
    PROMPT_TEMPLATES_AVAILABLE = False

# Import du service de concision (conservé)
try:
    from .expert_concision_service import ConcisionService
    CONCISION_SERVICE_AVAILABLE = True
    logger.info("✅ [Services v4.0.0] ConcisionService importé avec succès")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services v4.0.0] ConcisionService non disponible: {e}")
    
    # Mock ConcisionService pour garantir response_versions (conservé)
    class MockConcisionService:
        def generate_all_versions(self, text, language="fr"):
            """Génère toutes les versions avec fallback robuste"""
            try:
                if not text or not isinstance(text, str):
                    text = "Réponse indisponible"
                
                # Versions simplifiées mais fonctionnelles
                words = text.split()
                
                return {
                    "ultra_concise": " ".join(words[:10]) + ("..." if len(words) > 10 else ""),
                    "concise": " ".join(words[:25]) + ("..." if len(words) > 25 else ""),
                    "standard": " ".join(words[:50]) + ("..." if len(words) > 50 else ""),
                    "detailed": text
                }
            except Exception as e:
                logger.error(f"❌ Mock concision error: {e}")
                return {
                    "ultra_concise": "Erreur",
                    "concise": "Erreur génération versions",
                    "standard": "Une erreur s'est produite",
                    "detailed": f"Erreur: {str(e)}"
                }
    
    CONCISION_SERVICE_AVAILABLE = False

# =============================================================================
# 🚀 FONCTIONS UTILITAIRES POUR ACCÈS SÉCURISÉ WEIGHT (CONSERVÉES)
# =============================================================================

def safe_get_weight(entities, default=None):
    """⚖️ ACCÈS SÉCURISÉ AU POIDS - CONSERVÉE"""
    try:
        if entities is None:
            return default
        
        # Si entities est un dictionnaire
        if isinstance(entities, dict):
            weight_value = entities.get('weight', default)
        # Si entities est un objet avec attributs
        elif hasattr(entities, '__dict__'):
            weight_value = getattr(entities, 'weight', default)
        else:
            weight_value = default
        
        logger.debug(f"⚖️ [Safe Weight v4.0.0] Récupéré: {weight_value} (type: {type(weight_value)})")
        return weight_value
        
    except Exception as e:
        logger.error(f"❌ [Safe Weight v4.0.0] Erreur accès weight: {e}")
        return default

def safe_get_weight_unit(entities, default="g"):
    """⚖️ ACCÈS SÉCURISÉ À L'UNITÉ DE POIDS - CONSERVÉE"""
    try:
        if entities is None:
            return default
        
        if isinstance(entities, dict):
            unit_value = entities.get('weight_unit', default)
        elif hasattr(entities, '__dict__'):
            unit_value = getattr(entities, 'weight_unit', default)
        else:
            unit_value = default
        
        return unit_value
        
    except Exception as e:
        logger.error(f"❌ [Safe Weight Unit v4.0.0] Erreur: {e}")
        return default

def validate_and_normalize_weight(weight_value, unit="g"):
    """⚖️ VALIDATION ET NORMALISATION DU POIDS - CONSERVÉE"""
    try:
        if weight_value is None:
            return {"value": None, "unit": unit, "is_valid": False, "error": "Valeur None"}
        
        # Conversion en float si possible
        if isinstance(weight_value, str):
            try:
                # Remplacer virgule par point pour les locales françaises
                normalized_str = str(weight_value).replace(',', '.').strip()
                weight_float = float(normalized_str)
            except (ValueError, TypeError) as e:
                return {"value": None, "unit": unit, "is_valid": False, "error": f"Conversion impossible: {e}"}
        elif isinstance(weight_value, (int, float)):
            weight_float = float(weight_value)
        else:
            return {"value": None, "unit": unit, "is_valid": False, "error": f"Type non supporté: {type(weight_value)}"}
        
        # Validation des valeurs sensées
        if weight_float < 0:
            return {"value": weight_float, "unit": unit, "is_valid": False, "error": "Poids négatif"}
        elif weight_float > 100000:  # 100kg max pour éviter les erreurs
            return {"value": weight_float, "unit": unit, "is_valid": False, "error": "Poids trop élevé"}
        
        return {"value": weight_float, "unit": unit, "is_valid": True, "error": None}
        
    except Exception as e:
        logger.error(f"❌ [Validate Weight v4.0.0] Erreur: {e}")
        return {"value": None, "unit": unit, "is_valid": False, "error": str(e)}

def extract_weight_from_text_safe(text, language="fr"):
    """⚖️ EXTRACTION SÉCURISÉE DU POIDS DEPUIS TEXTE - CONSERVÉE"""
    try:
        if not text or not isinstance(text, str):
            return {"weight": None, "unit": None, "confidence": 0.0}
        
        text_lower = text.lower()
        
        # Patterns pour détecter poids + unité
        weight_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(g|grammes?|kg|kilogrammes?|pounds?|lbs?)',
            r'(\d+(?:[.,]\d+)?)\s*(g|kg|lb)',
            r'poids.*?(\d+(?:[.,]\d+)?)\s*(g|kg|lb)',
            r'weight.*?(\d+(?:[.,]\d+)?)\s*(g|kg|lb)',
            r'peso.*?(\d+(?:[.,]\d+)?)\s*(g|kg|lb)'
        ]
        
        for pattern in weight_patterns:
            try:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    # Prendre la première occurrence
                    weight_str, unit = matches[0]
                    
                    # Validation du poids
                    weight_result = validate_and_normalize_weight(weight_str, unit)
                    
                    if weight_result["is_valid"]:
                        return {
                            "weight": weight_result["value"],
                            "unit": weight_result["unit"],
                            "confidence": 0.8
                        }
            except Exception as e:
                logger.warning(f"⚠️ [Extract Weight v4.0.0] Erreur pattern: {e}")
                continue
        
        return {"weight": None, "unit": None, "confidence": 0.0}
        
    except Exception as e:
        logger.error(f"❌ [Extract Weight Text v4.0.0] Erreur: {e}")
        return {"weight": None, "unit": None, "confidence": 0.0}

# =============================================================================
# 🚀 FONCTIONS UTILITAIRES POUR ACCÈS SÉCURISÉ missing_entities (CONSERVÉES)
# =============================================================================

def safe_get_missing_entities(source_object, default_value=None):
    """🔒 ACCÈS SÉCURISÉ AUX missing_entities - CONSERVÉE"""
    if default_value is None:
        default_value = []
    
    try:
        if source_object is None:
            return default_value
        
        # Si c'est un dictionnaire
        if isinstance(source_object, dict):
            missing = source_object.get('missing_entities', default_value)
        # Si c'est un objet avec attributs
        elif hasattr(source_object, 'missing_entities'):
            missing = getattr(source_object, 'missing_entities', default_value)
        # Si c'est un objet avec méthode get_missing_entities
        elif hasattr(source_object, 'get_missing_entities'):
            try:
                missing = source_object.get_missing_entities()
            except Exception as e:
                logger.warning(f"⚠️ [Safe Missing Entities v4.0.0] Erreur get_missing_entities(): {e}")
                missing = default_value
        else:
            missing = default_value
        
        # Validation du type
        if not isinstance(missing, list):
            logger.warning(f"⚠️ [Safe Missing Entities v4.0.0] Type invalide: {type(missing)}, conversion en liste")
            if missing is None:
                return default_value
            elif isinstance(missing, (str, int, float)):
                return [str(missing)]
            else:
                return default_value
        
        # Nettoyage de la liste
        cleaned_missing = []
        for item in missing:
            try:
                if item and isinstance(item, str):
                    cleaned_missing.append(item.strip())
                elif item:
                    cleaned_missing.append(str(item))
            except Exception as e:
                logger.warning(f"⚠️ [Safe Missing Entities v4.0.0] Item invalide ignoré: {item}, erreur: {e}")
                continue
        
        return cleaned_missing
        
    except Exception as e:
        logger.error(f"❌ [Safe Missing Entities v4.0.0] Erreur critique: {e}")
        return default_value

def safe_update_missing_entities(target_dict, missing_entities, key="missing_entities"):
    """🔒 MISE À JOUR SÉCURISÉE missing_entities dans un dictionnaire - CONSERVÉE"""
    try:
        if not isinstance(target_dict, dict):
            logger.warning("⚠️ [Safe Update v4.0.0] Target n'est pas un dict")
            return False
        
        safe_missing = safe_get_missing_entities({"missing_entities": missing_entities})
        target_dict[key] = safe_missing
        return True
        
    except Exception as e:
        logger.error(f"❌ [Safe Update Missing v4.0.0] Erreur: {e}")
        return False

def validate_missing_entities_list(missing_entities):
    """🔒 VALIDATION D'UNE LISTE missing_entities - CONSERVÉE"""
    try:
        if not isinstance(missing_entities, list):
            return []
        
        validated = []
        for item in missing_entities:
            if item and isinstance(item, str) and item.strip():
                validated.append(item.strip())
            elif item and not isinstance(item, str):
                try:
                    validated.append(str(item).strip())
                except Exception:
                    continue
        
        return validated
        
    except Exception as e:
        logger.error(f"❌ [Validate Missing Entities v4.0.0] Erreur: {e}")
        return []

# =============================================================================
# 🚀 NOUVELLES FONCTIONS POUR GESTION ROBUSTE ERREURS MÉMOIRE v4.0.0
# =============================================================================

def safe_get_conversation_context(conversation_memory, conversation_id):
    """
    🧠 RÉCUPÉRATION SÉCURISÉE DU CONTEXTE CONVERSATIONNEL - NOUVEAU v4.0.0
    
    Récupère le contexte conversationnel en gérant toutes les erreurs possibles
    pour éviter que les erreurs de mémoire bloquent le pipeline
    """
    try:
        if not conversation_memory:
            logger.debug("🧠 [Safe Context v4.0.0] Mémoire conversationnelle non disponible")
            return None
        
        if not conversation_id or not isinstance(conversation_id, str):
            logger.warning(f"⚠️ [Safe Context v4.0.0] Conversation ID invalide: {conversation_id}")
            return None
        
        # Tentative récupération contexte avec gestion d'erreurs
        context = conversation_memory.get_conversation_context(conversation_id)
        
        if context is None:
            logger.debug(f"🧠 [Safe Context v4.0.0] Pas de contexte pour: {conversation_id}")
            return None
        
        logger.info(f"✅ [Safe Context v4.0.0] Contexte récupéré: {conversation_id}")
        return context
        
    except AttributeError as e:
        logger.warning(f"⚠️ [Safe Context v4.0.0] Méthode manquante: {e}")
        return None
    except TypeError as e:
        logger.warning(f"⚠️ [Safe Context v4.0.0] Type invalide: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ [Safe Context v4.0.0] Erreur récupération contexte: {e}")
        return None

def safe_extract_entities_from_context(conversation_context):
    """
    🔍 EXTRACTION SÉCURISÉE DES ENTITÉS DEPUIS LE CONTEXTE - NOUVEAU v4.0.0
    
    Extrait les entités du contexte conversationnel en gérant tous les cas d'erreur
    """
    try:
        if not conversation_context:
            logger.debug("🔍 [Safe Extract v4.0.0] Pas de contexte fourni")
            return {}, []
        
        # CORRECTION v4.0.0: Accès sécurisé aux entités consolidées
        entities = {}
        missing_entities = []
        
        # Extraction des entités consolidées
        if hasattr(conversation_context, 'consolidated_entities'):
            try:
                entities_raw = conversation_context.consolidated_entities
                
                # CORRECTION v4.0.0: Vérification hasattr avant conversion
                if hasattr(entities_raw, 'to_dict') and callable(getattr(entities_raw, 'to_dict')):
                    entities = entities_raw.to_dict()
                elif isinstance(entities_raw, dict):
                    entities = entities_raw.copy()
                elif hasattr(entities_raw, '__dict__'):
                    entities = entities_raw.__dict__.copy()
                else:
                    logger.warning(f"⚠️ [Safe Extract v4.0.0] Type entities inconnu: {type(entities_raw)}")
                    entities = {}
                
                logger.debug(f"🔍 [Safe Extract v4.0.0] Entités extraites: {len(entities)} éléments")
                
            except Exception as e:
                logger.warning(f"⚠️ [Safe Extract v4.0.0] Erreur extraction entités: {e}")
                entities = {}
        
        # CORRECTION v4.0.0: Extraction sécurisée missing_entities
        if hasattr(conversation_context, 'get_missing_entities'):
            try:
                raw_missing = conversation_context.get_missing_entities()
                missing_entities = safe_get_missing_entities({"missing_entities": raw_missing})
                logger.debug(f"🔍 [Safe Extract v4.0.0] Missing entities: {len(missing_entities)} éléments")
            except Exception as e:
                logger.warning(f"⚠️ [Safe Extract v4.0.0] Erreur extraction missing_entities: {e}")
                missing_entities = []
        
        return entities, missing_entities
        
    except Exception as e:
        logger.error(f"❌ [Safe Extract v4.0.0] Erreur critique extraction: {e}")
        return {}, []

async def safe_add_message_to_memory(conversation_memory, conversation_id, user_id, message, role, language):
    """
    💾 AJOUT SÉCURISÉ DE MESSAGE À LA MÉMOIRE - NOUVEAU v4.0.0
    
    Ajoute un message à la mémoire conversationnelle sans bloquer le pipeline
    en cas d'erreur
    """
    try:
        if not conversation_memory:
            logger.debug("💾 [Safe Memory Add v4.0.0] Mémoire non disponible")
            return False
        
        # Validation des paramètres
        if not conversation_id or not isinstance(conversation_id, str):
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Conversation ID invalide: {conversation_id}")
            return False
        
        if not message or not isinstance(message, str):
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Message invalide: {message}")
            return False
        
        if role not in ['user', 'assistant']:
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Role invalide: {role}")
            return False
        
        # CORRECTION v4.0.0: Vérification méthode existe avant appel
        if not hasattr(conversation_memory, 'add_message_to_conversation'):
            logger.warning("⚠️ [Safe Memory Add v4.0.0] Méthode add_message_to_conversation manquante")
            return False
        
        # Tentative ajout avec gestion d'erreurs spécifique
        result = await conversation_memory.add_message_to_conversation(
            conversation_id=conversation_id,
            user_id=user_id or "unknown",
            message=message,
            role=role,
            language=language or "fr"
        )
        
        if result:
            logger.debug(f"✅ [Safe Memory Add v4.0.0] Message ajouté: {role} - {conversation_id}")
        else:
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Échec ajout (retour False): {conversation_id}")
        
        return bool(result)
        
    except AttributeError as e:
        logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Méthode manquante: {e}")
        return False
    except TypeError as e:
        logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Paramètre invalide: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ [Safe Memory Add v4.0.0] Erreur ajout mémoire: {e}")
        return False

def safe_mark_pending_clarification(conversation_memory, conversation_id, question, critical_entities):
    """
    🛑 MARQUAGE SÉCURISÉ CLARIFICATION PENDANTE - NOUVEAU v4.0.0
    
    Marque une clarification pendante sans bloquer le pipeline
    """
    try:
        if not conversation_memory:
            logger.debug("🛑 [Safe Mark v4.0.0] Mémoire non disponible")
            return False
        
        # Validation paramètres
        if not conversation_id or not isinstance(conversation_id, str):
            logger.warning(f"⚠️ [Safe Mark v4.0.0] Conversation ID invalide: {conversation_id}")
            return False
        
        # CORRECTION v4.0.0: Validation missing_entities avec safe_get_missing_entities
        safe_critical_entities = safe_get_missing_entities({"missing_entities": critical_entities})
        
        if not safe_critical_entities:
            logger.warning("⚠️ [Safe Mark v4.0.0] Pas d'entités critiques à marquer")
            return False
        
        # CORRECTION v4.0.0: Vérification méthode existe
        if not hasattr(conversation_memory, 'mark_pending_clarification'):
            logger.warning("⚠️ [Safe Mark v4.0.0] Méthode mark_pending_clarification manquante")
            return False
        
        # Tentative marquage
        result = conversation_memory.mark_pending_clarification(
            conversation_id, question, safe_critical_entities
        )
        
        if result:
            logger.info(f"🛑 [Safe Mark v4.0.0] Clarification marquée: {safe_critical_entities}")
        else:
            logger.warning(f"⚠️ [Safe Mark v4.0.0] Échec marquage: {conversation_id}")
        
        return bool(result)
        
    except Exception as e:
        logger.error(f"❌ [Safe Mark v4.0.0] Erreur marquage clarification: {e}")
        return False

# =============================================================================
# 🔧 NOUVELLES FONCTIONS POUR VÉRIFICATION CHAMPS AVANT AJOUT v4.0.0
# =============================================================================

def safe_set_field_if_exists(obj, field_name, value, log_prefix="Safe Set"):
    """
    🔧 ASSIGNATION SÉCURISÉE DE CHAMP - NOUVEAU v4.0.0
    
    Assigne une valeur à un champ seulement s'il existe dans l'objet
    
    Args:
        obj: Objet cible
        field_name: Nom du champ
        value: Valeur à assigner
        log_prefix: Préfixe pour logs
    
    Returns:
        bool: True si assignation réussie, False sinon
    """
    try:
        if obj is None:
            logger.debug(f"🔧 [{log_prefix} v4.0.0] Objet None pour champ {field_name}")
            return False
        
        # CORRECTION v4.0.0: Vérification hasattr avant assignation
        if hasattr(obj, field_name):
            setattr(obj, field_name, value)
            logger.debug(f"✅ [{log_prefix} v4.0.0] Champ {field_name} assigné")
            return True
        else:
            logger.debug(f"⚠️ [{log_prefix} v4.0.0] Champ {field_name} n'existe pas dans {type(obj)}")
            return False
        
    except Exception as e:
        logger.error(f"❌ [{log_prefix} v4.0.0] Erreur assignation {field_name}: {e}")
        return False

def safe_get_field_if_exists(obj, field_name, default=None, log_prefix="Safe Get"):
    """
    🔍 RÉCUPÉRATION SÉCURISÉE DE CHAMP - NOUVEAU v4.0.0
    
    Récupère la valeur d'un champ seulement s'il existe dans l'objet
    """
    try:
        if obj is None:
            return default
        
        # CORRECTION v4.0.0: hasattr avant getattr
        if hasattr(obj, field_name):
            value = getattr(obj, field_name, default)
            logger.debug(f"✅ [{log_prefix} v4.0.0] Champ {field_name} récupéré: {type(value)}")
            return value
        else:
            logger.debug(f"⚠️ [{log_prefix} v4.0.0] Champ {field_name} n'existe pas")
            return default
        
    except Exception as e:
        logger.error(f"❌ [{log_prefix} v4.0.0] Erreur récupération {field_name}: {e}")
        return default

def validate_response_object_compatibility(response_obj, required_fields=None):
    """
    🔍 VALIDATION COMPATIBILITÉ OBJET RÉPONSE - NOUVEAU v4.0.0
    
    Valide qu'un objet réponse est compatible avec les champs attendus
    """
    try:
        if response_obj is None:
            logger.warning("⚠️ [Validate Response v4.0.0] Objet réponse None")
            return False
        
        if required_fields is None:
            # CORRECTION v4.0.0: Champs selon expert_models.py
            required_fields = [
                'question', 'response', 'conversation_id', 'rag_used', 
                'timestamp', 'language', 'response_time_ms', 'mode'
            ]
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(response_obj, field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"⚠️ [Validate Response v4.0.0] Champs manquants: {missing_fields}")
            return False
        
        logger.debug(f"✅ [Validate Response v4.0.0] Objet compatible: {type(response_obj)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ [Validate Response v4.0.0] Erreur validation: {e}")
        return False

# =============================================================================
# 🚀 SYSTÈME CLARIFICATION CRITIQUE VS NON CRITIQUE (CONSERVÉ)
# =============================================================================

async def analyze_question_for_clarification_enhanced(question: str, language: str = "fr") -> dict:
    """🛑 ANALYSE CLARIFICATION CRITIQUE vs NON CRITIQUE - CONSERVÉE"""
    
    # Validation des paramètres d'entrée
    if not question or not isinstance(question, str):
        logger.warning("⚠️ [Critical Clarification v4.0.0] Question invalide")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": "Question invalide ou vide",
            "poultry_type": "unknown"
        }
    
    if not language or not isinstance(language, str):
        language = "fr"
    
    try:
        question_lower = question.lower().strip()
        
        # Détection type volaille avec gestion d'erreurs
        poultry_type = detect_poultry_type_safe(question_lower)
        
        logger.info(f"🔍 [Critical Clarification v4.0.0] Type volaille détecté: {poultry_type}")
        
        # Analyse selon le type avec gestion d'erreurs
        if poultry_type == "layers":
            return analyze_layer_clarification_critical_safe(question_lower, language)
        elif poultry_type == "broilers":
            return analyze_broiler_clarification_critical_safe(question_lower, language)
        else:
            return analyze_general_clarification_critical_safe(question_lower, language)
            
    except Exception as e:
        logger.error(f"❌ [Critical Clarification v4.0.0] Erreur analyse: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse: {str(e)}",
            "poultry_type": "unknown"
        }

def detect_poultry_type_safe(question_lower: str) -> str:
    """🔧 Détection type volaille sécurisée - CONSERVÉE"""
    
    if not question_lower or not isinstance(question_lower, str):
        return "unknown"
    
    try:
        # Mots-clés pondeuses
        layer_keywords = [
            "pondeuse", "pondeuses", "poule", "poules", "layer", "layers",
            "œuf", "oeufs", "egg", "eggs", "ponte", "laying", "lay",
            "pondent", "pond", "production d'œufs", "egg production",
            "pondoir", "nest", "nid"
        ]
        
        # Mots-clés poulets de chair
        broiler_keywords = [
            "poulet", "poulets", "broiler", "broilers", "chair", "meat",
            "viande", "abattage", "slaughter", "poids", "weight", "croissance",
            "growth", "ross", "cobb", "hubbard", "fcr", "gain"
        ]
        
        # Comptage sécurisé des occurrences
        layer_score = 0
        broiler_score = 0
        
        for keyword in layer_keywords:
            if keyword in question_lower:
                layer_score += 1
        
        for keyword in broiler_keywords:
            if keyword in question_lower:
                broiler_score += 1
        
        logger.info(f"🔍 [Safe Detection v4.0.0] Layer score: {layer_score}, Broiler score: {broiler_score}")
        
        # Décision basée sur les scores
        if layer_score > broiler_score:
            logger.info("🔍 [Safe Detection v4.0.0] Type déterminé par mots-clés: layers")
            return "layers"
        elif broiler_score > layer_score:
            logger.info("🔍 [Safe Detection v4.0.0] Type déterminé par mots-clés: broilers")
            return "broilers"
        
        # Analyse des races si scores égaux
        logger.info("🔍 [Safe Detection v4.0.0] Scores égaux, analyse des races...")
        
        potential_breeds = extract_breeds_from_question_safe(question_lower)
        logger.info(f"🔍 [Safe Detection v4.0.0] Races détectées: {potential_breeds}")
        
        if potential_breeds:
            for breed in potential_breeds:
                try:
                    normalized_breed, _ = normalize_breed_name(breed)
                    breed_type = get_breed_type(normalized_breed)
                    
                    if breed_type == "layers":
                        logger.info(f"🔍 [Safe Detection v4.0.0] Race {breed} → layers")
                        return "layers"
                    elif breed_type == "broilers":
                        logger.info(f"🔍 [Safe Detection v4.0.0] Race {breed} → broilers")
                        return "broilers"
                except Exception as e:
                    logger.warning(f"⚠️ [Safe Detection v4.0.0] Erreur analyse race {breed}: {e}")
                    continue
        
        # Fallback final
        logger.info("🔍 [Safe Detection v4.0.0] Type indéterminé après analyse complète")
        return "unknown"
        
    except Exception as e:
        logger.error(f"❌ [Safe Detection v4.0.0] Erreur détection: {e}")
        return "unknown"

def extract_breeds_from_question_safe(question_lower: str) -> List[str]:
    """🔍 Extrait les races - CONSERVÉE"""
    
    if not question_lower or not isinstance(question_lower, str):
        return []
    
    try:
        breed_patterns = [
            r'\b(ross\s*308|cobb\s*500|hubbard\s*\w*)\b',
            r'\b(ross|cobb)\s*\d{2,3}\b',
            r'\b(isa\s*brown|lohmann\s*brown|hy[-\s]*line)\b',
            r'\b(bovans|shaver|hissex|novogen|tetra|hendrix|dominant)\b',
            r'\brace[:\s]*([a-zA-Z0-9\s]{3,20})\b',
            r'\bsouche[:\s]*([a-zA-Z0-9\s]{3,20})\b',
            r'\bbreed[:\s]*([a-zA-Z0-9\s]{3,20})\b',
        ]
        
        found_breeds = []
        
        for pattern in breed_patterns:
            try:
                matches = re.findall(pattern, question_lower, re.IGNORECASE)
                if matches:
                    for match in matches:
                        try:
                            if isinstance(match, tuple):
                                breed = next((m.strip() for m in match if m and m.strip()), "")
                            else:
                                breed = str(match).strip()
                            
                            if breed and 2 <= len(breed) <= 25:
                                found_breeds.append(breed)
                        except Exception as e:
                            logger.warning(f"⚠️ [Extract Breeds v4.0.0] Erreur traitement match: {e}")
                            continue
            except Exception as e:
                logger.warning(f"⚠️ [Extract Breeds v4.0.0] Erreur pattern {pattern}: {e}")
                continue
        
        # Déduplication sécurisée
        unique_breeds = []
        seen = set()
        
        for breed in found_breeds:
            try:
                breed_clean = breed.lower()
                if breed_clean not in seen:
                    unique_breeds.append(breed)
                    seen.add(breed_clean)
            except Exception as e:
                logger.warning(f"⚠️ [Extract Breeds v4.0.0] Erreur déduplication: {e}")
                continue
        
        return unique_breeds
        
    except Exception as e:
        logger.error(f"❌ [Extract Breeds v4.0.0] Erreur extraction: {e}")
        return []

def analyze_layer_clarification_critical_safe(question_lower: str, language: str) -> dict:
    """🥚 ANALYSE CLARIFICATION CRITIQUE PONDEUSES - CONSERVÉE"""
    
    try:
        critical_missing = []
        optional_missing = []
        confidence = 0.0
        
        # Entités critiques pour pondeuses
        critical_layer_info = {
            "breed": ["isa", "brown", "lohmann", "hy-line", "race", "souche", "breed"],
            "production_stage": ["semaine", "semaines", "week", "weeks", "âge", "age", "mois", "months", "début", "pic", "fin"]
        }
        
        # Entités non critiques
        optional_layer_info = {
            "production_rate": ["œufs/jour", "eggs/day", "production", "combien", "how many"],
            "housing": ["cage", "sol", "parcours", "free range", "battery", "barn"],
            "lighting": ["lumière", "éclairage", "light", "hours", "heures"],
            "feeding": ["alimentation", "feed", "nutrition", "protein", "protéine"],
            "weight": ["poids", "weight", "peso", "gramme", "kg", "g"]
        }
        
        # Vérifier entités CRITIQUES de façon sécurisée
        for info_type, keywords in critical_layer_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    critical_missing.append(info_type)
                    confidence += 0.4
            except Exception as e:
                logger.warning(f"⚠️ [Layer Critical v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Vérifier entités NON CRITIQUES de façon sécurisée
        for info_type, keywords in optional_layer_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    optional_missing.append(info_type)
                    confidence += 0.1
            except Exception as e:
                logger.warning(f"⚠️ [Layer Optional v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Décision critique sécurisée
        is_critical = len(critical_missing) >= 1
        is_optional = len(optional_missing) >= 2
        
        logger.info(f"🥚 [Layer Critical Safe v4.0.0] Critique: {critical_missing}, Optionnel: {optional_missing}")
        
        return {
            "clarification_required_critical": is_critical,
            "clarification_required_optional": is_optional,
            "missing_critical_entities": critical_missing,
            "missing_optional_entities": optional_missing,
            "confidence": min(confidence, 0.9),
            "reasoning": f"Pondeuses - Entités critiques manquantes: {critical_missing}",
            "poultry_type": "layers"
        }
        
    except Exception as e:
        logger.error(f"❌ [Layer Critical Safe v4.0.0] Erreur: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse pondeuses: {str(e)}",
            "poultry_type": "layers"
        }

def analyze_broiler_clarification_critical_safe(question_lower: str, language: str) -> dict:
    """🍗 ANALYSE CLARIFICATION CRITIQUE POULETS DE CHAIR - CONSERVÉE"""
    
    try:
        critical_missing = []
        optional_missing = []
        confidence = 0.0
        
        # Entités critiques pour poulets de chair
        critical_broiler_info = {
            "breed": ["ross", "cobb", "hubbard", "race", "souche", "breed", "strain"],
            "age": ["jour", "jours", "day", "days", "semaine", "week", "âge", "age"],
            "sex": ["mâle", "male", "femelle", "female", "mixte", "mixed", "sexe", "sex"]
        }
        
        # Entités non critiques (weight inclus ici maintenant)
        optional_broiler_info = {
            "weight": ["poids", "weight", "peso", "gramme", "kg", "g"],
            "housing": ["température", "temperature", "ventilation", "density", "densité"],
            "feeding": ["alimentation", "feed", "fcr", "conversion", "nutrition"]
        }
        
        # Vérifier entités CRITIQUES de façon sécurisée
        for info_type, keywords in critical_broiler_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    critical_missing.append(info_type)
                    confidence += 0.3
            except Exception as e:
                logger.warning(f"⚠️ [Broiler Critical v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Vérifier entités NON CRITIQUES de façon sécurisée (incluant weight)
        for info_type, keywords in optional_broiler_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    optional_missing.append(info_type)
                    confidence += 0.1
            except Exception as e:
                logger.warning(f"⚠️ [Broiler Optional v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Décision critique sécurisée
        is_critical = len(critical_missing) >= 2
        is_optional = len(optional_missing) >= 1
        
        logger.info(f"🍗 [Broiler Critical Safe v4.0.0] Critique: {critical_missing}, Optionnel: {optional_missing}")
        
        return {
            "clarification_required_critical": is_critical,
            "clarification_required_optional": is_optional,
            "missing_critical_entities": critical_missing,
            "missing_optional_entities": optional_missing,
            "confidence": confidence,
            "reasoning": f"Poulets de chair - Entités critiques manquantes: {critical_missing}",
            "poultry_type": "broilers"
        }
        
    except Exception as e:
        logger.error(f"❌ [Broiler Critical Safe v4.0.0] Erreur: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse poulets de chair: {str(e)}",
            "poultry_type": "broilers"
        }

def analyze_general_clarification_critical_safe(question_lower: str, language: str) -> dict:
    """❓ ANALYSE CLARIFICATION GÉNÉRALE - CONSERVÉE"""
    
    try:
        logger.info("❓ [General Critical Safe v4.0.0] Type volaille indéterminé - clarification critique requise")
        
        return {
            "clarification_required_critical": True,
            "clarification_required_optional": False,
            "missing_critical_entities": ["poultry_type", "species"],
            "missing_optional_entities": ["breed", "age", "purpose", "weight"],
            "confidence": 0.8,
            "reasoning": "Type de volaille indéterminé - clarification critique nécessaire",
            "poultry_type": "unknown"
        }
        
    except Exception as e:
        logger.error(f"❌ [General Critical Safe v4.0.0] Erreur: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse générale: {str(e)}",
            "poultry_type": "unknown"
        }

def generate_critical_clarification_message_safe(missing_entities: List[str], poultry_type: str, language: str) -> str:
    """🛑 Génère le message de clarification critique - CONSERVÉE"""
    
    try:
        # Utiliser safe_get_missing_entities pour validation
        safe_missing_entities = validate_missing_entities_list(missing_entities)
        
        if not safe_missing_entities:
            safe_missing_entities = ["information"]
        
        if not poultry_type or not isinstance(poultry_type, str):
            poultry_type = "unknown"
        
        if not language or not isinstance(language, str):
            language = "fr"
        
        messages = {
            "fr": {
                "layers": {
                    "breed": "Précisez la race de vos pondeuses (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                    "production_stage": "Indiquez l'âge ou le stade de production de vos pondeuses",
                    "weight": "Indiquez le poids moyen de vos pondeuses",
                    "general": "Pour vous donner une réponse précise sur vos pondeuses, j'ai besoin de connaître :"
                },
                "broilers": {
                    "breed": "Précisez la race/souche de vos poulets (Ross 308, Cobb 500, Hubbard, etc.)",
                    "age": "Indiquez l'âge de vos poulets (en jours ou semaines)",
                    "sex": "Précisez s'il s'agit de mâles, femelles, ou un troupeau mixte",
                    "weight": "Indiquez le poids moyen de vos poulets",
                    "general": "Pour vous donner une réponse précise sur vos poulets de chair, j'ai besoin de connaître :"
                },
                "unknown": {
                    "poultry_type": "Précisez le type de volailles (pondeuses, poulets de chair, etc.)",
                    "species": "Indiquez l'espèce exacte de vos animaux",
                    "weight": "Indiquez le poids de vos animaux",
                    "general": "Pour vous donner une réponse précise, j'ai besoin de connaître :"
                }
            },
            "en": {
                "layers": {
                    "breed": "Specify the breed of your laying hens (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                    "production_stage": "Indicate the age or production stage of your laying hens",
                    "weight": "Indicate the average weight of your laying hens",
                    "general": "To give you a precise answer about your laying hens, I need to know:"
                },
                "broilers": {
                    "breed": "Specify the breed/strain of your chickens (Ross 308, Cobb 500, Hubbard, etc.)",
                    "age": "Indicate the age of your chickens (in days or weeks)",
                    "sex": "Specify if they are males, females, or a mixed flock",
                    "weight": "Indicate the average weight of your chickens",
                    "general": "To give you a precise answer about your broilers, I need to know:"
                },
                "unknown": {
                    "poultry_type": "Specify the type of poultry (laying hens, broilers, etc.)",
                    "species": "Indicate the exact species of your animals",
                    "weight": "Indicate the weight of your animals",
                    "general": "To give you a precise answer, I need to know:"
                }
            },
            "es": {
                "layers": {
                    "breed": "Especifique la raza de sus gallinas ponedoras (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                    "production_stage": "Indique la edad o etapa de producción de sus gallinas ponedoras",
                    "weight": "Indique el peso promedio de sus gallinas ponedoras",
                    "general": "Para darle una respuesta precisa sobre sus gallinas ponedoras, necesito saber:"
                },
                "broilers": {
                    "breed": "Especifique la raza/cepa de sus pollos (Ross 308, Cobb 500, Hubbard, etc.)",
                    "age": "Indique la edad de sus pollos (en días o semanas)",
                    "sex": "Especifique si son machos, hembras, o una bandada mixta",
                    "weight": "Indique el peso promedio de sus pollos",
                    "general": "Para darle una respuesta precisa sobre sus pollos de engorde, necesito saber:"
                },
                "unknown": {
                    "poultry_type": "Especifique el tipo de aves (gallinas ponedoras, pollos de engorde, etc.)",
                    "species": "Indique la especie exacta de sus animales",
                    "weight": "Indique el peso de sus animales",
                    "general": "Para darle una respuesta precisa, necesito saber:"
                }
            }
        }
        
        lang = language if language in messages else "fr"
        type_messages = messages[lang].get(poultry_type, messages[lang]["unknown"])
        
        # Construire le message de façon sécurisée
        general_msg = type_messages.get("general", "Pour vous donner une réponse précise, j'ai besoin de connaître :")
        specific_msgs = []
        
        for entity in safe_missing_entities:
            if isinstance(entity, str) and entity in type_messages:
                specific_msgs.append(f"• {type_messages[entity]}")
        
        if specific_msgs:
            return f"{general_msg}\n\n" + "\n".join(specific_msgs)
        else:
            return general_msg
            
    except Exception as e:
        logger.error(f"❌ [Generate Critical Message v4.0.0] Erreur: {e}")
        # Fallback sécurisé
        fallback_messages = {
            "fr": "Pour vous donner une réponse précise, j'ai besoin de plus d'informations sur vos animaux.",
            "en": "To give you a precise answer, I need more information about your animals.",
            "es": "Para darle una respuesta precisa, necesito más información sobre sus animales."
        }
        return fallback_messages.get(language, fallback_messages["fr"])

# =============================================================================
# 🚀 SERVICE PRINCIPAL EXPERT AVEC GESTION D'ERREURS ROBUSTE v4.0.0
# =============================================================================

class ExpertService:
    """Service principal pour le système expert avec ALIGNMENT COMPLET v4.0.0"""
    
    def __init__(self):
        try:
            self.integrations = IntegrationsManager()
            self.enhancement_service = APIEnhancementService() if API_ENHANCEMENT_AVAILABLE else None
            
            # Initialiser le service de concision
            if CONCISION_SERVICE_AVAILABLE:
                try:
                    self.concision_service = ConcisionService()
                    logger.info("✅ [Expert Service v4.0.0] ConcisionService initialisé")
                except Exception as e:
                    logger.error(f"❌ [Expert Service v4.0.0] Erreur init ConcisionService: {e}")
                    self.concision_service = MockConcisionService()
            else:
                self.concision_service = MockConcisionService()
                logger.warning("⚠️ [Expert Service v4.0.0] ConcisionService mock utilisé")
            
            # CORRECTION v4.0.0: Initialiser la mémoire conversationnelle avec GESTION ROBUSTE
            if CONVERSATION_MEMORY_AVAILABLE:
                try:
                    self.conversation_memory = IntelligentConversationMemory()
                    logger.info("✅ [Expert Service v4.0.0] Mémoire conversationnelle initialisée avec gestion robuste")
                except Exception as e:
                    logger.error(f"❌ [Expert Service v4.0.0] Erreur init mémoire: {e}")
                    self.conversation_memory = MockConversationMemory()
            else:
                self.conversation_memory = MockConversationMemory()
                logger.warning("⚠️ [Expert Service v4.0.0] Mémoire conversationnelle mock utilisée")
            
            # CORRECTION v4.0.0: Configuration avec nouvelles fonctionnalités
            self.config = {
                "enable_concise_responses": True,
                "default_concision_level": getattr(ConcisionLevel, 'CONCISE', 'concise'),
                "max_response_length": {
                    "ultra_concise": 50, 
                    "concise": 200, 
                    "standard": 500, 
                    "detailed": 1000
                },
                "fallback_mode": not all([MODELS_AVAILABLE, UTILS_AVAILABLE, INTEGRATIONS_AVAILABLE]),
                "critical_clarification_blocking": True,
                "optional_clarification_non_blocking": True,
                "agents_always_active": True,
                "agents_enabled": AGENTS_AVAILABLE,
                "conversation_memory_enabled": CONVERSATION_MEMORY_AVAILABLE,
                "concision_service_enabled": CONCISION_SERVICE_AVAILABLE or True,
                "safe_weight_access": True,
                "safe_missing_entities_access": True,
                # CORRECTION v4.0.0: Nouvelles fonctionnalités
                "robust_memory_error_handling": True,
                "field_existence_verification": True,
                "response_object_validation": True,
                "alignment_expert_models": True
            }
            
            logger.info("🚀 [Expert Service v4.0.0] Service expert initialisé avec ALIGNMENT COMPLET")
            logger.info(f"🛑 [Expert Service v4.0.0] Clarification critique bloquante: {self.config['critical_clarification_blocking']}")
            logger.info(f"💡 [Expert Service v4.0.0] Clarification optionnelle non bloquante: {self.config['optional_clarification_non_blocking']}")
            logger.info(f"📏 [Expert Service v4.0.0] Service concision activé: {self.config['concision_service_enabled']}")
            logger.info(f"⚖️ [Expert Service v4.0.0] Accès sécurisé weight: {self.config['safe_weight_access']}")
            logger.info(f"🔒 [Expert Service v4.0.0] Accès sécurisé missing_entities: {self.config['safe_missing_entities_access']}")
            logger.info(f"🧠 [Expert Service v4.0.0] Gestion robuste erreurs mémoire: {self.config['robust_memory_error_handling']}")
            logger.info(f"🔧 [Expert Service v4.0.0] Vérification existence champs: {self.config['field_existence_verification']}")
            logger.info(f"🎯 [Expert Service v4.0.0] Alignment expert_models: {self.config['alignment_expert_models']}")
            
        except Exception as e:
            logger.error(f"❌ [Expert Service v4.0.0] Erreur critique lors de l'initialisation: {e}")
            # Configuration d'urgence
            self.integrations = IntegrationsManager()
            self.enhancement_service = None
            self.conversation_memory = MockConversationMemory()
            self.concision_service = MockConcisionService()
            self.config = {
                "enable_concise_responses": False,
                "default_concision_level": "standard",
                "max_response_length": {"standard": 500},
                "fallback_mode": True,
                "critical_clarification_blocking": False,
                "optional_clarification_non_blocking": False,
                "agents_always_active": False,
                "agents_enabled": False,
                "conversation_memory_enabled": False,
                "concision_service_enabled": True,
                "safe_weight_access": True,
                "safe_missing_entities_access": True,
                "robust_memory_error_handling": True,
                "field_existence_verification": True,
                "response_object_validation": True,
                "alignment_expert_models": False
            }
    
    def get_current_user_dependency(self):
        """Retourne la dépendance pour l'authentification de façon sécurisée"""
        try:
            return self.integrations.get_current_user_dependency()
        except Exception as e:
            logger.error(f"❌ [Expert Service v4.0.0] Erreur get_current_user_dependency: {e}")
            return lambda: {"id": "error", "email": "error@intelia.com"}
    
    async def process_expert_question(
        self,
        request_data,
        request: Request,
        current_user: Optional[Dict[str, Any]] = None,
        start_time: float = None
    ):
        """🚀 MÉTHODE PRINCIPALE AVEC ALIGNMENT COMPLET v4.0.0"""
        
        if start_time is None:
            start_time = time.time()
        
        try:
            logger.info("🚀 [ExpertService v4.0.0] Traitement avec ALIGNMENT COMPLET expert_models")
            
            # Extraction sécurisée des paramètres
            question_text = self._extract_question_safe(request_data)
            language = self._extract_language_safe(request_data)
            conversation_id = self._extract_conversation_id_safe(request_data)
            
            logger.info(f"📝 [ExpertService v4.0.0] Question: '{question_text[:100] if question_text else 'VIDE'}...'")
            logger.info(f"🌐 [ExpertService v4.0.0] Langue: {language}")
            logger.info(f"🆔 [ExpertService v4.0.0] Conversation: {conversation_id}")
            
            # Variables de traitement
            processing_steps = ["initialization", "parameter_extraction"]
            ai_enhancements_used = []
            
            # Authentification sécurisée
            user_id = self._extract_user_id_safe(current_user, request_data, request)
            user_email = current_user.get("email") if current_user and isinstance(current_user, dict) else None
            
            processing_steps.append("authentication")
            
            # Validation question
            if not question_text or len(question_text.strip()) < 3:
                return self._create_error_response(
                    "Question trop courte", question_text or "Question vide", 
                    conversation_id, language, start_time
                )
            
            processing_steps.append("question_validation")
            
            # Mode fallback si nécessaire
            if self.config["fallback_mode"]:
                logger.info("🔄 [ExpertService v4.0.0] Mode fallback activé")
                return await self._process_question_fallback(
                    question_text, conversation_id, language, user_email, start_time, processing_steps
                )
            
            # Pipeline principal avec gestion d'erreurs
            return await self._process_question_critical_clarification_pipeline_safe(
                request_data, request, current_user, start_time, processing_steps, ai_enhancements_used,
                question_text, language, conversation_id, user_id
            )
                
        except Exception as e:
            logger.error(f"❌ [ExpertService v4.0.0] Erreur critique: {e}")
            return self._create_error_response(
                f"Erreur interne: {str(e)}", 
                self._extract_question_safe(request_data), 
                self._extract_conversation_id_safe(request_data), 
                self._extract_language_safe(request_data), 
                start_time
            )
    
    # === MÉTHODES D'EXTRACTION SÉCURISÉES (CONSERVÉES) ===
    
    def _extract_question_safe(self, request_data) -> str:
        """Extraction sécurisée du texte de la question"""
        try:
            if hasattr(request_data, 'text') and request_data.text:
                return str(request_data.text)
            elif isinstance(request_data, dict) and 'text' in request_data:
                return str(request_data['text'])
            else:
                return "Question vide"
        except Exception as e:
            logger.error(f"❌ [Extract Question v4.0.0] Erreur: {e}")
            return "Question invalide"
    
    def _extract_language_safe(self, request_data) -> str:
        """Extraction sécurisée de la langue"""
        try:
            if hasattr(request_data, 'language') and request_data.language:
                lang = str(request_data.language).lower()
                return lang if lang in ['fr', 'en', 'es'] else 'fr'
            elif isinstance(request_data, dict) and 'language' in request_data:
                lang = str(request_data['language']).lower()
                return lang if lang in ['fr', 'en', 'es'] else 'fr'
            else:
                return "fr"
        except Exception as e:
            logger.error(f"❌ [Extract Language v4.0.0] Erreur: {e}")
            return "fr"
    
    def _extract_conversation_id_safe(self, request_data) -> str:
        """Extraction sécurisée de l'ID de conversation"""
        try:
            if hasattr(request_data, 'conversation_id') and request_data.conversation_id:
                return str(request_data.conversation_id)
            elif isinstance(request_data, dict) and 'conversation_id' in request_data:
                return str(request_data['conversation_id'])
            else:
                return str(uuid.uuid4())
        except Exception as e:
            logger.error(f"❌ [Extract Conversation ID v4.0.0] Erreur: {e}")
            return str(uuid.uuid4())
    
    def _extract_user_id_safe(self, current_user, request_data, request) -> str:
        """Extraction sécurisée de l'ID utilisateur"""
        try:
            if current_user and isinstance(current_user, dict) and "id" in current_user:
                return str(current_user["id"])
            elif hasattr(request_data, 'user_id') and request_data.user_id:
                return str(request_data.user_id)
            elif UTILS_AVAILABLE:
                return get_user_id_from_request(request)
            else:
                return f"fallback_{uuid.uuid4().hex[:8]}"
        except Exception as e:
            logger.warning(f"⚠️ [ExpertService v4.0.0] Erreur extraction user_id: {e}")
            return f"error_{uuid.uuid4().hex[:8]}"
    
    # === PIPELINE PRINCIPAL SÉCURISÉ v4.0.0 ===
    
    async def _process_question_critical_clarification_pipeline_safe(
        self, request_data, request, current_user, start_time, processing_steps, ai_enhancements_used,
        question_text, language, conversation_id, user_id
    ):
        """🛑 Pipeline avec clarification critique et GESTION ROBUSTE ERREURS MÉMOIRE v4.0.0"""
        
        try:
            logger.info("🛑 [ExpertService v4.0.0] Pipeline clarification critique activé avec gestion robuste mémoire")
            processing_steps.append("critical_clarification_pipeline_activated")
            
            # Traitement clarification (si applicable)
            is_clarification = getattr(request_data, 'is_clarification_response', False)
            
            if is_clarification:
                logger.info("🎪 [ExpertService v4.0.0] Mode clarification détecté")
                processing_steps.append("clarification_mode_detected")
                
                try:
                    clarification_result = await self._process_clarification_enhanced_safe(request_data, processing_steps, language)
                    if clarification_result:
                        return clarification_result
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur traitement clarification: {e}")
                    # Continuer le pipeline normal
            
            # Validation agricole sécurisée
            if self.integrations.agricultural_validator_available:
                try:
                    validation_result = await self._validate_agricultural_question_safe(
                        question_text, language, current_user
                    )
                    processing_steps.append("agricultural_validation")
                    
                    if not validation_result.is_valid:
                        return self._create_validation_error_response(
                            validation_result, question_text, conversation_id, language, start_time
                        )
                except Exception as e:
                    logger.warning(f"⚠️ [ExpertService v4.0.0] Erreur validation agricole: {e}")
            
            # ANALYSE CLARIFICATION CRITIQUE AVANT RAG - CONSERVÉE
            try:
                logger.info("🛑 [Pipeline v4.0.0] Analyse clarification critique AVANT RAG")
                
                clarification_result = await self._analyze_clarification_safe(question_text, language)
                
                processing_steps.append("critical_clarification_analysis")
                ai_enhancements_used.append("critical_clarification_analysis")
                
                # Vérifier si clarification critique requise
                if clarification_result.get("clarification_required_critical", False):
                    logger.info("🛑 [Pipeline v4.0.0] Clarification critique requise - ARRÊT AVANT RAG")
                    processing_steps.append("critical_clarification_blocking")
                    
                    return await self._handle_critical_clarification_safe(
                        clarification_result, question_text, conversation_id, language, 
                        start_time, current_user, processing_steps, ai_enhancements_used
                    )
                    
            except Exception as e:
                logger.error(f"❌ [Pipeline v4.0.0] Erreur analyse clarification critique: {e}")
                processing_steps.append("critical_clarification_error_continue")
            
            # PIPELINE NORMAL SI PAS DE CLARIFICATION CRITIQUE
            logger.info("✅ [Pipeline v4.0.0] Pas de clarification critique - continuation pipeline normal")
            
            return await self._process_normal_pipeline_safe(
                question_text, language, conversation_id, user_id, current_user,
                start_time, processing_steps, ai_enhancements_used, request, request_data
            )
            
        except Exception as e:
            logger.error(f"❌ [Pipeline Safe v4.0.0] Erreur critique: {e}")
            return await self._handle_pipeline_error_safe(
                e, question_text, conversation_id, language, start_time, 
                processing_steps, ai_enhancements_used
            )
    
    async def _analyze_clarification_safe(self, question_text: str, language: str) -> dict:
        """Analyse clarification de façon sécurisée - CONSERVÉE"""
        try:
            if hasattr(self.integrations, '_clarification_functions') and \
               'analyze_question_for_clarification_enhanced' in self.integrations._clarification_functions:
                return await self.integrations._clarification_functions['analyze_question_for_clarification_enhanced'](question_text, language)
            else:
                return await analyze_question_for_clarification_enhanced(question_text, language)
        except Exception as e:
            logger.error(f"❌ [Analyze Clarification Safe v4.0.0] Erreur: {e}")
            return {
                "clarification_required_critical": False,
                "clarification_required_optional": False,
                "missing_critical_entities": [],
                "missing_optional_entities": [],
                "confidence": 0.0,
                "reasoning": f"Erreur analyse: {str(e)}",
                "poultry_type": "unknown"
            }
    
    async def _handle_critical_clarification_safe(
        self, clarification_result, question_text, conversation_id, language, 
        start_time, current_user, processing_steps, ai_enhancements_used
    ):
        """CORRECTION v4.0.0: Gestion sécurisée clarification critique avec GESTION ROBUSTE MÉMOIRE"""
        try:
            # Validation missing_entities sécurisée
            raw_missing_critical = clarification_result.get("missing_critical_entities", [])
            missing_critical_entities = safe_get_missing_entities({"missing_entities": raw_missing_critical})
            
            # CORRECTION v4.0.0: Marquage dans la mémoire avec GESTION ROBUSTE D'ERREURS
            if self.config["robust_memory_error_handling"]:
                try:
                    mark_success = safe_mark_pending_clarification(
                        self.conversation_memory, conversation_id, question_text, missing_critical_entities
                    )
                    
                    if mark_success:
                        logger.info(f"🧠 [Pipeline v4.0.0] Clarification critique marquée avec succès: {missing_critical_entities}")
                        processing_steps.append("memory_clarification_marked_success")
                    else:
                        logger.warning(f"⚠️ [Pipeline v4.0.0] Échec marquage clarification (non bloquant): {conversation_id}")
                        processing_steps.append("memory_clarification_marked_failed_non_blocking")
                        
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur marquage mémoire (NON BLOQUANT): {e}")
                    processing_steps.append("memory_clarification_error_non_blocking")
                    # CORRECTION v4.0.0: Ne pas bloquer la réponse utilisateur pour erreur mémoire
            else:
                # Méthode legacy si gestion robuste désactivée
                try:
                    if self.conversation_memory and missing_critical_entities:
                        self.conversation_memory.mark_pending_clarification(
                            conversation_id, question_text, missing_critical_entities
                        )
                        logger.info(f"🧠 [Pipeline v4.0.0] Clarification marquée (legacy): {missing_critical_entities}")
                except Exception as e:
                    logger.warning(f"⚠️ [Pipeline v4.0.0] Erreur marquage legacy (ignorée): {e}")
            
            # Générer message de clarification critique
            poultry_type = clarification_result.get("poultry_type", "unknown")
            critical_message = generate_critical_clarification_message_safe(
                missing_critical_entities, poultry_type, language
            )
            
            # Retourner la réponse de clarification
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return self._create_critical_clarification_response(
                question_text, critical_message, conversation_id, language, response_time_ms,
                current_user, processing_steps, ai_enhancements_used, clarification_result
            )
            
        except Exception as e:
            logger.error(f"❌ [Handle Critical Clarification v4.0.0] Erreur: {e}")
            return self._create_error_response(
                "Erreur lors de la clarification critique", question_text, 
                conversation_id, language, start_time
            )
    
    async def _process_normal_pipeline_safe(
        self, question_text, language, conversation_id, user_id, current_user,
        start_time, processing_steps, ai_enhancements_used, request, request_data
    ):
        """CORRECTION v4.0.0: Pipeline normal avec GESTION ROBUSTE ERREURS MÉMOIRE et ALIGNMENT"""
        try:
            # Variables par défaut
            question_for_rag = question_text
            final_answer = ""
            rag_score = None
            mode = "unknown"
            optional_clarifications = []
            
            # CORRECTION v4.0.0: Récupération contexte conversationnel avec GESTION ROBUSTE ERREURS
            conversation_context = None
            entities = {}
            missing_entities = []
            formatted_context = ""
            
            if self.config["robust_memory_error_handling"] and self.conversation_memory:
                try:
                    # CORRECTION v4.0.0: Utilisation fonction sécurisée
                    conversation_context = safe_get_conversation_context(self.conversation_memory, conversation_id)
                    
                    if conversation_context:
                        # CORRECTION v4.0.0: Extraction sécurisée des entités
                        entities, missing_entities = safe_extract_entities_from_context(conversation_context)
                        
                        # CORRECTION v4.0.0: Accès sécurisé weight avec validation
                        if self.config["safe_weight_access"]:
                            weight_value = safe_get_weight(entities)
                            weight_unit = safe_get_weight_unit(entities)
                            
                            if weight_value is not None:
                                logger.info(f"⚖️ [Pipeline v4.0.0] Weight récupéré: {weight_value} {weight_unit}")
                                weight_result = validate_and_normalize_weight(weight_value, weight_unit)
                                if weight_result["is_valid"]:
                                    entities["weight"] = weight_result["value"]
                                    entities["weight_unit"] = weight_result["unit"]
                                else:
                                    logger.warning(f"⚠️ [Pipeline v4.0.0] Weight invalide ignoré: {weight_result['error']}")
                        
                        # Formatted context sécurisé
                        if hasattr(conversation_context, 'get_formatted_context'):
                            try:
                                formatted_context = conversation_context.get_formatted_context()
                            except Exception as e:
                                logger.warning(f"⚠️ [Pipeline v4.0.0] Erreur formatted_context (ignorée): {e}")
                                formatted_context = ""
                        
                        logger.info(f"🧠 [Pipeline v4.0.0] Contexte récupéré: {len(entities)} entités, {len(missing_entities)} missing")
                        processing_steps.append("conversation_context_retrieved_safe")
                    else:
                        logger.info("🆕 [Pipeline v4.0.0] Nouvelle conversation")
                        processing_steps.append("new_conversation_detected")
                        
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur récupération contexte (NON BLOQUANT): {e}")
                    processing_steps.append("context_retrieval_error_non_blocking")
                    # CORRECTION v4.0.0: Continuer sans contexte au lieu de planter
                    conversation_context = None
                    entities = {}
                    missing_entities = []
                    formatted_context = ""
            else:
                # Mode legacy ou mémoire désactivée
                logger.info("🔄 [Pipeline v4.0.0] Mémoire robuste désactivée ou non disponible")
                processing_steps.append("memory_disabled_or_unavailable")
            
            # Agent Contextualizer sécurisé avec missing_entities validé
            contextualization_info = {}
            
            if self.config["agents_enabled"]:
                try:
                    logger.info("🤖 [Pipeline v4.0.0] Agent Contextualizer - TOUJOURS ACTIF")
                    
                    # Validation missing_entities avant passage à l'agent
                    safe_missing_entities = safe_get_missing_entities({"missing_entities": missing_entities})
                    
                    contextualization_result = await agent_contextualizer.enrich_question(
                        question=question_text,
                        entities=entities,
                        missing_entities=safe_missing_entities,
                        conversation_context=formatted_context,
                        language=language
                    )
                    
                    if isinstance(contextualization_result, dict):
                        question_for_rag = contextualization_result.get("enriched_question", question_text)
                        contextualization_info = contextualization_result
                        ai_enhancements_used.append(f"contextualizer_{contextualization_result.get('method_used', 'unknown')}")
                    
                    if question_for_rag != question_text:
                        logger.info("✨ [Pipeline v4.0.0] Question enrichie par agent")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur Agent Contextualizer: {e}")
                    question_for_rag = question_text
            
            # Traitement RAG sécurisé
            try:
                app = request.app if request else None
                process_rag = getattr(app.state, 'process_question_with_rag', None) if app else None
                
                if process_rag:
                    logger.info("🔍 [Pipeline v4.0.0] Système RAG disponible")
                    processing_steps.append("rag_processing_with_enriched_question")
                    ai_enhancements_used.append("rag_system_enriched")
                    
                    result = await process_rag(
                        question=question_for_rag,
                        user=current_user,
                        language=language,
                        speed_mode=getattr(request_data, 'speed_mode', 'balanced')
                    )
                    
                    if isinstance(result, dict):
                        final_answer = str(result.get("response", ""))
                        rag_score = result.get("score", 0.0)
                        mode = "rag_processing_with_enriched_question"
                else:
                    logger.info("🔄 [Pipeline v4.0.0] RAG non disponible - Fallback")
                    processing_steps.append("no_rag_fallback_enriched")
                    
                    fallback_data = self._generate_fallback_responses_safe(question_for_rag, language)
                    final_answer = fallback_data["response"]
                    rag_score = None
                    mode = "no_rag_fallback_enriched"
                    
            except Exception as e:
                logger.error(f"❌ [Pipeline v4.0.0] Erreur traitement RAG: {e}")
                fallback_data = self._generate_fallback_responses_safe(question_for_rag, language)
                final_answer = fallback_data["response"]
                rag_score = None
                mode = "rag_error_fallback"
            
            # Agent RAG Enhancer sécurisé avec missing_entities validé
            enhancement_info = {}
            
            if self.config["agents_enabled"]:
                try:
                    logger.info("🔧 [Pipeline v4.0.0] Agent RAG Enhancer")
                    
                    # Validation missing_entities avant passage à l'agent
                    safe_missing_entities = safe_get_missing_entities({"missing_entities": missing_entities})
                    
                    enhancement_result = await agent_rag_enhancer.enhance_rag_answer(
                        rag_answer=final_answer,
                        entities=entities,
                        missing_entities=safe_missing_entities,
                        conversation_context=formatted_context,
                        original_question=question_text,
                        enriched_question=question_for_rag,
                        language=language
                    )
                    
                    if isinstance(enhancement_result, dict):
                        final_answer = enhancement_result.get("enhanced_answer", final_answer)
                        optional_clarifications.extend(enhancement_result.get("optional_clarifications", []))
                        enhancement_info = enhancement_result
                        ai_enhancements_used.append(f"rag_enhancer_{enhancement_result.get('method_used', 'unknown')}")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur Agent RAG Enhancer: {e}")
            
            # Génération des versions de réponse GARANTIE
            response_versions = None
            try:
                if self.config["concision_service_enabled"] and final_answer:
                    logger.info("📏 [Pipeline v4.0.0] Génération versions de réponse")
                    response_versions = self.concision_service.generate_all_versions(final_answer, language)
                    processing_steps.append("response_versions_generated")
                    ai_enhancements_used.append("concision_service")
                    logger.info(f"✅ [Pipeline v4.0.0] Versions générées: {list(response_versions.keys()) if response_versions else 'None'}")
            except Exception as e:
                logger.error(f"❌ [Pipeline v4.0.0] Erreur génération versions: {e}")
                # Fallback versions simple
                try:
                    response_versions = self.concision_service.generate_all_versions(final_answer, language)
                except Exception as e2:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur fallback versions: {e2}")
                    response_versions = None
            
            # CORRECTION v4.0.0: Mise à jour mémoire avec GESTION ROBUSTE D'ERREURS
            if self.config["robust_memory_error_handling"] and self.conversation_memory:
                try:
                    # Ajout message utilisateur
                    user_message_success = await safe_add_message_to_memory(
                        self.conversation_memory, conversation_id, user_id, 
                        question_for_rag, "user", language
                    )
                    
                    # Ajout message assistant
                    assistant_message_success = await safe_add_message_to_memory(
                        self.conversation_memory, conversation_id, user_id, 
                        final_answer, "assistant", language
                    )
                    
                    if user_message_success and assistant_message_success:
                        processing_steps.append("conversation_memory_updated_success")
                        logger.info("✅ [Pipeline v4.0.0] Mémoire mise à jour avec succès")
                    else:
                        processing_steps.append("conversation_memory_partial_success")
                        logger.warning(f"⚠️ [Pipeline v4.0.0] Mise à jour mémoire partielle: user={user_message_success}, assistant={assistant_message_success}")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur mise à jour mémoire (NON BLOQUANT): {e}")
                    processing_steps.append("conversation_memory_error_non_blocking")
                    # CORRECTION v4.0.0: Ne pas bloquer la réponse utilisateur
            
            # CORRECTION v4.0.0: Construction réponse finale avec ALIGNMENT COMPLET
            response_time_ms = int((time.time() - start_time) * 1000)
            user_email = current_user.get("email") if current_user and isinstance(current_user, dict) else None
            
            return self._create_enhanced_response_safe_aligned(
                question_text, final_answer, conversation_id, language, response_time_ms,
                user_email, processing_steps, ai_enhancements_used, rag_score, mode,
                contextualization_info, enhancement_info, optional_clarifications,
                conversation_context, entities, missing_entities, question_for_rag, response_versions
            )

        except Exception as e:
            logger.error(f"❌ [Normal Pipeline v4.0.0] Erreur: {e}")
            return await self._handle_pipeline_error_safe(
                e, question_text, conversation_id, language, start_time, 
                processing_steps, ai_enhancements_used
            )
    
    # === MÉTHODES DE CRÉATION DE RÉPONSES SÉCURISÉES ALIGNÉES v4.0.0 ===
    
    def _create_enhanced_response_safe_aligned(
        self, question_text, final_answer, conversation_id, language, response_time_ms,
        user_email, processing_steps, ai_enhancements_used, rag_score, mode,
        contextualization_info, enhancement_info, optional_clarifications,
        conversation_context, entities, missing_entities, question_for_rag, response_versions
    ):
        """CORRECTION v4.0.0: Création sécurisée réponse enrichie avec ALIGNMENT COMPLET expert_models"""
        try:
            if MODELS_AVAILABLE:
                # CORRECTION v4.0.0: Création avec vérification champs selon expert_models.py
                response_data = {
                    # Champs obligatoires selon expert_models.py
                    "question": str(question_text),
                    "response": str(final_answer),
                    "conversation_id": str(conversation_id),
                    "rag_used": bool(rag_score),
                    "timestamp": datetime.now().isoformat(),
                    "language": str(language),
                    "response_time_ms": int(response_time_ms),
                    "mode": str(mode),
                    
                    # Champs optionnels selon expert_models.py
                    "rag_score": rag_score,
                    "user": str(user_email) if user_email else None,
                    "logged": True,
                    "validation_passed": True,
                    "validation_confidence": None,
                    "processing_steps": list(processing_steps) if isinstance(processing_steps, list) else [],
                    "ai_enhancements_used": list(ai_enhancements_used) if isinstance(ai_enhancements_used, list) else []
                }
                
                # CORRECTION v4.0.0: Créer objet avec alignment expert_models
                response = EnhancedExpertResponse(**response_data)
                
                # CORRECTION v4.0.0: Ajout champs avec vérification existence
                if self.config["field_existence_verification"]:
                    # enriched_question avec vérification
                    if question_for_rag != question_text:
                        safe_set_field_if_exists(response, "enriched_question", str(question_for_rag), "Enhanced Response")
                    
                    # response_versions avec garantie
                    try:
                        if response_versions and isinstance(response_versions, dict):
                            safe_set_field_if_exists(response, "response_versions", response_versions, "Enhanced Response")
                            logger.info("✅ [Enhanced Response v4.0.0] response_versions ajoutées avec vérification")
                        else:
                            # Fallback si versions non générées
                            logger.warning("⚠️ [Enhanced Response v4.0.0] Génération fallback response_versions")
                            fallback_versions = self.concision_service.generate_all_versions(final_answer, language)
                            safe_set_field_if_exists(response, "response_versions", fallback_versions, "Enhanced Response")
                    except Exception as e:
                        logger.error(f"❌ [Enhanced Response v4.0.0] Erreur response_versions: {e}")
                        # Fallback minimal avec vérification
                        minimal_versions = {
                            "ultra_concise": final_answer[:50] + "..." if len(final_answer) > 50 else final_answer,
                            "concise": final_answer[:150] + "..." if len(final_answer) > 150 else final_answer,
                            "standard": final_answer[:300] + "..." if len(final_answer) > 300 else final_answer,
                            "detailed": final_answer
                        }
                        safe_set_field_if_exists(response, "response_versions", minimal_versions, "Enhanced Response")
                    
                    # Informations contextuelles avec vérification
                    if self.config["agents_enabled"]:
                        if isinstance(contextualization_info, dict) and contextualization_info:
                            safe_set_field_if_exists(response, "contextualization_info", contextualization_info, "Enhanced Response")
                        
                        if isinstance(enhancement_info, dict) and enhancement_info:
                            safe_set_field_if_exists(response, "enhancement_info", enhancement_info, "Enhanced Response")
                    
                    # Clarifications optionnelles
                    if isinstance(optional_clarifications, list) and optional_clarifications:
                        safe_set_field_if_exists(response, "optional_clarifications", optional_clarifications, "Enhanced Response")
                        safe_set_field_if_exists(response, "clarification_mode", "optional_non_blocking", "Enhanced Response")
                    
                    # Contexte conversationnel avec gestion robuste
                    if conversation_context:
                        try:
                            entities_count = 0
                            if isinstance(entities, dict):
                                entities_count = len([k for k, v in entities.items() if v is not None])
                                
                                # Information weight dans contexte si disponible
                                weight_info = {}
                                if self.config["safe_weight_access"]:
                                    weight_value = safe_get_weight(entities)
                                    weight_unit = safe_get_weight_unit(entities)
                                    if weight_value is not None:
                                        weight_result = validate_and_normalize_weight(weight_value, weight_unit)
                                        if weight_result["is_valid"]:
                                            weight_info = {
                                                "value": weight_result["value"],
                                                "unit": weight_result["unit"],
                                                "validated": True
                                            }
                            
                            # Accès sécurisé missing_entities pour conversation_context_info
                            safe_missing_entities = safe_get_missing_entities({"missing_entities": missing_entities})
                            
                            conversation_context_info = {
                                "total_exchanges": safe_get_field_if_exists(conversation_context, 'total_exchanges', 0),
                                "conversation_urgency": safe_get_field_if_exists(conversation_context, 'conversation_urgency', 'normal'),
                                "entities_count": entities_count,
                                "missing_entities": safe_missing_entities,
                                "missing_entities_count": len(safe_missing_entities),
                                "overall_confidence": safe_get_field_if_exists(
                                    safe_get_field_if_exists(conversation_context, 'consolidated_entities'), 
                                    'confidence_overall', 0.5
                                )
                            }
                            
                            # Ajouter weight_info si disponible
                            if weight_info:
                                conversation_context_info["weight_info"] = weight_info
                            
                            safe_set_field_if_exists(response, "conversation_context", conversation_context_info, "Enhanced Response")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ [Enhanced Response v4.0.0] Erreur conversation_context: {e}")
                    
                    # Métadonnées pipeline
                    safe_set_field_if_exists(response, "pipeline_version", "expert_models_aligned_v4.0.0", "Enhanced Response")
                    safe_set_field_if_exists(response, "pipeline_improvements", [
                        "agents_always_active",
                        "critical_clarification_blocking",
                        "optional_clarification_non_blocking", 
                        "enriched_question_to_rag",
                        "intelligent_fallback",
                        "robust_error_handling",
                        "response_versions_guaranteed",
                        "safe_weight_access",
                        "safe_missing_entities_access",
                        "robust_memory_error_handling",  # NOUVEAU v4.0.0
                        "field_existence_verification",  # NOUVEAU v4.0.0
                        "expert_models_alignment"        # NOUVEAU v4.0.0
                    ], "Enhanced Response")
                    
                else:
                    # Mode legacy sans vérification champs (non recommandé)
                    logger.warning("⚠️ [Enhanced Response v4.0.0] Mode legacy sans vérification champs")
                    if hasattr(response, 'enriched_question') and question_for_rag != question_text:
                        response.enriched_question = str(question_for_rag)
                    if response_versions and hasattr(response, 'response_versions'):
                        response.response_versions = response_versions
                
                # CORRECTION v4.0.0: Validation finale objet réponse
                if self.config["response_object_validation"]:
                    is_valid = validate_response_object_compatibility(response)
                    if not is_valid:
                        logger.warning("⚠️ [Enhanced Response v4.0.0] Objet réponse non compatible, utilisation fallback")
                        return self._create_basic_response_safe_aligned(
                            question_text, final_answer, conversation_id, 
                            language, response_time_ms, processing_steps, response_versions
                        )
                
                logger.info("✅ [Enhanced Response v4.0.0] Réponse enrichie créée avec alignment complet")
                return response
                
            else:
                # Fallback avec response_versions garanties
                basic_response = self._create_basic_response_safe_aligned(
                    question_text, final_answer, conversation_id, 
                    language, response_time_ms, processing_steps, response_versions
                )
                return basic_response
                
        except Exception as e:
            logger.error(f"❌ [Create Enhanced Response v4.0.0] Erreur: {e}")
            fallback = self._create_basic_response_safe_aligned(
                question_text, final_answer, conversation_id, 
                language, response_time_ms, processing_steps, response_versions
            )
            return fallback

    def _create_basic_response_safe_aligned(self, question_text, final_answer, conversation_id, language, response_time_ms, processing_steps, response_versions=None):
        """CORRECTION v4.0.0: Création de réponse basique avec alignment"""
        try:
            basic_response = {
                "question": str(question_text),
                "response": str(final_answer),
                "conversation_id": str(conversation_id),
                "timestamp": datetime.now().isoformat(),
                "language": str(language),
                "response_time_ms": int(response_time_ms),
                "mode": "fallback_basic_aligned",
                "processing_steps": list(processing_steps) if isinstance(processing_steps, list) else [],
                "pipeline_version": "basic_fallback_aligned_v4.0.0"
            }
            
            # CORRECTION v4.0.0: Garantir response_versions même en fallback
            try:
                if response_versions and isinstance(response_versions, dict):
                    basic_response["response_versions"] = response_versions
                else:
                    basic_response["response_versions"] = self.concision_service.generate_all_versions(final_answer, language)
            except Exception as e:
                logger.error(f"❌ [Basic Response v4.0.0] Erreur response_versions: {e}")
                basic_response["response_versions"] = {"detailed": final_answer}
            
            # Flags nouveaux features v4.0.0
            basic_response["safe_weight_access"] = self.config["safe_weight_access"]
            basic_response["safe_missing_entities_access"] = self.config["safe_missing_entities_access"]
            basic_response["robust_memory_error_handling"] = self.config["robust_memory_error_handling"]
            basic_response["alignment_expert_models"] = self.config["alignment_expert_models"]
            
            return basic_response
            
        except Exception as e:
            logger.error(f"❌ [Create Basic Response v4.0.0] Erreur: {e}")
            return {
                "question": "Erreur",
                "response": "Une erreur s'est produite",
                "conversation_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "language": "fr",
                "response_time_ms": 0,
                "mode": "error_fallback_aligned",
                "processing_steps": ["error"],
                "pipeline_version": "error_fallback_aligned_v4.0.0",
                "response_versions": {"detailed": "Erreur"},
                "safe_weight_access": True,
                "safe_missing_entities_access": True,
                "robust_memory_error_handling": True,
                "alignment_expert_models": False
            }