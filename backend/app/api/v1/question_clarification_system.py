"""
app/api/v1/question_clarification_system.py - VERSION COMPLÈTE AVEC VALIDATION GPT INTÉGRÉE

AMÉLIORATIONS MAJEURES:
1. ✅ Extraction intelligente d'entités via OpenAI avec raisonnement dynamique (CONSERVÉ)
2. ✅ Clarification multi-tour (interactive vs batch) (CONSERVÉ)
3. ✅ Retraitement automatique après clarification (CONSERVÉ)
4. ✅ Gestion avancée du contexte conversationnel (CONSERVÉ)
5. ✅ Prompts plus intelligents pour données numériques (CONSERVÉ)
6. ✅ Clarification partielle adaptative (1 question si 1 info manque) (CONSERVÉ)
7. 🆕 Mode sémantique dynamique avec génération GPT de questions contextuelles (CONSERVÉ)
8. 🔧 NOUVEAU: Validation automatique robuste des questions générées par GPT
9. 🔧 NOUVEAU: Filtrage avancé des questions non pertinentes
10. 🔧 NOUVEAU: Fallback intelligent si validation échoue
11. 🔧 NOUVEAU: Fallback lisible si GPT échoue complètement
"""

import os
import re
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

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

class ClarificationMode(Enum):
    """Modes de clarification disponibles"""
    BATCH = "batch"
    INTERACTIVE = "interactive"
    ADAPTIVE = "adaptive"
    SEMANTIC_DYNAMIC = "semantic_dynamic"

class ClarificationState(Enum):
    """États de clarification"""
    NONE = "none"
    NEEDED = "needed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    AWAITING_REPROCESS = "awaiting_reprocess"

