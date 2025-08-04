"""
app/api/v1/conversation_memory_integrated.py - SYSTÈME DE MÉMOIRE COMPLET INTÉGRÉ

🚨 VERSION FINALE INTÉGRÉE + MÉTHODES AGENTS:
✅ Toutes les fonctionnalités existantes conservées
✅ Système de clarification enrichi ajouté
✅ Fonction d'enrichissement de questions intégrée
✅ Méthodes utilitaires pour agents GPT ajoutées
✅ Prêt pour intégration directe dans FastAPI

NOUVELLES FONCTIONNALITÉS AJOUTÉES:
1. EnhancedClarificationSystem intégré dans IntelligentConversationMemory
2. build_enriched_question_from_clarification()
3. process_enhanced_question_with_clarification()
4. detect_clarification_state()
5. check_if_clarification_needed()
🤖 NOUVELLES MÉTHODES POUR AGENTS:
6. get_missing_entities() - Liste entités manquantes AVEC IMPORTANCE
7. get_formatted_context() - Contexte formaté pour agents
8. get_raw_context_summary() - Contexte brut complet pour inférence
"""

import os
import json
import logging
import sqlite3
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
import time
import threading
from threading import Lock

# Import OpenAI sécurisé pour extraction intelligente
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)

@dataclass
class IntelligentEntities:
    """Entités extraites intelligemment avec raisonnement contextuel"""
    
    # Informations de base
    breed: Optional[str] = None
    breed_confidence: float = 0.0
    breed_type: Optional[str] = None  # specific/generic
    
    # Sexe avec variations multilingues
    sex: Optional[str] = None
    sex_confidence: float = 0.0
    
    # Âge avec conversion intelligente
    age_days: Optional[int] = None
    age_weeks: Optional[float] = None
    age_confidence: float = 0.0
    age_last_updated: Optional[datetime] = None
    
    # Performance et croissance
    weight_grams: Optional[float] = None
    weight_confidence: float = 0.0
    expected_weight_range: Optional[Tuple[float, float]] = None
    growth_rate: Optional[str] = None  # normal/slow/fast
    
    # Santé et problèmes
    mortality_rate: Optional[float] = None
    mortality_confidence: float = 0.0
    symptoms: List[str] = field(default_factory=list)
    health_status: Optional[str] = None  # good/concerning/critical
    
    # Environnement
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    housing_type: Optional[str] = None
    ventilation_quality: Optional[str] = None
    
    # Alimentation
    feed_type: Optional[str] = None
    feed_conversion: Optional[float] = None
    water_consumption: Optional[str] = None
    
    # Gestion et historique
    flock_size: Optional[int] = None
    vaccination_status: Optional[str] = None
    previous_treatments: List[str] = field(default_factory=list)
    
    # Contextuel intelligent
    problem_duration: Optional[str] = None
    problem_severity: Optional[str] = None  # low/medium/high/critical
    intervention_urgency: Optional[str] = None  # none/monitor/act/urgent
    
    # Métadonnées IA
    extraction_method: str = "basic"  # basic/openai/hybrid/fallback
    extraction_attempts: int = 0
    extraction_success: bool = True
    last_ai_update: Optional[datetime] = None
    confidence_overall: float = 0.0
    data_validated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour logs et stockage"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, tuple):
                    result[key] = list(value)
                else:
                    result[key] = value
        return result
    
    def validate_and_correct(self) -> 'IntelligentEntities':
        """Valide et corrige automatiquement les données incohérentes"""
        
        # Validation âge
        if self.age_days and self.age_weeks:
            calculated_weeks = self.age_days / 7
            if abs(calculated_weeks - self.age_weeks) > 0.5:  # Tolérance 0.5 semaine
                logger.warning(f"⚠️ [Validation] Incohérence âge: {self.age_days}j vs {self.age_weeks}sem")
                # Prioriser les jours si confiance plus élevée
                if self.age_confidence > 0.7:
                    self.age_weeks = round(self.age_days / 7, 1)
                else:
                    self.age_days = int(self.age_weeks * 7)
        
        # Validation poids
        if self.weight_grams and self.age_days:
            # Vérifications de cohérence basiques
            if self.weight_grams < 10 or self.weight_grams > 5000:  # Limites réalistes
                logger.warning(f"⚠️ [Validation] Poids suspect: {self.weight_grams}g pour {self.age_days}j")
                if self.weight_grams > 5000:  # Probablement en kg au lieu de g
                    self.weight_grams = self.weight_grams / 1000
                    logger.info(f"✅ [Correction] Poids corrigé: {self.weight_grams}g")
        
        # Validation mortalité
        if self.mortality_rate is not None:
            if self.mortality_rate < 0:
                self.mortality_rate = 0
            elif self.mortality_rate > 100:
                logger.warning(f"⚠️ [Validation] Mortalité > 100%: {self.mortality_rate}")
                self.mortality_rate = min(self.mortality_rate, 100)
        
        # Validation température
        if self.temperature is not None:
            if self.temperature < 15 or self.temperature > 45:
                logger.warning(f"⚠️ [Validation] Température suspecte: {self.temperature}°C")
                if self.temperature > 100:  # Probablement en Fahrenheit
                    self.temperature = (self.temperature - 32) * 5/9
                    logger.info(f"✅ [Correction] Température convertie: {self.temperature:.1f}°C")
        
        # Nettoyer les listes
        if self.symptoms:
            self.symptoms = [s.strip().lower() for s in self.symptoms if s and s.strip()]
            self.symptoms = list(set(self.symptoms))  # Supprimer doublons
        
        if self.previous_treatments:
            self.previous_treatments = [t.strip() for t in self.previous_treatments if t and t.strip()]
            self.previous_treatments = list(set(self.previous_treatments))
        
        self.data_validated = True
        return self
    
    def get_critical_missing_info(self, question_type: str = "general") -> List[str]:
        """Détermine les informations critiques manquantes selon le contexte"""
        missing = []
        
        # Race toujours critique pour questions techniques
        if not self.breed or self.breed_type == "generic" or self.breed_confidence < 0.7:
            missing.append("breed")
        
        # Sexe critique pour questions de performance
        if question_type in ["performance", "weight", "growth"] and (not self.sex or self.sex_confidence < 0.7):
            missing.append("sex")
        
        # Âge critique pour la plupart des questions
        if not self.age_days or self.age_confidence < 0.7:
            missing.append("age")
        
        # Spécifique selon le type de question
        if question_type in ["growth", "weight", "performance"]:
            if not self.weight_grams and not self.growth_rate:
                missing.append("current_performance")
        elif question_type in ["health", "mortality", "disease"]:
            if not self.symptoms and not self.health_status:
                missing.append("symptoms")
            if self.mortality_rate is None and "mortality" in question_type:
                missing.append("mortality_rate")
        elif question_type in ["environment", "temperature", "housing"]:
            if not self.housing_type:
                missing.append("housing_conditions")
        elif question_type in ["feeding", "nutrition"]:
            if not self.feed_type:
                missing.append("feed_information")
        
        return missing
    
    def merge_with(self, other: 'IntelligentEntities') -> 'IntelligentEntities':
        """Fusionne intelligemment avec une autre instance d'entités"""
        merged = IntelligentEntities()
        
        # Logique de fusion pour chaque champ
        for field_name, field_value in asdict(self).items():
            other_value = getattr(other, field_name, None)
            
            # Prendre la valeur avec la meilleure confiance
            if field_name.endswith('_confidence'):
                base_field = field_name.replace('_confidence', '')
                self_conf = field_value or 0.0
                other_conf = getattr(other, field_name, 0.0) or 0.0
                
                if other_conf > self_conf:
                    setattr(merged, base_field, getattr(other, base_field))
                    setattr(merged, field_name, other_conf)
                else:
                    setattr(merged, base_field, getattr(self, base_field))
                    setattr(merged, field_name, self_conf)
            
            # Fusionner les listes
            elif isinstance(field_value, list):
                self_list = field_value or []
                other_list = other_value or []
                # Garder les éléments uniques
                merged_list = list(set(self_list + other_list))
                setattr(merged, field_name, merged_list)
            
            # Prendre la valeur la plus récente pour les dates
            elif isinstance(field_value, datetime):
                if other_value and (not field_value or other_value > field_value):
                    setattr(merged, field_name, other_value)
                else:
                    setattr(merged, field_name, field_value)
            
            # Logique par défaut
            else:
                if other_value is not None:
                    setattr(merged, field_name, other_value)
                elif field_value is not None:
                    setattr(merged, field_name, field_value)
        
        merged.last_ai_update = datetime.now()
        return merged.validate_and_correct()

@dataclass
class ConversationMessage:
    """Message dans une conversation avec métadonnées"""
    id: str
    conversation_id: str
    user_id: str
    role: str  # user/assistant/system
    message: str
    timestamp: datetime
    language: str = "fr"
    message_type: str = "text"  # text/clarification/response/original_question_marker
    extracted_entities: Optional[IntelligentEntities] = None
    confidence_score: float = 0.0
    processing_method: str = "basic"
    
    # ✅ CHAMPS POUR CLARIFICATIONS
    is_original_question: bool = False
    is_clarification_response: bool = False
    original_question_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "role": self.role,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "language": self.language,
            "message_type": self.message_type,
            "extracted_entities": self.extracted_entities.to_dict() if self.extracted_entities else None,
            "confidence_score": self.confidence_score,
            "processing_method": self.processing_method,
            "is_original_question": self.is_original_question,
            "is_clarification_response": self.is_clarification_response,
            "original_question_id": self.original_question_id
        }

