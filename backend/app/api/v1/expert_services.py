"""
expert_services.py - SERVICE PRINCIPAL AVEC NORMALISATION CENTRALISÉE

🎯 PHASE 1: NORMALISATION DES ENTITÉS INTÉGRÉE (PRIORITÉ: HAUTE)

AMÉLIORATIONS INTÉGRÉES:
- ✅ Intégration EntityNormalizer pour cohérence totale
- ✅ Gestion complète du contexte conversationnel  
- ✅ Support du type CONTEXTUAL_ANSWER
- ✅ Passage du conversation_id au classifier
- ✅ Entités normalisées systématiquement
- ✅ Compatibilité totale avec l'ancien système

NOUVEAU FLUX AMÉLIORÉ:
1. Récupération du conversation_id depuis la requête
2. Extraction des entités + NORMALISATION automatique
3. Passage du conversation_id au classifier intelligent
4. Classifier détecte les clarifications et fusionne le contexte
5. Response Generator utilise les entités normalisées + weight_data
6. Résultat: "Ross 308 mâle à 12 jours : 380-420g" 🎯

IMPACT ATTENDU: +25% performance grâce à la normalisation
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

# Imports des nouveaux modules avec contexte ET normalisation
from .entities_extractor import EntitiesExtractor, ExtractedEntities
from .entity_normalizer import EntityNormalizer, NormalizedEntities  # NOUVEAU
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

logger = logging.getLogger(__name__)

class ProcessingResult:
    """Résultat du traitement d'une question avec contexte ET entités normalisées"""
    def __init__(self, success: bool, response: str, response_type: str, 
                 confidence: float, entities: ExtractedEntities, 
                 processing_time_ms: int, error: str = None,
                 context_used: bool = False, weight_data: Dict[str, Any] = None,
                 normalized_entities: NormalizedEntities = None):  # NOUVEAU
        self.success = success
        self.response = response
        self.response_type = response_type
        self.confidence = confidence
        self.entities = entities  # Entités originales (pour compatibilité)
        self.processing_time_ms = processing_time_ms
        self.error = error
        self.context_used = context_used
        self.weight_data = weight_data or {}
        self.normalized_entities = normalized_entities  # NOUVEAU: Entités normalisées
        self.timestamp = datetime.now().isoformat()

