"""
app/api/v1/question_clarification_system.py - SYSTÈME PRINCIPAL DE CLARIFICATION

Contient:
- EnhancedQuestionClarificationSystem (classe principale)
- Extraction d'entités intelligente
- Analyse complète des questions
- Interface publique + logging
- Identification des entités critiques

COMPATIBLE: Préserve tous les imports existants
"""

import os
import re
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Imports des modules séparés
from .clarification_entities import (
    ExtractedEntities, ClarificationResult, ClarificationMode, ClarificationState
)
from .clarification_generators import QuestionGenerator

# Import des settings Intelia
try:
    from app.config.settings import settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False
    settings = None

# Import OpenAI sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)

# ==================== CONSTANTES ENTITÉS CRITIQUES ====================

# Entités considérées comme critiques pour les réponses vétérinaires
CRITICAL_ENTITIES = [
    "breed",        # Race/souche (essentiel pour protocoles spécifiques)
    "age",          # Âge (critique pour nutrition, vaccination, traitements)
    "sex",          # Sexe (important pour certains protocoles)
    "symptoms",     # Symptômes (essentiel pour diagnostic)
    "environment",  # Environnement (température, humidité, logement)
    "feed",         # Alimentation (critique pour nutrition et performance)
    "flock_size",   # Taille du troupeau (important pour gestion)
    "mortality_rate" # Taux de mortalité (critique pour urgences)
]

# Mappage des entités vers les attributs ExtractedEntities
ENTITY_ATTRIBUTE_MAPPING = {
    "breed": ["breed", "breed_type"],
    "age": ["age_days", "age_weeks"],
    "sex": ["sex"],
    "symptoms": ["symptoms"],
    "environment": ["temperature", "humidity", "housing_type"],
    "feed": ["feed_type"],
    "flock_size": ["flock_size"],
    "mortality_rate": ["mortality_rate"]
}

# Entités critiques par type de question
CRITICAL_ENTITIES_BY_QUESTION_TYPE = {
    "growth": ["breed", "age", "feed"],
    "weight": ["breed", "age", "feed"],
    "mortality": ["breed", "age", "symptoms", "mortality_rate"],
    "health": ["breed", "age", "symptoms"],
    "temperature": ["age", "environment"],
    "feeding": ["breed", "age", "feed"],
    "environment": ["age", "environment"],
    "performance": ["breed", "age", "feed", "environment"],
    "laying": ["breed", "age", "feed", "environment"],
    "general": ["breed", "age"]
}