@dataclass
class IntelligentConversationContext:
    """Contexte conversationnel intelligent avec raisonnement"""
    conversation_id: str
    user_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    
    # Entités consolidées intelligemment
    consolidated_entities: IntelligentEntities = field(default_factory=IntelligentEntities)
    
    # Métadonnées contextuelles
    language: str = "fr"
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    total_exchanges: int = 0
    
    # État conversationnel intelligent
    conversation_topic: Optional[str] = None
    conversation_urgency: Optional[str] = None  # low/medium/high/critical
    problem_resolution_status: Optional[str] = None  # identifying/diagnosing/treating/resolved
    
    # Optimisations IA
    ai_enhanced: bool = False
    last_ai_analysis: Optional[datetime] = None
    needs_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    
    # ✅ CHAMPS POUR CLARIFICATIONS
    pending_clarification: bool = False
    last_original_question_id: Optional[str] = None
    
    def add_message(self, message: ConversationMessage):
        """Ajoute un message et met à jour le contexte intelligemment"""
        self.messages.append(message)
        self.last_activity = datetime.now()
        self.total_exchanges += 1
        
        # ✅ TRACKING SPÉCIAL POUR CLARIFICATIONS
        if message.is_original_question:
            self.last_original_question_id = message.id
            self.pending_clarification = True
            logger.info(f"🎯 [Context] Question originale marquée: {message.id}")
        
        if message.is_clarification_response and message.original_question_id:
            self.pending_clarification = False
            logger.info(f"🎯 [Context] Clarification reçue pour: {message.original_question_id}")
        
        # Fusionner les entités si disponibles
        if message.extracted_entities:
            old_entities = self.consolidated_entities
            self.consolidated_entities = self.consolidated_entities.merge_with(message.extracted_entities)
            
            # Log des changements d'entités
            if old_entities.breed != self.consolidated_entities.breed:
                logger.info(f"🔄 [Entities] Race mise à jour: {old_entities.breed} → {self.consolidated_entities.breed}")
            if old_entities.sex != self.consolidated_entities.sex:
                logger.info(f"🔄 [Entities] Sexe mis à jour: {old_entities.sex} → {self.consolidated_entities.sex}")
            if old_entities.age_days != self.consolidated_entities.age_days:
                logger.info(f"🔄 [Entities] Âge mis à jour: {old_entities.age_days} → {self.consolidated_entities.age_days}j")
        
        # Mettre à jour le statut conversationnel
        self._update_conversation_status()
    
    def _update_conversation_status(self):
        """Met à jour le statut conversationnel basé sur les messages récents"""
        if not self.messages:
            return
        
        recent_messages = self.messages[-3:]  # 3 derniers messages
        
        # Analyser l'urgence basée sur les mots-clés
        urgency_keywords = {
            "critical": ["urgence", "urgent", "critique", "emergency", "critical", "dying", "meurent"],
            "high": ["problème", "problem", "maladie", "disease", "mortalité", "mortality"],
            "medium": ["inquiet", "concerned", "surveillance", "monitoring"],
            "low": ["prévention", "prevention", "routine", "normal"]
        }
        
        max_urgency = "low"
        for message in recent_messages:
            message_lower = message.message.lower()
            for urgency, keywords in urgency_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    if urgency == "critical":
                        max_urgency = "critical"
                        break
                    elif urgency == "high" and max_urgency not in ["critical"]:
                        max_urgency = "high"
                    elif urgency == "medium" and max_urgency in ["low"]:
                        max_urgency = "medium"
        
        self.conversation_urgency = max_urgency
    
    # ✅ FONCTION CRITIQUE - RÉCUPÉRATION QUESTION ORIGINALE
    def find_original_question(self, limit_messages: int = 20) -> Optional[ConversationMessage]:
        """
        🚨 FONCTION CRITIQUE - Trouve la question originale marquée pour clarification
        """
        
        # Rechercher par ID si on a un last_original_question_id
        if self.last_original_question_id:
            for msg in reversed(self.messages[-limit_messages:]):
                if msg.id == self.last_original_question_id and msg.is_original_question:
                    logger.info(f"✅ [Context] Question originale trouvée par ID: {msg.id}")
                    return msg
        
        # Rechercher par marqueur spécial dans le message
        for msg in reversed(self.messages[-limit_messages:]):
            if msg.role == "system" and "ORIGINAL_QUESTION_FOR_CLARIFICATION:" in msg.message:
                # Extraire la question du marqueur
                question_text = msg.message.replace("ORIGINAL_QUESTION_FOR_CLARIFICATION: ", "")
                
                # Créer un message virtuel pour la question originale
                original_msg = ConversationMessage(
                    id=f"original_{msg.id}",
                    conversation_id=self.conversation_id,
                    user_id=self.user_id,
                    role="user",
                    message=question_text,
                    timestamp=msg.timestamp,
                    language=self.language,
                    message_type="original_question",
                    is_original_question=True
                )
                
                logger.info(f"✅ [Context] Question originale extraite du marqueur: {question_text}")
                return original_msg
        
        # Rechercher par flag is_original_question
        for msg in reversed(self.messages[-limit_messages:]):
            if msg.is_original_question and msg.role == "user":
                logger.info(f"✅ [Context] Question originale trouvée par flag: {msg.message[:50]}...")
                return msg
        
        # Fallback: chercher la dernière question utilisateur avant demande clarification
        clarification_keywords = [
            "j'ai besoin de", "pouvez-vous préciser", "quelle est la race",
            "quel est le sexe", "breed", "sex", "clarification"
        ]
        
        for i, msg in enumerate(reversed(self.messages[-limit_messages:])):
            if msg.role == "assistant" and any(keyword in msg.message.lower() for keyword in clarification_keywords):
                # Chercher la question utilisateur juste avant cette clarification
                actual_index = len(self.messages) - 1 - i
                if actual_index > 0:
                    prev_msg = self.messages[actual_index - 1]
                    if prev_msg.role == "user":
                        logger.info(f"🔄 [Context] Question originale trouvée par fallback: {prev_msg.message[:50]}...")
                        return prev_msg
        
        logger.warning("⚠️ [Context] Question originale non trouvée!")
        return None
    
    def get_last_user_question(self, exclude_clarifications: bool = True) -> Optional[ConversationMessage]:
        """
        🚨 MÉTHODE FALLBACK - Récupère la dernière question utilisateur
        """
        
        for msg in reversed(self.messages):
            if msg.role == "user":
                # Exclure les réponses de clarification courtes si demandé
                if exclude_clarifications:
                    # Si c'est très court et contient une race/sexe, c'est probablement une clarification
                    if len(msg.message.split()) <= 3:
                        breed_sex_patterns = [
                            r'ross\s*308', r'cobb\s*500', r'hubbard',
                            r'mâles?', r'femelles?', r'males?', r'females?',
                            r'mixte', r'mixed'
                        ]
                        if any(re.search(pattern, msg.message.lower()) for pattern in breed_sex_patterns):
                            continue  # Ignorer cette réponse de clarification
                
                logger.info(f"🔄 [Context] Dernière question utilisateur: {msg.message[:50]}...")
                return msg
        
        logger.warning("⚠️ [Context] Aucune question utilisateur trouvée!")
        return None
    
    def get_context_for_clarification(self) -> Dict[str, Any]:
        """Retourne le contexte optimisé pour les clarifications"""
        
        # ✅ AMÉLIORATION - Inclure la question originale si trouvée
        original_question = self.find_original_question()
        
        context = {
            "breed": self.consolidated_entities.breed,
            "breed_type": self.consolidated_entities.breed_type,
            "sex": self.consolidated_entities.sex,
            "sex_confidence": self.consolidated_entities.sex_confidence,
            "age": self.consolidated_entities.age_days,
            "age_confidence": self.consolidated_entities.age_confidence,
            "weight": self.consolidated_entities.weight_grams,
            "symptoms": self.consolidated_entities.symptoms,
            "housing": self.consolidated_entities.housing_type,
            "urgency": self.conversation_urgency,
            "topic": self.conversation_topic,
            "total_exchanges": self.total_exchanges,
            "missing_critical": self.consolidated_entities.get_critical_missing_info(),
            "overall_confidence": self.consolidated_entities.confidence_overall,
            
            # ✅ NOUVEAUX CHAMPS CRITIQUES
            "original_question": original_question.message if original_question else None,
            "original_question_id": original_question.id if original_question else None,
            "pending_clarification": self.pending_clarification,
            "last_original_question_id": self.last_original_question_id
        }
        
        return context
    
    def _safe_topic_check(self, keywords: List[str]) -> bool:
        """Helper sécurisé pour vérifier les mots-clés dans conversation_topic"""
        if not self.conversation_topic:
            return False
        topic_lower = self.conversation_topic.lower()
        return any(keyword in topic_lower for keyword in keywords)

    # 🤖 MÉTHODES POUR AGENTS GPT AMÉLIORÉES
    def get_missing_entities(self, include_importance: bool = False) -> Union[List[str], Dict[str, str]]:
        """
        Retourne les entités manquantes avec leur niveau d'importance
        
        Args:
            include_importance: Si True, retourne dict avec importance, sinon liste simple
            
        Returns:
            Dict[entity, importance] ou List[entity] selon include_importance
            
        ⚠️  ATTENTION: Cette fonction retourne 2 types différents selon le paramètre !
            - include_importance=False: List[str] 
            - include_importance=True: Dict[str, str]
        """
        entities = self.consolidated_entities
        missing_with_importance = {}
        
        # Race - toujours critique pour questions techniques
        if not entities.breed or entities.breed_type == "generic" or entities.breed_confidence < 0.7:
            missing_with_importance["breed"] = "critique"
        
        # Sexe - critique pour performance, secondaire pour santé
        if not entities.sex or entities.sex_confidence < 0.7:
            # 🔒 PROTECTION None avec helper sécurisé
            if self._safe_topic_check(["performance", "weight", "growth", "croissance", "poids"]):
                missing_with_importance["sex"] = "critique"
            else:
                missing_with_importance["sex"] = "secondaire"
        
        # Âge - critique pour la plupart des questions
        if not entities.age_days or entities.age_confidence < 0.7:
            missing_with_importance["age"] = "critique"
        
        # Poids - critique pour questions de performance
        if not entities.weight_grams and not entities.growth_rate:
            # 🔒 PROTECTION None avec helper sécurisé
            if self._safe_topic_check(["performance", "weight", "growth", "croissance", "poids"]):
                missing_with_importance["current_performance"] = "critique"
            else:
                missing_with_importance["current_performance"] = "secondaire"
        
        # Symptômes - critique pour questions de santé
        if not entities.symptoms and not entities.health_status:
            # 🔒 PROTECTION None avec helper sécurisé
            if self._safe_topic_check(["health", "mortality", "disease", "santé", "mortalité", "maladie"]):
                missing_with_importance["symptoms"] = "critique"
            else:
                missing_with_importance["symptoms"] = "secondaire"
        
        # Mortalité - critique si mentionnée dans la conversation
        if entities.mortality_rate is None:
            recent_messages_text = " ".join([msg.message.lower() for msg in self.messages[-3:]])
            if any(keyword in recent_messages_text for keyword in ["mortality", "mortalité", "meurent", "dying"]):
                missing_with_importance["mortality_rate"] = "critique"
        
        # Conditions environnementales - secondaire sauf si problème mentionné
        if not entities.housing_type and not entities.temperature:
            # 🔒 PROTECTION None avec helper sécurisé
            if self._safe_topic_check(["environment", "temperature", "housing", "environnement", "température"]):
                missing_with_importance["housing_conditions"] = "critique"
            else:
                missing_with_importance["housing_conditions"] = "secondaire"
        
        # Alimentation - secondaire sauf si problème nutritionnel
        if not entities.feed_type:
            # 🔒 PROTECTION None avec helper sécurisé
            if self._safe_topic_check(["feeding", "nutrition", "alimentation", "nourriture"]):
                missing_with_importance["feed_information"] = "critique"
            else:
                missing_with_importance["feed_information"] = "secondaire"
        
        # 🚨 RETOUR CONDITIONNEL - ATTENTION AU TYPE !
        if include_importance:
            return missing_with_importance  # Type: Dict[str, str]
        else:
            return list(missing_with_importance.keys())  # Type: List[str]

    def get_raw_context_summary(self) -> Dict[str, Any]:
        """
        Retourne TOUT le contexte conversationnel brut pour les agents
        Même les données non validées ou partielles pour permettre l'inférence
        """
        entities = self.consolidated_entities
        
        # Messages récents pour analyse contextuelle
        recent_messages = []
        for msg in self.messages[-5:]:  # 5 derniers messages
            recent_messages.append({
                "role": msg.role,
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "confidence": msg.confidence_score,
                "entities_extracted": msg.extracted_entities.to_dict() if msg.extracted_entities else None
            })
        
        # Toutes les entités, même partielles
        raw_entities = {
            # Informations de base (même non validées)
            "breed": {
                "value": entities.breed,
                "confidence": entities.breed_confidence,
                "type": entities.breed_type,
                "validated": entities.breed_confidence > 0.7
            },
            "sex": {
                "value": entities.sex,
                "confidence": entities.sex_confidence,
                "validated": entities.sex_confidence > 0.7
            },
            "age": {
                "days": entities.age_days,
                "weeks": entities.age_weeks,
                "confidence": entities.age_confidence,
                "last_updated": entities.age_last_updated.isoformat() if entities.age_last_updated else None,
                "validated": entities.age_confidence > 0.7
            },
            
            # Performance et croissance
            "performance": {
                "weight_grams": entities.weight_grams,
                "weight_confidence": entities.weight_confidence,
                "expected_range": entities.expected_weight_range,
                "growth_rate": entities.growth_rate,
                "validated": entities.weight_confidence > 0.7
            },
            
            # Santé
            "health": {
                "mortality_rate": entities.mortality_rate,
                "mortality_confidence": entities.mortality_confidence,
                "symptoms": entities.symptoms,
                "health_status": entities.health_status,
                "previous_treatments": entities.previous_treatments,
                "validated": len(entities.symptoms) > 0 or entities.health_status is not None
            },
            
            # Environnement
            "environment": {
                "temperature": entities.temperature,
                "humidity": entities.humidity,
                "housing_type": entities.housing_type,
                "ventilation_quality": entities.ventilation_quality,
                "validated": entities.temperature is not None or entities.housing_type is not None
            },
            
            # Gestion
            "management": {
                "flock_size": entities.flock_size,
                "feed_type": entities.feed_type,
                "feed_conversion": entities.feed_conversion,
                "water_consumption": entities.water_consumption,
                "vaccination_status": entities.vaccination_status,
                "validated": entities.flock_size is not None or entities.feed_type is not None
            },
            
            # Problème contextuel
            "problem_context": {
                "severity": entities.problem_severity,
                "duration": entities.problem_duration,
                "urgency": entities.intervention_urgency,
                "validated": entities.problem_severity is not None
            }
        }
        
        # Patterns et indices dans les messages pour inférence
        conversation_patterns = self._analyze_conversation_patterns()
        
        # Entités manquantes avec importance
        missing_entities = self.get_missing_entities(include_importance=True)
        
        return {
            "conversation_metadata": {
                "conversation_id": self.conversation_id,
                "user_id": self.user_id,
                "language": self.language,
                "total_exchanges": self.total_exchanges,
                "created_at": self.created_at.isoformat(),
                "last_activity": self.last_activity.isoformat()
            },
            
            "conversation_state": {
                "topic": self.conversation_topic,
                "urgency": self.conversation_urgency,
                "resolution_status": self.problem_resolution_status,
                "pending_clarification": self.pending_clarification,
                "ai_enhanced": self.ai_enhanced
            },
            
            "entities_raw": raw_entities,
            "missing_entities": missing_entities,
            "conversation_patterns": conversation_patterns,
            "recent_messages": recent_messages,
            
            "extraction_metadata": {
                "overall_confidence": entities.confidence_overall,
                "last_ai_update": entities.last_ai_update.isoformat() if entities.last_ai_update else None,
                "extraction_method": entities.extraction_method,
                "data_validated": entities.data_validated,
                "extraction_attempts": entities.extraction_attempts
            },
            
            "context_quality_score": self._calculate_context_quality_score()
        }
    
    def _analyze_conversation_patterns(self) -> Dict[str, Any]:
        """Analyse les patterns dans la conversation pour aider l'inférence"""
        
        if not self.messages:
            return {}
        
        all_text = " ".join([msg.message.lower() for msg in self.messages if msg.role == "user"])
        
        patterns = {
            "breeds_mentioned": [],
            "numbers_mentioned": [],
            "symptoms_mentioned": [],
            "time_indicators": [],
            "urgency_indicators": [],
            "performance_indicators": []
        }
        
        # Rechercher mentions de races (même partielles)
        breed_patterns = [
            r'ross\s*\d*', r'cobb\s*\d*', r'hubbard', r'arbor', 
            r'poulets?\s+de\s+chair', r'broilers?'
        ]
        for pattern in breed_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            patterns["breeds_mentioned"].extend(matches)
        
        # Rechercher nombres (âges, poids, quantités)
        number_matches = re.findall(r'\d+(?:\.\d+)?', all_text)
        patterns["numbers_mentioned"] = [float(n) for n in number_matches[:10]]  # Limiter à 10
        
        # Rechercher indicateurs temporels
        time_indicators = re.findall(r'\d+\s*(?:jours?|semaines?|mois|days?|weeks?|months?)', all_text, re.IGNORECASE)
        patterns["time_indicators"] = time_indicators
        
        # Rechercher indicateurs d'urgence
        urgency_words = ["urgent", "urgence", "critique", "emergency", "problème", "problem", "meurent", "dying"]
        for word in urgency_words:
            if word in all_text:
                patterns["urgency_indicators"].append(word)
        
        # Rechercher indicateurs de performance
        performance_words = ["poids", "weight", "croissance", "growth", "performance", "développement"]
        for word in performance_words:
            if word in all_text:
                patterns["performance_indicators"].append(word)
        
        return patterns
    
    def _calculate_context_quality_score(self) -> float:
        """Calcule un score de qualité du contexte (0.0 à 1.0)"""
        
        entities = self.consolidated_entities
        score_components = []
        
        # Score basé sur les entités critiques présentes
        if entities.breed and entities.breed_confidence > 0.7:
            score_components.append(0.25)
        elif entities.breed:
            score_components.append(0.15)
        
        if entities.age_days and entities.age_confidence > 0.7:
            score_components.append(0.25)
        elif entities.age_days:
            score_components.append(0.15)
        
        if entities.sex and entities.sex_confidence > 0.7:
            score_components.append(0.20)
        elif entities.sex:
            score_components.append(0.10)
        
        # Score basé sur les informations additionnelles
        additional_info_score = 0
        if entities.weight_grams:
            additional_info_score += 0.1
        if entities.symptoms:
            additional_info_score += 0.1
        if entities.flock_size:
            additional_info_score += 0.05
        if entities.temperature:
            additional_info_score += 0.05
        
        score_components.append(min(additional_info_score, 0.30))
        
        return sum(score_components)

    def get_formatted_context(self) -> str:
        """Retourne un résumé texte du contexte conversationnel pour les agents"""
        parts = []
        entities = self.consolidated_entities
        
        if entities.breed:
            confidence_indicator = "✅" if entities.breed_confidence > 0.7 else "⚠️"
            parts.append(f"Race: {entities.breed} {confidence_indicator}")
        else:
            parts.append("Race: inconnue ❌")
        
        if entities.age_days:
            confidence_indicator = "✅" if entities.age_confidence > 0.7 else "⚠️"
            weeks = entities.age_weeks or (entities.age_days / 7)
            parts.append(f"Âge: {entities.age_days} jours ({weeks:.1f} sem) {confidence_indicator}")
        else:
            parts.append("Âge: inconnu ❌")
        
        if entities.sex:
            confidence_indicator = "✅" if entities.sex_confidence > 0.7 else "⚠️"
            parts.append(f"Sexe: {entities.sex} {confidence_indicator}")
        else:
            parts.append("Sexe: inconnu ❌")
        
        # Informations additionnelles importantes
        if entities.weight_grams:
            parts.append(f"Poids: {entities.weight_grams}g")
        
        if entities.symptoms:
            parts.append(f"Symptômes: {', '.join(entities.symptoms)}")
        
        if entities.mortality_rate is not None:
            status = "🚨" if entities.mortality_rate > 5 else "⚠️" if entities.mortality_rate > 2 else "✅"
            parts.append(f"Mortalité: {entities.mortality_rate}% {status}")
        
        if entities.temperature:
            status = "🚨" if entities.temperature < 18 or entities.temperature > 30 else "✅"
            parts.append(f"Température: {entities.temperature}°C {status}")
        
        # Contexte conversationnel
        if self.conversation_urgency:
            urgency_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
            icon = urgency_icons.get(self.conversation_urgency, "🟡")
            parts.append(f"Urgence: {self.conversation_urgency} {icon}")
        
        return " | ".join(parts)

    def get_context_for_rag(self, max_chars: int = 500) -> str:
        """Retourne le contexte optimisé pour le RAG"""
        context_parts = []
        
        # Informations de base validées
        entities = self.consolidated_entities
        if not entities.data_validated:
            entities = entities.validate_and_correct()
        
        if entities.breed:
            context_parts.append(f"Race: {entities.breed}")
        
        if entities.sex:
            context_parts.append(f"Sexe: {entities.sex}")
        
        if entities.age_days:
            context_parts.append(f"Âge: {entities.age_days} jours")
        
        if entities.weight_grams:
            context_parts.append(f"Poids: {entities.weight_grams}g")
        
        # Problèmes identifiés
        if entities.symptoms:
            context_parts.append(f"Symptômes: {', '.join(entities.symptoms)}")
        
        if entities.mortality_rate:
            context_parts.append(f"Mortalité: {entities.mortality_rate}%")
        
        # Environnement
        if entities.temperature:
            context_parts.append(f"Température: {entities.temperature}°C")
        
        if entities.housing_type:
            context_parts.append(f"Logement: {entities.housing_type}")
        
        # Messages récents pertinents
        if self.messages:
            recent_user_messages = [m.message for m in self.messages[-3:] if m.role == "user"]
            if recent_user_messages:
                context_parts.append(f"Questions récentes: {' | '.join(recent_user_messages)}")
        
        # Assembler et limiter
        full_context = ". ".join(context_parts)
        
        if len(full_context) > max_chars:
            # Tronquer intelligemment en gardant les infos les plus importantes
            important_parts = context_parts[:5]  # Race, sexe, âge, poids, symptômes
            full_context = ". ".join(important_parts)
            
            if len(full_context) > max_chars:
                full_context = full_context[:max_chars-3] + "..."
        
        return full_context
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "messages": [m.to_dict() for m in self.messages],
            "consolidated_entities": self.consolidated_entities.to_dict(),
            "language": self.language,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "total_exchanges": self.total_exchanges,
            "conversation_topic": self.conversation_topic,
            "conversation_urgency": self.conversation_urgency,
            "problem_resolution_status": self.problem_resolution_status,
            "ai_enhanced": self.ai_enhanced,
            "last_ai_analysis": self.last_ai_analysis.isoformat() if self.last_ai_analysis else None,
            "needs_clarification": self.needs_clarification,
            "clarification_questions": self.clarification_questions,
            "pending_clarification": self.pending_clarification,
            "last_original_question_id": self.last_original_question_id
        }

