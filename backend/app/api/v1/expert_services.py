"""
expert_services.py - SERVICE PRINCIPAL AVEC CONTEXTE CONVERSATIONNEL COMPLET

🎯 AMÉLIORATIONS INTÉGRÉES:
- ✅ Gestion complète du contexte conversationnel
- ✅ Support du type CONTEXTUAL_ANSWER
- ✅ Passage du conversation_id au classifier
- ✅ Intégration avec la base de données existante
- ✅ Compatibilité totale avec l'ancien système

NOUVEAU FLUX:
1. Récupération du conversation_id depuis la requête
2. Passage du conversation_id au classifier intelligent
3. Classifier détecte les clarifications et fusionne le contexte
4. Response Generator utilise les weight_data pour réponse précise
5. Résultat: "Ross 308 mâle à 12 jours : 380-420g" 🎯
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

# Imports des nouveaux modules avec contexte
from .entities_extractor import EntitiesExtractor, ExtractedEntities
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
    """Résultat du traitement d'une question avec contexte"""
    def __init__(self, success: bool, response: str, response_type: str, 
                 confidence: float, entities: ExtractedEntities, 
                 processing_time_ms: int, error: str = None,
                 context_used: bool = False, weight_data: Dict[str, Any] = None):
        self.success = success
        self.response = response
        self.response_type = response_type
        self.confidence = confidence
        self.entities = entities
        self.processing_time_ms = processing_time_ms
        self.error = error
        self.context_used = context_used  # NOUVEAU: Indique si le contexte a été utilisé
        self.weight_data = weight_data or {}  # NOUVEAU: Données de poids calculées
        self.timestamp = datetime.now().isoformat()