class ExpertService:
    """Service expert unifié avec normalisation centralisée et contexte conversationnel"""
    
    def __init__(self, db_path: str = "conversations.db"):
        """Initialisation du service avec les composants contextuels ET normalisation"""
        self.entities_extractor = EntitiesExtractor()
        self.entity_normalizer = EntityNormalizer()  # NOUVEAU: Normalizer centralisé
        self.smart_classifier = SmartClassifier(db_path=db_path)
        self.response_generator = UnifiedResponseGenerator()
        
        # Statistiques pour monitoring (améliorées avec normalisation)
        self.stats = {
            "questions_processed": 0,
            "precise_answers": 0,
            "general_answers": 0,
            "clarifications": 0,
            "contextual_answers": 0,
            "entities_normalized": 0,  # NOUVEAU: Compteur normalisation
            "normalization_success_rate": 0.0,  # NOUVEAU: Taux de succès normalisation
            "errors": 0,
            "average_processing_time_ms": 0,
            "context_usage_rate": 0.0
        }
        
        # Configuration
        self.config = {
            "enable_logging": True,
            "enable_stats": True,
            "enable_context": True,
            "enable_normalization": True,  # NOUVEAU: Activer normalisation
            "max_processing_time_ms": 10000,
            "fallback_enabled": True,
            "context_expiry_minutes": 10,
            "normalization_confidence_threshold": 0.5  # NOUVEAU: Seuil confiance normalisation
        }
        
        logger.info("✅ [Expert Service] Service unifié avec normalisation initialisé")
        
        # 🔧 FIX: Gestion sécurisée des statistiques de l'extracteur
        try:
            extractor_stats = self.entities_extractor.get_extraction_stats()
            logger.info(f"   📊 Extracteur: {extractor_stats}")
        except Exception as e:
            logger.warning(f"   ⚠️ Impossible de récupérer les stats extracteur: {e}")
        
        logger.info(f"   🔧 Normalizer: Races={len(self.entity_normalizer.breed_mapping)}")
        
        # 🔧 FIX: Gestion sécurisée des statistiques du classifier
        try:
            classifier_stats = self.smart_classifier.get_classification_stats()
            logger.info(f"   🧠 Classifier: {classifier_stats}")
        except Exception as e:
            logger.warning(f"   ⚠️ Impossible de récupérer les stats classifier: {e}")
        
        logger.info(f"   🔗 Contexte: {'Activé' if self.config['enable_context'] else 'Désactivé'}")
        logger.info(f"   🎯 Normalisation: {'Activée' if self.config['enable_normalization'] else 'Désactivée'}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> ProcessingResult:
        """
        POINT D'ENTRÉE PRINCIPAL - Traite une question avec normalisation et contexte
        
        Args:
            question: Question à traiter
            context: Contexte optionnel (conversation_id, user_id, is_clarification_response)
            language: Langue de réponse
            
        Returns:
            ProcessingResult avec la réponse et les métadonnées contextuelles + entités normalisées
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
            
            # 1️⃣ EXTRACTION DES ENTITÉS (sans normalisation)
            raw_entities = self.entities_extractor.extract(question)
            logger.info(f"   🔍 Entités extraites: {raw_entities}")
            
            # 2️⃣ NOUVEAU: NORMALISATION CENTRALISÉE
            normalized_entities = None
            entities_for_processing = self._entities_to_dict(raw_entities)  # Format par défaut
            
            if self.config["enable_normalization"]:
                try:
                    normalized_entities = self.entity_normalizer.normalize(raw_entities)
                    
                    # Vérifier la confiance de normalisation
                    if normalized_entities.normalization_confidence >= self.config["normalization_confidence_threshold"]:
                        entities_for_processing = normalized_entities.to_dict()
                        self.stats["entities_normalized"] += 1
                        logger.info(f"   🔧 Entités normalisées: {self._normalized_summary(normalized_entities)}")
                        logger.info(f"   📊 Confiance normalisation: {normalized_entities.normalization_confidence:.2f}")
                    else:
                        logger.warning(f"   ⚠️ Confiance normalisation faible: {normalized_entities.normalization_confidence:.2f}")
                        # Garder les entités originales
                        
                except Exception as e:
                    logger.error(f"   ❌ Erreur normalisation: {e}")
                    # Continuer avec les entités originales
            
            # 3️⃣ CLASSIFICATION INTELLIGENTE AVEC CONTEXTE (utilise entités normalisées si disponibles)
            classification = self.smart_classifier.classify_question(
                question, 
                entities_for_processing,
                conversation_id=conversation_id,
                is_clarification_response=is_clarification_response
            )
            
            logger.info(f"   🧠 Classification: {classification.response_type.value} (confiance: {classification.confidence})")
            
            # Vérifier si le contexte a été utilisé
            context_used = classification.response_type == ResponseType.CONTEXTUAL_ANSWER
            if context_used:
                logger.info("   🔗 Contexte conversationnel utilisé pour la réponse")
            
            # 4️⃣ GÉNÉRATION DE LA RÉPONSE AVEC SUPPORT CONTEXTUEL ET ENTITÉS NORMALISÉES
            # Utiliser les entités fusionnées si disponibles, sinon les entités normalisées
            final_entities = classification.merged_entities if classification.merged_entities else entities_for_processing
            
            response_data = self.response_generator.generate(question, final_entities, classification)
            logger.info(f"   🎨 Réponse générée: {response_data.response_type}")
            
            # Afficher les données de poids si calculées
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
                entities=raw_entities,  # Entités originales pour compatibilité
                processing_time_ms=processing_time_ms,
                context_used=context_used,
                weight_data=classification.weight_data,
                normalized_entities=normalized_entities  # NOUVEAU: Entités normalisées
            )
            
            # 6️⃣ MISE À JOUR DES STATISTIQUES AVEC NORMALISATION
            self._update_stats(classification.response_type, processing_time_ms, True, context_used, 
                             normalized_entities is not None)
            
            logger.info(f"✅ [Expert Service] Traitement réussi en {processing_time_ms}ms")
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Erreur de traitement: {str(e)}"
            
            logger.error(f"❌ [Expert Service] {error_msg}")
            
            # Réponse de fallback
            fallback_response = self._generate_fallback_response(question, language)
            
            result = ProcessingResult(
                success=False,
                response=fallback_response,
                response_type="error_fallback",
                confidence=0.3,
                entities=ExtractedEntities(),
                processing_time_ms=processing_time_ms,
                error=error_msg
            )
            
            self._update_stats(ResponseType.NEEDS_CLARIFICATION, processing_time_ms, False, False, False)
            return result

    async def ask_expert_enhanced(self, request: EnhancedQuestionRequest) -> EnhancedExpertResponse:
        """
        Interface compatible avec l'ancien système - AMÉLIORÉE avec normalisation et contexte
        
        Args:
            request: Requête formatée selon l'ancien modèle
            
        Returns:
            EnhancedExpertResponse compatible avec l'ancien système
        """
        try:
            # Extraire plus d'informations contextuelles
            context = {
                "conversation_id": getattr(request, 'conversation_id', None),
                "user_id": getattr(request, 'user_id', None),
                "is_clarification_response": getattr(request, 'is_clarification_response', False),
                "original_question": getattr(request, 'original_question', None),
                "clarification_entities": getattr(request, 'clarification_entities', None),
                "concision_level": getattr(request, 'concision_level', 'standard')
            }
            
            # Traitement unifié avec normalisation et contexte
            result = await self.process_question(
                question=request.text,
                context=context,
                language=getattr(request, 'language', 'fr')
            )
            
            # Conversion en format ancien pour compatibilité
            return self._convert_to_legacy_response(request, result)
            
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur ask_expert_enhanced: {e}")
            return self._create_error_response(request, str(e))

    def _entities_to_dict(self, entities) -> Dict[str, Any]:
        """Convertit les entités en dictionnaire pour compatibilité"""
        # 🔧 FIX: Gestion flexible des différents types d'entités
        if hasattr(entities, '__dict__'):
            # Pour ExtractedEntities ou NormalizedEntities
            entity_dict = {}
            for key, value in entities.__dict__.items():
                if not key.startswith('_'):
                    entity_dict[key] = value
            return entity_dict
        elif isinstance(entities, dict):
            return entities
        else:
            # Fallback pour autres types
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
        """NOUVEAU: Crée un résumé des entités normalisées pour le logging"""
        
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

    def _convert_to_legacy_response(self, request: EnhancedQuestionRequest, 
                                  result: ProcessingResult) -> EnhancedExpertResponse:
        """Convertit le résultat moderne vers le format legacy avec données normalisées"""
        
        conversation_id = getattr(request, 'conversation_id', None) or str(uuid.uuid4())
        language = getattr(request, 'language', 'fr')
        
        # Données de base obligatoires
        response_data = {
            "question": request.text,
            "response": result.response,
            "conversation_id": conversation_id,
            "rag_used": False,
            "timestamp": result.timestamp,
            "language": language,
            "response_time_ms": result.processing_time_ms,
            "mode": "unified_intelligent_system_v2_normalized"  # NOUVEAU: Version avec normalisation
        }
        
        # Ajout des champs optionnels pour compatibilité (améliorés)
        optional_fields = {
            "user": getattr(request, 'user_id', None),
            "logged": True,
            "validation_passed": result.success,
            "processing_steps": [
                "entities_extraction",
                "entity_normalization",  # NOUVEAU: Étape de normalisation
                "smart_classification_with_context",
                "unified_response_generation",
                "contextual_data_calculation" if result.context_used else "standard_processing"
            ],
            "ai_enhancements_used": [
                "smart_classifier_v2_contextual",
                "unified_generator_v2_contextual",
                "entities_extractor_v1",
                "entity_normalizer_v1",  # NOUVEAU: Normalizer
                "conversation_context_manager" if result.context_used else None
            ]
        }
        
        # Informations de classification contextuelles AVEC normalisation
        classification_info = {
            "response_type_detected": result.response_type,
            "confidence_score": result.confidence,
            "entities_extracted": self._entities_to_dict(result.entities),
            "entities_normalized": result.normalized_entities.to_dict() if result.normalized_entities else None,  # NOUVEAU
            "normalization_confidence": result.normalized_entities.normalization_confidence if result.normalized_entities else None,  # NOUVEAU
            "processing_successful": result.success,
            "context_used": result.context_used,
            "weight_data_calculated": bool(result.weight_data),
            "conversation_id": conversation_id
        }
        
        # Données de poids si calculées
        if result.weight_data:
            classification_info["weight_calculation"] = {
                "breed": result.weight_data.get('breed'),
                "age_days": result.weight_data.get('age_days'),
                "sex": result.weight_data.get('sex'),
                "weight_range": result.weight_data.get('weight_range'),
                "target_weight": result.weight_data.get('target_weight'),
                "data_source": result.weight_data.get('data_source', 'intelligent_system_config')
            }
        
        # Fusionner toutes les données
        response_data.update(optional_fields)
        response_data["classification_result"] = classification_info
        
        # Informations de contexte conversationnel AVEC normalisation
        response_data["contextual_features"] = {
            "context_detection_enabled": self.config["enable_context"],
            "clarification_detection": True,
            "entity_inheritance": True,
            "entity_normalization": self.config["enable_normalization"],  # NOUVEAU
            "weight_data_calculation": True,
            "conversation_persistence": True
        }
        
        # NOUVEAU: Statistiques de normalisation
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
        
        # Gestion d'erreur si échec
        if not result.success:
            response_data["error_details"] = {
                "error_message": result.error,
                "fallback_used": True,
                "original_processing_failed": True,
                "context_available": bool(getattr(request, 'conversation_id', None)),
                "normalization_attempted": self.config["enable_normalization"]
            }
        
        if MODELS_AVAILABLE:
            return EnhancedExpertResponse(**response_data)
        else:
            return EnhancedExpertResponse(**response_data)

    def _create_error_response(self, request: EnhancedQuestionRequest, error: str) -> EnhancedExpertResponse:
        """Crée une réponse d'erreur compatible avec normalisation et contexte"""
        
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
            mode="error_fallback_normalized",  # NOUVEAU: Version avec normalisation
            logged=True,
            validation_passed=False,
            error_details={
                "error": error, 
                "system": "unified_expert_service_v2_normalized",  # NOUVEAU
                "context_available": bool(getattr(request, 'conversation_id', None)),
                "normalization_enabled": self.config["enable_normalization"]  # NOUVEAU
            }
        )

    def _generate_fallback_response(self, question: str, language: str = "fr") -> str:
        """Génère une réponse de fallback en cas d'erreur (conservée)"""
        
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

    def _update_stats(self, response_type: ResponseType, processing_time_ms: int, 
                     success: bool, context_used: bool = False, normalization_used: bool = False):
        """Met à jour les statistiques de traitement avec informations normalisées"""
        
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
        
        # Mise à jour du taux d'utilisation du contexte
        if context_used:
            total_context_usage = self.stats["context_usage_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["context_usage_rate"] = (total_context_usage + 1) / self.stats["questions_processed"]
        else:
            total_context_usage = self.stats["context_usage_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["context_usage_rate"] = total_context_usage / self.stats["questions_processed"]
        
        # NOUVEAU: Mise à jour du taux de normalisation
        if normalization_used:
            total_normalization = self.stats["normalization_success_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["normalization_success_rate"] = (total_normalization + 1) / self.stats["questions_processed"]
        else:
            total_normalization = self.stats["normalization_success_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["normalization_success_rate"] = total_normalization / self.stats["questions_processed"]
        
        # Mise à jour du temps moyen (moyenne mobile)
        current_avg = self.stats["average_processing_time_ms"]
        total_questions = self.stats["questions_processed"]
        
        self.stats["average_processing_time_ms"] = int(
            (current_avg * (total_questions - 1) + processing_time_ms) / total_questions
        )

    def get_system_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques système pour monitoring avec informations de normalisation"""
        
        total_questions = self.stats["questions_processed"]
        
        if total_questions == 0:
            return {
                "service_status": "ready",
                "version": "unified_v2.0.0_normalized",  # NOUVEAU: Version avec normalisation
                "questions_processed": 0,
                "statistics": "No questions processed yet",
                "normalization_features": {  # NOUVEAU: Features de normalisation
                    "entity_normalization": "enabled" if self.config["enable_normalization"] else "disabled",
                    "breed_standardization": "enabled",
                    "age_conversion": "enabled",
                    "sex_mapping": "enabled"
                }
            }
        
        success_rate = ((total_questions - self.stats["errors"]) / total_questions) * 100
        
        return {
            "service_status": "active",
            "version": "unified_v2.0.0_normalized",  # NOUVEAU
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
            "normalization_metrics": {  # NOUVEAU: Métriques de normalisation
                "normalization_success_rate": round(self.stats["normalization_success_rate"] * 100, 2),
                "entities_normalized_count": self.stats["entities_normalized"],
                "normalization_enabled": self.config["enable_normalization"],
                "normalizer_stats": self.entity_normalizer.get_stats()
            },
            "performance": {
                "average_processing_time_ms": self.stats["average_processing_time_ms"],
                "system_components": {
                    "entities_extractor": "active",
                    "entity_normalizer": "active" if self.config["enable_normalization"] else "disabled",  # NOUVEAU
                    "smart_classifier": "active_contextual",
                    "response_generator": "active_contextual",
                    "conversation_context_manager": "active" if self.config["enable_context"] else "disabled"
                }
            },
            "configuration": self.config,
            "timestamp": datetime.now().isoformat()
        }

    def reset_stats(self):
        """Remet à zéro les statistiques (mise à jour avec nouvelles métriques)"""
        self.stats = {
            "questions_processed": 0,
            "precise_answers": 0,
            "general_answers": 0,
            "clarifications": 0,
            "contextual_answers": 0,
            "entities_normalized": 0,  # NOUVEAU
            "normalization_success_rate": 0.0,  # NOUVEAU
            "errors": 0,
            "average_processing_time_ms": 0,
            "context_usage_rate": 0.0
        }
        logger.info("📊 [Expert Service] Statistiques remises à zéro (version normalisée)")

    def update_config(self, new_config: Dict[str, Any]):
        """Met à jour la configuration du service"""
        self.config.update(new_config)
        logger.info(f"⚙️ [Expert Service] Configuration mise à jour: {new_config}")
        
        # NOUVEAU: Réactualiser le normalizer si config changée
        if "enable_normalization" in new_config:
            logger.info(f"🔧 [Expert Service] Normalisation {'activée' if new_config['enable_normalization'] else 'désactivée'}")

    def get_contextual_debug_info(self, conversation_id: str) -> Dict[str, Any]:
        """Récupère les informations de debug contextuelles avec normalisation"""
        try:
            context = self.smart_classifier._get_conversation_context(conversation_id)
            
            return {
                "conversation_id": conversation_id,
                "context_available": context is not None,
                "context_fresh": context.is_fresh() if context else False,
                "context_data": context.to_dict() if context else None,
                "classifier_stats": self.smart_classifier.get_classification_stats(),
                "normalizer_stats": self.entity_normalizer.get_stats(),  # NOUVEAU
                "service_version": "v2.0.0_normalized"  # NOUVEAU
            }
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur debug contextuel: {e}")
            return {
                "conversation_id": conversation_id,
                "error": str(e),
                "context_available": False,
                "normalization_available": self.config["enable_normalization"]  # NOUVEAU
            }

    def get_normalization_debug_info(self, raw_entities: Dict[str, Any]) -> Dict[str, Any]:
        """NOUVEAU: Récupère les informations de debug pour la normalisation"""
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
                "normalizer_stats": self.entity_normalizer.get_stats()
            }
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur debug normalisation: {e}")
            return {
                "error": str(e),
                "raw_entities": raw_entities,
                "normalization_failed": True
            }

# =============================================================================
# FONCTIONS UTILITAIRES ET TESTS AVEC NORMALISATION
# =============================================================================

async def quick_ask(question: str, conversation_id: str = None, language: str = "fr") -> str:
    """Interface rapide pour poser une question avec support normalisation et contexte"""
    service = ExpertService()
    context = {"conversation_id": conversation_id} if conversation_id else None
    result = await service.process_question(question, context=context, language=language)
    return result.response

def create_expert_service() -> ExpertService:
    """Factory pour créer une instance du service avec normalisation et contexte"""
    return ExpertService()

# =============================================================================
# TESTS INTÉGRÉS AVEC NORMALISATION ET CONTEXTE COMPLET
# =============================================================================

async def test_expert_service_normalized():
    """Tests du service expert avec normalisation et contexte conversationnel complet"""
    
    print("🧪 Tests du Service Expert avec Normalisation et Contexte")
    print("=" * 80)
    
    service = ExpertService()
    conversation_id = "test_conv_normalized_ross308"
    
    test_cases = [
        # Cas 1: Test normalisation races (variantes d'écriture)
        {
            "question": "Quel est le poids d'un ross308 à 12 jours ?",
            "context": {"conversation_id": conversation_id},
            "expected_type": "general",
            "description": "Test normalisation: ross308 → Ross 308"
        },
        
        # Cas 2: Test normalisation âge (semaines → jours)
        {
            "question": "Poids cobb500 à 3 semaines ?",
            "context": {"conversation_id": f"{conversation_id}_2"},
            "expected_type": "general", 
            "description": "Test normalisation: cobb500 → Cobb 500, 3 sem → 21j"
        },
        
        # Cas 3: Test normalisation sexe + clarification contextuelle
        {
            "question": "Pour des mâles",
            "context": {
                "conversation_id": conversation_id,
                "is_clarification_response": True
            },
            "expected_type": "contextual",
            "description": "Test clarification avec sexe normalisé: mâles → male"
        },
        
        # Cas 4: Test avec entités multiples à normaliser
        {
            "question": "poids isa brown femelles 20 semaines ?",
            "context": {"conversation_id": f"{conversation_id}_3"},
            "expected_type": "precise",
            "description": "Test normalisation complète: isa brown → ISA Brown, femelles → female, 20 sem → 140j"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['description']}")
        print(f"   Question: {test_case['question']}")
        print(f"   Type attendu: {test_case['expected_type']}")
        
        try:
            result = await service.process_question(
                test_case['question'], 
                context=test_case['context']
            )
            
            status = "✅" if result.success else "❌"
            print(f"   {status} Type obtenu: {result.response_type}")
            print(f"   ⏱️ Temps: {result.processing_time_ms}ms")
            print(f"   🎯 Confiance: {result.confidence:.2f}")
            print(f"   🔗 Contexte utilisé: {'Oui' if result.context_used else 'Non'}")
            
            # NOUVEAU: Afficher informations de normalisation
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
            
            if len(result.response) > 150:
                preview = result.response[:150] + "..."
            else:
                preview = result.response
            print(f"   💬 Réponse: {preview}")
            
            # Vérification spéciale pour les tests avec normalisation
            if i == 1 and result.normalized_entities and result.normalized_entities.breed == "Ross 308":
                print("   ✅ SUCCESS: Normalisation race ross308 → Ross 308!")
            if i == 2 and result.normalized_entities and result.normalized_entities.age_days == 21:
                print("   ✅ SUCCESS: Normalisation âge 3 semaines → 21 jours!")
            
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
    print(f"   Temps moyen: {stats['performance']['average_processing_time_ms']}ms")
    
    # NOUVEAU: Test spécifique de normalisation
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
    asyncio.run(test_expert_service_normalized())