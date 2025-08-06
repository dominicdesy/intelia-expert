"""
smart_classifier_v3.py - CLASSIFIER INTELLIGENT AVEC IA OpenAI

🎯 AMÉLIORATIONS MAJEURES:
- ✅ Intégration OpenAI pour analyse intelligente
- ✅ Classification basée sur l'intention réelle
- ✅ Validation contextuelle intelligente
- ✅ Fallback vers règles si IA indisponible
- ✅ Correction du bug "contexte utile"

Architecture hybride:
1. Analyse OpenAI pour comprendre l'intention
2. Validation des entités fusionnées 
3. Calcul des données de poids
4. Fallback règles hardcodées si nécessaire
"""

import logging
import json
import openai
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types de réponse possibles"""
    PRECISE_ANSWER = "precise_answer"
    GENERAL_ANSWER = "general_answer" 
    NEEDS_CLARIFICATION = "needs_clarification"
    CONTEXTUAL_ANSWER = "contextual_answer"

@dataclass 
class ClassificationResult:
    """Résultat de classification enrichi avec analyse IA"""
    response_type: ResponseType
    confidence: float
    reasoning: str
    missing_entities: List[str] = None
    merged_entities: Dict[str, Any] = None
    weight_data: Dict[str, Any] = None
    ai_analysis: Dict[str, Any] = None  # 🆕 NOUVEAU
    fallback_used: bool = False  # 🆕 NOUVEAU

class EnhancedSmartClassifier:
    """Classifier intelligent avec IA OpenAI"""
    
    def __init__(self, openai_client=None, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.openai_client = openai_client
        self.use_ai = openai_client is not None
        
        # Configuration IA
        self.ai_model = "gpt-4"  # ou "gpt-3.5-turbo" pour économie
        self.max_tokens = 500
        
        logger.info(f"🤖 [Enhanced Classifier] IA disponible: {self.use_ai}")

    async def classify_question_with_ai(self, question: str, entities: Dict[str, Any], 
                                      conversation_context: Optional[Dict] = None,
                                      conversation_id: Optional[str] = None) -> ClassificationResult:
        """
        🆕 NOUVEAU: Classification intelligente avec OpenAI
        """
        try:
            # 1. Analyse IA si disponible
            if self.use_ai:
                ai_analysis = await self._analyze_with_openai(
                    question, entities, conversation_context
                )
                
                # 2. Fusionner contexte basé sur analyse IA
                merged_entities = self._merge_context_intelligently(
                    entities, conversation_context, ai_analysis
                )
                
                # 3. Validation finale avec IA
                final_classification = self._determine_final_classification(
                    ai_analysis, merged_entities
                )
                
                return final_classification
            
            # 4. Fallback vers règles classiques
            else:
                logger.warning("⚠️ [AI] OpenAI indisponible - fallback règles")
                return self._classify_with_rules(question, entities, conversation_context)
                
        except Exception as e:
            logger.error(f"❌ [AI Classification] Erreur: {e}")
            return self._classify_with_rules(question, entities, conversation_context)

    async def _analyze_with_openai(self, question: str, entities: Dict[str, Any], 
                                 context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyse la question avec OpenAI pour comprendre l'intention"""
        
        # Construire le prompt d'analyse
        analysis_prompt = self._build_analysis_prompt(question, entities, context)
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Tu es un expert en élevage avicole qui analyse les questions des utilisateurs pour déterminer le type de réponse optimal."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.1  # Réponses cohérentes
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parser la réponse JSON
            try:
                analysis = json.loads(analysis_text)
                logger.info(f"✅ [AI Analysis] Intention détectée: {analysis.get('intention', 'unknown')}")
                return analysis
            except json.JSONDecodeError:
                logger.warning("⚠️ [AI] Réponse non-JSON, parsing manuel")
                return self._parse_analysis_manually(analysis_text)
                
        except Exception as e:
            logger.error(f"❌ [OpenAI] Erreur API: {e}")
            raise

    def _build_analysis_prompt(self, question: str, entities: Dict[str, Any], 
                             context: Optional[Dict] = None) -> str:
        """Construit le prompt d'analyse pour OpenAI"""
        
        context_info = ""
        if context:
            previous_q = context.get('previous_question', '')
            previous_e = context.get('previous_entities', {})
            context_info = f"""
CONTEXTE CONVERSATIONNEL:
- Question précédente: "{previous_q}"
- Entités précédentes: {json.dumps(previous_e, ensure_ascii=False)}
"""

        prompt = f"""Analyse cette question d'élevage avicole et détermine le type de réponse optimal.

QUESTION ACTUELLE: "{question}"

ENTITÉS DÉTECTÉES:
{json.dumps(entities, ensure_ascii=False)}

{context_info}

TÂCHE:
Détermine si cette question nécessite:
1. PRECISE_ANSWER: Assez d'infos pour réponse spécifique (race + âge/sexe)
2. CONTEXTUAL_ANSWER: Clarification qui complète le contexte précédent  
3. GENERAL_ANSWER: Contexte suffisant pour conseil général utile
4. NEEDS_CLARIFICATION: Information insuffisante

FOCUS SPÉCIAL:
- Si c'est une clarification courte après une question de poids (ex: "Ross 308 male" après "poids poulet 10j"), c'est CONTEXTUAL_ANSWER
- Pour les questions de poids/croissance, race + âge = PRECISE_ANSWER
- Éviter NEEDS_CLARIFICATION sauf si vraiment impossible à traiter

Réponds en JSON avec:
{{
    "intention": "question_performance|clarification|question_sante|question_generale",
    "classification_recommandee": "PRECISE_ANSWER|CONTEXTUAL_ANSWER|GENERAL_ANSWER|NEEDS_CLARIFICATION",
    "confidence": 0.0-1.0,
    "raisonnement": "explication courte",
    "entites_manquantes": ["liste", "des", "manquantes"],
    "contexte_suffisant": true|false,
    "peut_calculer_poids": true|false,
    "recommandation_fusion": "fuser_avec_contexte|utiliser_entites_actuelles|demander_clarification"
}}"""

        return prompt

    def _merge_context_intelligently(self, entities: Dict[str, Any], 
                                   context: Optional[Dict], 
                                   ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne le contexte basé sur l'analyse IA"""
        
        merged = entities.copy()
        
        # Si l'IA recommande la fusion
        if ai_analysis.get('recommandation_fusion') == 'fuser_avec_contexte' and context:
            previous_entities = context.get('previous_entities', {})
            
            # Hériter intelligemment
            if not merged.get('age_days') and previous_entities.get('age_days'):
                merged['age_days'] = previous_entities['age_days']
                merged['age_inherited_from_context'] = True
                logger.info(f"🔗 [AI Merge] Âge hérité: {previous_entities['age_days']}j")
            
            if not merged.get('context_type') and previous_entities.get('weight_mentioned'):
                merged['context_type'] = 'performance'
                merged['context_inherited_from_weight_question'] = True
                logger.info("🔗 [AI Merge] Contexte performance détecté")
        
        return merged

    def _determine_final_classification(self, ai_analysis: Dict[str, Any], 
                                      merged_entities: Dict[str, Any]) -> ClassificationResult:
        """Détermine la classification finale basée sur l'analyse IA"""
        
        recommended_type = ai_analysis.get('classification_recommandee', 'GENERAL_ANSWER')
        confidence = ai_analysis.get('confidence', 0.7)
        reasoning = ai_analysis.get('raisonnement', 'Analyse IA')
        
        # Convertir en ResponseType
        try:
            response_type = ResponseType(recommended_type.lower())
        except ValueError:
            logger.warning(f"⚠️ [AI] Type inconnu {recommended_type}, fallback GENERAL")
            response_type = ResponseType.GENERAL_ANSWER
        
        # Calculer les données de poids si recommandé
        weight_data = {}
        if ai_analysis.get('peut_calculer_poids', False):
            weight_data = self._calculate_weight_data_enhanced(merged_entities)
        
        # Entités manquantes suggérées par l'IA
        missing_entities = ai_analysis.get('entites_manquantes', [])
        
        result = ClassificationResult(
            response_type=response_type,
            confidence=confidence,
            reasoning=f"IA: {reasoning}",
            missing_entities=missing_entities,
            merged_entities=merged_entities,
            weight_data=weight_data,
            ai_analysis=ai_analysis,
            fallback_used=False
        )
        
        logger.info(f"🤖 [AI Classification] {response_type.value} (conf: {confidence})")
        return result

    def _calculate_weight_data_enhanced(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Version améliorée du calcul de poids avec plus de contexte"""
        
        breed = entities.get('breed_specific', '').lower().replace(' ', '_')
        age_days = entities.get('age_days')
        sex = entities.get('sex', 'mixed').lower()
        
        if not breed or not age_days:
            return {}
        
        # Normalisation sexe améliorée
        sex_mapping = {
            'mâle': 'male', 'male': 'male', 'coq': 'male',
            'femelle': 'female', 'female': 'female', 'poule': 'female',
            'mixte': 'mixed', 'mixed': 'mixed'
        }
        sex = sex_mapping.get(sex, 'mixed')
        
        try:
            # Import de la fonction de calcul existante
            from .intelligent_system_config import get_weight_range
            
            weight_range = get_weight_range(breed, age_days, sex)
            min_weight, max_weight = weight_range
            target_weight = (min_weight + max_weight) // 2
            
            # Seuils d'alerte plus précis
            alert_low = int(min_weight * 0.85)
            alert_high = int(max_weight * 1.15)
            critical_low = int(min_weight * 0.70)
            critical_high = int(max_weight * 1.30)
            
            weight_data = {
                "breed": breed.replace('_', ' ').title(),
                "age_days": age_days,
                "sex": sex,
                "weight_range": weight_range,
                "target_weight": target_weight,
                "alert_thresholds": {
                    "low": alert_low,
                    "high": alert_high,
                    "critical_low": critical_low,
                    "critical_high": critical_high
                },
                "data_source": "intelligent_system_config",
                "calculation_method": "enhanced_ai_driven",
                "confidence": 0.95,
                "context_used": {
                    "age_inherited": entities.get('age_inherited_from_context', False),
                    "performance_context": entities.get('context_inherited_from_weight_question', False)
                }
            }
            
            logger.info(f"📊 [Enhanced Weight] {breed} {sex} {age_days}j → {min_weight}-{max_weight}g")
            return weight_data
            
        except Exception as e:
            logger.error(f"❌ [Enhanced Weight] Erreur: {e}")
            return {}

    def _classify_with_rules(self, question: str, entities: Dict[str, Any], 
                           context: Optional[Dict] = None) -> ClassificationResult:
        """Fallback avec règles améliorées (version corrigée)"""
        
        logger.info("🔧 [Fallback] Classification avec règles améliorées")
        
        # 🔧 CORRECTION: Détection contextuelle améliorée
        if self._is_contextual_clarification(question, entities, context):
            merged_entities = self._merge_entities_simple(entities, context)
            
            # ✅ CORRECTION: Validation plus permissive
            if self._has_sufficient_merged_info(merged_entities):
                weight_data = self._calculate_weight_data_enhanced(merged_entities)
                
                return ClassificationResult(
                    response_type=ResponseType.CONTEXTUAL_ANSWER,
                    confidence=0.85,
                    reasoning="Clarification contextuelle détectée - entités fusionnées suffisantes",
                    merged_entities=merged_entities,
                    weight_data=weight_data,
                    fallback_used=True
                )
        
        # Règles classiques améliorées
        if self._has_precise_info(entities):
            return ClassificationResult(
                ResponseType.PRECISE_ANSWER,
                confidence=0.9,
                reasoning="Informations précises suffisantes",
                weight_data=self._calculate_weight_data_enhanced(entities),
                fallback_used=True
            )
        
        elif self._has_useful_context_fixed(question, entities):  # ✅ Version corrigée
            return ClassificationResult(
                ResponseType.GENERAL_ANSWER,
                confidence=0.8,
                reasoning="Contexte utile pour réponse générale",
                missing_entities=self._identify_missing_for_precision(entities),
                fallback_used=True
            )
        
        else:
            return ClassificationResult(
                ResponseType.NEEDS_CLARIFICATION,
                confidence=0.6,
                reasoning="Informations insuffisantes",
                missing_entities=self._identify_critical_missing(question, entities),
                fallback_used=True
            )

    def _is_contextual_clarification(self, question: str, entities: Dict[str, Any], 
                                   context: Optional[Dict]) -> bool:
        """🔧 Version améliorée de détection des clarifications"""
        
        if not context or not context.get('previous_question'):
            return False
        
        # Question très courte avec race/sexe spécifique
        if len(question.split()) <= 3:
            has_breed = entities.get('breed_specific') or entities.get('breed_generic')
            has_sex = entities.get('sex')
            if has_breed or has_sex:
                logger.info("🔗 [Enhanced] Clarification courte détectée")
                return True
        
        # Patterns typiques
        patterns = ['pour un', 'pour une', 'avec un', 'ross 308', 'cobb 500', 'mâle', 'femelle']
        if any(pattern in question.lower() for pattern in patterns):
            return True
        
        return False

    def _has_sufficient_merged_info(self, merged_entities: Dict[str, Any]) -> bool:
        """✅ CORRECTION: Validation plus permissive pour contexte fusionné"""
        
        breed = merged_entities.get('breed_specific')
        age = merged_entities.get('age_days')
        sex = merged_entities.get('sex')
        context_type = merged_entities.get('context_type')
        
        # Combinaisons suffisantes
        checks = [
            breed and age and sex,  # Trio complet
            breed and age and context_type == 'performance',  # Race + âge + contexte poids
            breed and sex and merged_entities.get('age_inherited_from_context'),  # Race + sexe + âge hérité
        ]
        
        if any(checks):
            logger.info("✅ [Sufficient Merged] Informations fusionnées suffisantes")
            return True
        
        logger.info("❌ [Sufficient Merged] Pas assez d'infos même fusionnées")
        return False

    def _has_useful_context_fixed(self, question: str, entities: Dict[str, Any]) -> bool:
        """🔧 CORRECTION: Version fixée qui détecte mieux le contexte utile"""
        
        question_lower = question.lower()
        
        # Questions de poids avec âge
        weight_keywords = ['poids', 'weight', 'gramme', 'kg', 'pesé', 'peser', 'cible', 'croissance']
        has_weight_question = any(word in question_lower for word in weight_keywords)
        has_age = entities.get('age_days') or entities.get('age_weeks')
        
        if has_weight_question and has_age:
            logger.info("✅ [Useful Fixed] Question poids + âge détectée")
            return True
        
        # Question avec race générique + âge (utile même sans spécificité)
        has_breed = entities.get('breed_generic') or entities.get('breed_specific')
        if has_breed and has_age:
            logger.info("✅ [Useful Fixed] Race + âge détectés")
            return True
        
        # Contexte hérité
        if entities.get('age_inherited_from_context') or entities.get('context_inherited_from_weight_question'):
            logger.info("✅ [Useful Fixed] Contexte hérité détecté")
            return True
        
        return False

    # Autres méthodes utilitaires (reprises de l'ancien code mais simplifiées)
    def _merge_entities_simple(self, entities: Dict[str, Any], context: Optional[Dict]) -> Dict[str, Any]:
        """Fusion simple des entités avec contexte"""
        merged = entities.copy()
        
        if context and context.get('previous_entities'):
            prev = context['previous_entities']
            
            if not merged.get('age_days') and prev.get('age_days'):
                merged['age_days'] = prev['age_days']
                merged['age_inherited_from_context'] = True
            
            if not merged.get('context_type') and prev.get('weight_mentioned'):
                merged['context_type'] = 'performance'
                merged['context_inherited_from_weight_question'] = True
        
        return merged

    def _has_precise_info(self, entities: Dict[str, Any]) -> bool:
        """Check pour informations précises"""
        breed = entities.get('breed_specific')
        age = entities.get('age_days')
        sex = entities.get('sex')
        
        return (breed and age and sex) or (breed and age)

    def _identify_missing_for_precision(self, entities: Dict[str, Any]) -> List[str]:
        """Identifie manquants pour précision"""
        missing = []
        if not entities.get('breed_specific'): missing.append('breed')
        if not entities.get('sex'): missing.append('sex')  
        if not entities.get('age_days'): missing.append('age')
        return missing

    def _identify_critical_missing(self, question: str, entities: Dict[str, Any]) -> List[str]:
        """Identifie manquants critiques"""
        return ['context', 'specifics'] if len(question.split()) < 4 else ['breed', 'age']

    def _parse_analysis_manually(self, text: str) -> Dict[str, Any]:
        """Parse manuel si JSON échoue"""
        return {
            "intention": "question_generale",
            "classification_recommandee": "GENERAL_ANSWER",
            "confidence": 0.7,
            "raisonnement": "Parse manuel - réponse IA non-structurée",
            "peut_calculer_poids": False,
            "recommandation_fusion": "utiliser_entites_actuelles"
        }

# =============================================================================
# EXEMPLE D'UTILISATION
# =============================================================================

async def demo_enhanced_classifier():
    """Démo du classifier amélioré"""
    
    # Initialisation avec client OpenAI
    import openai
    client = openai.AsyncOpenAI(api_key="your-api-key")
    
    classifier = EnhancedSmartClassifier(openai_client=client)
    
    # Test conversation problématique
    conversation_context = {
        "previous_question": "Quel est le poids cible pour un poulet au jour 10 ?",
        "previous_entities": {"age_days": 10, "weight_mentioned": True, "context_type": "performance"}
    }
    
    # Question clarification
    entities = {"breed_specific": "Ross 308", "sex": "male"}
    
    result = await classifier.classify_question_with_ai(
        "Ross 308 male", 
        entities, 
        conversation_context
    )
    
    print(f"Classification: {result.response_type.value}")
    print(f"Confiance: {result.confidence}")
    print(f"Données poids: {result.weight_data}")
    print(f"IA utilisée: {not result.fallback_used}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_enhanced_classifier())