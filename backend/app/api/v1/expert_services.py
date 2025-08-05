"""
app/api/v1/expert_services.py - SERVICE PRINCIPAL EXPERT SYSTEM (REFACTORISÉ v4.0.0)

🚀 CORRECTIONS APPLIQUÉES v4.0.0:
1. ✅ REFACTORISATION en modules séparés
2. ✅ CORRECTION complète des problèmes d'indentation
3. ✅ CONSERVATION de tout le code original
4. ✅ STRUCTURE modulaire maintenable
"""

import os
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request

# Imports des modules refactorisés
from .expert_services_utils import (
    safe_get_weight, safe_get_weight_unit, validate_and_normalize_weight,
    extract_weight_from_text_safe, safe_get_missing_entities, 
    safe_update_missing_entities, validate_missing_entities_list,
    safe_get_conversation_context, safe_extract_entities_from_context,
    safe_add_message_to_memory, safe_mark_pending_clarification,
    safe_set_field_if_exists, safe_get_field_if_exists,
    validate_response_object_compatibility
)

from .expert_services_responses import (
    ExpertResponseCreator
)

from .expert_services_clarification import (
    analyze_question_for_clarification_enhanced,
    generate_critical_clarification_message_safe
)

logger = logging.getLogger(__name__)

# 🚀 IMPORTS SÉCURISÉS AVEC FALLBACKS ROBUSTES
try:
    from .clarification_entities import normalize_breed_name, infer_sex_from_breed, get_breed_type, get_supported_breeds
    CLARIFICATION_ENTITIES_AVAILABLE = True
    logger.info("✅ [Services] clarification_entities importé avec succès")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services] clarification_entities non disponible: {e}")
    
    # Fonctions fallback
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
        IntelligentEntities
    )
    MODELS_AVAILABLE = True
    logger.info("✅ [Services v4.0.0] expert_models importé avec ALIGNMENT COMPLET")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"⚠️ [Services v4.0.0] expert_models non disponible: {e}")
    from pydantic import BaseModel
    
    # Modèles de fallback robustes
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
    
    class EnhancedExpertResponse:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    MODELS_AVAILABLE = False

# Imports des services et intégrations
try:
    from .expert_integrations import IntegrationsManager
    INTEGRATIONS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    class IntegrationsManager:
        def __init__(self):
            self.agricultural_validator_available = False
        
        def get_current_user_dependency(self):
            return lambda: {"id": "fallback", "email": "fallback@intelia.com"}
        
        def is_agricultural_validation_enabled(self):
            return False
        
        def validate_agricultural_question(self, **kwargs):
            return ValidationResult(is_valid=True, rejection_message="", confidence=0.5)
    
    INTEGRATIONS_AVAILABLE = False

try:
    from .agent_contextualizer import agent_contextualizer
    from .agent_rag_enhancer import agent_rag_enhancer
    AGENTS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    class MockAgent:
        async def enrich_question(self, *args, **kwargs):
            question = args[0] if args else kwargs.get('question', 'Question vide')
            return {"enriched_question": str(question), "method_used": "mock", "entities_used": []}
        
        async def enhance_rag_answer(self, *args, **kwargs):
            answer = args[0] if args else kwargs.get('rag_answer', 'Réponse vide')
            return {"enhanced_answer": str(answer), "optional_clarifications": [], "method_used": "mock"}
    
    agent_contextualizer = MockAgent()
    agent_rag_enhancer = MockAgent()
    AGENTS_AVAILABLE = False

try:
    from .conversation_memory import IntelligentConversationMemory
    CONVERSATION_MEMORY_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    class MockConversationMemory:
        def get_conversation_context(self, conversation_id):
            return None
        
        async def add_message_to_conversation(self, *args, **kwargs):
            return True
        
        def mark_pending_clarification(self, conversation_id, question, critical_entities):
            return True
    
    CONVERSATION_MEMORY_AVAILABLE = False

