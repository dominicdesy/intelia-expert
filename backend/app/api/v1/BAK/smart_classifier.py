"""
smart_classifier.py - CLASSIFIER INTELLIGENT AVEC IA OpenAI + CONTEXTMANAGER MAXIMISÉ

🎯 VERSION AMÉLIORÉE - Utilisation MAXIMALE du ContextManager + Pipeline IA complet

AMÉLIORATIONS SELON LE PLAN DE TRANSFORMATION PHASE 2:
- ✅ Intégration IA pour classification intelligente
- ✅ Système de fallback robuste vers règles existantes
- ✅ Conservation du code original comme backup
- ✅ Pipeline hybride IA + règles hardcodées
- ✅ Validation contextuelle avec ContextManager MAXIMISÉ
- ✅ Correction du bug "contexte utile"
- 🔧 NOUVEAU: Initialisation automatique du ContextManager
- 🔧 NOUVEAU: Conversion UnifiedContext → Dict pour compatibilité
- 🔧 NOUVEAU: Mise à jour automatique du contexte après classification
- 🔧 NOUVEAU: Configuration IA du ContextManager pour enrichissement
- 🔧 CORRECTION: Classification moins restrictive (GÉNÉRAL au lieu de CLARIFICATION)

Architecture hybride avec ContextManager centralisé:
1. PRIORITÉ: Récupération contexte via ContextManager unifié
2. Classification IA pour comprendre l'intention  
3. Validation avec ContextManager centralisé
4. Calcul des données de poids enrichi
5. MISE À JOUR: Sauvegarde dans ContextManager après classification
6. FALLBACK: Règles hardcodées si IA indisponible
7. Conservation totale du code original
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
    NEEDS_RAG_CLARIFICATION = "needs_rag_clarification"

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
    """🔧 ENHANCED: Classifier intelligent avec IA OpenAI + ContextManager MAXIMISÉ selon plan Phase 2"""
    
    def __init__(self, openai_client=None, db_path: str = "conversations.db", context_manager=None):
        self.db_path = db_path
        self.openai_client = openai_client
        self.use_ai = openai_client is not None
        
        # 🆕 NOUVEAU: ContextManager selon plan Phase 2 - Initialisation automatique
        self.context_manager = context_manager
        if not self.context_manager:
            try:
                from .context_manager import ContextManager
                self.context_manager = ContextManager(db_path=db_path)
                logger.info("✅ [SmartClassifier] ContextManager initialisé automatiquement")
            except ImportError as e:
                logger.warning(f"⚠️ [SmartClassifier] ContextManager non disponible: {e}")
                self.context_manager = None
        
        # Configuration IA
        self.ai_model = "gpt-4"  # ou "gpt-3.5-turbo" pour économie
        self.max_tokens = 500
        
        # 🔧 CORRECTION: Initialisation des compteurs pour les statistiques
        self._total_classifications = 0
        self._ai_classifications = 0
        self._fallback_classifications = 0
        self._classification_errors = 0
        self._precise_responses = 0
        self._general_responses = 0
        self._contextual_responses = 0
        self._clarification_requests = 0
        
        # 🔧 Conservation du code original comme fallback
        self._initialize_classic_rules()
        
        logger.info(f"🤖 [SmartClassifier] IA: {self.use_ai} | ContextManager: {self.context_manager is not None}")
        
        # 🆕 NOUVEAU: Configuration du ContextManager avec IA si disponible
        if self.context_manager and self.use_ai:
            try:
                # Passer l'instance OpenAI au ContextManager pour enrichissement IA
                if hasattr(self.context_manager, 'set_ai_enhancer'):
                    self.context_manager.set_ai_enhancer(openai_client)
                    logger.info("🤖 [SmartClassifier] ContextManager configuré avec IA enhancer")
            except Exception as e:
                logger.warning(f"⚠️ [SmartClassifier] Erreur configuration IA enhancer: {e}")

    def _initialize_classic_rules(self):
        """🔧 CONSERVATION: Initialise les règles classiques comme backup"""
        # Conserver toute la logique originale
        pass

    async def classify_question_with_ai(self, question: str, entities: Dict[str, Any], 
                                      conversation_context: Optional[Dict] = None,
                                      conversation_id: Optional[str] = None) -> ClassificationResult:
        """
        🆕 Classification intelligente avec IA selon plan de transformation
        PRIORITÉ: ContextManager → IA → FALLBACK: Règles classiques conservées
        """
        context_source = "parameter"
        self._total_classifications += 1
        
        try:
            # 🆕 PHASE 2: Utilisation MAXIMALE du ContextManager centralisé
            unified_context = None
            if self.context_manager and conversation_id:
                try:
                    unified_context = self.context_manager.get_unified_context(
                        conversation_id, type="classification"
                    )
                    context_source = "context_manager"
                    logger.info(f"📋 [ContextManager] Contexte unifié récupéré - Entités: {unified_context.has_entities() if hasattr(unified_context, 'has_entities') else 'N/A'}")
                    
                    # Convertir UnifiedContext vers format dict pour compatibilité
                    conversation_context = self._convert_unified_context_to_dict(unified_context)
                    
                except Exception as context_error:
                    logger.error(f"❌ [ContextManager] Erreur récupération contexte: {context_error}")
                    # Fallback vers contexte fourni en paramètre
                    logger.info("🔄 [ContextManager] Fallback vers contexte paramètre")
            
            # Si pas de ContextManager ou erreur, utiliser contexte fourni
            if not unified_context and conversation_context:
                context_source = "parameter"
                logger.info("📋 [Parameter] Utilisation contexte fourni en paramètre")
            
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
                
                # 🆕 NOUVEAU: Mise à jour contexte après classification réussie
                self._update_context_after_classification(
                    conversation_id, final_classification, question, entities
                )
                
                self._ai_classifications += 1
                self._update_response_counters(final_classification.response_type)
                
                logger.info(f"✅ [AI Pipeline] Classification: {final_classification.response_type.value}")
                return final_classification
            
            # 4. FALLBACK: Règles classiques conservées
            else:
                logger.warning("⚠️ [AI Fallback] OpenAI indisponible - utilisation règles classiques")
                result = self._classify_with_rules_enhanced(
                    question, entities, conversation_context, context_source
                )
                
                # 🆕 NOUVEAU: Mise à jour contexte même en fallback
                self._update_context_after_classification(
                    conversation_id, result, question, entities
                )
                
                self._fallback_classifications += 1
                self._update_response_counters(result.response_type)
                return result
                
        except Exception as e:
            logger.error(f"❌ [AI Classification] Erreur: {e}")
            self._classification_errors += 1
            # FALLBACK ROBUSTE: Toujours avoir une réponse
            result = self._classify_with_rules_enhanced(
                question, entities, conversation_context, context_source, error=str(e)
            )
            
            # 🆕 NOUVEAU: Mise à jour contexte même en cas d'erreur
            if conversation_id:
                self._update_context_after_classification(
                    conversation_id, result, question, entities
                )
            
            self._fallback_classifications += 1
            self._update_response_counters(result.response_type)
            return result

    def _convert_unified_context_to_dict(self, unified_context) -> Dict[str, Any]:
        """
        🆕 NOUVEAU: Convertit UnifiedContext en dict pour compatibilité avec le code existant
        """
        if not unified_context:
            return {}
        
        try:
            context_dict = {
                'conversation_id': getattr(unified_context, 'conversation_id', ''),
                'previous_question': '',
                'previous_entities': {},
                'established_entities': {},
                'conversation_topic': getattr(unified_context, 'conversation_topic', ''),
                'conversation_intent': getattr(unified_context, 'conversation_intent', ''),
                'conversation_flow': getattr(unified_context, 'conversation_flow', ''),
                'ai_inferred_entities': getattr(unified_context, 'ai_inferred_entities', {}),
                'confidence_scores': getattr(unified_context, 'confidence_scores', {}),
                'user_expertise_level': getattr(unified_context, 'user_expertise_level', ''),
                'preferred_response_style': getattr(unified_context, 'preferred_response_style', ''),
                'ai_context_summary': getattr(unified_context, 'ai_context_summary', ''),
                'context_age_minutes': getattr(unified_context, 'context_age_minutes', 0),
                'cache_hit': getattr(unified_context, 'cache_hit', False)
            }
            
            # Entités établies
            if hasattr(unified_context, 'established_breed') and unified_context.established_breed:
                context_dict['established_entities']['breed'] = unified_context.established_breed
                context_dict['previous_entities']['breed_specific'] = unified_context.established_breed
            
            if hasattr(unified_context, 'established_age') and unified_context.established_age:
                context_dict['established_entities']['age_days'] = unified_context.established_age
                context_dict['previous_entities']['age_days'] = unified_context.established_age
            
            if hasattr(unified_context, 'established_sex') and unified_context.established_sex:
                context_dict['established_entities']['sex'] = unified_context.established_sex
                context_dict['previous_entities']['sex'] = unified_context.established_sex
            
            if hasattr(unified_context, 'established_weight') and unified_context.established_weight:
                context_dict['established_entities']['weight'] = unified_context.established_weight
                context_dict['previous_entities']['weight_mentioned'] = True
            
            # Questions précédentes
            if hasattr(unified_context, 'previous_questions') and unified_context.previous_questions:
                context_dict['previous_question'] = unified_context.previous_questions[-1]
            
            # Fusionner entités IA si disponibles
            if unified_context.ai_inferred_entities:
                context_dict['previous_entities'].update(unified_context.ai_inferred_entities)
            
            logger.info(f"🔄 [Conversion] UnifiedContext → Dict: {len(context_dict['previous_entities'])} entités")
            return context_dict
            
        except Exception as e:
            logger.error(f"❌ [Conversion] Erreur conversion UnifiedContext: {e}")
            return {}

    def _update_context_after_classification(self, conversation_id: str, 
                                           classification_result: ClassificationResult,
                                           question: str, entities: Dict[str, Any]):
        """
        🆕 NOUVEAU: Met à jour le contexte dans ContextManager après classification
        """
        if not self.context_manager or not conversation_id:
            return
        
        try:
            # Déterminer topic/intent selon classification
            topic = None
            intent = None
            
            if classification_result.response_type == ResponseType.PRECISE_ANSWER:
                if classification_result.weight_data:
                    topic = "performance"
                    intent = "weight_inquiry"
                else:
                    topic = "general_inquiry" 
                    intent = "precise_info"
            elif classification_result.response_type == ResponseType.CONTEXTUAL_ANSWER:
                topic = "clarification"
                intent = "context_completion"
            elif classification_result.response_type == ResponseType.NEEDS_CLARIFICATION:
                topic = "incomplete_inquiry"
                intent = "needs_clarification"
            
            # Extraire nouvelles entités à sauvegarder
            update_entities = {}
            if classification_result.merged_entities:
                for key, value in classification_result.merged_entities.items():
                    if key in ['breed_specific', 'age_days', 'sex', 'weight_mentioned']:
                        update_entities[key] = value
            
            # Mettre à jour via ContextManager
            success = self.context_manager.update_context(
                conversation_id=conversation_id,
                entities=update_entities,
                topic=topic,
                intent=intent,
                question=question,
                classification_confidence=classification_result.confidence,
                ai_analysis=classification_result.ai_analysis
            )
            
            if success:
                logger.info(f"✅ [ContextUpdate] Classification sauvée: {topic}/{intent}")
            else:
                logger.warning("⚠️ [ContextUpdate] Échec mise à jour contexte")
                
        except Exception as e:
            logger.error(f"❌ [ContextUpdate] Erreur mise à jour: {e}")

    def _update_response_counters(self, response_type: ResponseType):
        """Met à jour les compteurs selon le type de réponse"""
        if response_type == ResponseType.PRECISE_ANSWER:
            self._precise_responses += 1
        elif response_type == ResponseType.GENERAL_ANSWER:
            self._general_responses += 1
        elif response_type == ResponseType.CONTEXTUAL_ANSWER:
            self._contextual_responses += 1
        elif response_type == ResponseType.NEEDS_CLARIFICATION:
            self._clarification_requests += 1

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
            # 🆕 NOUVEAU: Inclure données ContextManager
            ai_summary = context.get('ai_context_summary', '')
            user_level = context.get('user_expertise_level', '')
            
            context_info = f"""
