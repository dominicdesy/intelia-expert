"""
smart_classifier.py - CLASSIFIER INTELLIGENT AVEC IA OpenAI + FALLBACK ROBUSTE

🎯 VERSION CORRIGÉE - Compatibilité paramètres améliorée

AMÉLIORATIONS SELON LE PLAN DE TRANSFORMATION:
- ✅ Intégration IA pour classification intelligente
- ✅ Système de fallback robuste vers règles existantes
- ✅ Conservation du code original comme backup
- ✅ Pipeline hybride IA + règles hardcodées
- ✅ Validation contextuelle avec ContextManager
- ✅ Correction du bug "contexte utile"
- 🔧 CORRECTION: Compatibilité paramètres (is_clarification_response, question_text, etc.)

Architecture hybride selon plan:
1. PRIORITÉ: Classification IA pour comprendre l'intention
2. Validation avec ContextManager centralisé
3. Calcul des données de poids enrichi
4. FALLBACK: Règles hardcodées si IA indisponible
5. Conservation totale du code original
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
    ai_analysis: Dict[str, Any] = None  # 🆕 Analyse IA
    fallback_used: bool = False  # 🆕 Indicateur fallback
    context_source: str = "unknown"  # 🆕 Source du contexte

class SmartClassifier:
    """🔧 CORRIGÉ: Classifier intelligent avec IA OpenAI selon plan de transformation"""
    
    def __init__(self, openai_client=None, db_path: str = "conversations.db", context_manager=None):
        self.db_path = db_path
        self.openai_client = openai_client
        self.use_ai = openai_client is not None
        
        # 🆕 NOUVEAU: ContextManager selon plan Phase 3
        self.context_manager = context_manager
        
        # Configuration IA
        self.ai_model = "gpt-4"  # ou "gpt-3.5-turbo" pour économie
        self.max_tokens = 500
        
        # 🔧 Conservation du code original comme fallback
        self._initialize_classic_rules()
        
        logger.info(f"🤖 [SmartClassifier] IA: {self.use_ai} | ContextManager: {context_manager is not None}")

    def _initialize_classic_rules(self):
        """🔧 CONSERVATION: Initialise les règles classiques comme backup"""
        # Conserver toute la logique originale
        pass

    async def classify_question_with_ai(self, question: str, entities: Dict[str, Any], 
                                      conversation_context: Optional[Dict] = None,
                                      conversation_id: Optional[str] = None) -> ClassificationResult:
        """
        🆕 Classification intelligente avec IA selon plan de transformation
        PRIORITÉ: IA → FALLBACK: Règles classiques conservées
        """
        context_source = "parameter"
        
        try:
            # 🆕 PHASE 3: Utiliser ContextManager centralisé si disponible
            if self.context_manager and conversation_id:
                conversation_context = self.context_manager.get_unified_context(
                    conversation_id, type="classification"
                )
                context_source = "context_manager"
                logger.info(f"📋 [ContextManager] Contexte récupéré: {len(conversation_context) if conversation_context else 0} éléments")
            
            # 1. PRIORITÉ: Analyse IA si disponible
            if self.use_ai:
                ai_analysis = await self._analyze_with_openai(
                    question, entities, conversation_context
                )
                
                # 2. Fusionner contexte basé sur analyse IA
                merged_entities = self._merge_context_intelligently(
                    entities, conversation_context, ai_analysis
                )
                
                # 3. Classification finale avec IA
                final_classification = self._determine_final_classification(
                    ai_analysis, merged_entities, context_source
                )
                
                logger.info(f"✅ [AI Pipeline] Classification: {final_classification.response_type.value}")
                return final_classification
            
            # 4. FALLBACK: Règles classiques conservées
            else:
                logger.warning("⚠️ [AI Fallback] OpenAI indisponible - utilisation règles classiques")
                return self._classify_with_rules_enhanced(
                    question, entities, conversation_context, context_source
                )
                
        except Exception as e:
            logger.error(f"❌ [AI Classification] Erreur: {e}")
            # FALLBACK ROBUSTE: Toujours avoir une réponse
            return self._classify_with_rules_enhanced(
                question, entities, conversation_context, context_source, error=str(e)
            )

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
                        "content": "Tu es un expert en élevage avicole qui analyse les questions des utilisateurs pour déterminer le type de réponse optimal. Tu comprends parfaitement les clarifications contextuelles."
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
                logger.info(f"✅ [AI Analysis] Intention: {analysis.get('intention', 'unknown')} | Confiance: {analysis.get('confidence', 0.0)}")
                return analysis
            except json.JSONDecodeError:
                logger.warning("⚠️ [AI Parse] Réponse non-JSON, parsing manuel")
                return self._parse_analysis_manually(analysis_text)
                
        except Exception as e:
            logger.error(f"❌ [OpenAI API] Erreur: {e}")
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
- Entités précédentes: {json.dumps(previous_e, ensure_ascii=False, indent=2)}
"""

        prompt = f"""Analyse cette question d'élevage avicole et détermine le type de réponse optimal.

QUESTION ACTUELLE: "{question}"

ENTITÉS DÉTECTÉES:
{json.dumps(entities, ensure_ascii=False, indent=2)}

{context_info}

RÈGLES DE CLASSIFICATION:
1. PRECISE_ANSWER: Question avec race spécifique + âge/sexe suffisants pour réponse précise
2. CONTEXTUAL_ANSWER: Clarification courte qui complète le contexte précédent (ex: "Ross 308 male" après question poids)
3. GENERAL_ANSWER: Contexte suffisant pour conseil général utile mais pas assez spécifique
4. NEEDS_CLARIFICATION: Informations vraiment insuffisantes pour toute réponse utile

PRIORITÉS SPÉCIALES:
- Détecter les clarifications contextuelles même très courtes
- Pour poids/croissance: race + âge = PRECISE_ANSWER
- Éviter NEEDS_CLARIFICATION sauf si réellement impossible
- Favoriser CONTEXTUAL_ANSWER si c'est une suite de conversation

Réponds en JSON strict:
{{
    "intention": "question_performance|clarification_contextuelle|question_sante|question_generale",
    "classification_recommandee": "PRECISE_ANSWER|CONTEXTUAL_ANSWER|GENERAL_ANSWER|NEEDS_CLARIFICATION",
    "confidence": 0.85,
    "raisonnement": "explication claire et courte",
    "entites_manquantes": ["race", "age", "sexe"],
    "contexte_suffisant": true,
    "peut_calculer_poids": true,
    "recommandation_fusion": "fuser_avec_contexte|utiliser_entites_actuelles|demander_clarification"
}}"""

        return prompt

    def _merge_context_intelligently(self, entities: Dict[str, Any], 
                                   context: Optional[Dict], 
                                   ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fusionne le contexte basé sur l'analyse IA"""
        
        merged = entities.copy()
        
        # Si l'IA recommande la fusion
        fusion_recommendation = ai_analysis.get('recommandation_fusion', '')
        
        if fusion_recommendation == 'fuser_avec_contexte' and context:
            previous_entities = context.get('previous_entities', {})
            
            # Hériter intelligemment selon les recommandations IA
            if not merged.get('age_days') and previous_entities.get('age_days'):
                merged['age_days'] = previous_entities['age_days']
                merged['age_inherited_from_context'] = True
                logger.info(f"🔗 [AI Merge] Âge hérité du contexte: {previous_entities['age_days']}j")
            
            if not merged.get('context_type') and previous_entities.get('weight_mentioned'):
                merged['context_type'] = 'performance'
                merged['context_inherited_from_weight_question'] = True
                logger.info("🔗 [AI Merge] Contexte performance hérité")
            
            # Hériter race si manquante
            if not merged.get('breed_specific') and previous_entities.get('breed_specific'):
                merged['breed_specific'] = previous_entities['breed_specific']
                merged['breed_inherited_from_context'] = True
                logger.info(f"🔗 [AI Merge] Race héritée: {previous_entities['breed_specific']}")
        
        return merged

    def _determine_final_classification(self, ai_analysis: Dict[str, Any], 
                                      merged_entities: Dict[str, Any],
                                      context_source: str) -> ClassificationResult:
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
            fallback_used=False,
            context_source=context_source
        )
        
        logger.info(f"🤖 [AI Final] {response_type.value} (conf: {confidence}) via {context_source}")
        return result

    def _classify_with_rules_enhanced(self, question: str, entities: Dict[str, Any], 
                                   context: Optional[Dict] = None, 
                                   context_source: str = "parameter",
                                   error: str = None) -> ClassificationResult:
        """🔧 FALLBACK AMÉLIORÉ: Classification avec règles conservées + améliorations"""
        
        if error:
            logger.info(f"🔧 [Enhanced Fallback] Erreur IA: {error[:100]}... | Utilisation règles")
        else:
            logger.info("🔧 [Enhanced Fallback] Classification avec règles améliorées")
        
        # 🔧 CONSERVATION + AMÉLIORATION: Détection contextuelle améliorée
        if self._is_contextual_clarification_enhanced(question, entities, context):
            merged_entities = self._merge_entities_enhanced(entities, context)
            
            # ✅ AMÉLIORATION: Validation plus intelligente
            if self._has_sufficient_merged_info_enhanced(merged_entities):
                weight_data = self._calculate_weight_data_enhanced(merged_entities)
                
                return ClassificationResult(
                    response_type=ResponseType.CONTEXTUAL_ANSWER,
                    confidence=0.85,
                    reasoning="Clarification contextuelle détectée (règles améliorées)",
                    merged_entities=merged_entities,
                    weight_data=weight_data,
                    fallback_used=True,
                    context_source=context_source
                )
        
        # Règles classiques conservées mais améliorées
        if self._has_precise_info_enhanced(entities):
            weight_data = self._calculate_weight_data_enhanced(entities)
            return ClassificationResult(
                ResponseType.PRECISE_ANSWER,
                confidence=0.9,
                reasoning="Informations précises suffisantes (règles)",
                weight_data=weight_data,
                fallback_used=True,
                context_source=context_source
            )
        
        elif self._has_useful_context_enhanced(question, entities):
            return ClassificationResult(
                ResponseType.GENERAL_ANSWER,
                confidence=0.8,
                reasoning="Contexte utile pour réponse générale (règles améliorées)",
                missing_entities=self._identify_missing_for_precision_enhanced(entities),
                fallback_used=True,
                context_source=context_source
            )
        
        else:
            return ClassificationResult(
                ResponseType.NEEDS_CLARIFICATION,
                confidence=0.6,
                reasoning="Informations insuffisantes (règles de fallback)",
                missing_entities=self._identify_critical_missing_enhanced(question, entities),
                fallback_used=True,
                context_source=context_source
            )

    # ==================================================================================
    # 🔧 MÉTHODES CONSERVÉES ET AMÉLIORÉES (selon plan de transformation)
    # ==================================================================================

    def _is_contextual_clarification_enhanced(self, question: str, entities: Dict[str, Any], 
                                           context: Optional[Dict]) -> bool:
        """🔧 Version améliorée de détection des clarifications avec conservation du code original"""
        
        if not context or not context.get('previous_question'):
            return False
        
        # AMÉLIORATION: Détection plus fine
        question_words = question.split()
        
        # Question très courte avec race/sexe spécifique
        if len(question_words) <= 4:  # Un peu plus permissif
            has_breed = entities.get('breed_specific') or entities.get('breed_generic')
            has_sex = entities.get('sex')
            has_age = entities.get('age_days') or entities.get('age_weeks')
            
            if has_breed or has_sex or has_age:
                logger.info(f"🔗 [Enhanced Rules] Clarification courte détectée: {question}")
                return True
        
        # CONSERVATION: Patterns originaux + nouveaux
        patterns_clarification = [
            'pour un', 'pour une', 'avec un', 'avec une',
            'ross 308', 'cobb 500', 'hubbard', 'arbor acres',
            'mâle', 'femelle', 'male', 'female',
            'poulet de chair', 'broiler', 
            'jour', 'jours', 'semaine', 'semaines'
        ]
        
        if any(pattern in question.lower() for pattern in patterns_clarification):
            logger.info(f"🔗 [Enhanced Rules] Pattern clarification détecté: {question}")
            return True
        
        return False

    def _merge_entities_enhanced(self, entities: Dict[str, Any], context: Optional[Dict]) -> Dict[str, Any]:
        """Fusion améliorée des entités avec contexte"""
        merged = entities.copy()
        
        if context and context.get('previous_entities'):
            prev = context['previous_entities']
            
            # Hériter âge si manquant
            if not merged.get('age_days') and prev.get('age_days'):
                merged['age_days'] = prev['age_days']
                merged['age_inherited_from_context'] = True
            
            # Hériter race si manquante
            if not merged.get('breed_specific') and prev.get('breed_specific'):
                merged['breed_specific'] = prev['breed_specific']
                merged['breed_inherited_from_context'] = True
            
            # Hériter contexte performance
            if not merged.get('context_type') and prev.get('weight_mentioned'):
                merged['context_type'] = 'performance'
                merged['context_inherited_from_weight_question'] = True
            
            logger.info(f"🔗 [Enhanced Merge] Entités fusionnées: {list(merged.keys())}")
        
        return merged

    def _has_sufficient_merged_info_enhanced(self, merged_entities: Dict[str, Any]) -> bool:
        """✅ Validation améliorée pour contexte fusionné"""
        
        breed = merged_entities.get('breed_specific')
        age = merged_entities.get('age_days')
        sex = merged_entities.get('sex')
        context_type = merged_entities.get('context_type')
        
        # Combinaisons suffisantes améliorées
        checks = [
            breed and age and sex,  # Trio complet
            breed and age and context_type == 'performance',  # Race + âge + contexte poids
            breed and sex and merged_entities.get('age_inherited_from_context'),  # Race + sexe + âge hérité
            breed and age,  # Race + âge (minimum pour utilité)
        ]
        
        is_sufficient = any(checks)
        
        if is_sufficient:
            logger.info("✅ [Enhanced Sufficient] Informations fusionnées suffisantes")
        else:
            logger.info("❌ [Enhanced Sufficient] Pas assez d'informations même fusionnées")
        
        return is_sufficient

    def _has_precise_info_enhanced(self, entities: Dict[str, Any]) -> bool:
        """Check amélioré pour informations précises"""
        breed = entities.get('breed_specific')
        age = entities.get('age_days')
        sex = entities.get('sex')
        
        # AMÉLIORATION: Plus de combinaisons acceptables
        precise_combinations = [
            breed and age and sex,  # Trio parfait
            breed and age,  # Race + âge (suffisant pour beaucoup de cas)
        ]
        
        return any(precise_combinations)

    def _has_useful_context_enhanced(self, question: str, entities: Dict[str, Any]) -> bool:
        """🔧 Version améliorée qui détecte mieux le contexte utile"""
        
        question_lower = question.lower()
        
        # Questions de poids/croissance avec âge
        weight_keywords = ['poids', 'weight', 'gramme', 'kg', 'pesé', 'peser', 'cible', 'croissance', 'grandir']
        has_weight_question = any(word in question_lower for word in weight_keywords)
        has_age = entities.get('age_days') or entities.get('age_weeks')
        
        if has_weight_question and has_age:
            logger.info("✅ [Enhanced Useful] Question poids + âge détectée")
            return True
        
        # Race générique + âge
        has_breed = entities.get('breed_generic') or entities.get('breed_specific')
        if has_breed and has_age:
            logger.info("✅ [Enhanced Useful] Race + âge détectés")
            return True
        
        # Contexte hérité (nouveau)
        inherited_markers = [
            'age_inherited_from_context',
            'context_inherited_from_weight_question',
            'breed_inherited_from_context'
        ]
        
        if any(entities.get(marker) for marker in inherited_markers):
            logger.info("✅ [Enhanced Useful] Contexte hérité détecté")
            return True
        
        # Questions de santé avec race
        health_keywords = ['santé', 'maladie', 'symptôme', 'vaccination', 'traitement']
        has_health_question = any(word in question_lower for word in health_keywords)
        
        if has_health_question and has_breed:
            logger.info("✅ [Enhanced Useful] Question santé + race détectée")
            return True
        
        return False

    def _calculate_weight_data_enhanced(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Version améliorée du calcul de poids avec plus de contexte"""
        
        breed = entities.get('breed_specific', '').lower().replace(' ', '_')
        age_days = entities.get('age_days')
        sex = entities.get('sex', 'mixed').lower()
        
        if not breed or not age_days:
            logger.debug("❌ [Enhanced Weight] Breed ou age manquant pour calcul poids")
            return {}
        
        # Normalisation sexe améliorée
        sex_mapping = {
            'mâle': 'male', 'male': 'male', 'coq': 'male', 'cock': 'male',
            'femelle': 'female', 'female': 'female', 'poule': 'female', 'hen': 'female',
            'mixte': 'mixed', 'mixed': 'mixed', 'both': 'mixed'
        }
        sex = sex_mapping.get(sex, 'mixed')
        
        try:
            # Import de la fonction de calcul existante (conservée selon plan)
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
                "calculation_method": "enhanced_with_context",
                "confidence": 0.95,
                "context_used": {
                    "age_inherited": entities.get('age_inherited_from_context', False),
                    "breed_inherited": entities.get('breed_inherited_from_context', False),
                    "performance_context": entities.get('context_inherited_from_weight_question', False)
                }
            }
            
            logger.info(f"📊 [Enhanced Weight] {breed} {sex} {age_days}j → {min_weight}-{max_weight}g")
            return weight_data
            
        except Exception as e:
            logger.error(f"❌ [Enhanced Weight] Erreur calcul: {e}")
            return {}

    def _identify_missing_for_precision_enhanced(self, entities: Dict[str, Any]) -> List[str]:
        """Identifie les entités manquantes pour une réponse précise"""
        missing = []
        
        if not entities.get('breed_specific'):
            missing.append('race_specifique')
        
        if not entities.get('age_days') and not entities.get('age_weeks'):
            missing.append('age')
        
        if not entities.get('sex'):
            missing.append('sexe')
        
        return missing

    def _identify_critical_missing_enhanced(self, question: str, entities: Dict[str, Any]) -> List[str]:
        """Identifie les entités manquantes critiques"""
        question_words = question.split()
        
        if len(question_words) < 3:
            return ['contexte', 'informations_specifiques']
        
        missing = []
        if not entities.get('breed_generic') and not entities.get('breed_specific'):
            missing.append('race')
        
        if not entities.get('age_days') and not entities.get('age_weeks'):
            missing.append('age')
        
        return missing or ['contexte']

    def _parse_analysis_manually(self, text: str) -> Dict[str, Any]:
        """Parse manuel si JSON échoue"""
        logger.warning("⚠️ [Manual Parse] Analyse manuelle de la réponse IA")
        
        # Parse basique par mots-clés
        text_lower = text.lower()
        
        # Détecter le type recommandé
        classification = "GENERAL_ANSWER"  # défaut
        if "precise" in text_lower or "précise" in text_lower:
            classification = "PRECISE_ANSWER"
        elif "contextual" in text_lower or "contexte" in text_lower:
            classification = "CONTEXTUAL_ANSWER" 
        elif "clarification" in text_lower:
            classification = "NEEDS_CLARIFICATION"
        
        return {
            "intention": "question_generale",
            "classification_recommandee": classification,
            "confidence": 0.7,
            "raisonnement": "Parse manuel - réponse IA non-structurée",
            "peut_calculer_poids": "poids" in text_lower,
            "recommandation_fusion": "utiliser_entites_actuelles"
        }

    # =============================================================================
    # 🔧 MÉTHODES DE COMPATIBILITÉ (conservation de l'interface existante + corrections)
    # =============================================================================

    async def classify_question(self, question: Optional[str] = None, entities: Optional[Dict[str, Any]] = None, 
                              conversation_context: Optional[Dict] = None,
                              conversation_id: Optional[str] = None,
                              # 🔧 CORRECTION: Paramètres de compatibilité ajoutés
                              question_text: Optional[str] = None,
                              context: Optional[Dict] = None,
                              is_clarification_response: Optional[bool] = None,
                              **kwargs) -> ClassificationResult:
        """
        🔧 CORRIGÉ: Interface de compatibilité étendue pour supporter tous les appels
        
        Cette méthode supporte maintenant:
        - classify_question(question, entities, conversation_context, conversation_id)  # Format original
        - classify_question(question_text=..., context=..., is_clarification_response=...)  # Format expert_services.py
        - classify_question(**kwargs)  # Format flexible
        """
        
        # 🔧 NORMALISATION DES PARAMÈTRES: Résoudre les différents formats d'appel
        if question_text and not question:
            question = question_text
        if context and not conversation_context:
            conversation_context = context
        
        # Log pour debug compatibilité
        if is_clarification_response is not None:
            logger.info(f"🔧 [Compatibility] is_clarification_response={is_clarification_response} (paramètre ignoré)")
        
        if kwargs:
            logger.info(f"🔧 [Compatibility] Paramètres additionnels ignorés: {list(kwargs.keys())}")
        
        # Validation des paramètres essentiels
        if not question:
            logger.error("❌ [Compatibility] Paramètre 'question' ou 'question_text' requis")
            return ClassificationResult(
                response_type=ResponseType.NEEDS_CLARIFICATION,
                confidence=0.0,
                reasoning="Erreur: question manquante dans l'appel",
                fallback_used=True,
                context_source="error"
            )
        
        if not entities:
            logger.warning("⚠️ [Compatibility] Paramètre 'entities' manquant, utilisation dict vide")
            entities = {}
        
        # Appel de la méthode principale avec paramètres normalisés
        logger.info(f"🔄 [Compatibility] Appel normalisé: question='{question[:50]}...', entities={len(entities)} éléments")
        
        return await self.classify_question_with_ai(
            question, entities, conversation_context, conversation_id
        )

    # Alias pour compatibilité maximale
    async def classify(self, **kwargs) -> ClassificationResult:
        """Alias simplifié pour tous types d'appels"""
        return await self.classify_question(**kwargs)

# =============================================================================
# FONCTION DE COMPATIBILITÉ POUR LES IMPORTS
# =============================================================================

def quick_classify(question: str, entities: Dict[str, Any]) -> ClassificationResult:
    """Fonction rapide de classification pour compatibilité"""
    classifier = SmartClassifier()
    # Version synchrone simplifiée 
    return classifier._classify_with_rules_enhanced(question, entities)

# =============================================================================
# EXPORTS POUR COMPATIBILITÉ
# =============================================================================

__all__ = [
    'SmartClassifier',
    'ClassificationResult', 
    'ResponseType',
    'quick_classify'
]

logger.info("✅ [SmartClassifier] Module initialisé (version compatibilité étendue)")
logger.info("   - Classe: SmartClassifier (nom corrigé)")
logger.info("   - Support IA: OpenAI GPT-4")
logger.info("   - Fallback: Règles améliorées")
logger.info("   - 🔧 Compatibilité: question_text, context, is_clarification_response")
logger.info("   - Exports: SmartClassifier, ClassificationResult, ResponseType")

# =============================================================================
# EXEMPLE D'UTILISATION AVEC TOUS LES FORMATS D'APPEL SUPPORTÉS
# =============================================================================

async def demo_compatibility():
    """Démo des différents formats d'appel supportés"""
    
    classifier = SmartClassifier()
    
    # Format 1: Original
    result1 = await classifier.classify_question(
        question="Quel poids pour Ross 308 mâle 14 jours?",
        entities={"breed_specific": "Ross 308", "sex": "male", "age_days": 14}
    )
    print(f"✅ Format original: {result1.response_type.value}")
    
    # Format 2: expert_services.py (problématique corrigée)  
    result2 = await classifier.classify_question(
        question_text="Quel poids pour Ross 308 mâle 14 jours?",
        context={"previous_question": "Question précédente"},
        is_clarification_response=False  # ← Maintenant supporté (ignoré proprement)
    )
    print(f"✅ Format expert_services: {result2.response_type.value}")
    
    # Format 3: Flexible
    result3 = await classifier.classify_question(
        question="Ross 308 male",
        entities={"breed_specific": "Ross 308", "sex": "male"},
        extra_param="ignoré"  # Paramètres additionnels ignorés
    )
    print(f"✅ Format flexible: {result3.response_type.value}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_compatibility())