class EnhancedQuestionClarificationSystem:
    """
    Système de clarification intelligent AMÉLIORÉ avec validation GPT robuste intégrée + reconnaissance souches + entités critiques
    """
    
    def __init__(self):
        """Initialise le système avec configuration améliorée"""
        
        if SETTINGS_AVAILABLE and settings:
            self.enabled = getattr(settings, 'clarification_system_enabled', True)
            self.model = getattr(settings, 'clarification_model', 'gpt-4o-mini')
            self.timeout = getattr(settings, 'clarification_timeout', 25)
            self.max_questions = getattr(settings, 'clarification_max_questions', 3)
            self.min_question_length = getattr(settings, 'clarification_min_length', 15)
            self.log_all_clarifications = getattr(settings, 'clarification_log_all', True)
            self.confidence_threshold = getattr(settings, 'clarification_confidence_threshold', 0.7)
            
            self.clarification_mode = ClarificationMode(getattr(settings, 'clarification_mode', 'adaptive'))
            self.smart_entity_extraction = getattr(settings, 'smart_entity_extraction', True)
            self.auto_reprocess_after_clarification = getattr(settings, 'auto_reprocess_after_clarification', True)
            self.adaptive_question_count = getattr(settings, 'adaptive_question_count', True)
            
            self.enable_semantic_dynamic = getattr(settings, 'enable_semantic_dynamic_clarification', True)
            self.semantic_dynamic_max_questions = getattr(settings, 'semantic_dynamic_max_questions', 4)
            
            # Configuration validation GPT robuste
            self.enable_question_validation = getattr(settings, 'enable_question_validation', True)
            self.validation_threshold = getattr(settings, 'validation_threshold', 0.5)
            self.enable_intelligent_fallback = getattr(settings, 'enable_intelligent_fallback', True)
            
            # Configuration reconnaissance souches
            self.enable_breed_normalization = getattr(settings, 'enable_breed_normalization', True)
            self.enable_sex_inference = getattr(settings, 'enable_sex_inference', True)
            
            # Configuration entités critiques
            self.enable_critical_entity_analysis = getattr(settings, 'enable_critical_entity_analysis', True)
            self.critical_entities_threshold = getattr(settings, 'critical_entities_threshold', 0.8)
        else:
            self.enabled = os.getenv('ENABLE_CLARIFICATION_SYSTEM', 'true').lower() == 'true'
            self.model = os.getenv('CLARIFICATION_MODEL', 'gpt-4o-mini')
            self.timeout = int(os.getenv('CLARIFICATION_TIMEOUT', '25'))
            self.max_questions = int(os.getenv('CLARIFICATION_MAX_QUESTIONS', '3'))
            self.min_question_length = int(os.getenv('CLARIFICATION_MIN_LENGTH', '15'))
            self.log_all_clarifications = os.getenv('LOG_ALL_CLARIFICATIONS', 'true').lower() == 'true'
            self.confidence_threshold = float(os.getenv('CLARIFICATION_CONFIDENCE_THRESHOLD', '0.7'))
            
            self.clarification_mode = ClarificationMode(os.getenv('CLARIFICATION_MODE', 'adaptive'))
            self.smart_entity_extraction = os.getenv('SMART_ENTITY_EXTRACTION', 'true').lower() == 'true'
            self.auto_reprocess_after_clarification = os.getenv('AUTO_REPROCESS_AFTER_CLARIFICATION', 'true').lower() == 'true'
            self.adaptive_question_count = os.getenv('ADAPTIVE_QUESTION_COUNT', 'true').lower() == 'true'
            
            self.enable_semantic_dynamic = os.getenv('ENABLE_SEMANTIC_DYNAMIC_CLARIFICATION', 'true').lower() == 'true'
            self.semantic_dynamic_max_questions = int(os.getenv('SEMANTIC_DYNAMIC_MAX_QUESTIONS', '4'))
            
            # Configuration validation GPT robuste
            self.enable_question_validation = os.getenv('ENABLE_QUESTION_VALIDATION', 'true').lower() == 'true'
            self.validation_threshold = float(os.getenv('VALIDATION_THRESHOLD', '0.5'))
            self.enable_intelligent_fallback = os.getenv('ENABLE_INTELLIGENT_FALLBACK', 'true').lower() == 'true'
            
            # Configuration reconnaissance souches
            self.enable_breed_normalization = os.getenv('ENABLE_BREED_NORMALIZATION', 'true').lower() == 'true'
            self.enable_sex_inference = os.getenv('ENABLE_SEX_INFERENCE', 'true').lower() == 'true'
            
            # Configuration entités critiques
            self.enable_critical_entity_analysis = os.getenv('ENABLE_CRITICAL_ENTITY_ANALYSIS', 'true').lower() == 'true'
            self.critical_entities_threshold = float(os.getenv('CRITICAL_ENTITIES_THRESHOLD', '0.8'))
        
        # Initialiser le générateur de questions
        self.question_generator = QuestionGenerator(
            model=self.model, 
            timeout=self.timeout, 
            max_questions=self.semantic_dynamic_max_questions
        )
        
        self._init_patterns()
        self._init_enhanced_prompts()
        self._init_clarification_logger()
        
        # Log de démarrage
        logger.info("✅ [EnhancedQuestionClarificationSystem] READY: Agent de clarification opérationnel!")
        logger.info(f"🔧 [Enhanced Clarification] Mode: {self.clarification_mode.value}")
        logger.info(f"🔧 [Enhanced Clarification] Validation GPT robuste: {'✅' if self.enable_question_validation else '❌'}")
        logger.info(f"🆕 [Breed Recognition] Normalisation souches: {'✅' if self.enable_breed_normalization else '❌'}")
        logger.info(f"🎯 [Critical Entities] Analyse entités critiques: {'✅' if self.enable_critical_entity_analysis else '❌'}")
        logger.info(f"📊 [Critical Entities] Entités critiques définies: {len(CRITICAL_ENTITIES)} ({', '.join(CRITICAL_ENTITIES)})")

    def _init_patterns(self):
        """Patterns de détection améliorés avec reconnaissance souches"""
        
        # Races spécifiques avec nouvelles souches pondeuses
        self.specific_breed_patterns = {
            "fr": [
                # Poulets de chair
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro',
                
                # Poules pondeuses
                r'lohmann(?:\s*lsl)?(?:\s*-?\s*lite)?', r'lsl\s*-?\s*lite?',
                r'bovans\s*(?:brown|blanc|white)?', 
                r'hisex\s*(?:brown|blanc|white)?',
                r'isa\s*(?:brown|blanc|white)?',
                r'hyline\s*(?:brown|white)?'
            ],
            "en": [
                # Poulets de chair
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro',
                
                # Poules pondeuses
                r'lohmann(?:\s*lsl)?(?:\s*-?\s*lite)?', r'lsl\s*-?\s*lite?',
                r'bovans\s*(?:brown|white)?', 
                r'hisex\s*(?:brown|white)?',
                r'isa\s*(?:brown|white)?',
                r'hyline\s*(?:brown|white)?'
            ],
            "es": [
                # Poulets de chair
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro',
                
                # Poules pondeuses
                r'lohmann(?:\s*lsl)?(?:\s*-?\s*lite)?', r'lsl\s*-?\s*lite?',
                r'bovans\s*(?:brown|blanco|white)?', 
                r'hisex\s*(?:brown|blanco|white)?',
                r'isa\s*(?:brown|blanco|white)?',
                r'hyline\s*(?:brown|white)?'
            ]
        }
        
        # Patterns pour classification de type de question
        self.question_type_patterns = {
            "growth": [r'croissance', r'growth', r'crecimiento', r'grossissent?', r'growing', r'crecen'],
            "weight": [r'poids', r'weight', r'peso', r'pèsent?', r'weigh', r'pesan', r'grammes?', r'grams?', r'gramos?'],
            "mortality": [r'mortalité', r'mortality', r'mortalidad', r'meurent', r'dying', r'mueren', r'dead', r'muerte'],
            "health": [r'maladie', r'disease', r'enfermedad', r'malade', r'sick', r'enfermo', r'santé', r'health', r'salud'],
            "temperature": [r'température', r'temperature', r'temperatura', r'chaud', r'hot', r'caliente', r'froid', r'cold', r'frío'],
            "feeding": [r'alimentation', r'feeding', r'alimentación', r'nourriture', r'food', r'comida', r'aliment'],
            "environment": [r'environnement', r'environment', r'ambiente', r'ventilation', r'humidity', r'humidité'],
            "performance": [r'performance', r'rendement', r'efficacité', r'efficiency', r'eficiencia', r'conversion'],
            "laying": [r'ponte', r'laying', r'puesta', r'oeufs?', r'eggs?', r'huevos?']
        }

    def _init_enhanced_prompts(self):
        """Prompts améliorés avec gestion du contexte et entités critiques"""
        
        self.clarification_prompts = {
            "fr": """Tu es un expert vétérinaire spécialisé en aviculture. Analyse cette question et le contexte pour déterminer si des clarifications sont nécessaires.

Question: "{question}"
Type de question détecté: {question_type}
Entités extraites: {extracted_entities}
Contexte conversationnel: {conversation_context}
Informations critiques manquantes: {missing_info}
Entités critiques manquantes: {missing_critical_entities}

RÈGLES STRICTES:
1. Si TOUTES les informations critiques sont présentes → réponds "CLEAR"
2. Si des informations critiques manquent → génère des questions PRÉCISES
3. Priorise TOUJOURS les entités critiques manquantes
4. Adapte le nombre de questions au nombre d'informations critiques manquantes
5. Pour {question_type}, ces entités sont particulièrement importantes: {critical_entities_for_type}

Format: soit "CLEAR" soit liste de questions avec tirets.""",

            "en": """You are a veterinary expert specialized in poultry farming. Analyze this question and context to determine if clarifications are needed.

Question: "{question}"
Detected question type: {question_type}
Extracted entities: {extracted_entities}
Conversational context: {conversation_context}
Missing critical information: {missing_info}
Missing critical entities: {missing_critical_entities}

STRICT RULES:
1. If ALL critical information is present → answer "CLEAR"
2. If critical information is missing → generate PRECISE questions
3. ALWAYS prioritize missing critical entities
4. Adapt number of questions to missing critical information count
5. For {question_type}, these entities are particularly important: {critical_entities_for_type}

Format: either "CLEAR" or bulleted question list.""",

            "es": """Eres un experto veterinario especializado en avicultura. Analiza esta pregunta y contexto para determinar si se necesitan aclaraciones.

Pregunta: "{question}"
Tipo de pregunta detectado: {question_type}
Entidades extraídas: {extracted_entities}
Contexto conversacional: {conversation_context}
Información crítica faltante: {missing_info}
Entidades críticas faltantes: {missing_critical_entities}

REGLAS ESTRICTAS:
1. Si TODA la información crítica está presente → responde "CLEAR"
2. Si falta información crítica → genera preguntas PRECISAS
3. Prioriza SIEMPRE las entidades críticas faltantes
4. Adapta el número de preguntas a la información crítica faltante
5. Para {question_type}, estas entidades son particularmente importantes: {critical_entities_for_type}

Formato: "CLEAR" o lista de preguntas con guiones."""
        }

    def _init_clarification_logger(self):
        """Initialise le logger spécialisé pour les clarifications"""
        self.clarification_logger = logging.getLogger("enhanced_question_clarification")
        self.clarification_logger.setLevel(logging.INFO)
        
        if not self.clarification_logger.handlers and self.log_all_clarifications:
            try:
                from logging.handlers import RotatingFileHandler
                
                log_dir = os.getenv('VALIDATION_LOGS_DIR', 'logs')
                os.makedirs(log_dir, exist_ok=True)
                
                log_file_path = os.path.join(log_dir, 'enhanced_question_clarifications.log')
                clarification_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=int(os.getenv('VALIDATION_LOG_MAX_SIZE', '10485760')),
                    backupCount=int(os.getenv('VALIDATION_LOG_BACKUP_COUNT', '5'))
                )
                clarification_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                clarification_handler.setFormatter(clarification_formatter)
                self.clarification_logger.addHandler(clarification_handler)
                
                logger.info(f"✅ [Enhanced Clarification] Logger configuré: {log_file_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ [Enhanced Clarification] Impossible de créer le fichier de log: {e}")

    def classify_question_type(self, question: str, language: str) -> str:
        """Classifie le type de question"""
        
        question_lower = question.lower()
        
        for question_type, patterns in self.question_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower, re.IGNORECASE):
                    return question_type
        
        return "general"

    def analyze_critical_entities(self, extracted_entities: ExtractedEntities, question_type: str) -> Dict[str, Any]:
        """
        Analyse les entités critiques manquantes selon le type de question
        
        Returns:
            Dict contenant:
            - missing_entities: Liste de toutes les entités manquantes
            - missing_critical_entities: Liste des entités critiques manquantes
            - clarification_required_critical: Boolean indiquant si une clarification critique est nécessaire
            - critical_entities_for_type: Entités critiques spécifiques au type de question
        """
        
        if not self.enable_critical_entity_analysis:
            return {
                "missing_entities": [],
                "missing_critical_entities": [],
                "clarification_required_critical": False,
                "critical_entities_for_type": []
            }
            
        # Obtenir les entités critiques pour ce type de question
        critical_entities_for_type = CRITICAL_ENTITIES_BY_QUESTION_TYPE.get(
            question_type, 
            CRITICAL_ENTITIES_BY_QUESTION_TYPE["general"]
        )
        
        # Analyser toutes les entités manquantes
        missing_entities = []
        missing_critical_entities = []
        
        entities_dict = extracted_entities.to_dict()
        
        for entity in CRITICAL_ENTITIES:
            # Vérifier si l'entité est présente via son mapping
            entity_attributes = ENTITY_ATTRIBUTE_MAPPING.get(entity, [entity])
            entity_present = False
            
            for attr in entity_attributes:
                if attr in entities_dict and entities_dict[attr] is not None:
                    # Vérifications spéciales pour certains types
                    if attr == "breed_type" and entities_dict[attr] == "generic":
                        # Race générique = entité manquante (besoin de spécificité)
                        continue
                    if attr == "symptoms" and isinstance(entities_dict[attr], list) and len(entities_dict[attr]) == 0:
                        # Liste vide de symptômes = entité manquante
                        continue
                    entity_present = True
                    break
            
            if not entity_present:
                missing_entities.append(entity)
                # Vérifier si c'est critique pour ce type de question
                if entity in critical_entities_for_type:
                    missing_critical_entities.append(entity)
        
        # Déterminer si une clarification critique est nécessaire
        clarification_required_critical = len(missing_critical_entities) > 0
        
        # Log de l'analyse
        logger.info(f"🎯 [Critical Entities] Type: {question_type}")
        logger.info(f"🎯 [Critical Entities] Critiques pour ce type: {critical_entities_for_type}")
        logger.info(f"❌ [Critical Entities] Manquantes: {missing_entities}")
        logger.info(f"🚨 [Critical Entities] Critiques manquantes: {missing_critical_entities}")
        logger.info(f"⚠️ [Critical Entities] Clarification critique requise: {clarification_required_critical}")
        
        return {
            "missing_entities": missing_entities,
            "missing_critical_entities": missing_critical_entities,
            "clarification_required_critical": clarification_required_critical,
            "critical_entities_for_type": critical_entities_for_type
        }

    async def extract_entities_intelligent(self, question: str, language: str, conversation_context: Dict = None) -> ExtractedEntities:
        """Extraction intelligente d'entités via OpenAI avec reconnaissance souches"""
        
        if not self.smart_entity_extraction or not OPENAI_AVAILABLE or not openai:
            logger.warning("⚠️ [Enhanced Clarification] Extraction intelligente désactivée ou OpenAI indisponible")
            return await self._extract_entities_fallback(question, language)
        
        try:
            # Construire le contexte pour l'extraction
            context_info = ""
            if conversation_context:
                context_info = f"\n\nContexte conversationnel disponible:\n{json.dumps(conversation_context, ensure_ascii=False, indent=2)}"
            
            # Prompt avec reconnaissance des souches pondeuses et focus sur entités critiques
            extraction_prompt = f"""Tu es un expert en extraction d'informations pour l'aviculture. Extrait TOUTES les informations pertinentes de cette question et du contexte.

Question: "{question}"{context_info}

CONSIGNE: Extrait les informations sous format JSON strict. Utilise null pour les valeurs manquantes.

PRIORITÉ AUX ENTITÉS CRITIQUES: {', '.join(CRITICAL_ENTITIES)}

IMPORTANT POUR LES RACES/SOUCHES:
- Reconnaître les souches pondeuses: Lohmann LSL-Lite, Bovans Brown, Hisex Brown, ISA Brown, Hyline
- Reconnaître les souches de chair: Ross 308, Cobb 500, Hubbard Flex, etc.
- Normaliser les noms (ex: "lohmann" → "Lohmann LSL-Lite")
- Inférer le sexe si possible (souches pondeuses = femelles)

```json
{{
  "breed": "race spécifique (ex: Ross 308, Lohmann LSL-Lite) ou null",
  "breed_type": "specific/generic/null",
  "sex": "mâle/femelle/mixte ou null (inférer si souche pondeuse)",
  "age_days": nombre_jours_ou_null,
  "age_weeks": nombre_semaines_ou_null,
  "weight_grams": poids_grammes_ou_null,
  "mortality_rate": taux_mortalité_pourcentage_ou_null,
  "temperature": température_celsius_ou_null,
  "humidity": humidité_pourcentage_ou_null,
  "housing_type": "type_bâtiment_ou_null",
  "feed_type": "type_alimentation_ou_null",
  "flock_size": nombre_poulets_ou_null,
  "symptoms": ["symptôme1", "symptôme2"] ou null,
  "duration_problem": "durée_problème_ou_null",
  "previous_treatments": ["traitement1"] ou null
}}
```"""

            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return await self._extract_entities_fallback(question, language)
            
            openai.api_key = api_key
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un extracteur d'entités expert en aviculture avec reconnaissance des souches et focus sur les entités critiques. Réponds uniquement avec du JSON valide."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                timeout=self.timeout
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Extraire le JSON de la réponse
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', answer, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', answer, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.warning("⚠️ [Enhanced Clarification] Pas de JSON trouvé dans la réponse")
                    return await self._extract_entities_fallback(question, language)
            
            # Parser le JSON
            try:
                extracted_data = json.loads(json_str)
                
                # Convertir en ExtractedEntities
                entities = ExtractedEntities(
                    breed=extracted_data.get("breed"),
                    breed_type=extracted_data.get("breed_type"),
                    sex=extracted_data.get("sex"),
                    age_days=extracted_data.get("age_days"),
                    age_weeks=extracted_data.get("age_weeks"),
                    weight_grams=extracted_data.get("weight_grams"),
                    mortality_rate=extracted_data.get("mortality_rate"),
                    temperature=extracted_data.get("temperature"),
                    humidity=extracted_data.get("humidity"),
                    housing_type=extracted_data.get("housing_type"),
                    feed_type=extracted_data.get("feed_type"),
                    flock_size=extracted_data.get("flock_size"),
                    symptoms=extracted_data.get("symptoms"),
                    duration_problem=extracted_data.get("duration_problem"),
                    previous_treatments=extracted_data.get("previous_treatments")
                )
                
                # Appliquer normalisation et inférence
                if self.enable_breed_normalization or self.enable_sex_inference:
                    entities.normalize_and_infer()
                
                logger.info(f"🤖 [Enhanced Clarification] Entités extraites intelligemment: {entities.to_dict()}")
                return entities
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ [Enhanced Clarification] Erreur parsing JSON: {e}")
                return await self._extract_entities_fallback(question, language)
        
        except Exception as e:
            logger.error(f"❌ [Enhanced Clarification] Erreur extraction intelligente: {e}")
            return await self._extract_entities_fallback(question, language)

    async def _extract_entities_fallback(self, question: str, language: str) -> ExtractedEntities:
        """Extraction d'entités fallback avec reconnaissance souches (règles basiques)"""
        
        entities = ExtractedEntities()
        question_lower = question.lower()
        
        # Détection race spécifique avec nouvelles souches
        specific_patterns = self.specific_breed_patterns.get(language, self.specific_breed_patterns["fr"])
        for pattern in specific_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                raw_breed = match.group(0).strip()
                entities.breed = raw_breed
                entities.breed_type = "specific"
                break
        
        # Détection race générique si pas spécifique
        if not entities.breed:
            generic_patterns = [r'poulets?', r'volailles?', r'chickens?', r'poultry', r'pollos?', r'aves?', r'poules?']
            for pattern in generic_patterns:
                match = re.search(pattern, question_lower, re.IGNORECASE)
                if match:
                    entities.breed = match.group(0).strip()
                    entities.breed_type = "generic"
                    break
        
        # Détection sexe explicite
        sex_patterns = {
            "fr": [r'mâles?', r'femelles?', r'coqs?', r'poules?', r'poulettes?', r'mixte'],
            "en": [r'males?', r'females?', r'roosters?', r'hens?', r'pullets?', r'mixed'],
            "es": [r'machos?', r'hembras?', r'gallos?', r'gallinas?', r'pollas?', r'mixto']
        }
        
        patterns = sex_patterns.get(language, sex_patterns["fr"])
        for pattern in patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                sex_word = match.group(0).lower()
                if sex_word in ['mâle', 'mâles', 'male', 'males', 'macho', 'machos', 'coq', 'coqs', 'rooster', 'roosters', 'gallo', 'gallos']:
                    entities.sex = "mâle"
                elif sex_word in ['femelle', 'femelles', 'female', 'females', 'hembra', 'hembras', 'poule', 'poules', 'hen', 'hens', 'gallina', 'gallinas', 'poulette', 'poulettes', 'pullet', 'pullets', 'polla', 'pollas']:
                    entities.sex = "femelle"
                elif sex_word in ['mixte', 'mixed', 'mixto']:
                    entities.sex = "mixte"
                break
        
        # Détection âge
        age_patterns = [
            r'(\d+)\s*jours?', r'(\d+)\s*days?', r'(\d+)\s*días?',
            r'(\d+)\s*semaines?', r'(\d+)\s*weeks?', r'(\d+)\s*semanas?',
            r'jour\s*(\d+)', r'day\s*(\d+)', r'día\s*(\d+)'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                if 'semaine' in pattern or 'week' in pattern or 'semana' in pattern:
                    entities.age_weeks = value
                    entities.age_days = value * 7
                else:
                    entities.age_days = value
                break
        
        # Détection poids
        weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|gramm?es?|g|lbs?)',
            r'pèsent?\s+(\d+(?:\.\d+)?)', r'weigh\s+(\d+(?:\.\d+)?)'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                entities.weight_grams = float(match.group(1))
                break
        
        # Appliquer normalisation et inférence même en fallback
        if self.enable_breed_normalization or self.enable_sex_inference:
            entities.normalize_and_infer()
        
        return entities

    async def analyze_question_enhanced(
        self, 
        question: str, 
        language: str = "fr",
        user_id: str = "unknown",
        conversation_id: str = None,
        conversation_context: Dict = None,
        original_question: str = None,
        mode: str = None
    ) -> ClarificationResult:
        """
        ANALYSE AMÉLIORÉE avec extraction intelligente, gestion du contexte et analyse des entités critiques
        """
        
        start_time = time.time()
        
        if not self.enabled:
            logger.info(f"🔧 [Enhanced Clarification] Système désactivé")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="system_disabled",
                clarification_state=ClarificationState.NONE
            )
        
        if not question or len(question.strip()) < self.min_question_length:
            logger.info(f"⚠️ [Enhanced Clarification] Question trop courte: {len(question)}")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="question_too_short",
                clarification_state=ClarificationState.NONE
            )
        
        # Classification du type de question
        question_type = self.classify_question_type(question, language)
        logger.info(f"🏷️ [Enhanced Clarification] Type de question: {question_type}")
        
        # Extraction intelligente d'entités avec reconnaissance souches
        extracted_entities = await self.extract_entities_intelligent(
            question, 
            language, 
            conversation_context
        )
        
        logger.info(f"🔍 [Enhanced Clarification] Analyse: '{question[:80]}...'")
        logger.info(f"📊 [Enhanced Clarification] Entités extraites: {extracted_entities.to_dict()}")
        
        # Logging de reconnaissance automatique
        if extracted_entities.breed_normalized:
            logger.info(f"🔄 [Breed Recognition] Souche normalisée automatiquement: {extracted_entities.breed}")
        if extracted_entities.sex_inferred:
            logger.info(f"🚺 [Sex Inference] Sexe inféré automatiquement: {extracted_entities.sex}")
        
        # NOUVELLE FONCTIONNALITÉ: Analyse des entités critiques
        critical_analysis = self.analyze_critical_entities(extracted_entities, question_type)
        
        # Déterminer les informations critiques manquantes (ancien système)
        missing_critical_info = extracted_entities.get_missing_critical_info(question_type)
        
        logger.info(f"❌ [Enhanced Clarification] Informations critiques manquantes (ancien): {missing_critical_info}")
        logger.info(f"🎯 [Critical Analysis] Résultats: {critical_analysis}")
        
        # Gestion du mode sémantique dynamique avec validation robuste
        if (mode == "semantic_dynamic" or 
            self.clarification_mode == ClarificationMode.SEMANTIC_DYNAMIC) and \
           self.enable_semantic_dynamic:
            
            logger.info(f"🎯 [Semantic Dynamic] Mode activé pour: '{question[:50]}...'")
            
            # Générer questions dynamiques avec métadonnées de validation
            dynamic_questions, validation_metadata = self.question_generator.generate_dynamic_questions_with_validation(question, language)
            
            if dynamic_questions:
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                result = ClarificationResult(
                    needs_clarification=True,
                    questions=dynamic_questions,
                    processing_time_ms=processing_time_ms,
                    reason="semantic_dynamic_clarification_generated",
                    model_used=f"{self.model}_semantic_dynamic",
                    extracted_entities=extracted_entities,
                    question_type=question_type,
                    clarification_mode=ClarificationMode.SEMANTIC_DYNAMIC,
                    clarification_state=ClarificationState.NEEDED,
                    missing_critical_info=missing_critical_info,
                    confidence_score=0.9,
                    original_question=original_question or question,
                    validation_score=validation_metadata.get("validation_score", 0.8),
                    validation_details=validation_metadata,
                    fallback_used=validation_metadata.get("fallback_used", False),
                    gpt_failed=not validation_metadata.get("gpt_success", False),
                    # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                    missing_entities=critical_analysis["missing_entities"],
                    missing_critical_entities=critical_analysis["missing_critical_entities"],
                    clarification_required_critical=critical_analysis["clarification_required_critical"]
                )
                
                logger.info(f"✅ [Semantic Dynamic] {len(dynamic_questions)} questions générées dynamiquement")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            else:
                logger.warning("⚠️ [Semantic Dynamic] Aucune question générée, fallback vers mode normal")
        
        # Logique de clarification basée sur les entités critiques
        if critical_analysis["clarification_required_critical"]:
            logger.info(f"🚨 [Critical Entities] Clarification critique requise - entités manquantes: {critical_analysis['missing_critical_entities']}")
            
            # Générer questions spécifiques aux entités critiques manquantes
            critical_questions = self.question_generator.generate_critical_entity_questions(
                language, 
                critical_analysis["missing_critical_entities"], 
                question_type
            )
            
            return ClarificationResult(
                needs_clarification=True,
                questions=critical_questions,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="critical_entities_missing",
                model_used="rule_based_critical_entities",
                extracted_entities=extracted_entities,
                question_type=question_type,
                clarification_mode=self.clarification_mode,
                clarification_state=ClarificationState.NEEDED,
                missing_critical_info=missing_critical_info,
                confidence_score=95.0,
                original_question=original_question or question,
                validation_score=0.9,
                fallback_used=False,
                gpt_failed=False,
                # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                missing_entities=critical_analysis["missing_entities"],
                missing_critical_entities=critical_analysis["missing_critical_entities"],
                clarification_required_critical=True
            )
        
        # Logique de clarification intelligente (ancien système amélioré)
        if extracted_entities.breed_type == "generic":
            logger.info(f"🚨 [Enhanced Clarification] Race générique détectée - clarification obligatoire")
            
            generic_questions = self.question_generator.generate_adaptive_questions(
                language, missing_critical_info, question_type
            )
            
            return ClarificationResult(
                needs_clarification=True,
                questions=generic_questions,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="generic_breed_detected",
                model_used="rule_based_enhanced",
                extracted_entities=extracted_entities,
                question_type=question_type,
                clarification_mode=self.clarification_mode,
                clarification_state=ClarificationState.NEEDED,
                missing_critical_info=missing_critical_info,
                confidence_score=95.0,
                original_question=original_question or question,
                validation_score=0.9,
                fallback_used=False,
                gpt_failed=False,
                # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                missing_entities=critical_analysis["missing_entities"],
                missing_critical_entities=critical_analysis["missing_critical_entities"],
                clarification_required_critical=critical_analysis["clarification_required_critical"]
            )
        
        # Si race spécifique + âge présents = OK
        if extracted_entities.breed_type == "specific" and (extracted_entities.age_days or extracted_entities.age_weeks):
            logger.info(f"✅ [Enhanced Clarification] Race spécifique + âge - question complète")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="specific_breed_and_age_detected",
                extracted_entities=extracted_entities,
                question_type=question_type,
                clarification_state=ClarificationState.NONE,
                validation_score=1.0,
                fallback_used=False,
                gpt_failed=False,
                # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                missing_entities=critical_analysis["missing_entities"],
                missing_critical_entities=critical_analysis["missing_critical_entities"],
                clarification_required_critical=False
            )
        
        # Si pas d'informations critiques manquantes (ancien + nouveau système)
        if not missing_critical_info and not critical_analysis["clarification_required_critical"]:
            logger.info(f"✅ [Enhanced Clarification] Toutes les informations critiques présentes")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="all_critical_info_present",
                extracted_entities=extracted_entities,
                question_type=question_type,
                clarification_state=ClarificationState.NONE,
                validation_score=1.0,
                fallback_used=False,
                gpt_failed=False,
                # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                missing_entities=critical_analysis["missing_entities"],
                missing_critical_entities=critical_analysis["missing_critical_entities"],
                clarification_required_critical=False
            )
        
        # Analyse via OpenAI pour les cas complexes (avec informations d'entités critiques)
        if not OPENAI_AVAILABLE or not openai:
            logger.warning(f"⚠️ [Enhanced Clarification] OpenAI non disponible - fallback vers questions adaptatives")
            
            adaptive_questions = self.question_generator.generate_adaptive_questions(
                language, missing_critical_info, question_type
            )
            
            return ClarificationResult(
                needs_clarification=True,
                questions=adaptive_questions,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="openai_unavailable_adaptive_fallback",
                model_used="rule_based_adaptive",
                extracted_entities=extracted_entities,
                question_type=question_type,
                clarification_mode=self.clarification_mode,
                clarification_state=ClarificationState.NEEDED,
                missing_critical_info=missing_critical_info,
                confidence_score=0.7,
                original_question=original_question or question,
                validation_score=0.8,
                fallback_used=True,
                gpt_failed=True,
                # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                missing_entities=critical_analysis["missing_entities"],
                missing_critical_entities=critical_analysis["missing_critical_entities"],
                clarification_required_critical=critical_analysis["clarification_required_critical"]
            )
        
        try:
            # Configuration OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning(f"⚠️ [Enhanced Clarification] Clé API OpenAI manquante - fallback adaptatif")
                
                adaptive_questions = self.question_generator.generate_adaptive_questions(
                    language, missing_critical_info, question_type
                )
                
                return ClarificationResult(
                    needs_clarification=True,
                    questions=adaptive_questions,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    reason="openai_key_missing_adaptive_fallback",
                    model_used="rule_based_adaptive",
                    extracted_entities=extracted_entities,
                    question_type=question_type,
                    clarification_mode=self.clarification_mode,
                    clarification_state=ClarificationState.NEEDED,
                    missing_critical_info=missing_critical_info,
                    confidence_score=0.7,
                    original_question=original_question or question,
                    validation_score=0.8,
                    fallback_used=True,
                    gpt_failed=True,
                    # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                    missing_entities=critical_analysis["missing_entities"],
                    missing_critical_entities=critical_analysis["missing_critical_entities"],
                    clarification_required_critical=critical_analysis["clarification_required_critical"]
                )
            
            openai.api_key = api_key
            
            # PROMPT ENRICHI avec toutes les informations + entités critiques
            prompt_template = self.clarification_prompts.get(language.lower(), self.clarification_prompts["fr"])
            
            context_str = json.dumps(conversation_context, ensure_ascii=False) if conversation_context else "Aucun contexte"
            entities_str = json.dumps(extracted_entities.to_dict(), ensure_ascii=False)
            missing_info_str = ", ".join(missing_critical_info) if missing_critical_info else "Aucune"
            missing_critical_entities_str = ", ".join(critical_analysis["missing_critical_entities"]) if critical_analysis["missing_critical_entities"] else "Aucune"
            critical_entities_for_type_str = ", ".join(critical_analysis["critical_entities_for_type"])
            
            user_prompt = prompt_template.format(
                question=question,
                question_type=question_type,
                extracted_entities=entities_str,
                conversation_context=context_str,
                missing_info=missing_info_str,
                missing_critical_entities=missing_critical_entities_str,
                critical_entities_for_type=critical_entities_for_type_str
            )
            
            system_prompt = f"""Tu es un assistant expert qui détermine si une question d'aviculture nécessite des clarifications. 

Mode de clarification: {self.clarification_mode.value}
Questions adaptatives: {'activées' if self.adaptive_question_count else 'désactivées'}
Analyse entités critiques: {'activée' if self.enable_critical_entity_analysis else 'désactivée'}

FOCUS PRIORITAIRE sur les entités critiques: {', '.join(CRITICAL_ENTITIES)}

Sois très précis et utilise intelligemment le contexte conversationnel pour éviter les questions redondantes."""
            
            # Appel OpenAI enrichi
            logger.info(f"🤖 [Enhanced Clarification] Appel GPT-4o-mini enrichi avec analyse entités critiques...")
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=400,
                timeout=self.timeout
            )
            
            answer = response.choices[0].message.content.strip()
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"🤖 [Enhanced Clarification] Réponse GPT-4o-mini ({processing_time_ms}ms): {answer[:100]}...")
            
            # Analyse de la réponse
            if answer.upper().strip() in ["CLEAR", "CLEAR.", "CLEAR !"]:
                result = ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="question_clear_by_gpt4o_mini_enhanced",
                    model_used=self.model,
                    extracted_entities=extracted_entities,
                    question_type=question_type,
                    clarification_state=ClarificationState.NONE,
                    validation_score=1.0,
                    fallback_used=False,
                    gpt_failed=False,
                    # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                    missing_entities=critical_analysis["missing_entities"],
                    missing_critical_entities=critical_analysis["missing_critical_entities"],
                    clarification_required_critical=False
                )
                
                logger.info(f"✅ [Enhanced Clarification] Question claire selon GPT-4o-mini enrichi")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            
            # Extraire les questions de clarification
            clarification_questions = self._extract_questions(answer)
            
            # Limitation adaptative du nombre de questions
            if self.adaptive_question_count:
                max_questions = min(len(critical_analysis["missing_critical_entities"]) + 1, self.max_questions)
            else:
                max_questions = self.max_questions
            
            if clarification_questions and len(clarification_questions) > 0:
                limited_questions = clarification_questions[:max_questions]
                
                # Mode de clarification
                clarification_mode = self.clarification_mode
                if clarification_mode == ClarificationMode.ADAPTIVE:
                    clarification_mode = ClarificationMode.INTERACTIVE if len(limited_questions) == 1 else ClarificationMode.BATCH
                
                result = ClarificationResult(
                    needs_clarification=True,
                    questions=limited_questions,
                    processing_time_ms=processing_time_ms,
                    reason="clarification_needed_by_gpt4o_mini_enhanced",
                    model_used=self.model,
                    confidence_score=self._calculate_confidence_score_enhanced(question, limited_questions, extracted_entities, question_type),
                    extracted_entities=extracted_entities,
                    question_type=question_type,
                    clarification_mode=clarification_mode,
                    clarification_state=ClarificationState.NEEDED,
                    missing_critical_info=missing_critical_info,
                    original_question=original_question or question,
                    validation_score=0.8,
                    fallback_used=False,
                    gpt_failed=False,
                    # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                    missing_entities=critical_analysis["missing_entities"],
                    missing_critical_entities=critical_analysis["missing_critical_entities"],
                    clarification_required_critical=critical_analysis["clarification_required_critical"]
                )
                
                logger.info(f"❓ [Enhanced Clarification] {len(limited_questions)} questions générées (mode: {clarification_mode.value})")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            else:
                logger.info(f"✅ [Enhanced Clarification] Aucune question valide - question suffisante")
                return ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="no_valid_questions_from_gpt4o_mini_enhanced",
                    model_used=self.model,
                    extracted_entities=extracted_entities,
                    question_type=question_type,
                    clarification_state=ClarificationState.NONE,
                    validation_score=1.0,
                    fallback_used=False,
                    gpt_failed=False,
                    # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                    missing_entities=critical_analysis["missing_entities"],
                    missing_critical_entities=critical_analysis["missing_critical_entities"],
                    clarification_required_critical=critical_analysis["clarification_required_critical"]
                )
        
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ [Enhanced Clarification] Erreur GPT-4o-mini: {e}")
            
            # Fallback intelligent en cas d'erreur GPT
            if self.enable_intelligent_fallback:
                logger.info(f"🔄 [Enhanced Clarification] Fallback intelligent activé suite à erreur GPT")
                
                adaptive_questions = self.question_generator.generate_adaptive_questions(
                    language, missing_critical_info, question_type
                )
                
                return ClarificationResult(
                    needs_clarification=True,
                    questions=adaptive_questions,
                    processing_time_ms=processing_time_ms,
                    reason=f"gpt_error_intelligent_fallback: {str(e)}",
                    model_used="rule_based_adaptive_fallback",
                    extracted_entities=extracted_entities,
                    question_type=question_type,
                    clarification_mode=self.clarification_mode,
                    clarification_state=ClarificationState.NEEDED,
                    missing_critical_info=missing_critical_info,
                    confidence_score=0.6,
                    original_question=original_question or question,
                    validation_score=0.7,
                    fallback_used=True,
                    gpt_failed=True,
                    # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                    missing_entities=critical_analysis["missing_entities"],
                    missing_critical_entities=critical_analysis["missing_critical_entities"],
                    clarification_required_critical=critical_analysis["clarification_required_critical"]
                )
            else:
                return ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason=f"error_gpt4o_mini_enhanced: {str(e)}",
                    model_used=self.model,
                    extracted_entities=extracted_entities,
                    question_type=question_type,
                    clarification_state=ClarificationState.NONE,
                    fallback_used=False,
                    gpt_failed=True,
                    # NOUVEAUX CHAMPS ENTITÉS CRITIQUES
                    missing_entities=critical_analysis["missing_entities"],
                    missing_critical_entities=critical_analysis["missing_critical_entities"],
                    clarification_required_critical=critical_analysis["clarification_required_critical"]
                )

    def _extract_questions(self, answer: str) -> List[str]:
        """Extrait les questions de clarification de la réponse GPT"""
        questions = []
        lines = answer.splitlines()
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 15:
                # Nettoyer les puces et formatage
                cleaned_line = re.sub(r'^[-•*]\s*', '', line)
                cleaned_line = re.sub(r'^\d+\.\s*', '', cleaned_line)
                cleaned_line = cleaned_line.strip()
                
                # Vérifier que c'est une vraie question
                if cleaned_line and len(cleaned_line) > 20 and cleaned_line not in questions:
                    # Ajouter un point d'interrogation si manquant
                    if not cleaned_line.endswith('?') and not cleaned_line.endswith(' ?'):
                        if any(word in cleaned_line.lower() for word in ['quel', 'quelle', 'combien', 'comment', 'what', 'how', 'which', 'cuál', 'cómo', 'cuánto']):
                            cleaned_line += ' ?'
                    
                    questions.append(cleaned_line)
        
        return questions

    def _calculate_confidence_score_enhanced(
        self, 
        original_question: str, 
        clarification_questions: List[str], 
        extracted_entities: ExtractedEntities,
        question_type: str
    ) -> float:
        """Score de confiance plus intelligent avec entités critiques"""
        
        # Score de base
        base_score = min(len(clarification_questions) * 20, 70)
        
        # Bonus pour informations génériques détectées
        if extracted_entities.breed_type == "generic":
            base_score += 20
        
        # Bonus selon le type de question et informations manquantes
        critical_info_bonus = {
            "growth": 15 if not extracted_entities.age_days else 0,
            "weight": 15 if not extracted_entities.age_days else 0,
            "health": 10 if not extracted_entities.symptoms else 0,
            "mortality": 15 if not extracted_entities.mortality_rate else 0,
            "laying": 10 if not extracted_entities.age_days else 0
        }
        
        base_score += critical_info_bonus.get(question_type, 5)
        
        # NOUVEAU: Bonus pour entités critiques manquantes
        if self.enable_critical_entity_analysis:
            critical_analysis = self.analyze_critical_entities(extracted_entities, question_type)
            critical_missing_count = len(critical_analysis["missing_critical_entities"])
            base_score += critical_missing_count * 10  # Bonus de 10 points par entité critique manquante
        
        # Malus si beaucoup d'informations déjà présentes
        extracted_count = len([v for v in extracted_entities.to_dict().values() if v is not None])
        if extracted_count > 3:
            base_score -= 10
        
        # Bonus si reconnaissance automatique a fonctionné
        if extracted_entities.breed_normalized:
            base_score += 5
        if extracted_entities.sex_inferred:
            base_score += 5
        
        return min(base_score, 95.0)

    async def check_for_reprocessing(
        self,
        conversation_id: str,
        user_response: str,
        original_clarification_result: ClarificationResult
    ) -> Optional[ClarificationResult]:
        """
        Vérifie si la question originale peut être retraitée après clarification
        """
        
        if not self.auto_reprocess_after_clarification:
            return None
        
        if not original_clarification_result.original_question:
            return None
        
        logger.info(f"🔄 [Enhanced Clarification] Vérification retraitement après clarification")
        
        # Construire la question enrichie
        enriched_question = f"{original_clarification_result.original_question}\n\nInformation supplémentaire: {user_response}"
        
        # Réanalyser avec le contexte enrichi
        reprocess_result = await self.analyze_question_enhanced(
            question=enriched_question,
            language="fr",
            conversation_id=conversation_id,
            original_question=original_clarification_result.original_question
        )
        
        if not reprocess_result.needs_clarification:
            reprocess_result.should_reprocess = True
            reprocess_result.clarification_state = ClarificationState.AWAITING_REPROCESS
            logger.info(f"✅ [Enhanced Clarification] Question prête pour retraitement")
            return reprocess_result
        
        logger.info(f"⚠️ [Enhanced Clarification] Clarification supplémentaire encore nécessaire")
        return None

    def format_clarification_response_enhanced(
        self, 
        result: ClarificationResult,
        language: str
    ) -> str:
        """Formatage enrichi selon le mode de clarification avec mention des entités critiques"""
        
        if not result.questions:
            return ""
        
        intros = {
            "fr": {
                ClarificationMode.BATCH: "❓ Pour vous donner la réponse la plus précise possible, j'aurais besoin de quelques informations supplémentaires :",
                ClarificationMode.INTERACTIVE: "❓ Pour vous aider au mieux, puis-je vous poser une question rapide :",
                ClarificationMode.ADAPTIVE: "❓ J'ai besoin d'une précision pour vous donner une réponse adaptée :",
                ClarificationMode.SEMANTIC_DYNAMIC: "❓ Pour mieux comprendre votre situation et vous aider efficacement :"
            },
            "en": {
                ClarificationMode.BATCH: "❓ To give you the most accurate answer possible, I would need some additional information:",
                ClarificationMode.INTERACTIVE: "❓ To help you best, may I ask you a quick question:",
                ClarificationMode.ADAPTIVE: "❓ I need clarification to give you a tailored answer:",
                ClarificationMode.SEMANTIC_DYNAMIC: "❓ To better understand your situation and help you effectively:"
            },
            "es": {
                ClarificationMode.BATCH: "❓ Para darle la respuesta más precisa posible, necesitaría información adicional:",
                ClarificationMode.INTERACTIVE: "❓ Para ayudarle mejor, ¿puedo hacerle una pregunta rápida:",
                ClarificationMode.ADAPTIVE: "❓ Necesito una aclaración para darle una respuesta adaptada:",
                ClarificationMode.SEMANTIC_DYNAMIC: "❓ Para entender mejor su situación y ayudarle efectivamente:"
            }
        }
        
        outros = {
            "fr": {
                ClarificationMode.BATCH: "\n\nCes précisions m'aideront à vous donner des conseils spécifiques et adaptés à votre situation ! 🐔",
                ClarificationMode.INTERACTIVE: "\n\nMerci pour votre précision ! 🐔",
                ClarificationMode.ADAPTIVE: "\n\nCela m'aidera à vous donner une réponse plus précise ! 🐔",
                ClarificationMode.SEMANTIC_DYNAMIC: "\n\nCela me permettra de vous donner les conseils les plus pertinents ! 🐔"
            },
            "en": {
                ClarificationMode.BATCH: "\n\nThese details will help me give you specific advice tailored to your situation! 🐔",
                ClarificationMode.INTERACTIVE: "\n\nThank you for the clarification! 🐔",
                ClarificationMode.ADAPTIVE: "\n\nThis will help me give you a more precise answer! 🐔",
                ClarificationMode.SEMANTIC_DYNAMIC: "\n\nThis will allow me to give you the most relevant advice! 🐔"
            },
            "es": {
                ClarificationMode.BATCH: "\n\n¡Estos detalles me ayudarán a darle consejos específicos adaptados a su situación! 🐔",
                ClarificationMode.INTERACTIVE: "\n\n¡Gracias por la aclaración! 🐔",
                ClarificationMode.ADAPTIVE: "\n\n¡Esto me ayudará a darle una respuesta más precisa! 🐔",
                ClarificationMode.SEMANTIC_DYNAMIC: "\n\n¡Esto me permitirá darle los consejos más relevantes! 🐔"
            }
        }
        
        mode = result.clarification_mode or ClarificationMode.BATCH
        intro = intros.get(language, intros["fr"]).get(mode, intros["fr"][ClarificationMode.BATCH])
        outro = outros.get(language, outros["fr"]).get(mode, outros["fr"][ClarificationMode.BATCH])
        
        # Ajouter une mention spéciale si des entités critiques sont manquantes
        critical_mention = ""
        if hasattr(result, 'clarification_required_critical') and result.clarification_required_critical:
            critical_mentions = {
                "fr": " (informations essentielles pour un diagnostic précis)",
                "en": " (essential information for accurate diagnosis)",
                "es": " (información esencial para un diagnóstico preciso)"
            }
            critical_mention = critical_mentions.get(language, critical_mentions["fr"])
        
        if mode == ClarificationMode.INTERACTIVE or len(result.questions) == 1:
            # Mode interactif ou une seule question
            return f"{intro}{critical_mention}\n\n{result.questions[0]}{outro}"
        else:
            # Mode batch - plusieurs questions
            formatted_questions = "\n".join([f"• {q}" for q in result.questions])
            return f"{intro}{critical_mention}\n\n{formatted_questions}{outro}"

    async def _log_clarification_decision(
        self,
        question: str,
        language: str,
        user_id: str,
        conversation_id: str,
        result: ClarificationResult
    ):
        """Log détaillé des décisions de clarification enrichi avec entités critiques"""
        
        clarification_data = {
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "user_id": user_id,
            "question": question,
            "question_length": len(question),
            "language": language,
            "result": result.to_dict(),
            "system_config": {
                "enabled": self.enabled,
                "model": self.model,
                "max_questions": self.max_questions,
                "confidence_threshold": self.confidence_threshold,
                "clarification_mode": self.clarification_mode.value,
                "enable_semantic_dynamic": self.enable_semantic_dynamic,
                "enable_question_validation": self.enable_question_validation,
                "enable_breed_normalization": self.enable_breed_normalization,
                "enable_sex_inference": self.enable_sex_inference,
                "enable_critical_entity_analysis": self.enable_critical_entity_analysis,
                "critical_entities_threshold": self.critical_entities_threshold
            }
        }
        
        # Log structuré
        self.clarification_logger.info(json.dumps(clarification_data, ensure_ascii=False))
        
        # Log standard enrichi avec entités critiques
        if result.needs_clarification:
            critical_info = ""
            if hasattr(result, 'clarification_required_critical'):
                critical_status = "🚨 CRITIQUE" if result.clarification_required_critical else "📝 Standard"
                critical_entities_count = len(getattr(result, 'missing_critical_entities', []))
                critical_info = f" | {critical_status} ({critical_entities_count} entités critiques manquantes)"
            
            logger.info(
                f"❓ [Enhanced Clarification] CLARIFICATION - "
                f"User: {user_id[:8]} | Type: {result.question_type} | "
                f"Questions: {len(result.questions)} | Mode: {result.clarification_mode.value if result.clarification_mode else 'N/A'} | "
                f"Validation: {result.validation_score:.1f} | "
                f"Fallback: {'✅' if result.fallback_used else '❌'} | "
                f"Temps: {result.processing_time_ms}ms{critical_info}"
            )
        else:
            logger.info(
                f"✅ [Enhanced Clarification] CLEAR - "
                f"User: {user_id[:8]} | Type: {result.question_type} | "
                f"Raison: {result.reason} | "
                f"Temps: {result.processing_time_ms}ms"
            )

    def get_stats_enhanced(self) -> Dict:
        """Retourne les statistiques du système enrichi avec entités critiques"""
        return {
            "enabled": self.enabled,
            "model": self.model,
            "max_questions": self.max_questions,
            "confidence_threshold": self.confidence_threshold,
            "openai_available": OPENAI_AVAILABLE,
            "clarification_mode": self.clarification_mode.value,
            "smart_entity_extraction": self.smart_entity_extraction,
            "semantic_dynamic_enabled": self.enable_semantic_dynamic,
            "question_validation_enabled": self.enable_question_validation,
            "breed_normalization_enabled": self.enable_breed_normalization,
            "sex_inference_enabled": self.enable_sex_inference,
            "critical_entity_analysis_enabled": self.enable_critical_entity_analysis,
            "critical_entities_threshold": self.critical_entities_threshold,
            "critical_entities": CRITICAL_ENTITIES,
            "critical_entities_count": len(CRITICAL_ENTITIES),
            "supported_question_types": list(self.question_type_patterns.keys()),
            "supported_languages": ["fr", "en", "es"],
            "critical_entities_by_question_type": CRITICAL_ENTITIES_BY_QUESTION_TYPE
        }


