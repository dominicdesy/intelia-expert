"""

expert_services.py - SERVICE PRINCIPAL AVEC PIPELINE IA UNIFIÉ - VERSION CORRIGÉE

🎯 PHASE 4: PIPELINE UNIFIÉ IA INTÉGRÉ (PRIORITÉ: HAUTE)

TRANSFORMATIONS APPLIQUÉES selon Plan de Transformation:
- ✅ Intégration UnifiedAIPipeline pour orchestration IA
- ✅ AIFallbackSystem pour robustesse maximale
- ✅ Conservation du code existant comme backup
- ✅ Gestion complète du contexte conversationnel
- ✅ Support du type CONTEXTUAL_ANSWER
- ✅ Passage du conversation_id au classifier
- ✅ Entités normalisées systématiquement
- ✅ Compatibilité totale avec l'ancien système

🔧 CORRECTIONS APPLIQUÉES DANS CETTE VERSION:
- ✅ Correction des appels async/await avec vérification dynamique
- ✅ Gestion robuste des méthodes sync/async avec detection
- ✅ Fallback intelligent vers patterns classiques  
- ✅ Conservation intégrale du code original
- ✅ Gestion d'erreurs améliorée avec fallbacks multiples
- ✅ Détection automatique du type de méthode (sync/async)

NOUVEAU FLUX IA UNIFIÉ:
1. Tentative pipeline IA complet (UnifiedAIPipeline)
2. Si succès: résultat IA optimisé
3. Si échec: fallback automatique vers système classique
4. Résultat: "Ross 308 mâle à 12 jours : 380-420g" avec IA ou fallback 🎯

IMPACT ATTENDU: +50% performance grâce au pipeline IA unifié

"""

import logging
import time
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

# ✅ CORRECTION: Initialiser le logger EN PREMIER
logger = logging.getLogger(__name__)

# ✅ CORRECTION PRINCIPALE: Initialisation sécurisée de AI_PIPELINE_AVAILABLE
AI_PIPELINE_AVAILABLE = False

# Imports des modules IA unifiés (NOUVEAUX selon plan transformation)
try:
    from .unified_ai_pipeline import get_unified_ai_pipeline, PipelineResult
    from .ai_fallback_system import AIFallbackSystem
    # ✅ CORRECTION: Assignment locale seulement après importation réussie
    AI_PIPELINE_AVAILABLE = True
    logger.info("✅ [Expert Services] Pipeline IA unifié disponible")
except ImportError as e:
    # ✅ CORRECTION: Ne pas réassigner la variable globale ici
    logger.warning(f"⚠️ [Expert Services] Pipeline IA non disponible: {e}")
except Exception as e:
    # ✅ CORRECTION: Gestion d'autres exceptions potentielles
    logger.error(f"❌ [Expert Services] Erreur import pipeline IA: {e}")

# Imports des modules existants (CONSERVÉS pour fallback)
from .entities_extractor import EntitiesExtractor, ExtractedEntities
from .entity_normalizer import EntityNormalizer, NormalizedEntities  # CONSERVÉ
from .smart_classifier import SmartClassifier, ClassificationResult, ResponseType
from .unified_response_generator import UnifiedResponseGenerator, ResponseData

# Import des modèles (gardés pour compatibilité)
try:
    from .expert_models import EnhancedExpertResponse, EnhancedQuestionRequest
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Classes de fallback minimalistes
    class EnhancedExpertResponse:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class EnhancedQuestionRequest:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

class ProcessingResult:
    """Résultat du traitement d'une question avec pipeline IA unifié"""
    def __init__(self, success: bool, response: str, response_type: str, 
                 confidence: float, entities: ExtractedEntities, 
                 processing_time_ms: int, error: str = None,
                 context_used: bool = False, weight_data: Dict[str, Any] = None,
                 normalized_entities: NormalizedEntities = None,
                 ai_pipeline_used: bool = False, pipeline_result: PipelineResult = None):  # NOUVEAU
        self.success = success
        self.response = response
        self.response_type = response_type
        self.confidence = confidence
        self.entities = entities  # Entités originales (pour compatibilité)
        self.processing_time_ms = processing_time_ms
        self.error = error
        self.context_used = context_used
        self.weight_data = weight_data or {}
        self.normalized_entities = normalized_entities  # Entités normalisées
        self.ai_pipeline_used = ai_pipeline_used  # NOUVEAU: Pipeline IA utilisé
        self.pipeline_result = pipeline_result  # NOUVEAU: Résultat complet pipeline IA
        self.timestamp = datetime.now().isoformat()

