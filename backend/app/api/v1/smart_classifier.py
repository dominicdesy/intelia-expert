"""
smart_classifier.py - CLASSIFIER INTELLIGENT AVEC CONTEXTE CONVERSATIONNEL COMPLET

🎯 SOLUTION COMPLÈTE:
- ✅ Détection des clarifications contextuelles
- ✅ Accès aux données de référence Ross 308  
- ✅ Persistance du contexte dans la base existante
- ✅ Intégration avec le pipeline existant
- ✅ Support complet du type CONTEXTUAL_ANSWER
- 🆕 MODIFICATION: Intégration ContextManager centralisé

Architecture:
- classify_question() : Point d'entrée unique avec contexte
- Accès direct aux standards de poids depuis intelligent_system_config
- Persistance automatique du contexte conversationnel
- Fusion intelligente des entités
- 🆕 ContextManager pour gestion centralisée du contexte
"""

import logging
import re
import sqlite3
import json
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

# Import des standards de poids depuis la config
from .intelligent_system_config import ReferenceData, get_weight_range

# 🆕 MODIFICATION: Import du ContextManager centralisé
try:
    from .context_manager import ContextManager
    CONTEXT_MANAGER_AVAILABLE = True
except ImportError:
    CONTEXT_MANAGER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ [Smart Classifier] ContextManager non disponible - utilisation du système local")

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types de réponse possibles"""
    PRECISE_ANSWER = "precise_answer"       # Assez d'infos pour réponse précise
    GENERAL_ANSWER = "general_answer"       # Réponse générale + offre de précision  
    NEEDS_CLARIFICATION = "needs_clarification"  # Vraiment trop vague
    CONTEXTUAL_ANSWER = "contextual_answer"    # Réponse basée sur contexte conversationnel

@dataclass
class ConversationContext:
    """Contexte d'une conversation avec accès aux standards"""
    previous_question: Optional[str] = None
    previous_entities: Optional[Dict[str, Any]] = None
    conversation_topic: Optional[str] = None  # performance, health, feeding
    established_breed: Optional[str] = None
    established_age: Optional[int] = None
    established_sex: Optional[str] = None
    last_interaction: Optional[datetime] = None
    
    # NOUVEAU: Données calculées pour réponse précise
    computed_weight_range: Optional[tuple] = None
    computed_confidence: float = 0.0
    
    def is_fresh(self, max_age_minutes: int = 10) -> bool:
        """Vérifie si le contexte est encore frais"""
        if not self.last_interaction:
            return False
        return datetime.now() - self.last_interaction < timedelta(minutes=max_age_minutes)
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sauvegarde"""
        return {
            "previous_question": self.previous_question,
            "previous_entities": self.previous_entities,
            "conversation_topic": self.conversation_topic,
            "established_breed": self.established_breed,
            "established_age": self.established_age,
            "established_sex": self.established_sex,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "computed_weight_range": self.computed_weight_range,
            "computed_confidence": self.computed_confidence
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationContext":
        """Crée depuis un dictionnaire"""
        context = cls()
        context.previous_question = data.get("previous_question")
        context.previous_entities = data.get("previous_entities")
        context.conversation_topic = data.get("conversation_topic")
        context.established_breed = data.get("established_breed")
        context.established_age = data.get("established_age")
        context.established_sex = data.get("established_sex")
        context.computed_weight_range = data.get("computed_weight_range")
        context.computed_confidence = data.get("computed_confidence", 0.0)
        
        last_interaction_str = data.get("last_interaction")
        if last_interaction_str:
            context.last_interaction = datetime.fromisoformat(last_interaction_str)
        
        return context

class ClassificationResult:
    """Résultat de la classification avec données de référence"""
    def __init__(self, response_type: ResponseType, confidence: float, reasoning: str, 
                 missing_entities: list = None, merged_entities: Dict[str, Any] = None,
                 weight_data: Dict[str, Any] = None):
        self.response_type = response_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.missing_entities = missing_entities or []
        self.merged_entities = merged_entities or {}
        self.weight_data = weight_data or {}  # NOUVEAU: Données de poids calculées

class SmartClassifier:
    """Classifier intelligent avec contexte conversationnel et accès aux données"""
    
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.confidence_thresholds = {
            "precise": 0.85,
            "general": 0.6,
            "clarification": 0.4
        }
        
        # 🆕 MODIFICATION: Initialisation du ContextManager si disponible
        if CONTEXT_MANAGER_AVAILABLE:
            try:
                self.context_manager = ContextManager(db_path)
                self.use_context_manager = True
                logger.info("✅ [Smart Classifier] ContextManager initialisé avec succès")
            except Exception as e:
                logger.warning(f"⚠️ [Smart Classifier] Erreur init ContextManager: {e}")
                self.context_manager = None
                self.use_context_manager = False
        else:
            self.context_manager = None
            self.use_context_manager = False
        
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
        
        # Initialiser la table de contexte (fallback si pas de ContextManager)
        if not self.use_context_manager:
            self._init_context_table()

    def _init_context_table(self):
        """Initialise la table pour stocker les contextes conversationnels (fallback)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_contexts (
                        conversation_id TEXT PRIMARY KEY,
                        context_data TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_contexts_updated ON conversation_contexts(updated_at)")
                logger.info("✅ [Smart Classifier] Table contextes initialisée (fallback)")
        except Exception as e:
            logger.error(f"❌ [Smart Classifier] Erreur init table contexte: {e}")

    def classify_question(self, question: str, entities: Dict[str, Any], 
                         conversation_id: Optional[str] = None,
                         is_clarification_response: bool = False) -> ClassificationResult:
        """
        POINT D'ENTRÉE PRINCIPAL - Classifie la question avec contexte conversationnel
        
        Args:
            question: Texte de la question
            entities: Entités extraites de la question
            conversation_id: ID de la conversation pour récupérer le contexte
            is_clarification_response: Indique si c'est une réponse de clarification
            
        Returns:
            ClassificationResult avec le type de réponse recommandé
        """
        try:
            logger.info(f"🧠 [Smart Classifier] Classification: '{question[:50]}...'")
            logger.info(f"🔍 [Smart Classifier] Entités: {entities}")
            
            # 🆕 MODIFICATION: Récupérer le contexte via ContextManager ou système local
            conversation_context = None
            if conversation_id:
                conversation_context = self._get_conversation_context_unified(conversation_id)
                logger.info(f"🔗 [Smart Classifier] Contexte récupéré: {conversation_context is not None}")
            
            # NOUVEAU: Détection des clarifications contextuelles
            if self._is_clarification_response(question, entities, conversation_context, is_clarification_response):
                merged_entities = self._merge_with_context(entities, conversation_context)
                logger.info(f"🔗 [Contextual] Entités fusionnées: {merged_entities}")
                
                if self._has_specific_info(merged_entities):
                    # NOUVEAU: Calculer les données de poids si c'est une question de performance
                    weight_data = self._calculate_weight_data(merged_entities)
                    
                    result = ClassificationResult(
                        ResponseType.CONTEXTUAL_ANSWER,
                        confidence=0.9,
                        reasoning="Clarification détectée - contexte fusionné pour réponse précise",
                        merged_entities=merged_entities,
                        weight_data=weight_data
                    )
                    
                    # 🆕 MODIFICATION: Sauvegarder le contexte via ContextManager ou système local
                    if conversation_id:
                        updated_context = self._create_conversation_context(question, merged_entities, conversation_context)
                        self._save_conversation_context_unified(conversation_id, updated_context)
                    
                    return result
            
            # Règle 1: PRÉCIS - Assez d'informations pour réponse spécifique
            if self._has_specific_info(entities):
                weight_data = self._calculate_weight_data(entities)
                result = ClassificationResult(
                    ResponseType.PRECISE_ANSWER,
                    confidence=0.9,
                    reasoning="Informations spécifiques suffisantes (race + âge/sexe)",
                    weight_data=weight_data
                )
                
                # 🆕 MODIFICATION: Sauvegarder le contexte via ContextManager ou système local
                if conversation_id:
                    new_context = self._create_conversation_context(question, entities, conversation_context)
                    self._save_conversation_context_unified(conversation_id, new_context)
                
                return result
            
            # Règle 2: GÉNÉRAL - Contexte suffisant pour réponse utile
            elif self._has_useful_context(question, entities):
                missing = self._identify_missing_for_precision(entities)
                result = ClassificationResult(
                    ResponseType.GENERAL_ANSWER,
                    confidence=0.8,
                    reasoning="Contexte suffisant pour réponse générale utile",
                    missing_entities=missing
                )
                
                # 🆕 MODIFICATION: Sauvegarder le contexte via ContextManager ou système local
                if conversation_id:
                    new_context = self._create_conversation_context(question, entities, conversation_context)
                    self._save_conversation_context_unified(conversation_id, new_context)
                
                return result
            
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

    # 🆕 NOUVELLE MÉTHODE: Récupération de contexte unifiée
    def _get_conversation_context_unified(self, conversation_id: str) -> Optional[ConversationContext]:
        """Récupère le contexte via ContextManager ou système local"""
        if self.use_context_manager and self.context_manager:
            try:
                # Utiliser le ContextManager centralisé
                context_data = self.context_manager.get_unified_context(
                    conversation_id, context_type="classification"
                )
                if context_data:
                    # Convertir les données du ContextManager vers ConversationContext
                    return self._convert_context_manager_data(context_data)
            except Exception as e:
                logger.warning(f"⚠️ [Context] Erreur ContextManager, fallback local: {e}")
        
        # Fallback vers le système local
        return self._get_conversation_context(conversation_id)

    # 🆕 NOUVELLE MÉTHODE: Sauvegarde de contexte unifiée
    def _save_conversation_context_unified(self, conversation_id: str, context: ConversationContext):
        """Sauvegarde le contexte via ContextManager ou système local"""
        if self.use_context_manager and self.context_manager:
            try:
                # Convertir ConversationContext vers format ContextManager
                context_data = self._convert_to_context_manager_format(context)
                self.context_manager.save_unified_context(
                    conversation_id, context_data, context_type="classification"
                )
                logger.info(f"💾 [Context] Contexte sauvegardé via ContextManager: {conversation_id}")
                return
            except Exception as e:
                logger.warning(f"⚠️ [Context] Erreur sauvegarde ContextManager, fallback local: {e}")
        
        # Fallback vers le système local
        self._save_conversation_context(conversation_id, context)

    # 🆕 NOUVELLE MÉTHODE: Conversion depuis ContextManager
    def _convert_context_manager_data(self, context_data: Dict[str, Any]) -> ConversationContext:
        """Convertit les données du ContextManager vers ConversationContext"""
        context = ConversationContext()
        
        # Mapping des champs
        context.previous_question = context_data.get("last_question")
        context.previous_entities = context_data.get("last_entities")
        context.conversation_topic = context_data.get("topic")
        context.established_breed = context_data.get("established_breed")
        context.established_age = context_data.get("established_age_days")
        context.established_sex = context_data.get("established_sex")
        
        # Gestion de la date
        last_interaction_str = context_data.get("last_interaction")
        if last_interaction_str:
            try:
                context.last_interaction = datetime.fromisoformat(last_interaction_str)
            except:
                context.last_interaction = datetime.now()
        
        return context

    # 🆕 NOUVELLE MÉTHODE: Conversion vers ContextManager
    def _convert_to_context_manager_format(self, context: ConversationContext) -> Dict[str, Any]:
        """Convertit ConversationContext vers format ContextManager"""
        return {
            "last_question": context.previous_question,
            "last_entities": context.previous_entities,
            "topic": context.conversation_topic,
            "established_breed": context.established_breed,
            "established_age_days": context.established_age,
            "established_sex": context.established_sex,
            "last_interaction": context.last_interaction.isoformat() if context.last_interaction else None,
            "classifier_version": "2.0.0_with_context_manager"
        }

    def _calculate_weight_data(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """NOUVEAU: Calcule les données de poids basées sur les entités"""
        
        breed = entities.get('breed_specific', '').lower().replace(' ', '_')
        age_days = entities.get('age_days')
        sex = entities.get('sex', 'mixed').lower()
        
        if not breed or not age_days:
            return {}
        
        # Normaliser le sexe
        if sex in ['mâle', 'male', 'coq']:
            sex = 'male'
        elif sex in ['femelle', 'female', 'poule']:
            sex = 'female'
        else:
            sex = 'mixed'
        
        try:
            # Utiliser la fonction de la config pour obtenir la fourchette
            weight_range = get_weight_range(breed, age_days, sex)
            min_weight, max_weight = weight_range
            target_weight = (min_weight + max_weight) // 2
            
            # Calculer les seuils d'alerte
            alert_low = int(min_weight * 0.85)
            alert_high = int(max_weight * 1.15)
            
            weight_data = {
                "breed": breed.replace('_', ' ').title(),
                "age_days": age_days,
                "sex": sex,
                "weight_range": weight_range,
                "target_weight": target_weight,
                "alert_thresholds": {
                    "low": alert_low,
                    "high": alert_high
                },
                "data_source": "intelligent_system_config",
                "confidence": 0.95
            }
            
            logger.info(f"📊 [Weight Data] Calculé: {breed} {sex} {age_days}j → {min_weight}-{max_weight}g")
            return weight_data
            
        except Exception as e:
            logger.error(f"❌ [Weight Data] Erreur calcul: {e}")
            return {}

    def _is_clarification_response(self, question: str, entities: Dict[str, Any], 
                                 context: Optional[ConversationContext], 
                                 is_clarification_flag: bool) -> bool:
        """Détecte si c'est une réponse de clarification"""
        
        # Flag explicite
        if is_clarification_flag:
            return True
            
        # Pas de contexte frais
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
        """Fusionne les entités actuelles avec le contexte conversationnel"""
        
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
        """Détermine s'il y a assez d'infos pour une réponse précise"""
        
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
            
        # Contexte de performance avec race et âge
        if breed_specific and context_type == 'performance':
            logger.info("✅ [Specific] Race + contexte performance")
            return True
            
        # Race + sexe + contexte âge hérité
        if breed_specific and sex and entities.get('age_context_inherited'):
            logger.info("✅ [Specific] Race + sexe + âge du contexte")
            return True
            
        return False

    def _has_useful_context(self, question: str, entities: Dict[str, Any]) -> bool:
        """Détermine s'il y a assez de contexte pour une réponse générale utile"""
        
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
        
        # Contexte hérité de performance
        if entities.get('weight_context_inherited') or entities.get('age_context_inherited'):
            logger.info("✅ [Useful] Contexte performance hérité")
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

    # ===============================
    # MÉTHODES LOCALES (FALLBACK)
    # ===============================

    def _get_conversation_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Récupère le contexte d'une conversation depuis la base locale (fallback)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT context_data FROM conversation_contexts 
                    WHERE conversation_id = ?
                """, (conversation_id,))
                
                row = cursor.fetchone()
                if row:
                    context_data = json.loads(row[0])
                    return ConversationContext.from_dict(context_data)
                    
        except Exception as e:
            logger.error(f"❌ [Context] Erreur récupération contexte local: {e}")
        
        return None

    def _save_conversation_context(self, conversation_id: str, context: ConversationContext):
        """Sauvegarde le contexte d'une conversation dans la base locale (fallback)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                context_json = json.dumps(context.to_dict())
                now = datetime.now().isoformat()
                
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_contexts 
                    (conversation_id, context_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (conversation_id, context_json, now, now))
                
                logger.info(f"💾 [Context] Contexte sauvegardé localement: {conversation_id}")
                
        except Exception as e:
            logger.error(f"❌ [Context] Erreur sauvegarde contexte local: {e}")

    def _create_conversation_context(self, question: str, entities: Dict[str, Any], 
                                   previous_context: Optional[ConversationContext] = None) -> ConversationContext:
        """Crée un nouveau contexte conversationnel"""
        
        context = ConversationContext()
        context.previous_question = question
        context.previous_entities = entities
        context.last_interaction = datetime.now()
        
        # Déterminer le topic de conversation
        question_lower = question.lower()
        if any(word in question_lower for word in ['poids', 'croissance', 'performance', 'cible']):
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
            "classifier_version": "2.0.0_contextual_with_data_and_context_manager",
            "context_manager_active": self.use_context_manager,
            "context_manager_available": CONTEXT_MANAGER_AVAILABLE,
            "response_types": [t.value for t in ResponseType],
            "confidence_thresholds": self.confidence_thresholds,
            "supported_breeds_specific": len(self.specific_breeds),
            "supported_breeds_generic": len(self.generic_breeds),
            "clarification_indicators": len(self.clarification_indicators),
            "features": [
                "conversational_context",
                "clarification_detection", 
                "entity_inheritance",
                "contextual_merging",
                "weight_data_calculation",
                "database_persistence",
                "context_manager_integration"  # 🆕 NOUVEAU
            ],
            "data_sources": [
                "intelligent_system_config.ReferenceData",
                "conversation_contexts_table",
                "context_manager" if self.use_context_manager else "local_database"  # 🆕 NOUVEAU
            ]
        }

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def quick_classify(question: str, entities: Dict[str, Any] = None, 
                  conversation_id: str = None) -> str:
    """
    Classification rapide pour usage simple avec support du contexte
    
    Returns:
        String: 'precise', 'general', 'clarification', ou 'contextual'
    """
    if entities is None:
        entities = {}
    
    classifier = SmartClassifier()
    result = classifier.classify_question(question, entities, conversation_id)
    
    return {
        ResponseType.PRECISE_ANSWER: 'precise',
        ResponseType.GENERAL_ANSWER: 'general', 
        ResponseType.NEEDS_CLARIFICATION: 'clarification',
        ResponseType.CONTEXTUAL_ANSWER: 'contextual'
    }[result.response_type]

# =============================================================================
# TESTS INTÉGRÉS AVEC CONTEXTE ET DONNÉES
# =============================================================================

def test_classifier_complete():
    """Tests complets du classifier avec contexte et données"""
    classifier = SmartClassifier()
    
    print("🧪 Test de conversation complète avec données Ross 308:")
    print("=" * 60)
    
    # Simulation d'une conversation réelle
    conversation_id = "test_conv_12345"
    
    # Question 1: Question générale
    q1 = "Quel est le poids cible d'un poulet de 12 jours ?"
    e1 = {'age_days': 12, 'weight_mentioned': True, 'context_type': 'performance'}
    result1 = classifier.classify_question(q1, e1, conversation_id)
    
    print(f"Q1: {q1}")
    print(f"→ {result1.response_type.value} (confiance: {result1.confidence})")
    print(f"→ Entités manquantes: {result1.missing_entities}")
    print()
    
    # Question 2: Clarification (doit fusionner et calculer Ross 308 mâle 12j)
    q2 = "Pour un Ross 308 male"
    e2 = {'breed_specific': 'Ross 308', 'sex': 'mâle'}
    result2 = classifier.classify_question(q2, e2, conversation_id, is_clarification_response=True)
    
    print(f"Q2: {q2} (clarification)")
    print(f"→ {result2.response_type.value} (confiance: {result2.confidence})")
    print(f"→ Entités fusionnées: {result2.merged_entities}")
    print(f"→ Données de poids: {result2.weight_data}")
    print(f"→ Raisonnement: {result2.reasoning}")
    
    # Vérification du succès
    if result2.response_type == ResponseType.CONTEXTUAL_ANSWER:
        weight_data = result2.weight_data
        if weight_data and 'weight_range' in weight_data:
            min_w, max_w = weight_data['weight_range']
            print(f"✅ SUCCESS: Ross 308 mâle 12j → {min_w}-{max_w}g calculé!")
        else:
            print("❌ FAILED: Données de poids non calculées")
    else:
        print("❌ FAILED: Clarification non détectée")
    
    # 🆕 NOUVEAU: Test du ContextManager
    print("\n🔧 Test du ContextManager:")
    print(f"→ ContextManager disponible: {CONTEXT_MANAGER_AVAILABLE}")
    print(f"→ ContextManager actif: {classifier.use_context_manager}")
    stats = classifier.get_classification_stats()
    print(f"→ Version du classifier: {stats['classifier_version']}")
    print(f"→ Sources de données: {stats['data_sources']}")

if __name__ == "__main__":
    test_classifier_complete()