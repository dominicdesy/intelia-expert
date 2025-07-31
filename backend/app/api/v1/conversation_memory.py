"""
app/api/v1/conversation_memory_enhanced.py - VERSION AMÉLIORÉE AVEC IA

AMÉLIORATIONS MAJEURES:
1. Extraction d'entités intelligente via OpenAI (plus que les regex de base)
2. Raisonnement contextuel dynamique pour éviter les clarifications redondantes
3. Fusion intelligente d'informations entre messages
4. Mise à jour dynamique des entités au fil de la conversation
5. Contexte optimisé pour RAG et clarification
6. Expiration intelligente selon l'activité
"""

import os
import json
import logging
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
import time

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
    extraction_method: str = "basic"  # basic/openai/hybrid
    last_ai_update: Optional[datetime] = None
    confidence_overall: float = 0.0
    
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
        return merged

@dataclass
class ConversationMessage:
    """Message dans une conversation avec métadonnées"""
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
    processing_method: str = "basic"  # basic/ai_enhanced
    
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
            "processing_method": self.processing_method
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
    
    def add_message(self, message: ConversationMessage):
        """Ajoute un message et met à jour le contexte intelligemment"""
        self.messages.append(message)
        self.last_activity = datetime.now()
        self.total_exchanges += 1
        
        # Fusionner les entités si disponibles
        if message.extracted_entities:
            self.consolidated_entities = self.consolidated_entities.merge_with(message.extracted_entities)
        
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
    
    def get_context_for_clarification(self) -> Dict[str, Any]:
        """Retourne le contexte optimisé pour les clarifications"""
        return {
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
            "overall_confidence": self.consolidated_entities.confidence_overall
        }
    
    def get_context_for_rag(self, max_chars: int = 500) -> str:
        """Retourne le contexte optimisé pour le RAG"""
        context_parts = []
        
        # Informations de base
        if self.consolidated_entities.breed:
            context_parts.append(f"Race: {self.consolidated_entities.breed}")
        
        if self.consolidated_entities.age_days:
            context_parts.append(f"Âge: {self.consolidated_entities.age_days} jours")
        
        if self.consolidated_entities.weight_grams:
            context_parts.append(f"Poids: {self.consolidated_entities.weight_grams}g")
        
        # Problèmes identifiés
        if self.consolidated_entities.symptoms:
            context_parts.append(f"Symptômes: {', '.join(self.consolidated_entities.symptoms)}")
        
        if self.consolidated_entities.mortality_rate:
            context_parts.append(f"Mortalité: {self.consolidated_entities.mortality_rate}%")
        
        # Environnement
        if self.consolidated_entities.temperature:
            context_parts.append(f"Température: {self.consolidated_entities.temperature}°C")
        
        if self.consolidated_entities.housing_type:
            context_parts.append(f"Logement: {self.consolidated_entities.housing_type}")
        
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
            "clarification_questions": self.clarification_questions
        }