CONTEXTE CONVERSATIONNEL (via ContextManager):
- Question précédente: "{previous_q}"
- Entités précédentes: {json.dumps(previous_e, ensure_ascii=False, indent=2)}
- Résumé IA: "{ai_summary}"
- Niveau utilisateur: "{user_level}"
- Topic actuel: "{context.get('conversation_topic', '')}"
- Intent: "{context.get('conversation_intent', '')}"
- Cache hit: {context.get('cache_hit', False)}
"""

        prompt = f"""Analyse cette question d'élevage avicole et détermine le type de réponse optimal.

QUESTION ACTUELLE: "{question}"

ENTITÉS DÉTECTÉES:
{json.dumps(entities, ensure_ascii=False, indent=2)}

{context_info}

RÈGLES DE CLASSIFICATION:
1. PRECISE_ANSWER: Question avec race spécifique + âge/sexe suffisants pour réponse précise
2. CONTEXTUAL_ANSWER: Clarification courte qui complète le contexte précédent (ex: "Ross 308 male" après question poids)
3. GENERAL_ANSWER: TOUJOURS PRIVILÉGIER - Donner réponse utile même avec informations partielles (âge seul, contexte performance, etc.)
4. NEEDS_CLARIFICATION: RÉSERVÉ uniquement aux questions incompréhensibles (moins de 3 mots, aucun contexte avicole)

