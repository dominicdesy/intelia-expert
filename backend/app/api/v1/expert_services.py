"""
app/api/v1/expert_services.py - SERVICE PRINCIPAL EXPERT SYSTEM (RESTRUCTURÉ)

🚀 SERVICE PRINCIPAL:
- Orchestration de tous les services
- Traitement des questions avec auto-clarification
- Gestion RAG et contexte conversationnel
- Réponses enrichies avec toutes les améliorations
"""

import os
import logging
import uuid
import time
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

from fastapi import HTTPException, Request

from .expert_models import (
    EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest,
    ValidationResult, ProcessingContext, VaguenessResponse, ResponseFormat,
    ConcisionLevel, ConcisionMetrics, DynamicClarification
)
from .expert_utils import (
    get_user_id_from_request, 
    build_enriched_question_from_clarification,
    get_enhanced_topics_by_language,
    save_conversation_auto_enhanced,
    extract_breed_and_sex_from_clarification,
    build_enriched_question_with_breed_sex,
    validate_clarification_completeness  # ✅ CORRECTION: Import ajouté
)
from .expert_integrations import IntegrationsManager
from .api_enhancement_service import APIEnhancementService
from .prompt_templates import build_structured_prompt, extract_context_from_entities, validate_prompt_context, build_clarification_prompt

# Import des nouveaux services séparés
from .expert_concision_service import ResponseConcisionProcessor, ResponseVersionsGenerator
from .expert_clarification_service import (
    ExpertClarificationService, 
    auto_clarify_if_needed, 
    validate_dynamic_questions
)

logger = logging.getLogger(__name__)

# =============================================================================
# RAG CONTEXT ENHANCER
# =============================================================================