@dataclass
class ExtractedEntities:
    """Entités extraites intelligemment du contexte"""
    breed: Optional[str] = None
    breed_type: Optional[str] = None
    age_days: Optional[int] = None
    age_weeks: Optional[float] = None
    weight_grams: Optional[float] = None
    mortality_rate: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    housing_type: Optional[str] = None
    feed_type: Optional[str] = None
    flock_size: Optional[int] = None
    symptoms: Optional[List[str]] = None
    duration_problem: Optional[str] = None
    previous_treatments: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour logs"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def get_missing_critical_info(self, question_type: str) -> List[str]:
        """Détermine les informations critiques manquantes selon le type de question"""
        missing = []
        
        if not self.breed or self.breed_type == "generic":
            missing.append("breed")
        
        if question_type in ["growth", "weight", "performance"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
        elif question_type in ["health", "mortality", "disease"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
            if not self.symptoms:
                missing.append("symptoms")
        elif question_type in ["environment", "temperature", "housing"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
        elif question_type in ["feeding", "nutrition"]:
            if not self.age_days and not self.age_weeks:
                missing.append("age")
        
        return missing

@dataclass
class ClarificationResult:
    """Résultat de l'analyse de clarification amélioré"""
    needs_clarification: bool
    questions: Optional[List[str]] = None
    confidence_score: float = 0.0
    processing_time_ms: int = 0
    reason: Optional[str] = None
    model_used: Optional[str] = None
    extracted_entities: Optional[ExtractedEntities] = None
    question_type: Optional[str] = None
    clarification_mode: Optional[ClarificationMode] = None
    clarification_state: Optional[ClarificationState] = None
    missing_critical_info: Optional[List[str]] = None
    should_reprocess: bool = False
    original_question: Optional[str] = None
    validation_score: Optional[float] = None  # 🔧 NOUVEAU: Score de validation des questions
    validation_details: Optional[Dict[str, Any]] = None  # 🔧 NOUVEAU: Détails validation
    fallback_used: bool = False  # 🔧 NOUVEAU: Indicateur si fallback utilisé
    gpt_failed: bool = False  # 🔧 NOUVEAU: Indicateur si GPT a échoué
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour les logs"""
        return {
            "needs_clarification": self.needs_clarification,
            "questions": self.questions,
            "questions_count": len(self.questions) if self.questions else 0,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "reason": self.reason,
            "model_used": self.model_used,
            "extracted_entities": self.extracted_entities.to_dict() if self.extracted_entities else None,
            "question_type": self.question_type,
            "clarification_mode": self.clarification_mode.value if self.clarification_mode else None,
            "clarification_state": self.clarification_state.value if self.clarification_state else None,
            "missing_critical_info": self.missing_critical_info,
            "should_reprocess": self.should_reprocess,
            "original_question": self.original_question,
            "validation_score": self.validation_score,
            "validation_details": self.validation_details,
            "fallback_used": self.fallback_used,
            "gpt_failed": self.gpt_failed
        }

class EnhancedQuestionClarificationSystem:
    """
    Système de clarification intelligent AMÉLIORÉ avec validation GPT robuste intégrée
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
            self.intelligent_missing_detection = getattr(settings, 'intelligent_missing_detection', True)
            
            self.enable_semantic_dynamic = getattr(settings, 'enable_semantic_dynamic_clarification', True)
            self.semantic_dynamic_max_questions = getattr(settings, 'semantic_dynamic_max_questions', 4)
            
            # 🔧 NOUVEAU: Configuration validation GPT robuste
            self.enable_question_validation = getattr(settings, 'enable_question_validation', True)
            self.validation_threshold = getattr(settings, 'validation_threshold', 0.5)
            self.enable_intelligent_fallback = getattr(settings, 'enable_intelligent_fallback', True)
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
            self.intelligent_missing_detection = os.getenv('INTELLIGENT_MISSING_DETECTION', 'true').lower() == 'true'
            
            self.enable_semantic_dynamic = os.getenv('ENABLE_SEMANTIC_DYNAMIC_CLARIFICATION', 'true').lower() == 'true'
            self.semantic_dynamic_max_questions = int(os.getenv('SEMANTIC_DYNAMIC_MAX_QUESTIONS', '4'))
            
            # 🔧 NOUVEAU: Configuration validation GPT robuste
            self.enable_question_validation = os.getenv('ENABLE_QUESTION_VALIDATION', 'true').lower() == 'true'
            self.validation_threshold = float(os.getenv('VALIDATION_THRESHOLD', '0.5'))
            self.enable_intelligent_fallback = os.getenv('ENABLE_INTELLIGENT_FALLBACK', 'true').lower() == 'true'
        
           - Logs détaillés: métadonnées validation + fallback + erreurs
logger.info("✅ [EnhancedQuestionClarificationSystem] READY: Agent de clarification avec VALIDATION ROBUSTE + FALLBACK INTELLIGENT opérationnel!")(f"🔧 [Enhanced Clarification] Mode: {self.clarification_mode.value}")
        logger.info(f"🔧 [Enhanced Clarification] Extraction entités: {'✅' if self.smart_entity_extraction else '❌'}")
        logger.info(f"🔧 [Enhanced Clarification] Auto-reprocess: {'✅' if self.auto_reprocess_after_clarification else '❌'}")
        logger.info(f"🔧 [Enhanced Clarification] Questions adaptatives: {'✅' if self.adaptive_question_count else '❌'}")
        logger.info(f"🔧 [Enhanced Clarification] Validation GPT robuste: {'✅' if self.enable_question_validation else '❌'}")
        logger.info(f"🔧 [Enhanced Clarification] Fallback intelligent: {'✅' if self.enable_intelligent_fallback else '❌'}")
        logger.info(f"🆕 [Semantic Dynamic] Mode dynamique: {'✅' if self.enable_semantic_dynamic else '❌'}")
        
        self._init_patterns()
        self._init_enhanced_prompts()
        self._init_clarification_logger()

    def _init_patterns(self):
        """Patterns de détection améliorés"""
        
        # Races spécifiques (identiques)
        self.specific_breed_patterns = {
            "fr": [
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro'
            ],
            "en": [
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro'
            ],
            "es": [
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro'
            ]
        }
        
        # ✅ NOUVEAUX: Patterns pour classification de type de question
        self.question_type_patterns = {
            "growth": [r'croissance', r'growth', r'crecimiento', r'grossissent?', r'growing', r'crecen'],
            "weight": [r'poids', r'weight', r'peso', r'pèsent?', r'weigh', r'pesan', r'grammes?', r'grams?', r'gramos?'],
            "mortality": [r'mortalité', r'mortality', r'mortalidad', r'meurent', r'dying', r'mueren', r'dead', r'muerte'],
            "health": [r'maladie', r'disease', r'enfermedad', r'malade', r'sick', r'enfermo', r'santé', r'health', r'salud'],
            "temperature": [r'température', r'temperature', r'temperatura', r'chaud', r'hot', r'caliente', r'froid', r'cold', r'frío'],
            "feeding": [r'alimentation', r'feeding', r'alimentación', r'nourriture', r'food', r'comida', r'aliment'],
            "environment": [r'environnement', r'environment', r'ambiente', r'ventilation', r'humidity', r'humidité'],
            "performance": [r'performance', r'rendement', r'efficacité', r'efficiency', r'eficiencia', r'conversion']
        }

    # 🔧 MÉTHODE COMPLÈTEMENT RÉÉCRITE: Génération dynamique avec validation robuste intégrée
    def generate_dynamic_clarification_questions(self, user_question: str, language: str = "fr") -> Tuple[List[str], Dict[str, Any]]:
        """
        🆕 Génère jusqu'à 4 questions de clarification via GPT avec validation robuste automatique
        🔧 COMPLÈTEMENT RÉÉCRIT: Validation intégrée + fallback intelligent
        
        Returns:
            Tuple[List[str], Dict[str, Any]]: (questions_validées, métadonnées_validation)
        """
        
        validation_metadata = {
            "gpt_called": False,
            "gpt_success": False,
            "validation_performed": False,
            "validation_score": 0.0,
            "fallback_used": False,
            "fallback_reason": None,
            "questions_generated": 0,
            "questions_validated": 0
        }
        
        try:
            # Import dynamique du prompt template avec fallback
            try:
                from .prompt_templates import (
                    build_contextualization_prompt, 
                    validate_dynamic_questions,
                    get_dynamic_clarification_fallback_questions
                )
            except ImportError:
                logger.error("❌ [Semantic Dynamic] Impossible d'importer les templates - fallback direct")
                validation_metadata["fallback_used"] = True
                validation_metadata["fallback_reason"] = "import_error"
                fallback_questions = self._basic_fallback_questions(user_question, language)
                return fallback_questions, validation_metadata

            # Vérifier disponibilité OpenAI
            if not OPENAI_AVAILABLE or not openai:
                logger.warning("⚠️ [Semantic Dynamic] OpenAI non disponible - fallback intelligent")
                validation_metadata["fallback_used"] = True
                validation_metadata["fallback_reason"] = "openai_unavailable"
                fallback_questions = get_dynamic_clarification_fallback_questions(user_question, language)
                return fallback_questions, validation_metadata

            # Configuration OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("⚠️ [Semantic Dynamic] Clé API OpenAI manquante - fallback intelligent")
                validation_metadata["fallback_used"] = True
                validation_metadata["fallback_reason"] = "api_key_missing"
                fallback_questions = get_dynamic_clarification_fallback_questions(user_question, language)
                return fallback_questions, validation_metadata
            
            openai.api_key = api_key

            # Construire le prompt contextualisé amélioré
            prompt = build_contextualization_prompt(user_question, language)
            logger.info(f"🤖 [Clarification-Dynamique] Prompt généré pour: '{user_question[:50]}...'")
            logger.debug(f"🤖 [Clarification-Dynamique] Prompt complet:\n{prompt}")

            # Appel GPT pour génération dynamique
            validation_metadata["gpt_called"] = True
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un expert en aviculture spécialisé dans la génération de questions pertinentes et précises."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300,
                timeout=self.timeout
            )
            
            content = response.choices[0].message.content.strip()
            validation_metadata["gpt_success"] = True
            
            logger.info(f"🤖 [Clarification-Dynamique] Réponse brute reçue ({len(content)} chars)")
            logger.debug(f"🤖 [Clarification-Dynamique] Contenu: {content}")
            
            # Parser la réponse JSON avec fallback amélioré
            questions = []
            try:
                json_match = re.search(r'\{.*?\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    questions = data.get("clarification_questions", [])
                    validation_metadata["questions_generated"] = len(questions)
                    
                    logger.info(f"🤖 [Clarification-Dynamique] {len(questions)} questions extraites du JSON")
                else:
                    logger.warning("⚠️ [Semantic Dynamic] Pas de JSON trouvé - extraction texte libre")
                    questions = self._extract_questions_from_text(content, language)
                    validation_metadata["questions_generated"] = len(questions)
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ [Semantic Dynamic] Erreur parsing JSON: {e}")
                logger.debug(f"Contenu problématique: {content}")
                questions = self._extract_questions_from_text(content, language)
                validation_metadata["questions_generated"] = len(questions)
            
            # 🔧 NOUVEAU: Validation robuste des questions générées
            if self.enable_question_validation and questions:
                validation_metadata["validation_performed"] = True
                
                validation_result = validate_dynamic_questions(questions, user_question, language)
                validation_metadata["validation_score"] = validation_result.get("quality_score", 0.0)
                
                logger.info(f"🔧 [Question Validation] Score qualité: {validation_metadata['validation_score']:.2f}")
                logger.info(f"🔧 [Question Validation] Questions valides: {len(validation_result.get('valid_questions', []))}/{len(questions)}")
                
                # Vérifier si validation échoue
                if validation_metadata["validation_score"] < self.validation_threshold:
                    logger.warning(f"⚠️ [Question Validation] Score trop bas ({validation_metadata['validation_score']:.2f} < {self.validation_threshold})")
                    
                    valid_questions = validation_result.get("valid_questions", [])
                    if valid_questions and len(valid_questions) >= 1:
                        logger.info(f"🔧 [Question Validation] Utilisation des {len(valid_questions)} questions valides")
                        questions = valid_questions[:self.semantic_dynamic_max_questions]
                        validation_metadata["questions_validated"] = len(questions)
                    else:
                        logger.warning("⚠️ [Question Validation] Aucune question valide - fallback intelligent")
                        if self.enable_intelligent_fallback:
                            validation_metadata["fallback_used"] = True
                            validation_metadata["fallback_reason"] = "validation_failed"
                            fallback_questions = get_dynamic_clarification_fallback_questions(user_question, language)
                            return fallback_questions, validation_metadata
                        else:
                            questions = []
                else:
                    # Validation réussie - utiliser les questions valides
                    questions = validation_result.get("valid_questions", questions)[:self.semantic_dynamic_max_questions]
                    validation_metadata["questions_validated"] = len(questions)
                    
            else:
                # Pas de validation - nettoyage basique
                cleaned_questions = []
                for q in questions[:self.semantic_dynamic_max_questions]:
                    if isinstance(q, str) and len(q.strip()) > 10:
                        cleaned_q = q.strip()
                        if not cleaned_q.endswith('?'):
                            cleaned_q += ' ?'
                        cleaned_questions.append(cleaned_q)
                questions = cleaned_questions
                validation_metadata["questions_validated"] = len(questions)
            
            if questions:
                logger.info(f"✅ [Semantic Dynamic] {len(questions)} questions générées et validées avec succès")
                return questions, validation_metadata
            else:
                logger.warning("⚠️ [Semantic Dynamic] Aucune question finale valide - fallback intelligent")
                if self.enable_intelligent_fallback:
                    validation_metadata["fallback_used"] = True
                    validation_metadata["fallback_reason"] = "no_final_questions"
                    fallback_questions = get_dynamic_clarification_fallback_questions(user_question, language)
                    return fallback_questions, validation_metadata
                else:
                    return [], validation_metadata
            
        except Exception as e:
            logger.error(f"❌ [Semantic Dynamic] Erreur génération questions de clarification: {e}")
            validation_metadata["fallback_used"] = True
            validation_metadata["fallback_reason"] = f"exception: {str(e)}"
            
            if self.enable_intelligent_fallback:
                try:
                    from .prompt_templates import get_dynamic_clarification_fallback_questions
                    fallback_questions = get_dynamic_clarification_fallback_questions(user_question, language)
                    return fallback_questions, validation_metadata
                except ImportError:
                    return self._basic_fallback_questions(user_question, language), validation_metadata
            else:
                return [], validation_metadata

    def _extract_questions_from_text(self, text: str, language: str) -> List[str]:
        """Extrait les questions depuis un texte libre si JSON parsing échoue (AMÉLIORÉ)"""
        
        questions = []
        lines = text.split('\n')
        
        # Mots-clés de questions par langue pour validation
        question_keywords = {
            "fr": ['quel', 'quelle', 'comment', 'combien', 'où', 'quand', 'pourquoi', 'depuis quand'],
            "en": ['what', 'how', 'which', 'where', 'when', 'why', 'how long', 'what type'],
            "es": ['qué', 'cuál', 'cómo', 'dónde', 'cuándo', 'por qué', 'cuánto tiempo', 'qué tipo']
        }
        
        keywords = question_keywords.get(language, question_keywords["fr"])
        
        for line in lines:
            line = line.strip()
            
            # Vérifier que la ligne ressemble à une question
            if ('?' in line or 
                any(word in line.lower() for word in keywords)):
                
                # Nettoyer la ligne
                cleaned = re.sub(r'^[-•*\d]+\.?\s*', '', line)  # Supprimer puces/numéros
                cleaned = cleaned.strip()
                
                # Vérifications de qualité améliorées
                if (len(cleaned) > 15 and 
                    len(cleaned) < 150 and 
                    len(questions) < self.semantic_dynamic_max_questions and
                    cleaned not in questions):
                    
                    # Éviter les questions trop génériques
                    generic_words = ['exemple', 'example', 'ejemplo', 'etc', 'généralement', 'usually']
                    if not any(generic in cleaned.lower() for generic in generic_words):
                        if not cleaned.endswith('?'):
                            cleaned += ' ?'
                        questions.append(cleaned)
        
        logger.info(f"📝 [Semantic Dynamic] Questions extraites du texte libre: {len(questions)}")
        return questions

    def _basic_fallback_questions(self, user_question: str, language: str) -> List[str]:
        """Questions de fallback basiques si tout échoue (NOUVEAU)"""
        
        basic_fallbacks = {
            "fr": [
                "Pouvez-vous préciser la race ou souche de vos volailles ?",
                "Quel âge ont actuellement vos animaux ?", 
                "Dans quel contexte d'élevage vous trouvez-vous ?"
            ],
            "en": [
                "Could you specify the breed or strain of your poultry?",
                "What age are your animals currently?",
                "What farming context are you in?"
            ],
            "es": [
                "¿Podría especificar la raza o cepa de sus aves?",
                "¿Qué edad tienen actualmente sus animales?",
                "¿En qué contexto de cría se encuentra?"
            ]
        }
        
        questions = basic_fallbacks.get(language, basic_fallbacks["fr"])
        logger.info(f"🔄 [Fallback Basique] Questions de base utilisées ({language}): {len(questions)}")
        return questions

    async def extract_entities_intelligent(self, question: str, language: str, conversation_context: Dict = None) -> ExtractedEntities:
        """✅ NOUVEAU: Extraction intelligente d'entités via OpenAI (CONSERVÉ IDENTIQUE)"""
        
        if not self.smart_entity_extraction or not OPENAI_AVAILABLE or not openai:
            logger.warning("⚠️ [Enhanced Clarification] Extraction intelligente désactivée ou OpenAI indisponible")
            return await self._extract_entities_fallback(question, language)
        
        try:
            # Construire le contexte pour l'extraction
            context_info = ""
            if conversation_context:
                context_info = f"\n\nContexte conversationnel disponible:\n{json.dumps(conversation_context, ensure_ascii=False, indent=2)}"
            
            extraction_prompt = f"""Tu es un expert en extraction d'informations pour l'aviculture. Extrait TOUTES les informations pertinentes de cette question et du contexte.

Question: "{question}"{context_info}

CONSIGNE: Extrait les informations sous format JSON strict. Utilise null pour les valeurs manquantes.

```json
{{
  "breed": "race spécifique (ex: Ross 308) ou null",
  "breed_type": "specific/generic/null",
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
```

IMPORTANT: 
- Si une race générique est mentionnée (poulet, volaille), breed_type = "generic"
- Si une race spécifique est mentionnée (Ross 308), breed_type = "specific"
- Convertir les semaines en jours si nécessaire (1 semaine = 7 jours)
- Être très précis sur les valeurs numériques"""

            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return await self._extract_entities_fallback(question, language)
            
            openai.api_key = api_key
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un extracteur d'entités expert en aviculture. Réponds uniquement avec du JSON valide."},
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
                # Fallback: chercher directement du JSON
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
                
                logger.info(f"🤖 [Enhanced Clarification] Entités extraites intelligemment: {entities.to_dict()}")
                return entities
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ [Enhanced Clarification] Erreur parsing JSON: {e}")
                return await self._extract_entities_fallback(question, language)
        
        except Exception as e:
            logger.error(f"❌ [Enhanced Clarification] Erreur extraction intelligente: {e}")
            return await self._extract_entities_fallback(question, language)

    async def _extract_entities_fallback(self, question: str, language: str) -> ExtractedEntities:
        """Extraction d'entités fallback (règles basiques) (CONSERVÉ IDENTIQUE)"""
        
        entities = ExtractedEntities()
        question_lower = question.lower()
        
        # Détection race spécifique
        specific_patterns = self.specific_breed_patterns.get(language, self.specific_breed_patterns["fr"])
        for pattern in specific_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                entities.breed = match.group(0).strip()
                entities.breed_type = "specific"
                break
        
        # Détection race générique si pas spécifique
        if not entities.breed:
            generic_patterns = [r'poulets?', r'volailles?', r'chickens?', r'poultry', r'pollos?', r'aves?']
            for pattern in generic_patterns:
                match = re.search(pattern, question_lower, re.IGNORECASE)
                if match:
                    entities.breed = match.group(0).strip()
                    entities.breed_type = "generic"
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
        
        # Détection mortalité
        mortality_patterns = [
            r'mortalité\s+(?:de\s+)?(\d+(?:\.\d+)?)%?',
            r'mortality\s+(?:of\s+)?(\d+(?:\.\d+)?)%?',
            r'(\d+(?:\.\d+)?)%\s+mortalit[éy]'
        ]
        
        for pattern in mortality_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                entities.mortality_rate = float(match.group(1))
                break
        
        return entities

    def classify_question_type(self, question: str, language: str) -> str:
        """✅ NOUVEAU: Classifie le type de question (CONSERVÉ IDENTIQUE)"""
        
        question_lower = question.lower()
        
        for question_type, patterns in self.question_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower, re.IGNORECASE):
                    return question_type
        
        return "general"

    def _init_enhanced_prompts(self):
        """✅ NOUVEAUX PROMPTS AMÉLIORÉS avec gestion du contexte (CONSERVÉ IDENTIQUE)"""
        
        self.clarification_prompts = {
            "fr": """Tu es un expert vétérinaire spécialisé en aviculture. Analyse cette question et le contexte pour déterminer si des clarifications sont nécessaires.

Question: "{question}"
Type de question détecté: {question_type}
Entités extraites: {extracted_entities}
Contexte conversationnel: {conversation_context}
Informations critiques manquantes: {missing_info}

RÈGLES STRICTES:
1. Si TOUTES les informations critiques sont présentes → réponds "CLEAR"
2. Si des informations critiques manquent → génère des questions PRÉCISES
3. Adapte le nombre de questions au nombre d'informations manquantes
4. Priorise les informations les plus critiques pour ce type de question

INFORMATIONS CRITIQUES PAR TYPE:
- Questions de poids/croissance: race spécifique + âge OBLIGATOIRES
- Questions de santé/mortalité: race + âge + symptômes
- Questions d'environnement: race + âge + conditions actuelles
- Questions d'alimentation: race + âge + type d'aliment actuel

Si clarification nécessaire, pose des questions TRÈS SPÉCIFIQUES:
- Pour la race: "Quelle race/lignée exacte (Ross 308, Cobb 500, etc.) ?"
- Pour l'âge: "Quel âge exact en jours ?"
- Pour les symptômes: "Quels symptômes précis observez-vous ?"

IMPORTANT: 
- Ne pose QUE les questions pour les informations vraiment manquantes
- Utilise le contexte conversationnel pour éviter de redemander des infos déjà connues
- Sois très précis dans tes questions

Format: soit "CLEAR" soit liste de questions avec tirets.""",

            "en": """You are a veterinary expert specialized in poultry farming. Analyze this question and context to determine if clarifications are needed.

Question: "{question}"
Detected question type: {question_type}
Extracted entities: {extracted_entities}
Conversational context: {conversation_context}
Missing critical information: {missing_info}

STRICT RULES:
1. If ALL critical information is present → answer "CLEAR"
2. If critical information is missing → generate PRECISE questions
3. Adapt number of questions to missing information count
4. Prioritize most critical information for this question type

CRITICAL INFORMATION BY TYPE:
- Weight/growth questions: specific breed + age MANDATORY
- Health/mortality questions: breed + age + symptoms
- Environment questions: breed + age + current conditions
- Feeding questions: breed + age + current feed type

If clarification needed, ask VERY SPECIFIC questions:
- For breed: "What exact breed/line (Ross 308, Cobb 500, etc.)?"
- For age: "What exact age in days?"
- For symptoms: "What specific symptoms do you observe?"

IMPORTANT:
- Only ask questions for truly missing information
- Use conversational context to avoid re-asking known information
- Be very precise in your questions

Format: either "CLEAR" or bulleted question list.""",

            "es": """Eres un experto veterinario especializado en avicultura. Analiza esta pregunta y contexto para determinar si se necesitan aclaraciones.

Pregunta: "{question}"
Tipo de pregunta detectado: {question_type}
Entidades extraídas: {extracted_entities}
Contexto conversacional: {conversation_context}
Información crítica faltante: {missing_info}

REGLAS ESTRICTAS:
1. Si TODA la información crítica está presente → responde "CLEAR"
2. Si falta información crítica → genera preguntas PRECISAS
3. Adapta el número de preguntas a la información faltante
4. Prioriza la información más crítica para este tipo de pregunta

INFORMACIÓN CRÍTICA POR TIPO:
- Preguntas peso/crecimiento: raza específica + edad OBLIGATORIAS
- Preguntas salud/mortalidad: raza + edad + síntomas
- Preguntas ambiente: raza + edad + condiciones actuales
- Preguntas alimentación: raza + edad + tipo alimento actual

Si necesita aclaración, haz preguntas MUY ESPECÍFICAS:
- Para raza: "¿Qué raza/línea exacta (Ross 308, Cobb 500, etc.)?"
- Para edad: "¿Qué edad exacta en días?"
- Para síntomas: "¿Qué síntomas específicos observa?"

IMPORTANTE:
- Solo pregunta por información realmente faltante
- Usa el contexto conversacional para evitar preguntar información ya conocida
- Sé muy preciso en tus preguntas

Formato: "CLEAR" o lista de preguntas con guiones."""
        }

    def _init_clarification_logger(self):
        """Initialise le logger spécialisé pour les clarifications (CONSERVÉ IDENTIQUE)"""
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
        ✅ ANALYSE AMÉLIORÉE avec extraction intelligente et gestion du contexte
        🆕 NOUVEAU: Support mode sémantique dynamique
        🔧 AMÉLIORÉ: Gestion complète des erreurs avec validation robuste
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
        
        # ✅ NOUVEAU: Classification du type de question
        question_type = self.classify_question_type(question, language)
        logger.info(f"🏷️ [Enhanced Clarification] Type de question: {question_type}")
        
        # ✅ NOUVEAU: Extraction intelligente d'entités
        extracted_entities = await self.extract_entities_intelligent(
            question, 
            language, 
            conversation_context
        )
        
        logger.info(f"🔍 [Enhanced Clarification] Analyse: '{question[:80]}...'")
        logger.info(f"📊 [Enhanced Clarification] Entités extraites: {extracted_entities.to_dict()}")
        
        # 🆕 NOUVEAU: Gestion du mode sémantique dynamique avec validation robuste
        if (mode == "semantic_dynamic" or 
            self.clarification_mode == ClarificationMode.SEMANTIC_DYNAMIC) and \
           self.enable_semantic_dynamic:
            
            logger.info(f"🎯 [Semantic Dynamic] Mode activé pour: '{question[:50]}...'")
            
            # Générer questions dynamiques avec métadonnées de validation
            dynamic_questions, validation_metadata = self.generate_dynamic_clarification_questions(question, language)
            
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
                    missing_critical_info=["context_understanding"],
                    confidence_score=0.9,
                    original_question=original_question or question,
                    validation_score=validation_metadata.get("validation_score", 0.8),
                    validation_details=validation_metadata,
                    fallback_used=validation_metadata.get("fallback_used", False),
                    gpt_failed=not validation_metadata.get("gpt_success", False)
                )
                
                logger.info(f"✅ [Semantic Dynamic] {len(dynamic_questions)} questions générées dynamiquement")
                logger.info(f"🔧 [Validation Metadata] GPT: {'✅' if validation_metadata.get('gpt_success') else '❌'}, " +
                           f"Validation: {'✅' if validation_metadata.get('validation_performed') else '❌'}, " +
                           f"Fallback: {'✅' if validation_metadata.get('fallback_used') else '❌'}")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            else:
                logger.warning("⚠️ [Semantic Dynamic] Aucune question générée, fallback vers mode normal")
        
        # ✅ NOUVEAU: Déterminer les informations critiques manquantes
        missing_critical_info = extracted_entities.get_missing_critical_info(question_type)
        logger.info(f"❌ [Enhanced Clarification] Informations critiques manquantes: {missing_critical_info}")
        
        # ✅ NOUVEAU: Logique de clarification intelligente
        if extracted_entities.breed_type == "generic":
            logger.info(f"🚨 [Enhanced Clarification] Race générique détectée - clarification obligatoire")
            
            generic_questions = self._generate_adaptive_clarification_questions(
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
                gpt_failed=False
            )
        
        # ✅ NOUVEAU: Si race spécifique + âge présents = OK
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
                gpt_failed=False
            )
        
        # ✅ NOUVEAU: Si pas d'informations critiques manquantes
        if not missing_critical_info:
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
                gpt_failed=False
            )
        
        # ✅ ANALYSE VIA OpenAI pour les cas complexes avec gestion d'erreur robuste
        if not OPENAI_AVAILABLE or not openai:
            logger.warning(f"⚠️ [Enhanced Clarification] OpenAI non disponible - fallback vers questions adaptatives")
            
            adaptive_questions = self._generate_adaptive_clarification_questions(
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
                gpt_failed=True
            )
        
        try:
            # ✅ Configuration OpenAI avec gestion d'erreur
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning(f"⚠️ [Enhanced Clarification] Clé API OpenAI manquante - fallback adaptatif")
                
                adaptive_questions = self._generate_adaptive_clarification_questions(
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
                    gpt_failed=True
                )
            
            openai.api_key = api_key
            
            # ✅ PROMPT ENRICHI avec toutes les informations
            prompt_template = self.clarification_prompts.get(language.lower(), self.clarification_prompts["fr"])
            
            context_str = json.dumps(conversation_context, ensure_ascii=False) if conversation_context else "Aucun contexte"
            entities_str = json.dumps(extracted_entities.to_dict(), ensure_ascii=False)
            missing_info_str = ", ".join(missing_critical_info) if missing_critical_info else "Aucune"
            
            user_prompt = prompt_template.format(
                question=question,
                question_type=question_type,
                extracted_entities=entities_str,
                conversation_context=context_str,
                missing_info=missing_info_str
            )
            
            system_prompt = f"""Tu es un assistant expert qui détermine si une question d'aviculture nécessite des clarifications. 

Mode de clarification: {self.clarification_mode.value}
Questions adaptatives: {'activées' if self.adaptive_question_count else 'désactivées'}

Sois très précis et utilise intelligemment le contexte conversationnel pour éviter les questions redondantes."""
            
            # ✅ Appel OpenAI enrichi
            logger.info(f"🤖 [Enhanced Clarification] Appel GPT-4o-mini enrichi...")
            
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
                    gpt_failed=False
                )
                
                logger.info(f"✅ [Enhanced Clarification] Question claire selon GPT-4o-mini enrichi")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            
            # Extraire les questions de clarification
            clarification_questions = self._extract_questions(answer)
            
            # ✅ NOUVEAU: Limitation adaptative du nombre de questions
            if self.adaptive_question_count:
                max_questions = min(len(missing_critical_info) + 1, self.max_questions)
            else:
                max_questions = self.max_questions
            
            if clarification_questions and len(clarification_questions) > 0:
                limited_questions = clarification_questions[:max_questions]
                
                # ✅ NOUVEAU: Mode de clarification
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
                    validation_score=0.8,  # Score par défaut pour questions GPT
                    fallback_used=False,
                    gpt_failed=False
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
                    gpt_failed=False
                )
        
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ [Enhanced Clarification] Erreur GPT-4o-mini: {e}")
            
            # 🔧 NOUVEAU: Fallback intelligent en cas d'erreur GPT
            if self.enable_intelligent_fallback:
                logger.info(f"🔄 [Enhanced Clarification] Fallback intelligent activé suite à erreur GPT")
                
                adaptive_questions = self._generate_adaptive_clarification_questions(
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
                    gpt_failed=True
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
                    gpt_failed=True
                )

    def _generate_adaptive_clarification_questions(
        self, 
        language: str, 
        missing_info: List[str], 
        question_type: str
    ) -> List[str]:
        """✅ NOUVEAU: Génère des questions adaptatives selon les informations manquantes (CONSERVÉ IDENTIQUE)"""
        
        question_templates = {
            "fr": {
                "breed": "Quelle est la race/lignée exacte de vos poulets (Ross 308, Cobb 500, Hubbard, etc.) ?",
                "age": "Quel âge ont-ils actuellement (en jours précis) ?",
                "symptoms": "Quels symptômes spécifiques observez-vous ?",
                "housing": "Dans quel type d'élevage sont-ils logés (bâtiment fermé, semi-ouvert, plein air) ?",
                "feed": "Quel type d'alimentation utilisez-vous actuellement ?",
                "duration": "Depuis combien de temps observez-vous ce problème ?",
                "conditions": "Quelles sont les conditions environnementales actuelles (température, humidité) ?"
            },
            "en": {
                "breed": "What is the exact breed/line of your chickens (Ross 308, Cobb 500, Hubbard, etc.)?",
                "age": "How old are they currently (in precise days)?",
                "symptoms": "What specific symptoms do you observe?",
                "housing": "What type of housing are they in (closed building, semi-open, free-range)?",
                "feed": "What type of feed are you currently using?",
                "duration": "How long have you been observing this problem?",
                "conditions": "What are the current environmental conditions (temperature, humidity)?"
            },
            "es": {
                "breed": "¿Cuál es la raza/línea exacta de sus pollos (Ross 308, Cobb 500, Hubbard, etc.)?",
                "age": "¿Qué edad tienen actualmente (en días precisos)?",
                "symptoms": "¿Qué síntomas específicos observa?",
                "housing": "¿En qué tipo de alojamiento están (edificio cerrado, semi-abierto, campo libre)?",
                "feed": "¿Qué tipo de alimentación está usando actualmente?",
                "duration": "¿Desde cuándo observa este problema?",
                "conditions": "¿Cuáles son las condiciones ambientales actuales (temperatura, humedad)?"
            }
        }
        
        templates = question_templates.get(language, question_templates["fr"])
        questions = []
        
        # Priorise selon le type de question
        priority_mapping = {
            "growth": ["breed", "age"],
            "weight": ["breed", "age"],
            "health": ["breed", "age", "symptoms"],
            "mortality": ["breed", "age", "symptoms", "duration"],
            "environment": ["breed", "age", "conditions"],
            "feeding": ["breed", "age", "feed"],
            "performance": ["breed", "age"]
        }
        
        priority_order = priority_mapping.get(question_type, ["breed", "age"])
        
        # Ajouter les questions dans l'ordre de priorité
        for info_type in priority_order:
            if info_type in missing_info and info_type in templates:
                questions.append(templates[info_type])
        
        # Ajouter les autres informations manquantes
        for info_type in missing_info:
            if info_type in templates and templates[info_type] not in questions:
                questions.append(templates[info_type])
        
        return questions[:self.max_questions]

    def _extract_questions(self, answer: str) -> List[str]:
        """Extrait les questions de clarification de la réponse GPT (CONSERVÉ IDENTIQUE)"""
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
        """✅ AMÉLIORÉ: Score de confiance plus intelligent avec entités (CONSERVÉ IDENTIQUE)"""
        
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
            "mortality": 15 if not extracted_entities.mortality_rate else 0
        }
        
        base_score += critical_info_bonus.get(question_type, 5)
        
        # Malus si beaucoup d'informations déjà présentes
        extracted_count = len([v for v in extracted_entities.to_dict().values() if v is not None])
        if extracted_count > 3:
            base_score -= 10
        
        return min(base_score, 95.0)

    async def check_for_reprocessing(
        self,
        conversation_id: str,
        user_response: str,
        original_clarification_result: ClarificationResult
    ) -> Optional[ClarificationResult]:
        """
        ✅ NOUVEAU: Vérifie si la question originale peut être retraitée après clarification (CONSERVÉ IDENTIQUE)
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
            language="fr",  # À améliorer: récupérer la langue du contexte
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
        """✅ NOUVEAU: Formatage enrichi selon le mode de clarification (CONSERVÉ IDENTIQUE)"""
        
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
        
        if mode == ClarificationMode.INTERACTIVE or len(result.questions) == 1:
            # Mode interactif ou une seule question
            return f"{intro}\n\n{result.questions[0]}{outro}"
        else:
            # Mode batch - plusieurs questions
            formatted_questions = "\n".join([f"• {q}" for q in result.questions])
            return f"{intro}\n\n{formatted_questions}{outro}"

    async def _log_clarification_decision(
        self,
        question: str,
        language: str,
        user_id: str,
        conversation_id: str,
        result: ClarificationResult
    ):
        """Log détaillé des décisions de clarification enrichi avec validation (AMÉLIORÉ)"""
        
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
                "min_question_length": self.min_question_length,
                "clarification_mode": self.clarification_mode.value,
                "smart_entity_extraction": self.smart_entity_extraction,
                "auto_reprocess_after_clarification": self.auto_reprocess_after_clarification,
                "adaptive_question_count": self.adaptive_question_count,
                "enable_semantic_dynamic": self.enable_semantic_dynamic,
                "semantic_dynamic_max_questions": self.semantic_dynamic_max_questions,
                "enable_question_validation": self.enable_question_validation,
                "validation_threshold": self.validation_threshold,
                "enable_intelligent_fallback": self.enable_intelligent_fallback
            }
        }
        
        # Log structuré
        self.clarification_logger.info(json.dumps(clarification_data, ensure_ascii=False))
        
        # Log standard enrichi avec informations de validation
        if result.needs_clarification:
            logger.info(
                f"❓ [Enhanced Clarification] CLARIFICATION - "
                f"User: {user_id[:8]} | Type: {result.question_type} | "
                f"Questions: {len(result.questions)} | Mode: {result.clarification_mode.value if result.clarification_mode else 'N/A'} | "
                f"Missing: {result.missing_critical_info} | "
                f"Modèle: {result.model_used} | "
                f"Confiance: {result.confidence_score:.1f}% | "
                f"Validation: {result.validation_score:.1f} | "
                f"Fallback: {'✅' if result.fallback_used else '❌'} | "
                f"GPT: {'❌' if result.gpt_failed else '✅'} | "
                f"Temps: {result.processing_time_ms}ms"
            )
        else:
            logger.info(
                f"✅ [Enhanced Clarification] CLEAR - "
                f"User: {user_id[:8]} | Type: {result.question_type} | "
                f"Raison: {result.reason} | "
                f"Entités: {len(result.extracted_entities.to_dict()) if result.extracted_entities else 0} | "
                f"Modèle: {result.model_used} | "
                f"Validation: {result.validation_score:.1f} | "
                f"Fallback: {'✅' if result.fallback_used else '❌'} | "
                f"GPT: {'❌' if result.gpt_failed else '✅'} | "
                f"Temps: {result.processing_time_ms}ms"
            )

    def get_stats_enhanced(self) -> Dict:
        """Retourne les statistiques du système enrichi avec nouvelles fonctionnalités (AMÉLIORÉ)"""
        return {
            "enabled": self.enabled,
            "model": self.model,
            "timeout": self.timeout,
            "max_questions": self.max_questions,
            "min_question_length": self.min_question_length,
            "confidence_threshold": self.confidence_threshold,
            "log_all_clarifications": self.log_all_clarifications,
            "openai_available": OPENAI_AVAILABLE,
            "supported_languages": list(self.clarification_prompts.keys()),
            "settings_source": "intelia_settings" if SETTINGS_AVAILABLE else "environment_variables",
            
            # ✅ NOUVELLES STATISTIQUES
            "clarification_mode": self.clarification_mode.value,
            "smart_entity_extraction": self.smart_entity_extraction,
            "auto_reprocess_after_clarification": self.auto_reprocess_after_clarification,
            "adaptive_question_count": self.adaptive_question_count,
            "intelligent_missing_detection": self.intelligent_missing_detection,
            "question_types_supported": list(self.question_type_patterns.keys()),
            "entity_types_extracted": [
                "breed", "age_days", "weight_grams", "mortality_rate", 
                "temperature", "humidity", "housing_type", "feed_type", 
                "symptoms", "duration_problem", "previous_treatments"
            ],
            "clarification_modes_available": [mode.value for mode in ClarificationMode],
            "clarification_states_available": [state.value for state in ClarificationState],
            
            # 🆕 NOUVELLES STATISTIQUES MODE SÉMANTIQUE DYNAMIQUE
            "semantic_dynamic_enabled": self.enable_semantic_dynamic,
            "semantic_dynamic_max_questions": self.semantic_dynamic_max_questions,
            "semantic_dynamic_available": OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY')),
            
            # 🔧 NOUVELLES STATISTIQUES VALIDATION GPT ROBUSTE
            "question_validation_enabled": self.enable_question_validation,
            "validation_threshold": self.validation_threshold,
            "validation_available": OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY')),
            "intelligent_fallback_enabled": self.enable_intelligent_fallback,
            
            # 🔧 NOUVELLES STATISTIQUES GESTION D'ERREURS
            "error_handling_features": {
                "openai_unavailable_fallback": True,
                "api_key_missing_fallback": True,
                "gpt_error_fallback": self.enable_intelligent_fallback,
                "validation_failure_fallback": self.enable_intelligent_fallback,
                "json_parsing_fallback": True,
                "question_extraction_fallback": True
            },
            
            # 🔧 STATISTIQUES FALLBACK
            "fallback_strategies": {
                "adaptive_clarification_questions": True,
                "basic_fallback_questions": True,
                "intelligent_question_selection": True,
                "type_specific_fallbacks": True
            }
        }

# ==================== INSTANCE GLOBALE AMÉLIORÉE ====================

# Instance singleton du système de clarification AMÉLIORÉ avec validation robuste
enhanced_clarification_system = EnhancedQuestionClarificationSystem()

# ==================== FONCTIONS UTILITAIRES AMÉLIORÉES ====================

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

# 🆕 NOUVELLE FONCTION: Mode sémantique dynamique
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
    """Construit une question enrichie avec les réponses de clarification (version améliorée)"""
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

# 🆕 NOUVELLE FONCTION: Génération directe de questions dynamiques avec validation
def generate_dynamic_clarification_questions_with_validation(question: str, language: str = "fr") -> Tuple[List[str], Dict[str, Any]]:
    """Génère dynamiquement des questions de clarification avec validation robuste"""
    return enhanced_clarification_system.generate_dynamic_clarification_questions(question, language)

# ==================== LOGGING DE DÉMARRAGE AMÉLIORÉ ====================

logger.info("❓ [EnhancedQuestionClarificationSystem] Module COMPLÈTEMENT RÉÉCRIT avec VALIDATION ROBUSTE initialisé")
logger.info(f"📊 [EnhancedQuestionClarificationSystem] Statistiques: {enhanced_clarification_system.get_stats_enhanced()}")
logger.info("✅ [EnhancedQuestionClarificationSystem] FONCTIONNALITÉS CONSERVÉES:")
logger.info("   - 🤖 Extraction intelligente d'entités via OpenAI")
logger.info("   - 🔄 Retraitement automatique après clarification")
logger.info("   - 🎯 Clarification adaptative (1 question si 1 info manque)")
logger.info("   - 🧠 Gestion avancée du contexte conversationnel")
logger.info("   - 📊 Classification automatique des types de questions")
logger.info("   - 🎛️ Modes de clarification multiples (batch/interactive/adaptive)")
logger.info("   - 📈 Prompts optimisés pour données numériques")
logger.info("   - 🔍 Détection intelligente des informations critiques manquantes")
logger.info("🆕 [EnhancedQuestionClarificationSystem] MODE SÉMANTIQUE DYNAMIQUE CONSERVÉ:")
logger.info("   - 🎭 Génération GPT de 1-4 questions contextuelles")
logger.info("   - 🤖 Prompt contextualisé pour questions métier intelligentes")
logger.info("   - 🔄 Fallback automatique si génération échoue")
logger.info("   - ⚙️ Configuration flexible (enable_semantic_dynamic, max_questions)")
logger.info("🔧 [EnhancedQuestionClarificationSystem] NOUVELLES FONCTIONNALITÉS VALIDATION ROBUSTE:")
logger.info("   - ✅ Validation automatique complète des questions générées par GPT")
logger.info("   - 🎯 Filtrage avancé: longueur, mots-clés, phrases interdites, doublons")
logger.info("   - 📊 Score de qualité détaillé (0.0 à 1.0) avec bonus diversité/spécificité")
logger.info("   - 🚫 Détection reformulations, exemples génériques, questions non pertinentes")
logger.info("   - 🔄 Fallback intelligent par type de question si validation échoue")
logger.info("   - 📈 Métadonnées validation complètes dans les résultats")
logger.info("🔧 [EnhancedQuestionClarificationSystem] GESTION D'ERREURS COMPLÈTE:")
logger.info("   - 🛡️ Fallback si OpenAI indisponible → Questions adaptatives")
logger.info("   - 🛡️ Fallback si clé API manquante → Questions adaptatives")
logger.info("   - 🛡️ Fallback si erreur GPT → Questions adaptatives (si enabled)")
logger.info("   - 🛡️ Fallback si validation échoue → Questions par type")
logger.info("   - 🛡️ Fallback si JSON parsing échoue → Extraction texte libre")
logger.info("   - 🛡️ Fallback si imports échouent → Questions de base")
logger.info("   - 📊 Traçabilité complète: gpt_failed, fallback_used dans résultats")
logger.info("✨ [EnhancedQuestionClarificationSystem] RÉSULTAT FINAL:")
logger.info('   - Question floue: "J\'ai un problème avec mes poulets"')
logger.info('   - Génération GPT: 3-4 questions contextuelles')
logger.info('   - Validation robuste: score qualité > seuil configurable')
logger.info('   - Si échec: fallback intelligent par type de question')
logger.info('   - Si erreur technique: fallback adaptatif garanti')
logger.info