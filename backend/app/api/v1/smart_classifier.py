"""
smart_classifier.py - CLASSIFIER INTELLIGENT AVEC CONTEXTE CONVERSATIONNEL

🎯 AMÉLIORATIONS:
- ✅ Détection des clarifications contextuelles
- ✅ Mémoire conversationnelle
- ✅ Logique avancée pour combinaisons d'entités
- ✅ Support des conversations multi-tours
- ✅ Interpolation automatique des données manquantes

Architecture:
- classify_question() : Point d'entrée unique avec contexte
- Règles hiérarchiques avancées
- Support contexte conversationnel
- Pas de conflits entre systèmes
"""

import logging
import re
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types de réponse possibles"""
    PRECISE_ANSWER = "precise_answer"       # Assez d'infos pour réponse précise
    GENERAL_ANSWER = "general_answer"       # Réponse générale + offre de précision  
    NEEDS_CLARIFICATION = "needs_clarification"  # Vraiment trop vague
    CONTEXTUAL_ANSWER = "contextual_answer"    # Réponse basée sur contexte conversationnel

@dataclass
class ConversationContext:
    """Contexte d'une conversation"""
    previous_question: Optional[str] = None
    previous_entities: Optional[Dict[str, Any]] = None
    conversation_topic: Optional[str] = None  # performance, health, feeding
    established_breed: Optional[str] = None
    established_age: Optional[int] = None
    established_sex: Optional[str] = None
    last_interaction: Optional[datetime] = None
    
    def is_fresh(self, max_age_minutes: int = 10) -> bool:
        """Vérifie si le contexte est encore frais"""
        if not self.last_interaction:
            return False
        return datetime.now() - self.last_interaction < timedelta(minutes=max_age_minutes)

class ClassificationResult:
    """Résultat de la classification"""
    def __init__(self, response_type: ResponseType, confidence: float, reasoning: str, 
                 missing_entities: list = None, merged_entities: Dict[str, Any] = None):
        self.response_type = response_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.missing_entities = missing_entities or []
        self.merged_entities = merged_entities or {}