class ExpertService:
    """Service expert unifié avec support du contexte conversationnel"""
    
    def __init__(self, db_path: str = "conversations.db"):
        """Initialisation du service avec les composants contextuels"""
        self.entities_extractor = EntitiesExtractor()
        self.smart_classifier = SmartClassifier(db_path=db_path)  # NOUVEAU: Passer db_path
        self.response_generator = UnifiedResponseGenerator()
        
        # Statistiques pour monitoring (améliorées)
        self.stats = {
            "questions_processed": 0,
            "precise_answers": 0,
            "general_answers": 0,
            "clarifications": 0,
            "contextual_answers": 0,  # NOUVEAU: Compteur pour réponses contextuelles
            "errors": 0,
            "average_processing_time_ms": 0,
            "context_usage_rate": 0.0  # NOUVEAU: Taux d'utilisation du contexte
        }
        
        # Configuration
        self.config = {
            "enable_logging": True,
            "enable_stats": True,
            "enable_context": True,  # NOUVEAU: Activer le contexte conversationnel
            "max_processing_time_ms": 10000,  # 10 secondes max
            "fallback_enabled": True,
            "context_expiry_minutes": 10  # NOUVEAU: Expiration du contexte
        }
        
        logger.info("✅ [Expert Service] Service unifié avec contexte initialisé")
        logger.info(f"   📊 Extracteur: {self.entities_extractor.get_extraction_stats()}")
        logger.info(f"   🧠 Classifier: {self.smart_classifier.get_classification_stats()}")
        logger.info(f"   🔗 Contexte: {'Activé' if self.config['enable_context'] else 'Désactivé'}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> ProcessingResult:
        """
        POINT D'ENTRÉE PRINCIPAL - Traite une question avec contexte conversationnel
        
        Args:
            question: Question à traiter
            context: Contexte optionnel (conversation_id, user_id, is_clarification_response)
            language: Langue de réponse
            
        Returns:
            ProcessingResult avec la réponse et les métadonnées contextuelles
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
            
            # 1️⃣ EXTRACTION DES ENTITÉS
            entities = self.entities_extractor.extract(question)
            logger.info(f"   🔍 Entités extraites: {entities}")
            
            # 2️⃣ CLASSIFICATION INTELLIGENTE AVEC CONTEXTE
            classification = self.smart_classifier.classify_question(
                question, 
                self._entities_to_dict(entities),
                conversation_id=conversation_id,  # NOUVEAU: Passer le conversation_id
                is_clarification_response=is_clarification_response  # NOUVEAU: Flag clarification
            )
            
            logger.info(f"   🧠 Classification: {classification.response_type.value} (confiance: {classification.confidence})")
            
            # Vérifier si le contexte a été utilisé
            context_used = classification.response_type == ResponseType.CONTEXTUAL_ANSWER
            if context_used:
                logger.info("   🔗 Contexte conversationnel utilisé pour la réponse")
            
            # 3️⃣ GÉNÉRATION DE LA RÉPONSE AVEC SUPPORT CONTEXTUEL
            # Utiliser les entités fusionnées si disponibles
            entities_for_generation = classification.merged_entities if classification.merged_entities else self._entities_to_dict(entities)
            
            response_data = self.response_generator.generate(question, entities_for_generation, classification)
            logger.info(f"   🎨 Réponse générée: {response_data.response_type}")
            
            # Afficher les données de poids si calculées
            if classification.weight_data:
                weight_range = classification.weight_data.get('weight_range')
                if weight_range:
                    logger.info(f"   📊 Données de poids: {weight_range[0]}-{weight_range[1]}g")
            
            # 4️⃣ FORMATAGE FINAL
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = ProcessingResult(
                success=True,
                response=response_data.response,
                response_type=response_data.response_type,
                confidence=response_data.confidence,
                entities=entities,
                processing_time_ms=processing_time_ms,
                context_used=context_used,  # NOUVEAU: Indiquer utilisation du contexte
                weight_data=classification.weight_data  # NOUVEAU: Données de poids
            )
            
            # 5️⃣ MISE À JOUR DES STATISTIQUES AVEC CONTEXTE
            self._update_stats(classification.response_type, processing_time_ms, True, context_used)
            
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
            
            self._update_stats(ResponseType.NEEDS_CLARIFICATION, processing_time_ms, False, False)
            return result

    async def ask_expert_enhanced(self, request: EnhancedQuestionRequest) -> EnhancedExpertResponse:
        """
        Interface compatible avec l'ancien système - AMÉLIORÉE avec contexte
        
        Args:
            request: Requête formatée selon l'ancien modèle
            
        Returns:
            EnhancedExpertResponse compatible avec l'ancien système
        """
        try:
            # NOUVEAU: Extraire plus d'informations contextuelles
            context = {
                "conversation_id": getattr(request, 'conversation_id', None),
                "user_id": getattr(request, 'user_id', None),
                "is_clarification_response": getattr(request, 'is_clarification_response', False),
                "original_question": getattr(request, 'original_question', None),
                "clarification_entities": getattr(request, 'clarification_entities', None),
                "concision_level": getattr(request, 'concision_level', 'standard')
            }
            
            # Traitement unifié avec contexte
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

    def _entities_to_dict(self, entities: ExtractedEntities) -> Dict[str, Any]:
        """Convertit les entités en dictionnaire pour compatibilité"""
        return {
            'age_days': entities.age_days,
            'age_weeks': entities.age_weeks,
            'age': entities.age,
            'breed_specific': entities.breed_specific,
            'breed_generic': entities.breed_generic,
            'sex': entities.sex,
            'weight_mentioned': entities.weight_mentioned,
            'weight_grams': entities.weight_grams,
            'weight_unit': entities.weight_unit,
            'symptoms': entities.symptoms,
            'context_type': entities.context_type,
            'housing_conditions': entities.housing_conditions,
            'feeding_context': entities.feeding_context
        }

    def _convert_to_legacy_response(self, request: EnhancedQuestionRequest, 
                                  result: ProcessingResult) -> EnhancedExpertResponse:
        """Convertit le résultat moderne vers le format legacy avec données contextuelles"""
        
        conversation_id = getattr(request, 'conversation_id', None) or str(uuid.uuid4())
        language = getattr(request, 'language', 'fr')
        
        # Données de base obligatoires
        response_data = {
            "question": request.text,
            "response": result.response,
            "conversation_id": conversation_id,
            "rag_used": False,  # Le nouveau système n'utilise plus RAG
            "timestamp": result.timestamp,
            "language": language,
            "response_time_ms": result.processing_time_ms,
            "mode": "unified_intelligent_system_v2_contextual"  # NOUVEAU: Version avec contexte
        }
        
        # Ajout des champs optionnels pour compatibilité (améliorés)
        optional_fields = {
            "user": getattr(request, 'user_id', None),
            "logged": True,
            "validation_passed": result.success,
            "processing_steps": [
                "entities_extraction",
                "smart_classification_with_context",  # NOUVEAU: Avec contexte
                "unified_response_generation",
                "contextual_data_calculation" if result.context_used else "standard_processing"
            ],
            "ai_enhancements_used": [
                "smart_classifier_v2_contextual",  # NOUVEAU: Version contextuelle
                "unified_generator_v2_contextual",
                "entities_extractor_v1",
                "conversation_context_manager" if result.context_used else None
            ]
        }
        
        # NOUVEAU: Informations de classification contextuelles
        classification_info = {
            "response_type_detected": result.response_type,
            "confidence_score": result.confidence,
            "entities_extracted": self._entities_to_dict(result.entities),
            "processing_successful": result.success,
            "context_used": result.context_used,  # NOUVEAU: Contexte utilisé
            "weight_data_calculated": bool(result.weight_data),  # NOUVEAU: Données calculées
            "conversation_id": conversation_id
        }
        
        # NOUVEAU: Données de poids si calculées
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
        
        # NOUVEAU: Informations de contexte conversationnel
        response_data["contextual_features"] = {
            "context_detection_enabled": self.config["enable_context"],
            "clarification_detection": True,
            "entity_inheritance": True,
            "weight_data_calculation": True,
            "conversation_persistence": True
        }
        
        # Gestion d'erreur si échec
        if not result.success:
            response_data["error_details"] = {
                "error_message": result.error,
                "fallback_used": True,
                "original_processing_failed": True,
                "context_available": bool(getattr(request, 'conversation_id', None))
            }
        
        if MODELS_AVAILABLE:
            return EnhancedExpertResponse(**response_data)
        else:
            # Fallback si modèles pas disponibles
            return EnhancedExpertResponse(**response_data)

    def _create_error_response(self, request: EnhancedQuestionRequest, error: str) -> EnhancedExpertResponse:
        """Crée une réponse d'erreur compatible avec contexte"""
        
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
            mode="error_fallback_contextual",
            logged=True,
            validation_passed=False,
            error_details={
                "error": error, 
                "system": "unified_expert_service_v2_contextual",
                "context_available": bool(getattr(request, 'conversation_id', None))
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
                     success: bool, context_used: bool = False):
        """Met à jour les statistiques de traitement avec informations contextuelles"""
        
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
            elif response_type == ResponseType.CONTEXTUAL_ANSWER:  # NOUVEAU
                self.stats["contextual_answers"] += 1
        else:
            self.stats["errors"] += 1
        
        # NOUVEAU: Mise à jour du taux d'utilisation du contexte
        if context_used:
            total_context_usage = self.stats["context_usage_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["context_usage_rate"] = (total_context_usage + 1) / self.stats["questions_processed"]
        else:
            total_context_usage = self.stats["context_usage_rate"] * (self.stats["questions_processed"] - 1)
            self.stats["context_usage_rate"] = total_context_usage / self.stats["questions_processed"]
        
        # Mise à jour du temps moyen (moyenne mobile)
        current_avg = self.stats["average_processing_time_ms"]
        total_questions = self.stats["questions_processed"]
        
        self.stats["average_processing_time_ms"] = int(
            (current_avg * (total_questions - 1) + processing_time_ms) / total_questions
        )

    def get_system_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques système pour monitoring avec informations contextuelles"""
        
        total_questions = self.stats["questions_processed"]
        
        if total_questions == 0:
            return {
                "service_status": "ready",
                "version": "unified_v2.0.0_contextual",
                "questions_processed": 0,
                "statistics": "No questions processed yet",
                "contextual_features": {
                    "conversation_context": "enabled",
                    "clarification_detection": "enabled",
                    "weight_data_calculation": "enabled"
                }
            }
        
        success_rate = ((total_questions - self.stats["errors"]) / total_questions) * 100
        
        return {
            "service_status": "active",
            "version": "unified_v2.0.0_contextual",
            "questions_processed": total_questions,
            "success_rate_percent": round(success_rate, 2),
            "response_distribution": {
                "precise_answers": self.stats["precise_answers"],
                "general_answers": self.stats["general_answers"], 
                "clarifications": self.stats["clarifications"],
                "contextual_answers": self.stats["contextual_answers"],  # NOUVEAU
                "errors": self.stats["errors"]
            },
            "contextual_metrics": {  # NOUVEAU: Métriques contextuelles
                "context_usage_rate": round(self.stats["context_usage_rate"] * 100, 2),
                "contextual_answers_count": self.stats["contextual_answers"],
                "context_enabled": self.config["enable_context"]
            },
            "performance": {
                "average_processing_time_ms": self.stats["average_processing_time_ms"],
                "system_components": {
                    "entities_extractor": "active",
                    "smart_classifier": "active_contextual",  # NOUVEAU
                    "response_generator": "active_contextual",  # NOUVEAU
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
            "contextual_answers": 0,  # NOUVEAU
            "errors": 0,
            "average_processing_time_ms": 0,
            "context_usage_rate": 0.0  # NOUVEAU
        }
        logger.info("📊 [Expert Service] Statistiques remises à zéro (version contextuelle)")

    def update_config(self, new_config: Dict[str, Any]):
        """Met à jour la configuration du service"""
        self.config.update(new_config)
        logger.info(f"⚙️ [Expert Service] Configuration mise à jour: {new_config}")

    def get_contextual_debug_info(self, conversation_id: str) -> Dict[str, Any]:
        """NOUVEAU: Récupère les informations de debug contextuelles"""
        try:
            context = self.smart_classifier._get_conversation_context(conversation_id)
            
            return {
                "conversation_id": conversation_id,
                "context_available": context is not None,
                "context_fresh": context.is_fresh() if context else False,
                "context_data": context.to_dict() if context else None,
                "classifier_stats": self.smart_classifier.get_classification_stats(),
                "service_version": "v2.0.0_contextual"
            }
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur debug contextuel: {e}")
            return {
                "conversation_id": conversation_id,
                "error": str(e),
                "context_available": False
            }

# =============================================================================
# FONCTIONS UTILITAIRES ET TESTS
# =============================================================================

async def quick_ask(question: str, conversation_id: str = None, language: str = "fr") -> str:
    """Interface rapide pour poser une question avec support contextuel"""
    service = ExpertService()
    context = {"conversation_id": conversation_id} if conversation_id else None
    result = await service.process_question(question, context=context, language=language)
    return result.response

def create_expert_service() -> ExpertService:
    """Factory pour créer une instance du service avec contexte"""
    return ExpertService()

# =============================================================================
# TESTS INTÉGRÉS AVEC CONTEXTE COMPLET
# =============================================================================

async def test_expert_service_contextual():
    """Tests du service expert avec contexte conversationnel complet"""
    
    print("🧪 Tests du Service Expert avec Contexte Conversationnel")
    print("=" * 70)
    
    service = ExpertService()
    conversation_id = "test_conv_ross308_12j"
    
    test_cases = [
        # Cas 1: Question générale qui établit le contexte
        {
            "question": "Quel est le poids cible d'un poulet de 12 jours ?",
            "context": {"conversation_id": conversation_id},
            "expected_type": "general",
            "description": "Question générale qui établit âge=12j et contexte=performance"
        },
        
        # Cas 2: Clarification qui devrait fusionner le contexte
        {
            "question": "Pour un Ross 308 male",
            "context": {
                "conversation_id": conversation_id, 
                "is_clarification_response": True
            },
            "expected_type": "contextual",
            "description": "Clarification qui devrait donner Ross 308 mâle 12j → 380-420g"
        },
        
        # Cas 3: Question précise sans contexte
        {
            "question": "Poids Ross 308 femelle 21 jours ?",
            "context": {"conversation_id": "new_conv_123"},
            "expected_type": "precise",
            "description": "Question précise complète sans besoin de contexte"
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
            
            # Afficher les données de poids si calculées
            if result.weight_data and 'weight_range' in result.weight_data:
                weight_range = result.weight_data['weight_range']
                print(f"   📊 Poids calculé: {weight_range[0]}-{weight_range[1]}g")
            
            if len(result.response) > 150:
                preview = result.response[:150] + "..."
            else:
                preview = result.response
            print(f"   💬 Réponse: {preview}")
            
            # Vérification spéciale pour le test Ross 308
            if i == 2 and "380" in result.response and "420" in result.response:
                print("   ✅ SUCCESS: Ross 308 mâle 12j correctement calculé!")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print(f"\n📊 Statistiques finales:")
    stats = service.get_system_stats()
    print(f"   Questions traitées: {stats['questions_processed']}")
    print(f"   Taux de succès: {stats['success_rate_percent']:.1f}%")
    print(f"   Réponses contextuelles: {stats['contextual_metrics']['contextual_answers_count']}")
    print(f"   Taux d'utilisation contexte: {stats['contextual_metrics']['context_usage_rate']:.1f}%")
    print(f"   Temps moyen: {stats['performance']['average_processing_time_ms']}ms")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_expert_service_contextual())