"""
ai_validation_service.py - VALIDATION ET CLASSIFICATION AVEC IA

🎯 REMPLACE: Logique complexe de validation hardcodée par analyse IA intelligente
🚀 CAPACITÉS:
- ✅ Classification d'intention avec IA (performance, santé, alimentation)
- ✅ Validation de clarifications contextuelles
- ✅ Détection intelligente des types de réponse optimaux
- ✅ Analyse de cohérence des entités
- ✅ Recommandations de classification avec raisonnement
- ✅ Support du workflow conversationnel

Architecture:
- Classification basée sur compréhension du langage naturel
- Validation contextuelle des clarifications utilisateur
- Analyse de cohérence multi-entités
- Intégration seamless avec le smart_classifier existant
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .ai_service_manager import AIServiceType, call_ai, AIResponse

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types de réponse recommandés"""
    PRECISE_ANSWER = "precise_answer"
    CONTEXTUAL_ANSWER = "contextual_answer"  
    GENERAL_ANSWER = "general_answer"
    NEEDS_CLARIFICATION = "needs_clarification"

class IntentType(Enum):
    """Types d'intention détectés"""
    PERFORMANCE_QUERY = "performance"     # Poids, croissance, standards
    HEALTH_CONCERN = "santé"             # Symptômes, maladies, traitements
    FEEDING_QUESTION = "alimentation"     # Nutrition, aliments, rationing
    HOUSING_QUERY = "logement"           # Conditions, environnement
    GENERAL_INFO = "général"             # Questions générales
    CLARIFICATION = "clarification"       # Réponse à une demande de précision

@dataclass
class ValidationResult:
    """Résultat de validation d'une clarification"""
    is_valid_clarification: bool = False
    extracted_entities: Dict[str, Any] = None
    confidence: float = 0.0
    validation_reasoning: str = ""
    suggested_action: str = ""  # "accept", "request_more", "reject"
    
    def __post_init__(self):
        if self.extracted_entities is None:
            self.extracted_entities = {}

@dataclass
class ClassificationResult:
    """Résultat de classification d'intention"""
    intent_type: IntentType
    response_type: ResponseType
    confidence: float
    reasoning: str
    missing_entities: List[str] = None
    suggested_weight_calculation: bool = False
    urgency_level: str = "normal"  # normal, elevated, urgent
    
    def __post_init__(self):
        if self.missing_entities is None:
            self.missing_entities = []

