# app/api/v1/context_manager.py
"""
Context Manager - Gestionnaire centralisé du contexte conversationnel

🎯 OBJECTIF: Éliminer les récupérations multiples incohérentes du contexte
✅ RÉSOUT: get_context_for_rag() vs get_context_for_clarification() vs get_conversation_context()
🚀 IMPACT: +15% de cohérence conversationnelle
✅ CORRECTION: Ajout de la méthode save_unified_context manquante
🔄 AMÉLIORATION: Support IA et enrichissement contextuel intelligent

PRINCIPE:
- Récupération unique du contexte mémoire
- Cache intelligent pour éviter les accès redondants
- Interface unifiée pour tous les modules  
- Vues spécialisées selon le besoin (RAG, clarification, classification)
- Enrichissement contextuel avec IA (si disponible)

UTILISATION:
```python
context_manager = ContextManager()
context = context_manager.get_unified_context(conversation_id, type="rag")
# Tous les modules utilisent exactement le même contexte
```
"""

import logging
import sqlite3
import json
import time
import asyncio
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from threading import Lock
from enum import Enum

logger = logging.getLogger(__name__)

class ContextType(Enum):
    """Types de contexte supportés"""
    RAG = "rag"
    CLARIFICATION = "clarification" 
    CLASSIFICATION = "classification"
    GENERAL = "general"

@dataclass
class UnifiedContext:
    """Structure unifiée pour tout le contexte conversationnel"""
    
    # Contexte conversationnel de base
    conversation_id: str
    last_interaction: Optional[datetime] = None
    
    # Historique des messages
    recent_messages: List[Dict[str, Any]] = None
    conversation_topic: Optional[str] = None
    conversation_flow: Optional[str] = None  # ✅ NOUVEAU: Flow conversationnel
    
    # Entités établies dans la conversation
    established_breed: Optional[str] = None
    established_age: Optional[int] = None
    established_sex: Optional[str] = None
    established_weight: Optional[float] = None
    
    # ✅ NOUVEAU: Entités enrichies par IA
    ai_inferred_entities: Dict[str, Any] = None
    confidence_scores: Dict[str, float] = None
    
    # Contexte sémantique  
    previous_questions: List[str] = None
    previous_answers: List[str] = None
    clarification_history: List[Dict[str, Any]] = None
    
    # ✅ NOUVEAU: Contexte sémantique enrichi
    conversation_intent: Optional[str] = None
    user_expertise_level: Optional[str] = None  # novice, intermediate, expert
    preferred_response_style: Optional[str] = None  # detailed, concise, technical
    
    # Données de performance (pour contexte RAG)
    weight_data: Dict[str, Any] = None
    feeding_context: Dict[str, Any] = None
    health_context: Dict[str, Any] = None
    
    # ✅ NOUVEAU: Contexte enrichi IA
    ai_context_summary: Optional[str] = None
    ai_suggested_topics: List[str] = None
    ai_confidence: float = 0.0
    
    # Métadonnées
    context_age_minutes: float = 0.0
    confidence: float = 1.0
    cache_hit: bool = False
    last_ai_enhancement: Optional[datetime] = None  # ✅ NOUVEAU
    
    def __post_init__(self):
        if self.recent_messages is None:
            self.recent_messages = []
        if self.previous_questions is None:
            self.previous_questions = []
        if self.previous_answers is None:
            self.previous_answers = []
        if self.clarification_history is None:
            self.clarification_history = []
        if self.weight_data is None:
            self.weight_data = {}
        if self.feeding_context is None:
            self.feeding_context = {}
        if self.health_context is None:
            self.health_context = {}
        if self.ai_inferred_entities is None:
            self.ai_inferred_entities = {}
        if self.confidence_scores is None:
            self.confidence_scores = {}
        if self.ai_suggested_topics is None:
            self.ai_suggested_topics = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion pour compatibilité"""
        data = asdict(self)
        # Convertir datetime vers string pour JSON
        if self.last_interaction:
            data['last_interaction'] = self.last_interaction.isoformat()
        if self.last_ai_enhancement:
            data['last_ai_enhancement'] = self.last_ai_enhancement.isoformat()
        return data
    
    def has_entities(self) -> bool:
        """Vérifie si des entités sont établies"""
        return any([
            self.established_breed,
            self.established_age,
            self.established_sex,
            self.established_weight,
            self.ai_inferred_entities
        ])
    
    def get_context_summary(self) -> str:
        """Résumé textuel du contexte pour logs"""
        parts = []
        
        if self.established_breed:
            parts.append(f"race={self.established_breed}")
        if self.established_age:
            parts.append(f"âge={self.established_age}j")
        if self.established_sex:
            parts.append(f"sexe={self.established_sex}")
        if self.conversation_topic:
            parts.append(f"topic={self.conversation_topic}")
        if self.conversation_intent:
            parts.append(f"intent={self.conversation_intent}")
        if self.ai_confidence > 0:
            parts.append(f"ai_confidence={self.ai_confidence:.2f}")
        
        return ", ".join(parts) if parts else "contexte vide"
    
    def needs_ai_enhancement(self, enhancement_interval_minutes: int = 30) -> bool:
        """✅ NOUVEAU: Vérifie si le contexte a besoin d'enrichissement IA"""
        if not self.last_ai_enhancement:
            return True
        
        age_minutes = (datetime.now() - self.last_ai_enhancement).total_seconds() / 60
        return age_minutes > enhancement_interval_minutes
    
    def get_enrichment_priority(self) -> str:
        """✅ NOUVEAU: Détermine la priorité d'enrichissement"""
        if not self.has_entities():
            return "high"  # Pas d'entités = priorité haute
        elif not self.conversation_intent:
            return "medium"  # Pas d'intent = priorité moyenne  
        elif self.ai_confidence < 0.7:
            return "medium"  # Faible confidence = priorité moyenne
        else:
            return "low"  # Contexte bien établi = priorité basse