class SmartClassifier:
    """Classifier intelligent avec contexte conversationnel"""
    
    def __init__(self):
        self.confidence_thresholds = {
            "precise": 0.85,
            "general": 0.6,
            "clarification": 0.4
        }
        
        # Races spécifiques reconnues
        self.specific_breeds = [
            'ross 308', 'cobb 500', 'hubbard', 'arbor acres',
            'isa brown', 'lohmann brown', 'hy-line', 'bovans',
            'shaver', 'hissex', 'novogen'
        ]
        
        # Races génériques
        self.generic_breeds = ['ross', 'cobb', 'broiler', 'poulet', 'poule']
        
        # Indicateurs de clarification
        self.clarification_indicators = [
            'pour un', 'pour une', 'avec un', 'avec une', 'chez un', 'chez une',
            'ross 308', 'cobb 500', 'mâle', 'femelle', 'mâles', 'femelles'
        ]

    def classify_question(self, question: str, entities: Dict[str, Any], 
                         conversation_context: Optional[ConversationContext] = None,
                         is_clarification_response: bool = False) -> ClassificationResult:
        """
        POINT D'ENTRÉE UNIQUE - Classifie la question avec contexte conversationnel
        
        Args:
            question: Texte de la question
            entities: Entités extraites de la question
            conversation_context: Contexte de la conversation précédente
            is_clarification_response: Indique si c'est une réponse de clarification
            
        Returns:
            ClassificationResult avec le type de réponse recommandé
        """
        try:
            logger.info(f"🧠 [Smart Classifier] Classification: '{question[:50]}...'")
            logger.info(f"🔍 [Smart Classifier] Entités: {entities}")
            
            # NOUVEAU: Détection des clarifications contextuelles
            if self._is_clarification_response(question, entities, conversation_context, is_clarification_response):
                merged_entities = self._merge_with_context(entities, conversation_context)
                logger.info(f"🔗 [Contextual] Entités fusionnées: {merged_entities}")
                
                if self._has_specific_info(merged_entities):
                    return ClassificationResult(
                        ResponseType.CONTEXTUAL_ANSWER,
                        confidence=0.9,
                        reasoning="Clarification détectée - contexte fusionné pour réponse précise",
                        merged_entities=merged_entities
                    )
            
            # Règle 1: PRÉCIS - Assez d'informations pour réponse spécifique
            if self._has_specific_info(entities):
                return ClassificationResult(
                    ResponseType.PRECISE_ANSWER,
                    confidence=0.9,
                    reasoning="Informations spécifiques suffisantes (race + âge/sexe)"
                )
            
            # Règle 2: GÉNÉRAL - Contexte suffisant pour réponse utile
            elif self._has_useful_context(question, entities):
                missing = self._identify_missing_for_precision(entities)
                return ClassificationResult(
                    ResponseType.GENERAL_ANSWER,
                    confidence=0.8,
                    reasoning="Contexte suffisant pour réponse générale utile",
                    missing_entities=missing
                )
            
            # Règle 3: CLARIFICATION - Vraiment trop vague
            else:
                missing = self._identify_critical_missing(question, entities)
                return ClassificationResult(
                    ResponseType.NEEDS_CLARIFICATION,
                    confidence=0.6,
                    reasoning="Information insuffisante pour réponse utile",
                    missing_entities=missing
                )
                
        except Exception as e:
            logger.error(f"❌ [Smart Classifier] Erreur classification: {e}")
            # Fallback sécurisé
            return ClassificationResult(
                ResponseType.GENERAL_ANSWER,
                confidence=0.5,
                reasoning="Erreur de classification - fallback général"
            )

    def _is_clarification_response(self, question: str, entities: Dict[str, Any], 
                                 context: Optional[ConversationContext], 
                                 is_clarification_flag: bool) -> bool:
        """NOUVEAU: Détecte si c'est une réponse de clarification"""
        
        # Flag explicite
        if is_clarification_flag:
            return True
            
        # Pas de contexte
        if not context or not context.is_fresh():
            return False
            
        question_lower = question.lower()
        
        # Patterns de clarification
        clarification_patterns = [
            r'pour un\s+\w+',  # "pour un Ross 308"
            r'avec un\s+\w+',  # "avec un mâle"  
            r'chez\s+\w+',     # "chez Ross 308"
            r'^\w+\s+\w+$',    # "Ross 308" ou "cobb 500"
            r'^(mâle|femelle|mâles|femelles)$'  # Juste le sexe
        ]
        
        for pattern in clarification_patterns:
            if re.search(pattern, question_lower):
                logger.info(f"🔗 [Clarification] Pattern détecté: {pattern}")
                return True
        
        # Question très courte après question complexe
        if len(question.split()) <= 3 and context.previous_question:
            if len(context.previous_question.split()) > 5:
                logger.info("🔗 [Clarification] Question courte après question complexe")
                return True
        
        # Mots-clés de clarification détectés
        clarification_indicators = any(indicator in question_lower 
                                     for indicator in self.clarification_indicators)
        if clarification_indicators:
            logger.info("🔗 [Clarification] Indicateurs détectés")
            return True
            
        return False

    def _merge_with_context(self, current_entities: Dict[str, Any], 
                          context: Optional[ConversationContext]) -> Dict[str, Any]:
        """NOUVEAU: Fusionne les entités actuelles avec le contexte conversationnel"""
        
        if not context:
            return current_entities
            
        merged = current_entities.copy()
        
        # Hériter des entités précédentes si manquantes
        if context.previous_entities:
            prev = context.previous_entities
            
            # Âge du contexte précédent
            if not merged.get('age_days') and prev.get('age_days'):
                merged['age_days'] = prev['age_days']
                merged['age_context_inherited'] = True
                logger.info(f"🔗 [Context] Âge hérité: {prev['age_days']} jours")
            
            # Contexte de performance (poids, croissance)
            if not merged.get('context_type') and prev.get('weight_mentioned'):
                merged['context_type'] = 'performance'
                merged['weight_context_inherited'] = True
                logger.info("🔗 [Context] Contexte performance hérité")
                
            # Topic conversationnel
            if not merged.get('context_type') and prev.get('context_type'):
                merged['context_type'] = prev['context_type']
                
        # Entités établies dans la conversation
        if context.established_breed and not merged.get('breed_specific'):
            merged['breed_specific'] = context.established_breed
            merged['breed_context_inherited'] = True
            
        if context.established_age and not merged.get('age_days'):
            merged['age_days'] = context.established_age
            merged['age_context_inherited'] = True
            
        if context.established_sex and not merged.get('sex'):
            merged['sex'] = context.established_sex
            merged['sex_context_inherited'] = True
            
        return merged

    def _has_specific_info(self, entities: Dict[str, Any]) -> bool:
        """Détermine s'il y a assez d'infos pour une réponse précise (amélioré)"""
        
        breed_specific = entities.get('breed_specific')
        age = entities.get('age_days') or entities.get('age')
        sex = entities.get('sex')
        weight = entities.get('weight_grams')
        context_type = entities.get('context_type')
        
        # Combinaisons suffisantes pour réponse précise
        if breed_specific and age and sex:
            logger.info("✅ [Specific] Race spécifique + âge + sexe")
            return True
            
        if breed_specific and weight:
            logger.info("✅ [Specific] Race spécifique + poids")
            return True
            
        if breed_specific and age:
            logger.info("✅ [Specific] Race spécifique + âge (suffisant)")
            return True
            
        # NOUVEAU: Contexte de performance avec race et âge
        if breed_specific and context_type == 'performance':
            logger.info("✅ [Specific] Race + contexte performance")
            return True
            
        # NOUVEAU: Race + sexe + contexte âge hérité
        if breed_specific and sex and entities.get('age_context_inherited'):
            logger.info("✅ [Specific] Race + sexe + âge du contexte")
            return True
            
        return False

    def _has_useful_context(self, question: str, entities: Dict[str, Any]) -> bool:
        """Détermine s'il y a assez de contexte pour une réponse générale utile (amélioré)"""
        
        question_lower = question.lower()
        
        # Questions de poids avec âge
        weight_question = any(word in question_lower for word in 
                            ['poids', 'weight', 'gramme', 'kg', 'pesé', 'peser', 'cible'])
        
        age_info = entities.get('age_days') or entities.get('age') or entities.get('age_weeks')
        
        if weight_question and age_info:
            logger.info("✅ [Useful] Question poids + âge")
            return True
        
        # Questions de croissance avec contexte
        growth_question = any(word in question_lower for word in 
                            ['croissance', 'grandir', 'développement', 'taille'])
        
        if growth_question and age_info:
            logger.info("✅ [Useful] Question croissance + âge")
            return True
        
        # Questions de santé avec symptômes décrits
        health_question = any(word in question_lower for word in 
                            ['malade', 'symptôme', 'problème', 'mort', 'faible'])
        
        symptoms = entities.get('symptoms') or len([w for w in question_lower.split() 
                                                  if w in ['apathique', 'diarrhée', 'toux', 'boiterie']]) > 0
        
        if health_question and (symptoms or age_info):
            logger.info("✅ [Useful] Question santé + contexte")
            return True
        
        # Questions d'alimentation avec stade
        feeding_question = any(word in question_lower for word in 
                             ['alimentation', 'nourrir', 'aliment', 'nutrition'])
        
        if feeding_question and age_info:
            logger.info("✅ [Useful] Question alimentation + âge")
            return True
        
        # NOUVEAU: Contexte hérité de performance
        if entities.get('weight_context_inherited') or entities.get('age_context_inherited'):
            logger.info("✅ [Useful] Contexte performance hérité")
            return True
        
        logger.info("❌ [Useful] Pas assez de contexte utile")
        return False

    def _identify_missing_for_precision(self, entities: Dict[str, Any]) -> list:
        """Identifie ce qui manque pour une réponse plus précise (amélioré)"""
        missing = []
        
        if not entities.get('breed_specific'):
            missing.append('breed')
        
        if not entities.get('sex'):
            missing.append('sex')
        
        if not entities.get('age_days') and not entities.get('age'):
            missing.append('age')
        
        return missing

    def _identify_critical_missing(self, question: str, entities: Dict[str, Any]) -> list:
        """Identifie les informations critiques manquantes (amélioré)"""
        missing = []
        question_lower = question.lower()
        
        # Pour questions de performance/poids
        if any(word in question_lower for word in ['poids', 'croissance', 'performance', 'cible']):
            if not entities.get('breed_specific') and not entities.get('breed_generic'):
                missing.append('breed')
            if not entities.get('age_days') and not entities.get('age'):
                missing.append('age')
        
        # Pour questions de santé
        elif any(word in question_lower for word in ['malade', 'problème', 'symptôme']):
            if not entities.get('symptoms') and len(question.split()) < 5:
                missing.append('symptoms')
            if not entities.get('age_days') and not entities.get('age'):
                missing.append('age')
        
        # Cas général - question très vague
        elif len(question.split()) < 4:
            missing.extend(['context', 'specifics'])
        
        return missing

    def create_conversation_context(self, question: str, entities: Dict[str, Any], 
                                  previous_context: Optional[ConversationContext] = None) -> ConversationContext:
        """NOUVEAU: Crée un contexte conversationnel pour la prochaine interaction"""
        
        context = ConversationContext()
        context.previous_question = question
        context.previous_entities = entities
        context.last_interaction = datetime.now()
        
        # Déterminer le topic de conversation
        question_lower = question.lower()
        if any(word in question_lower for word in ['poids', 'croissance', 'performance']):
            context.conversation_topic = 'performance'
        elif any(word in question_lower for word in ['malade', 'symptôme', 'santé']):
            context.conversation_topic = 'health'
        elif any(word in question_lower for word in ['alimentation', 'nourrir']):
            context.conversation_topic = 'feeding'
        
        # Établir des entités persistantes
        if entities.get('breed_specific'):
            context.established_breed = entities['breed_specific']
        if entities.get('age_days'):
            context.established_age = entities['age_days']
        if entities.get('sex'):
            context.established_sex = entities['sex']
            
        # Hériter du contexte précédent si disponible
        if previous_context and previous_context.is_fresh():
            if not context.established_breed and previous_context.established_breed:
                context.established_breed = previous_context.established_breed
            if not context.established_age and previous_context.established_age:
                context.established_age = previous_context.established_age
            if not context.established_sex and previous_context.established_sex:
                context.established_sex = previous_context.established_sex
        
        return context

    def get_classification_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de classification pour debugging"""
        return {
            "classifier_version": "2.0.0_contextual",
            "response_types": [t.value for t in ResponseType],
            "confidence_thresholds": self.confidence_thresholds,
            "supported_breeds_specific": len(self.specific_breeds),
            "supported_breeds_generic": len(self.generic_breeds),
            "clarification_indicators": len(self.clarification_indicators),
            "features": [
                "conversational_context",
                "clarification_detection", 
                "entity_inheritance",
                "contextual_merging"
            ]
        }

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def quick_classify(question: str, entities: Dict[str, Any] = None, 
                  context: Optional[ConversationContext] = None) -> str:
    """
    Classification rapide pour usage simple avec support du contexte
    
    Returns:
        String: 'precise', 'general', 'clarification', ou 'contextual'
    """
    if entities is None:
        entities = {}
    
    classifier = SmartClassifier()
    result = classifier.classify_question(question, entities, context)
    
    return {
        ResponseType.PRECISE_ANSWER: 'precise',
        ResponseType.GENERAL_ANSWER: 'general', 
        ResponseType.NEEDS_CLARIFICATION: 'clarification',
        ResponseType.CONTEXTUAL_ANSWER: 'contextual'
    }[result.response_type]

# =============================================================================
# TESTS INTÉGRÉS AVEC CONTEXTE
# =============================================================================

def test_classifier_with_context():
    """Tests du classifier avec contexte conversationnel"""
    classifier = SmartClassifier()
    
    # Simulation d'une conversation
    print("🧪 Test de conversation avec contexte:")
    print("=" * 50)
    
    # Question 1: Question générale
    q1 = "Quel est le poids cible d'un poulet de 12 jours ?"
    e1 = {'age_days': 12, 'weight_mentioned': True, 'context_type': 'performance'}
    result1 = classifier.classify_question(q1, e1)
    context1 = classifier.create_conversation_context(q1, e1)
    
    print(f"Q1: {q1}")
    print(f"→ {result1.response_type.value} (confiance: {result1.confidence})")
    print(f"→ Contexte établi: âge={context1.established_age}, topic={context1.conversation_topic}")
    print()
    
    # Question 2: Clarification (devrait être détectée)
    q2 = "Pour un Ross 308 male"
    e2 = {'breed_specific': 'Ross 308', 'sex': 'mâle'}
    result2 = classifier.classify_question(q2, e2, context1, is_clarification_response=True)
    
    print(f"Q2: {q2} (clarification)")
    print(f"→ {result2.response_type.value} (confiance: {result2.confidence})")
    print(f"→ Entités fusionnées: {result2.merged_entities}")
    print(f"→ Raisonnement: {result2.reasoning}")
    
    # Vérification du succès
    if result2.response_type == ResponseType.CONTEXTUAL_ANSWER:
        print("✅ SUCCESS: Clarification détectée et contexte fusionné!")
    else:
        print("❌ FAILED: Clarification non détectée")

if __name__ == "__main__":
    test_classifier_with_context()