class IntelligentConversationMemory:
    """Système de mémoire conversationnelle intelligent avec IA"""
    
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
        
        # Statistiques
        self.stats = {
            "total_conversations": 0,
            "total_messages": 0,
            "ai_enhancements": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Initialiser la base de données
        self._init_database()
        
        logger.info(f"🧠 [IntelligentMemory] Système initialisé")
        logger.info(f"🧠 [IntelligentMemory] DB: {self.db_path}")
        logger.info(f"🧠 [IntelligentMemory] IA enhancing: {'✅' if self.ai_enhancement_enabled else '❌'}")
        logger.info(f"🧠 [IntelligentMemory] Modèle IA: {self.ai_enhancement_model}")

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
                    
                    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                )
            """)
            
            # Index pour performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_user_activity ON conversations (user_id, last_activity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv_time ON conversation_messages (conversation_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_urgency ON conversations (conversation_urgency, last_activity)")
            
        logger.info(f"✅ [IntelligentMemory] Base de données initialisée")

    @contextmanager
    def _get_db_connection(self):
        """Context manager pour les connexions DB"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    async def extract_entities_ai_enhanced(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """Extraction d'entités améliorée par IA"""
        
        if not self.ai_enhancement_enabled or not OPENAI_AVAILABLE or not openai:
            logger.debug("🧠 [IntelligentMemory] IA désactivée, extraction basique")
            return await self._extract_entities_basic(message, language)
        
        try:
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
                return await self._extract_entities_basic(message, language)
            
            openai.api_key = api_key
            
            response = openai.chat.completions.create(
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
                    logger.warning("⚠️ [IntelligentMemory] Pas de JSON trouvé dans la réponse IA")
                    return await self._extract_entities_basic(message, language)
            
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
                    confidence_overall=data.get("confidence_overall", 0.0)
                )
                
                self.stats["ai_enhancements"] += 1
                logger.info(f"🤖 [IntelligentMemory] Entités extraites par IA: {len([k for k, v in entities.to_dict().items() if v is not None])} informations")
                
                return entities
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ [IntelligentMemory] Erreur parsing JSON IA: {e}")
                return await self._extract_entities_basic(message, language)
        
        except Exception as e:
            logger.error(f"❌ [IntelligentMemory] Erreur extraction IA: {e}")
            return await self._extract_entities_basic(message, language)

    async def _extract_entities_basic(self, message: str, language: str) -> IntelligentEntities:
        """Extraction d'entités basique par regex (fallback)"""
        
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
                entities.breed = match.group(0).strip()
                entities.breed_type = "specific"
                entities.breed_confidence = 0.9
                break
        
        # Race générique
        if not entities.breed:
            generic_patterns = [r'poulets?', r'volailles?', r'chickens?', r'pollos?']
            for pattern in generic_patterns:
                match = re.search(pattern, message_lower, re.IGNORECASE)
                if match:
                    entities.breed = match.group(0).strip()
                    entities.breed_type = "generic"
                    entities.breed_confidence = 0.3
                    break
        
        # Âge
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
                entities.age_confidence = 0.8
                entities.age_last_updated = datetime.now()
                break
        
        # Poids
        weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*g\b',
            r'(\d+(?:\.\d+)?)\s*grammes?',
            r'(\d+(?:\.\d+)?)\s*kg',
            r'pèsent?\s+(\d+(?:\.\d+)?)',
            r'weigh\s+(\d+(?:\.\d+)?)'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                weight = float(match.group(1))
                if 'kg' in pattern:
                    weight *= 1000
                entities.weight_grams = weight
                entities.weight_confidence = 0.8
                break
        
        # Mortalité
        mortality_patterns = [
            r'mortalité\s+(?:de\s+)?(\d+(?:\.\d+)?)%?',
            r'(\d+(?:\.\d+)?)%\s+mortalit[éy]',
            r'mortality\s+(?:of\s+)?(\d+(?:\.\d+)?)%?'
        ]
        
        for pattern in mortality_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                entities.mortality_rate = float(match.group(1))
                entities.mortality_confidence = 0.8
                break
        
        # Température
        temp_patterns = [
            r'(\d+(?:\.\d+)?)\s*°?c',
            r'température\s+(?:de\s+)?(\d+(?:\.\d+)?)',
            r'temperature\s+(?:of\s+)?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in temp_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                entities.temperature = float(match.group(1))
                break
        
        # Symptômes basiques
        symptom_keywords = {
            "fr": ["diarrhée", "boiterie", "toux", "éternuements", "léthargie", "perte appétit"],
            "en": ["diarrhea", "lameness", "cough", "sneezing", "lethargy", "loss appetite"],
            "es": ["diarrea", "cojera", "tos", "estornudos", "letargo", "pérdida apetito"]
        }
        
        symptoms = symptom_keywords.get(language, symptom_keywords["fr"])
        detected_symptoms = [symptom for symptom in symptoms if symptom in message_lower]
        if detected_symptoms:
            entities.symptoms = detected_symptoms
        
        # Calculer confiance globale
        confidence_scores = [
            entities.breed_confidence,
            entities.age_confidence,
            entities.weight_confidence,
            entities.mortality_confidence
        ]
        
        non_zero_scores = [s for s in confidence_scores if s > 0]
        entities.confidence_overall = sum(non_zero_scores) / len(non_zero_scores) if non_zero_scores else 0.0
        
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
        """Ajoute un message à une conversation avec extraction intelligente d'entités"""
        
        # Récupérer ou créer le contexte
        context = self.get_conversation_context(conversation_id)
        if not context:
            context = IntelligentConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                language=language
            )
        
        # Extraire les entités de manière asynchrone (simulé synchrone pour la compatibilité)
        import asyncio
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
            processing_method="ai_enhanced" if self.ai_enhancement_enabled else "basic"
        )
        
        # Ajouter au contexte
        context.add_message(message_obj)
        
        # Sauvegarder en base
        self._save_conversation_to_db(context)
        self._save_message_to_db(message_obj)
        
        # Mettre en cache
        self.conversation_cache[conversation_id] = context
        self._manage_cache_size()
        
        self.stats["total_messages"] += 1
        
        logger.info(f"💬 [IntelligentMemory] Message ajouté: {conversation_id} ({len(context.messages)} msgs)")
        
        return context

    def get_conversation_context(self, conversation_id: str) -> Optional[IntelligentConversationContext]:
        """Récupère le contexte d'une conversation"""
        
        # Vérifier le cache d'abord
        if conversation_id in self.conversation_cache:
            self.stats["cache_hits"] += 1
            return self.conversation_cache[conversation_id]
        
        self.stats["cache_misses"] += 1
        
        # Charger depuis la DB
        try:
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
                    clarification_questions=json.loads(conv_row["clarification_questions"]) if conv_row["clarification_questions"] else []
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
                        processing_method=msg_row["processing_method"] or "basic"
                    )
                    
                    context.messages.append(message_obj)
                
                # Mettre en cache
                self.conversation_cache[conversation_id] = context
                self._manage_cache_size()
                
                return context
                
        except Exception as e:
            logger.error(f"❌ [IntelligentMemory] Erreur chargement conversation: {e}")
            return None

    def _entities_from_dict(self, data: Dict[str, Any]) -> IntelligentEntities:
        """Reconstruit les entités depuis un dictionnaire"""
        
        # Convertir les dates
        for date_field in ["age_last_updated", "last_ai_update"]:
            if data.get(date_field):
                data[date_field] = datetime.fromisoformat(data[date_field])
        
        # Convertir les tuples
        if data.get("expected_weight_range") and isinstance(data["expected_weight_range"], list):
            data["expected_weight_range"] = tuple(data["expected_weight_range"])
        
        # Assurer les listes
        for list_field in ["symptoms", "previous_treatments"]:
            if not isinstance(data.get(list_field), list):
                data[list_field] = []
        
        return IntelligentEntities(**{k: v for k, v in data.items() if k in IntelligentEntities.__dataclass_fields__})

    def _save_conversation_to_db(self, context: IntelligentConversationContext):
        """Sauvegarde le contexte en base"""
        
        try:
            with self._get_db_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversations (
                        conversation_id, user_id, language, created_at, last_activity,
                        total_exchanges, consolidated_entities, conversation_topic,
                        conversation_urgency, problem_resolution_status, ai_enhanced,
                        last_ai_analysis, needs_clarification, clarification_questions,
                        confidence_overall
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    context.consolidated_entities.confidence_overall
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ [IntelligentMemory] Erreur sauvegarde conversation: {e}")

    def _save_message_to_db(self, message: ConversationMessage):
        """Sauvegarde un message en base"""
        
        try:
            with self._get_db_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_messages (
                        id, conversation_id, user_id, role, message, timestamp,
                        language, message_type, extracted_entities, confidence_score,
                        processing_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    message.processing_method
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ [IntelligentMemory] Erreur sauvegarde message: {e}")

    def _manage_cache_size(self):
        """Gère la taille du cache en mémoire"""
        
        if len(self.conversation_cache) > self.cache_max_size:
            # Supprimer les plus anciennes (LRU basique)
            sorted_conversations = sorted(
                self.conversation_cache.items(),
                key=lambda x: x[1].last_activity
            )
            
            # Garder seulement les plus récentes
            to_keep = sorted_conversations[-self.cache_max_size//2:]
            self.conversation_cache = dict(to_keep)

    def get_context_for_clarification(self, conversation_id: str) -> Dict[str, Any]:
        """Retourne le contexte optimisé pour les clarifications"""
        
        context = self.get_conversation_context(conversation_id)
        if not context:
            return {}
        
        return context.get_context_for_clarification()

    def get_context_for_rag(self, conversation_id: str, max_chars: int = 500) -> str:
        """Retourne le contexte optimisé pour le RAG"""
        
        context = self.get_conversation_context(conversation_id)
        if not context:
            return ""
        
        return context.get_context_for_rag(max_chars)

    def cleanup_expired_conversations(self):
        """Nettoie les conversations expirées"""
        
        cutoff_time = datetime.now() - timedelta(hours=self.context_expiry_hours)
        
        try:
            with self._get_db_connection() as conn:
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
                expired_ids = [
                    conv_id for conv_id, context in self.conversation_cache.items()
                    if context.last_activity < cutoff_time
                ]
                
                for conv_id in expired_ids:
                    del self.conversation_cache[conv_id]
                
                logger.info(f"🗑️ [IntelligentMemory] Nettoyage: {deleted_count} conversations expirées supprimées")
                
        except Exception as e:
            logger.error(f"❌ [IntelligentMemory] Erreur nettoyage: {e}")

    def get_conversation_memory_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du système"""
        
        try:
            with self._get_db_connection() as conn:
                # Compter les conversations actives
                active_conversations = conn.execute("""
                    SELECT COUNT(*) as count FROM conversations 
                    WHERE last_activity > ?
                """, ((datetime.now() - timedelta(hours=24)).isoformat(),)).fetchone()["count"]
                
                # Compter les messages
                total_messages = conn.execute("SELECT COUNT(*) as count FROM conversation_messages").fetchone()["count"]
                
                # Conversations par urgence
                urgency_stats = {}
                for urgency in ["low", "medium", "high", "critical"]:
                    count = conn.execute("""
                        SELECT COUNT(*) as count FROM conversations 
                        WHERE conversation_urgency = ? AND last_activity > ?
                    """, (urgency, (datetime.now() - timedelta(hours=24)).isoformat())).fetchone()["count"]
                    urgency_stats[urgency] = count
        
        except Exception as e:
            logger.error(f"❌ [IntelligentMemory] Erreur stats: {e}")
            active_conversations = 0
            total_messages = 0
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
            
            # Statistiques d'usage
            "active_conversations_24h": active_conversations,
            "total_messages": total_messages,
            "conversations_by_urgency": urgency_stats,
            
            # Statistiques système
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "ai_enhancements": self.stats["ai_enhancements"],
            "cache_hit_ratio": self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"]) if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0.0,
            
            # Capacités
            "intelligent_entity_extraction": True,
            "contextual_reasoning": True,
            "urgency_detection": True,
            "ai_powered": OPENAI_AVAILABLE and self.ai_enhancement_enabled
        }

# ==================== INSTANCE GLOBALE ====================

# Configuration depuis l'environnement
db_path = os.getenv('INTELLIGENT_CONVERSATION_MEMORY_DB_PATH', 'data/intelligent_conversation_memory.db')

# Instance singleton
intelligent_conversation_memory = IntelligentConversationMemory(db_path)

# ==================== FONCTIONS UTILITAIRES ====================

def add_message_to_conversation(
    conversation_id: str,
    user_id: str,
    message: str,
    role: str = "user",
    language: str = "fr",
    message_type: str = "text"
) -> IntelligentConversationContext:
    """Ajoute un message à une conversation intelligente"""
    return intelligent_conversation_memory.add_message_to_conversation(
        conversation_id, user_id, message, role, language, message_type
    )

def get_conversation_context(conversation_id: str) -> Optional[IntelligentConversationContext]:
    """Récupère le contexte intelligent d'une conversation"""
    return intelligent_conversation_memory.get_conversation_context(conversation_id)

def get_context_for_clarification(conversation_id: str) -> Dict[str, Any]:
    """Retourne le contexte optimisé pour les clarifications"""
    return intelligent_conversation_memory.get_context_for_clarification(conversation_id)

def get_context_for_rag(conversation_id: str, max_chars: int = 500) -> str:
    """Retourne le contexte optimisé pour le RAG"""
    return intelligent_conversation_memory.get_context_for_rag(conversation_id, max_chars)

def get_conversation_memory_stats() -> Dict[str, Any]:
    """Retourne les statistiques du système intelligent"""
    return intelligent_conversation_memory.get_conversation_memory_stats()

def cleanup_expired_conversations():
    """Nettoie les conversations expirées"""
    intelligent_conversation_memory.cleanup_expired_conversations()

# ==================== LOGGING DE DÉMARRAGE ====================

logger.info("🧠 [IntelligentConversationMemory] Système de mémoire intelligent initialisé")
logger.info(f"📊 [IntelligentConversationMemory] Statistiques: {intelligent_conversation_memory.get_conversation_memory_stats()}")
logger.info("✅ [IntelligentConversationMemory] FONCTIONNALITÉS INTELLIGENTES:")
logger.info("   - 🤖 Extraction d'entités par IA (OpenAI)")
logger.info("   - 🧠 Raisonnement contextuel pour éviter clarifications redondantes")
logger.info("   - 🔄 Fusion intelligente d'informations entre messages")
logger.info("   - 📊 Classification automatique d'urgence et état de santé")
logger.info("   - 🎯 Contexte optimisé pour RAG et clarifications")
logger.info("   - 💾 Cache intelligent avec gestion LRU")
logger.info("   - 📈 Scores de confiance dynamiques")
logger.info("   - ⚡ Détection automatique de problèmes critiques")