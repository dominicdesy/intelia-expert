"""
smart_classifier.py - CLASSIFIER UNIQUE ET INTELLIGENT

🎯 REMPLACE: expert_legacy, intelligent_clarification_classifier, expert_services_clarification
🚀 PRINCIPE: Un seul endroit pour décider du type de réponse
✨ SIMPLE: Règles claires et non-contradictoires

Architecture:
- classify_question() : Point d'entrée unique
- Règles hiérarchiques claires
- Pas de conflits entre systèmes
"""

import logging
import re
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types de réponse possibles"""
    PRECISE_ANSWER = "precise_answer"       # Assez d'infos pour réponse précise
    GENERAL_ANSWER = "general_answer"       # Réponse générale + offre de précision  
    NEEDS_CLARIFICATION = "needs_clarification"  # Vraiment trop vague

class ClassificationResult:
    """Résultat de la classification"""
    def __init__(self, response_type: ResponseType, confidence: float, reasoning: str, missing_entities: list = None):
        self.response_type = response_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.missing_entities = missing_entities or []

class SmartClassifier:
    """Classifier unique pour toutes les décisions de réponse"""
    
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

    def classify_question(self, question: str, entities: Dict[str, Any]) -> ClassificationResult:
        """
        POINT D'ENTRÉE UNIQUE - Classifie la question pour déterminer le type de réponse
        
        Args:
            question: Texte de la question
            entities: Entités extraites de la question
            
        Returns:
            ClassificationResult avec le type de réponse recommandé
        """
        try:
            logger.info(f"🧠 [Smart Classifier] Classification: '{question[:50]}...'")
            logger.info(f"🔍 [Smart Classifier] Entités: {entities}")
            
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

    def _has_specific_info(self, entities: Dict[str, Any]) -> bool:
        """Détermine s'il y a assez d'infos pour une réponse précise"""
        
        breed_specific = entities.get('breed_specific')
        age = entities.get('age_days') or entities.get('age')
        sex = entities.get('sex')
        weight = entities.get('weight_grams')
        
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
            
        return False

    def _has_useful_context(self, question: str, entities: Dict[str, Any]) -> bool:
        """Détermine s'il y a assez de contexte pour une réponse générale utile"""
        
        question_lower = question.lower()
        
        # Questions de poids avec âge
        weight_question = any(word in question_lower for word in 
                            ['poids', 'weight', 'gramme', 'kg', 'pesé', 'peser'])
        
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
        
        logger.info("❌ [Useful] Pas assez de contexte utile")
        return False

    def _identify_missing_for_precision(self, entities: Dict[str, Any]) -> list:
        """Identifie ce qui manque pour une réponse plus précise"""
        missing = []
        
        if not entities.get('breed_specific'):
            missing.append('breed')
        
        if not entities.get('sex'):
            missing.append('sex')
        
        if not entities.get('age_days') and not entities.get('age'):
            missing.append('age')
        
        return missing

    def _identify_critical_missing(self, question: str, entities: Dict[str, Any]) -> list:
        """Identifie les informations critiques manquantes"""
        missing = []
        question_lower = question.lower()
        
        # Pour questions de performance/poids
        if any(word in question_lower for word in ['poids', 'croissance', 'performance']):
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

    def get_classification_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de classification pour debugging"""
        return {
            "classifier_version": "1.0.0",
            "response_types": [t.value for t in ResponseType],
            "confidence_thresholds": self.confidence_thresholds,
            "supported_breeds_specific": len(self.specific_breeds),
            "supported_breeds_generic": len(self.generic_breeds)
        }

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def quick_classify(question: str, entities: Dict[str, Any] = None) -> str:
    """
    Classification rapide pour usage simple
    
    Returns:
        String: 'precise', 'general', ou 'clarification'
    """
    if entities is None:
        entities = {}
    
    classifier = SmartClassifier()
    result = classifier.classify_question(question, entities)
    
    return {
        ResponseType.PRECISE_ANSWER: 'precise',
        ResponseType.GENERAL_ANSWER: 'general', 
        ResponseType.NEEDS_CLARIFICATION: 'clarification'
    }[result.response_type]

# =============================================================================
# TESTS INTÉGRÉS
# =============================================================================

def test_classifier():
    """Tests rapides du classifier"""
    classifier = SmartClassifier()
    
    test_cases = [
        # Cas précis
        ("Quel est le poids d'un Ross 308 mâle de 21 jours ?", 
         {'breed_specific': 'Ross 308', 'age_days': 21, 'sex': 'mâle'}, 
         ResponseType.PRECISE_ANSWER),
        
        # Cas général
        ("Quel est le poids d'un poulet de 22 jours ?",
         {'age_days': 22, 'weight_mentioned': True},
         ResponseType.GENERAL_ANSWER),
        
        # Cas clarification
        ("Mes poulets vont mal",
         {},
         ResponseType.NEEDS_CLARIFICATION)
    ]
    
    for question, entities, expected in test_cases:
        result = classifier.classify_question(question, entities)
        status = "✅" if result.response_type == expected else "❌"
        print(f"{status} {question[:30]}... → {result.response_type.value}")

if __name__ == "__main__":
    test_classifier()