class RAGContextEnhancer:
    """Améliore le contexte conversationnel pour optimiser les requêtes RAG"""
    
    def __init__(self):
        self.pronoun_patterns = {
            "fr": [
                r'\b(son|sa|ses|leur|leurs)\s+(poids|âge|croissance|développement)',
                r'\b(ils|elles)\s+(pèsent|grandissent|se développent)',
                r'\b(qu\'?est-ce que|quel est)\s+(son|sa|ses|leur)',
                r'\b(combien)\s+(pèsent-ils|font-ils|mesurent-ils)'
            ],
            "en": [
                r'\b(their|its)\s+(weight|age|growth|development)',
                r'\b(they)\s+(weigh|grow|develop)',
                r'\b(what is|how much is)\s+(their|its)',
                r'\b(how much do they)\s+(weigh|measure)'
            ],
            "es": [
                r'\b(su|sus)\s+(peso|edad|crecimiento|desarrollo)',
                r'\b(ellos|ellas)\s+(pesan|crecen|se desarrollan)',
                r'\b(cuál es|cuánto es)\s+(su|sus)',
                r'\b(cuánto)\s+(pesan|miden)'
            ]
        }
    
    def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr"
    ) -> Tuple[str, Dict[str, any]]:
        """Améliore une question pour le RAG en utilisant le contexte conversationnel"""
        
        enhancement_info = {
            "pronoun_detected": False,
            "context_entities_used": [],
            "question_enriched": False,
            "original_question": question
        }
        
        has_pronouns = self._detect_contextual_references(question, language)
        if has_pronouns:
            enhancement_info["pronoun_detected"] = True
            logger.info(f"🔍 [RAG Context] Pronoms détectés dans: '{question}'")
        
        context_entities = self._extract_context_entities(conversation_context)
        if context_entities:
            enhancement_info["context_entities_used"] = list(context_entities.keys())
            logger.info(f"📊 [RAG Context] Entités contextuelles: {context_entities}")
        
        enriched_question = question
        
        if has_pronouns and context_entities:
            enriched_question = self._build_enriched_question(
                question, context_entities, language
            )
            enhancement_info["question_enriched"] = True
            logger.info(f"✨ [RAG Context] Question enrichie: '{enriched_question}'")
        
        if context_entities or has_pronouns:
            technical_context = self._build_technical_context(context_entities, language)
            if technical_context:
                enriched_question += f"\n\nContexte technique: {technical_context}"
        
        return enriched_question, enhancement_info
    
    def _detect_contextual_references(self, question: str, language: str) -> bool:
        """Détecte si la question contient des pronoms/références contextuelles"""
        
        patterns = self.pronoun_patterns.get(language, self.pronoun_patterns["fr"])
        question_lower = question.lower()
        
        for pattern in patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                logger.debug(f"🎯 [RAG Context] Pattern trouvé: {pattern}")
                return True
        
        return False
    
    def _extract_context_entities(self, context: str) -> Dict[str, str]:
        """Extrait les entités importantes du contexte conversationnel"""
        
        if not context:
            return {}
        
        entities = {}
        context_lower = context.lower()
        
        # Patterns pour races
        breed_patterns = [
            r'race[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)',
            r'breed[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)',
            r'(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)',
            r'poulets?\s+(ross\s*308|cobb\s*500)',
            r'chickens?\s+(ross\s*308|cobb\s*500)'
        ]
        
        for pattern in breed_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["breed"] = match.group(1).strip()
                break
        
        # Patterns pour sexe
        sex_patterns = [
            r'sexe[:\s]+([a-zA-Z\s]+?)(?:\n|,|\.|\s|$)',
            r'sex[:\s]+([a-zA-Z\s]+?)(?:\n|,|\.|\s|$)',
            r'\b(mâles?|femelles?|males?|females?|mixte|mixed)\b'
        ]
        
        for pattern in sex_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["sex"] = match.group(1).strip()
                break
        
        # Patterns pour âge
        age_patterns = [
            r'âge[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'age[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'(\d+)\s*(?:jour|day)s?',
            r'(\d+)\s*(?:semaine|week)s?'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["age"] = match.group(1).strip()
                break
        
        return entities
    
    def _build_enriched_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> str:
        """Construit une question enrichie en remplaçant les pronoms par les entités contextuelles"""
        
        enriched = question
        
        templates = {
            "fr": {
                "breed_sex_age": "Pour des {breed} {sex} de {age}",
                "breed_age": "Pour des {breed} de {age}",
                "breed_sex": "Pour des {breed} {sex}",
                "breed_only": "Pour des {breed}",
                "age_only": "Pour des poulets de {age}"
            },
            "en": {
                "breed_sex_age": "For {breed} {sex} chickens at {age}",
                "breed_age": "For {breed} chickens at {age}",
                "breed_sex": "For {breed} {sex} chickens",
                "breed_only": "For {breed} chickens", 
                "age_only": "For chickens at {age}"
            },
            "es": {
                "breed_sex_age": "Para pollos {breed} {sex} de {age}",
                "breed_age": "Para pollos {breed} de {age}",
                "breed_sex": "Para pollos {breed} {sex}",
                "breed_only": "Para pollos {breed}",
                "age_only": "Para pollos de {age}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        context_prefix = ""
        if "breed" in context_entities and "sex" in context_entities and "age" in context_entities:
            context_prefix = template_set["breed_sex_age"].format(
                breed=context_entities["breed"],
                sex=context_entities["sex"],
                age=context_entities["age"]
            )
        elif "breed" in context_entities and "age" in context_entities:
            context_prefix = template_set["breed_age"].format(
                breed=context_entities["breed"],
                age=context_entities["age"]
            )
        elif "breed" in context_entities and "sex" in context_entities:
            context_prefix = template_set["breed_sex"].format(
                breed=context_entities["breed"],
                sex=context_entities["sex"]
            )
        elif "breed" in context_entities:
            context_prefix = template_set["breed_only"].format(
                breed=context_entities["breed"]
            )
        elif "age" in context_entities:
            context_prefix = template_set["age_only"].format(age=context_entities["age"])
        
        if context_prefix:
            if any(word in question.lower() for word in ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]):
                enriched = f"{context_prefix}, {question.lower()}"
            else:
                enriched = f"{context_prefix}: {question}"
        
        return enriched
    
    def _build_technical_context(self, entities: Dict[str, str], language: str) -> str:
        """Construit un contexte technique pour aider le RAG"""
        
        if not entities:
            return ""
        
        context_parts = []
        
        if "breed" in entities:
            context_parts.append(f"Race: {entities['breed']}")
        
        if "sex" in entities:
            context_parts.append(f"Sexe: {entities['sex']}")
        
        if "age" in entities:
            context_parts.append(f"Âge: {entities['age']}")
        
        return " | ".join(context_parts)

# =============================================================================
# SERVICE PRINCIPAL EXPERT
# =============================================================================

class ExpertService:
    """Service principal pour le système expert avec auto-clarification simplifiée intégrée"""
    
    def __init__(self):
        self.integrations = IntegrationsManager()
        self.rag_enhancer = RAGContextEnhancer()
        self.enhancement_service = APIEnhancementService()
        
        # Services de concision et clarification
        self.concision_processor = ResponseConcisionProcessor()
        self.response_versions_generator = ResponseVersionsGenerator(
            existing_processor=self.concision_processor
        )
        self.clarification_service = ExpertClarificationService()
        
        logger.info("✅ [Expert Service] Service expert initialisé avec tous les modules")
    
    def get_current_user_dependency(self):
        """Retourne la dépendance pour l'authentification"""
        return self.integrations.get_current_user_dependency()
    
    async def process_expert_question(
        self,
        request_data: EnhancedQuestionRequest,
        request: Request,
        current_user: Optional[Dict[str, Any]] = None,
        start_time: float = None
    ) -> EnhancedExpertResponse:
        """Méthode principale avec auto-clarification intégrée"""
        
        if start_time is None:
            start_time = time.time()
        
        try:
            logger.info("🚀 [ExpertService] Traitement question avec auto-clarification")
            
            concision_level = getattr(request_data, 'concision_level', ConcisionLevel.CONCISE)
            generate_all_versions = getattr(request_data, 'generate_all_versions', True)
            semantic_dynamic_mode = getattr(request_data, 'semantic_dynamic_mode', False)
            
            logger.info(f"🚀 [ResponseVersions] Paramètres: level={concision_level}, generate_all={generate_all_versions}")
            logger.info(f"🆕 [Semantic Dynamic] Mode: {semantic_dynamic_mode}")
            
            # Traitement principal
            base_response = await self._process_question_with_auto_clarification(
                request_data, request, current_user, start_time, semantic_dynamic_mode
            )
            
            # Génération des versions de réponse si demandé
            if generate_all_versions and base_response.response:
                try:
                    logger.info("🚀 [ResponseVersions] Génération de toutes les versions")
                    
                    versions_result = await self.response_versions_generator.generate_all_response_versions(
                        original_response=base_response.response,
                        question=request_data.text,
                        context={
                            "language": request_data.language,
                            "user_id": current_user.get("id") if current_user else None,
                            "conversation_id": request_data.conversation_id
                        },
                        requested_level=concision_level
                    )
                    
                    base_response.response_versions = versions_result["response_versions"]
                    base_response.response = versions_result["selected_response"]
                    base_response.concision_metrics = versions_result["concision_metrics"]
                    
                    logger.info("✅ [ResponseVersions] Versions ajoutées à la réponse")
                    
                except Exception as e:
                    logger.warning(f"⚠️ [ResponseVersions] Erreur génération versions: {e}")
                    base_response.response_versions = None
            else:
                logger.info("🚀 [ResponseVersions] Génération versions désactivée")
                base_response.response_versions = None
            
            return base_response
            
        except Exception as e:
            logger.error(f"❌ [ExpertService] Erreur traitement avec auto-clarification: {e}")
            raise
    
    async def _process_question_with_auto_clarification(
        self,
        request_data: EnhancedQuestionRequest,
        request: Request,
        current_user: Optional[Dict[str, Any]] = None,
        start_time: float = None,
        semantic_dynamic_mode: bool = False
    ) -> EnhancedExpertResponse:
        """Logique avec auto-clarification intégrée au début"""
        
        processing_steps = []
        ai_enhancements_used = []
        debug_info = {}
        performance_breakdown = {"start": int(time.time() * 1000)}
        
        processing_steps.append("initialization")
        
        # === AUTHENTIFICATION ===
        if current_user is None and self.integrations.auth_available:
            raise HTTPException(status_code=401, detail="Authentification requise")
        
        user_id = self._extract_user_id(current_user, request_data, request)
        user_email = current_user.get("email") if current_user else None
        request_ip = request.client.host if request.client else "unknown"
        
        processing_steps.append("authentication")
        performance_breakdown["auth_complete"] = int(time.time() * 1000)
        
        # === GESTION CONVERSATION ID ===
        conversation_id = self._get_or_create_conversation_id(request_data)
        
        # === VALIDATION QUESTION ===
        question_text = request_data.text.strip()
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        processing_steps.append("question_validation")
        
        # === MÉMOIRE CONVERSATIONNELLE ===
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
                logger.info(f"💾 [Expert Service] Message ajouté à la mémoire: {question_text[:50]}...")
                
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur mémoire: {e}")
        
        performance_breakdown["memory_complete"] = int(time.time() * 1000)
        
        # === AUTO-CLARIFICATION INTÉGRÉE ===
        if not request_data.is_clarification_response:
            conversation_context_str = ""
            if conversation_context and hasattr(conversation_context, 'get_context_for_rag'):
                conversation_context_str = conversation_context.get_context_for_rag(max_chars=500)
            
            clarification_result = auto_clarify_if_needed(
                question_text, conversation_context_str, request_data.language
            )
            
            if clarification_result:
                logger.info("🔧 [Auto Clarification] Clarification déclenchée automatiquement")
                
                processing_steps.append("auto_clarification_triggered")
                ai_enhancements_used.append("auto_clarification_system")
                
                # Formater les questions
                if len(clarification_result["questions"]) == 1:
                    formatted_questions = clarification_result["questions"][0]
                else:
                    formatted_questions = "\n".join([f"• {q}" for q in clarification_result["questions"]])
                
                response_text = f"{clarification_result['message']}\n\n{formatted_questions}\n\nCela m'aidera à vous donner une réponse plus précise ! 🐔"
                
                response_time_ms = int((time.time() - start_time) * 1000)
                
                return EnhancedExpertResponse(
                    question=question_text,
                    response=response_text,
                    conversation_id=conversation_id,
                    rag_used=False,
                    rag_score=None,
                    timestamp=datetime.now().isoformat(),
                    language=request_data.language,
                    response_time_ms=response_time_ms,
                    mode="auto_clarification_triggered",
                    user=user_email,
                    logged=True,
                    validation_passed=True,
                    clarification_result={
                        "clarification_requested": True,
                        "clarification_type": "auto_triggered",
                        "completeness_score": clarification_result.get("completeness_score", 0.0),
                        "questions_generated": len(clarification_result["questions"]),
                        "generation_method": clarification_result.get("generation_method", "auto_clarification"),
                        "automatic_trigger": True
                    },
                    processing_steps=processing_steps,
                    ai_enhancements_used=ai_enhancements_used,
                    dynamic_clarification=DynamicClarification(
                        original_question=question_text,
                        clarification_questions=clarification_result["questions"],
                        confidence=0.8,
                        generation_method="auto_clarification_system",
                        generation_time_ms=response_time_ms,
                        fallback_used=False
                    )
                )
        
        # === VALIDATION AGRICOLE ===
        validation_result = await self._validate_agricultural_question(
            question_text, request_data.language, user_id, request_ip, conversation_id
        )
        
        processing_steps.append("agricultural_validation")
        performance_breakdown["validation_complete"] = int(time.time() * 1000)
        
        if not validation_result.is_valid:
            return self._create_rejection_response(
                question_text, validation_result, conversation_id, 
                user_email, request_data.language, start_time,
                processing_steps, ai_enhancements_used, None
            )
        
        # === SYSTÈME DE CLARIFICATION INTELLIGENT + SÉMANTIQUE DYNAMIQUE ===
        clarification_result = await self._handle_clarification_corrected_with_semantic_dynamic(
            request_data, question_text, user_id, conversation_id,
            processing_steps, ai_enhancements_used, semantic_dynamic_mode
        )
        
        if clarification_result:
            return clarification_result
        
        # Détection vagueness après clarifications spécialisées
        vagueness_result = None
        if request_data.enable_vagueness_detection:
            vagueness_result = self.enhancement_service.detect_vagueness(
                question_text, request_data.language
            )
            
            ai_enhancements_used.append("vagueness_detection")
            performance_breakdown["vagueness_check"] = int(time.time() * 1000)
            
            if vagueness_result.is_vague and vagueness_result.vagueness_score > 0.6:
                logger.info(f"🎯 [Expert Service] Question floue détectée (score: {vagueness_result.vagueness_score})")
                return self._create_vagueness_response(
                    vagueness_result, question_text, conversation_id, 
                    request_data.language, start_time, processing_steps, ai_enhancements_used
                )
        
        performance_breakdown["clarification_complete"] = int(time.time() * 1000)
        
        # === TRAITEMENT EXPERT AVEC RAG-FIRST + AMÉLIORATIONS + TAXONOMIC FILTERING ===
        expert_result = await self._process_expert_response_enhanced_corrected_with_taxonomy(
            question_text, request_data, request, current_user,
            conversation_id, processing_steps, ai_enhancements_used,
            debug_info, performance_breakdown, vagueness_result
        )
        
        # === APPLICATION DU SYSTÈME DE CONCISION EXISTANT ===
        if expert_result["answer"] and self.concision_processor.config.ENABLE_CONCISE_RESPONSES:
            
            user_concision_preference = getattr(request_data, 'concision_level', None)
            
            original_answer = expert_result["answer"]
            processed_answer = self.concision_processor.process_response(
                response=original_answer,
                question=question_text,
                concision_level=user_concision_preference,
                language=request_data.language
            )
            
            if processed_answer != original_answer:
                expert_result["answer"] = processed_answer
                expert_result["original_answer"] = original_answer
                expert_result["concision_applied"] = True
                ai_enhancements_used.append("response_concision")
                processing_steps.append("concision_processing")
                
                logger.info(f"✂️ [Expert Service] Concision appliquée: {len(original_answer)} → {len(processed_answer)} chars")
            else:
                expert_result["concision_applied"] = False
        
        performance_breakdown["concision_complete"] = int(time.time() * 1000)
        
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
        performance_breakdown["final"] = int(time.time() * 1000)
        
        # === CONSTRUCTION RÉPONSE FINALE AMÉLIORÉE ===
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return self._build_final_enhanced_response(
            question_text, expert_result["answer"], conversation_id,
            user_email, request_data.language, response_time_ms,
            expert_result, validation_result, conversation_context,
            processing_steps, ai_enhancements_used, request_data,
            debug_info, performance_breakdown
        )
    
    # =============================================================================
    # MÉTHODES DE TRAITEMENT RAG ET CONTEXTE
    # =============================================================================
    
    async def _process_expert_response_enhanced_corrected_with_taxonomy(
        self, question_text: str, request_data: EnhancedQuestionRequest,
        request: Request, current_user: Optional[Dict], conversation_id: str,
        processing_steps: list, ai_enhancements_used: list,
        debug_info: Dict, performance_breakdown: Dict, vagueness_result = None
    ) -> Dict[str, Any]:
        """RAG parfaitement corrigé avec mémoire intelligente + FILTRAGE TAXONOMIQUE"""
        
        # === 1. RÉCUPÉRATION FORCÉE DU CONTEXTE CONVERSATIONNEL ===
        conversation_context_str = ""
        extracted_entities = {}
        
        if self.integrations.intelligent_memory_available:
            try:
                context_obj = self.integrations.get_conversation_context(conversation_id)
                if context_obj:
                    conversation_context_str = context_obj.get_context_for_rag(max_chars=800)
                    
                    if request_data.is_clarification_response or request_data.original_question:
                        if request_data.original_question:
                            conversation_context_str = f"Question originale: {request_data.original_question}. " + conversation_context_str
                        
                        if hasattr(context_obj, 'messages'):
                            for msg in reversed(context_obj.messages[-5:]):
                                if msg.role == "user" and any(word in msg.message.lower() for word in ["ross", "cobb", "hubbard", "mâle", "femelle", "male", "female"]):
                                    conversation_context_str += f" | Clarification: {msg.message}"
                                    break
                    
                    if hasattr(context_obj, 'consolidated_entities'):
                        extracted_entities = context_obj.consolidated_entities.to_dict()
                    
                    logger.info(f"🧠 [Expert Service] Contexte enrichi récupéré: {conversation_context_str[:150]}...")
                    ai_enhancements_used.append("intelligent_memory_context_retrieval")
                else:
                    logger.warning(f"⚠️ [Expert Service] Aucun contexte trouvé pour: {conversation_id}")
                    
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur récupération contexte: {e}")
        
        performance_breakdown["context_retrieved"] = int(time.time() * 1000)
        
        # === 2. AMÉLIORATION INTELLIGENTE DE LA QUESTION ===
        enriched_question, enhancement_info = self.rag_enhancer.enhance_question_for_rag(
            question=question_text,
            conversation_context=conversation_context_str,
            language=request_data.language
        )
        
        if request_data.original_question and request_data.is_clarification_response:
            logger.info(f"✨ [Expert Service] Question déjà enrichie par clarification: {question_text[:100]}...")
            ai_enhancements_used.append("clarification_based_enrichment")
        
        if enhancement_info["question_enriched"]:
            ai_enhancements_used.append("intelligent_question_enhancement")
            logger.info(f"✨ [Expert Service] Question améliorée: {enriched_question[:150]}...")
        
        if enhancement_info["pronoun_detected"]:
            ai_enhancements_used.append("contextual_pronoun_resolution")
            logger.info(f"🎯 [Expert Service] Pronoms contextuels résolus: {enhancement_info['context_entities_used']}")
        
        processing_steps.append("intelligent_question_enhancement")
        performance_breakdown["question_enhanced"] = int(time.time() * 1000)
        
        # === 3. FILTRAGE TAXONOMIQUE INTELLIGENT ===
        from .api_enhancement_service import infer_taxonomy_from_entities, enhance_rag_query_with_taxonomy
        
        taxonomy = infer_taxonomy_from_entities(extracted_entities)
        enhanced_question_with_taxonomy, rag_filters = enhance_rag_query_with_taxonomy(
            enriched_question, extracted_entities, request_data.language
        )
        
        logger.info(f"🏷️ [Taxonomy Filter] Taxonomie détectée: {taxonomy}")
        if rag_filters:
            logger.info(f"🏷️ [Taxonomy Filter] Filtres RAG: {rag_filters}")
            ai_enhancements_used.append("taxonomic_document_filtering")
        
        processing_steps.append("taxonomic_analysis_and_filtering")
        performance_breakdown["taxonomy_analysis"] = int(time.time() * 1000)
        
        # === 4. VÉRIFICATION RAG DISPONIBLE ===
        app = request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if not process_rag:
            logger.error("❌ [Expert Service] Système RAG indisponible - Erreur critique")
            raise HTTPException(
                status_code=503, 
                detail="Service RAG indisponible - Le système expert nécessite l'accès à la base documentaire"
            )
        
        # === 5. APPEL RAG AVEC CONTEXTE FORCÉ + FILTRAGE TAXONOMIQUE ===
        try:
            logger.info("🔍 [Expert Service] Appel RAG avec contexte intelligent + taxonomie...")
            
            if request_data.debug_mode:
                debug_info["original_question"] = question_text
                debug_info["enriched_question"] = enriched_question
                debug_info["enriched_question_with_taxonomy"] = enhanced_question_with_taxonomy
                debug_info["conversation_context"] = conversation_context_str
                debug_info["enhancement_info"] = enhancement_info
                debug_info["taxonomy_detected"] = taxonomy
                debug_info["rag_filters"] = rag_filters
            
            result = None
            rag_call_method = "unknown"
            
            rag_context = extract_context_from_entities(extracted_entities)
            rag_context["lang"] = request_data.language
            rag_context["taxonomy"] = taxonomy
            
            # Tentative 1: Avec paramètre context + filtres taxonomiques si supporté
            try:
                structured_question = build_structured_prompt(
                    documents="[DOCUMENTS_WILL_BE_INSERTED_BY_RAG]",
                    question=enhanced_question_with_taxonomy,
                    context=rag_context
                )
                
                logger.debug(f"🔍 [Prompt Final RAG] Contexte: {rag_context}")
                logger.debug(f"🏷️ [Prompt Final RAG] Taxonomie: {taxonomy}")
                logger.debug(f"🔍 [Prompt Final RAG]\n{structured_question[:500]}...")
                
                rag_params = {
                    "question": structured_question,
                    "user": current_user,
                    "language": request_data.language,
                    "speed_mode": request_data.speed_mode,
                    "context": conversation_context_str
                }
                
                if rag_filters:
                    try:
                        rag_params["filters"] = rag_filters
                        result = await process_rag(**rag_params)
                        rag_call_method = "context_parameter_structured_with_taxonomy"
                        logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte + filtres taxonomiques")
                    except TypeError:
                        del rag_params["filters"]
                        result = await process_rag(**rag_params)
                        rag_call_method = "context_parameter_structured_taxonomy_fallback"
                        logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte (filtres taxonomiques non supportés)")
                else:
                    result = await process_rag(**rag_params)
                    rag_call_method = "context_parameter_structured"
                    logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte")
                    
            except TypeError as te:
                logger.info(f"ℹ️ [Expert Service] Paramètre context non supporté: {te}")
                
                if conversation_context_str:
                    structured_question = build_structured_prompt(
                        documents="[DOCUMENTS_WILL_BE_INSERTED_BY_RAG]",
                        question=enhanced_question_with_taxonomy,
                        context=rag_context
                    )
                    
                    logger.debug(f"🔍 [Prompt Final RAG - Injecté + Taxonomie]\n{structured_question[:500]}...")
                    
                    contextual_question = f"{structured_question}\n\nContexte: {conversation_context_str}"
                    result = await process_rag(
                        question=contextual_question,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode
                    )
                    rag_call_method = "context_injected_structured_with_taxonomy"
                    logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte injecté + taxonomie")
                else:
                    structured_question = build_structured_prompt(
                        documents="[DOCUMENTS_WILL_BE_INSERTED_BY_RAG]",
                        question=enhanced_question_with_taxonomy,
                        context=rag_context
                    )
                    
                    logger.debug(f"🔍 [Prompt Final RAG - Seul + Taxonomie]\n{structured_question[:500]}...")
                    
                    result = await process_rag(
                        question=structured_question,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode
                    )
                    rag_call_method = "structured_with_taxonomy_only"
                    logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + taxonomie seul")
            
            performance_breakdown["rag_complete"] = int(time.time() * 1000)
            
            # === 6. TRAITEMENT RÉSULTAT RAG ===
            answer = str(result.get("response", ""))
            
            answer = self.concision_processor._clean_document_references_only(answer)
            
            rag_score = result.get("score", 0.0)
            original_mode = result.get("mode", "rag_processing")
            
            quality_check = self._validate_rag_response_quality(
                answer, enhanced_question_with_taxonomy, enhancement_info
            )
            
            if not quality_check["valid"]:
                logger.warning(f"⚠️ [Expert Service] Qualité RAG insuffisante: {quality_check['reason']}")
                ai_enhancements_used.append("quality_validation_failed")
            
            logger.info(f"✅ [Expert Service] RAG réponse reçue: {len(answer)} caractères, score: {rag_score}")
            
            mode = f"enhanced_contextual_{original_mode}_{rag_call_method}_corrected_with_concision_and_response_versions_and_taxonomy_and_semantic_dynamic_and_auto_clarification_simplified"
            
            processing_steps.append("mandatory_rag_with_intelligent_context_and_taxonomy")
            
            return {
                "answer": answer,
                "rag_used": True,
                "rag_score": rag_score,
                "mode": mode,
                "context_used": bool(conversation_context_str),
                "question_enriched": enhancement_info["question_enriched"] or bool(request_data.original_question),
                "enhancement_info": enhancement_info,
                "quality_check": quality_check,
                "extracted_entities": extracted_entities,
                "rag_call_method": rag_call_method,
                "taxonomy_used": taxonomy,
                "taxonomy_filters_applied": bool(rag_filters)
            }
            
        except Exception as rag_error:
            logger.error(f"❌ [Expert Service] Erreur critique RAG: {rag_error}")
            processing_steps.append("rag_error")
            
            error_details = {
                "error": "Erreur RAG",
                "message": "Impossible d'interroger la base documentaire",
                "question_original": question_text,
                "question_enriched": enriched_question,
                "question_with_taxonomy": enhanced_question_with_taxonomy,
                "context_available": bool(conversation_context_str),
                "taxonomy_detected": taxonomy,
                "technical_error": str(rag_error)
            }
            
            raise HTTPException(status_code=503, detail=error_details)
    
    # =============================================================================
    # MÉTHODES DE CLARIFICATION ET VALIDATION
    # =============================================================================
    
    async def _handle_clarification_corrected_with_semantic_dynamic(
        self, request_data, question_text, user_id, conversation_id, 
        processing_steps, ai_enhancements_used, semantic_dynamic_mode: bool = False
    ):
        """Système de clarification parfaitement corrigé + MODE SÉMANTIQUE DYNAMIQUE"""
        
        # 1. TRAITEMENT DES RÉPONSES DE CLARIFICATION CORRIGÉ
        if request_data.is_clarification_response:
            return await self._process_clarification_response_corrected(
                request_data, question_text, conversation_id,
                processing_steps, ai_enhancements_used
            )
        
        # 2. MODE SÉMANTIQUE DYNAMIQUE
        if semantic_dynamic_mode and self.integrations.enhanced_clarification_available:
            logger.info(f"🆕 [Semantic Dynamic] Mode activé pour: '{question_text[:50]}...'")
            
            try:
                from .question_clarification_system import analyze_question_for_clarification_semantic_dynamic
                
                clarification_result = await analyze_question_for_clarification_semantic_dynamic(
                    question=question_text,
                    language=request_data.language,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_context={}
                )
                
                if clarification_result.needs_clarification:
                    logger.info(f"🆕 [Semantic Dynamic] {len(clarification_result.questions)} questions générées")
                    processing_steps.append("semantic_dynamic_clarification_triggered")
                    ai_enhancements_used.append("semantic_dynamic_clarification")
                    
                    return self.clarification_service.create_semantic_dynamic_clarification_response(
                        question_text, clarification_result, request_data.language, conversation_id
                    )
                else:
                    logger.info(f"✅ [Semantic Dynamic] Question claire, pas de clarification nécessaire")
                
            except Exception as e:
                logger.error(f"❌ [Semantic Dynamic] Erreur mode sémantique: {e}")
        
        # 3. DÉTECTION QUESTIONS NÉCESSITANT CLARIFICATION (mode normal)
        clarification_needed = self.clarification_service.detect_performance_question_needing_clarification(
            question_text, request_data.language
        )
        
        if not clarification_needed:
            return None
        
        logger.info(f"🎯 [Expert Service] Clarification nécessaire: {clarification_needed['type']}")
        processing_steps.append("automatic_clarification_triggered")
        ai_enhancements_used.append("smart_performance_clarification")
        
        # 4. SAUVEGARDE FORCÉE AVEC MÉMOIRE INTELLIGENTE
        if self.integrations.intelligent_memory_available:
            try:
                from .conversation_memory_enhanced import mark_question_for_clarification
                
                question_id = mark_question_for_clarification(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    original_question=question_text,
                    language=request_data.language
                )
                
                logger.info(f"💾 [Expert Service] Question originale marquée: {question_id}")
                processing_steps.append("original_question_marked")
                ai_enhancements_used.append("intelligent_memory_clarification_marking")
                
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur marquage question: {e}")
                self.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=f"ORIGINAL_QUESTION_FOR_CLARIFICATION: {question_text}",
                    role="system",
                    language=request_data.language,
                    message_type="original_question_marker"
                )
        
        # 5. Générer la demande de clarification
        clarification_response = self.clarification_service.generate_performance_clarification_response(
            question_text, clarification_needed, request_data.language, conversation_id
        )
        
        return clarification_response
    
    async def _process_clarification_response_corrected(
        self, request_data, question_text, conversation_id, 
        processing_steps, ai_enhancements_used
    ):
        """Traitement des réponses de clarification - VERSION CORRIGÉE FINALE"""
        
        original_question = request_data.original_question
        clarification_context = request_data.clarification_context
        
        if (not original_question or not clarification_context) and self.integrations.intelligent_memory_available:
            try:
                from .conversation_memory_enhanced import find_original_question
                
                original_msg = find_original_question(conversation_id)
                
                if original_msg:
                    original_question = original_msg.message
                    clarification_context = {
                        "missing_information": ["breed", "sex"],
                        "clarification_type": "performance_breed_sex"
                    }
                    logger.info(f"✅ [Expert Service] Question originale récupérée: {original_question}")
                    ai_enhancements_used.append("intelligent_memory_original_question_recovery")
                else:
                    logger.warning("⚠️ [Expert Service] Question originale non trouvée dans la mémoire")
                    
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur récupération question originale: {e}")
        
        if not original_question:
            logger.warning("⚠️ [Expert Service] Fallback: création question par défaut")
            original_question = "Quel est le poids de référence pour ces poulets ?"
            clarification_context = {
                "missing_information": ["breed", "sex"],
                "clarification_type": "performance_breed_sex_fallback"
            }
        
        missing_info = clarification_context.get("missing_information", [])
        
        validation = validate_clarification_completeness(
            question_text, missing_info, request_data.language
        )
        
        if not validation["is_complete"]:
            logger.info(f"🔄 [Expert Service] Clarification incomplète: {validation['still_missing']}")
            return self._generate_follow_up_clarification(
                question_text, validation, request_data.language, conversation_id
            )
        
        breed = validation["extracted_info"].get("breed")
        sex = validation["extracted_info"].get("sex")
        
        age_info = self._extract_age_from_original_question(original_question, request_data.language)
        
        enriched_original_question = self._build_complete_enriched_question(
            original_question, breed, sex, age_info, request_data.language
        )
        
        logger.info(f"✅ [Expert Service] Question COMPLÈTEMENT enrichie: {enriched_original_question}")
        
        request_data.text = enriched_original_question
        request_data.is_clarification_response = False
        request_data.original_question = original_question
        
        processing_steps.append("clarification_processed_successfully_with_age")
        ai_enhancements_used.append("breed_sex_age_extraction_complete")
        ai_enhancements_used.append("complete_question_enrichment")
        ai_enhancements_used.append("forced_question_replacement_with_age")
        
        return None
    
    # =============================================================================
    # MÉTHODES UTILITAIRES ET DE CONSTRUCTION DE RÉPONSE
    # =============================================================================
    
    def _extract_user_id(self, current_user: Optional[Dict], request_data: EnhancedQuestionRequest, request: Request) -> str:
        if current_user:
            return current_user.get("user_id") or request_data.user_id or "authenticated_user"
        return request_data.user_id or get_user_id_from_request(request)
    
    def _get_or_create_conversation_id(self, request_data: EnhancedQuestionRequest) -> str:
        if request_data.conversation_id and request_data.conversation_id.strip():
            conversation_id = request_data.conversation_id.strip()
            logger.info(f"🔄 [Expert Service] CONTINUATION: {conversation_id}")
            return conversation_id
        else:
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 [Expert Service] NOUVELLE: {conversation_id}")
            return conversation_id
    
    def _validate_rag_response_quality(
        self, answer: str, enriched_question: str, enhancement_info: Dict
    ) -> Dict[str, any]:
        """Valide la qualité de la réponse RAG"""
        
        if not answer or len(answer.strip()) < 20:
            return {
                "valid": False,
                "reason": "Réponse trop courte",
                "answer_length": len(answer) if answer else 0
            }
        
        negative_responses = [
            "je ne sais pas", "i don't know", "no sé",
            "pas d'information", "no information", "sin información"
        ]
        
        answer_lower = answer.lower()
        for negative in negative_responses:
            if negative in answer_lower:
                return {
                    "valid": False,
                    "reason": f"Réponse négative détectée: {negative}",
                    "answer_length": len(answer)
                }
        
        if any(word in enriched_question.lower() for word in ["poids", "weight", "peso"]):
            if not re.search(r'\d+', answer):
                return {
                    "valid": False,
                    "reason": "Question numérique mais pas de chiffres dans la réponse",
                    "answer_length": len(answer)
                }
        
        return {
            "valid": True,
            "reason": "Réponse valide",
            "answer_length": len(answer)
        }
    
    def _build_final_enhanced_response(
        self, question_text: str, answer: str, conversation_id: str,
        user_email: Optional[str], language: str, response_time_ms: int,
        expert_result: Dict, validation_result: ValidationResult,
        conversation_context: Any, processing_steps: list,
        ai_enhancements_used: list, request_data: EnhancedQuestionRequest,
        debug_info: Dict, performance_breakdown: Dict
    ) -> EnhancedExpertResponse:
        """Construit la réponse finale avec toutes les améliorations"""
        
        extracted_entities = expert_result.get("extracted_entities")
        confidence_overall = None
        conversation_state = None
        
        if conversation_context and hasattr(conversation_context, 'consolidated_entities'):
            if not extracted_entities:
                extracted_entities = conversation_context.consolidated_entities.to_dict()
            confidence_overall = conversation_context.consolidated_entities.confidence_overall
            conversation_state = conversation_context.conversation_urgency
        
        final_debug_info = None
        final_performance = None
        
        if request_data.debug_mode:
            final_debug_info = {
                **debug_info,
                "total_processing_time_ms": response_time_ms,
                "ai_enhancements_count": len(ai_enhancements_used),
                "processing_steps_count": len(processing_steps),
                "concision_applied": expert_result.get("concision_applied", False),
                "response_versions_support": True,
                "taxonomy_used": expert_result.get("taxonomy_used"),
                "taxonomy_filters_applied": expert_result.get("taxonomy_filters_applied", False),
                "semantic_dynamic_available": True,
                "auto_clarification_simplified": True
            }
            
            final_performance = performance_breakdown
        
        concision_info = {
            "concision_applied": expert_result.get("concision_applied", False),
            "original_response_available": "original_answer" in expert_result,
            "detected_question_type": None,
            "applied_concision_level": None,
            "response_versions_supported": True
        }
        
        if expert_result.get("concision_applied"):
            concision_info["detected_question_type"] = self.concision_processor.detect_question_type(question_text)
            concision_info["applied_concision_level"] = self.concision_processor.detect_optimal_concision_level(question_text).value
        
        taxonomy_info = {
            "taxonomy_detected": expert_result.get("taxonomy_used", "general"),
            "taxonomy_filters_applied": expert_result.get("taxonomy_filters_applied", False),
            "taxonomy_enhanced_question": bool(expert_result.get("taxonomy_used") != "general")
        }
        
        semantic_dynamic_info = {
            "semantic_dynamic_available": getattr(request_data, 'semantic_dynamic_mode', False),
            "semantic_dynamic_used": "semantic_dynamic_clarification" in ai_enhancements_used,
            "dynamic_questions_generated": any("semantic_dynamic" in step for step in processing_steps)
        }
        
        auto_clarification_info = {
            "auto_clarification_simplified": True,
            "auto_clarification_used": "auto_clarification_system" in ai_enhancements_used,
            "auto_clarification_trigger": "auto_clarification_triggered" in processing_steps,
            "completeness_scoring_used": True,
            "validation_robuste_active": True,
            "fallback_intelligent_active": True
        }
            
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
            ai_enhancements_used=ai_enhancements_used,
            
            document_relevance=expert_result.get("document_relevance"),
            context_coherence=expert_result.get("context_coherence"),
            vagueness_detection=None,
            fallback_details=None,
            response_format_applied=request_data.expected_response_format.value,
            quality_metrics=expert_result.get("quality_metrics"),
            debug_info=final_debug_info,
            performance_breakdown=final_performance,
            
            concision_info=concision_info,
            original_response=expert_result.get("original_answer"),
            
            response_versions=None,
            concision_metrics=None,
            
            taxonomy_info=taxonomy_info,
            semantic_dynamic_info=semantic_dynamic_info,
            auto_clarification_info=auto_clarification_info
        )
    
    # =============================================================================
    # MÉTHODES ADDITIONNELLES (STUBS - À IMPLÉMENTER SI NÉCESSAIRE)
    # =============================================================================
    
    async def _validate_agricultural_question(self, question: str, language: str, user_id: str, request_ip: str, conversation_id: str) -> ValidationResult:
        if not self.integrations.agricultural_validator_available:
            return ValidationResult(is_valid=False, rejection_message="Service temporairement indisponible")
        
        try:
            enriched_question = question
            if self.integrations.intelligent_memory_available:
                try:
                    rag_context = self.integrations.get_context_for_rag(conversation_id)
                    if rag_context:
                        enriched_question = f"{question}\n\nContexte: {rag_context}"
                except Exception:
                    pass
            
            validation_result = self.integrations.validate_agricultural_question(
                question=enriched_question, language=language, user_id=user_id, request_ip=request_ip
            )
            
            return ValidationResult(
                is_valid=validation_result.is_valid,
                rejection_message=validation_result.reason or "Question hors domaine agricole",
                confidence=validation_result.confidence
            )
            
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur validateur: {e}")
            return ValidationResult(is_valid=False, rejection_message="Erreur de validation")
    
    def _create_rejection_response(self, question_text, validation_result, conversation_id, user_email, language, start_time, processing_steps, ai_enhancements_used, vagueness_result=None):
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return EnhancedExpertResponse(
            question=str(question_text),
            response=str(validation_result.rejection_message),
            conversation_id=conversation_id,
            rag_used=False,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode="enhanced_agricultural_validation_rejected",
            user=user_email,
            logged=True,
            validation_passed=False,
            validation_confidence=validation_result.confidence,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used,
            vagueness_detection=vagueness_result
        )
    
    def _create_vagueness_response(
        self, vagueness_result, question_text: str, conversation_id: str,
        language: str, start_time: float, processing_steps: list, ai_enhancements_used: list
    ) -> EnhancedExpertResponse:
        """Crée une réponse spécialisée pour questions floues"""
        
        clarification_messages = {
            "fr": f"Votre question semble manquer de précision. {vagueness_result.suggested_clarification or 'Pouvez-vous être plus spécifique ?'}",
            "en": f"Your question seems to lack precision. {vagueness_result.suggested_clarification or 'Could you be more specific?'}",
            "es": f"Su pregunta parece carecer de precisión. {vagueness_result.suggested_clarification or '¿Podría ser más específico?'}"
        }
        
        response_message = clarification_messages.get(language, clarification_messages["fr"])
        
        if vagueness_result.question_clarity in ["very_unclear", "unclear"]:
            examples = {
                "fr": "\n\nExemples de questions précises:\n• Quel est le poids normal d'un Ross 308 de 21 jours?\n• Comment traiter la mortalité élevée chez des poulets de 3 semaines?\n• Quelle température maintenir pour des poussins de 7 jours?",
                "en": "\n\nExamples of precise questions:\n• What is the normal weight of a 21-day Ross 308?\n• How to treat high mortality in 3-week-old chickens?\n• What temperature to maintain for 7-day chicks?",
                "es": "\n\nEjemplos de preguntas precisas:\n• ¿Cuál es el peso normal de un Ross 308 de 21 días?\n• ¿Cómo tratar la alta mortalidad en pollos de 3 semanas?\n• ¿Qué temperatura mantener para pollitos de 7 días?"
            }
            response_message += examples.get(language, examples["fr"])
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return EnhancedExpertResponse(
            question=question_text,
            response=response_message,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode="vagueness_clarification",
            user=None,
            logged=True,
            validation_passed=True,
            vagueness_detection=vagueness_result,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used
        )
    
    def _generate_follow_up_clarification(
        self, question: str, validation: Dict, language: str, conversation_id: str
    ) -> EnhancedExpertResponse:
        """Génère une clarification de suivi si première réponse incomplète"""
        
        still_missing = validation["still_missing"]
        
        messages = {
            "fr": {
                "breed": "Il me manque encore la **race/souche**. Ross 308, Cobb 500, ou autre ?",
                "sex": "Il me manque encore le **sexe**. Mâles, femelles, ou troupeau mixte ?",  
                "both": "Il me manque encore la **race et le sexe**. Exemple : \"Ross 308 mâles\""
            },
            "en": {
                "breed": "I still need the **breed/strain**. Ross 308, Cobb 500, or other?",
                "sex": "I still need the **sex**. Males, females, or mixed flock?",
                "both": "I still need the **breed and sex**. Example: \"Ross 308 males\""
            },
            "es": {
                "breed": "Aún necesito la **raza/cepa**. ¿Ross 308, Cobb 500, u otra?",
                "sex": "Aún necesito el **sexo**. ¿Machos, hembras, o lote mixto?",
                "both": "Aún necesito la **raza y sexo**. Ejemplo: \"Ross 308 machos\""
            }
        }
        
        lang_messages = messages.get(language, messages["fr"])
        
        if len(still_missing) >= 2:
            message = lang_messages["both"]
        elif "breed" in still_missing:
            message = lang_messages["breed"]
        else:
            message = lang_messages["sex"]
        
        return EnhancedExpertResponse(
            question=question,
            response=message,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=30,
            mode="follow_up_clarification_corrected",
            user=None,
            logged=True,
            validation_passed=True,
            clarification_result={
                "clarification_requested": True,
                "clarification_type": "follow_up_incomplete",
                "still_missing_information": still_missing,
                "confidence": validation["confidence"]
            },
            processing_steps=["follow_up_clarification_triggered"],
            ai_enhancements_used=["incomplete_clarification_handling"]
        )
    
    def _extract_age_from_original_question(self, original_question: str, language: str = "fr") -> Dict[str, Any]:
        """Extrait l'âge depuis la question originale"""
        
        age_info = {"days": None, "weeks": None, "text": None, "detected": False}
        
        if not original_question:
            return age_info
        
        question_lower = original_question.lower()
        
        age_patterns = {
            "fr": [
                (r'(\d+)\s*jours?', "days"),
                (r'(\d+)\s*semaines?', "weeks"),
                (r'de\s+(\d+)\s*jours?', "days"),
                (r'de\s+(\d+)\s*semaines?', "weeks"),
                (r'à\s+(\d+)\s*jours?', "days"),
                (r'à\s+(\d+)\s*semaines?', "weeks")
            ],
            "en": [
                (r'(\d+)\s*days?', "days"),
                (r'(\d+)\s*weeks?', "weeks"),
                (r'of\s+(\d+)\s*days?', "days"),
                (r'of\s+(\d+)\s*weeks?', "weeks"),
                (r'at\s+(\d+)\s*days?', "days"),
                (r'at\s+(\d+)\s*weeks?', "weeks")
            ],
            "es": [
                (r'(\d+)\s*días?', "days"),
                (r'(\d+)\s*semanas?', "weeks"),
                (r'de\s+(\d+)\s*días?', "days"),
                (r'de\s+(\d+)\s*semanas?', "weeks"),
                (r'a\s+(\d+)\s*días?', "days"),
                (r'a\s+(\d+)\s*semanas?', "weeks")
            ]
        }
        
        patterns = age_patterns.get(language, age_patterns["fr"])
        
        for pattern, unit in patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                
                if unit == "days":
                    age_info["days"] = value
                    age_info["weeks"] = round(value / 7, 1)
                    age_info["text"] = f"{value} jour{'s' if value > 1 else ''}"
                else:
                    age_info["weeks"] = value
                    age_info["days"] = value * 7
                    age_info["text"] = f"{value} semaine{'s' if value > 1 else ''}"
                
                age_info["detected"] = True
                
                logger.info(f"🕐 [Age Extraction] Âge détecté: {age_info['text']} ({age_info['days']} jours)")
                break
        
        if not age_info["detected"]:
            logger.warning(f"⚠️ [Age Extraction] Aucun âge détecté dans: {original_question}")
        
        return age_info

    def _build_complete_enriched_question(
        self, 
        original_question: str, 
        breed: Optional[str], 
        sex: Optional[str], 
        age_info: Dict[str, Any], 
        language: str = "fr"
    ) -> str:
        """Construit une question complètement enrichie"""
        
        templates = {
            "fr": {
                "complete": "Pour des poulets {breed} {sex} de {age}",
                "breed_age": "Pour des poulets {breed} de {age}",
                "sex_age": "Pour des poulets {sex} de {age}",
                "breed_sex": "Pour des poulets {breed} {sex}",
                "age_only": "Pour des poulets de {age}",
                "breed_only": "Pour des poulets {breed}",
                "sex_only": "Pour des poulets {sex}"
            },
            "en": {
                "complete": "For {breed} {sex} chickens at {age}",
                "breed_age": "For {breed} chickens at {age}",
                "sex_age": "For {sex} chickens at {age}",
                "breed_sex": "For {breed} {sex} chickens",
                "age_only": "For chickens at {age}",
                "breed_only": "For {breed} chickens",
                "sex_only": "For {sex} chickens"
            },
            "es": {
                "complete": "Para pollos {breed} {sex} de {age}",
                "breed_age": "Para pollos {breed} de {age}",
                "sex_age": "Para pollos {sex} de {age}",
                "breed_sex": "Para pollos {breed} {sex}",
                "age_only": "Para pollos de {age}",
                "breed_only": "Para pollos {breed}",
                "sex_only": "Para pollos {sex}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        context_prefix = ""
        age_text = age_info.get("text") if age_info.get("detected") else None
        
        if breed and sex and age_text:
            context_prefix = template_set["complete"].format(
                breed=breed, sex=sex, age=age_text
            )
            logger.info(f"🌟 [Complete Enrichment] Contexte COMPLET: {context_prefix}")
            
        elif breed and age_text:
            context_prefix = template_set["breed_age"].format(
                breed=breed, age=age_text
            )
            logger.info(f"🏷️ [Breed+Age] Contexte: {context_prefix}")
            
        elif sex and age_text:
            context_prefix = template_set["sex_age"].format(
                sex=sex, age=age_text
            )
            logger.info(f"⚧ [Sex+Age] Contexte: {context_prefix}")
            
        elif breed and sex:
            context_prefix = template_set["breed_sex"].format(
                breed=breed, sex=sex
            )
            logger.info(f"🏷️⚧ [Breed+Sex] Contexte: {context_prefix}")
            
        elif age_text:
            context_prefix = template_set["age_only"].format(age=age_text)
            logger.info(f"🕐 [Age Only] Contexte: {context_prefix}")
            
        elif breed:
            context_prefix = template_set["breed_only"].format(breed=breed)
            logger.info(f"🏷️ [Breed Only] Contexte: {context_prefix}")
            
        elif sex:
            context_prefix = template_set["sex_only"].format(sex=sex)
            logger.info(f"⚧ [Sex Only] Contexte: {context_prefix}")
        
        if context_prefix:
            original_lower = original_question.lower().strip()
            
            if "quel est" in original_lower or "what is" in original_lower or "cuál es" in original_lower:
                enriched_question = f"{context_prefix}, {original_lower}"
            elif "comment" in original_lower or "how" in original_lower or "cómo" in original_lower:
                enriched_question = f"{context_prefix}: {original_question}"
            else:
                enriched_question = f"{context_prefix}: {original_question}"
            
            logger.info(f"✨ [Final Enrichment] Question finale: {enriched_question}")
            return enriched_question
        
        else:
            logger.warning("⚠️ [Enrichment] Pas d'enrichissement possible, question originale conservée")
            return original_question
    
    # =============================================================================
    # MÉTHODES DE FEEDBACK ET TOPICS
    # =============================================================================
    
    async def process_feedback(self, feedback_data: FeedbackRequest) -> Dict[str, Any]:
        feedback_updated = False
        
        if feedback_data.conversation_id and self.integrations.logging_available:
            try:
                rating_numeric = {"positive": 1, "negative": -1, "neutral": 0}.get(feedback_data.rating, 0)
                feedback_updated = await self.integrations.update_feedback(feedback_data.conversation_id, rating_numeric)
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur feedback: {e}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès (Enhanced + Auto-Clarification Simplifiée + Validation Robuste + Fallback Intelligent)",
            "rating": feedback_data.rating,
            "comment": feedback_data.comment,
            "conversation_id": feedback_data.conversation_id,
            "feedback_updated_in_db": feedback_updated,
            "enhanced_features_used": True,
            "concision_system_active": self.concision_processor.config.ENABLE_CONCISE_RESPONSES,
            "response_versions_supported": True,
            "taxonomic_filtering_active": True,
            "semantic_dynamic_available": True,
            "auto_clarification_simplified": True,
            "validation_robuste_active": True,
            "fallback_intelligent_active": True,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_suggested_topics(self, language: str) -> Dict[str, Any]:
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
                "vagueness_detection_available": True,
                "context_coherence_available": True,
                "detailed_rag_scoring_available": True,
                "quality_metrics_available": True,
                "smart_clarification_available": True,
                "intelligent_memory_available": self.integrations.intelligent_memory_available,
                
                "response_concision_available": True,
                "concision_levels": [level.value for level in ConcisionLevel],
                "auto_concision_detection": True,
                "concision_enabled": self.concision_processor.config.ENABLE_CONCISE_RESPONSES,
                
                "response_versions_available": True,
                "multiple_concision_levels_generation": True,
                "dynamic_level_switching_support": True,
                "concision_metrics_available": True,
                
                "taxonomic_filtering_available": True,
                "supported_taxonomies": ["broiler", "layer", "swine", "dairy", "general"],
                "automatic_taxonomy_detection": True,
                "taxonomy_based_document_filtering": True,
                
                "semantic_dynamic_clarification_available": True,
                "gpt_question_generation": True,
                "contextual_clarification_questions": True,
                "intelligent_clarification_mode": True,
                
                "auto_clarification_simplified": True,
                "validation_robuste": True,
                "fallback_intelligent": True,
                "scoring_questions_generees": True,
                "integration_visible_expert_services": True
            },
            "system_status": {
                "validation_enabled": self.integrations.is_agricultural_validation_enabled(),
                "enhanced_clarification_enabled": self.integrations.is_enhanced_clarification_enabled(),
                "intelligent_memory_enabled": self.integrations.intelligent_memory_available,
                "api_enhancements_enabled": True,
                "concision_processor_enabled": True,
                "response_versions_generator_enabled": True,
                "taxonomic_filtering_enabled": True,
                "semantic_dynamic_clarification_enabled": True,
                "auto_clarification_simplified_enabled": True,
                "validation_robuste_enabled": True,
                "fallback_intelligent_enabled": True
            },
            
            "concision_config": {
                "default_level": self.concision_processor.config.DEFAULT_CONCISION_LEVEL.value,
                "auto_detect_enabled": True,
                "max_lengths": self.concision_processor.config.MAX_RESPONSE_LENGTH,
                "ultra_concise_keywords": self.concision_processor.config.ULTRA_CONCISE_KEYWORDS,
                "complex_keywords": self.concision_processor.config.COMPLEX_KEYWORDS,
                
                "response_versions_generation": {
                    "enabled": True,
                    "supported_levels": [level.value for level in ConcisionLevel],
                    "metrics_included": True,
                    "cache_supported": False,
                    "fallback_strategy": "simple_truncation"
                }
            },
            
            "taxonomic_config": {
                "enabled": True,
                "supported_categories": {
                    "broiler": ["ross", "cobb", "hubbard", "indian river"],
                    "layer": ["lohmann", "isa", "dekalb", "hy-line", "bovans", "h&n", "shaver"],
                    "swine": ["gestation_day", "parity"],
                    "dairy": ["days_in_milk", "milk_yield_liters"]
                },
                "auto_detection_enabled": True,
                "filter_fallback_enabled": True,
                "question_enhancement_enabled": True
            },
            
            "semantic_dynamic_config": {
                "enabled": True,
                "max_questions_generated": 4,
                "supported_languages": ["fr", "en", "es"],
                "gpt_model_used": "gpt-4o-mini",
                "fallback_questions_available": True,
                "context_aware_generation": True,
                "automatic_mode_detection": True
            },
            
            "auto_clarification_simplified_config": {
                "enabled": True,
                "completeness_score_threshold": 0.5,
                "validation_robuste_enabled": True,
                "fallback_intelligent_enabled": True,
                "scoring_questions_enabled": True,
                "integration_visible": True,
                "centralized_function": "auto_clarify_if_needed",
                "fallback_questions_by_type": True,
                "gpt_error_handling": True
            }
        }

# =============================================================================
# CONFIGURATION FINALE
# =============================================================================

logger.info("🚀" * 30)
logger.info("🚀 [EXPERT SERVICES] VERSION 3.11.0 - RESTRUCTURÉ EN 3 MODULES!")
logger.info("🚀 [MODULES CRÉÉS]:")
logger.info("   📁 1. expert_concision_service.py - Service de concision des réponses")
logger.info("   📁 2. expert_clarification_service.py - Service d'auto-clarification")
logger.info("   📁 3. expert_services.py - Service principal (restructuré)")
logger.info("🚀 [AVANTAGES RESTRUCTURATION]:")
logger.info("   ✅ Code plus maintenable et lisible")
logger.info("   ✅ Séparation claire des responsabilités") 
logger.info("   ✅ Modules réutilisables indépendamment")
logger.info("   ✅ Tests unitaires plus faciles")
logger.info("   ✅ Développement parallèle possible")
logger.info("🚀 [FONCTIONNALITÉS CONSERVÉES]:")
logger.info("   ✅ Toutes les fonctionnalités existantes intactes")
logger.info("   ✅ Auto-clarification simplifiée + validation robuste")
logger.info("   ✅ Système de concision multi-niveaux")
logger.info("   ✅ Génération versions de réponse")
logger.info("   ✅ Filtrage taxonomique intelligent")
logger.info("   ✅ Mode sémantique dynamique")
logger.info("   ✅ RAG avec contexte conversationnel")
logger.info("🚀" * 30)

logger.info("✅ [Expert Service] Service principal restructuré et opérationnel!")