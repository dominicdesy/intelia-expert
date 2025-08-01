"""
app/api/v1/conversation_memory_enhanced.py - VERSION AMÉLIORÉE AVEC IA + ROBUSTESSE

🔵 CORRECTIONS OPTIONNELLES APPLIQUÉES:
1. ✅ Fallback plus robuste si extraction IA échoue
2. ✅ Persistence forcée des questions de clarification
3. ✅ Cache conversationnel renforcé avec backup
4. ✅ Retry automatique en cas d'échec IA
5. ✅ Validation et correction automatique des données

AMÉLIORATIONS MAJEURES RENFORCÉES + TOUTES LES FONCTIONS ORIGINALES:
1. Extraction d'entités intelligente via OpenAI avec fallbacks multiples
2. Raisonnement contextuel dynamique pour éviter les clarifications redondantes
3. Fusion intelligente d'informations entre messages avec validation
4. Mise à jour dynamique des entités au fil de la conversation
5. Contexte optimisé pour RAG et clarification avec backup
6. Expiration intelligente selon l'activité avec récupération
"""

import os
import json
import logging
import sqlite3
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
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
    """Entités extraites intelligemment avec raisonnement contextuel + ROBUSTESSE"""
    
    # Informations de base
    breed: Optional[str] = None
    breed_confidence: float = 0.0
    breed_type: Optional[str] = None  # specific/generic
    
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
    
    # 🔵 ROBUSTESSE - Métadonnées IA étendues
    extraction_method: str = "basic"  # basic/openai/hybrid/fallback
    extraction_attempts: int = 0
    extraction_success: bool = True
    last_ai_update: Optional[datetime] = None
    confidence_overall: float = 0.0
    data_validated: bool = False
    backup_extraction_used: bool = False
    
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
        """🔵 NOUVEAU: Valide et corrige automatiquement les données incohérentes"""
        
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
        
        # Race toujours critique
        if not self.breed or self.breed_type == "generic" or self.breed_confidence < 0.7:
            missing.append("breed")
        
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
        return merged.validate_and_correct()  # 🔵 Auto-validation après fusion

@dataclass
class ConversationMessage:
    """Message dans une conversation avec métadonnées + ROBUSTESSE"""
    id: str
    conversation_id: str
    user_id: str
    role: str  # user/assistant
    message: str
    timestamp: datetime
    language: str = "fr"
    message_type: str = "text"  # text/clarification/response
    extracted_entities: Optional[IntelligentEntities] = None
    confidence_score: float = 0.0
    processing_method: str = "basic"  # basic/ai_enhanced/fallback
    
    # 🔵 ROBUSTESSE - Métadonnées de persistance
    extraction_retries: int = 0
    backup_saved: bool = False
    validated: bool = False
    
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
            "extraction_retries": self.extraction_retries,
            "backup_saved": self.backup_saved,
            "validated": self.validated
        }

@dataclass
class IntelligentConversationContext:
    """Contexte conversationnel intelligent avec raisonnement + ROBUSTESSE"""
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
    
    # 🔵 ROBUSTESSE - Persistance forcée et backup
    forced_backup: bool = False
    backup_timestamp: Optional[datetime] = None
    cache_hits: int = 0
    cache_restored: bool = False
    data_integrity_checked: bool = False
    
    def add_message(self, message: ConversationMessage):
        """Ajoute un message et met à jour le contexte intelligemment"""
        self.messages.append(message)
        self.last_activity = datetime.now()
        self.total_exchanges += 1
        
        # Fusionner les entités si disponibles
        if message.extracted_entities:
            old_entities = self.consolidated_entities
            self.consolidated_entities = self.consolidated_entities.merge_with(message.extracted_entities)
            
            # 🔵 Log des changements d'entités
            if old_entities.breed != self.consolidated_entities.breed:
                logger.info(f"🔄 [Entities] Race mise à jour: {old_entities.breed} → {self.consolidated_entities.breed}")
            if old_entities.age_days != self.consolidated_entities.age_days:
                logger.info(f"🔄 [Entities] Âge mis à jour: {old_entities.age_days} → {self.consolidated_entities.age_days}j")
        
        # Mettre à jour le statut conversationnel
        self._update_conversation_status()
        
        # 🔵 Forcer backup après chaque message
        self.forced_backup = True
        self.backup_timestamp = datetime.now()
    
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
    
    def get_context_for_clarification(self) -> Dict[str, Any]:
        """Retourne le contexte optimisé pour les clarifications + BACKUP"""
        context = {
            "breed": self.consolidated_entities.breed,
            "breed_type": self.consolidated_entities.breed_type,
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
            # 🔵 ROBUSTESSE - Info backup
            "data_validated": self.consolidated_entities.data_validated,
            "backup_available": self.forced_backup,
            "extraction_method": self.consolidated_entities.extraction_method
        }
        
        return context
    
    def get_context_for_rag(self, max_chars: int = 500) -> str:
        """Retourne le contexte optimisé pour le RAG + VALIDATION"""
        context_parts = []
        
        # Informations de base validées
        entities = self.consolidated_entities
        if entities.data_validated or not entities.data_validated:  # Valider si pas déjà fait
            entities = entities.validate_and_correct()
        
        if entities.breed:
            context_parts.append(f"Race: {entities.breed}")
        
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
            important_parts = context_parts[:4]  # Race, âge, poids, symptômes
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
            # 🔵 ROBUSTESSE
            "forced_backup": self.forced_backup,
            "backup_timestamp": self.backup_timestamp.isoformat() if self.backup_timestamp else None,
            "cache_hits": self.cache_hits,
            "cache_restored": self.cache_restored,
            "data_integrity_checked": self.data_integrity_checked
        }