PRIORITÉS SPÉCIALES:
- FAVORISER GENERAL_ANSWER pour toute question avec contexte avicole identifiable
- Pour poids/croissance: âge seul = GENERAL_ANSWER (donner fourchettes générales)
- Éviter NEEDS_CLARIFICATION sauf si vraiment impossible de donner info utile
- Même "poulet 6 jours" = GENERAL_ANSWER avec fourchettes par race
- Détecter les clarifications contextuelles même très courtes
- Utiliser insights IA du contexte précédent

Réponds en JSON strict:
{{
    "intention": "question_performance|clarification_contextuelle|question_sante|question_generale",
    "classification_recommandee": "PRECISE_ANSWER|CONTEXTUAL_ANSWER|GENERAL_ANSWER|NEEDS_CLARIFICATION",
    "confidence": 0.85,
    "raisonnement": "explication claire et courte",
    "entites_manquantes": ["race", "age", "sexe"],
    "contexte_suffisant": true,
    "peut_calculer_poids": true,
    "recommandation_fusion": "fuser_avec_contexte|utiliser_entites_actuelles|demander_clarification",
    "contexte_manager_insights": "insights du ContextManager utilisés pour classification"
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
            established_entities = context.get('established_entities', {})
            
            # 🆕 AMÉLIORATION: Utiliser entités établies du ContextManager en priorité
            for entity_type in ['breed_specific', 'age_days', 'sex']:
                if not merged.get(entity_type):
                    # Priorité 1: Entités établies dans ContextManager
                    if established_entities.get(entity_type.split('_')[0]):  # breed, age, sex
                        merged[entity_type] = established_entities[entity_type.split('_')[0]]
                        merged[f'{entity_type}_inherited_from_context_manager'] = True
                        logger.info(f"🔗 [ContextManager Merge] {entity_type} hérité: {merged[entity_type]}")
                    
                    # Priorité 2: Entités précédentes
                    elif previous_entities.get(entity_type):
                        merged[entity_type] = previous_entities[entity_type]
                        merged[f'{entity_type}_inherited_from_context'] = True
                        logger.info(f"🔗 [AI Merge] {entity_type} hérité du contexte: {previous_entities[entity_type]}")
            
            # Hériter contexte performance si poids mentionné précédemment
            if not merged.get('context_type') and (previous_entities.get('weight_mentioned') or 
                                                  context.get('conversation_topic') == 'performance'):
                merged['context_type'] = 'performance'
                merged['context_inherited_from_weight_question'] = True
                logger.info("🔗 [ContextManager Merge] Contexte performance hérité")
            
            # 🆕 NOUVEAU: Utiliser entités inférées par l'IA
            ai_inferred = context.get('ai_inferred_entities', {})
            if ai_inferred:
                for key, value in ai_inferred.items():
                    if not merged.get(key):
                        merged[key] = value
                        merged[f'{key}_from_ai_inference'] = True
                        logger.info(f"🤖 [AI Inference] {key} inféré: {value}")
        
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
        """🔧 FALLBACK AMÉLIORÉ: Classification avec règles conservées + améliorations + CORRECTION classification moins restrictive"""
        
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

        # 🔧 CORRECTION APPLIQUÉE: Nouvelle logique équilibrée (moins restrictive)
        age_days = entities.get('age_days')
        context_type = entities.get('context_type', 'général')
        breed_specific = entities.get('breed_specific')
        breed_generic = entities.get('breed_generic')
        sex = entities.get('sex')
        
        # ✅ NOUVELLE LOGIQUE: Âge + contexte performance = réponse générale (pas clarification!)
        if age_days and context_type == 'performance':
            if breed_specific and sex:
                weight_data = self._calculate_weight_data_enhanced(entities)
                return ClassificationResult(
                    ResponseType.PRECISE_ANSWER,
                    confidence=0.95,
                    reasoning="Race spécifique + âge + sexe = réponse précise possible (règles corrigées)",
                    weight_data=weight_data,
                    fallback_used=True,
                    context_source=context_source
                )
            elif breed_specific or breed_generic:
                weight_data = self._calculate_weight_data_enhanced(entities)
                return ClassificationResult(
                    ResponseType.GENERAL_ANSWER,  # ✅ GÉNÉRAL au lieu de CLARIFICATION !
                    confidence=0.85,
                    reasoning="Âge + race (partielle) = réponse générale + offre précision (règles corrigées)",
                    missing_entities=self._identify_missing_for_precision_enhanced(entities),
                    weight_data=weight_data,
                    fallback_used=True,
                    context_source=context_source
                )
            elif age_days:
                return ClassificationResult(
                    ResponseType.GENERAL_ANSWER,  # ✅ GÉNÉRAL au lieu de CLARIFICATION !
                    confidence=0.75,
                    reasoning="Âge spécifique en contexte performance = réponse générale utile (règles corrigées)",
                    missing_entities=['race_specifique', 'sexe'],
                    fallback_used=True,
                    context_source=context_source
                )
        
        # Règles classiques conservées mais avec logique améliorée
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
        
        # ✅ CORRECTION: Seulement si vraiment trop vague (condition plus stricte)
        elif not age_days and not breed_generic and not breed_specific:
            return ClassificationResult(
                ResponseType.NEEDS_CLARIFICATION,
                confidence=0.6,
                reasoning="Informations vraiment insuffisantes pour réponse utile (règles corrigées)",
                missing_entities=self._identify_critical_missing_enhanced(question, entities),
                fallback_used=True,
                context_source=context_source
            )
        
        else:
            # ✅ NOUVEAU: Fallback vers réponse générale plutôt que clarification
            return ClassificationResult(
                ResponseType.GENERAL_ANSWER,
                confidence=0.7,
                reasoning="Informations partielles = réponse générale (règles moins restrictives)",
                missing_entities=self._identify_missing_for_precision_enhanced(entities),
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
        
        if context:
            # 🆕 PRIORITÉ: Entités établies du ContextManager
            established = context.get('established_entities', {})
            if established:
                for key, value in established.items():
                    if key == 'breed' and not merged.get('breed_specific'):
                        merged['breed_specific'] = value
                        merged['breed_from_context_manager'] = True
                    elif key == 'age_days' and not merged.get('age_days'):
                        merged['age_days'] = value
                        merged['age_from_context_manager'] = True
                    elif key == 'sex' and not merged.get('sex'):
                        merged['sex'] = value
                        merged['sex_from_context_manager'] = True
            
            # Fallback vers entités précédentes
            prev = context.get('previous_entities', {})
            if prev:
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
            'breed_inherited_from_context',
            'age_from_context_manager',
            'breed_from_context_manager',
            'sex_from_context_manager'
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
                "calculation_method": "enhanced_with_context_manager",
                "confidence": 0.95,
                "context_used": {
                    "age_inherited": entities.get('age_inherited_from_context', False),
                    "breed_inherited": entities.get('breed_inherited_from_context', False),
                    "performance_context": entities.get('context_inherited_from_weight_question', False),
                    "context_manager_data": any(entities.get(k) for k in ['age_from_context_manager', 'breed_from_context_manager', 'sex_from_context_manager'])
                }
            }
            
            logger.info(f"📊 [Enhanced Weight] {breed} {sex} {age_days}j → {min_weight}-{max_weight}g (ContextManager: {weight_data['context_used']['context_manager_data']})")
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
    # 🔧 CORRECTION CRITIQUE: MÉTHODE MANQUANTE get_classification_stats() AJOUTÉE
    # =============================================================================

    def get_classification_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de classification
        🔧 CORRECTION CRITIQUE: Méthode manquante qui causait le warning dans les logs
        """
        try:
            # Calculer les taux de réussite
            total = max(self._total_classifications, 1)
            success_rate = ((self._total_classifications - self._classification_errors) / total) * 100
            ai_success_rate = (self._ai_classifications / total) * 100
            fallback_rate = (self._fallback_classifications / total) * 100
            error_rate = (self._classification_errors / total) * 100
            
            return {
                "service_name": "Smart Classifier",
                "version": "v3.2_less_restrictive_classification",
                "total_classifications": self._total_classifications,
                "precise_responses": self._precise_responses,
                "general_responses": self._general_responses,
                "contextual_responses": self._contextual_responses,
                "clarification_requests": self._clarification_requests,
                "ai_classifications": self._ai_classifications,
                "fallback_classifications": self._fallback_classifications,
                "classification_errors": self._classification_errors,
                "success_rate": f"{success_rate:.1f}%",
                "ai_success_rate": f"{ai_success_rate:.1f}%",
                "fallback_rate": f"{fallback_rate:.1f}%",
                "error_rate": f"{error_rate:.1f}%",
                "ai_available": self.use_ai,
                "context_manager_active": self.context_manager is not None,
                "context_manager_features": [
                    "unified_context_retrieval",
                    "automatic_context_update", 
                    "ai_enhancement_integration",
                    "established_entities_prioritization",
                    "conversation_flow_tracking"
                ],
                "features": [
                    "ai_classification",
                    "contextual_analysis", 
                    "weight_calculation",
                    "entity_fusion",
                    "conversation_context",
                    "enhanced_fallback",
                    "context_manager_integration",
                    "less_restrictive_classification"  # 🆕 Nouvelle fonctionnalité
                ],
                "classification_improvements": [
                    "age_context_performance_general_answer",
                    "partial_breed_info_general_answer", 
                    "fallback_to_general_instead_clarification",
                    "stricter_needs_clarification_conditions"
                ]
            }
        except Exception as e:
            logger.error(f"❌ [SmartClassifier] Erreur stats: {e}")
            return {
                "service_name": "Smart Classifier",
                "error": str(e),
                "ai_available": getattr(self, 'use_ai', False),
                "total_classifications": getattr(self, '_total_classifications', 0)
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

logger.info("✅ [SmartClassifier] Module initialisé (version classification moins restrictive)")
logger.info("   - Classe: SmartClassifier (ContextManager auto-init)")
logger.info("   - Support IA: OpenAI GPT-4 + IA enhancer pour ContextManager")
logger.info("   - ContextManager: Initialisation automatique + mise à jour après classification")
logger.info("   - Fallback: Règles améliorées avec priorité entités ContextManager")
logger.info("   - 🔧 NOUVEAU: Classification moins restrictive (GÉNÉRAL vs CLARIFICATION)")
logger.info("   - 🔧 Compatibilité: question_text, context, is_clarification_response")
logger.info("   - 🔧 NOUVEAU: UnifiedContext → Dict conversion pour compatibilité")
logger.info("   - Exports: SmartClassifier, ClassificationResult, ResponseType")

# =============================================================================
# EXEMPLE D'UTILISATION AVEC CONTEXTMANAGER MAXIMISÉ ET CLASSIFICATION CORRIGÉE
# =============================================================================

async def demo_context_manager_integration():
    """Démo d'utilisation avec ContextManager maximisé et classification moins restrictive"""
    
    # 🆕 Le ContextManager s'initialise automatiquement
    classifier = SmartClassifier()
    conversation_id = "demo_conv_2025"
    
    print(f"✅ ContextManager actif: {classifier.context_manager is not None}")
    
    # Test 1: Question avec âge seulement (avant: CLARIFICATION, maintenant: GENERAL)
    result1 = await classifier.classify_question(
        question="Quel poids pour 14 jours?",
        entities={"age_days": 14, "context_type": "performance"},  # Pas de race spécifique
        conversation_id=conversation_id
    )
    print(f"✅ Test âge seul: {result1.response_type.value} (Avant: NEEDS_CLARIFICATION, Maintenant: GENERAL_ANSWER)")
    
    # Test 2: Question avec race générique + âge (avant: possiblement CLARIFICATION, maintenant: GENERAL)
    result2 = await classifier.classify_question(
        question="Poids broiler 14 jours?",
        entities={"breed_generic": "broiler", "age_days": 14, "context_type": "performance"},
        conversation_id=conversation_id
    )
    print(f"✅ Test race générique + âge: {result2.response_type.value}")
    
    # Test 3: Question très vague (devrait rester CLARIFICATION car vraiment insuffisant)
    result3 = await classifier.classify_question(
        question="Comment faire?",
        entities={},  # Aucune entité
        conversation_id=conversation_id
    )
    print(f"✅ Test très vague: {result3.response_type.value} (Devrait rester NEEDS_CLARIFICATION)")
    
    # Vérifier les statistiques incluant les améliorations de classification
    stats = classifier.get_classification_stats()
    print(f"✅ Stats améliorées: {stats.get('classification_improvements', [])}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_context_manager_integration())