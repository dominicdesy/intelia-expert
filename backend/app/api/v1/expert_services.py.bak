"""
app/api/v1/expert_services.py - SERVICES MÉTIER EXPERT SYSTEM

Logique métier principale pour le système expert
"""

import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request

from .expert_models import (
    EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest,
    ValidationResult, ProcessingContext
)
from .expert_utils import (
    get_user_id_from_request, 
    build_enriched_question_from_clarification,
    process_question_with_enhanced_prompt,
    get_enhanced_topics_by_language,
    save_conversation_auto_enhanced
)
from .expert_integrations import IntegrationsManager

logger = logging.getLogger(__name__)

class ExpertService:
    """Service principal pour le système expert"""
    
    def __init__(self):
        self.integrations = IntegrationsManager()
        logger.info("✅ [Expert Service] Service expert initialisé")
    
    def get_current_user_dependency(self):
        """Retourne la dépendance pour l'authentification"""
        return self.integrations.get_current_user_dependency()
    
    async def process_expert_question(
        self,
        request_data: EnhancedQuestionRequest,
        request: Request,
        current_user: Optional[Dict[str, Any]],
        start_time: float
    ) -> EnhancedExpertResponse:
        """Traite une question expert avec toutes les fonctionnalités améliorées"""
        
        processing_steps = []
        ai_enhancements_used = []
        
        # Initialisation
        processing_steps.append("initialization")
        
        # === AUTHENTIFICATION ===
        if current_user is None and self.integrations.auth_available:
            raise HTTPException(status_code=401, detail="Authentification requise")
        
        user_id = self._extract_user_id(current_user, request_data, request)
        user_email = current_user.get("email") if current_user else None
        request_ip = request.client.host if request.client else "unknown"
        
        processing_steps.append("authentication")
        
        # === GESTION CONVERSATION ID ===
        conversation_id = self._get_or_create_conversation_id(request_data)
        
        # === VALIDATION QUESTION ===
        question_text = request_data.text.strip()
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        processing_steps.append("question_validation")
        
        # === ENREGISTREMENT DANS MÉMOIRE INTELLIGENTE ===
        conversation_context = None
        if self.integrations.intelligent_memory_available:
            try:
                conversation_context = self.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=request_data.language,
                    message_type="clarification_response" if request_data.is_clarification_response else "question"
                )
                ai_enhancements_used.append("intelligent_memory")
                processing_steps.append("memory_storage")
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur mémoire: {e}")
        
        # === VALIDATION AGRICOLE ===
        validation_result = await self._validate_agricultural_question(
            question_text, request_data.language, user_id, request_ip, conversation_id
        )
        
        processing_steps.append("agricultural_validation")
        
        if not validation_result.is_valid:
            return self._create_rejection_response(
                question_text, validation_result, conversation_id, 
                user_email, request_data.language, start_time,
                processing_steps, ai_enhancements_used
            )
        
        # === SYSTÈME DE CLARIFICATION ===
        clarification_result = await self._handle_clarification(
            request_data, question_text, user_id, conversation_id,
            processing_steps, ai_enhancements_used
        )
        
        if clarification_result:
            return clarification_result
        
        # === TRAITEMENT EXPERT ===
        expert_result = await self._process_expert_response(
            question_text, request_data, request, current_user,
            conversation_id, processing_steps, ai_enhancements_used
        )
        
        # === ENREGISTREMENT RÉPONSE ===
        if self.integrations.intelligent_memory_available and expert_result["answer"]:
            try:
                self.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=expert_result["answer"],
                    role="assistant",
                    language=request_data.language,
                    message_type="response"
                )
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur enregistrement réponse: {e}")
        
        processing_steps.append("response_storage")
        
        # === CONSTRUCTION RÉPONSE FINALE ===
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return self._build_final_response(
            question_text, expert_result["answer"], conversation_id,
            user_email, request_data.language, response_time_ms,
            expert_result, validation_result, conversation_context,
            processing_steps, ai_enhancements_used, request_data
        )
    
    async def process_feedback(self, feedback_data: FeedbackRequest) -> Dict[str, Any]:
        """Traite le feedback utilisateur"""
        
        feedback_updated = False
        
        if feedback_data.conversation_id and self.integrations.logging_available:
            try:
                # Convertir le rating en format numérique
                rating_numeric = {
                    "positive": 1,
                    "negative": -1,
                    "neutral": 0
                }.get(feedback_data.rating, 0)
                
                feedback_updated = await self.integrations.update_feedback(
                    feedback_data.conversation_id, rating_numeric
                )
                
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur mise à jour feedback: {e}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès (Enhanced)",
            "rating": feedback_data.rating,
            "comment": feedback_data.comment,
            "conversation_id": feedback_data.conversation_id,
            "feedback_updated_in_db": feedback_updated,
            "enhanced_features_used": True,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_suggested_topics(self, language: str) -> Dict[str, Any]:
        """Récupère les topics suggérés enrichis"""
        
        lang = language.lower() if language else "fr"
        if lang not in ["fr", "en", "es"]:
            lang = "fr"
        
        topics_by_language = get_enhanced_topics_by_language()
        topics = topics_by_language.get(lang, topics_by_language["fr"])
        
        return {
            "topics": topics,
            "language": lang,
            "count": len(topics),
            "enhanced_features": {
                "numerical_data_included": True,
                "context_aware": True,
                "breed_specific_examples": True
            },
            "system_status": {
                "validation_enabled": self.integrations.is_agricultural_validation_enabled(),
                "enhanced_clarification_enabled": self.integrations.is_enhanced_clarification_enabled(),
                "intelligent_memory_enabled": self.integrations.intelligent_memory_available,
                "ai_enhancements_enabled": self.integrations.intelligent_memory_available and self.integrations.enhanced_clarification_available
            },
            "note": "Topics enrichis avec données numériques et exemples spécifiques"
        }
    
    # === MÉTHODES PRIVÉES ===
    
    def _extract_user_id(self, current_user: Optional[Dict], request_data: EnhancedQuestionRequest, request: Request) -> str:
        """Extrait l'user_id depuis différentes sources"""
        if current_user:
            return current_user.get("user_id") or request_data.user_id or "authenticated_user"
        return request_data.user_id or get_user_id_from_request(request)
    
    def _get_or_create_conversation_id(self, request_data: EnhancedQuestionRequest) -> str:
        """Récupère ou crée un conversation_id"""
        if request_data.conversation_id and request_data.conversation_id.strip():
            conversation_id = request_data.conversation_id.strip()
            logger.info(f"🔄 [Expert Service] CONTINUATION: {conversation_id}")
            return conversation_id
        else:
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 [Expert Service] NOUVELLE: {conversation_id}")
            return conversation_id
    
    async def _validate_agricultural_question(
        self, question: str, language: str, user_id: str, 
        request_ip: str, conversation_id: str
    ) -> ValidationResult:
        """Valide la question dans le domaine agricole"""
        
        if not self.integrations.agricultural_validator_available:
            return ValidationResult(
                is_valid=False,
                rejection_message="Service temporairement indisponible. Veuillez réessayer plus tard.",
                confidence=0.0
            )
        
        # Enrichir avec contexte intelligent si disponible
        enriched_question = question
        if self.integrations.intelligent_memory_available:
            try:
                rag_context = self.integrations.get_context_for_rag(conversation_id)
                if rag_context:
                    enriched_question = f"{question}\n\nContexte conversationnel:\n{rag_context}"
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur enrichissement contexte: {e}")
        
        try:
            validation_result = self.integrations.validate_agricultural_question(
                question=enriched_question,
                language=language,
                user_id=user_id,
                request_ip=request_ip
            )
            
            return ValidationResult(
                is_valid=validation_result.is_valid,
                rejection_message=validation_result.reason or "Question hors domaine agricole",
                confidence=validation_result.confidence
            )
            
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur validateur: {e}")
            
            rejection_messages = {
                "fr": "Erreur de validation. Veuillez reformuler votre question sur le domaine avicole.",
                "en": "Validation error. Please rephrase your question about the poultry domain.",
                "es": "Error de validación. Por favor, reformule su pregunta sobre el dominio avícola."
            }
            
            return ValidationResult(
                is_valid=False,
                rejection_message=rejection_messages.get(language, rejection_messages["fr"]),
                confidence=0.0
            )
    
    async def _handle_clarification(
        self, request_data: EnhancedQuestionRequest, question_text: str,
        user_id: str, conversation_id: str, processing_steps: list,
        ai_enhancements_used: list
    ) -> Optional[EnhancedExpertResponse]:
        """Gère le système de clarification"""
        
        # Vérifier si c'est une réponse à clarification avec retraitement
        if request_data.is_clarification_response and request_data.original_question:
            if self.integrations.enhanced_clarification_available:
                try:
                    # Construire question enrichie
                    enriched_question = build_enriched_question_from_clarification(
                        original_question=request_data.original_question,
                        clarification_response=question_text,
                        conversation_context=self.integrations.get_context_for_rag(conversation_id) if self.integrations.intelligent_memory_available else ""
                    )
                    
                    # Vérifier retraitement possible
                    if hasattr(request_data, 'clarification_context') and request_data.clarification_context:
                        reprocess_result = await self.integrations.check_for_reprocessing_after_clarification(
                            conversation_id=conversation_id,
                            user_response=question_text,
                            original_clarification_result=request_data.clarification_context
                        )
                        
                        if reprocess_result and reprocess_result.should_reprocess:
                            logger.info("✅ [Expert Service] Retraitement automatique activé")
                            ai_enhancements_used.append("automatic_reprocessing")
                            processing_steps.append("automatic_reprocessing")
                            return None  # Continue avec le traitement normal
                
                except Exception as e:
                    logger.warning(f"⚠️ [Expert Service] Erreur vérification retraitement: {e}")
        
        # Analyse de clarification normale
        if not request_data.is_clarification_response and not request_data.force_reprocess:
            if self.integrations.enhanced_clarification_available and self.integrations.is_enhanced_clarification_enabled():
                try:
                    clarification_context = {}
                    if self.integrations.intelligent_memory_available:
                        clarification_context = self.integrations.get_context_for_clarification(conversation_id)
                        ai_enhancements_used.append("intelligent_clarification_context")
                    
                    clarification_result = await self.integrations.analyze_question_for_clarification_enhanced(
                        question=question_text,
                        language=request_data.language,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        conversation_context=clarification_context,
                        original_question=question_text
                    )
                    
                    processing_steps.append("enhanced_clarification_analysis")
                    
                    if clarification_result.needs_clarification:
                        logger.info(f"❓ [Expert Service] Clarification nécessaire")
                        
                        clarification_response = self.integrations.format_clarification_response_enhanced(
                            result=clarification_result,
                            language=request_data.language
                        )
                        
                        # Enregistrer clarification dans mémoire
                        if self.integrations.intelligent_memory_available:
                            try:
                                self.integrations.add_message_to_conversation(
                                    conversation_id=conversation_id,
                                    user_id=user_id,
                                    message=clarification_response,
                                    role="assistant",
                                    language=request_data.language,
                                    message_type="clarification"
                                )
                            except Exception as e:
                                logger.warning(f"⚠️ [Expert Service] Erreur enregistrement clarification: {e}")
                        
                        # Retourner la réponse de clarification
                        return EnhancedExpertResponse(
                            question=str(question_text),
                            response=str(clarification_response),
                            conversation_id=conversation_id,
                            rag_used=False,
                            rag_score=None,
                            timestamp=datetime.now().isoformat(),
                            language=request_data.language,
                            response_time_ms=0,  # Sera calculé plus tard
                            mode="enhanced_clarification_needed",
                            user=None,
                            logged=True,
                            validation_passed=True,
                            clarification_result=clarification_result.to_dict(),
                            processing_steps=processing_steps,
                            ai_enhancements_used=ai_enhancements_used
                        )
                
                except Exception as e:
                    logger.warning(f"⚠️ [Expert Service] Erreur clarification: {e}")
        
        return None  # Pas de clarification nécessaire
    
    async def _process_expert_response(
        self, question_text: str, request_data: EnhancedQuestionRequest,
        request: Request, current_user: Optional[Dict], conversation_id: str,
        processing_steps: list, ai_enhancements_used: list
    ) -> Dict[str, Any]:
        """Traite la réponse expert avec RAG ou OpenAI"""
        
        # Récupérer contexte pour traitement
        conversation_context_str = ""
        if self.integrations.intelligent_memory_available:
            try:
                conversation_context_str = self.integrations.get_context_for_rag(conversation_id, max_chars=800)
                ai_enhancements_used.append("contextual_rag")
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur récupération contexte: {e}")
        
        # Essayer RAG d'abord
        app = request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if process_rag:
            try:
                logger.info("🔍 Utilisation du système RAG avec contexte intelligent...")
                
                try:
                    result = await process_rag(
                        question=question_text,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id,
                        context=conversation_context_str
                    )
                except TypeError:
                    # Si process_rag ne supporte pas le paramètre context
                    result = await process_rag(
                        question=question_text,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode,
                        conversation_id=conversation_id
                    )
                
                answer = str(result.get("response", ""))
                rag_used = result.get("mode", "").startswith("rag")
                rag_score = result.get("score")
                mode = f"enhanced_{result.get('mode', 'rag_processing')}"
                
                processing_steps.append("rag_processing")
                
                return {
                    "answer": answer,
                    "rag_used": rag_used,
                    "rag_score": rag_score,
                    "mode": mode
                }
                
            except Exception as rag_error:
                logger.error(f"❌ Erreur RAG: {rag_error}")
        
        # Fallback vers OpenAI
        logger.info("⚠️ RAG non disponible, utilisation OpenAI avec contexte intelligent")
        answer = await process_question_with_enhanced_prompt(
            question_text,
            request_data.language,
            request_data.speed_mode,
            conversation_context=conversation_context_str
        )
        
        if conversation_context_str:
            ai_enhancements_used.append("enhanced_prompts")
        
        processing_steps.append("direct_openai" if process_rag else "fallback_openai")
        
        return {
            "answer": answer,
            "rag_used": False,
            "rag_score": None,
            "mode": "enhanced_direct_openai" if not process_rag else "enhanced_fallback_openai"
        }
    
    def _create_rejection_response(
        self, question_text: str, validation_result: ValidationResult,
        conversation_id: str, user_email: Optional[str], language: str,
        start_time: float, processing_steps: list, ai_enhancements_used: list
    ) -> EnhancedExpertResponse:
        """Crée une réponse de rejet"""
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return EnhancedExpertResponse(
            question=str(question_text),
            response=str(validation_result.rejection_message),
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode="enhanced_agricultural_validation_rejected",
            user=user_email,
            logged=True,
            validation_passed=False,
            validation_confidence=validation_result.confidence,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used
        )
    
    def _build_final_response(
        self, question_text: str, answer: str, conversation_id: str,
        user_email: Optional[str], language: str, response_time_ms: int,
        expert_result: Dict, validation_result: ValidationResult,
        conversation_context: Any, processing_steps: list,
        ai_enhancements_used: list, request_data: EnhancedQuestionRequest
    ) -> EnhancedExpertResponse:
        """Construit la réponse finale"""
        
        # Métriques finales
        extracted_entities = None
        confidence_overall = None
        conversation_state = None
        
        if conversation_context and hasattr(conversation_context, 'consolidated_entities'):
            extracted_entities = conversation_context.consolidated_entities.to_dict()
            confidence_overall = conversation_context.consolidated_entities.confidence_overall
            conversation_state = conversation_context.conversation_urgency
        
        return EnhancedExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,
            rag_used=expert_result["rag_used"],
            rag_score=expert_result["rag_score"],
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode=expert_result["mode"],
            user=user_email,
            logged=True,
            validation_passed=True,
            validation_confidence=validation_result.confidence,
            reprocessed_after_clarification=request_data.is_clarification_response,
            conversation_state=conversation_state,
            extracted_entities=extracted_entities,
            confidence_overall=confidence_overall,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used
        )

# =============================================================================
# CONFIGURATION
# =============================================================================

logger.info("✅ [Expert Service] Services métier initialisés")