# ==================== INSTANCE GLOBALE ====================

# Instance singleton du système de clarification
enhanced_clarification_system = EnhancedQuestionClarificationSystem()

# ==================== FONCTIONS UTILITAIRES PUBLIQUES ====================

async def analyze_question_for_clarification_enhanced(
    question: str, 
    language: str = "fr",
    user_id: str = "unknown", 
    conversation_id: str = None,
    conversation_context: Dict = None,
    original_question: str = None
) -> ClarificationResult:
    """Fonction utilitaire pour analyser les questions avec le système amélioré"""
    return await enhanced_clarification_system.analyze_question_enhanced(
        question, language, user_id, conversation_id, conversation_context, original_question
    )

async def analyze_question_for_clarification_semantic_dynamic(
    question: str, 
    language: str = "fr",
    user_id: str = "unknown", 
    conversation_id: str = None,
    conversation_context: Dict = None
) -> ClarificationResult:
    """Fonction utilitaire pour utiliser le mode sémantique dynamique directement"""
    return await enhanced_clarification_system.analyze_question_enhanced(
        question, language, user_id, conversation_id, conversation_context, mode="semantic_dynamic"
    )

def analyze_critical_entities_for_question(
    extracted_entities: ExtractedEntities, 
    question_type: str
) -> Dict[str, Any]:
    """Fonction utilitaire pour analyser les entités critiques d'une question"""
    return enhanced_clarification_system.analyze_critical_entities(extracted_entities, question_type)