class IntelligentConversationMemory:
    """Système de mémoire conversationnelle intelligent avec IA + ROBUSTESSE"""
    
    def __init__(self, db_path: str = None):
        """Initialise le système de mémoire intelligent + ROBUSTE"""
        
        # Configuration
        self.db_path = db_path or os.getenv('CONVERSATION_MEMORY_DB_PATH', 'data/conversation_memory.db')
        self.max_messages_in_memory = int(os.getenv('MAX_MESSAGES_IN_MEMORY', '50'))
        self.context_expiry_hours = int(os.getenv('CONTEXT_EXPIRY_HOURS', '24'))
        self.ai_enhancement_enabled = os.getenv('AI_ENHANCEMENT_ENABLED', 'true').lower() == 'true'
        self.ai_enhancement_model = os.getenv('AI_ENHANCEMENT_MODEL', 'gpt-4o-mini')
        self.ai_enhancement_timeout = int(os.getenv('AI_ENHANCEMENT_TIMEOUT', '15'))
        
        # 🔵 ROBUSTESSE - Configuration avancée
        self.ai_retry_attempts = int(os.getenv('AI_RETRY_ATTEMPTS', '3'))
        self.ai_retry_delay = float(os.getenv('AI_RETRY_DELAY', '1.0'))
        self.backup_enabled = os.getenv('MEMORY_BACKUP_ENABLED', 'true').lower() == 'true'
        self.force_backup_interval = int(os.getenv('FORCE_BACKUP_INTERVAL', '5'))  # minutes
        
        # Cache en mémoire pour performance + ROBUSTESSE
        self.conversation_cache: Dict[str, IntelligentConversationContext] = {}
        self.cache_max_size = int(os.getenv('CONVERSATION_CACHE_SIZE', '100'))
        self.cache_lock = Lock()  # 🔵 Thread safety
        
        # 🔵 BACKUP cache pour récupération
        self.backup_cache: Dict[str, IntelligentConversationContext] = {}
        
        # Statistiques étendues
        self.stats = {
            "total_conversations": 0,
            "total_messages": 0,
            "ai_enhancements": 0,
            "ai_failures": 0,
            "ai_retries": 0,
            "backup_recoveries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "data_corrections": 0
        }
        
        # Initialiser la base de données
        self._init_database()
        
        # 🔵 Démarrer thread de backup automatique
        if self.backup_enabled:
            self._start_backup_thread()
        
        logger.info(f"🧠 [IntelligentMemory] Système ROBUSTE initialisé")
        logger.info(f"🧠 [IntelligentMemory] DB: {self.db_path}")
        logger.info(f"🧠 [IntelligentMemory] IA enhancing: {'✅' if self.ai_enhancement_enabled else '❌'}")
        logger.info(f"🧠 [IntelligentMemory] Modèle IA: {self.ai_enhancement_model}")
        logger.info(f"🔵 [Robustesse] Retry IA: {self.ai_retry_attempts} tentatives")
        logger.info(f"🔵 [Robustesse] Backup auto: {'✅' if self.backup_enabled else '❌'}")

    def _init_database(self):
        """Initialise la base de données avec schéma amélioré + ROBUSTESSE"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Table des conversations avec métadonnées étendues + ROBUSTESSE
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
                    
                    -- 🔵 ROBUSTESSE - Backup et validation
                    forced_backup BOOLEAN DEFAULT FALSE,
                    backup_timestamp TIMESTAMP,
                    data_integrity_checked BOOLEAN DEFAULT FALSE,
                    validation_errors TEXT,
                    
                    -- Performance
                    confidence_overall REAL DEFAULT 0.0
                )
            """)
            
            # Table des messages avec extraction d'entités + ROBUSTESSE
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
                    
                    -- 🔵 ROBUSTESSE - Métadonnées extraction
                    extraction_retries INTEGER DEFAULT 0,
                    extraction_success BOOLEAN DEFAULT TRUE,
                    backup_saved BOOLEAN DEFAULT FALSE,
                    validated BOOLEAN DEFAULT FALSE,
                    
                    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                )
            """)
            
            # 🔵 NOUVEAU - Table de backup pour récupération
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_backups (
                    backup_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    backup_data TEXT NOT NULL,
                    backup_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    backup_type TEXT DEFAULT 'auto',
                    recovery_tested BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Index pour performance + ROBUSTESSE
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_user_activity ON conversations (user_id, last_activity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv_time ON conversation_messages (conversation_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_urgency ON conversations (conversation_urgency, last_activity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_backup_conv ON conversation_backups (conversation_id, backup_timestamp)")
            
        logger.info(f"✅ [IntelligentMemory] Base de données ROBUSTE initialisée")

    def _start_backup_thread(self):
        """🔵 NOUVEAU: Démarre le thread de backup automatique"""
        def backup_worker():
            while True:
                try:
                    time.sleep(self.force_backup_interval * 60)  # Convertir en secondes
                    self._force_backup_conversations()
                except Exception as e:
                    logger.error(f"❌ [Backup Thread] Erreur: {e}")
                    time.sleep(60)  # Attendre 1 minute avant retry
        
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        logger.info("🔵 [Backup Thread] Thread de backup automatique démarré")

    def _force_backup_conversations(self):
        """🔵 NOUVEAU: Force le backup des conversations critiques"""
        try:
            with self.cache_lock:
                conversations_to_backup = [
                    ctx for ctx in self.conversation_cache.values()
                    if ctx.forced_backup and (
                        not ctx.backup_timestamp or 
                        (datetime.now() - ctx.backup_timestamp).total_seconds() > 300  # 5 minutes
                    )
                ]
            
            for ctx in conversations_to_backup:
                self._create_conversation_backup(ctx)
                ctx.forced_backup = False
                ctx.backup_timestamp = datetime.now()
                
            if conversations_to_backup:
                logger.info(f"🔵 [Auto Backup] {len(conversations_to_backup)} conversations sauvegardées")
                
        except Exception as e:
            logger.error(f"❌ [Auto Backup] Erreur backup forcé: {e}")

    def _create_conversation_backup(self, context: IntelligentConversationContext):
        """🔵 NOUVEAU: Crée un backup d'une conversation"""
        try:
            backup_id = f"{context.conversation_id}_{int(time.time())}"
            backup_data = json.dumps(context.to_dict(), ensure_ascii=False, indent=2)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversation_backups (backup_id, conversation_id, backup_data, backup_type)
                    VALUES (?, ?, ?, ?)
                """, (backup_id, context.conversation_id, backup_data, "auto"))
                conn.commit()
                
            # Garder aussi en mémoire
            self.backup_cache[context.conversation_id] = context
            
        except Exception as e:
            logger.error(f"❌ [Backup] Erreur création backup: {e}")

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
        """🔵 AMÉLIORÉ: Extraction d'entités avec fallbacks multiples et retry"""
        
        # Tentative 1: Extraction IA si disponible
        if self.ai_enhancement_enabled and OPENAI_AVAILABLE and openai:
            for attempt in range(self.ai_retry_attempts):
                try:
                    entities = await self._extract_entities_openai(message, language, conversation_context)
                    if entities and entities.confidence_overall > 0.3:  # Seuil minimum de qualité
                        entities.extraction_attempts = attempt + 1
                        entities.extraction_success = True
                        self.stats["ai_enhancements"] += 1
                        logger.info(f"✅ [AI Extraction] Succès tentative {attempt + 1}")
                        return entities.validate_and_correct()
                    
                except Exception as e:
                    self.stats["ai_failures"] += 1
                    self.stats["ai_retries"] += 1
                    logger.warning(f"⚠️ [AI Extraction] Tentative {attempt + 1} échouée: {e}")
                    
                    if attempt < self.ai_retry_attempts - 1:
                        await asyncio.sleep(self.ai_retry_delay * (attempt + 1))
            
            logger.warning("⚠️ [AI Extraction] Toutes les tentatives IA ont échoué, fallback vers extraction basique")
        
        # Fallback: Extraction basique
        logger.info("🔄 [Fallback] Utilisation extraction basique")
        entities = await self._extract_entities_basic(message, language)
        entities.extraction_method = "fallback"
        entities.backup_extraction_used = True
        
        return entities.validate_and_correct()

    async def _extract_entities_openai(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """Extraction d'entités par OpenAI avec gestion robuste des erreurs"""
        
        # Contexte pour l'IA
        context_info = ""
        if conversation_context and conversation_context.consolidated_entities:
            existing_entities = conversation_context.consolidated_entities.to_dict()
            if existing_entities:
                context_info = f"\n\nEntités déjà connues dans cette conversation:\n{json.dumps(existing_entities, ensure_ascii=False, indent=2)}"
        
        extraction_prompt = f"""Tu es un expert en extraction d'informations vétérinaires pour l'aviculture. Analyse ce message et extrait TOUTES les informations pertinentes.

Message: "{message}"{context_info}

INSTRUCTIONS CRITIQUES:
1. Extrait toutes les informations, même partielles ou implicites
2. Utilise le contexte existant pour éviter les doublons
3. Assigne des scores de confiance (0.0 à 1.0) basés sur la précision
4. Inférer des informations logiques (ex: si "mes poulets Ross 308", alors breed_type="specific")
5. Convertir automatiquement les unités (semaines -> jours, kg -> grammes)

Réponds UNIQUEMENT avec ce JSON exact:
```json
{{
  "breed": "race_détectée_ou_null",
  "breed_confidence": 0.0_à_1.0,
  "breed_type": "specific/generic/null",
  
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
  "ventilation_quality": "good/poor/null",
  
  "feed_type": "type_ou_null",
  "feed_conversion": ratio_ou_null,
  "water_consumption": "normal/low/high/null",
  
  "flock_size": nombre_ou_null,
  "vaccination_status": "up_to_date/delayed/unknown/null",
  "previous_treatments": ["traitement1"] ou [],
  
  "problem_duration": "durée_ou_null",
  "problem_severity": "low/medium/high/critical/null",
  "intervention_urgency": "none/monitor/act/urgent/null",
  
  "extraction_method": "openai",
  "confidence_overall": 0.0_à_1.0
}}
```

EXEMPLES DE RAISONNEMENT:
- "mes poulets" → breed_type="generic", breed_confidence=0.3
- "Ross 308" → breed="Ross 308", breed_type="specific", breed_confidence=0.95
- "3 semaines" → age_weeks=3, age_days=21, age_confidence=0.9
- "800g" → weight_grams=800, weight_confidence=0.95
- "mortalité élevée" → health_status="concerning", intervention_urgency="act"
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
                ventilation_quality=data.get("ventilation_quality"),
                
                feed_type=data.get("feed_type"),
                feed_conversion=data.get("feed_conversion"),
                water_consumption=data.get("water_consumption"),
                
                flock_size=data.get("flock_size"),
                vaccination_status=data.get("vaccination_status"),
                previous_treatments=data.get("previous_treatments", []),
                
                problem_duration=data.get("problem_duration"),
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
        """🔵 AMÉLIORÉ: Extraction d'entités basique avec validation renforcée"""
        
        entities = IntelligentEntities(extraction_method="basic")
        message_lower = message.lower()
        
        # Race spécifique avec validation
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
        
        # Race générique
        if not entities.breed:
            generic_patterns = [r'poulets?', r'volailles?', r'chickens?', r'pollos?']
            for pattern in generic_patterns:
                match = re.search(pattern, message_lower, re.IGNORECASE)
                if match:
                    entities.breed = "Poulets (générique)"
                    entities.breed_type = "generic"
                    entities.breed_confidence = 0.3
                    break
        
        # Âge avec validation et conversion
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
                if entities.age_days <= 0 or entities.age_days > 365:
                    logger.warning(f"⚠️ [Basic] Âge suspect: {entities.age_days} jours")
                    entities.age_confidence = 0.3
                else:
                    entities.age_confidence = 0.8
                
                entities.age_last_updated = datetime.now()
                logger.debug(f"🔍 [Basic] Âge détecté: {entities.age_days}j ({entities.age_weeks}sem)")
                break
        
        # Poids avec validation et conversion automatique
        weight_patterns = [
            (r'(\d+(?:\.\d+)?)\s*g\b', 1, "grams"),
            (r'(\d+(?:\.\d+)?)\s*grammes?', 1, "grams"),
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
                    logger.info(f"✅ [Basic] Poids corrigé: {weight}g (était probablement en kg)")
                elif weight > 10000:  # Trop élevé
                    logger.warning(f"⚠️ [Basic] Poids suspect: {weight}g")
                    entities.weight_confidence = 0.3
                else:
                    entities.weight_confidence = 0.8
                
                entities.weight_grams = weight
                logger.debug(f"🔍 [Basic] Poids détecté: {weight}g")
                break
        
        # Mortalité avec validation
        mortality_patterns = [
            r'mortalité\s+(?:de\s+)?(\d+(?:\.\d+)?)%?',
            r'(\d+(?:\.\d+)?)%\s+mortalit[éy]',
            r'mortality\s+(?:of\s+)?(\d+(?:\.\d+)?)%?'
        ]
        
        for pattern in mortality_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                mortality = float(match.group(1))
                
                # Validation et correction
                if mortality < 0:
                    mortality = 0
                elif mortality > 100:
                    logger.warning(f"⚠️ [Basic] Mortalité > 100%: {mortality}%")
                    mortality = min(mortality, 100)
                    entities.mortality_confidence = 0.5
                else:
                    entities.mortality_confidence = 0.8
                
                entities.mortality_rate = mortality
                logger.debug(f"🔍 [Basic] Mortalité détectée: {mortality}%")
                break
        
        # Température avec validation et conversion
        temp_patterns = [
            r'(\d+(?:\.\d+)?)\s*°?c',
            r'température\s+(?:de\s+)?(\d+(?:\.\d+)?)',
            r'temperature\s+(?:of\s+)?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in temp_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                temp = float(match.group(1))
                
                # Conversion Fahrenheit vers Celsius si nécessaire
                if temp > 50:  # Probablement Fahrenheit
                    temp = (temp - 32) * 5/9
                    logger.info(f"✅ [Basic] Température convertie F→C: {temp:.1f}°C")
                
                # Validation plage réaliste
                if temp < 10 or temp > 45:
                    logger.warning(f"⚠️ [Basic] Température suspecte: {temp}°C")
                
                entities.temperature = round(temp, 1)
                logger.debug(f"🔍 [Basic] Température détectée: {temp}°C")
                break
        
        # Symptômes basiques avec nettoyage
        symptom_keywords = {
            "fr": ["diarrhée", "boiterie", "toux", "éternuements", "léthargie", "perte appétit", "mortalité"],
            "en": ["diarrhea", "lameness", "cough", "sneezing", "lethargy", "loss appetite", "mortality"],
            "es": ["diarrea", "cojera", "tos", "estornudos", "letargo", "pérdida apetito", "mortalidad"]
        }
        
        symptoms = symptom_keywords.get(language, symptom_keywords["fr"])
        detected_symptoms = []
        
        for symptom in symptoms:
            if symptom in message_lower:
                detected_symptoms.append(symptom.title())
        
        if detected_symptoms:
            entities.symptoms = list(set(detected_symptoms))  # Supprimer doublons
            logger.debug(f"🔍 [Basic] Symptômes détectés: {entities.symptoms}")
        
        # Calculer confiance globale
        confidence_scores = [
            entities.breed_confidence,
            entities.age_confidence,
            entities.weight_confidence,
            entities.mortality_confidence
        ]
        
        non_zero_scores = [s for s in confidence_scores if s > 0]
        entities.confidence_overall = sum(non_zero_scores) / len(non_zero_scores) if non_zero_scores else 0.0
        
        entities.extraction_success = entities.confidence_overall > 0.1
        
        return entities

    def add_message_to_conversation(
        self,
        conversation_id: str,
        user_id: str,
        message: str,
        role: str = "user",
        language: str = "fr",
        message_type: str = "text"
    ) -> IntelligentConversationContext:
        """🔵 AMÉLIORÉ: Ajoute un message avec gestion robuste des erreurs"""
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
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
                    extraction_retries=attempt,
                    validated=True
                )
                
                # Ajouter au contexte
                context.add_message(message_obj)
                
                # 🔵 PERSISTANCE FORCÉE
                try:
                    self._save_conversation_to_db(context)
                    self._save_message_to_db(message_obj)
                    
                    # Backup immédiat si critique
                    if context.conversation_urgency in ["high", "critical"]:
                        self._create_conversation_backup(context)
                        
                except Exception as save_error:
                    logger.error(f"❌ [Persistance] Erreur sauvegarde: {save_error}")
                    # Ne pas échouer pour une erreur de sauvegarde
                
                # Mettre en cache avec thread safety
                with self.cache_lock:
                    self.conversation_cache[conversation_id] = context
                    self._manage_cache_size()
                
                self.stats["total_messages"] += 1
                
                logger.info(f"💬 [Memory] Message ajouté: {conversation_id} ({len(context.messages)} msgs)")
                
                return context
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ [Memory] Tentative {attempt + 1} échouée: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
        
        # Si toutes les tentatives ont échoué, essayer de récupérer depuis backup
        logger.error(f"❌ [Memory] Toutes les tentatives échouées: {last_error}")
        
        # Tentative de récupération depuis backup
        backup_context = self._recover_from_backup(conversation_id)
        if backup_context:
            self.stats["backup_recoveries"] += 1
            logger.info(f"✅ [Recovery] Contexte récupéré depuis backup")
            return backup_context
        
        # Dernière option: créer un contexte minimal
        minimal_context = IntelligentConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
            language=language
        )
        
        logger.warning("⚠️ [Memory] Contexte minimal créé en fallback")
        return minimal_context

    def _recover_from_backup(self, conversation_id: str) -> Optional[IntelligentConversationContext]:
        """🔵 NOUVEAU: Récupère une conversation depuis les backups"""
        try:
            # Vérifier backup en mémoire d'abord
            if conversation_id in self.backup_cache:
                return self.backup_cache[conversation_id]
            
            # Chercher en base de données
            with self._get_db_connection() as conn:
                backup_row = conn.execute("""
                    SELECT backup_data FROM conversation_backups 
                    WHERE conversation_id = ? 
                    ORDER BY backup_timestamp DESC 
                    LIMIT 1
                """, (conversation_id,)).fetchone()
                
                if backup_row:
                    backup_data = json.loads(backup_row["backup_data"])
                    # Reconstruire le contexte depuis le backup
                    context = self._context_from_backup_data(backup_data)
                    if context:
                        context.cache_restored = True
                        return context
                        
        except Exception as e:
            logger.error(f"❌ [Recovery] Erreur récupération backup: {e}")
        
        return None

    def _context_from_backup_data(self, data: Dict[str, Any]) -> Optional[IntelligentConversationContext]:
        """🔵 NOUVEAU: Reconstruit un contexte depuis les données de backup"""
        try:
            # Reconstituir les entités consolidées
            consolidated_entities = IntelligentEntities()
            if data.get("consolidated_entities"):
                consolidated_entities = self._entities_from_dict(data["consolidated_entities"])
            
            # Reconstituer les messages
            messages = []
            for msg_data in data.get("messages", []):
                entities = None
                if msg_data.get("extracted_entities"):
                    entities = self._entities_from_dict(msg_data["extracted_entities"])
                
                message_obj = ConversationMessage(
                    id=msg_data["id"],
                    conversation_id=msg_data["conversation_id"],
                    user_id=msg_data["user_id"],
                    role=msg_data["role"],
                    message=msg_data["message"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    language=msg_data.get("language", "fr"),
                    message_type=msg_data.get("message_type", "text"),
                    extracted_entities=entities,
                    confidence_score=msg_data.get("confidence_score", 0.0),
                    processing_method=msg_data.get("processing_method", "basic")
                )
                messages.append(message_obj)
            
            # Reconstituer le contexte
            context = IntelligentConversationContext(
                conversation_id=data["conversation_id"],
                user_id=data["user_id"],
                messages=messages,
                consolidated_entities=consolidated_entities,
                language=data.get("language", "fr"),
                created_at=datetime.fromisoformat(data["created_at"]),
                last_activity=datetime.fromisoformat(data["last_activity"]),
                total_exchanges=data.get("total_exchanges", 0),
                conversation_topic=data.get("conversation_topic"),
                conversation_urgency=data.get("conversation_urgency"),
                problem_resolution_status=data.get("problem_resolution_status"),
                ai_enhanced=data.get("ai_enhanced", False),
                last_ai_analysis=datetime.fromisoformat(data["last_ai_analysis"]) if data.get("last_ai_analysis") else None,
                needs_clarification=data.get("needs_clarification", False),
                clarification_questions=data.get("clarification_questions", [])
            )
            
            return context
            
        except Exception as e:
            logger.error(f"❌ [Backup Recovery] Erreur reconstruction: {e}")
            return None

    def get_conversation_context(self, conversation_id: str) -> Optional[IntelligentConversationContext]:
        """🔵 AMÉLIORÉ: Récupère le contexte avec fallbacks multiples"""
        
        # Vérifier le cache d'abord avec thread safety
        with self.cache_lock:
            if conversation_id in self.conversation_cache:
                context = self.conversation_cache[conversation_id]
                context.cache_hits += 1
                self.stats["cache_hits"] += 1
                return context
        
        self.stats["cache_misses"] += 1
        
        # Charger depuis la DB avec retry
        max_db_retries = 3
        for attempt in range(max_db_retries):
            try:
                context = self._load_context_from_db(conversation_id)
                if context:
                    # Mettre en cache
                    with self.cache_lock:
                        self.conversation_cache[conversation_id] = context
                        self._manage_cache_size()
                    return context
                break  # Pas trouvé en DB, pas besoin de retry
                
            except Exception as e:
                logger.warning(f"⚠️ [DB Load] Tentative {attempt + 1} échouée: {e}")
                if attempt < max_db_retries - 1:
                    time.sleep(0.2 * (attempt + 1))
        
        # Fallback: essayer de récupérer depuis backup
        backup_context = self._recover_from_backup(conversation_id)
        if backup_context:
            self.stats["backup_recoveries"] += 1
            logger.info(f"✅ [Fallback] Contexte récupéré depuis backup")
            
            # Mettre en cache
            with self.cache_lock:
                self.conversation_cache[conversation_id] = backup_context
            
            return backup_context
        
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
                data_integrity_checked=bool(conv_row.get("data_integrity_checked", False))
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
                    extraction_retries=msg_row.get("extraction_retries", 0),
                    backup_saved=bool(msg_row.get("backup_saved", False)),
                    validated=bool(msg_row.get("validated", False))
                )
                
                context.messages.append(message_obj)
            
            return context

    def _entities_from_dict(self, data: Dict[str, Any]) -> IntelligentEntities:
        """Reconstruit les entités depuis un dictionnaire avec validation"""
        
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
        
        # Créer l'entité avec validation des champs
        valid_fields = {k: v for k, v in data.items() if k in IntelligentEntities.__dataclass_fields__}
        
        entities = IntelligentEntities(**valid_fields)
        return entities.validate_and_correct()

    def _save_conversation_to_db(self, context: IntelligentConversationContext):
        """🔵 AMÉLIORÉ: Sauvegarde avec gestion d'erreurs robuste"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self._get_db_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO conversations (
                            conversation_id, user_id, language, created_at, last_activity,
                            total_exchanges, consolidated_entities, conversation_topic,
                            conversation_urgency, problem_resolution_status, ai_enhanced,
                            last_ai_analysis, needs_clarification, clarification_questions,
                            confidence_overall, forced_backup, backup_timestamp, 
                            data_integrity_checked
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        context.conversation_id,
                        context.user_id,
                        context.language,
                        context.created_at.isoformat(),
                        context.last_activity.isoformat(),
                        context.total_exchanges,
                        json.dumps(context.consolidated_entities.to_dict()),
                        context.conversation_topic,
                        context.conversation_urgency,
                        context.problem_resolution_status,
                        context.ai_enhanced,
                        context.last_ai_analysis.isoformat() if context.last_ai_analysis else None,
                        context.needs_clarification,
                        json.dumps(context.clarification_questions),
                        context.consolidated_entities.confidence_overall,
                        context.forced_backup,
                        context.backup_timestamp.isoformat() if context.backup_timestamp else None,
                        context.data_integrity_checked
                    ))
                    conn.commit()
                break  # Succès
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"❌ [Save Conv] Échec final: {e}")
                    raise
                logger.warning(f"⚠️ [Save Conv] Retry {attempt + 1}: {e}")
                time.sleep(0.1 * (attempt + 1))

    def _save_message_to_db(self, message: ConversationMessage):
        """🔵 AMÉLIORÉ: Sauvegarde message avec retry"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self._get_db_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO conversation_messages (
                            id, conversation_id, user_id, role, message, timestamp,
                            language, message_type, extracted_entities, confidence_score,
                            processing_method, extraction_retries, backup_saved, validated
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
                        json.dumps(message.extracted_entities.to_dict()) if message.extracted_entities else None,
                        message.confidence_score,
                        message.processing_method,
                        message.extraction_retries,
                        message.backup_saved,
                        message.validated
                    ))
                    conn.commit()
                break
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"❌ [Save Msg] Échec final: {e}")
                    raise
                logger.warning(f"⚠️ [Save Msg] Retry {attempt + 1}: {e}")
                time.sleep(0.1 * (attempt + 1))

    def _manage_cache_size(self):
        """🔵 AMÉLIORÉ: Gestion cache avec backup préventif"""
        
        if len(self.conversation_cache) > self.cache_max_size:
            # Identifier les conversations à supprimer
            sorted_conversations = sorted(
                self.conversation_cache.items(),
                key=lambda x: x[1].last_activity
            )
            
            # Sauvegarder les conversations importantes avant suppression
            to_remove = sorted_conversations[:len(sorted_conversations) - self.cache_max_size//2]
            
            for conv_id, context in to_remove:
                # Backup si critique ou récent
                if (context.conversation_urgency in ["high", "critical"] or 
                    (datetime.now() - context.last_activity).total_seconds() < 3600):  # 1 heure
                    self._create_conversation_backup(context)
            
            # Garder seulement les plus récentes
            to_keep = sorted_conversations[-self.cache_max_size//2:]
            self.conversation_cache = dict(to_keep)

    def get_context_for_clarification(self, conversation_id: str) -> Dict[str, Any]:
        """Retourne le contexte optimisé pour les clarifications avec fallback"""
        
        context = self.get_conversation_context(conversation_id)
        if not context:
            return {
                "error": "Context not found",
                "fallback_available": conversation_id in self.backup_cache
            }
        
        return context.get_context_for_clarification()

    def get_context_for_rag(self, conversation_id: str, max_chars: int = 500) -> str:
        """Retourne le contexte optimisé pour le RAG avec fallback"""
        
        context = self.get_conversation_context(conversation_id)
        if not context:
            return ""
        
        return context.get_context_for_rag(max_chars)

    def cleanup_expired_conversations(self):
        """🔵 AMÉLIORÉ: Nettoie avec backup préventif des conversations importantes"""
        
        cutoff_time = datetime.now() - timedelta(hours=self.context_expiry_hours)
        
        try:
            with self._get_db_connection() as conn:
                # Identifier les conversations à supprimer
                expiring_rows = conn.execute("""
                    SELECT conversation_id, conversation_urgency, total_exchanges 
                    FROM conversations 
                    WHERE last_activity < ?
                """, (cutoff_time.isoformat(),)).fetchall()
                
                # Backup préventif des conversations importantes
                important_conversations = [
                    row["conversation_id"] for row in expiring_rows
                    if row["conversation_urgency"] in ["high", "critical"] or row["total_exchanges"] > 10
                ]
                
                for conv_id in important_conversations:
                    context = self.get_conversation_context(conv_id)
                    if context:
                        self._create_conversation_backup(context)
                        logger.info(f"🔵 [Cleanup] Backup préventif: {conv_id}")
                
                # Supprimer les messages expirés
                conn.execute("""
                    DELETE FROM conversation_messages 
                    WHERE conversation_id IN (
                        SELECT conversation_id FROM conversations 
                        WHERE last_activity < ?
                    )
                """, (cutoff_time.isoformat(),))
                
                # Supprimer les conversations expirées
                result = conn.execute("""
                    DELETE FROM conversations 
                    WHERE last_activity < ?
                """, (cutoff_time.isoformat(),))
                
                deleted_count = result.rowcount
                conn.commit()
                
                # Nettoyer le cache
                with self.cache_lock:
                    expired_ids = [
                        conv_id for conv_id, context in self.conversation_cache.items()
                        if context.last_activity < cutoff_time
                    ]
                    
                    for conv_id in expired_ids:
                        del self.conversation_cache[conv_id]
                
                logger.info(f"🗑️ [Cleanup] {deleted_count} conversations expirées supprimées, {len(important_conversations)} sauvegardées")
                
        except Exception as e:
            logger.error(f"❌ [Cleanup] Erreur nettoyage: {e}")

    def get_conversation_memory_stats(self) -> Dict[str, Any]:
        """🔵 AMÉLIORÉ: Statistiques étendues avec info robustesse"""
        
        try:
            with self._get_db_connection() as conn:
                # Compter les conversations actives
                active_conversations = conn.execute("""
                    SELECT COUNT(*) as count FROM conversations 
                    WHERE last_activity > ?
                """, ((datetime.now() - timedelta(hours=24)).isoformat(),)).fetchone()["count"]
                
                # Compter les messages
                total_messages = conn.execute("SELECT COUNT(*) as count FROM conversation_messages").fetchone()["count"]
                
                # Compter les backups
                total_backups = conn.execute("SELECT COUNT(*) as count FROM conversation_backups").fetchone()["count"]
                
                # Conversations par urgence
                urgency_stats = {}
                for urgency in ["low", "medium", "high", "critical"]:
                    count = conn.execute("""
                        SELECT COUNT(*) as count FROM conversations 
                        WHERE conversation_urgency = ? AND last_activity > ?
                    """, (urgency, (datetime.now() - timedelta(hours=24)).isoformat())).fetchone()["count"]
                    urgency_stats[urgency] = count
        
        except Exception as e:
            logger.error(f"❌ [Stats] Erreur: {e}")
            active_conversations = 0
            total_messages = 0
            total_backups = 0
            urgency_stats = {}
        
        return {
            "enabled": True,
            "ai_enhancement_enabled": self.ai_enhancement_enabled,
            "ai_enhancement_model": self.ai_enhancement_model,
            "database_path": self.db_path,
            "max_messages_in_memory": self.max_messages_in_memory,
            "context_expiry_hours": self.context_expiry_hours,
            "cache_size": len(self.conversation_cache),
            "cache_max_size": self.cache_max_size,
            
            # 🔵 ROBUSTESSE - Statistiques étendues
            "backup_enabled": self.backup_enabled,
            "backup_cache_size": len(self.backup_cache),
            "ai_retry_attempts": self.ai_retry_attempts,
            "force_backup_interval": self.force_backup_interval,
            
            # Statistiques d'usage
            "active_conversations_24h": active_conversations,
            "total_messages": total_messages,
            "total_backups": total_backups,
            "conversations_by_urgency": urgency_stats,
            
            # Statistiques système robustes
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "ai_enhancements": self.stats["ai_enhancements"],
            "ai_failures": self.stats["ai_failures"],
            "ai_retries": self.stats["ai_retries"],
            "backup_recoveries": self.stats["backup_recoveries"],
            "data_corrections": self.stats["data_corrections"],
            "cache_hit_ratio": self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"]) if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0.0,
            "ai_success_ratio": self.stats["ai_enhancements"] / (self.stats["ai_enhancements"] + self.stats["ai_failures"]) if (self.stats["ai_enhancements"] + self.stats["ai_failures"]) > 0 else 0.0,
            
            # Capacités robustes
            "intelligent_entity_extraction": True,
            "contextual_reasoning": True,
            "urgency_detection": True,
            "ai_powered": OPENAI_AVAILABLE and self.ai_enhancement_enabled,
            "backup_system": self.backup_enabled,
            "automatic_recovery": True,
            "data_validation": True,
            "thread_safe": True
        }

# ==================== INSTANCE GLOBALE ROBUSTE ====================

# Configuration depuis l'environnement
db_path = os.getenv('INTELLIGENT_CONVERSATION_MEMORY_DB_PATH', 'data/intelligent_conversation_memory.db')

# Instance singleton robuste
intelligent_conversation_memory = IntelligentConversationMemory(db_path)

# ==================== FONCTIONS UTILITAIRES ROBUSTES ====================

def add_message_to_conversation(
    conversation_id: str,
    user_id: str,
    message: str,
    role: str = "user",
    language: str = "fr",
    message_type: str = "text"
) -> IntelligentConversationContext:
    """🔵 ROBUSTE: Ajoute un message avec fallbacks multiples"""
    return intelligent_conversation_memory.add_message_to_conversation(
        conversation_id, user_id, message, role, language, message_type
    )

def get_conversation_context(conversation_id: str) -> Optional[IntelligentConversationContext]:
    """🔵 ROBUSTE: Récupère le contexte avec recovery automatique"""
    return intelligent_conversation_memory.get_conversation_context(conversation_id)

def get_context_for_clarification(conversation_id: str) -> Dict[str, Any]:
    """🔵 ROBUSTE: Contexte clarification avec fallback"""
    return intelligent_conversation_memory.get_context_for_clarification(conversation_id)

def get_context_for_rag(conversation_id: str, max_chars: int = 500) -> str:
    """🔵 ROBUSTE: Contexte RAG avec validation"""
    return intelligent_conversation_memory.get_context_for_rag(conversation_id, max_chars)

def get_conversation_memory_stats() -> Dict[str, Any]:
    """🔵 ROBUSTE: Statistiques complètes avec métriques robustesse"""
    return intelligent_conversation_memory.get_conversation_memory_stats()

def cleanup_expired_conversations():
    """🔵 ROBUSTE: Nettoyage avec backup préventif"""
    intelligent_conversation_memory.cleanup_expired_conversations()

# ==================== LOGGING DE DÉMARRAGE ROBUSTE ====================

logger.info("🔵" * 60)
logger.info("🧠 [IntelligentConversationMemory] Système ROBUSTE initialisé")
logger.info(f"📊 [Stats] {intelligent_conversation_memory.get_conversation_memory_stats()}")
logger.info("✅ [FONCTIONNALITÉS ROBUSTES]:")
logger.info("   - 🤖 Extraction IA avec retry automatique")
logger.info("   - 🔄 Fallback robuste si IA échoue") 
logger.info("   - 💾 Backup automatique et récupération")
logger.info("   - 🛡️ Validation et correction automatique des données")
logger.info("   - 🧵 Thread safety avec locks")
logger.info("   - 📊 Persistance forcée des clarifications")
logger.info("   - 🔄 Cache conversationnel renforcé")
logger.info("   - ⚡ Retry intelligent avec backoff")
logger.info("   - 🗄️ Backup préventif conversations importantes")
logger.info("   - 📈 Métriques robustesse détaillées")
logger.info("   - ✅ TOUTES les fonctions originales préservées")
logger.info("   - 🔧 Validation et correction automatique (°F→°C, kg→g)")
logger.info("   - 📋 Gestion intelligente entités avec fusion")
logger.info("   - 🎯 Contexte optimisé pour RAG et clarifications")
logger.info("   - 🔒 Thread safety complet avec locks")
logger.info("   - 📊 Statistiques étendues avec métriques de qualité")
logger.info("🔵" * 60)