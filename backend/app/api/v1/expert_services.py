"""
expert_services.py - SERVICE PRINCIPAL SIMPLIFIÉ

🎯 REMPLACE: Tous les services complexes et contradictoires
🚀 PRINCIPE: Un seul point d'entrée, logique claire et unifiée
✨ SIMPLE: Flux linéaire sans conflits

Architecture:
1. EntitiesExtractor -> Extraction des informations
2. SmartClassifier -> Décision du type de réponse  
3. UnifiedResponseGenerator -> Génération de la réponse
4. Formatage final -> Réponse standardisée

Fini les imports circulaires, les conflits de règles, et la complexité excessive !
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

# Imports des nouveaux modules simplifiés
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
    """Résultat du traitement d'une question"""
    def __init__(self, success: bool, response: str, response_type: str, 
                 confidence: float, entities: ExtractedEntities, 
                 processing_time_ms: int, error: str = None):
        self.success = success
        self.response = response
        self.response_type = response_type
        self.confidence = confidence
        self.entities = entities
        self.processing_time_ms = processing_time_ms
        self.error = error
        self.timestamp = datetime.now().isoformat()

class ExpertService:
    """Service expert unifié - Point d'entrée unique pour toutes les questions"""
    
    def __init__(self):
        """Initialisation du service avec les 3 composants principaux"""
        self.entities_extractor = EntitiesExtractor()
        self.smart_classifier = SmartClassifier()
        self.response_generator = UnifiedResponseGenerator()
        
        # Statistiques pour monitoring
        self.stats = {
            "questions_processed": 0,
            "precise_answers": 0,
            "general_answers": 0,
            "clarifications": 0,
            "errors": 0,
            "average_processing_time_ms": 0
        }
        
        # Configuration
        self.config = {
            "enable_logging": True,
            "enable_stats": True,
            "max_processing_time_ms": 10000,  # 10 secondes max
            "fallback_enabled": True
        }
        
        logger.info("✅ [Expert Service] Service unifié initialisé")
        logger.info(f"   📊 Extracteur: {self.entities_extractor.get_extraction_stats()}")
        logger.info(f"   🧠 Classifier: {self.smart_classifier.get_classification_stats()}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> ProcessingResult:
        """
        POINT D'ENTRÉE PRINCIPAL - Traite une question de A à Z
        
        Args:
            question: Question à traiter
            context: Contexte optionnel (conversation_id, user_id, etc.)
            language: Langue de réponse
            
        Returns:
            ProcessingResult avec la réponse et les métadonnées
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 [Expert Service] Traitement: '{question[:50]}...'")
            
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
            
            # 2️⃣ CLASSIFICATION INTELLIGENTE
            classification = self.smart_classifier.classify_question(question, self._entities_to_dict(entities))
            logger.info(f"   🧠 Classification: {classification.response_type.value} (confiance: {classification.confidence})")
            
            # 3️⃣ GÉNÉRATION DE LA RÉPONSE
            response_data = self.response_generator.generate(question, self._entities_to_dict(entities), classification)
            logger.info(f"   🎨 Réponse générée: {response_data.response_type}")
            
            # 4️⃣ FORMATAGE FINAL
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = ProcessingResult(
                success=True,
                response=response_data.response,
                response_type=response_data.response_type,
                confidence=response_data.confidence,
                entities=entities,
                processing_time_ms=processing_time_ms
            )
            
            # 5️⃣ MISE À JOUR DES STATISTIQUES
            self._update_stats(classification.response_type, processing_time_ms, True)
            
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
            
            self._update_stats(ResponseType.NEEDS_CLARIFICATION, processing_time_ms, False)
            return result

    async def ask_expert_enhanced(self, request: EnhancedQuestionRequest) -> EnhancedExpertResponse:
        """
        Interface compatible avec l'ancien système - Point d'entrée pour API
        
        Args:
            request: Requête formatée selon l'ancien modèle
            
        Returns:
            EnhancedExpertResponse compatible avec l'ancien système
        """
        try:
            # Traitement unifié
            context = {
                "conversation_id": getattr(request, 'conversation_id', None),
                "user_id": getattr(request, 'user_id', None),
                "is_clarification_response": getattr(request, 'is_clarification_response', False),
                "original_question": getattr(request, 'original_question', None)
            }
            
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
        """Convertit le résultat moderne vers le format legacy"""
        
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
            "mode": "unified_intelligent_system"
        }
        
        # Ajout des champs optionnels pour compatibilité
        optional_fields = {
            "user": getattr(request, 'user_id', None),
            "logged": True,
            "validation_passed": result.success,
            "processing_steps": [
                "entities_extraction",
                "smart_classification", 
                "unified_response_generation"
            ],
            "ai_enhancements_used": [
                "smart_classifier_v1",
                "unified_generator_v1",
                "entities_extractor_v1"
            ]
        }
        
        # Informations de classification pour debugging
        classification_info = {
            "response_type_detected": result.response_type,
            "confidence_score": result.confidence,
            "entities_extracted": self._entities_to_dict(result.entities),
            "processing_successful": result.success
        }
        
        # Fusionner toutes les données
        response_data.update(optional_fields)
        response_data["classification_result"] = classification_info
        
        # Gestion d'erreur si échec
        if not result.success:
            response_data["error_details"] = {
                "error_message": result.error,
                "fallback_used": True,
                "original_processing_failed": True
            }
        
        if MODELS_AVAILABLE:
            return EnhancedExpertResponse(**response_data)
        else:
            # Fallback si modèles pas disponibles
            return EnhancedExpertResponse(**response_data)

    def _create_error_response(self, request: EnhancedQuestionRequest, error: str) -> EnhancedExpertResponse:
        """Crée une réponse d'erreur compatible"""
        
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
            mode="error_fallback",
            logged=True,
            validation_passed=False,
            error_details={"error": error, "system": "unified_expert_service"}
        )

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

    def _update_stats(self, response_type: ResponseType, processing_time_ms: int, success: bool):
        """Met à jour les statistiques de traitement"""
        
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
        else:
            self.stats["errors"] += 1
        
        # Mise à jour du temps moyen (moyenne mobile)
        current_avg = self.stats["average_processing_time_ms"]
        total_questions = self.stats["questions_processed"]
        
        self.stats["average_processing_time_ms"] = int(
            (current_avg * (total_questions - 1) + processing_time_ms) / total_questions
        )

    def get_system_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques système pour monitoring"""
        
        total_questions = self.stats["questions_processed"]
        
        if total_questions == 0:
            return {
                "service_status": "ready",
                "questions_processed": 0,
                "statistics": "No questions processed yet"
            }
        
        success_rate = ((total_questions - self.stats["errors"]) / total_questions) * 100
        
        return {
            "service_status": "active",
            "version": "unified_v1.0.0",
            "questions_processed": total_questions,
            "success_rate_percent": round(success_rate, 2),
            "response_distribution": {
                "precise_answers": self.stats["precise_answers"],
                "general_answers": self.stats["general_answers"], 
                "clarifications": self.stats["clarifications"],
                "errors": self.stats["errors"]
            },
            "performance": {
                "average_processing_time_ms": self.stats["average_processing_time_ms"],
                "system_components": {
                    "entities_extractor": "active",
                    "smart_classifier": "active",
                    "response_generator": "active"
                }
            },
            "configuration": self.config,
            "timestamp": datetime.now().isoformat()
        }

    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            "questions_processed": 0,
            "precise_answers": 0,
            "general_answers": 0,
            "clarifications": 0,
            "errors": 0,
            "average_processing_time_ms": 0
        }
        logger.info("📊 [Expert Service] Statistiques remises à zéro")

    def update_config(self, new_config: Dict[str, Any]):
        """Met à jour la configuration du service"""
        self.config.update(new_config)
        logger.info(f"⚙️ [Expert Service] Configuration mise à jour: {new_config}")

# =============================================================================
# FONCTIONS UTILITAIRES ET TESTS
# =============================================================================

async def quick_ask(question: str, language: str = "fr") -> str:
    """Interface rapide pour poser une question"""
    service = ExpertService()
    result = await service.process_question(question, language=language)
    return result.response

def create_expert_service() -> ExpertService:
    """Factory pour créer une instance du service"""
    return ExpertService()

# =============================================================================
# TESTS INTÉGRÉS
# =============================================================================

async def test_expert_service():
    """Tests du service expert unifié"""
    
    print("🧪 Tests du Service Expert Unifié")
    print("=" * 60)
    
    service = ExpertService()
    
    test_cases = [
        # Cas précis (devrait donner une réponse spécifique)
        ("Quel est le poids d'un Ross 308 mâle de 21 jours ?", "precise"),
        
        # Cas général (devrait donner une réponse générale + offre de précision)
        ("Poids normal poulet 22 jours ?", "general"),
        
        # Cas clarification (vraiment trop vague)
        ("Mes poulets vont mal", "clarification"),
        
        # Cas santé avec contexte
        ("Poules 25 semaines font diarrhée depuis 2 jours", "general")
    ]
    
    for question, expected_type in test_cases:
        print(f"\n📝 Question: {question}")
        print(f"   🎯 Type attendu: {expected_type}")
        
        try:
            result = await service.process_question(question)
            status = "✅" if result.success else "❌"
            print(f"   {status} Type: {result.response_type}")
            print(f"   ⏱️ Temps: {result.processing_time_ms}ms")
            print(f"   🎯 Confiance: {result.confidence:.2f}")
            
            if len(result.response) > 100:
                preview = result.response[:100] + "..."
            else:
                preview = result.response
            print(f"   💬 Réponse: {preview}")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print(f"\n📊 Statistiques finales:")
    stats = service.get_system_stats()
    print(f"   Questions traitées: {stats['questions_processed']}")
    print(f"   Taux de succès: {stats['success_rate_percent']:.1f}%")
    print(f"   Temps moyen: {stats['performance']['average_processing_time_ms']}ms")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_expert_service())