try:
    from .expert_concision_service import ConcisionService
    CONCISION_SERVICE_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    class MockConcisionService:
        def generate_all_versions(self, text, language="fr"):
            if not text:
                text = "Réponse indisponible"
            words = text.split()
            return {
                "ultra_concise": " ".join(words[:10]) + ("..." if len(words) > 10 else ""),
                "concise": " ".join(words[:25]) + ("..." if len(words) > 25 else ""),
                "standard": " ".join(words[:50]) + ("..." if len(words) > 50 else ""),
                "detailed": text
            }
    
    CONCISION_SERVICE_AVAILABLE = False

# =============================================================================
# 🚀 SERVICE PRINCIPAL EXPERT AVEC INDENTATION CORRIGÉE v4.0.0
# =============================================================================

class ExpertService:
    """Service principal pour le système expert avec ALIGNMENT COMPLET v4.0.0"""
    
    def __init__(self):
        try:
            self.integrations = IntegrationsManager()
            
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
            
            # Initialiser la mémoire conversationnelle
            if CONVERSATION_MEMORY_AVAILABLE:
                try:
                    self.conversation_memory = IntelligentConversationMemory()
                    logger.info("✅ [Expert Service v4.0.0] Mémoire conversationnelle initialisée")
                except Exception as e:
                    logger.error(f"❌ [Expert Service v4.0.0] Erreur init mémoire: {e}")
                    self.conversation_memory = MockConversationMemory()
            else:
                self.conversation_memory = MockConversationMemory()
            
            # Initialiser le créateur de réponses
            self.response_creator = ExpertResponseCreator(self.concision_service)
            
            # Configuration
            self.config = {
                "enable_concise_responses": True,
                "default_concision_level": getattr(ConcisionLevel, 'CONCISE', 'concise'),
                "fallback_mode": not all([MODELS_AVAILABLE, INTEGRATIONS_AVAILABLE]),
                "critical_clarification_blocking": True,
                "optional_clarification_non_blocking": True,
                "agents_enabled": AGENTS_AVAILABLE,
                "conversation_memory_enabled": CONVERSATION_MEMORY_AVAILABLE,
                "concision_service_enabled": CONCISION_SERVICE_AVAILABLE or True,
                "safe_weight_access": True,
                "safe_missing_entities_access": True,
                "robust_memory_error_handling": True,
                "field_existence_verification": True,
                "response_object_validation": True,
                "alignment_expert_models": True
            }
            
            logger.info("🚀 [Expert Service v4.0.0] Service expert initialisé avec ALIGNMENT COMPLET")
            
        except Exception as e:
            logger.error(f"❌ [Expert Service v4.0.0] Erreur critique lors de l'initialisation: {e}")
            # Configuration d'urgence
            self.integrations = IntegrationsManager()
            self.conversation_memory = MockConversationMemory()
            self.concision_service = MockConcisionService()
            self.response_creator = ExpertResponseCreator(self.concision_service)
            self.config = {
                "enable_concise_responses": False,
                "fallback_mode": True,
                "critical_clarification_blocking": False,
                "agents_enabled": False,
                "conversation_memory_enabled": False,
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
                return self.response_creator.create_error_response(
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
            return self.response_creator.create_error_response(
                f"Erreur interne: {str(e)}", 
                self._extract_question_safe(request_data), 
                self._extract_conversation_id_safe(request_data), 
                self._extract_language_safe(request_data), 
                start_time
            )
    
    # === MÉTHODES D'EXTRACTION SÉCURISÉES ===
    
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
            else:
                return f"fallback_{uuid.uuid4().hex[:8]}"
        except Exception as e:
            logger.warning(f"⚠️ [ExpertService v4.0.0] Erreur extraction user_id: {e}")
            return f"error_{uuid.uuid4().hex[:8]}"
    
    # === PIPELINE PRINCIPAL SÉCURISÉ ===
    
    async def _process_question_critical_clarification_pipeline_safe(
        self, request_data, request, current_user, start_time, processing_steps, ai_enhancements_used,
        question_text, language, conversation_id, user_id
    ):
        """🛑 Pipeline avec clarification critique et GESTION ROBUSTE ERREURS MÉMOIRE v4.0.0"""
        
        try:
            logger.info("🛑 [ExpertService v4.0.0] Pipeline clarification critique activé")
            processing_steps.append("critical_clarification_pipeline_activated")
            
            # ANALYSE CLARIFICATION CRITIQUE AVANT RAG
            try:
                logger.info("🛑 [Pipeline v4.0.0] Analyse clarification critique AVANT RAG")
                
                clarification_result = await analyze_question_for_clarification_enhanced(question_text, language)
                
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
            return self.response_creator.create_error_response(
                str(e), question_text, conversation_id, language, start_time
            )
    
    async def _handle_critical_clarification_safe(
        self, clarification_result, question_text, conversation_id, language, 
        start_time, current_user, processing_steps, ai_enhancements_used
    ):
        """Gestion sécurisée clarification critique avec GESTION ROBUSTE MÉMOIRE"""
        try:
            # Validation missing_entities sécurisée
            raw_missing_critical = clarification_result.get("missing_critical_entities", [])
            missing_critical_entities = safe_get_missing_entities({"missing_entities": raw_missing_critical})
            
            # Marquage dans la mémoire avec GESTION ROBUSTE D'ERREURS
            if self.config["robust_memory_error_handling"]:
                try:
                    mark_success = safe_mark_pending_clarification(
                        self.conversation_memory, conversation_id, question_text, missing_critical_entities
                    )
                    
                    if mark_success:
                        logger.info(f"🧠 [Pipeline v4.0.0] Clarification critique marquée: {missing_critical_entities}")
                        processing_steps.append("memory_clarification_marked_success")
                    else:
                        logger.warning(f"⚠️ [Pipeline v4.0.0] Échec marquage clarification: {conversation_id}")
                        processing_steps.append("memory_clarification_marked_failed_non_blocking")
                        
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur marquage mémoire (NON BLOQUANT): {e}")
                    processing_steps.append("memory_clarification_error_non_blocking")
            
            # Générer message de clarification critique
            poultry_type = clarification_result.get("poultry_type", "unknown")
            critical_message = generate_critical_clarification_message_safe(
                missing_critical_entities, poultry_type, language
            )
            
            # Retourner la réponse de clarification
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return self.response_creator.create_critical_clarification_response(
                question_text, critical_message, conversation_id, language, response_time_ms,
                current_user, processing_steps, ai_enhancements_used, clarification_result
            )
            
        except Exception as e:
            logger.error(f"❌ [Handle Critical Clarification v4.0.0] Erreur: {e}")
            return self.response_creator.create_error_response(
                "Erreur lors de la clarification critique", question_text, 
                conversation_id, language, start_time
            )
    
    async def _process_normal_pipeline_safe(
        self, question_text, language, conversation_id, user_id, current_user,
        start_time, processing_steps, ai_enhancements_used, request, request_data
    ):
        """Pipeline normal avec GESTION ROBUSTE ERREURS MÉMOIRE et ALIGNMENT"""
        try:
            # Variables par défaut
            question_for_rag = question_text
            final_answer = ""
            rag_score = None
            mode = "unknown"
            optional_clarifications = []
            
            # Récupération contexte conversationnel avec GESTION ROBUSTE ERREURS
            conversation_context = None
            entities = {}
            missing_entities = []
            formatted_context = ""
            
            if self.config["robust_memory_error_handling"] and self.conversation_memory:
                try:
                    conversation_context = safe_get_conversation_context(self.conversation_memory, conversation_id)
                    
                    if conversation_context:
                        entities, missing_entities = safe_extract_entities_from_context(conversation_context)
                        
                        # Accès sécurisé weight avec validation
                        if self.config["safe_weight_access"]:
                            weight_value = safe_get_weight(entities)
                            weight_unit = safe_get_weight_unit(entities)
                            
                            if weight_value is not None:
                                logger.info(f"⚖️ [Pipeline v4.0.0] Weight récupéré: {weight_value} {weight_unit}")
                                weight_result = validate_and_normalize_weight(weight_value, weight_unit)
                                if weight_result["is_valid"]:
                                    entities["weight"] = weight_result["value"]
                                    entities["weight_unit"] = weight_result["unit"]
                        
                        logger.info(f"🧠 [Pipeline v4.0.0] Contexte récupéré: {len(entities)} entités")
                        processing_steps.append("conversation_context_retrieved_safe")
                    else:
                        logger.info("🆕 [Pipeline v4.0.0] Nouvelle conversation")
                        
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur récupération contexte (NON BLOQUANT): {e}")
                    processing_steps.append("context_retrieval_error_non_blocking")
            
            # Agent Contextualizer sécurisé
            contextualization_info = {}
            
            if self.config["agents_enabled"]:
                try:
                    logger.info("🤖 [Pipeline v4.0.0] Agent Contextualizer")
                    
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
            
            # Agent RAG Enhancer sécurisé
            enhancement_info = {}
            
            if self.config["agents_enabled"]:
                try:
                    logger.info("🔧 [Pipeline v4.0.0] Agent RAG Enhancer")
                    
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
            
            # Génération des versions de réponse
            response_versions = None
            try:
                if self.config["concision_service_enabled"] and final_answer:
                    response_versions = self.concision_service.generate_all_versions(final_answer, language)
                    processing_steps.append("response_versions_generated")
            except Exception as e:
                logger.error(f"❌ [Pipeline v4.0.0] Erreur génération versions: {e}")
            
            # Mise à jour mémoire avec GESTION ROBUSTE D'ERREURS
            if self.config["robust_memory_error_handling"] and self.conversation_memory:
                try:
                    user_message_success = await safe_add_message_to_memory(
                        self.conversation_memory, conversation_id, user_id, 
                        question_for_rag, "user", language
                    )
                    
                    assistant_message_success = await safe_add_message_to_memory(
                        self.conversation_memory, conversation_id, user_id, 
                        final_answer, "assistant", language
                    )
                    
                    if user_message_success and assistant_message_success:
                        processing_steps.append("conversation_memory_updated_success")
                        logger.info("✅ [Pipeline v4.0.0] Mémoire mise à jour avec succès")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline v4.0.0] Erreur mise à jour mémoire (NON BLOQUANT): {e}")
                    processing_steps.append("conversation_memory_error_non_blocking")
            
            # Construction réponse finale avec ALIGNMENT COMPLET
            response_time_ms = int((time.time() - start_time) * 1000)
            user_email = current_user.get("email") if current_user and isinstance(current_user, dict) else None
            
            return self.response_creator.create_enhanced_response_safe_aligned(
                question_text, final_answer, conversation_id, language, response_time_ms,
                user_email, processing_steps, ai_enhancements_used, rag_score, mode,
                contextualization_info, enhancement_info, optional_clarifications,
                conversation_context, entities, missing_entities, question_for_rag, response_versions
            )

        except Exception as e:
            logger.error(f"❌ [Normal Pipeline v4.0.0] Erreur: {e}")
            return self.response_creator.create_error_response(
                str(e), question_text, conversation_id, language, start_time
            )
    
    async def _process_question_fallback(self, question_text, conversation_id, language, user_email, start_time, processing_steps):
        """Pipeline de fallback sécurisé avec alignment"""
        try:
            logger.info("🔄 [ExpertService v4.0.0] Mode fallback complet activé")
            processing_steps.append("fallback_mode_complete_aligned")
            
            fallback_data = self._generate_fallback_responses_safe(question_text, language)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return self.response_creator.create_basic_response_safe_aligned(
                question_text, fallback_data["response"], conversation_id, 
                language, response_time_ms, processing_steps
            )
            
        except Exception as e:
            logger.error(f"❌ [Process Fallback v4.0.0] Erreur: {e}")
            return self.response_creator.create_error_response(
                "Erreur fallback", question_text, conversation_id, language, start_time
            )
    
    def _generate_fallback_responses_safe(self, question, language):
        """Génération de réponses de fallback sécurisées"""
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


# Instance globale du service expert
try:
    expert_service = ExpertService()
    logger.info("🎉 [Expert Services v4.0.0] Service expert global initialisé avec REFACTORISATION COMPLÈTE")
except Exception as e:
    logger.error(f"❌ [Expert Services v4.0.0] Erreur initialisation service global: {e}")
    expert_service = None

# Export des fonctions principales
__all__ = [
    'ExpertService',
    'expert_service'
]