def get_critical_entities_for_question_type(question_type: str) -> List[str]:
    """Retourne les entités critiques pour un type de question donné"""
    return CRITICAL_ENTITIES_BY_QUESTION_TYPE.get(question_type, CRITICAL_ENTITIES_BY_QUESTION_TYPE["general"])

def is_critical_entity_missing(entity_name: str, extracted_entities: ExtractedEntities) -> bool:
    """Vérifie si une entité critique spécifique est manquante"""
    if entity_name not in CRITICAL_ENTITIES:
        return False
    
    entity_attributes = ENTITY_ATTRIBUTE_MAPPING.get(entity_name, [entity_name])
    entities_dict = extracted_entities.to_dict()
    
    for attr in entity_attributes:
        if attr in entities_dict and entities_dict[attr] is not None:
            # Vérifications spéciales
            if attr == "breed_type" and entities_dict[attr] == "generic":
                continue
            if attr == "symptoms" and isinstance(entities_dict[attr], list) and len(entities_dict[attr]) == 0:
                continue
            return False
    
    return True

def format_clarification_response_enhanced(result: ClarificationResult, language: str) -> str:
    """Formate la réponse de clarification avec le système amélioré"""
    return enhanced_clarification_system.format_clarification_response_enhanced(result, language)

async def check_for_reprocessing_after_clarification(
    conversation_id: str,
    user_response: str,
    original_clarification_result: ClarificationResult
) -> Optional[ClarificationResult]:
    """Vérifie si une question peut être retraitée après clarification"""
    return await enhanced_clarification_system.check_for_reprocessing(
        conversation_id, user_response, original_clarification_result
    )