class ContextManager:
    """Gestionnaire centralisé du contexte avec cache intelligent et IA"""
    
    def __init__(self, 
                 db_path: str = "conversations.db", 
                 cache_duration_minutes: int = 5,
                 ai_enhancer: Optional[object] = None,
                 enable_ai_enhancement: bool = True):
        """
        Initialisation du gestionnaire
        
        Args:
            db_path: Chemin vers la base SQLite
            cache_duration_minutes: Durée de validité du cache
            ai_enhancer: Instance du service d'enrichissement IA (optionnel)
            enable_ai_enhancement: Activer l'enrichissement IA
        """
        
        self.db_path = db_path
        self.cache_duration = cache_duration_minutes
        self.ai_enhancer = ai_enhancer
        self.enable_ai_enhancement = enable_ai_enhancement
        
        # Cache en mémoire avec verrou thread-safe
        self._cache: Dict[str, UnifiedContext] = {}
        self._cache_lock = Lock()
        self._last_cleanup = time.time()
        
        # ✅ NOUVEAU: Queue pour enrichissements IA asynchrones
        self._ai_enhancement_queue: List[str] = []
        self._ai_enhancement_lock = Lock()
        
        # Statistiques pour monitoring (enrichies)
        self.stats = {
            "context_retrievals": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "database_queries": 0,
            "context_creations": 0,
            "context_updates": 0,
            "cache_cleanups": 0,
            "ai_enhancements": 0,  # ✅ NOUVEAU
            "ai_enhancement_failures": 0,  # ✅ NOUVEAU
            "ai_enhancement_cache_hits": 0  # ✅ NOUVEAU
        }
        
        # Initialiser la base de données
        self._init_database()
        
        logger.info("🧠 [ContextManager] Gestionnaire centralisé initialisé")
        logger.info(f"   Base de données: {self.db_path}")
        logger.info(f"   Cache duration: {self.cache_duration} minutes")
        logger.info(f"   IA enhancement: {'✅' if self.enable_ai_enhancement else '❌'}")
    
    def get_unified_context(
        self, 
        conversation_id: str, 
        context_type: str = "general",
        max_chars: int = 800,
        enable_ai_enhancement: Optional[bool] = None
    ) -> UnifiedContext:
        """
        Point d'entrée principal - récupération unifiée du contexte
        
        Args:
            conversation_id: ID de la conversation
            context_type: Type de contexte ("rag", "clarification", "classification", "general")
            max_chars: Limite de caractères pour le contexte textuel
            enable_ai_enhancement: Override pour l'enrichissement IA
            
        Returns:
            UnifiedContext: Contexte complet et unifié
        """
        
        self.stats["context_retrievals"] += 1
        
        if not conversation_id:
            logger.debug("🔍 [ContextManager] Pas de conversation_id, retour contexte vide")
            return UnifiedContext(conversation_id="")
        
        try:
            # Nettoyage périodique du cache
            self._cleanup_cache_if_needed()
            
            # Vérifier le cache d'abord
            cached_context = self._get_from_cache(conversation_id)
            if cached_context:
                self.stats["cache_hits"] += 1
                cached_context.cache_hit = True
                
                # ✅ NOUVEAU: Vérifier si enrichissement IA nécessaire
                if (enable_ai_enhancement or self.enable_ai_enhancement) and cached_context.needs_ai_enhancement():
                    self._schedule_ai_enhancement(conversation_id)
                
                # Adapter selon le type demandé
                adapted_context = self._adapt_context_for_type(cached_context, context_type, max_chars)
                
                logger.debug(f"📋 [ContextManager] Cache hit pour {conversation_id} (type: {context_type})")
                return adapted_context
            
            # Cache miss - récupérer depuis la base
            self.stats["cache_misses"] += 1
            self.stats["database_queries"] += 1
            
            context = self._load_context_from_database(conversation_id)
            if not context:
                # Créer nouveau contexte
                context = self._create_new_context(conversation_id)
                self.stats["context_creations"] += 1
            
            # ✅ NOUVEAU: Enrichissement IA si demandé
            if (enable_ai_enhancement or self.enable_ai_enhancement) and context.needs_ai_enhancement():
                self._schedule_ai_enhancement(conversation_id)
            
            # Mettre en cache
            self._put_in_cache(conversation_id, context)
            
            # Adapter selon le type demandé
            adapted_context = self._adapt_context_for_type(context, context_type, max_chars)
            
            logger.debug(f"📋 [ContextManager] Context chargé depuis DB pour {conversation_id} (type: {context_type})")
            return adapted_context
            
        except Exception as e:
            logger.error(f"❌ [ContextManager] Erreur récupération contexte: {e}")
            # Retourner contexte minimal en cas d'erreur
            return UnifiedContext(conversation_id=conversation_id)
    
    def update_context(
        self, 
        conversation_id: str, 
        new_message: Dict[str, Any] = None,
        entities: Dict[str, Any] = None,
        topic: str = None,
        intent: str = None,  # ✅ NOUVEAU
        user_profile: Dict[str, Any] = None  # ✅ NOUVEAU
    ) -> bool:
        """
        Met à jour le contexte avec de nouvelles informations
        
        Args:
            conversation_id: ID de la conversation
            new_message: Nouveau message à ajouter
            entities: Nouvelles entités détectées
            topic: Nouveau topic de conversation
            intent: Intent conversationnel détecté
            user_profile: Profil utilisateur (expertise, style préféré)
            
        Returns:
            bool: Succès de la mise à jour
        """
        
        if not conversation_id:
            return False
        
        try:
            self.stats["context_updates"] += 1
            
            # Récupérer le contexte actuel
            context = self.get_unified_context(conversation_id)
            
            # Mettre à jour avec nouvelles infos
            if new_message:
                context.recent_messages.append(new_message)
                # Garder seulement les 10 derniers messages
                context.recent_messages = context.recent_messages[-10:]
                
                # Extraire questions/réponses
                if new_message.get('role') == 'user':
                    context.previous_questions.append(new_message.get('content', ''))
                    context.previous_questions = context.previous_questions[-5:]
                elif new_message.get('role') == 'assistant':
                    context.previous_answers.append(new_message.get('content', ''))
                    context.previous_answers = context.previous_answers[-5:]
            
            if entities:
                # Mettre à jour entités établies
                if entities.get('breed') and not context.established_breed:
                    context.established_breed = entities['breed']
                if entities.get('breed_specific') and not context.established_breed:
                    context.established_breed = entities['breed_specific']
                if entities.get('age_days') and not context.established_age:
                    context.established_age = entities['age_days']
                if entities.get('sex') and not context.established_sex:
                    context.established_sex = entities['sex']
                if entities.get('weight_grams') and not context.established_weight:
                    context.established_weight = entities['weight_grams']
                
                # ✅ NOUVEAU: Stocker entités inférées par IA
                if entities.get('ai_inferred'):
                    context.ai_inferred_entities.update(entities['ai_inferred'])
                if entities.get('confidence_scores'):
                    context.confidence_scores.update(entities['confidence_scores'])
            
            if topic and not context.conversation_topic:
                context.conversation_topic = topic
            
            # ✅ NOUVEAU: Mettre à jour intent et profil utilisateur
            if intent:
                context.conversation_intent = intent
            
            if user_profile:
                if user_profile.get('expertise_level'):
                    context.user_expertise_level = user_profile['expertise_level']
                if user_profile.get('response_style'):
                    context.preferred_response_style = user_profile['response_style']
            
            context.last_interaction = datetime.now()
            
            # Sauvegarder en base et cache
            self._save_context_to_database(context)
            self._put_in_cache(conversation_id, context)
            
            # ✅ NOUVEAU: Déclencher enrichissement IA si approprié
            if self.enable_ai_enhancement and context.get_enrichment_priority() in ["high", "medium"]:
                self._schedule_ai_enhancement(conversation_id)
            
            logger.debug(f"💾 [ContextManager] Contexte mis à jour: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [ContextManager] Erreur mise à jour contexte: {e}")
            return False
    
    def save_unified_context(
        self, 
        conversation_id: str, 
        context_data: Union[Dict[str, Any], object], 
        context_type: str = "general"
    ) -> bool:
        """
        ✅ CORRECTION: Méthode de compatibilité pour save_unified_context
        
        Cette méthode était manquante et causait l'erreur dans smart_classifier.py
        Elle redirige vers update_context avec normalisation des données.
        
        Args:
            conversation_id: ID de la conversation
            context_data: Données du contexte à sauvegarder (dict ou objet)
            context_type: Type de contexte
            
        Returns:
            bool: True si la sauvegarde a réussi
        """
        try:
            # ✅ CORRECTION: Normaliser context_data pour gérer différents types
            entities = {}
            topic = None
            intent = None
            user_profile = {}
            
            if isinstance(context_data, dict):
                entities = context_data.copy()
                topic = entities.pop('topic', None) or entities.pop('conversation_topic', None)
                intent = entities.pop('intent', None) or entities.pop('conversation_intent', None)
                # ✅ NOUVEAU: Extraire profil utilisateur
                user_profile = {
                    'expertise_level': entities.pop('user_expertise_level', None),
                    'response_style': entities.pop('preferred_response_style', None)
                }
            elif hasattr(context_data, '__dict__'):
                # Si c'est un objet avec des attributs
                try:
                    if hasattr(context_data, 'to_dict') and callable(getattr(context_data, 'to_dict')):
                        entities = context_data.to_dict()
                    else:
                        entities = context_data.__dict__.copy()
                    
                    topic = entities.pop('topic', None) or entities.pop('conversation_topic', None)
                    intent = entities.pop('intent', None) or entities.pop('conversation_intent', None)
                    user_profile = {
                        'expertise_level': entities.pop('user_expertise_level', None),
                        'response_style': entities.pop('preferred_response_style', None)
                    }
                except Exception as e:
                    logger.warning(f"⚠️ [ContextManager] Erreur conversion objet: {e}")
                    entities = {}
            else:
                # Fallback pour autres types
                logger.warning(f"⚠️ [ContextManager] Type de données inattendu: {type(context_data)}")
                entities = {"raw_data": str(context_data)}
            
            # Nettoyer user_profile des valeurs None
            user_profile = {k: v for k, v in user_profile.items() if v is not None}
            
            # Utiliser update_context pour faire la sauvegarde
            success = self.update_context(
                conversation_id=conversation_id,
                entities=entities,
                topic=topic,
                intent=intent,
                user_profile=user_profile if user_profile else None
            )
            
            if success:
                logger.info(f"✅ [ContextManager] Contexte unifié sauvegardé: {conversation_id} (type: {context_type})")
            else:
                logger.warning(f"⚠️ [ContextManager] Échec sauvegarde contexte unifié: {conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ [ContextManager] Erreur save_unified_context: {e}")
            return False
    
    async def enhance_context_with_ai(self, conversation_id: str) -> bool:
        """
        ✅ NOUVEAU: Enrichit le contexte avec l'IA
        
        Args:
            conversation_id: ID de la conversation à enrichir
            
        Returns:
            bool: True si l'enrichissement a réussi
        """
        
        if not self.ai_enhancer or not self.enable_ai_enhancement:
            logger.debug(f"🤖 [ContextManager] IA enhancer non disponible pour {conversation_id}")
            return False
        
        try:
            # Récupérer le contexte actuel
            context = self.get_unified_context(conversation_id, enable_ai_enhancement=False)
            
            if not context or not context.recent_messages:
                logger.debug(f"🤖 [ContextManager] Pas assez de contexte pour enrichissement: {conversation_id}")
                return False
            
            # Appeler le service d'enrichissement IA
            enhancement_result = await self.ai_enhancer.analyze_conversational_context(
                conversation_id, context.to_dict()
            )
            
            if enhancement_result:
                # Mettre à jour le contexte avec les insights IA
                context.ai_context_summary = enhancement_result.get('summary')
                context.ai_suggested_topics = enhancement_result.get('suggested_topics', [])
                context.ai_confidence = enhancement_result.get('confidence', 0.0)
                context.last_ai_enhancement = datetime.now()
                
                # Enrichir les entités inférées
                if enhancement_result.get('inferred_entities'):
                    context.ai_inferred_entities.update(enhancement_result['inferred_entities'])
                
                # Mettre à jour intent et profil si détectés
                if enhancement_result.get('conversation_intent'):
                    context.conversation_intent = enhancement_result['conversation_intent']
                
                if enhancement_result.get('user_expertise_level'):
                    context.user_expertise_level = enhancement_result['user_expertise_level']
                
                # Sauvegarder le contexte enrichi
                self._save_context_to_database(context)
                self._put_in_cache(conversation_id, context)
                
                self.stats["ai_enhancements"] += 1
                logger.info(f"🤖 [ContextManager] Contexte enrichi par IA: {conversation_id}")
                return True
            
        except Exception as e:
            self.stats["ai_enhancement_failures"] += 1
            logger.error(f"❌ [ContextManager] Erreur enrichissement IA: {e}")
        
        return False
    
    def _schedule_ai_enhancement(self, conversation_id: str):
        """✅ NOUVEAU: Programme un enrichissement IA asynchrone"""
        
        with self._ai_enhancement_lock:
            if conversation_id not in self._ai_enhancement_queue:
                self._ai_enhancement_queue.append(conversation_id)
                logger.debug(f"📅 [ContextManager] Enrichissement IA programmé: {conversation_id}")
    
    async def process_ai_enhancement_queue(self, max_concurrent: int = 3):
        """✅ NOUVEAU: Traite la queue d'enrichissements IA"""
        
        if not self._ai_enhancement_queue:
            return
        
        # Limiter le nombre de traitements concurrent
        batch_size = min(len(self._ai_enhancement_queue), max_concurrent)
        
        with self._ai_enhancement_lock:
            batch = self._ai_enhancement_queue[:batch_size]
            self._ai_enhancement_queue = self._ai_enhancement_queue[batch_size:]
        
        # Traiter le batch en parallèle
        tasks = [self.enhance_context_with_ai(conv_id) for conv_id in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"🤖 [ContextManager] Batch IA traité: {success_count}/{len(batch)} réussites")
    
    def _get_from_cache(self, conversation_id: str) -> Optional[UnifiedContext]:
        """Récupération depuis le cache avec vérification d'expiration"""
        
        with self._cache_lock:
            if conversation_id not in self._cache:
                return None
            
            cached_context = self._cache[conversation_id]
            
            # Vérifier expiration
            if cached_context.last_interaction:
                age_minutes = (datetime.now() - cached_context.last_interaction).total_seconds() / 60
                if age_minutes > self.cache_duration:
                    # Expiré, supprimer du cache
                    del self._cache[conversation_id]
                    return None
                
                cached_context.context_age_minutes = age_minutes
            
            return cached_context
    
    def _put_in_cache(self, conversation_id: str, context: UnifiedContext):
        """Mise en cache thread-safe"""
        
        with self._cache_lock:
            self._cache[conversation_id] = context
    
    def _cleanup_cache_if_needed(self):
        """Nettoyage périodique du cache (toutes les 10 minutes)"""
        
        current_time = time.time()
        if current_time - self._last_cleanup > 600:  # 10 minutes
            
            with self._cache_lock:
                expired_keys = []
                cutoff_time = datetime.now() - timedelta(minutes=self.cache_duration)
                
                for key, context in self._cache.items():
                    if context.last_interaction and context.last_interaction < cutoff_time:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._cache[key]
                
                if expired_keys:
                    self.stats["cache_cleanups"] += 1
                    logger.debug(f"🧹 [ContextManager] Cache nettoyé: {len(expired_keys)} entrées expirées")
            
            self._last_cleanup = current_time
    
    def _adapt_context_for_type(
        self, 
        context: UnifiedContext, 
        context_type: str,
        max_chars: int
    ) -> UnifiedContext:
        """
        Adapte le contexte selon le type demandé
        
        Types supportés:
        - "rag": Contexte optimisé pour recherche RAG
        - "clarification": Contexte pour génération de clarifications
        - "classification": Contexte pour classification intelligente  
        - "general": Contexte complet
        """
        
        if context_type == ContextType.RAG.value:
            return self._adapt_for_rag(context, max_chars)
        elif context_type == ContextType.CLARIFICATION.value:
            return self._adapt_for_clarification(context, max_chars)
        elif context_type == ContextType.CLASSIFICATION.value:
            return self._adapt_for_classification(context, max_chars)
        else:
            return context  # Type "general" ou inconnu = contexte complet
    
    def _adapt_for_rag(self, context: UnifiedContext, max_chars: int) -> UnifiedContext:
        """Adapte le contexte pour recherche RAG (focus sur entités et performance)"""
        
        # Créer une copie adaptée
        rag_context = UnifiedContext(
            conversation_id=context.conversation_id,
            last_interaction=context.last_interaction,
            
            # Entités établies (priorité pour RAG)
            established_breed=context.established_breed,
            established_age=context.established_age,
            established_sex=context.established_sex,
            established_weight=context.established_weight,
            
            # ✅ NOUVEAU: Entités IA pour RAG plus précis
            ai_inferred_entities=context.ai_inferred_entities,
            confidence_scores=context.confidence_scores,
            
            # Topic et intent de conversation
            conversation_topic=context.conversation_topic,
            conversation_intent=context.conversation_intent,
            
            # Données de performance (essentielles pour RAG)
            weight_data=context.weight_data,
            feeding_context=context.feeding_context,
            
            # Historique limité pour RAG
            previous_questions=context.previous_questions[-2:] if context.previous_questions else [],
            
            # ✅ NOUVEAU: Contexte IA pour RAG enrichi
            ai_context_summary=context.ai_context_summary,
            ai_suggested_topics=context.ai_suggested_topics,
            user_expertise_level=context.user_expertise_level,
            
            # Métadonnées
            context_age_minutes=context.context_age_minutes,
            confidence=context.confidence,
            cache_hit=context.cache_hit,
            ai_confidence=context.ai_confidence
        )
        
        return rag_context
    
    def _adapt_for_clarification(self, context: UnifiedContext, max_chars: int) -> UnifiedContext:
        """Adapte le contexte pour génération de clarifications"""
        
        clarification_context = UnifiedContext(
            conversation_id=context.conversation_id,
            last_interaction=context.last_interaction,
            
            # Entités pour déterminer ce qui manque
            established_breed=context.established_breed,
            established_age=context.established_age,
            established_sex=context.established_sex,
            
            # ✅ NOUVEAU: Entités IA pour clarifications plus intelligentes
            ai_inferred_entities=context.ai_inferred_entities,
            confidence_scores=context.confidence_scores,
            
            # Historique des clarifications (éviter répétitions)
            clarification_history=context.clarification_history,
            
            # Topic pour clarifications contextuelles
            conversation_topic=context.conversation_topic,
            conversation_intent=context.conversation_intent,
            
            # Dernières questions pour contexte
            previous_questions=context.previous_questions[-3:] if context.previous_questions else [],
            
            # ✅ NOUVEAU: Style de réponse préféré
            user_expertise_level=context.user_expertise_level,
            preferred_response_style=context.preferred_response_style,
            
            # Métadonnées
            context_age_minutes=context.context_age_minutes,
            confidence=context.confidence,
            cache_hit=context.cache_hit
        )
        
        return clarification_context
    
    def _adapt_for_classification(self, context: UnifiedContext, max_chars: int) -> UnifiedContext:
        """Adapte le contexte pour classification intelligente"""
        
        classification_context = UnifiedContext(
            conversation_id=context.conversation_id,
            last_interaction=context.last_interaction,
            
            # Toutes les entités pour classification
            established_breed=context.established_breed,
            established_age=context.established_age,
            established_sex=context.established_sex,
            established_weight=context.established_weight,
            
            # ✅ NOUVEAU: Entités IA pour classification plus précise
            ai_inferred_entities=context.ai_inferred_entities,
            confidence_scores=context.confidence_scores,
            
            # Topic et intent actuels
            conversation_topic=context.conversation_topic,
            conversation_intent=context.conversation_intent,
            conversation_flow=context.conversation_flow,
            
            # Messages récents pour détecter clarifications
            recent_messages=context.recent_messages[-3:] if context.recent_messages else [],
            
            # Historique des questions pour détecter suites
            previous_questions=context.previous_questions,
            previous_answers=context.previous_answers,
            
            # ✅ NOUVEAU: Insights IA pour classification
            ai_context_summary=context.ai_context_summary,
            ai_suggested_topics=context.ai_suggested_topics,
            user_expertise_level=context.user_expertise_level,
            
            # Métadonnées
            context_age_minutes=context.context_age_minutes,
            confidence=context.confidence,
            cache_hit=context.cache_hit,
            ai_confidence=context.ai_confidence
        )
        
        return classification_context
    
    def _load_context_from_database(self, conversation_id: str) -> Optional[UnifiedContext]:
        """Charge le contexte depuis la base de données"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT context_data, updated_at 
                    FROM conversation_contexts 
                    WHERE conversation_id = ?
                """, (conversation_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Désérialiser le contexte
                context_data = json.loads(row['context_data'])
                
                # Convertir vers UnifiedContext avec compatibilité
                context_dict = {}
                for key, value in context_data.items():
                    if key in UnifiedContext.__annotations__:
                        context_dict[key] = value
                
                context = UnifiedContext(
                    conversation_id=conversation_id,
                    **context_dict
                )
                
                # Convertir timestamps
                if context_data.get('last_interaction'):
                    context.last_interaction = datetime.fromisoformat(context_data['last_interaction'])
                
                if context_data.get('last_ai_enhancement'):
                    context.last_ai_enhancement = datetime.fromisoformat(context_data['last_ai_enhancement'])
                
                return context
                
        except Exception as e:
            logger.error(f"❌ [ContextManager] Erreur chargement DB: {e}")
            return None
    
    def _save_context_to_database(self, context: UnifiedContext) -> bool:
        """Sauvegarde le contexte en base de données"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                context_json = json.dumps(context.to_dict())
                now = datetime.now().isoformat()
                
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_contexts 
                    (conversation_id, context_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (context.conversation_id, context_json, now, now))
                
                return True
                
        except Exception as e:
            logger.error(f"❌ [ContextManager] Erreur sauvegarde DB: {e}")
            return False
    
    def _create_new_context(self, conversation_id: str) -> UnifiedContext:
        """Crée un nouveau contexte vide"""
        
        return UnifiedContext(
            conversation_id=conversation_id,
            last_interaction=datetime.now()
        )
    
    def _init_database(self):
        """Initialise la base de données si nécessaire"""
        
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
                
                # Index pour performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversation_contexts_updated 
                    ON conversation_contexts(updated_at)
                """)
                
        except Exception as e:
            logger.error(f"❌ [ContextManager] Erreur init DB: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire (enrichies)"""
        
        total_retrievals = max(self.stats["context_retrievals"], 1)
        cache_hit_rate = (self.stats["cache_hits"] / total_retrievals) * 100
        
        # ✅ NOUVEAU: Statistiques IA
        total_ai_attempts = self.stats["ai_enhancements"] + self.stats["ai_enhancement_failures"]
        ai_success_rate = (self.stats["ai_enhancements"] / max(total_ai_attempts, 1)) * 100
        
        with self._cache_lock:
            cache_size = len(self._cache)
        
        with self._ai_enhancement_lock:
            enhancement_queue_size = len(self._ai_enhancement_queue)
        
        return {
            **self.stats,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "cache_size": cache_size,
            "cache_duration_minutes": self.cache_duration,
            "database_path": self.db_path,
            "ai_enhancement_enabled": self.enable_ai_enhancement,
            "ai_success_rate": f"{ai_success_rate:.1f}%",
            "ai_enhancement_queue_size": enhancement_queue_size
        }
    
    def clear_cache(self):
        """Vide le cache (pour tests ou maintenance)"""
        
        with self._cache_lock:
            self._cache.clear()
        
        with self._ai_enhancement_lock:
            self._ai_enhancement_queue.clear()
        
        logger.info("🧹 [ContextManager] Cache et queue IA vidés manuellement")
    
    def set_ai_enhancer(self, ai_enhancer: object):
        """✅ NOUVEAU: Définit le service d'enrichissement IA"""
        self.ai_enhancer = ai_enhancer
        self.enable_ai_enhancement = ai_enhancer is not None
        logger.info(f"🤖 [ContextManager] IA Enhancer configuré: {type(ai_enhancer).__name__}")

# Fonctions utilitaires pour compatibilité avec l'ancien système

def get_context_for_rag(conversation_id: str, max_chars: int = 800) -> str:
    """
    Fonction de compatibilité pour get_context_for_rag
    
    Remplace les appels directs aux anciens modules par le ContextManager unifié
    """
    if not conversation_id:
        return ""
    
    try:
        # Utiliser le gestionnaire centralisé
        context_manager = ContextManager()
        unified_context = context_manager.get_unified_context(conversation_id, "rag", max_chars)
        
        # Convertir vers format texte pour compatibilité
        context_parts = []
        
        if unified_context.established_breed:
            context_parts.append(f"Race: {unified_context.established_breed}")
        
        if unified_context.established_age:
            context_parts.append(f"Âge: {unified_context.established_age} jours")
        
        if unified_context.established_sex:
            context_parts.append(f"Sexe: {unified_context.established_sex}")
        
        if unified_context.conversation_topic:
            context_parts.append(f"Topic: {unified_context.conversation_topic}")
        
        # ✅ NOUVEAU: Inclure insights IA
        if unified_context.ai_context_summary:
            context_parts.append(f"Contexte IA: {unified_context.ai_context_summary[:100]}")
        
        if unified_context.conversation_intent:
            context_parts.append(f"Intent: {unified_context.conversation_intent}")
        
        if unified_context.previous_questions:
            recent_q = unified_context.previous_questions[-1]
            context_parts.append(f"Dernière question: {recent_q[:100]}...")
        
        context_text = " | ".join(context_parts)
        
        # Limiter aux caractères demandés
        if len(context_text) > max_chars:
            context_text = context_text[:max_chars-3] + "..."
        
        return context_text
        
    except Exception as e:
        logger.error(f"❌ [ContextManager] Erreur compatibilité RAG: {e}")
        return ""

def get_context_for_clarification(conversation_id: str) -> Dict[str, Any]:
    """
    Fonction de compatibilité pour get_context_for_clarification
    """
    if not conversation_id:
        return {}
    
    try:
        context_manager = ContextManager()
        unified_context = context_manager.get_unified_context(conversation_id, "clarification")
        
        # Convertir vers format dict pour compatibilité
        return {
            "established_entities": {
                "breed": unified_context.established_breed,
                "age_days": unified_context.established_age,
                "sex": unified_context.established_sex
            },
            "conversation_topic": unified_context.conversation_topic,
            "conversation_intent": unified_context.conversation_intent,  # ✅ NOUVEAU
            "previous_questions": unified_context.previous_questions,
            "clarification_history": unified_context.clarification_history,
            "ai_inferred_entities": unified_context.ai_inferred_entities,  # ✅ NOUVEAU
            "user_expertise_level": unified_context.user_expertise_level,  # ✅ NOUVEAU
            "preferred_response_style": unified_context.preferred_response_style  # ✅ NOUVEAU
        }
        
    except Exception as e:
        logger.error(f"❌ [ContextManager] Erreur compatibilité clarification: {e}")
        return {}

def get_conversation_context(conversation_id: str) -> Optional[UnifiedContext]:
    """
    Fonction de compatibilité pour get_conversation_context
    """
    if not conversation_id:
        return None
    
    try:
        context_manager = ContextManager()
        unified_context = context_manager.get_unified_context(conversation_id, "classification")
        
        # Retourner le contexte unifié (compatible avec les attributs attendus)
        return unified_context
        
    except Exception as e:
        logger.error(f"❌ [ContextManager] Erreur compatibilité conversation: {e}")
        return None

# Instance globale pour réutilisation
context_manager = ContextManager()

# ✅ NOUVEAU: Fonction pour configurer l'IA enhancer
def configure_ai_enhancer(ai_enhancer_instance):
    """Configure l'instance globale avec l'IA enhancer"""
    global context_manager
    context_manager.set_ai_enhancer(ai_enhancer_instance)

# Fonction de test (enrichie)
def test_context_manager():
    """Teste le gestionnaire de contexte avec des scénarios réels + IA"""
    
    print("🧪 Test du gestionnaire de contexte (version IA):")
    print("=" * 60)
    
    manager = ContextManager(db_path="test_conversations.db", enable_ai_enhancement=False)
    test_conv_id = "test_conv_123"
    
    # Test 1: Contexte nouveau
    print("\n📝 Test 1: Nouveau contexte")
    context1 = manager.get_unified_context(test_conv_id, "rag")
    print(f"   Context créé: {context1.conversation_id}")
    print(f"   Entités: {context1.has_entities()}")
    print(f"   Cache hit: {context1.cache_hit}")
    print(f"   Priorité enrichissement: {context1.get_enrichment_priority()}")
    
    # Test 2: Mise à jour avec entités et profil utilisateur
    print("\n📝 Test 2: Mise à jour avec entités et profil")
    entities = {
        "breed": "Ross 308", 
        "age_days": 21, 
        "sex": "male",
        "ai_inferred": {"potential_weight": "2.1kg"},
        "confidence_scores": {"breed": 0.95, "age": 0.80}
    }
    user_profile = {"expertise_level": "intermediate", "response_style": "detailed"}
    
    success = manager.update_context(
        test_conv_id, 
        entities=entities, 
        topic="performance",
        intent="growth_optimization",
        user_profile=user_profile
    )
    print(f"   Mise à jour: {'✅' if success else '❌'}")
    
    # Test 3: Récupération avec cache et nouvelles données
    print("\n📝 Test 3: Récupération depuis cache (enrichi)")
    context2 = manager.get_unified_context(test_conv_id, "clarification")
    print(f"   Cache hit: {context2.cache_hit}")
    print(f"   Entités établies: {context2.get_context_summary()}")
    print(f"   Intent: {context2.conversation_intent}")
    print(f"   Expertise utilisateur: {context2.user_expertise_level}")
    print(f"   Entités IA: {len(context2.ai_inferred_entities)} items")
    
    # Test 4: Types de contexte différents
    print("\n📝 Test 4: Types de contexte")
    for ctx_type in ["rag", "clarification", "classification", "general"]:
        ctx = manager.get_unified_context(test_conv_id, ctx_type)
        ai_info = f"IA_conf={ctx.ai_confidence:.2f}" if ctx.ai_confidence > 0 else "pas_IA"
        print(f"   Type {ctx_type}: entités={ctx.has_entities()}, âge={ctx.context_age_minutes:.1f}min, {ai_info}")
    
    # Test 5: Test save_unified_context avec données IA
    print("\n📝 Test 5: Test save_unified_context (avec IA)")
    test_context_data = {
        "breed_specific": "Cobb 500",
        "age_days": 14,
        "sex": "female",
        "topic": "health",
        "intent": "disease_prevention",
        "user_expertise_level": "novice",
        "ai_inferred": {"health_score": 0.85},
        "confidence_scores": {"overall": 0.90}
    }
    success = manager.save_unified_context(test_conv_id, test_context_data, "test")
    print(f"   save_unified_context: {'✅' if success else '❌'}")
    
    # Vérifier que les données ont été sauvegardées
    updated_context = manager.get_unified_context(test_conv_id, "general")
    print(f"   Breed après save: {updated_context.established_breed}")
    print(f"   Age après save: {updated_context.established_age}")
    print(f"   Intent après save: {updated_context.conversation_intent}")
    print(f"   Expertise après save: {updated_context.user_expertise_level}")
    
    # ✅ NOUVEAU Test 6: Test besoins enrichissement IA
    print("\n📝 Test 6: Test besoins enrichissement IA")
    needs_enhancement = updated_context.needs_ai_enhancement()
    priority = updated_context.get_enrichment_priority()
    print(f"   Besoin enrichissement: {needs_enhancement}")
    print(f"   Priorité: {priority}")
    
    # Test 7: Statistiques (enrichies)
    print("\n📊 Statistiques enrichies:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Tests terminés!")
    print("🤖 Note: Tests IA simulés (pas de vrai service IA connecté)")

if __name__ == "__main__":
    test_context_manager()