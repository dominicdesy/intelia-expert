"""
app/api/v1/expert_services_responses.py - GESTIONNAIRE DE RÉPONSES EXPERT SYSTEM

🚀 CRÉATION ET GESTION DES RÉPONSES v4.1.1:
1. ✅ Création de réponses d'erreur
2. ✅ Création de réponses de clarification critique  
3. ✅ Création de réponses enrichies alignées
4. ✅ Création de réponses basiques de fallback
5. 🆕 CORRECTION: Utilisation de allow_creation=True pour enriched_question
6. 🔧 CORRECTION v4.1.1: Assignations sécurisées avec try/catch
"""

import logging
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from .expert_services_utils import (
    safe_get_missing_entities, safe_set_field_if_exists, safe_set_field_with_creation,
    safe_get_field_if_exists, safe_get_weight, safe_get_weight_unit,
    validate_and_normalize_weight, validate_response_object_compatibility,
    safe_set_field_smart
)

logger = logging.getLogger(__name__)

# Import conditionnel des modèles
try:
    from .expert_models import EnhancedExpertResponse
    MODELS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    class EnhancedExpertResponse:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    MODELS_AVAILABLE = False

class ExpertResponseCreator:
    """Créateur de réponses pour le système expert avec ALIGNMENT COMPLET et CHAMPS DYNAMIQUES v4.1.1"""
    
    def __init__(self, concision_service):
        self.concision_service = concision_service
        self.config = {
            "field_existence_verification": True,
            "response_object_validation": True,
            "alignment_expert_models": True,
            "safe_weight_access": True,
            "safe_missing_entities_access": True,
            "dynamic_field_creation": True,  # 🆕 Nouveau flag v4.1.0
            "secure_field_assignment": True  # 🔧 Nouveau flag v4.1.1
        }
    
    def create_error_response(self, error_message, question_text, conversation_id, language, start_time):
        """CORRECTION v4.1.0: Création de réponse d'erreur avec alignment"""
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
                # Création avec alignment expert_models
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
                
                # Ajout response_versions avec vérification - UTILISATION INTELLIGENTE v4.1.0
                if self.config["field_existence_verification"]:
                    if self.config["dynamic_field_creation"]:
                        # 🧠 Utilisation de l'assignation intelligente
                        safe_set_field_smart(response, "response_versions", response_versions, "Error Response")
                        safe_set_field_smart(response, "pipeline_version", "error_response_aligned_v4.1.1", "Error Response")
                    else:
                        # Mode legacy
                        safe_set_field_if_exists(response, "response_versions", response_versions, "Error Response")
                        safe_set_field_if_exists(response, "pipeline_version", "error_response_aligned_v4.1.1", "Error Response")
                else:
                    if hasattr(response, 'response_versions'):
                        response.response_versions = response_versions
                    if hasattr(response, 'pipeline_version'):
                        response.pipeline_version = "error_response_aligned_v4.1.1"
                
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
                    "alignment_expert_models": False,
                    "dynamic_field_creation": True,  # 🆕 Nouveau flag v4.1.0
                    "secure_field_assignment": True  # 🔧 Nouveau flag v4.1.1
                }
                
        except Exception as e:
            logger.error(f"❌ [Create Error Response v4.1.1] Erreur critique: {e}")
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
                "alignment_expert_models": False,
                "dynamic_field_creation": True,  # 🆕 Nouveau flag v4.1.0
                "secure_field_assignment": True  # 🔧 Nouveau flag v4.1.1
            }

    def create_critical_clarification_response(
        self, question_text, critical_message, conversation_id, language, response_time_ms,
        current_user, processing_steps, ai_enhancements_used, clarification_result
    ):
        """CORRECTION v4.1.0: Création réponse clarification critique avec alignment et champs dynamiques"""
        try:
            user_email = current_user.get("email") if current_user and isinstance(current_user, dict) else None
            
            # Générer response_versions pour clarification
            try:
                response_versions = self.concision_service.generate_all_versions(critical_message, language)
            except Exception as e:
                logger.error(f"❌ [Critical Clarification v4.1.1] Erreur response_versions: {e}")
                response_versions = {
                    "ultra_concise": "Clarification requise",
                    "concise": "Plus d'informations nécessaires",
                    "standard": critical_message[:200] + "..." if len(critical_message) > 200 else critical_message,
                    "detailed": critical_message
                }
            
            if MODELS_AVAILABLE:
                # Création avec alignment expert_models
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
                
                # Ajout champs avec vérification - UTILISATION INTELLIGENTE v4.1.0
                if self.config["field_existence_verification"]:
                    if self.config["dynamic_field_creation"]:
                        # 🧠 Utilisation de l'assignation intelligente pour tous les champs
                        safe_set_field_smart(response, "response_versions", response_versions, "Critical Clarification")
                        safe_set_field_smart(response, "clarification_mode", "critical_blocking", "Critical Clarification")
                        
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
                            
                            safe_set_field_smart(response, "clarification_details", clarification_details, "Critical Clarification")
                        
                        safe_set_field_smart(response, "pipeline_version", "critical_clarification_aligned_v4.1.1", "Critical Clarification")
                    else:
                        # Mode legacy avec safe_set_field_if_exists standard
                        safe_set_field_if_exists(response, "response_versions", response_versions, "Critical Clarification")
                        safe_set_field_if_exists(response, "clarification_mode", "critical_blocking", "Critical Clarification")
                
                else:
                    # Mode legacy complet
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
                    "alignment_expert_models": False,
                    "dynamic_field_creation": True,  # 🆕 Nouveau flag v4.1.0
                    "secure_field_assignment": True  # 🔧 Nouveau flag v4.1.1
                }
                
        except Exception as e:
            logger.error(f"❌ [Create Critical Clarification Response v4.1.1] Erreur: {e}")
            return self.create_error_response(
                "Erreur création réponse clarification", question_text, 
                conversation_id, language, time.time() - (response_time_ms / 1000) if response_time_ms else time.time()
            )

    def create_enhanced_response_safe_aligned(
        self, question_text, final_answer, conversation_id, language, response_time_ms,
        user_email, processing_steps, ai_enhancements_used, rag_score, mode,
        contextualization_info, enhancement_info, optional_clarifications,
        conversation_context, entities, missing_entities, question_for_rag, response_versions
    ):
        """🔧 CORRECTION v4.1.1: Création sécurisée réponse enrichie avec ASSIGNATIONS SÉCURISÉES"""
        try:
            if MODELS_AVAILABLE:
                # Création avec vérification champs selon expert_models.py
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
                
                # Créer objet avec alignment expert_models
                response = EnhancedExpertResponse(**response_data)
                
                # 🔧 CORRECTION PRINCIPALE v4.1.1: Assignations sécurisées avec try/catch individuel
                
                # enriched_question - SÉCURISÉ
                try:
                    if question_for_rag != question_text:
                        response.enriched_question = str(question_for_rag)
                        logger.info(f"✅ [Enhanced Response v4.1.1] enriched_question ajouté: '{question_for_rag[:50]}...'")
                except Exception as e:
                    logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur enriched_question: {e}")
                
                # response_versions - SÉCURISÉ
                try:
                    if response_versions and isinstance(response_versions, dict):
                        response.response_versions = response_versions
                        logger.info(f"✅ [Enhanced Response v4.1.1] response_versions ajouté avec {len(response_versions)} versions")
                    else:
                        # Fallback si versions non générées
                        logger.warning("⚠️ [Enhanced Response v4.1.1] Génération fallback response_versions")
                        fallback_versions = self.concision_service.generate_all_versions(final_answer, language)
                        response.response_versions = fallback_versions
                        logger.info(f"✅ [Enhanced Response v4.1.1] response_versions fallback créées")
                except Exception as e:
                    logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur response_versions: {e}")
                    # Fallback minimal sécurisé
                    try:
                        minimal_versions = {
                            "ultra_concise": final_answer[:50] + "..." if len(final_answer) > 50 else final_answer,
                            "concise": final_answer[:150] + "..." if len(final_answer) > 150 else final_answer,
                            "standard": final_answer[:300] + "..." if len(final_answer) > 300 else final_answer,
                            "detailed": final_answer
                        }
                        response.response_versions = minimal_versions
                        logger.info(f"✅ [Enhanced Response v4.1.1] response_versions minimal créées")
                    except Exception as fallback_e:
                        logger.error(f"❌ [Enhanced Response v4.1.1] Erreur critique response_versions: {fallback_e}")
                
                # enhancement_info (nouveau) - SÉCURISÉ
                try:
                    if enhancement_info and isinstance(enhancement_info, dict):
                        response.enhancement_info = enhancement_info
                        logger.info(f"✅ [Enhanced Response v4.1.1] enhancement_info ajouté")
                except Exception as e:
                    logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur enhancement_info: {e}")
                
                # clarification_details (nouveau) - SÉCURISÉ
                try:
                    if optional_clarifications and isinstance(optional_clarifications, list):
                        safe_missing_entities_list = safe_get_missing_entities({"missing_entities": missing_entities or []})
                        response.clarification_details = {
                            "optional_clarifications": optional_clarifications,
                            "missing_entities": safe_missing_entities_list
                        }
                        logger.info(f"✅ [Enhanced Response v4.1.1] clarification_details ajouté avec {len(optional_clarifications)} clarifications")
                except Exception as e:
                    logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur clarification_details: {e}")
                
                # contextualization_info - SÉCURISÉ
                try:
                    if isinstance(contextualization_info, dict) and contextualization_info:
                        response.contextualization_info = contextualization_info
                        logger.info(f"✅ [Enhanced Response v4.1.1] contextualization_info ajouté")
                except Exception as e:
                    logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur contextualization_info: {e}")
                
                # conversation_context - SÉCURISÉ avec gestion robuste
                try:
                    if conversation_context:
                        entities_count = 0
                        weight_info = {}
                        
                        if isinstance(entities, dict):
                            entities_count = len([k for k, v in entities.items() if v is not None])
                            
                            # Information weight dans contexte si disponible
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
                        safe_missing_entities_list = safe_get_missing_entities({"missing_entities": missing_entities or []})
                        
                        conversation_context_info = {
                            "total_exchanges": safe_get_field_if_exists(conversation_context, 'total_exchanges', 0),
                            "conversation_urgency": safe_get_field_if_exists(conversation_context, 'conversation_urgency', 'normal'),
                            "entities_count": entities_count,
                            "missing_entities": safe_missing_entities_list,
                            "missing_entities_count": len(safe_missing_entities_list),
                            "overall_confidence": safe_get_field_if_exists(
                                safe_get_field_if_exists(conversation_context, 'consolidated_entities'), 
                                'confidence_overall', 0.5
                            )
                        }
                        
                        # Ajouter weight_info si disponible
                        if weight_info:
                            conversation_context_info["weight_info"] = weight_info
                        
                        response.conversation_context = conversation_context_info
                        logger.info(f"✅ [Enhanced Response v4.1.1] conversation_context ajouté")
                        
                except Exception as e:
                    logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur conversation_context: {e}")
                
                # Métadonnées pipeline - SÉCURISÉ
                try:
                    response.pipeline_version = "expert_models_aligned_v4.1.1"
                    response.pipeline_improvements = [
                        "agents_always_active",
                        "critical_clarification_blocking",
                        "optional_clarification_non_blocking", 
                        "enriched_question_to_rag",
                        "intelligent_fallback",
                        "robust_error_handling",
                        "response_versions_guaranteed",
                        "safe_weight_access",
                        "safe_missing_entities_access",
                        "robust_memory_error_handling",
                        "field_existence_verification",
                        "expert_models_alignment",
                        "dynamic_field_creation",  # 🆕 v4.1.0
                        "secure_field_assignment"  # 🔧 v4.1.1
                    ]
                    logger.info(f"✅ [Enhanced Response v4.1.1] Métadonnées pipeline ajoutées")
                except Exception as e:
                    logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur métadonnées pipeline: {e}")
                
                # Validation finale objet réponse
                if self.config["response_object_validation"]:
                    try:
                        is_valid = validate_response_object_compatibility(response)
                        if not is_valid:
                            logger.warning("⚠️ [Enhanced Response v4.1.1] Objet réponse non compatible, utilisation fallback")
                            return self.create_basic_response_safe_aligned(
                                question_text, final_answer, conversation_id, 
                                language, response_time_ms, processing_steps, response_versions
                            )
                    except Exception as e:
                        logger.warning(f"⚠️ [Enhanced Response v4.1.1] Erreur validation finale: {e}")
                
                logger.info("✅ [Enhanced Response v4.1.1] Réponse enrichie créée avec assignations sécurisées")
                return response
                
            else:
                # Fallback avec response_versions garanties
                logger.info("📦 [Enhanced Response v4.1.1] MODELS_AVAILABLE=False, utilisation fallback")
                basic_response = self.create_basic_response_safe_aligned(
                    question_text, final_answer, conversation_id, 
                    language, response_time_ms, processing_steps, response_versions
                )
                return basic_response
                
        except Exception as e:
            logger.error(f"❌ [Create Enhanced Response v4.1.1] Erreur création: {e}")
            fallback = self.create_basic_response_safe_aligned(
                question_text, final_answer, conversation_id, 
                language, response_time_ms, processing_steps, response_versions
            )
            return fallback

    def create_basic_response_safe_aligned(self, question_text, final_answer, conversation_id, language, response_time_ms, processing_steps, response_versions=None):
        """CORRECTION v4.1.1: Création de réponse basique avec alignment et champs dynamiques"""
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
                "pipeline_version": "basic_fallback_aligned_v4.1.1"
            }
            
            # Garantir response_versions même en fallback
            try:
                if response_versions and isinstance(response_versions, dict):
                    basic_response["response_versions"] = response_versions
                else:
                    basic_response["response_versions"] = self.concision_service.generate_all_versions(final_answer, language)
            except Exception as e:
                logger.error(f"❌ [Basic Response v4.1.1] Erreur response_versions: {e}")
                basic_response["response_versions"] = {"detailed": final_answer}
            
            # Flags nouveaux features v4.1.1
            basic_response["safe_weight_access"] = self.config["safe_weight_access"]
            basic_response["safe_missing_entities_access"] = self.config["safe_missing_entities_access"]
            basic_response["robust_memory_error_handling"] = True
            basic_response["alignment_expert_models"] = self.config["alignment_expert_models"]
            basic_response["dynamic_field_creation"] = self.config["dynamic_field_creation"]  # 🆕 v4.1.0
            basic_response["secure_field_assignment"] = self.config["secure_field_assignment"]  # 🔧 v4.1.1
            
            return basic_response
            
        except Exception as e:
            logger.error(f"❌ [Create Basic Response v4.1.1] Erreur: {e}")
            return {
                "question": "Erreur",
                "response": "Une erreur s'est produite",
                "conversation_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "language": "fr",
                "response_time_ms": 0,
                "mode": "error_fallback_aligned",
                "processing_steps": ["error"],
                "pipeline_version": "error_fallback_aligned_v4.1.1",
                "response_versions": {"detailed": "Erreur"},
                "safe_weight_access": True,
                "safe_missing_entities_access": True,
                "robust_memory_error_handling": True,
                "alignment_expert_models": False,
                "dynamic_field_creation": True,  # 🆕 v4.1.0
                "secure_field_assignment": True  # 🔧 v4.1.1
            }