"""
ai_fallback_system.py - SYSTÈME DE FALLBACK ROBUSTE

🎯 GARANTIT: Fonctionnement continu même si IA indisponible
🚀 CAPACITÉS:
- ✅ Fallback complet vers système existant
- ✅ Détection automatique des pannes IA
- ✅ Préservation de toute la logique actuelle
- ✅ Transition seamless IA ↔ Règles
- ✅ Monitoring des performances comparatives
- ✅ Recovery automatique quand IA revient

Architecture:
- Encapsulation des services existants
- Detection d'indisponibilité IA automatique
- Fallback transparent pour l'utilisateur
- Métriques comparatives IA vs Règles
- Recovery intelligent et monitoring continu
"""

import logging
import time
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class FallbackReason(Enum):
    """Raisons de fallback vers système classique"""
    AI_SERVICE_DOWN = "ai_service_down"
    AI_TIMEOUT = "ai_timeout"
    AI_QUOTA_EXCEEDED = "ai_quota_exceeded"
    AI_ERROR_RESPONSE = "ai_error_response"
    LOW_CONFIDENCE = "low_confidence"
    USER_PREFERENCE = "user_preference"
    EMERGENCY_MODE = "emergency_mode"

@dataclass
class FallbackResult:
    """Résultat du système de fallback"""
    response: str
    response_type: str
    confidence: float
    fallback_reason: FallbackReason
    processing_time_ms: int
    method_used: str  # "ai", "fallback_rules", "hybrid"
    original_error: Optional[str] = None