def get_enhanced_clarification_system_stats() -> Dict:
    """Retourne les statistiques du système amélioré"""
    return enhanced_clarification_system.get_stats_enhanced()

def is_enhanced_clarification_system_enabled() -> bool:
    """Vérifie si le système de clarification amélioré est activé"""
    return enhanced_clarification_system.enabled

def build_enriched_question_enhanced(
    original_question: str, 
    clarification_answers: Dict[str, str], 
    clarification_questions: List[str]
) -> str:
    """Construit une question enrichie avec les réponses de clarification"""
    enriched_question = original_question + "\n\nInformations supplémentaires :"
    
    for index_str, answer in clarification_answers.items():
        if answer and answer.strip():
            try:
                index = int(index_str)
                if 0 <= index < len(clarification_questions):
                    question = clarification_questions[index]
                    enriched_question += f"\n- {question}: {answer.strip()}"
            except (ValueError, IndexError):
                continue
    
    return enriched_question

def get_missing_critical_entities_summary(result: ClarificationResult, language: str = "fr") -> str:
    """Génère un résumé des entités critiques manquantes"""
    if not hasattr(result, 'missing_critical_entities') or not result.missing_critical_entities:
        return ""
    
    summaries = {
        "fr": {
            "breed": "race/souche",
            "age": "âge",
            "sex": "sexe",
            "symptoms": "symptômes",
            "environment": "environnement",
            "feed": "alimentation",
            "flock_size": "taille du troupeau",
            "mortality_rate": "taux de mortalité"
        },
        "en": {
            "breed": "breed/strain",
            "age": "age",
            "sex": "sex",
            "symptoms": "symptoms",
            "environment": "environment",
            "feed": "feeding",
            "flock_size": "flock size",
            "mortality_rate": "mortality rate"
        },
        "es": {
            "breed": "raza/cepa",
            "age": "edad",
            "sex": "sexo",
            "symptoms": "síntomas",
            "environment": "ambiente",
            "feed": "alimentación",
            "flock_size": "tamaño del rebaño",
            "mortality_rate": "tasa de mortalidad"
        }
    }
    
    entity_names = summaries.get(language, summaries["fr"])
    missing_names = [entity_names.get(entity, entity) for entity in result.missing_critical_entities]
    
    if len(missing_names) == 1:
        return missing_names[0]
    elif len(missing_names) == 2:
        conjunction = {"fr": " et ", "en": " and ", "es": " y "}.get(language, " et ")
        return conjunction.join(missing_names)
    else:
        conjunction = {"fr": " et ", "en": " and ", "es": " y "}.get(language, " et ")
        return ", ".join(missing_names[:-1]) + conjunction + missing_names[-1]