class AIValidationService:
    """Service de validation et classification avec IA"""
    
    def __init__(self):
        # Configuration des modèles
        self.models = {
            "intent_classification": "gpt-4",     # Classification d'intention
            "entity_validation": "gpt-3.5-turbo", # Validation d'entités
            "clarification_analysis": "gpt-4",    # Analyse de clarifications
            "coherence_check": "gpt-3.5-turbo"    # Vérification de cohérence
        }
        
        # Prompts spécialisés
        self.prompts = self._initialize_prompts()
        
        # Règles de validation (backup)
        self.validation_rules = self._initialize_validation_rules()
        
        logger.info("🤖 [AI Validation Service] Initialisé avec classification IA intelligente")
    
    def _initialize_prompts(self) -> Dict[str, str]:
        """Initialise les prompts spécialisés pour validation/classification"""
        return {
            "intent_classification": """Analyse cette question d'élevage avicole et détermine l'intention et le type de réponse optimal.

QUESTION: "{question}"

ENTITÉS DÉTECTÉES:
{entities}

CONTEXTE CONVERSATIONNEL:
{context}

TÂCHE: Détermine l'intention réelle et le type de réponse le plus approprié.

TYPES D'INTENTION POSSIBLES:
1. **PERFORMANCE** - Questions sur poids, croissance, standards, développement
2. **SANTÉ** - Symptômes, maladies, traitements, problèmes sanitaires
3. **ALIMENTATION** - Nutrition, aliments, rationing, besoins nutritionnels
4. **LOGEMENT** - Conditions d'élevage, environnement, hébergement
5. **GÉNÉRAL** - Questions générales, informations de base
6. **CLARIFICATION** - Réponse à une demande de précision précédente

TYPES DE RÉPONSE OPTIMAUX:
- **PRECISE_ANSWER**: Assez d'informations pour réponse spécifique avec calculs
- **CONTEXTUAL_ANSWER**: Question de clarification qui complète un contexte précédent  
- **GENERAL_ANSWER**: Informations générales utiles avec offre de précision
- **NEEDS_CLARIFICATION**: Vraiment trop vague pour être utile

CRITÈRES DE DÉCISION:
- PRECISE_ANSWER: Race spécifique + âge + (sexe OU contexte performance)
- CONTEXTUAL_ANSWER: Clarification courte + contexte conversationnel riche
- GENERAL_ANSWER: Un élément manque mais question reste utile
- NEEDS_CLARIFICATION: Plusieurs éléments essentiels manquants

Réponds en JSON:
```json
{{
  "intent_type": "performance"|"santé"|"alimentation"|"logement"|"général"|"clarification",
  "response_type": "precise_answer"|"contextual_answer"|"general_answer"|"needs_clarification",
  "confidence": 0.0-1.0,
  "reasoning": "explication détaillée du raisonnement",
  "missing_entities": ["liste des entités manquantes"],
  "suggested_weight_calculation": true|false,
  "urgency_level": "normal"|"elevated"|"urgent",
  "key_factors": ["facteurs clés de la décision"]
}}
```

EXEMPLES:
- "Poids Ross 308 mâles 21 jours" → PERFORMANCE + PRECISE_ANSWER
- "Ross 308 male" (après question poids) → CLARIFICATION + CONTEXTUAL_ANSWER
- "Mes poulets sont malades" → SANTÉ + NEEDS_CLARIFICATION (symptoms manquants)
- "Poids normal à 3 semaines" → PERFORMANCE + GENERAL_ANSWER (race manquante)""",

            "clarification_validation": """Valide cette clarification utilisateur et extrait les entités pertinentes.

CLARIFICATION UTILISATEUR: "{clarification}"

CONTEXTE PRÉCÉDENT:
{previous_context}

QUESTION ORIGINALE: "{original_question}"

TÂCHE: Détermine si cette clarification est valide et suffisante.

ANALYSE REQUISE:
1. **VALIDITÉ**: La clarification apporte-t-elle des informations utiles ?
2. **COHÉRENCE**: Est-elle cohérente avec le contexte précédent ?
3. **COMPLÉTUDE**: Suffit-elle pour répondre à la question originale ?
4. **EXTRACTION**: Quelles entités spécifiques sont mentionnées ?

ENTITÉS À CHERCHER:
- Race/souche (Ross 308, Cobb 500, Hubbard, ISA Brown, etc.)
- Sexe (mâle, femelle, mixte, coq, poule)
- Âge (si mentionné)
- Contexte additionnel (conditions, objectifs)

EXEMPLES DE VALIDITÉ:
✅ VALIDE: "Ross 308 male" → race et sexe spécifiés
✅ VALIDE: "femelles de 3 semaines" → sexe et âge précisés
❌ INVALIDE: "oui" → aucune information
❌ INVALIDE: "les poulets" → trop vague

Réponds en JSON:
```json
{{
  "is_valid_clarification": true|false,
  "extracted_entities": {{
    "breed_specific": "Ross 308"|null,
    "sex": "male"|"female"|"mixed"|null,
    "age_days": number|null,
    "additional_context": "description"|null
  }},
  "confidence": 0.0-1.0,
  "validation_reasoning": "explication de la validation",
  "suggested_action": "accept"|"request_more"|"reject",
  "missing_for_complete_answer": ["entités encore manquantes"]
}}
```""",

            "entity_coherence_check": """Vérifie la cohérence et validité de ces entités d'élevage avicole.

ENTITÉS À VÉRIFIER:
{entities}

QUESTION CONTEXTE: "{question}"

TÂCHE: Vérifie la logique et cohérence des combinaisons d'entités.

VÉRIFICATIONS:
1. **COHÉRENCE BIOLOGIQUE**: Combinaisons réalistes (race-âge-poids)
2. **LOGIQUE TEMPORELLE**: Âges cohérents avec stades de développement
3. **SPÉCIFICITÉ RACIALE**: Compatibilité race-usage (chair vs ponte)
4. **RANGES NORMAUX**: Valeurs dans les fourchettes attendues

EXEMPLES D'INCOHÉRENCES:
❌ ISA Brown (pondeuses) + 21 jours + poids 1000g (trop lourd pour pondeuses)
❌ Ross 308 + 50 semaines (races de chair ne vivent pas si longtemps)
❌ Âge 5 jours + poids 500g (croissance impossible)
✅ Ross 308 + 21 jours + poids 800g + mâle (cohérent)

Réponds en JSON:
```json
{{
  "entities_coherent": true|false,
  "coherence_score": 0.0-1.0,
  "issues_found": ["liste des problèmes détectés"],
  "corrected_entities": {{"entités corrigées si nécessaire"}},
  "confidence_level": "high"|"medium"|"low",
  "validation_notes": "explication des vérifications"
}}
```""",

            "contextual_analysis": """Analyse cette question dans son contexte pour déterminer si c'est une clarification contextuelle.

QUESTION ACTUELLE: "{current_question}"

HISTORIQUE CONVERSATION:
{conversation_history}

ENTITÉS ACTUELLES: {current_entities}

TÂCHE: Détermine si cette question fait suite logiquement à la conversation précédente.

INDICATEURS DE CLARIFICATION CONTEXTUELLE:
1. **QUESTION COURTE** avec entités spécifiques (≤ 5 mots)
2. **RÉFÉRENCES CONTEXTUELLES** ("pour un", "avec des", "race X")
3. **COMPLÉMENTARITÉ** avec question précédente
4. **PROGRESSION LOGIQUE** de la conversation

EXEMPLES:
- Question précédente: "Poids poulet 21 jours ?" + Actuelle: "Ross 308 male" → CONTEXTUEL
- Question précédente: "Problème santé" + Actuelle: "diarrhée depuis 2 jours" → CONTEXTUEL  
- Question isolée: "Comment nourrir mes poules ?" → NON CONTEXTUEL

Réponds en JSON:
```json
{{
  "is_contextual_clarification": true|false,
  "contextual_confidence": 0.0-1.0,
  "context_reasoning": "explication de l'analyse contextuelle",
  "merged_context": {{"contexte fusionné si applicable"}},
  "next_action": "process_as_contextual"|"process_as_new_question"
}}
```"""
        }
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Règles de validation de backup (fallback)"""
        return {
            "min_clarification_length": 2,  # Minimum 2 caractères
            "max_clarification_length": 100,  # Maximum 100 caractères
            "valid_breeds": [
                "ross 308", "cobb 500", "hubbard", "arbor acres", 
                "isa brown", "lohmann brown", "hy-line", "bovans"
            ],
            "valid_sexes": ["mâle", "male", "femelle", "female", "mixte", "mixed"],
            "age_ranges": {
                "broilers": {"min": 1, "max": 70},  # 1-70 jours
                "layers": {"min": 1, "max": 500}     # 1-500 jours
            },
            "weight_ranges": {
                "day_1": {"min": 35, "max": 50},      # Poussin 1 jour
                "day_7": {"min": 120, "max": 220},    # 1 semaine
                "day_21": {"min": 500, "max": 1200},  # 3 semaines
                "day_35": {"min": 1200, "max": 2800}  # 5 semaines
            }
        }
    
    async def classify_intent_and_response_type(self,
                                              question: str,
                                              entities: Dict[str, Any],
                                              conversation_context: str = "",
                                              language: str = "fr") -> ClassificationResult:
        """
        Classification principale - Détermine l'intention et le type de réponse optimal
        
        Args:
            question: Question de l'utilisateur
            entities: Entités extraites
            conversation_context: Contexte conversationnel
            language: Langue détectée
            
        Returns:
            ClassificationResult avec recommandations
        """
        try:
            logger.info(f"🤖 [AI Validation] Classification intention: '{question[:50]}...'")
            
            # Préparer les données pour le prompt
            entities_str = json.dumps(entities, ensure_ascii=False, indent=2)
            context_str = conversation_context[-1000:] if conversation_context else "Pas de contexte"
            
            # Construire le prompt
            prompt = self.prompts["intent_classification"].format(
                question=question,
                entities=entities_str,
                context=context_str
            )
            
            # Appel IA pour classification
            ai_response = await call_ai(
                service_type=AIServiceType.CLASSIFICATION,
                prompt=prompt,
                model=self.models["intent_classification"],
                max_tokens=700,
                temperature=0.1,  # Très conservateur pour classification
                cache_key=f"intent_classify_{hash(question + entities_str[:200])}"
            )
            
            # Parser le résultat
            classification_data = self._parse_json_response(ai_response.content)
            
            # Convertir en objets typés
            intent_type = IntentType(classification_data.get("intent_type", "général"))
            response_type = ResponseType(classification_data.get("response_type", "general_answer"))
            
            # Construire le résultat
            result = ClassificationResult(
                intent_type=intent_type,
                response_type=response_type,
                confidence=classification_data.get("confidence", 0.0),
                reasoning=classification_data.get("reasoning", ""),
                missing_entities=classification_data.get("missing_entities", []),
                suggested_weight_calculation=classification_data.get("suggested_weight_calculation", False),
                urgency_level=classification_data.get("urgency_level", "normal")
            )
            
            logger.info(f"✅ [AI Validation] Classification terminée: {intent_type.value} → {response_type.value} (conf: {result.confidence})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AI Validation] Erreur classification: {e}")
            return self._fallback_classification(question, entities)
    
    async def validate_clarification(self,
                                   clarification: str,
                                   original_question: str,
                                   previous_context: Dict[str, Any] = None,
                                   language: str = "fr") -> ValidationResult:
        """
        Valide une clarification utilisateur
        
        Args:
            clarification: Clarification fournie par l'utilisateur
            original_question: Question originale qui nécessitait clarification
            previous_context: Contexte de la conversation précédente
            language: Langue
            
        Returns:
            ValidationResult avec analyse de la clarification
        """
        try:
            logger.info(f"🤖 [AI Validation] Validation clarification: '{clarification}'")
            
            # Préparer le contexte
            context_str = json.dumps(previous_context or {}, ensure_ascii=False, indent=2)
            
            # Construire le prompt
            prompt = self.prompts["clarification_validation"].format(
                clarification=clarification,
                previous_context=context_str,
                original_question=original_question
            )
            
            # Appel IA pour validation
            ai_response = await call_ai(
                service_type=AIServiceType.VALIDATION,
                prompt=prompt,
                model=self.models["clarification_analysis"],
                max_tokens=500,
                temperature=0.05,  # Très précis pour validation
                cache_key=f"clarification_validate_{hash(clarification + original_question)}"
            )
            
            # Parser le résultat
            validation_data = self._parse_json_response(ai_response.content)
            
            # Construire le résultat
            result = ValidationResult(
                is_valid_clarification=validation_data.get("is_valid_clarification", False),
                extracted_entities=validation_data.get("extracted_entities", {}),
                confidence=validation_data.get("confidence", 0.0),
                validation_reasoning=validation_data.get("validation_reasoning", ""),
                suggested_action=validation_data.get("suggested_action", "request_more")
            )
            
            logger.info(f"✅ [AI Validation] Validation terminée: valide={result.is_valid_clarification}, action={result.suggested_action}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AI Validation] Erreur validation clarification: {e}")
            return self._fallback_clarification_validation(clarification)
    
    async def check_entity_coherence(self,
                                   entities: Dict[str, Any],
                                   question_context: str = "") -> Tuple[bool, float, List[str]]:
        """
        Vérifie la cohérence des entités extraites
        
        Args:
            entities: Entités à vérifier
            question_context: Contexte de la question
            
        Returns:
            Tuple (is_coherent, confidence_score, issues_found)
        """
        try:
            logger.info(f"🤖 [AI Validation] Vérification cohérence: {len(entities)} entités")
            
            # Préparer les données
            entities_str = json.dumps(entities, ensure_ascii=False, indent=2)
            
            # Construire le prompt
            prompt = self.prompts["entity_coherence_check"].format(
                entities=entities_str,
                question=question_context
            )
            
            # Appel IA pour vérification
            ai_response = await call_ai(
                service_type=AIServiceType.VALIDATION,
                prompt=prompt,
                model=self.models["coherence_check"],
                max_tokens=400,
                temperature=0.05,
                cache_key=f"coherence_check_{hash(entities_str)}"
            )
            
            # Parser le résultat
            coherence_data = self._parse_json_response(ai_response.content)
            
            is_coherent = coherence_data.get("entities_coherent", True)
            confidence = coherence_data.get("coherence_score", 0.5)
            issues = coherence_data.get("issues_found", [])
            
            logger.info(f"✅ [AI Validation] Cohérence vérifiée: cohérent={is_coherent}, score={confidence}")
            
            return is_coherent, confidence, issues
            
        except Exception as e:
            logger.error(f"❌ [AI Validation] Erreur vérification cohérence: {e}")
            return True, 0.5, []  # Assume coherent if check fails
    
    async def analyze_contextual_clarification(self,
                                             current_question: str,
                                             conversation_history: str,
                                             current_entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse si la question actuelle est une clarification contextuelle
        
        Args:
            current_question: Question actuelle
            conversation_history: Historique de conversation
            current_entities: Entités de la question actuelle
            
        Returns:
            Dict avec analyse contextuelle
        """
        try:
            logger.info(f"🤖 [AI Validation] Analyse contextuelle: '{current_question[:30]}...'")
            
            # Préparer les données
            entities_str = json.dumps(current_entities, ensure_ascii=False)
            
            # Construire le prompt
            prompt = self.prompts["contextual_analysis"].format(
                current_question=current_question,
                conversation_history=conversation_history[-1500:],  # Limiter pour tokens
                current_entities=entities_str
            )
            
            # Appel IA pour analyse
            ai_response = await call_ai(
                service_type=AIServiceType.VALIDATION,
                prompt=prompt,
                model=self.models["clarification_analysis"],
                max_tokens=500,
                temperature=0.1,
                cache_key=f"contextual_analysis_{hash(current_question + conversation_history[-500:])}"
            )
            
            # Parser et retourner
            analysis_data = self._parse_json_response(ai_response.content)
            
            logger.info(f"✅ [AI Validation] Analyse contextuelle terminée: contextuel={analysis_data.get('is_contextual_clarification', False)}")
            
            return analysis_data
            
        except Exception as e:
            logger.error(f"❌ [AI Validation] Erreur analyse contextuelle: {e}")
            return {
                "is_contextual_clarification": False,
                "contextual_confidence": 0.0,
                "context_reasoning": f"Erreur: {e}",
                "next_action": "process_as_new_question"
            }
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse une réponse JSON avec gestion d'erreurs robuste"""
        
        try:
            # Nettoyer le contenu
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [AI Validation] Erreur parsing JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ [AI Validation] Erreur parsing: {e}")
            return {}
    
    def _fallback_classification(self, question: str, entities: Dict[str, Any]) -> ClassificationResult:
        """Classification de fallback avec règles simples"""
        
        logger.info("🔧 [AI Validation] Fallback classification avec règles")
        
        question_lower = question.lower()
        
        # Détecter l'intention avec mots-clés
        if any(word in question_lower for word in ["poids", "croissance", "performance", "weight"]):
            intent = IntentType.PERFORMANCE_QUERY
        elif any(word in question_lower for word in ["malade", "symptôme", "santé", "problème"]):
            intent = IntentType.HEALTH_CONCERN
        elif any(word in question_lower for word in ["alimentation", "nourrir", "aliment"]):
            intent = IntentType.FEEDING_QUESTION
        else:
            intent = IntentType.GENERAL_INFO
        
        # Détecter le type de réponse
        has_breed = bool(entities.get("breed_specific"))
        has_age = bool(entities.get("age_days"))
        has_sex = bool(entities.get("sex"))
        
        if has_breed and has_age and has_sex:
            response_type = ResponseType.PRECISE_ANSWER
            confidence = 0.8
        elif has_breed and (has_age or has_sex):
            response_type = ResponseType.GENERAL_ANSWER
            confidence = 0.7
        elif len(question.split()) <= 3 and (has_breed or has_sex):
            response_type = ResponseType.CONTEXTUAL_ANSWER
            confidence = 0.6
        else:
            response_type = ResponseType.NEEDS_CLARIFICATION
            confidence = 0.5
        
        return ClassificationResult(
            intent_type=intent,
            response_type=response_type,
            confidence=confidence,
            reasoning="Classification fallback avec règles simples"
        )
    
    def _fallback_clarification_validation(self, clarification: str) -> ValidationResult:
        """Validation de clarification de fallback"""
        
        logger.info("🔧 [AI Validation] Fallback validation clarification")
        
        clarification_lower = clarification.lower().strip()
        
        # Vérifications basiques
        if len(clarification_lower) < 2:
            return ValidationResult(
                is_valid_clarification=False,
                confidence=0.1,
                validation_reasoning="Clarification trop courte",
                suggested_action="request_more"
            )
        
        # Recherche d'entités simples
        extracted = {}
        
        # Races
        for breed in self.validation_rules["valid_breeds"]:
            if breed in clarification_lower:
                extracted["breed_specific"] = breed.title()
                break
        
        # Sexes
        for sex in self.validation_rules["valid_sexes"]:
            if sex in clarification_lower:
                extracted["sex"] = "male" if sex in ["mâle", "male"] else "female" if sex in ["femelle", "female"] else "mixed"
                break
        
        is_valid = len(extracted) > 0
        confidence = 0.6 if is_valid else 0.3
        
        return ValidationResult(
            is_valid_clarification=is_valid,
            extracted_entities=extracted,
            confidence=confidence,
            validation_reasoning="Validation fallback avec patterns simples",
            suggested_action="accept" if is_valid else "request_more"
        )
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Statistiques de validation pour monitoring"""
        from .ai_service_manager import get_ai_service_manager
        
        manager = get_ai_service_manager()
        health = manager.get_service_health()
        
        return {
            "service_name": "AI Validation Service",
            "validation_requests": health.get("requests_by_service", {}).get("validation", 0),
            "classification_requests": health.get("requests_by_service", {}).get("classification", 0),
            "models_available": list(self.models.keys()),
            "intent_types": [t.value for t in IntentType],
            "response_types": [t.value for t in ResponseType],
            "validation_rules": {k: len(v) if isinstance(v, (list, dict)) else v for k, v in self.validation_rules.items()},
            "ai_service_health": health
        }

# Instance globale pour utilisation facile
_ai_validation_service = None

def get_ai_validation_service() -> AIValidationService:
    """Récupère l'instance singleton du service de validation IA"""
    global _ai_validation_service
    if _ai_validation_service is None:
        _ai_validation_service = AIValidationService()
    return _ai_validation_service