class AIFallbackSystem:
    """Système de fallback robuste préservant toute la logique existante"""
    
    def __init__(self):
        # Services existants (préservés intégralement)
        self._initialize_classic_services()
        
        # Configuration du fallback
        self.fallback_config = {
            "ai_timeout_seconds": 15,
            "max_ai_retries": 2,
            "emergency_mode": False,
            "min_ai_confidence": 0.3,
            "prefer_ai_when_available": True
        }
        
        # État du système
        self.system_state = {
            "ai_available": True,
            "last_ai_check": datetime.now(),
            "consecutive_ai_failures": 0,
            "emergency_mode_until": None
        }
        
        # Métriques comparatives
        self.comparative_metrics = {
            "ai_calls": {"total": 0, "successful": 0, "failed": 0, "avg_time": 0.0},
            "fallback_calls": {"total": 0, "successful": 0, "failed": 0, "avg_time": 0.0},
            "quality_comparison": {"ai_avg_confidence": 0.0, "fallback_avg_confidence": 0.0},
            "fallback_reasons": {reason.value: 0 for reason in FallbackReason}
        }
        
        logger.info("🛡️ [AI Fallback System] Initialisé avec préservation code existant")
    
    def _initialize_classic_services(self):
        """Initialise les services classiques (code existant préservé)"""
        
        try:
            # Import des services existants (préservés intégralement)
            from .entities_extractor import EntitiesExtractor
            from .smart_classifier import SmartClassifier
            from .unified_response_generator import UnifiedResponseGenerator
            from .expert_utils import extract_breed_and_sex_from_clarification, normalize_breed_name
            
            self.classic_entity_extractor = EntitiesExtractor()
            self.classic_classifier = SmartClassifier()
            self.classic_response_generator = UnifiedResponseGenerator()
            self.classic_utils = {
                "extract_clarification": extract_breed_and_sex_from_clarification,
                "normalize_breed": normalize_breed_name
            }
            
            logger.info("✅ [Fallback System] Services classiques initialisés")
            
        except ImportError as e:
            logger.error(f"❌ [Fallback System] Erreur import services classiques: {e}")
            self.classic_entity_extractor = None
            self.classic_classifier = None
            self.classic_response_generator = None
            self.classic_utils = {}
    
    async def process_with_intelligent_fallback(self,
                                              question: str,
                                              conversation_id: str = None,
                                              language: str = "fr",
                                              force_fallback: bool = False) -> FallbackResult:
        """
        Point d'entrée principal - Essaie IA puis fallback si nécessaire
        
        Args:
            question: Question de l'utilisateur
            conversation_id: ID de conversation
            language: Langue
            force_fallback: Force l'utilisation du fallback
            
        Returns:
            FallbackResult avec réponse et métriques
        """
        start_time = time.time()
        
        try:
            logger.info(f"🛡️ [Fallback System] Traitement: '{question[:50]}...' (force_fallback: {force_fallback})")
            
            # Vérifier si on doit utiliser le fallback directement
            if force_fallback or self._should_use_fallback():
                return await self._process_with_classic_system(question, conversation_id, language, start_time)
            
            # Essayer d'abord le système IA
            try:
                ai_result = await self._try_ai_processing(question, conversation_id, language, start_time)
                if ai_result:
                    return ai_result
                    
            except Exception as ai_error:
                logger.warning(f"⚠️ [Fallback System] IA échouée: {ai_error}")
                self._record_ai_failure(str(ai_error))
                
                # Fallback automatique vers système classique
                return await self._process_with_classic_system(
                    question, conversation_id, language, start_time, 
                    fallback_reason=FallbackReason.AI_ERROR_RESPONSE,
                    original_error=str(ai_error)
                )
            
            # Si on arrive ici, fallback par sécurité
            return await self._process_with_classic_system(
                question, conversation_id, language, start_time,
                fallback_reason=FallbackReason.AI_ERROR_RESPONSE
            )
            
        except Exception as e:
            logger.error(f"❌ [Fallback System] Erreur critique: {e}")
            return self._emergency_response(question, language, str(e), start_time)
    
    async def _try_ai_processing(self, 
                                question: str, 
                                conversation_id: str, 
                                language: str, 
                                start_time: float) -> Optional[FallbackResult]:
        """Essaie le traitement avec IA"""
        
        try:
            # Import du pipeline IA
            from .unified_ai_pipeline import get_unified_ai_pipeline
            
            ai_pipeline = get_unified_ai_pipeline()
            
            # Traitement avec timeout
            pipeline_result = await asyncio.wait_for(
                ai_pipeline.process_complete_pipeline(question, conversation_id, language),
                timeout=self.fallback_config["ai_timeout_seconds"]
            )
            
            # Vérifier la qualité du résultat
            if pipeline_result.confidence < self.fallback_config["min_ai_confidence"]:
                logger.warning(f"⚠️ [Fallback System] Confiance IA trop faible: {pipeline_result.confidence}")
                self._record_fallback_reason(FallbackReason.LOW_CONFIDENCE)
                return None
            
            # Enregistrer succès IA
            processing_time = int((time.time() - start_time) * 1000)
            self._record_ai_success(processing_time, pipeline_result.confidence)
            
            return FallbackResult(
                response=pipeline_result.final_response,
                response_type=pipeline_result.response_type,
                confidence=pipeline_result.confidence,
                fallback_reason=None,  # Pas de fallback
                processing_time_ms=processing_time,
                method_used="ai"
            )
            
        except asyncio.TimeoutError:
            logger.warning("⏰ [Fallback System] Timeout IA")
            self._record_fallback_reason(FallbackReason.AI_TIMEOUT)
            return None
            
        except ImportError:
            logger.error("❌ [Fallback System] Pipeline IA non disponible")
            self._record_fallback_reason(FallbackReason.AI_SERVICE_DOWN)
            return None
            
        except Exception as e:
            logger.error(f"❌ [Fallback System] Erreur IA: {e}")
            self._record_ai_failure(str(e))
            return None
    
    async def _process_with_classic_system(self,
                                         question: str,
                                         conversation_id: str,
                                         language: str,
                                         start_time: float,
                                         fallback_reason: FallbackReason = FallbackReason.AI_SERVICE_DOWN,
                                         original_error: str = None) -> FallbackResult:
        """Traitement avec le système classique (code existant préservé)"""
        
        try:
            logger.info(f"🔧 [Fallback System] Utilisation système classique (raison: {fallback_reason.value})")
            
            # ÉTAPE 1: Extraction d'entités classique
            if self.classic_entity_extractor:
                entities = self.classic_entity_extractor.extract(question)
                logger.info("✅ [Fallback] Entités extraites avec système classique")
            else:
                entities = self._basic_entity_extraction(question)
                logger.warning("⚠️ [Fallback] Extraction d'entités basique utilisée")
            
            # ÉTAPE 2: Classification classique
            if self.classic_classifier:
                classification = self.classic_classifier.classify_question(
                    question, entities, conversation_id
                )
                logger.info(f"✅ [Fallback] Classification: {classification.response_type.value}")
            else:
                classification = self._basic_classification(question, entities)
                logger.warning("⚠️ [Fallback] Classification basique utilisée")
            
            # ÉTAPE 3: Génération de réponse classique
            if self.classic_response_generator:
                response_data = self.classic_response_generator.generate(
                    question, entities, classification, conversation_id
                )
                logger.info("✅ [Fallback] Réponse générée avec système classique")
            else:
                response_data = self._basic_response_generation(question, entities, classification)
                logger.warning("⚠️ [Fallback] Génération de réponse basique utilisée")
            
            # Calculer métriques
            processing_time = int((time.time() - start_time) * 1000)
            confidence = getattr(response_data, 'confidence', 0.7)  # Confiance par défaut
            
            # Enregistrer succès fallback
            self._record_fallback_success(processing_time, confidence)
            self._record_fallback_reason(fallback_reason)
            
            return FallbackResult(
                response=getattr(response_data, 'response', str(response_data)),
                response_type=getattr(response_data, 'response_type', 'general_answer'),
                confidence=confidence,
                fallback_reason=fallback_reason,
                processing_time_ms=processing_time,
                method_used="fallback_rules",
                original_error=original_error
            )
            
        except Exception as e:
            logger.error(f"❌ [Fallback System] Erreur système classique: {e}")
            return self._emergency_response(question, language, str(e), start_time, fallback_reason)
    
    def _should_use_fallback(self) -> bool:
        """Détermine si on doit utiliser le fallback directement"""
        
        # Mode urgence activé
        if (self.system_state["emergency_mode_until"] and 
            datetime.now() < self.system_state["emergency_mode_until"]):
            return True
        
        # Trop de failures IA consécutifs
        if self.system_state["consecutive_ai_failures"] >= 3:
            return True
        
        # Configuration utilisateur
        if not self.fallback_config["prefer_ai_when_available"]:
            return True
        
        return False
    
    def _basic_entity_extraction(self, question: str) -> Dict[str, Any]:
        """Extraction d'entités ultra-basique en dernier recours"""
        
        import re
        
        entities = {
            "age_days": None,
            "breed_specific": None,
            "sex": None,
            "weight_mentioned": False,
            "context_type": "général"
        }
        
        # Âge basique
        age_match = re.search(r'(\d+)\s*(?:jour|day|j)', question.lower())
        if age_match:
            entities["age_days"] = int(age_match.group(1))
        
        # Races communes
        if "ross 308" in question.lower():
            entities["breed_specific"] = "Ross 308"
        elif "cobb 500" in question.lower():
            entities["breed_specific"] = "Cobb 500"
        
        # Sexe basique
        if any(word in question.lower() for word in ["mâle", "male"]):
            entities["sex"] = "male"
        elif any(word in question.lower() for word in ["femelle", "female"]):
            entities["sex"] = "female"
        
        # Poids mentionné
        entities["weight_mentioned"] = any(word in question.lower() for word in ["poids", "weight", "gramme", "kg"])
        
        return entities
    
    def _basic_classification(self, question: str, entities: Dict[str, Any]):
        """Classification ultra-basique"""
        
        # Mock classification result
        class BasicClassification:
            def __init__(self):
                self.response_type = self._determine_response_type(entities)
                self.confidence = 0.5
                self.reasoning = "Classification basique"
        
        classification = BasicClassification()
        classification.response_type.value = self._determine_response_type_value(entities)
        return classification
    
    def _determine_response_type_value(self, entities: Dict[str, Any]) -> str:
        """Détermine le type de réponse basiquement"""
        
        if entities.get("breed_specific") and entities.get("age_days"):
            return "precise_answer"
        elif entities.get("breed_specific") or entities.get("age_days"):
            return "general_answer"
        else:
            return "needs_clarification"
    
    def _basic_response_generation(self, question: str, entities: Dict[str, Any], classification):
        """Génération de réponse ultra-basique"""
        
        class BasicResponse:
            def __init__(self, content: str):
                self.response = content
                self.response_type = "general_answer"
                self.confidence = 0.5
        
        # Réponse basique selon contexte
        if entities.get("weight_mentioned"):
            content = f"Pour les questions de poids en élevage avicole, les standards varient selon la race, l'âge et le sexe. "
            
            if entities.get("breed_specific"):
                content += f"Pour {entities['breed_specific']}, "
            if entities.get("age_days"):
                content += f"à {entities['age_days']} jours, "
            
            content += "consultez un spécialiste avicole pour des valeurs précises adaptées à votre situation."
        
        else:
            content = "Pour votre question d'élevage avicole, je recommande de consulter un spécialiste ou vétérinaire avicole pour des conseils adaptés à votre situation spécifique."
        
        return BasicResponse(content)
    
    def _emergency_response(self, 
                          question: str, 
                          language: str, 
                          error: str, 
                          start_time: float,
                          fallback_reason: FallbackReason = FallbackReason.EMERGENCY_MODE) -> FallbackResult:
        """Réponse d'urgence absolue"""
        
        emergency_responses = {
            "fr": "Je rencontre des difficultés techniques temporaires. Pour vos questions d'élevage avicole, je vous recommande de consulter un vétérinaire spécialisé ou un technicien avicole qualifié.",
            "en": "I'm experiencing temporary technical difficulties. For your poultry farming questions, I recommend consulting a specialized veterinarian or qualified poultry technician.",
            "es": "Estoy experimentando dificultades técnicas temporales. Para sus preguntas de avicultura, recomiendo consultar a un veterinario especializado o técnico avícola calificado."
        }
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Activer mode urgence temporaire
        self.system_state["emergency_mode_until"] = datetime.now() + timedelta(minutes=5)
        
        return FallbackResult(
            response=emergency_responses.get(language, emergency_responses["fr"]),
            response_type="emergency",
            confidence=0.1,
            fallback_reason=fallback_reason,
            processing_time_ms=processing_time,
            method_used="emergency",
            original_error=error
        )
    
    def _record_ai_success(self, processing_time: int, confidence: float):
        """Enregistre un succès IA"""
        
        self.comparative_metrics["ai_calls"]["total"] += 1
        self.comparative_metrics["ai_calls"]["successful"] += 1
        
        # Moyenne pondérée du temps
        ai_calls = self.comparative_metrics["ai_calls"]
        ai_calls["avg_time"] = (ai_calls["avg_time"] * (ai_calls["total"] - 1) + processing_time) / ai_calls["total"]
        
        # Moyenne pondérée de la confiance
        current_avg = self.comparative_metrics["quality_comparison"]["ai_avg_confidence"]
        self.comparative_metrics["quality_comparison"]["ai_avg_confidence"] = (
            (current_avg * (ai_calls["successful"] - 1) + confidence) / ai_calls["successful"]
        )
        
        # Reset consecutive failures
        self.system_state["consecutive_ai_failures"] = 0
        self.system_state["ai_available"] = True
    
    def _record_ai_failure(self, error: str):
        """Enregistre un échec IA"""
        
        self.comparative_metrics["ai_calls"]["total"] += 1
        self.comparative_metrics["ai_calls"]["failed"] += 1
        self.system_state["consecutive_ai_failures"] += 1
        
        if self.system_state["consecutive_ai_failures"] >= 3:
            self.system_state["ai_available"] = False
    
    def _record_fallback_success(self, processing_time: int, confidence: float):
        """Enregistre un succès fallback"""
        
        self.comparative_metrics["fallback_calls"]["total"] += 1
        self.comparative_metrics["fallback_calls"]["successful"] += 1
        
        # Moyenne pondérée du temps
        fallback_calls = self.comparative_metrics["fallback_calls"]
        fallback_calls["avg_time"] = (fallback_calls["avg_time"] * (fallback_calls["total"] - 1) + processing_time) / fallback_calls["total"]
        
        # Moyenne pondérée de la confiance
        current_avg = self.comparative_metrics["quality_comparison"]["fallback_avg_confidence"]
        self.comparative_metrics["quality_comparison"]["fallback_avg_confidence"] = (
            (current_avg * (fallback_calls["successful"] - 1) + confidence) / fallback_calls["successful"]
        )
    
    def _record_fallback_reason(self, reason: FallbackReason):
        """Enregistre la raison du fallback"""
        self.comparative_metrics["fallback_reasons"][reason.value] += 1
    
    def get_fallback_health(self) -> Dict[str, Any]:
        """Retourne l'état de santé du système de fallback"""
        
        total_calls = (self.comparative_metrics["ai_calls"]["total"] + 
                      self.comparative_metrics["fallback_calls"]["total"])
        
        ai_usage_rate = (self.comparative_metrics["ai_calls"]["total"] / total_calls * 100) if total_calls > 0 else 0
        fallback_usage_rate = (self.comparative_metrics["fallback_calls"]["total"] / total_calls * 100) if total_calls > 0 else 0
        
        return {
            "system_name": "AI Fallback System",
            "ai_available": self.system_state["ai_available"],
            "consecutive_ai_failures": self.system_state["consecutive_ai_failures"],
            "emergency_mode_active": bool(
                self.system_state["emergency_mode_until"] and 
                datetime.now() < self.system_state["emergency_mode_until"]
            ),
            "usage_distribution": {
                "ai_usage_rate": round(ai_usage_rate, 2),
                "fallback_usage_rate": round(fallback_usage_rate, 2)
            },
            "performance_comparison": {
                "ai_avg_time_ms": round(self.comparative_metrics["ai_calls"]["avg_time"], 2),
                "fallback_avg_time_ms": round(self.comparative_metrics["fallback_calls"]["avg_time"], 2),
                "ai_avg_confidence": round(self.comparative_metrics["quality_comparison"]["ai_avg_confidence"], 3),
                "fallback_avg_confidence": round(self.comparative_metrics["quality_comparison"]["fallback_avg_confidence"], 3)
            },
            "fallback_reasons": self.comparative_metrics["fallback_reasons"],
            "classic_services_available": {
                "entity_extractor": self.classic_entity_extractor is not None,
                "classifier": self.classic_classifier is not None,
                "response_generator": self.classic_response_generator is not None
            }
        }
    
    def force_emergency_mode(self, duration_minutes: int = 10):
        """Force le mode urgence pour maintenance"""
        
        self.system_state["emergency_mode_until"] = datetime.now() + timedelta(minutes=duration_minutes)
        logger.warning(f"🆘 [Fallback System] Mode urgence forcé pour {duration_minutes} minutes")
    
    def reset_ai_failures(self):
        """Remet à zéro les compteurs d'échec IA"""
        
        self.system_state["consecutive_ai_failures"] = 0
        self.system_state["ai_available"] = True
        self.system_state["emergency_mode_until"] = None
        logger.info("🔄 [Fallback System] Compteurs d'échec IA remis à zéro")

# Instance globale pour utilisation facile
_ai_fallback_system = None

def get_ai_fallback_system() -> AIFallbackSystem:
    """Récupère l'instance singleton du système de fallback IA"""
    global _ai_fallback_system
    if _ai_fallback_system is None:
        _ai_fallback_system = AIFallbackSystem()
    return _ai_fallback_system

# Import asyncio pour timeout
import asyncio