# ==================== EXTENSIONS DU QUESTION GENERATOR ====================

def extend_question_generator_with_critical_entities():
    """Étend le générateur de questions avec le support des entités critiques"""
    
    def generate_critical_entity_questions(self, language: str, missing_critical_entities: List[str], question_type: str) -> List[str]:
        """Génère des questions spécifiques aux entités critiques manquantes"""
        
        questions = []
        
        critical_entity_questions = {
            "fr": {
                "breed": [
                    "Quelle est la race ou souche exacte de vos volailles ? (ex: Ross 308, Cobb 500, Lohmann LSL-Lite)",
                    "Quel type de poulets élevez-vous ? Précisez la souche si possible."
                ],
                "age": [
                    "Quel est l'âge de vos volailles en jours ou en semaines ?",
                    "Depuis combien de temps vos volailles sont-elles nées ?"
                ],
                "sex": [
                    "S'agit-il de mâles, de femelles ou d'un troupeau mixte ?",
                    "Quel est le sexe de vos volailles ?"
                ],
                "symptoms": [
                    "Quels symptômes précis observez-vous chez vos volailles ?",
                    "Pouvez-vous décrire les signes cliniques que vous avez remarqués ?"
                ],
                "environment": [
                    "Quelles sont les conditions d'élevage ? (température, humidité, type de bâtiment)",
                    "Dans quel environnement vos volailles sont-elles élevées ?"
                ],
                "feed": [
                    "Quel type d'alimentation donnez-vous à vos volailles ?",
                    "Pouvez-vous préciser le programme alimentaire utilisé ?"
                ],
                "flock_size": [
                    "Combien de volailles avez-vous dans votre troupeau ?",
                    "Quelle est la taille de votre élevage ?"
                ],
                "mortality_rate": [
                    "Quel est le taux de mortalité observé ? (nombre de morts / total)",
                    "Combien de volailles sont mortes et sur combien au total ?"
                ]
            },
            "en": {
                "breed": [
                    "What is the exact breed or strain of your poultry? (e.g., Ross 308, Cobb 500, Lohmann LSL-Lite)",
                    "What type of chickens are you raising? Please specify the strain if possible."
                ],
                "age": [
                    "What is the age of your poultry in days or weeks?",
                    "How long have your poultry been hatched?"
                ],
                "sex": [
                    "Are these males, females, or a mixed flock?",
                    "What is the sex of your poultry?"
                ],
                "symptoms": [
                    "What specific symptoms are you observing in your poultry?",
                    "Can you describe the clinical signs you have noticed?"
                ],
                "environment": [
                    "What are the housing conditions? (temperature, humidity, building type)",
                    "In what environment are your poultry being raised?"
                ],
                "feed": [
                    "What type of feed are you giving to your poultry?",
                    "Can you specify the feeding program used?"
                ],
                "flock_size": [
                    "How many poultry do you have in your flock?",
                    "What is the size of your operation?"
                ],
                "mortality_rate": [
                    "What is the observed mortality rate? (number of deaths / total)",
                    "How many poultry have died and out of how many total?"
                ]
            },
            "es": {
                "breed": [
                    "¿Cuál es la raza o cepa exacta de sus aves? (ej: Ross 308, Cobb 500, Lohmann LSL-Lite)",
                    "¿Qué tipo de pollos está criando? Especifique la cepa si es posible."
                ],
                "age": [
                    "¿Cuál es la edad de sus aves en días o semanas?",
                    "¿Hace cuánto tiempo nacieron sus aves?"
                ],
                "sex": [
                    "¿Son machos, hembras o un rebaño mixto?",
                    "¿Cuál es el sexo de sus aves?"
                ],
                "symptoms": [
                    "¿Qué síntomas específicos observa en sus aves?",
                    "¿Puede describir los signos clínicos que ha notado?"
                ],
                "environment": [
                    "¿Cuáles son las condiciones de crianza? (temperatura, humedad, tipo de edificio)",
                    "¿En qué ambiente se están criando sus aves?"
                ],
                "feed": [
                    "¿Qué tipo de alimentación da a sus aves?",
                    "¿Puede especificar el programa alimentario utilizado?"
                ],
                "flock_size": [
                    "¿Cuántas aves tiene en su rebaño?",
                    "¿Cuál es el tamaño de su operación?"
                ],
                "mortality_rate": [
                    "¿Cuál es la tasa de mortalidad observada? (número de muertes / total)",
                    "¿Cuántas aves han muerto y de cuántas en total?"
                ]
            }
        }
        
        language_questions = critical_entity_questions.get(language, critical_entity_questions["fr"])
        
        # Prioriser selon le type de question
        priority_order = CRITICAL_ENTITIES_BY_QUESTION_TYPE.get(question_type, CRITICAL_ENTITIES)
        
        # Trier les entités manquantes par priorité
        sorted_entities = [entity for entity in priority_order if entity in missing_critical_entities]
        remaining_entities = [entity for entity in missing_critical_entities if entity not in sorted_entities]
        sorted_entities.extend(remaining_entities)
        
        # Générer les questions dans l'ordre de priorité
        for entity in sorted_entities[:self.max_questions]:
            if entity in language_questions:
                # Prendre la première question pour cette entité
                questions.append(language_questions[entity][0])
        
        return questions
    
    # Ajouter la méthode au générateur de questions
    QuestionGenerator.generate_critical_entity_questions = generate_critical_entity_questions

# Appliquer l'extension
extend_question_generator_with_critical_entities()

# ==================== LOGGING DE DÉMARRAGE ====================

logger.info("❓ [EnhancedQuestionClarificationSystem] Module MODULAIRE initialisé avec ENTITÉS CRITIQUES")
logger.info("✅ [Clarification System] PRÊT - Toutes fonctionnalités disponibles + analyse entités critiques!")
logger.info(f"🎯 [Critical Entities] {len(CRITICAL_ENTITIES)} entités critiques configurées")
logger.info(f"📊 [System Stats] {enhanced_clarification_system.get_stats_enhanced()}")