class ExpertService:
    """Service expert unifié avec pipeline IA et fallback système classique"""
    
    def __init__(self, db_path: str = "conversations.db"):
        """Initialisation du service avec pipeline IA unifié et système classique"""
        
        # =================================================================
        # NOUVEAU: PIPELINE IA UNIFIÉ (PRIORITÉ ABSOLUE)
        # =================================================================
        self.ai_pipeline = None
        self.ai_fallback_system = None
        
        # ✅ CORRECTION: Utiliser la variable globale sans la modifier localement
        if AI_PIPELINE_AVAILABLE:
            try:
                self.ai_pipeline = get_unified_ai_pipeline()
                self.ai_fallback_system = AIFallbackSystem()
                logger.info("🤖 [Expert Service] Pipeline IA unifié activé")
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur init pipeline IA: {e}")
                # ✅ CORRECTION: Ne pas modifier la variable globale ici
                # Utiliser un flag d'instance à la place si nécessaire
                self.ai_pipeline_failed = True
        
        # =================================================================
        # CONSERVÉ: SYSTÈME CLASSIQUE (FALLBACK GARANTI)
        # =================================================================
        self.entities_extractor = EntitiesExtractor()
        self.entity_normalizer = EntityNormalizer()
        self.smart_classifier = SmartClassifier(db_path=db_path)
        self.response_generator = UnifiedResponseGenerator()
        
        # Statistiques étendues avec métriques IA
        self.stats = {
            "questions_processed": 0,
            "precise_answers": 0,
            "general_answers": 0,
            "clarifications": 0,
            "contextual_answers": 0,
            "entities_normalized": 0,
            "normalization_success_rate": 0.0,
            "ai_pipeline_usage": 0,  # NOUVEAU: Utilisation pipeline IA
            "ai_success_rate": 0.0,  # NOUVEAU: Taux succès IA
            "fallback_usage": 0,     # NOUVEAU: Utilisation fallback
            "errors": 0,
            "average_processing_time_ms": 0,
            "context_usage_rate": 0.0
        }
        
        # Configuration étendue avec paramètres IA
        self.config = {
            "enable_logging": True,
            "enable_stats": True,
            "enable_context": True,
            "enable_normalization": True,
            "enable_ai_pipeline": AI_PIPELINE_AVAILABLE and self.ai_pipeline is not None,  # ✅ CORRECTION
            "ai_pipeline_priority": True,  # NOUVEAU: IA en priorité
            "max_processing_time_ms": 15000,  # Augmenté pour IA
            "fallback_enabled": True,
            "context_expiry_minutes": 10,
            "normalization_confidence_threshold": 0.5,
            "ai_timeout_seconds": 10,  # NOUVEAU: Timeout IA
            "ai_fallback_on_error": True  # NOUVEAU: Fallback auto
        }
        
        logger.info("✅ [Expert Service] Service unifié avec pipeline IA initialisé")
        
        # Affichage des capacités
        if self.ai_pipeline:
            logger.info("   🤖 Pipeline IA: ACTIVÉ - Performances optimisées")
            try:
                pipeline_health = self.ai_pipeline.get_pipeline_health()
                logger.info(f"   📊 Pipeline Health: {pipeline_health.get('success_rate', 0):.1f}% success")
            except Exception as e:
                logger.warning(f"   ⚠️ Pipeline Health non disponible: {e}")
        else:
            logger.info("   🔄 Système classique uniquement - Fallback garanti")
        
        # Statistiques des composants existants (conservées)
        try:
            extractor_stats = self.entities_extractor.get_extraction_stats()
            logger.info(f"   📊 Extracteur classique: {extractor_stats}")
        except Exception as e:
            logger.warning(f"   ⚠️ Stats extracteur: {e}")
        
        logger.info(f"   🔧 Normalizer: Races={len(self.entity_normalizer.breed_mapping)}")
        
        try:
            classifier_stats = self.smart_classifier.get_classification_stats()
            logger.info(f"   🧠 Classifier classique: {classifier_stats}")
        except Exception as e:
            logger.warning(f"   ⚠️ Stats classifier: {e}")
        
        logger.info(f"   🔗 Contexte: {'Activé' if self.config['enable_context'] else 'Désactivé'}")
        logger.info(f"   🎯 Normalisation: {'Activée' if self.config['enable_normalization'] else 'Désactivée'}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> ProcessingResult:
        """
        POINT D'ENTRÉE PRINCIPAL - Pipeline IA unifié avec fallback système classique
        
        Args:
            question: Question à traiter
            context: Contexte optionnel (conversation_id, user_id, is_clarification_response)
            language: Langue de réponse
            
        Returns:
            ProcessingResult avec la réponse et les métadonnées complètes
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 [Expert Service] Traitement: '{question[:50]}...'")
            
            # Extraire les paramètres de contexte
            conversation_id = context.get('conversation_id') if context else None
            is_clarification_response = context.get('is_clarification_response', False) if context else False
            
            if conversation_id:
                logger.info(f"🔗 [Expert Service] Conversation ID: {conversation_id}")
            if is_clarification_response:
                logger.info("🔗 [Expert Service] Clarification détectée")
            
            # Validation de base
            if not question or len(question.strip()) < 2:
                return ProcessingResult(
                    success=False,
                    response="Question trop courte. Pouvez-vous préciser votre demande ?",
                    response_type="error",
                    confidence=0.0,
                    entities=ExtractedEntities(),
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    error="Question invalide"
                )
            
            # =============================================================
            # NOUVEAU: TENTATIVE PIPELINE IA UNIFIÉ EN PRIORITÉ
            # =============================================================
            if self.config["enable_ai_pipeline"] and self.ai_pipeline and self.config["ai_pipeline_priority"]:
                try:
                    logger.info("🤖 [Expert Service] Tentative pipeline IA unifié...")
                    
                    # ✅ CORRECTION CRITIQUE: Retirer le paramètre 'context' non supporté
                    pipeline_result = await self.ai_pipeline.process_complete_pipeline(
                        question=question,
                        conversation_id=conversation_id,
                        language=language
                        # context=context or {}  # ❌ RETIRÉ - Paramètre non supporté
                    )
                    
                    if pipeline_result and pipeline_result.final_response:
                        processing_time_ms = int((time.time() - start_time) * 1000)
                        
                        logger.info(f"✅ [Expert Service] Pipeline IA réussi en {processing_time_ms}ms")
                        logger.info(f"   🎯 Confiance IA: {pipeline_result.confidence:.2f}")
                        logger.info(f"   🏷️ Type réponse: {pipeline_result.response_type}")
                        
                        # Conversion du résultat IA vers ProcessingResult
                        result = ProcessingResult(
                            success=True,
                            response=pipeline_result.final_response,
                            response_type=pipeline_result.response_type,
                            confidence=pipeline_result.confidence,
                            entities=pipeline_result.extracted_entities or ExtractedEntities(),
                            processing_time_ms=processing_time_ms,
                            context_used=pipeline_result.enhanced_context is not None,
                            weight_data=pipeline_result.weight_data,
                            normalized_entities=getattr(pipeline_result, 'normalized_entities', None),
                            ai_pipeline_used=True,  # NOUVEAU
                            pipeline_result=pipeline_result  # NOUVEAU
                        )
                        
                        # Statistiques IA
                        self._update_stats_ai(pipeline_result.response_type, processing_time_ms, True, 
                                            pipeline_result.enhanced_context is not None, True, False)
                        
                        return result
                        
                    else:
                        logger.warning("⚠️ [Expert Service] Pipeline IA: résultat invalide, fallback...")
                        
                except Exception as e:
                    logger.error(f"❌ [Expert Service] Erreur pipeline IA: {e}")
                    logger.info("🔄 [Expert Service] Basculement vers système classique...")
            
            # =============================================================
            # FALLBACK: SYSTÈME CLASSIQUE (CONSERVÉ ET AMÉLIORÉ)
            # =============================================================
            logger.info("🔄 [Expert Service] Traitement système classique...")
            
            # 1️⃣ EXTRACTION DES ENTITÉS (classique avec correction async/sync)
            raw_entities = await self._safe_extract_entities(question)
            logger.info(f"   🔍 Entités extraites: {raw_entities}")
            
            # 2️⃣ NORMALISATION CENTRALISÉE (conservée)
            normalized_entities = None
            entities_for_processing = self._entities_to_dict(raw_entities)
            
            if self.config["enable_normalization"]:
                try:
                    normalized_entities = self.entity_normalizer.normalize(raw_entities)
                    
                    if normalized_entities.normalization_confidence >= self.config["normalization_confidence_threshold"]:
                        entities_for_processing = normalized_entities.to_dict()
                        self.stats["entities_normalized"] += 1
                        logger.info(f"   🔧 Entités normalisées: {self._normalized_summary(normalized_entities)}")
                        logger.info(f"   📊 Confiance normalisation: {normalized_entities.normalization_confidence:.2f}")
                    else:
                        logger.warning(f"   ⚠️ Confiance normalisation faible: {normalized_entities.normalization_confidence:.2f}")
                        
                except Exception as e:
                    logger.error(f"   ❌ Erreur normalisation: {e}")
            
            # 3️⃣ CLASSIFICATION INTELLIGENTE AVEC CONTEXTE (classique)
            # ✅ CORRECTION CRITIQUE: Retirer le paramètre 'is_clarification_response' non supporté
            try:
                classification = self.smart_classifier.classify_question(
                    question, 
                    entities_for_processing,
                    conversation_id=conversation_id
                    # is_clarification_response=is_clarification_response  # ❌ RETIRÉ - Paramètre non supporté
                )
                
                logger.info(f"   🧠 Classification: {classification.response_type.value} (confiance: {classification.confidence})")
                
            except Exception as e:
                logger.error(f"   ❌ Erreur classification: {e}")
                # Fallback vers classification simple
                classification = ClassificationResult(
                    response_type=ResponseType.GENERAL_ANSWER,
                    confidence=0.5,
                    entities=entities_for_processing,
                    weight_data={},
                    merged_entities=entities_for_processing
                )
            
            context_used = classification.response_type == ResponseType.CONTEXTUAL_ANSWER
            if context_used:
                logger.info("   🔗 Contexte conversationnel utilisé")
            
            # 4️⃣ GÉNÉRATION DE LA RÉPONSE (classique)
            final_entities = classification.merged_entities if classification.merged_entities else entities_for_processing
            
            response_data = self.response_generator.generate(question, final_entities, classification)
            logger.info(f"   🎨 Réponse générée: {response_data.response_type}")
            
            if classification.weight_data:
                weight_range = classification.weight_data.get('weight_range')
                if weight_range:
                    logger.info(f"   📊 Données de poids: {weight_range[0]}-{weight_range[1]}g")
            
            # 5️⃣ FORMATAGE FINAL
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = ProcessingResult(
                success=True,
                response=response_data.response,
                response_type=response_data.response_type,
                confidence=response_data.confidence,
                entities=raw_entities,
                processing_time_ms=processing_time_ms,
                context_used=context_used,
                weight_data=classification.weight_data,
                normalized_entities=normalized_entities,
                ai_pipeline_used=False  # Système classique utilisé
            )
            
            # 6️⃣ MISE À JOUR DES STATISTIQUES
            self._update_stats_ai(classification.response_type, processing_time_ms, True, context_used, 
                                False, True)  # Fallback utilisé
            
            logger.info(f"✅ [Expert Service] Traitement classique réussi en {processing_time_ms}ms")
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Erreur de traitement: {str(e)}"
            
            logger.error(f"❌ [Expert Service] {error_msg}")
            
            # Réponse d'urgence
            fallback_response = self._generate_fallback_response(question, language)
            
            result = ProcessingResult(
                success=False,
                response=fallback_response,
                response_type="error_fallback",
                confidence=0.3,
                entities=ExtractedEntities(),
                processing_time_ms=processing_time_ms,
                error=error_msg,
                ai_pipeline_used=False
            )
            
            self._update_stats_ai(ResponseType.NEEDS_CLARIFICATION, processing_time_ms, False, False, False, True)
            return result

    async def _safe_extract_entities(self, question: str) -> ExtractedEntities:
        """
        🔧 NOUVELLE MÉTHODE: Extraction sécurisée avec détection async/sync automatique
        
        Cette méthode résout le problème d'appel async/await en détectant automatiquement
        si la méthode extract() est synchrone ou asynchrone et l'appelle correctement.
        """
        try:
            # ✅ CORRECTION PRINCIPALE: Vérifier si extract() est une coroutine function
            extract_method = self.entities_extractor.extract
            
            if asyncio.iscoroutinefunction(extract_method):
                # Méthode asynchrone - utiliser await
                logger.debug("   🔍 [Safe Extract] Extraction async détectée")
                raw_entities = await extract_method(question)
                logger.debug("   ✅ [Safe Extract] Extraction async réussie")
            else:
                # Méthode synchrone - appel direct
                logger.debug("   🔍 [Safe Extract] Extraction sync détectée")
                raw_entities = extract_method(question)
                logger.debug("   ✅ [Safe Extract] Extraction sync réussie")
            
            return raw_entities
            
        except Exception as e:
            logger.error(f"   ❌ [Safe Extract] Erreur extraction principale: {e}")
            
            # ✅ FALLBACK ROBUSTE vers patterns classiques
            try:
                logger.info("   🔄 [Safe Extract] Tentative patterns fallback...")
                raw_entities = self.entities_extractor._raw_extract_with_patterns(question.lower().strip())
                logger.info("   ✅ [Safe Extract] Patterns fallback réussi")
                return raw_entities
                
            except Exception as e2:
                logger.error(f"   ❌ [Safe Extract] Erreur patterns fallback: {e2}")
                
                # ✅ DERNIER RECOURS: Entités vides mais valides
                logger.warning("   🆘 [Safe Extract] Utilisation entités vides (dernier recours)")
                return ExtractedEntities()

    async def ask_expert_enhanced(self, request: EnhancedQuestionRequest) -> EnhancedExpertResponse:
        """
        Interface compatible avec l'ancien système - AMÉLIORÉE avec pipeline IA unifié
        
        Args:
            request: Requête formatée selon l'ancien modèle
            
        Returns:
            EnhancedExpertResponse compatible avec l'ancien système
        """
        try:
            # Extraire contexte enrichi
            context = {
                "conversation_id": getattr(request, 'conversation_id', None),
                "user_id": getattr(request, 'user_id', None),
                "is_clarification_response": getattr(request, 'is_clarification_response', False),
                "original_question": getattr(request, 'original_question', None),
                "clarification_entities": getattr(request, 'clarification_entities', None),
                "concision_level": getattr(request, 'concision_level', 'standard')
            }
            
            # Traitement unifié avec pipeline IA et fallback système classique
            result = await self.process_question(
                question=request.text,
                context=context,
                language=getattr(request, 'language', 'fr')
            )
            
            # Conversion vers format legacy avec informations IA
            return self._convert_to_legacy_response(request, result)
            
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur ask_expert_enhanced: {e}")
            return self._create_error_response(request, str(e))

    def _convert_to_legacy_response(self, request: EnhancedQuestionRequest, 
                                  result: ProcessingResult) -> EnhancedExpertResponse:
        """Convertit le résultat moderne vers le format legacy avec informations IA"""
        
        conversation_id = getattr(request, 'conversation_id', None) or str(uuid.uuid4())
        language = getattr(request, 'language', 'fr')
        
        # Données de base avec informations IA
        response_data = {
            "question": request.text,
            "response": result.response,
            "conversation_id": conversation_id,
            "rag_used": False,
            "timestamp": result.timestamp,
            "language": language,
            "response_time_ms": result.processing_time_ms,
            "mode": "unified_ai_pipeline_v3.0" if result.ai_pipeline_used else "unified_intelligent_system_v2_normalized"
        }
        
        # Ajout des champs pour compatibilité avec informations IA
        optional_fields = {
            "user": getattr(request, 'user_id', None),
            "logged": True,
            "validation_passed": result.success,
            "processing_steps": [
                "ai_pipeline_attempt" if result.ai_pipeline_used else "entities_extraction",
                "entity_normalization_v1" if result.normalized_entities else "classic_extraction",
                "context_enhancement_ai" if result.ai_pipeline_used else "context_management",
                "smart_classification_v2",
                "response_generation_ai" if result.ai_pipeline_used else "unified_response_generation_v2",
                "contextual_data_calculation" if result.context_used else "standard_processing"
            ],
            "ai_enhancements_used": [
                "unified_ai_pipeline_v1" if result.ai_pipeline_used else None,
                "ai_entity_extractor_v1" if result.ai_pipeline_used else "entities_extractor_v1",
                "ai_context_enhancer_v1" if result.ai_pipeline_used else None,
                "ai_response_generator_v1" if result.ai_pipeline_used else "unified_response_generator_v2",
                "entity_normalizer_v1" if result.normalized_entities else None,
                "conversation_context_manager" if result.context_used else None
            ]
        }
        
        # Informations de classification avec données IA
        classification_info = {
            "response_type_detected": result.response_type,
            "confidence_score": result.confidence,
            "entities_extracted": self._entities_to_dict(result.entities),
            "entities_normalized": result.normalized_entities.to_dict() if result.normalized_entities else None,
            "normalization_confidence": result.normalized_entities.normalization_confidence if result.normalized_entities else None,
            "processing_successful": result.success,
            "context_used": result.context_used,
            "weight_data_calculated": bool(result.weight_data),
            "conversation_id": conversation_id,
            "ai_pipeline_used": result.ai_pipeline_used,  # NOUVEAU
            "ai_pipeline_result": {  # NOUVEAU
                "stages_completed": result.pipeline_result.stages_completed if result.pipeline_result else [],
                "ai_calls_made": result.pipeline_result.ai_calls_made if result.pipeline_result else 0,
                "cache_hits": result.pipeline_result.cache_hits if result.pipeline_result else 0,
                "fallback_used": result.pipeline_result.fallback_used if result.pipeline_result else (not result.ai_pipeline_used)
            }
        }
        
        # Données de poids
        if result.weight_data:
            classification_info["weight_calculation"] = {
                "breed": result.weight_data.get('breed'),
                "age_days": result.weight_data.get('age_days'),
                "sex": result.weight_data.get('sex'),
                "weight_range": result.weight_data.get('weight_range'),
                "target_weight": result.weight_data.get('target_weight'),
                "data_source": result.weight_data.get('data_source', 'ai_pipeline' if result.ai_pipeline_used else 'intelligent_system_config')
            }
        
        # Fusionner données
        response_data.update(optional_fields)
        response_data["classification_result"] = classification_info
        
        # Informations contextuelles avec IA
        response_data["contextual_features"] = {
            "context_detection_enabled": self.config["enable_context"],
            "clarification_detection": True,
            "entity_inheritance": True,
            "entity_normalization": self.config["enable_normalization"],
            "weight_data_calculation": True,
            "conversation_persistence": True,
            "ai_pipeline_enabled": self.config["enable_ai_pipeline"],  # NOUVEAU
            "ai_context_enhancement": result.ai_pipeline_used,  # NOUVEAU
            "ai_response_generation": result.ai_pipeline_used   # NOUVEAU
        }
        
        # Détails de normalisation
        if result.normalized_entities:
            response_data["normalization_details"] = {
                "normalization_applied": True,
                "confidence": result.normalized_entities.normalization_confidence,
                "breed_normalized": result.normalized_entities.breed != self._entities_to_dict(result.entities).get('breed_specific'),
                "age_converted": result.normalized_entities.age_days is not None,
                "sex_standardized": result.normalized_entities.sex is not None,
                "enrichments_applied": len([x for x in [result.normalized_entities.context_type, 
                                                      result.normalized_entities.sex] if x]),
                "original_format_preserved": result.normalized_entities.original_format
            }
        
        # NOUVEAU: Détails du pipeline IA
        if result.ai_pipeline_used and result.pipeline_result:
            response_data["ai_pipeline_details"] = {
                "pipeline_used": True,
                "total_processing_time_ms": result.pipeline_result.total_processing_time_ms,
                "stages_completed": result.pipeline_result.stages_completed,
                "ai_calls_made": result.pipeline_result.ai_calls_made,
                "cache_hits": result.pipeline_result.cache_hits,
                "fallback_used": result.pipeline_result.fallback_used,
                "pipeline_version": result.pipeline_result.pipeline_version,
                "confidence_ai": result.pipeline_result.confidence
            }
        
        # Gestion d'erreur
        if not result.success:
            response_data["error_details"] = {
                "error_message": result.error,
                "fallback_used": True,
                "original_processing_failed": True,
                "context_available": bool(getattr(request, 'conversation_id', None)),
                "normalization_attempted": self.config["enable_normalization"],
                "ai_pipeline_attempted": self.config["enable_ai_pipeline"]  # NOUVEAU
            }
        
        if MODELS_AVAILABLE:
            return EnhancedExpertResponse(**response_data)
        else:
            return EnhancedExpertResponse(**response_data)

    def _create_error_response(self, request: EnhancedQuestionRequest, error: str) -> EnhancedExpertResponse:
        """Crée une réponse d'erreur avec informations IA"""
        
        error_responses = {
            "fr": f"Désolé, je rencontre une difficulté technique. Erreur: {error}. Pouvez-vous reformuler votre question ?",
            "en": f"Sorry, I'm experiencing a technical difficulty. Error: {error}. Could you rephrase your question?",
            "es": f"Lo siento, estoy experimentando una dificultad técnica. Error: {error}. ¿Podrías reformular tu pregunta?"
        }
        
        language = getattr(request, 'language', 'fr')
        error_response = error_responses.get(language, error_responses['fr'])
        
        return EnhancedExpertResponse(
            question=request.text,
            response=error_response,
            conversation_id=getattr(request, 'conversation_id', str(uuid.uuid4())),
            rag_used=False,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=0,
            mode="error_fallback_ai_pipeline",  # NOUVEAU
            logged=True,
            validation_passed=False,
            error_details={
                "error": error, 
                "system": "unified_expert_service_ai_pipeline_v3",  # NOUVEAU
                "context_available": bool(getattr(request, 'conversation_id', None)),
                "normalization_enabled": self.config["enable_normalization"],
                "ai_pipeline_enabled": self.config["enable_ai_pipeline"]  # NOUVEAU
            }
        )

    def _update_stats_ai(self, response_type: ResponseType, processing_time_ms: int, 
                        success: bool, context_used: bool = False, 
                        normalization_used: bool = False, fallback_used: bool = False):
        """Met à jour les statistiques avec informations IA"""
        
        if not self.config["enable_stats"]:
            return
        
        self.stats["questions_processed"] += 1
        
        if success:
            if response_type == ResponseType.PRECISE_ANSWER:
                self.stats["precise_answers"] += 1
            elif response_type == ResponseType.GENERAL_ANSWER:
                self.stats["general_answers"] += 1
            elif response_type == ResponseType.NEEDS_CLARIFICATION:
                self.stats["clarifications"] += 1
            elif response_type == ResponseType.CONTEXTUAL_ANSWER:
                self.stats["contextual_answers"] += 1
        else:
            self.stats["errors"] += 1
        
        # Stats contexte
        if context_used:
            total_context_usage = self.stats["context_usage_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["context_usage_rate"] = (total_context_usage + 1) / self.stats["questions_processed"]
        else:
            total_context_usage = self.stats["context_usage_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["context_usage_rate"] = total_context_usage / self.stats["questions_processed"]
        
        # Stats normalisation
        if normalization_used:
            total_normalization = self.stats["normalization_success_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["normalization_success_rate"] = (total_normalization + 1) / self.stats["questions_processed"]
        else:
            total_normalization = self.stats["normalization_success_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["normalization_success_rate"] = total_normalization / self.stats["questions_processed"]
        
        # NOUVEAU: Stats IA
        if not fallback_used:  # Pipeline IA utilisé
            self.stats["ai_pipeline_usage"] += 1
            total_ai_success = self.stats["ai_success_rate"] * (self.stats["ai_pipeline_usage"] - 1)
            if success:
                self.stats["ai_success_rate"] = (total_ai_success + 1) / self.stats["ai_pipeline_usage"]
            else:
                self.stats["ai_success_rate"] = total_ai_success / self.stats["ai_pipeline_usage"]
        else:  # Fallback utilisé
            self.stats["fallback_usage"] += 1
        
        # Temps moyen
        current_avg = self.stats["average_processing_time_ms"]
        total_questions = self.stats["questions_processed"]
        
        self.stats["average_processing_time_ms"] = int(
            (current_avg * (total_questions - 1) + processing_time_ms) / total_questions
        )

    def get_system_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques système avec informations IA"""
        
        total_questions = self.stats["questions_processed"]
        
        if total_questions == 0:
            return {
                "service_status": "ready",
                "version": "unified_ai_pipeline_v3.0.0",  # NOUVEAU
                "questions_processed": 0,
                "statistics": "No questions processed yet",
                "ai_pipeline_features": {  # NOUVEAU
                    "ai_pipeline_enabled": self.config["enable_ai_pipeline"],
                    "unified_orchestration": "enabled",
                    "intelligent_fallback": "enabled"
                },
                "normalization_features": {
                    "entity_normalization": "enabled" if self.config["enable_normalization"] else "disabled",
                    "breed_standardization": "enabled",
                    "age_conversion": "enabled",
                    "sex_mapping": "enabled"
                }
            }
        
        success_rate = ((total_questions - self.stats["errors"]) / total_questions) * 100
        ai_usage_rate = (self.stats["ai_pipeline_usage"] / total_questions) * 100 if total_questions > 0 else 0
        fallback_rate = (self.stats["fallback_usage"] / total_questions) * 100 if total_questions > 0 else 0
        
        return {
            "service_status": "active",
            "version": "unified_ai_pipeline_v3.0.0",  # NOUVEAU
            "questions_processed": total_questions,
            "success_rate_percent": round(success_rate, 2),
            "response_distribution": {
                "precise_answers": self.stats["precise_answers"],
                "general_answers": self.stats["general_answers"], 
                "clarifications": self.stats["clarifications"],
                "contextual_answers": self.stats["contextual_answers"],
                "errors": self.stats["errors"]
            },
            "contextual_metrics": {
                "context_usage_rate": round(self.stats["context_usage_rate"] * 100, 2),
                "contextual_answers_count": self.stats["contextual_answers"],
                "context_enabled": self.config["enable_context"]
            },
            "normalization_metrics": {
                "normalization_success_rate": round(self.stats["normalization_success_rate"] * 100, 2),
                "entities_normalized_count": self.stats["entities_normalized"],
                "normalization_enabled": self.config["enable_normalization"],
                "normalizer_stats": self.entity_normalizer.get_stats()
            },
            "ai_pipeline_metrics": {  # NOUVEAU
                "ai_pipeline_usage_rate": round(ai_usage_rate, 2),
                "ai_success_rate": round(self.stats["ai_success_rate"] * 100, 2),
                "fallback_usage_rate": round(fallback_rate, 2),
                "ai_pipeline_enabled": self.config["enable_ai_pipeline"],
                "ai_pipeline_health": self.ai_pipeline.get_pipeline_health() if self.ai_pipeline else None
            },
            "performance": {
                "average_processing_time_ms": self.stats["average_processing_time_ms"],
                "system_components": {
                    "ai_unified_pipeline": "active" if self.config["enable_ai_pipeline"] else "disabled",  # NOUVEAU
                    "ai_fallback_system": "active" if self.ai_fallback_system else "disabled",  # NOUVEAU
                    "entities_extractor": "active",
                    "entity_normalizer": "active" if self.config["enable_normalization"] else "disabled",
                    "smart_classifier": "active_contextual",
                    "response_generator": "active_contextual",
                    "conversation_context_manager": "active" if self.config["enable_context"] else "disabled"
                }
            },
            "configuration": self.config,
            "timestamp": datetime.now().isoformat()
        }

    # =============================================================
    # MÉTHODES CONSERVÉES (compatibilité et fonctionnalités)
    # =============================================================
    
    def _entities_to_dict(self, entities) -> Dict[str, Any]:
        """Convertit les entités en dictionnaire pour compatibilité"""
        if hasattr(entities, '__dict__'):
            entity_dict = {}
            for key, value in entities.__dict__.items():
                if not key.startswith('_'):
                    entity_dict[key] = value
            return entity_dict
        elif isinstance(entities, dict):
            return entities
        else:
            return {
                'age_days': getattr(entities, 'age_days', None),
                'age_weeks': getattr(entities, 'age_weeks', None),
                'age': getattr(entities, 'age', None),
                'breed_specific': getattr(entities, 'breed_specific', None),
                'breed_generic': getattr(entities, 'breed_generic', None),
                'sex': getattr(entities, 'sex', None),
                'weight_mentioned': getattr(entities, 'weight_mentioned', False),
                'weight_grams': getattr(entities, 'weight_grams', None),
                'weight_unit': getattr(entities, 'weight_unit', None),
                'symptoms': getattr(entities, 'symptoms', []),
                'context_type': getattr(entities, 'context_type', None),
                'housing_conditions': getattr(entities, 'housing_conditions', None),
                'feeding_context': getattr(entities, 'feeding_context', None)
            }

    def _normalized_summary(self, normalized_entities: NormalizedEntities) -> str:
        """Crée un résumé des entités normalisées pour le logging"""
        
        summary_parts = []
        
        if normalized_entities.breed:
            summary_parts.append(f"race={normalized_entities.breed}")
        
        if normalized_entities.age_days:
            summary_parts.append(f"âge={normalized_entities.age_days}j")
        
        if normalized_entities.sex:
            summary_parts.append(f"sexe={normalized_entities.sex}")
        
        if normalized_entities.weight_grams:
            summary_parts.append(f"poids={normalized_entities.weight_grams}g")
        
        if normalized_entities.symptoms:
            summary_parts.append(f"symptômes={len(normalized_entities.symptoms)}")
        
        if normalized_entities.context_type:
            summary_parts.append(f"contexte={normalized_entities.context_type}")
        
        return ", ".join(summary_parts) if summary_parts else "aucune"

    def _generate_fallback_response(self, question: str, language: str = "fr") -> str:
        """Génère une réponse de fallback en cas d'erreur"""
        
        fallback_responses = {
            "fr": """Je rencontre une difficulté technique pour analyser votre question.

💡 **Pour m'aider à mieux vous répondre, précisez** :
• Le type de volailles (poulets de chair, pondeuses...)
• L'âge de vos animaux (21 jours, 3 semaines...)
• Votre problème ou objectif spécifique

**Exemple** : "Poids normal Ross 308 mâles à 21 jours ?"

🔄 Veuillez réessayer en reformulant votre question.""",

            "en": """I'm experiencing a technical difficulty analyzing your question.

💡 **To help me better assist you, please specify** :
• Type of poultry (broilers, layers...)
• Age of your animals (21 days, 3 weeks...)
• Your specific problem or objective

**Example** : "Normal weight Ross 308 males at 21 days?"

🔄 Please try again by rephrasing your question.""",

            "es": """Estoy experimentando una dificultad técnica para analizar tu pregunta.

💡 **Para ayudarme a responderte mejor, especifica** :
• Tipo de aves (pollos de engorde, ponedoras...)
• Edad de tus animales (21 días, 3 semanas...)
• Tu problema u objetivo específico

**Ejemplo** : "Peso normal Ross 308 machos a 21 días?"

🔄 Por favor, inténtalo de nuevo reformulando tu pregunta."""
        }
        
        return fallback_responses.get(language, fallback_responses['fr'])

    def reset_stats(self):
        """Remet à zéro les statistiques avec nouvelles métriques IA"""
        self.stats = {
            "questions_processed": 0,
            "precise_answers": 0,
            "general_answers": 0,
            "clarifications": 0,
            "contextual_answers": 0,
            "entities_normalized": 0,
            "normalization_success_rate": 0.0,
            "ai_pipeline_usage": 0,  # NOUVEAU
            "ai_success_rate": 0.0,  # NOUVEAU
            "fallback_usage": 0,     # NOUVEAU
            "errors": 0,
            "average_processing_time_ms": 0,
            "context_usage_rate": 0.0
        }
        logger.info("📊 [Expert Service] Statistiques remises à zéro (version IA pipeline)")

    def update_config(self, new_config: Dict[str, Any]):
        """Met à jour la configuration du service avec paramètres IA"""
        self.config.update(new_config)
        logger.info(f"⚙️ [Expert Service] Configuration mise à jour: {new_config}")
        
        # ✅ CORRECTION: Réactivation IA sans modification de variable globale
        if "enable_ai_pipeline" in new_config and new_config["enable_ai_pipeline"] and not self.ai_pipeline:
            if AI_PIPELINE_AVAILABLE:  # Utiliser la variable globale
                try:
                    self.ai_pipeline = get_unified_ai_pipeline()
                    self.ai_fallback_system = AIFallbackSystem()
                    logger.info("🤖 [Expert Service] Pipeline IA réactivé")
                except Exception as e:
                    logger.error(f"❌ [Expert Service] Impossible de réactiver IA: {e}")
            else:
                logger.warning("⚠️ [Expert Service] Pipeline IA non disponible globalement")
        
        if "enable_normalization" in new_config:
            logger.info(f"🔧 [Expert Service] Normalisation {'activée' if new_config['enable_normalization'] else 'désactivée'}")

    def get_contextual_debug_info(self, conversation_id: str) -> Dict[str, Any]:
        """Récupère les informations de debug avec données IA"""
        try:
            context = self.smart_classifier._get_conversation_context(conversation_id)
            
            debug_info = {
                "conversation_id": conversation_id,
                "context_available": context is not None,
                "context_fresh": context.is_fresh() if context else False,
                "context_data": context.to_dict() if context else None,
                "classifier_stats": self.smart_classifier.get_classification_stats(),
                "normalizer_stats": self.entity_normalizer.get_stats(),
                "service_version": "v3.0.0_ai_pipeline",  # NOUVEAU
                "ai_pipeline_available": self.ai_pipeline is not None,  # NOUVEAU
                "ai_pipeline_health": self.ai_pipeline.get_pipeline_health() if self.ai_pipeline else None  # NOUVEAU
            }
            
            return debug_info
            
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur debug contextuel: {e}")
            return {
                "conversation_id": conversation_id,
                "error": str(e),
                "context_available": False,
                "normalization_available": self.config["enable_normalization"],
                "ai_pipeline_available": self.config["enable_ai_pipeline"]  # NOUVEAU
            }

    def get_normalization_debug_info(self, raw_entities: Dict[str, Any]) -> Dict[str, Any]:
        """Récupère les informations de debug pour la normalisation"""
        try:
            normalized = self.entity_normalizer.normalize(raw_entities)
            
            return {
                "raw_entities": raw_entities,
                "normalized_entities": normalized.to_dict(),
                "normalization_confidence": normalized.normalization_confidence,
                "changes_applied": {
                    "breed_normalized": normalized.breed != raw_entities.get('breed_specific'),
                    "age_converted": normalized.age_days is not None,
                    "sex_standardized": normalized.sex is not None,
                    "weight_converted": normalized.weight_grams is not None
                },
                "normalizer_stats": self.entity_normalizer.get_stats(),
                "service_version": "v3.0.0_ai_pipeline"  # NOUVEAU
            }
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur debug normalisation: {e}")
            return {
                "error": str(e),
                "raw_entities": raw_entities,
                "normalization_failed": True
            }

    def get_ai_pipeline_debug_info(self) -> Dict[str, Any]:
        """NOUVEAU: Récupère les informations de debug pour le pipeline IA"""
        try:
            if not self.ai_pipeline:
                return {
                    "ai_pipeline_available": False,
                    "error": "Pipeline IA non disponible",
                    "fallback_system_available": self.ai_fallback_system is not None
                }
            
            return {
                "ai_pipeline_available": True,
                "pipeline_health": self.ai_pipeline.get_pipeline_health(),
                "fallback_system_available": self.ai_fallback_system is not None,
                "ai_service_stats": {
                    "usage_rate": round((self.stats["ai_pipeline_usage"] / self.stats["questions_processed"] * 100) if self.stats["questions_processed"] > 0 else 0, 2),
                    "success_rate": round(self.stats["ai_success_rate"] * 100, 2),
                    "fallback_rate": round((self.stats["fallback_usage"] / self.stats["questions_processed"] * 100) if self.stats["questions_processed"] > 0 else 0, 2)
                },
                "configuration": {
                    "ai_pipeline_enabled": self.config["enable_ai_pipeline"],
                    "ai_priority": self.config["ai_pipeline_priority"],
                    "ai_timeout": self.config["ai_timeout_seconds"],
                    "fallback_on_error": self.config["ai_fallback_on_error"]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur debug pipeline IA: {e}")
            return {
                "error": str(e),
                "ai_pipeline_available": False,
                "debug_failed": True
            }

# =============================================================================
# FONCTIONS UTILITAIRES ET TESTS AVEC PIPELINE IA UNIFIÉ
# =============================================================================

async def quick_ask(question: str, conversation_id: str = None, language: str = "fr") -> str:
    """Interface rapide pour poser une question avec pipeline IA unifié"""
    service = ExpertService()
    context = {"conversation_id": conversation_id} if conversation_id else None
    result = await service.process_question(question, context=context, language=language)
    return result.response

def create_expert_service() -> ExpertService:
    """Factory pour créer une instance du service avec pipeline IA unifié"""
    return ExpertService()

# =============================================================================
# TESTS INTÉGRÉS AVEC PIPELINE IA UNIFIÉ COMPLET
# =============================================================================

async def test_expert_service_ai_pipeline():
    """Tests du service expert avec pipeline IA unifié et fallback système classique"""
    
    print("🧪 Tests du Service Expert avec Pipeline IA Unifié")
    print("=" * 80)
    
    service = ExpertService()
    conversation_id = "test_conv_ai_pipeline_ross308"
    
    test_cases = [
        # Cas 1: Test IA - normalisation races (variantes d'écriture)
        {
            "question": "Quel est le poids d'un ross308 à 12 jours ?",
            "context": {"conversation_id": conversation_id},
            "expected_type": "general",
            "description": "Test IA: ross308 → Ross 308 avec pipeline unifié"
        },
        
        # Cas 2: Test IA - normalisation âge (semaines → jours)
        {
            "question": "Poids cobb500 à 3 semaines ?",
            "context": {"conversation_id": f"{conversation_id}_2"},
            "expected_type": "general", 
            "description": "Test IA: cobb500 → Cobb 500, 3 sem → 21j"
        },
        
        # Cas 3: Test IA - clarification contextuelle avec sexe
        {
            "question": "Pour des mâles",
            "context": {
                "conversation_id": conversation_id,
                "is_clarification_response": True
            },
            "expected_type": "contextual",
            "description": "Test IA: clarification avec sexe normalisé: mâles → male"
        },
        
        # Cas 4: Test fallback - entités complexes
        {
            "question": "poids isa brown femelles 20 semaines élevage bio ?",
            "context": {"conversation_id": f"{conversation_id}_3"},
            "expected_type": "precise",
            "description": "Test fallback: normalisation complète avec contexte élevage"
        },
        
        # Cas 5: Test IA - question ambiguë
        {
            "question": "Problème de croissance mes poulets",
            "context": {"conversation_id": f"{conversation_id}_4"},
            "expected_type": "general",
            "description": "Test IA: question ambiguë nécessitant analyse contextuelle"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['description']}")
        print(f"   Question: {test_case['question']}")
        print(f"   Type attendu: {test_case['expected_type']}")
        
        try:
            start_time = time.time()
            result = await service.process_question(
                test_case['question'], 
                context=test_case['context']
            )
            processing_time = int((time.time() - start_time) * 1000)
            
            status = "✅" if result.success else "❌"
            ai_used = "🤖 IA" if result.ai_pipeline_used else "🔄 Classique"
            print(f"   {status} Type obtenu: {result.response_type} ({ai_used})")
            print(f"   ⏱️ Temps: {processing_time}ms")
            print(f"   🎯 Confiance: {result.confidence:.2f}")
            print(f"   🔗 Contexte utilisé: {'Oui' if result.context_used else 'Non'}")
            
            # Afficher informations spécifiques au pipeline IA
            if result.ai_pipeline_used and result.pipeline_result:
                print(f"   🤖 Pipeline IA - Étapes: {len(result.pipeline_result.stages_completed)}")
                print(f"      Appels IA: {result.pipeline_result.ai_calls_made}")
                print(f"      Cache hits: {result.pipeline_result.cache_hits}")
                if result.pipeline_result.stages_completed:
                    print(f"      Étapes: {', '.join(result.pipeline_result.stages_completed)}")
            
            # Informations de normalisation
            if result.normalized_entities:
                print(f"   🔧 Normalisation: confiance={result.normalized_entities.normalization_confidence:.2f}")
                if result.normalized_entities.breed:
                    print(f"      Race normalisée: {result.normalized_entities.breed}")
                if result.normalized_entities.age_days:
                    print(f"      Âge normalisé: {result.normalized_entities.age_days} jours")
                if result.normalized_entities.sex:
                    print(f"      Sexe normalisé: {result.normalized_entities.sex}")
            
            # Afficher les données de poids si calculées
            if result.weight_data and 'weight_range' in result.weight_data:
                weight_range = result.weight_data['weight_range']
                print(f"   📊 Poids calculé: {weight_range[0]}-{weight_range[1]}g")
            
            # Prévisualisation de la réponse
            if len(result.response) > 150:
                preview = result.response[:150] + "..."
            else:
                preview = result.response
            print(f"   💬 Réponse: {preview}")
            
            # Vérifications spéciales pour les tests
            if i == 1 and result.normalized_entities and result.normalized_entities.breed == "Ross 308":
                print("   ✅ SUCCESS: Normalisation race ross308 → Ross 308!")
            if i == 2 and result.normalized_entities and result.normalized_entities.age_days == 21:
                print("   ✅ SUCCESS: Normalisation âge 3 semaines → 21 jours!")
            if i <= 3 and result.ai_pipeline_used:
                print("   🤖 SUCCESS: Pipeline IA utilisé avec succès!")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print(f"\n📊 Statistiques finales:")
    stats = service.get_system_stats()
    print(f"   Questions traitées: {stats['questions_processed']}")
    print(f"   Taux de succès: {stats['success_rate_percent']:.1f}%")
    print(f"   Réponses contextuelles: {stats['contextual_metrics']['contextual_answers_count']}")
    print(f"   Taux d'utilisation contexte: {stats['contextual_metrics']['context_usage_rate']:.1f}%")
    print(f"   Entités normalisées: {stats['normalization_metrics']['entities_normalized_count']}")
    print(f"   Taux normalisation: {stats['normalization_metrics']['normalization_success_rate']:.1f}%")
    
    # NOUVEAU: Statistiques pipeline IA
    if 'ai_pipeline_metrics' in stats:
        ai_metrics = stats['ai_pipeline_metrics']
        print(f"   🤖 Utilisation IA: {ai_metrics['ai_pipeline_usage_rate']:.1f}%")
        print(f"   🤖 Taux succès IA: {ai_metrics['ai_success_rate']:.1f}%")
        print(f"   🔄 Taux fallback: {ai_metrics['fallback_usage_rate']:.1f}%")
    
    print(f"   Temps moyen: {stats['performance']['average_processing_time_ms']}ms")
    
    # Test spécifique de debug du pipeline IA
    print(f"\n🤖 Test de debug pipeline IA:")
    ai_debug = service.get_ai_pipeline_debug_info()
    print(f"   Pipeline IA disponible: {'Oui' if ai_debug['ai_pipeline_available'] else 'Non'}")
    if ai_debug['ai_pipeline_available']:
        health = ai_debug['pipeline_health']
        print(f"   Santé pipeline: {health.get('success_rate', 0):.1f}% success, {health.get('total_runs', 0)} runs")
    
    # Test spécifique de normalisation (conservé)
    print(f"\n🔧 Test de normalisation isolée:")
    test_entities = {
        "breed_specific": "ross308",
        "age_weeks": 3,
        "sex": "mâles"
    }
    debug_info = service.get_normalization_debug_info(test_entities)
    print(f"   Entités brutes: {debug_info['raw_entities']}")
    print(f"   Entités normalisées: {debug_info['normalized_entities']}")
    print(f"   Confiance: {debug_info['normalization_confidence']:.2f}")
    print(f"   Changements: {debug_info['changes_applied']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_expert_service_ai_pipeline())