class IntelligentConversationMemory:
    """Système de mémoire conversationnelle intelligent avec IA et clarification intégrée"""
    
    def __init__(self, db_path: str = None):
        """Initialise le système de mémoire intelligent"""
        
        # Configuration
        self.db_path = db_path or os.getenv('CONVERSATION_MEMORY_DB_PATH', 'data/conversation_memory.db')
        self.max_messages_in_memory = int(os.getenv('MAX_MESSAGES_IN_MEMORY', '50'))
        self.context_expiry_hours = int(os.getenv('CONTEXT_EXPIRY_HOURS', '24'))
        self.ai_enhancement_enabled = os.getenv('AI_ENHANCEMENT_ENABLED', 'true').lower() == 'true'
        self.ai_enhancement_model = os.getenv('AI_ENHANCEMENT_MODEL', 'gpt-4o-mini')
        self.ai_enhancement_timeout = int(os.getenv('AI_ENHANCEMENT_TIMEOUT', '15'))
        
        # Cache en mémoire pour performance
        self.conversation_cache: Dict[str, IntelligentConversationContext] = {}
        self.cache_max_size = int(os.getenv('CONVERSATION_CACHE_SIZE', '100'))
        self.cache_lock = Lock()
        
        # Statistiques
        self.stats = {
            "total_conversations": 0,
            "total_messages": 0,
            "ai_enhancements": 0,
            "ai_failures": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "original_questions_recovered": 0,  # ✅ NOUVELLE MÉTRIQUE
            "clarification_resolutions": 0     # ✅ NOUVELLE MÉTRIQUE
        }
        
        # Initialiser la base de données
        self._init_database()
        
        logger.info(f"🧠 [IntelligentMemory] Système initialisé")
        logger.info(f"🧠 [IntelligentMemory] DB: {self.db_path}")
        logger.info(f"🧠 [IntelligentMemory] IA enhancing: {'✅' if self.ai_enhancement_enabled else '❌'}")
        logger.info(f"🧠 [IntelligentMemory] Modèle IA: {self.ai_enhancement_model}")
        logger.info(f"🚨 [IntelligentMemory] Système de clarification intégré: ✅")
        logger.info(f"🤖 [IntelligentMemory] Méthodes pour agents GPT ajoutées: ✅")

    def _init_database(self):
        """Initialise la base de données avec schéma amélioré"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Table des conversations avec métadonnées étendues
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    language TEXT DEFAULT 'fr',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_exchanges INTEGER DEFAULT 0,
                    
                    -- Entités consolidées (JSON)
                    consolidated_entities TEXT,
                    
                    -- État conversationnel
                    conversation_topic TEXT,
                    conversation_urgency TEXT,
                    problem_resolution_status TEXT,
                    
                    -- Métadonnées IA
                    ai_enhanced BOOLEAN DEFAULT FALSE,
                    last_ai_analysis TIMESTAMP,
                    needs_clarification BOOLEAN DEFAULT FALSE,
                    clarification_questions TEXT,
                    
                    -- ✅ CHAMPS POUR CLARIFICATIONS
                    pending_clarification BOOLEAN DEFAULT FALSE,
                    last_original_question_id TEXT,
                    
                    -- Performance
                    confidence_overall REAL DEFAULT 0.0
                )
            """)
            
            # Table des messages avec extraction d'entités
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    language TEXT DEFAULT 'fr',
                    message_type TEXT DEFAULT 'text',
                    
                    -- Entités extraites (JSON)
                    extracted_entities TEXT,
                    confidence_score REAL DEFAULT 0.0,
                    processing_method TEXT DEFAULT 'basic',
                    
                    -- ✅ CHAMPS POUR CLARIFICATIONS
                    is_original_question BOOLEAN DEFAULT FALSE,
                    is_clarification_response BOOLEAN DEFAULT FALSE,
                    original_question_id TEXT,
                    
                    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                )
            """)
            
            # Index pour performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_user_activity ON conversations (user_id, last_activity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv_time ON conversation_messages (conversation_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_urgency ON conversations (conversation_urgency, last_activity)")
            # ✅ INDEX POUR CLARIFICATIONS
            conn.execute("CREATE INDEX IF NOT EXISTS idx_original_questions ON conversation_messages (conversation_id, is_original_question)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clarification_responses ON conversation_messages (original_question_id, is_clarification_response)")
            
        logger.info(f"✅ [IntelligentMemory] Base de données initialisée avec support clarifications")

    @contextmanager
    def _get_db_connection(self):
        """Context manager pour les connexions DB avec retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                yield conn
                break
            except sqlite3.OperationalError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"⚠️ [DB] Retry connexion {attempt + 1}/{max_retries}: {e}")
                time.sleep(0.5 * (attempt + 1))
            finally:
                try:
                    conn.close()
                except:
                    pass

    async def extract_entities_ai_enhanced(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """Extraction d'entités avec IA ou fallback basique"""
        
        # Tentative IA si disponible
        if self.ai_enhancement_enabled and OPENAI_AVAILABLE and openai:
            try:
                entities = await self._extract_entities_openai(message, language, conversation_context)
                if entities and entities.confidence_overall > 0.3:
                    self.stats["ai_enhancements"] += 1
                    return entities.validate_and_correct()
            except Exception as e:
                self.stats["ai_failures"] += 1
                logger.warning(f"⚠️ [AI Extraction] Échec IA: {e}")
        
        # Fallback: Extraction basique
        logger.info("🔄 [Fallback] Utilisation extraction basique")
        entities = await self._extract_entities_basic(message, language)
        entities.extraction_method = "fallback"
        
        return entities.validate_and_correct()

    async def _extract_entities_openai(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """Extraction d'entités par OpenAI"""
        
        # Contexte pour l'IA
        context_info = ""
        if conversation_context and conversation_context.consolidated_entities:
            existing_entities = conversation_context.consolidated_entities.to_dict()
            if existing_entities:
                context_info = f"\n\nEntités déjà connues:\n{json.dumps(existing_entities, ensure_ascii=False, indent=2)}"
        
        extraction_prompt = f"""Tu es un expert en extraction d'informations vétérinaires pour l'aviculture. Analyse ce message et extrait TOUTES les informations pertinentes.

Message: "{message}"{context_info}

INSTRUCTIONS CRITIQUES:
1. Extrait toutes les informations, même partielles ou implicites
2. Utilise le contexte existant pour éviter les doublons
3. Assigne des scores de confiance (0.0 à 1.0) basés sur la précision
4. Inférer des informations logiques (ex: si "mes poulets Ross 308", alors breed_type="specific")
5. Convertir automatiquement les unités (semaines -> jours, kg -> grammes)
6. ✅ IMPORTANT: Détecte le SEXE avec variations multilingues

SEXES SUPPORTÉS:
- FR: mâles, mâle, femelles, femelle, mixte, troupeau mixte, coqs, poules
- EN: males, male, females, female, mixed, mixed flock, roosters, hens  
- ES: machos, macho, hembras, hembra, mixto, lote mixto, gallos, gallinas

Réponds UNIQUEMENT avec ce JSON exact:
```json
{{
  "breed": "race_détectée_ou_null",
  "breed_confidence": 0.0_à_1.0,
  "breed_type": "specific/generic/null",
  
  "sex": "sexe_détecté_ou_null",
  "sex_confidence": 0.0_à_1.0,
  
  "age_days": nombre_jours_ou_null,
  "age_weeks": nombre_semaines_ou_null,
  "age_confidence": 0.0_à_1.0,
  
  "weight_grams": poids_grammes_ou_null,
  "weight_confidence": 0.0_à_1.0,
  "expected_weight_range": [min_grammes, max_grammes] ou null,
  "growth_rate": "normal/slow/fast/null",
  
  "mortality_rate": pourcentage_ou_null,
  "mortality_confidence": 0.0_à_1.0,
  "symptoms": ["symptôme1", "symptôme2"] ou [],
  "health_status": "good/concerning/critical/null",
  
  "temperature": celsius_ou_null,
  "humidity": pourcentage_ou_null,
  "housing_type": "type_ou_null",
  
  "feed_type": "type_ou_null",
  "flock_size": nombre_ou_null,
  
  "problem_severity": "low/medium/high/critical/null",
  "intervention_urgency": "none/monitor/act/urgent/null",
  
  "extraction_method": "openai",
  "confidence_overall": 0.0_à_1.0
}}
```

EXEMPLES:
- "Ross 308 mâles" → breed="Ross 308", sex="mâles", breed_confidence=0.95, sex_confidence=0.95
- "Ross 308 male" → breed="Ross 308", sex="mâles", breed_confidence=0.95, sex_confidence=0.95
- "3 semaines" → age_weeks=3, age_days=21, age_confidence=0.9
"""

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception("Clé API OpenAI manquante")
        
        # Créer le client OpenAI
        client = openai.AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model=self.ai_enhancement_model,
            messages=[
                {"role": "system", "content": "Tu es un extracteur d'entités expert en aviculture. Réponds UNIQUEMENT avec du JSON valide."},
                {"role": "user", "content": extraction_prompt}
            ],
            temperature=0.1,
            max_tokens=800,
            timeout=self.ai_enhancement_timeout
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Extraire le JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', answer, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', answer, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise Exception("Pas de JSON trouvé dans la réponse IA")
        
        # Parser et créer les entités
        try:
            data = json.loads(json_str)
            
            entities = IntelligentEntities(
                breed=data.get("breed"),
                breed_confidence=data.get("breed_confidence", 0.0),
                breed_type=data.get("breed_type"),
                
                sex=data.get("sex"),
                sex_confidence=data.get("sex_confidence", 0.0),
                
                age_days=data.get("age_days"),
                age_weeks=data.get("age_weeks"),
                age_confidence=data.get("age_confidence", 0.0),
                age_last_updated=datetime.now(),
                
                weight_grams=data.get("weight_grams"),
                weight_confidence=data.get("weight_confidence", 0.0),
                expected_weight_range=tuple(data["expected_weight_range"]) if data.get("expected_weight_range") else None,
                growth_rate=data.get("growth_rate"),
                
                mortality_rate=data.get("mortality_rate"),
                mortality_confidence=data.get("mortality_confidence", 0.0),
                symptoms=data.get("symptoms", []),
                health_status=data.get("health_status"),
                
                temperature=data.get("temperature"),
                humidity=data.get("humidity"),
                housing_type=data.get("housing_type"),
                
                feed_type=data.get("feed_type"),
                flock_size=data.get("flock_size"),
                
                problem_severity=data.get("problem_severity"),
                intervention_urgency=data.get("intervention_urgency"),
                
                extraction_method="openai",
                last_ai_update=datetime.now(),
                confidence_overall=data.get("confidence_overall", 0.0),
                extraction_success=True
            )
            
            return entities
            
        except json.JSONDecodeError as e:
            raise Exception(f"Erreur parsing JSON IA: {e}")

    async def _extract_entities_basic(self, message: str, language: str) -> IntelligentEntities:
        """Extraction d'entités basique améliorée avec sexe"""
        
        entities = IntelligentEntities(extraction_method="basic")
        message_lower = message.lower()
        
        # Race spécifique
        specific_breeds = [
            r'ross\s*308', r'ross\s*708', r'cobb\s*500', r'cobb\s*700',
            r'hubbard\s*flex', r'arbor\s*acres'
        ]
        
        for pattern in specific_breeds:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                breed_found = match.group(0).strip().replace(' ', ' ').title()
                entities.breed = breed_found
                entities.breed_type = "specific"
                entities.breed_confidence = 0.9
                logger.debug(f"🔍 [Basic] Race spécifique détectée: {breed_found}")
                break
        
        # ✅ EXTRACTION SEXE AMÉLIORÉE
        sex_patterns = {
            "fr": [
                (r'\bmâles?\b', 'mâles'),
                (r'\bmales?\b', 'mâles'),
                (r'\bcoqs?\b', 'mâles'),
                (r'\bfemelles?\b', 'femelles'),
                (r'\bfemales?\b', 'femelles'),
                (r'\bpoules?\b', 'femelles'),
                (r'\bmixte\b', 'mixte'),
                (r'\btroupeau\s+mixte\b', 'mixte')
            ],
            "en": [
                (r'\bmales?\b', 'males'),
                (r'\brooster\b', 'males'),
                (r'\bfemales?\b', 'females'),
                (r'\bhens?\b', 'females'),
                (r'\bmixed?\b', 'mixed'),
                (r'\bmixed\s+flock\b', 'mixed')
            ],
            "es": [
                (r'\bmachos?\b', 'machos'),
                (r'\bgallos?\b', 'machos'),
                (r'\bhembras?\b', 'hembras'),
                (r'\bgallinas?\b', 'hembras'),
                (r'\bmixto\b', 'mixto'),
                (r'\blote\s+mixto\b', 'mixto')
            ]
        }
        
        patterns = sex_patterns.get(language, sex_patterns["fr"])
        
        for pattern, sex_name in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                entities.sex = sex_name
                entities.sex_confidence = 0.8
                logger.debug(f"🔍 [Basic] Sexe détecté: {sex_name}")
                break
        
        # Âge avec validation
        age_patterns = [
            (r'(\d+)\s*jours?', 1, "days"),
            (r'(\d+)\s*semaines?', 7, "weeks"),
            (r'(\d+)\s*days?', 1, "days"),
            (r'(\d+)\s*weeks?', 7, "weeks")
        ]
        
        for pattern, multiplier, unit in age_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                if unit == "weeks":
                    entities.age_weeks = value
                    entities.age_days = value * 7
                else:
                    entities.age_days = value
                    entities.age_weeks = round(value / 7, 1)
                
                # Validation âge réaliste
                if 0 < entities.age_days <= 365:
                    entities.age_confidence = 0.8
                else:
                    entities.age_confidence = 0.3
                
                entities.age_last_updated = datetime.now()
                logger.debug(f"🔍 [Basic] Âge détecté: {entities.age_days}j ({entities.age_weeks}sem)")
                break
        
        # Poids avec validation
        weight_patterns = [
            (r'(\d+(?:\.\d+)?)\s*g\b', 1, "grams"),
            (r'(\d+(?:\.\d+)?)\s*kg', 1000, "kg"),
            (r'pèsent?\s+(\d+(?:\.\d+)?)', 1, "grams"),
            (r'weigh\s+(\d+(?:\.\d+)?)', 1, "grams")
        ]
        
        for pattern, multiplier, unit in weight_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                weight = float(match.group(1)) * multiplier
                
                # Validation et correction automatique
                if weight < 10:  # Probablement en kg
                    weight *= 1000
                elif weight > 10000:  # Trop élevé
                    entities.weight_confidence = 0.3
                else:
                    entities.weight_confidence = 0.8
                
                entities.weight_grams = weight
                logger.debug(f"🔍 [Basic] Poids détecté: {weight}g")
                break
        
        # Calculer confiance globale
        confidence_scores = [
            entities.breed_confidence,
            entities.sex_confidence,
            entities.age_confidence,
            entities.weight_confidence
        ]
        
        non_zero_scores = [s for s in confidence_scores if s > 0]
        entities.confidence_overall = sum(non_zero_scores) / len(non_zero_scores) if non_zero_scores else 0.0
        
        entities.extraction_success = entities.confidence_overall > 0.1
        
        return entities

    # ✅ NOUVELLE SECTION - SYSTÈME DE CLARIFICATION INTÉGRÉ

    def build_enriched_question_from_clarification(
        self,
        original_question: str,
        clarification_response: str,
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> str:
        """
        🎯 FONCTION CRITIQUE - Enrichit la question originale avec la clarification
        
        Exemple:
        - Original: "Quel est le poids d'un poulet de 12 jours ?"
        - Clarification: "Ross 308 mâles"
        - Enrichi: "Quel est le poids d'un poulet Ross 308 mâle de 12 jours ?"
        """
        
        # Analyser la clarification pour extraire les entités
        clarification_lower = clarification_response.lower().strip()
        
        # Détection race
        breed_info = self._extract_breed_from_clarification(clarification_lower)
        sex_info = self._extract_sex_from_clarification(clarification_lower)
        
        # Construire l'enrichissement
        enrichments = []
        
        if breed_info:
            enrichments.append(breed_info)
        
        if sex_info:
            enrichments.append(sex_info)
        
        # Intégrer dans la question originale
        if enrichments:
            enriched_question = self._integrate_enrichments_into_question(
                original_question, 
                enrichments
            )
            
            logger.info(f"✅ [Clarification] Question enrichie réussie")
            logger.info(f"  📝 Original: {original_question}")
            logger.info(f"  🔁 Enrichi: {enriched_question}")
            
            return enriched_question
        else:
            # Fallback: concaténation simple
            fallback_question = f"{original_question} Contexte: {clarification_response}"
            logger.warning(f"⚠️ [Clarification] Fallback utilisé: {fallback_question}")
            return fallback_question
    
    def _extract_breed_from_clarification(self, clarification: str) -> Optional[str]:
        """Extrait la race de la réponse de clarification"""
        
        breed_patterns = [
            r'ross\s*308',
            r'ross\s*708', 
            r'cobb\s*500',
            r'cobb\s*700',
            r'hubbard\s*flex',
            r'arbor\s*acres'
        ]
        
        for pattern in breed_patterns:
            match = re.search(pattern, clarification, re.IGNORECASE)
            if match:
                breed = match.group(0).strip().replace(' ', ' ').title()
                logger.debug(f"🔍 [Clarification] Race détectée: {breed}")
                return breed
        
        # Patterns génériques
        generic_patterns = [
            r'poulets?\s+de\s+chair',
            r'broilers?',
            r'poulets?'
        ]
        
        for pattern in generic_patterns:
            if re.search(pattern, clarification, re.IGNORECASE):
                logger.debug(f"🔍 [Clarification] Race générique détectée")
                return "poulets de chair"
        
        return None
    
    def _extract_sex_from_clarification(self, clarification: str) -> Optional[str]:
        """Extrait le sexe de la réponse de clarification"""
        
        sex_patterns = [
            (r'\bmâles?\b', 'mâles'),
            (r'\bmales?\b', 'mâles'),
            (r'\bcoqs?\b', 'mâles'),
            (r'\bfemelles?\b', 'femelles'),
            (r'\bfemales?\b', 'femelles'),
            (r'\bpoules?\b', 'femelles'),
            (r'\bmixte\b', 'mixte'),
            (r'\btroupeau\s+mixte\b', 'mixte')
        ]
        
        for pattern, sex_name in sex_patterns:
            if re.search(pattern, clarification, re.IGNORECASE):
                logger.debug(f"🔍 [Clarification] Sexe détecté: {sex_name}")
                return sex_name
        
        return None
    
    def _integrate_enrichments_into_question(
        self, 
        original_question: str, 
        enrichments: list
    ) -> str:
        """Intègre intelligemment les enrichissements dans la question"""
        
        # Patterns de questions communes où insérer les enrichissements
        question_patterns = [
            # "Quel est le poids d'un poulet de X jours ?"
            (r'(quel\s+est\s+le\s+poids\s+d.un\s+)poulet(\s+de\s+\d+\s+jours?)',
             r'\1{} \2'),
            
            # "Mes poulets de X jours pèsent Y"
            (r'(mes\s+)poulets?(\s+de\s+\d+\s+jours?)',
             r'\1{} \2'),
            
            # "Comment nourrir des poulets de X semaines ?"
            (r'(comment\s+\w+\s+des\s+)poulets?(\s+de\s+\d+\s+semaines?)',
             r'\1{} \2'),
            
            # Pattern générique "poulet" → "poulet [race] [sexe]"
            (r'\bpoulets?\b',
             '{}')
        ]
        
        enrichment_text = ' '.join(enrichments)
        
        for pattern, replacement in question_patterns:
            if re.search(pattern, original_question, re.IGNORECASE):
                enriched = re.sub(
                    pattern, 
                    replacement.format(enrichment_text),
                    original_question, 
                    flags=re.IGNORECASE
                )
                
                # Nettoyer les espaces multiples
                enriched = re.sub(r'\s+', ' ', enriched).strip()
                
                return enriched
        
        # Fallback: ajout en contexte
        return f"{original_question} (Contexte: {enrichment_text})"
    
    def detect_clarification_state(
        self, 
        conversation_context: IntelligentConversationContext
    ) -> Tuple[bool, Optional[str]]:
        """
        🔍 Détecte si on est en attente de clarification
        
        Returns:
            (is_awaiting_clarification, original_question_text)
        """
        
        # Vérifier l'état dans le contexte
        if conversation_context.pending_clarification:
            original_question_msg = conversation_context.find_original_question()
            
            if original_question_msg:
                return True, original_question_msg.message
        
        # Fallback: analyser les derniers messages
        if len(conversation_context.messages) >= 2:
            last_assistant_msg = None
            
            # Chercher le dernier message assistant
            for msg in reversed(conversation_context.messages):
                if msg.role == "assistant":
                    last_assistant_msg = msg
                    break
            
            if last_assistant_msg:
                # Mots-clés indiquant une demande de clarification
                clarification_keywords = [
                    "j'ai besoin de", "pouvez-vous préciser", "quelle est la race",
                    "quel est le sexe", "de quelle race", "mâles ou femelles"
                ]
                
                msg_lower = last_assistant_msg.message.lower()
                
                if any(keyword in msg_lower for keyword in clarification_keywords):
                    # Chercher la question utilisateur précédente
                    original_question = conversation_context.get_last_user_question()
                    
                    if original_question:
                        return True, original_question.message
        
        return False, None

    async def process_enhanced_question_with_clarification(
        self,
        request_text: str,
        conversation_id: str,
        user_id: str,
        language: str = "fr"
    ) -> Tuple[str, bool]:
        """
        🚀 FONCTION PRINCIPALE - Traite les questions avec gestion clarification
        
        Returns:
            (processed_question, was_clarification_resolved)
        """
        
        try:
            # 1. Récupérer le contexte conversationnel
            conversation_context = self.get_conversation_context(conversation_id)
            
            if not conversation_context:
                # Nouvelle conversation
                logger.info(f"🆕 [Clarification] Nouvelle conversation: {conversation_id}")
                return request_text, False
            
            # 2. Détecter si on est en attente de clarification
            is_awaiting, original_question = self.detect_clarification_state(
                conversation_context
            )
            
            if is_awaiting and original_question:
                logger.info(f"🎯 [Clarification] État détecté - traitement clarification")
                
                # 3. Enrichir la question originale avec la clarification
                enriched_question = self.build_enriched_question_from_clarification(
                    original_question=original_question,
                    clarification_response=request_text,
                    conversation_context=conversation_context
                )
                
                # 4. Reset l'état de clarification pour éviter les boucles
                conversation_context.pending_clarification = False
                conversation_context.last_original_question_id = None
                
                # 5. Marquer ce message comme réponse de clarification
                self.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=request_text,
                    role="user",
                    language=language,
                    message_type="clarification_response"
                )
                
                # 6. Mettre à jour les statistiques
                self.stats["clarification_resolutions"] += 1
                
                logger.info(f"✅ [Clarification] Question enrichie avec succès")
                
                return enriched_question, True
            
            else:
                # 6. Question normale - pas de clarification en cours
                logger.info(f"💬 [Clarification] Question normale - pas de clarification")
                return request_text, False
        
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur traitement: {e}")
            # En cas d'erreur, retourner la question originale
            return request_text, False

    def check_if_clarification_needed(
        self,
        question: str,
        rag_response: Any,
        context: Optional[IntelligentConversationContext],
        language: str = "fr"
    ) -> Tuple[bool, List[str]]:
        """Détermine si une clarification est nécessaire"""
        
        if not context:
            return False, []
        
        entities = context.consolidated_entities
        missing_info = entities.get_critical_missing_info()
        
        clarification_questions = []
        
        # Messages de clarification par langue
        clarification_messages = {
            "fr": {
                "breed": "De quelle race de poulets s'agit-il ? (ex: Ross 308, Cobb 500)",
                "sex": "S'agit-il de mâles, femelles, ou d'un troupeau mixte ?",
                "age": "Quel est l'âge de vos poulets ?"
            },
            "en": {
                "breed": "What breed of chickens are we talking about? (e.g., Ross 308, Cobb 500)",
                "sex": "Are these males, females, or a mixed flock?",
                "age": "How old are your chickens?"
            },
            "es": {
                "breed": "¿De qué raza de pollos estamos hablando? (ej: Ross 308, Cobb 500)",
                "sex": "¿Son machos, hembras, o un lote mixto?",
                "age": "¿Qué edad tienen sus pollos?"
            }
        }
        
        messages = clarification_messages.get(language, clarification_messages["fr"])
        
        # Race manquante ou générique
        if "breed" in missing_info:
            clarification_questions.append(messages["breed"])
        
        # Sexe manquant
        if "sex" in missing_info:
            clarification_questions.append(messages["sex"])
        
        # Âge manquant
        if "age" in missing_info:
            clarification_questions.append(messages["age"])
        
        # Au maximum 2 questions de clarification
        needs_clarification = len(clarification_questions) > 0 and len(clarification_questions) <= 2
        
        return needs_clarification, clarification_questions[:2]

    def generate_clarification_request(
        self, 
        clarification_questions: List[str], 
        language: str = "fr"
    ) -> str:
        """Génère une demande de clarification naturelle"""
        
        if not clarification_questions:
            fallback_messages = {
                "fr": "Pouvez-vous me donner plus de détails ?",
                "en": "Can you give me more details?",
                "es": "¿Puede darme más detalles?"
            }
            return fallback_messages.get(language, fallback_messages["fr"])
        
        intro_messages = {
            "fr": "Pour vous donner une réponse plus précise, j'ai besoin de quelques informations supplémentaires :",
            "en": "To give you a more accurate answer, I need some additional information:",
            "es": "Para darle una respuesta más precisa, necesito información adicional:"
        }
        
        intro = intro_messages.get(language, intro_messages["fr"])
        questions_text = "\n".join([f"• {q}" for q in clarification_questions])
        
        return f"{intro}\n\n{questions_text}"

    # ✅ MÉTHODE CRITIQUE - MARQUAGE QUESTION ORIGINALE
    def mark_question_for_clarification(
        self, 
        conversation_id: str, 
        user_id: str, 
        original_question: str, 
        language: str = "fr"
    ) -> str:
        """
        🚨 FONCTION CRITIQUE - Marque une question pour clarification future
        """
        
        # Créer un marqueur spécial dans la conversation
        marker_message = f"ORIGINAL_QUESTION_FOR_CLARIFICATION: {original_question}"
        
        message_id = f"{conversation_id}_original_{int(time.time())}"
        
        # Créer le message marqueur
        marker_msg = ConversationMessage(
            id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            role="system",
            message=marker_message,
            timestamp=datetime.now(),
            language=language,
            message_type="original_question_marker",
            is_original_question=True
        )
        
        # Récupérer ou créer le contexte
        context = self.get_conversation_context(conversation_id)
        if not context:
            context = IntelligentConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                language=language
            )
        
        # Ajouter le marqueur
        context.add_message(marker_msg)
        context.pending_clarification = True
        context.last_original_question_id = message_id
        
        # Sauvegarder
        self._save_conversation_to_db(context)
        self._save_message_to_db(marker_msg)
        
        # Mettre en cache
        with self.cache_lock:
            self.conversation_cache[conversation_id] = context
        
        logger.info(f"🎯 [Memory] Question originale marquée: {original_question[:50]}...")
        
        return message_id

    def add_message_to_conversation(
        self,
        conversation_id: str,
        user_id: str,
        message: str,
        role: str = "user",
        language: str = "fr",
        message_type: str = "text"
    ) -> IntelligentConversationContext:
        """Ajoute un message avec extraction d'entités intelligente"""
        
        try:
            # Récupérer ou créer le contexte
            context = self.get_conversation_context(conversation_id)
            if not context:
                context = IntelligentConversationContext(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    language=language
                )
            
            # Extraire les entités de manière asynchrone
            try:
                loop = asyncio.get_event_loop()
                extracted_entities = loop.run_until_complete(
                    self.extract_entities_ai_enhanced(message, language, context)
                )
            except RuntimeError:
                # Si pas de loop actif, créer un nouveau
                extracted_entities = asyncio.run(
                    self.extract_entities_ai_enhanced(message, language, context)
                )
            
            # ✅ DÉTECTION AUTOMATIQUE DES CLARIFICATIONS
            is_clarification_response = False
            original_question_id = None
            
            # Si c'est un message court avec breed/sex ET qu'on a une clarification en attente
            if (role == "user" and context.pending_clarification and 
                len(message.split()) <= 5 and 
                (extracted_entities.breed or extracted_entities.sex)):
                
                is_clarification_response = True
                original_question_id = context.last_original_question_id
                logger.info(f"🎯 [Memory] Clarification détectée: {message} → {original_question_id}")
                self.stats["clarification_resolutions"] += 1
            
            # Créer le message
            message_obj = ConversationMessage(
                id=f"{conversation_id}_{len(context.messages)}_{int(time.time())}",
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                message=message,
                timestamp=datetime.now(),
                language=language,
                message_type=message_type,
                extracted_entities=extracted_entities,
                confidence_score=extracted_entities.confidence_overall if extracted_entities else 0.0,
                processing_method="ai_enhanced" if self.ai_enhancement_enabled else "basic",
                is_clarification_response=is_clarification_response,
                original_question_id=original_question_id
            )
            
            # Ajouter au contexte
            context.add_message(message_obj)
            
            # Sauvegarder
            self._save_conversation_to_db(context)
            self._save_message_to_db(message_obj)
            
            # Mettre en cache
            with self.cache_lock:
                self.conversation_cache[conversation_id] = context
                self._manage_cache_size()
            
            self.stats["total_messages"] += 1
            
            logger.info(f"💬 [Memory] Message ajouté: {conversation_id} ({len(context.messages)} msgs)")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ [Memory] Erreur ajout message: {e}")
            
            # Créer un contexte minimal en fallback
            minimal_context = IntelligentConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                language=language
            )
            
            return minimal_context

    def get_conversation_context(self, conversation_id: str) -> Optional[IntelligentConversationContext]:
        """Récupère le contexte conversationnel avec cache"""
        
        # Vérifier le cache d'abord
        with self.cache_lock:
            if conversation_id in self.conversation_cache:
                context = self.conversation_cache[conversation_id]
                self.stats["cache_hits"] += 1
                return context
        
        self.stats["cache_misses"] += 1
        
        # Charger depuis la DB
        try:
            context = self._load_context_from_db(conversation_id)
            if context:
                # Mettre en cache
                with self.cache_lock:
                    self.conversation_cache[conversation_id] = context
                    self._manage_cache_size()
                return context
        except Exception as e:
            logger.error(f"❌ [Memory] Erreur chargement contexte: {e}")
        
        return None

    def _load_context_from_db(self, conversation_id: str) -> Optional[IntelligentConversationContext]:
        """Charge un contexte depuis la base de données"""
        
        with self._get_db_connection() as conn:
            # Récupérer la conversation
            conv_row = conn.execute(
                "SELECT * FROM conversations WHERE conversation_id = ?",
                (conversation_id,)
            ).fetchone()
            
            if not conv_row:
                return None
            
            # Récupérer les messages
            message_rows = conn.execute(
                """SELECT * FROM conversation_messages 
                   WHERE conversation_id = ? 
                   ORDER BY timestamp ASC 
                   LIMIT ?""",
                (conversation_id, self.max_messages_in_memory)
            ).fetchall()
            
            # Reconstruire le contexte
            context = IntelligentConversationContext(
                conversation_id=conv_row["conversation_id"],
                user_id=conv_row["user_id"],
                language=conv_row["language"] or "fr",
                created_at=datetime.fromisoformat(conv_row["created_at"]),
                last_activity=datetime.fromisoformat(conv_row["last_activity"]),
                total_exchanges=conv_row["total_exchanges"] or 0,
                conversation_topic=conv_row["conversation_topic"],
                conversation_urgency=conv_row["conversation_urgency"],
                problem_resolution_status=conv_row["problem_resolution_status"],
                ai_enhanced=bool(conv_row["ai_enhanced"]),
                last_ai_analysis=datetime.fromisoformat(conv_row["last_ai_analysis"]) if conv_row["last_ai_analysis"] else None,
                needs_clarification=bool(conv_row["needs_clarification"]),
                clarification_questions=json.loads(conv_row["clarification_questions"]) if conv_row["clarification_questions"] else [],
                pending_clarification=bool(conv_row.get("pending_clarification", False)),
                last_original_question_id=conv_row.get("last_original_question_id")
            )
            
            # Charger les entités consolidées
            if conv_row["consolidated_entities"]:
                entities_data = json.loads(conv_row["consolidated_entities"])
                context.consolidated_entities = self._entities_from_dict(entities_data)
            
            # Charger les messages
            for msg_row in message_rows:
                entities = None
                if msg_row["extracted_entities"]:
                    entities_data = json.loads(msg_row["extracted_entities"])
                    entities = self._entities_from_dict(entities_data)
                
                message_obj = ConversationMessage(
                    id=msg_row["id"],
                    conversation_id=msg_row["conversation_id"],
                    user_id=msg_row["user_id"],
                    role=msg_row["role"],
                    message=msg_row["message"],
                    timestamp=datetime.fromisoformat(msg_row["timestamp"]),
                    language=msg_row["language"] or "fr",
                    message_type=msg_row["message_type"] or "text",
                    extracted_entities=entities,
                    confidence_score=msg_row["confidence_score"] or 0.0,
                    processing_method=msg_row["processing_method"] or "basic",
                    is_original_question=bool(msg_row.get("is_original_question", False)),
                    is_clarification_response=bool(msg_row.get("is_clarification_response", False)),
                    original_question_id=msg_row.get("original_question_id")
                )
                
                context.messages.append(message_obj)
            
            return context

    def _entities_from_dict(self, data: Dict[str, Any]) -> IntelligentEntities:
        """Reconstruit les entités depuis un dictionnaire"""
        
        # Convertir les dates
        for date_field in ["age_last_updated", "last_ai_update"]:
            if data.get(date_field):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except:
                    data[date_field] = None
        
        # Convertir les tuples
        if data.get("expected_weight_range") and isinstance(data["expected_weight_range"], list):
            data["expected_weight_range"] = tuple(data["expected_weight_range"])
        
        # Assurer les listes
        for list_field in ["symptoms", "previous_treatments"]:
            if not isinstance(data.get(list_field), list):
                data[list_field] = []
        
        return IntelligentEntities(**{k: v for k, v in data.items() if k in IntelligentEntities.__dataclass_fields__})

    def _save_conversation_to_db(self, context: IntelligentConversationContext):
        """Sauvegarde un contexte en base de données"""
        
        with self._get_db_connection() as conn:
            # Préparer les données
            consolidated_entities_json = json.dumps(context.consolidated_entities.to_dict(), ensure_ascii=False)
            clarification_questions_json = json.dumps(context.clarification_questions, ensure_ascii=False)
            
            # Upsert de la conversation
            conn.execute("""
                INSERT OR REPLACE INTO conversations (
                    conversation_id, user_id, language, created_at, last_activity,
                    total_exchanges, consolidated_entities, conversation_topic,
                    conversation_urgency, problem_resolution_status, ai_enhanced,
                    last_ai_analysis, needs_clarification, clarification_questions,
                    pending_clarification, last_original_question_id, confidence_overall
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                context.conversation_id,
                context.user_id,
                context.language,
                context.created_at.isoformat(),
                context.last_activity.isoformat(),
                context.total_exchanges,
                consolidated_entities_json,
                context.conversation_topic,
                context.conversation_urgency,
                context.problem_resolution_status,
                context.ai_enhanced,
                context.last_ai_analysis.isoformat() if context.last_ai_analysis else None,
                context.needs_clarification,
                clarification_questions_json,
                context.pending_clarification,
                context.last_original_question_id,
                context.consolidated_entities.confidence_overall
            ))
            
            conn.commit()

    def _save_message_to_db(self, message: ConversationMessage):
        """Sauvegarde un message en base de données"""
        
        with self._get_db_connection() as conn:
            # Préparer les données
            entities_json = json.dumps(message.extracted_entities.to_dict(), ensure_ascii=False) if message.extracted_entities else None
            
            # Insert du message
            conn.execute("""
                INSERT OR REPLACE INTO conversation_messages (
                    id, conversation_id, user_id, role, message, timestamp,
                    language, message_type, extracted_entities, confidence_score,
                    processing_method, is_original_question, is_clarification_response,
                    original_question_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.conversation_id,
                message.user_id,
                message.role,
                message.message,
                message.timestamp.isoformat(),
                message.language,
                message.message_type,
                entities_json,
                message.confidence_score,
                message.processing_method,
                message.is_original_question,
                message.is_clarification_response,
                message.original_question_id
            ))
            
            conn.commit()

    def _manage_cache_size(self):
        """Gère la taille du cache en mémoire"""
        
        if len(self.conversation_cache) > self.cache_max_size:
            # Supprimer les conversations les moins récemment utilisées
            sorted_conversations = sorted(
                self.conversation_cache.items(),
                key=lambda x: x[1].last_activity
            )
            
            # Garder seulement les plus récentes
            conversations_to_keep = dict(sorted_conversations[-self.cache_max_size//2:])
            self.conversation_cache = conversations_to_keep
            
            logger.info(f"🧹 [Memory] Cache nettoyé: {len(self.conversation_cache)} conversations gardées")

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du système"""
        
        return {
            "system_stats": self.stats.copy(),
            "cache_stats": {
                "cache_size": len(self.conversation_cache),
                "cache_max_size": self.cache_max_size,
                "hit_rate": self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"]) if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
            },
            "clarification_stats": {
                "questions_recovered": self.stats["original_questions_recovered"],
                "clarifications_resolved": self.stats["clarification_resolutions"]
            }
        }

    def cleanup_old_conversations(self, days_old: int = 30):
        """Nettoie les conversations anciennes"""
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with self._get_db_connection() as conn:
            # Supprimer les messages anciens
            result_messages = conn.execute(
                "DELETE FROM conversation_messages WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            
            # Supprimer les conversations anciennes
            result_conversations = conn.execute(
                "DELETE FROM conversations WHERE last_activity < ?",
                (cutoff_date.isoformat(),)
            )
            
            conn.commit()
            
            logger.info(f"🧹 [Cleanup] {result_messages.rowcount} messages et {result_conversations.rowcount} conversations supprimés")

# ===============================
# ✅ EXEMPLE D'UTILISATION DANS FASTAPI AVEC AGENTS
# ===============================

"""
Exemple d'intégration dans votre endpoint FastAPI avec agents GPT:

from app.core.conversation_memory_integrated import IntelligentConversationMemory
from app.api.v1.agent_contextualizer import agent_contextualizer
from app.api.v1.agent_rag_enhancer import agent_rag_enhancer

# Initialiser le système de mémoire
conversation_memory = IntelligentConversationMemory()

@app.post("/api/v1/expert/ask")
async def ask_expert_enhanced_with_agents(request: QuestionRequest):
    try:
        logger.info(f"🚀 [ASK] Question reçue: {request.text[:100]}...")
        
        # ✅ ÉTAPE 1: Traitement clarification avec votre approche
        processed_question, was_clarification = await conversation_memory.process_enhanced_question_with_clarification(
            request_text=request.text,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            language=request.language
        )
        
        # Si c'était une clarification, utiliser la question enrichie
        if was_clarification:
            logger.info(f"🔁 [ASK] Reprocessing enriched question: {processed_question}")
            request.text = processed_question
        
        # ✅ ÉTAPE 2: Ajouter le message à la conversation (si pas déjà fait)
        if not was_clarification:
            conversation_memory.add_message_to_conversation(
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                message=request.text,
                role="user",
                language=request.language
            )
        
        # ✅ ÉTAPE 3: Récupérer le contexte enrichi pour agents
        context = conversation_memory.get_conversation_context(request.conversation_id)
        if context:
            # 🔥 NOUVELLES MÉTHODES AMÉLIORÉES - ATTENTION AUX TYPES
            missing_entities_with_importance = context.get_missing_entities(include_importance=True)  # Dict
            missing_entities_list = context.get_missing_entities(include_importance=False)  # List
            raw_context_summary = context.get_raw_context_summary()  # Contexte brut complet
            formatted_context = context.get_formatted_context()
            rag_context = context.get_context_for_rag()
        else:
            missing_entities_with_importance, missing_entities_list = {}, []
            raw_context_summary, formatted_context, rag_context = {}, "", ""
        
        # ✅ ÉTAPE 4: Agent Contextualizer (pré-RAG) avec contexte enrichi
        contextualization_result = await agent_contextualizer.enrich_question(
            question=processed_question,
            raw_context=raw_context_summary,  # 🔥 CONTEXTE BRUT COMPLET
            missing_entities_with_importance=missing_entities_with_importance,  # 🔥 Dict avec importance
            missing_entities_list=missing_entities_list,  # 🔥 Liste simple (compatibilité)
            conversation_context=formatted_context,
            language=request.language
        )
        question_for_rag = contextualization_result["enriched_question"]
        
        # ✅ ÉTAPE 5: Appel au système RAG avec contexte enrichi
        response = await rag_system.query(
            question=question_for_rag,
            context=rag_context,
            language=request.language
        )
        
        # ✅ ÉTAPE 6: Agent RAG Enhancer (post-RAG) avec contexte enrichi
        enhancement_result = await agent_rag_enhancer.enhance_rag_answer(
            rag_answer=response.answer,
            raw_context=raw_context_summary,  # 🔥 CONTEXTE BRUT COMPLET
            missing_entities_with_importance=missing_entities_with_importance,  # 🔥 Dict avec importance
            missing_entities_list=missing_entities_list,  # 🔥 Liste simple (compatibilité)
            conversation_context=formatted_context,
            original_question=request.text,
            language=request.language
        )
        final_answer = enhancement_result["enhanced_answer"]
        optional_clarifications = enhancement_result.get("optional_clarifications", [])
        
        # ✅ ÉTAPE 7: Vérifier si nouvelle clarification nécessaire
        needs_clarification, clarification_questions = conversation_memory.check_if_clarification_needed(
            question=processed_question,
            rag_response=response,
            context=context,
            language=request.language
        )
        
        if needs_clarification and not was_clarification:
            # Marquer pour clarification future
            conversation_memory.mark_question_for_clarification(
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                original_question=request.text,
                language=request.language
            )
            
            # Générer la demande de clarification
            clarification_response = conversation_memory.generate_clarification_request(
                clarification_questions, 
                request.language
            )
            
            # Ajouter la réponse de clarification
            conversation_memory.add_message_to_conversation(
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                message=clarification_response,
                role="assistant",
                language=request.language,
                message_type="clarification_request"
            )
            
            return QuestionResponse(
                answer=clarification_response,
                confidence=0.5,
                context_used=rag_context,
                needs_clarification=True,
                conversation_id=request.conversation_id,
                contextualization_info=contextualization_result,
                enhancement_info=enhancement_result,
                context_quality_score=raw_context_summary.get("context_quality_score", 0.0)  # 🔥 NOUVEAU
            )
        
        # ✅ ÉTAPE 8: Réponse normale avec métadonnées agents enrichies
        conversation_memory.add_message_to_conversation(
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            message=final_answer,
            role="assistant",
            language=request.language
        )
        
        return QuestionResponse(
            answer=final_answer,
            confidence=response.confidence,
            context_used=rag_context,
            needs_clarification=False,
            conversation_id=request.conversation_id,
            sources=response.sources,
            optional_clarifications=optional_clarifications,
            contextualization_info=contextualization_result,
            enhancement_info=enhancement_result,
            context_quality_score=raw_context_summary.get("context_quality_score", 0.0),  # 🔥 NOUVEAU
            missing_entities_analysis=missing_entities_with_importance  # 🔥 NOUVEAU - pour debugging/analytics
        )
        
    except Exception as e:
        logger.error(f"❌ [ASK] Erreur: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""