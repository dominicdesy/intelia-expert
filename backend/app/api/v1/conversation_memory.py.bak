"""
app/api/v1/question_clarification_system.py - VERSION CORRIGÉE AVEC GPT-4o-mini

CORRECTIONS MAJEURES:
1. GPT-4o-mini par défaut pour meilleure intelligence
2. Prompts plus stricts et exigeants
3. Seuils optimisés pour moins de faux positifs
4. Meilleure détection des races génériques vs spécifiques
5. Système de validation renforcé
"""

import os
import re
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

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

@dataclass
class ClarificationResult:
    """Résultat de l'analyse de clarification"""
    needs_clarification: bool
    questions: Optional[List[str]] = None
    confidence_score: float = 0.0
    processing_time_ms: int = 0
    reason: Optional[str] = None
    model_used: Optional[str] = None
    detected_info: Optional[Dict[str, str]] = None
    
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
            "detected_info": self.detected_info
        }

class QuestionClarificationSystem:
    """
    Système de clarification intelligent CORRIGÉ avec GPT-4o-mini.
    Plus strict et précis pour éviter les faux positifs.
    """
    
    def __init__(self):
        """Initialise le système avec GPT-4o-mini et configuration stricte"""
        
        # ✅ NOUVELLE CONFIGURATION OPTIMISÉE
        if SETTINGS_AVAILABLE and settings:
            self.enabled = getattr(settings, 'clarification_system_enabled', True)
            self.model = getattr(settings, 'clarification_model', 'gpt-4o-mini')  # ✅ CHANGÉ
            self.timeout = getattr(settings, 'clarification_timeout', 20)  # ✅ Augmenté
            self.max_questions = getattr(settings, 'clarification_max_questions', 3)
            self.min_question_length = getattr(settings, 'clarification_min_length', 15)
            self.log_all_clarifications = getattr(settings, 'clarification_log_all', True)
            self.confidence_threshold = getattr(settings, 'clarification_confidence_threshold', 0.7)  # ✅ Réduit
        else:
            # ✅ FALLBACK OPTIMISÉ depuis .env
            self.enabled = os.getenv('ENABLE_CLARIFICATION_SYSTEM', 'true').lower() == 'true'
            self.model = os.getenv('CLARIFICATION_MODEL', 'gpt-4o-mini')  # ✅ CHANGÉ
            self.timeout = int(os.getenv('CLARIFICATION_TIMEOUT', '20'))  # ✅ Augmenté
            self.max_questions = int(os.getenv('CLARIFICATION_MAX_QUESTIONS', '3'))
            self.min_question_length = int(os.getenv('CLARIFICATION_MIN_LENGTH', '15'))
            self.log_all_clarifications = os.getenv('LOG_ALL_CLARIFICATIONS', 'true').lower() == 'true'
            self.confidence_threshold = float(os.getenv('CLARIFICATION_CONFIDENCE_THRESHOLD', '0.7'))  # ✅ Réduit
        
        logger.info(f"🔧 [ClarificationSystem] Clarification: {'✅ Activée' if self.enabled else '❌ Désactivée'}")
        logger.info(f"🔧 [ClarificationSystem] Modèle: {self.model}, Timeout: {self.timeout}s")
        logger.info(f"🔧 [ClarificationSystem] Questions max: {self.max_questions}, Seuil: {self.confidence_threshold}")
        
        self._init_patterns()
        self._init_prompts()
        self._init_clarification_logger()

    def _init_patterns(self):
        """✅ AMÉLIORÉ: Patterns de détection plus précis"""
        
        # ✅ NOUVEAU: Distinction races spécifiques vs génériques
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
        
        # ✅ NOUVEAU: Termes génériques qui nécessitent clarification
        self.generic_breed_patterns = {
            "fr": [r'poulets?', r'volailles?', r'oiseaux?', r'chair'],
            "en": [r'chickens?', r'poultry', r'birds?', r'broilers?'],
            "es": [r'pollos?', r'aves?', r'engorde']
        }
        
        self.age_patterns = {
            "fr": [
                r'(\d+)\s*jours?', r'(\d+)\s*semaines?', r'(\d+)\s*mois',
                r'jour\s*(\d+)', r'semaine\s*(\d+)', r'âgés?\s+de\s+(\d+)',
                r'(\d+)j', r'(\d+)sem', r'j(\d+)', r'(\d+)\s*j\b'
            ],
            "en": [
                r'(\d+)\s*days?', r'(\d+)\s*weeks?', r'(\d+)\s*months?',
                r'day\s*(\d+)', r'week\s*(\d+)', r'(\d+)\s*day\s*old',
                r'(\d+)d', r'(\d+)w', r'd(\d+)', r'(\d+)\s*d\b'
            ],
            "es": [
                r'(\d+)\s*días?', r'(\d+)\s*semanas?', r'(\d+)\s*meses?',
                r'día\s*(\d+)', r'semana\s*(\d+)', r'(\d+)\s*días?\s*de\s*edad',
                r'(\d+)d', r'(\d+)s', r'd(\d+)', r'(\d+)\s*d\b'
            ]
        }
        
        self.weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|kilogram|gramm?es?|g|lbs?|pound)',
            r'pèsent?\s+(\d+(?:\.\d+)?)', r'weigh\s+(\d+(?:\.\d+)?)', r'peso\s+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*g\b', r'(\d+(?:\.\d+)?)\s*kg\b'
        ]
        
        self.mortality_patterns = [
            r'mortalité\s+(?:de\s+)?(\d+(?:\.\d+)?)%?', r'mortality\s+(?:of\s+)?(\d+(?:\.\d+)?)%?',
            r'mortalidad\s+(?:del?\s+)?(\d+(?:\.\d+)?)%?', r'(\d+(?:\.\d+)?)%\s+mortalit[éy]',
            r'morts?\s+(\d+)', r'dead\s+(\d+)', r'muertos?\s+(\d+)'
        ]

    def _detect_existing_info(self, question: str, language: str) -> Dict[str, str]:
        """✅ AMÉLIORÉ: Détection plus intelligente avec distinction spécifique/générique"""
        
        detected = {}
        question_lower = question.lower()
        
        # ✅ NOUVEAU: Vérifier d'abord les races SPÉCIFIQUES
        specific_patterns = self.specific_breed_patterns.get(language, self.specific_breed_patterns["fr"])
        for pattern in specific_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["breed"] = match.group(0).strip()
                detected["breed_type"] = "specific"
                break
        
        # ✅ NOUVEAU: Si pas de race spécifique, vérifier les termes génériques
        if "breed" not in detected:
            generic_patterns = self.generic_breed_patterns.get(language, self.generic_breed_patterns["fr"])
            for pattern in generic_patterns:
                match = re.search(pattern, question_lower, re.IGNORECASE)
                if match:
                    detected["breed"] = match.group(0).strip()
                    detected["breed_type"] = "generic"  # ✅ CRITIQUE: Marqué comme générique
                    break
        
        # Détection de l'âge
        age_patterns = self.age_patterns.get(language, self.age_patterns["fr"])
        for pattern in age_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["age"] = match.group(0).strip()
                break
        
        # Autres détections
        for pattern in self.weight_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["weight"] = match.group(0).strip()
                break
        
        for pattern in self.mortality_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["mortality"] = match.group(0).strip()
                break
        
        return detected

    def _init_prompts(self):
        """✅ NOUVEAUX PROMPTS PLUS STRICTS ET INTELLIGENTS"""
        
        self.clarification_prompts = {
            "fr": """Tu es un expert vétérinaire spécialisé en aviculture. Analyse cette question pour déterminer si elle manque d'informations CRITIQUES.

Question: "{question}"
Informations détectées: {detected_info}

RÈGLES STRICTES ET PRÉCISES:
1. Si la question contient une RACE SPÉCIFIQUE (Ross 308, Cobb 500, etc.) ET un âge précis, réponds exactement: "CLEAR"
2. Si la question contient seulement "poulet", "volaille" ou terme GÉNÉRIQUE sans race spécifique → CLARIFICATION OBLIGATOIRE
3. Si l'âge manque pour une question sur croissance/poids/performance → CLARIFICATION OBLIGATOIRE
4. Ne demande que les informations VRAIMENT manquantes pour donner une réponse précise

EXEMPLES DE QUESTIONS COMPLÈTES (répondre "CLEAR"):
- "Mes poulets Ross 308 de 25 jours pèsent 800g, est-ce normal?"
- "Poids normal Ross 308 au jour 12?"
- "Température optimale pour Cobb 500 de 3 semaines?"

EXEMPLES DE QUESTIONS INCOMPLÈTES (clarifier):
- "Poids idéal d'un poulet au jour 12?" → Manque: race spécifique
- "Mes poulets ne grossissent pas" → Manque: race ET âge
- "Quelle température pour mes oiseaux?" → Manque: race ET âge
- "Mortalité élevée chez mes volailles" → Manque: race, âge, taux

IMPORTANT: 
- "poulet" seul = GÉNÉRIQUE → clarification obligatoire
- "Ross 308" = SPÉCIFIQUE → acceptable si âge présent
- Pour questions de poids/croissance: race ET âge sont OBLIGATOIRES

Si clarification nécessaire, pose 2-3 questions précises:
- Quelle est la race/lignée de vos poulets (Ross 308, Cobb 500, etc.) ?
- Quel âge ont-ils actuellement (en jours) ?
- [Question spécifique au contexte si nécessaire]

Format: soit "CLEAR" soit liste de questions avec tirets.""",

            "en": """You are a veterinary expert specialized in poultry farming. Analyze this question to determine if it lacks CRITICAL information.

Question: "{question}"
Detected information: {detected_info}

STRICT AND PRECISE RULES:
1. If the question contains a SPECIFIC BREED (Ross 308, Cobb 500, etc.) AND precise age, answer exactly: "CLEAR"
2. If the question contains only "chicken", "poultry" or GENERIC term without specific breed → CLARIFICATION REQUIRED
3. If age is missing for growth/weight/performance question → CLARIFICATION REQUIRED
4. Only ask for information TRULY missing to give a precise answer

EXAMPLES OF COMPLETE QUESTIONS (answer "CLEAR"):
- "My Ross 308 chickens at 25 days weigh 800g, is this normal?"
- "Normal weight Ross 308 day 12?"
- "Optimal temperature for Cobb 500 at 3 weeks?"

EXAMPLES OF INCOMPLETE QUESTIONS (clarify):
- "Ideal weight of a chicken at day 12?" → Missing: specific breed
- "My chickens aren't growing" → Missing: breed AND age
- "What temperature for my birds?" → Missing: breed AND age
- "High mortality in my poultry" → Missing: breed, age, rate

IMPORTANT:
- "chicken" alone = GENERIC → clarification required
- "Ross 308" = SPECIFIC → acceptable if age present
- For weight/growth questions: breed AND age are MANDATORY

If clarification needed, ask 2-3 precise questions:
- What breed/line are your chickens (Ross 308, Cobb 500, etc.)?
- How old are they currently (in days)?
- [Context-specific question if necessary]

Format: either "CLEAR" or bulleted question list.""",

            "es": """Eres un experto veterinario especializado en avicultura. Analiza esta pregunta para determinar si carece de información CRÍTICA.

Pregunta: "{question}"
Información detectada: {detected_info}

REGLAS ESTRICTAS Y PRECISAS:
1. Si la pregunta contiene una RAZA ESPECÍFICA (Ross 308, Cobb 500, etc.) Y edad precisa, responde exactamente: "CLEAR"
2. Si la pregunta contiene solo "pollo", "ave" o término GENÉRICO sin raza específica → ACLARACIÓN OBLIGATORIA
3. Si falta edad para pregunta sobre crecimiento/peso/rendimiento → ACLARACIÓN OBLIGATORIA
4. Solo pide información REALMENTE faltante para dar respuesta precisa

EJEMPLOS DE PREGUNTAS COMPLETAS (responder "CLEAR"):
- "Mis pollos Ross 308 de 25 días pesan 800g, ¿es normal?"
- "¿Peso normal Ross 308 día 12?"
- "¿Temperatura óptima para Cobb 500 de 3 semanas?"

EJEMPLOS DE PREGUNTAS INCOMPLETAS (aclarar):
- "¿Peso ideal de un pollo al día 12?" → Falta: raza específica
- "Mis pollos no crecen" → Falta: raza Y edad
- "¿Qué temperatura para mis aves?" → Falta: raza Y edad
- "Mortalidad alta en mis aves" → Falta: raza, edad, tasa

IMPORTANTE:
- "pollo" solo = GENÉRICO → aclaración obligatoria
- "Ross 308" = ESPECÍFICO → aceptable si edad presente
- Para preguntas peso/crecimiento: raza Y edad son OBLIGATORIAS

Si necesita aclaración, haz 2-3 preguntas precisas:
- ¿Cuál es la raza/línea de sus pollos (Ross 308, Cobb 500, etc.)?
- ¿Qué edad tienen actualmente (en días)?
- [Pregunta específica al contexto si necesario]

Formato: "CLEAR" o lista de preguntas con guiones."""
        }

    def _init_clarification_logger(self):
        """Initialise le logger spécialisé pour les clarifications"""
        self.clarification_logger = logging.getLogger("question_clarification")
        self.clarification_logger.setLevel(logging.INFO)
        
        if not self.clarification_logger.handlers and self.log_all_clarifications:
            try:
                from logging.handlers import RotatingFileHandler
                
                log_dir = os.getenv('VALIDATION_LOGS_DIR', 'logs')
                os.makedirs(log_dir, exist_ok=True)
                
                log_file_path = os.path.join(log_dir, 'question_clarifications.log')
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
                
                logger.info(f"✅ [ClarificationSystem] Logger configuré: {log_file_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ [ClarificationSystem] Impossible de créer le fichier de log: {e}")

    async def analyze_question(
        self, 
        question: str, 
        language: str = "fr",
        user_id: str = "unknown",
        conversation_id: str = None
    ) -> ClarificationResult:
        """
        ✅ ANALYSE AMÉLIORÉE avec GPT-4o-mini et logique plus stricte
        """
        
        start_time = time.time()
        
        if not self.enabled:
            logger.info(f"🔧 [ClarificationSystem] Système désactivé")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="system_disabled"
            )
        
        if not question or len(question.strip()) < self.min_question_length:
            logger.info(f"⚠️ [ClarificationSystem] Question trop courte: {len(question)}")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="question_too_short"
            )
        
        # ✅ NOUVEAU: Détection intelligente améliorée
        detected_info = self._detect_existing_info(question, language)
        
        logger.info(f"🔍 [ClarificationSystem] Analyse: '{question[:80]}...'")
        logger.info(f"📊 [ClarificationSystem] Info détectées: {detected_info}")
        
        # ✅ NOUVELLE LOGIQUE: Race générique = clarification obligatoire
        if detected_info.get("breed_type") == "generic":
            logger.info(f"🚨 [ClarificationSystem] Race générique détectée - clarification obligatoire")
            
            generic_clarification_questions = self._generate_generic_clarification_questions(language)
            
            return ClarificationResult(
                needs_clarification=True,
                questions=generic_clarification_questions,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="generic_breed_detected",
                model_used="rule_based",
                detected_info=detected_info,
                confidence_score=95.0
            )
        
        # ✅ LOGIQUE CONSERVÉE: Race spécifique + âge = OK
        if detected_info.get("breed_type") == "specific" and detected_info.get("age"):
            logger.info(f"✅ [ClarificationSystem] Race spécifique + âge - question complète")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="specific_breed_and_age_detected",
                detected_info=detected_info
            )
        
        if not OPENAI_AVAILABLE or not openai:
            logger.warning(f"⚠️ [ClarificationSystem] OpenAI non disponible")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="openai_unavailable",
                detected_info=detected_info
            )
        
        try:
            # ✅ Configuration OpenAI avec GPT-4o-mini
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning(f"⚠️ [ClarificationSystem] Clé API OpenAI manquante")
                return ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    reason="openai_key_missing",
                    detected_info=detected_info
                )
            
            openai.api_key = api_key
            
            # ✅ Prompt avec informations détectées
            prompt_template = self.clarification_prompts.get(language.lower(), self.clarification_prompts["fr"])
            detected_info_str = json.dumps(detected_info, ensure_ascii=False) if detected_info else "Aucune information spécifique détectée"
            
            user_prompt = prompt_template.format(
                question=question, 
                detected_info=detected_info_str
            )
            
            system_prompt = "Tu es un assistant expert qui détermine si une question d'aviculture nécessite des clarifications. Sois très précis et strict sur les races spécifiques vs génériques."
            
            # ✅ Appel GPT-4o-mini avec timeout plus long
            logger.info(f"🤖 [ClarificationSystem] Appel GPT-4o-mini...")
            
            response = openai.chat.completions.create(
                model=self.model,  # gpt-4o-mini
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Très faible pour cohérence
                max_tokens=400,
                timeout=self.timeout
            )
            
            answer = response.choices[0].message.content.strip()
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"🤖 [ClarificationSystem] Réponse GPT-4o-mini ({processing_time_ms}ms): {answer[:100]}...")
            
            # Analyse de la réponse
            if answer.upper().strip() in ["CLEAR", "CLEAR.", "CLEAR !"]:
                result = ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="question_clear_by_gpt4o_mini",
                    model_used=self.model,
                    detected_info=detected_info
                )
                
                logger.info(f"✅ [ClarificationSystem] Question claire selon GPT-4o-mini")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            
            # Extraire les questions de clarification
            clarification_questions = self._extract_questions(answer)
            
            if clarification_questions and len(clarification_questions) > 0:
                limited_questions = clarification_questions[:self.max_questions]
                
                result = ClarificationResult(
                    needs_clarification=True,
                    questions=limited_questions,
                    processing_time_ms=processing_time_ms,
                    reason="clarification_needed_by_gpt4o_mini",
                    model_used=self.model,
                    confidence_score=self._calculate_confidence_score(question, limited_questions, detected_info),
                    detected_info=detected_info
                )
                
                logger.info(f"❓ [ClarificationSystem] {len(limited_questions)} questions générées par GPT-4o-mini")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            else:
                logger.info(f"✅ [ClarificationSystem] Aucune question valide - question suffisante")
                return ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="no_valid_questions_from_gpt4o_mini",
                    model_used=self.model,
                    detected_info=detected_info
                )
        
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ [ClarificationSystem] Erreur GPT-4o-mini: {e}")
            
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=processing_time_ms,
                reason=f"error_gpt4o_mini: {str(e)}",
                model_used=self.model,
                detected_info=detected_info
            )

    def _generate_generic_clarification_questions(self, language: str) -> List[str]:
        """✅ NOUVEAU: Génère des questions standard pour races génériques"""
        
        questions_by_language = {
            "fr": [
                "Quelle est la race/lignée de vos poulets (Ross 308, Cobb 500, Hubbard, etc.) ?",
                "Quel âge ont-ils actuellement (en jours) ?",
                "Dans quel type d'élevage (bâtiment fermé, semi-ouvert, plein air) ?"
            ],
            "en": [
                "What breed/line are your chickens (Ross 308, Cobb 500, Hubbard, etc.)?",
                "How old are they currently (in days)?",
                "What type of housing (closed building, semi-open, free-range)?"
            ],
            "es": [
                "¿Cuál es la raza/línea de sus pollos (Ross 308, Cobb 500, Hubbard, etc.)?",
                "¿Qué edad tienen actualmente (en días)?",
                "¿En qué tipo de alojamiento (edificio cerrado, semi-abierto, campo libre)?"
            ]
        }
        
        return questions_by_language.get(language, questions_by_language["fr"])[:self.max_questions]

    def _extract_questions(self, answer: str) -> List[str]:
        """Extrait les questions de clarification de la réponse GPT"""
        questions = []
        lines = answer.splitlines()
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 15:  # Questions suffisamment longues
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

    def _calculate_confidence_score(self, original_question: str, clarification_questions: List[str], detected_info: Dict[str, str]) -> float:
        """✅ AMÉLIORÉ: Score de confiance plus intelligent"""
        
        # Score de base basé sur le nombre de questions
        base_score = min(len(clarification_questions) * 25, 80)
        
        # Bonus pour informations génériques détectées
        if detected_info.get("breed_type") == "generic":
            base_score += 15  # Questions génériques = clarification très probable
        
        # Bonus si race spécifique manque pour questions de performance
        performance_keywords = ['poids', 'weight', 'peso', 'croissance', 'growth', 'crecimiento', 'mortalité', 'mortality', 'mortalidad']
        if any(keyword in original_question.lower() for keyword in performance_keywords):
            if not detected_info.get("breed") or detected_info.get("breed_type") == "generic":
                base_score += 10
        
        return min(base_score, 95.0)

    def format_clarification_response(
        self, 
        questions: List[str], 
        language: str, 
        original_question: str
    ) -> str:
        """Formate la réponse de clarification de manière conviviale"""
        
        intros = {
            "fr": "❓ Pour vous donner la réponse la plus précise possible, j'aurais besoin de quelques informations supplémentaires :",
            "en": "❓ To give you the most accurate answer possible, I would need some additional information:",
            "es": "❓ Para darle la respuesta más precisa posible, necesitaría información adicional:"
        }
        
        outros = {
            "fr": "\n\nCes précisions m'aideront à vous donner des conseils spécifiques et adaptés à votre situation ! 🐔",
            "en": "\n\nThese details will help me give you specific advice tailored to your situation! 🐔",
            "es": "\n\n¡Estos detalles me ayudarán a darle consejos específicos adaptados a su situación! 🐔"
        }
        
        intro = intros.get(language, intros["fr"])
        outro = outros.get(language, outros["fr"])
        
        # Formatage des questions avec puces
        formatted_questions = "\n".join([f"• {q}" for q in questions])
        
        return f"{intro}\n\n{formatted_questions}{outro}"

    async def _log_clarification_decision(
        self,
        question: str,
        language: str,
        user_id: str,
        conversation_id: str,
        result: ClarificationResult
    ):
        """Log détaillé des décisions de clarification"""
        
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
                "min_question_length": self.min_question_length
            }
        }
        
        # Log structuré
        self.clarification_logger.info(json.dumps(clarification_data, ensure_ascii=False))
        
        # Log standard
        if result.needs_clarification:
            logger.info(
                f"❓ [ClarificationSystem] CLARIFICATION - "
                f"User: {user_id[:8]} | Questions: {len(result.questions)} | "
                f"Modèle: {result.model_used} | "
                f"Confiance: {result.confidence_score:.1f}% | "
                f"Temps: {result.processing_time_ms}ms"
            )
        else:
            logger.info(
                f"✅ [ClarificationSystem] CLEAR - "
                f"User: {user_id[:8]} | Raison: {result.reason} | "
                f"Modèle: {result.model_used} | "
                f"Temps: {result.processing_time_ms}ms"
            )

    def get_stats(self) -> Dict:
        """Retourne les statistiques du système pour monitoring"""
        return {
            "enabled": self.enabled,
            "model": self.model,  # Maintenant gpt-4o-mini
            "timeout": self.timeout,
            "max_questions": self.max_questions,
            "min_question_length": self.min_question_length,
            "confidence_threshold": self.confidence_threshold,
            "log_all_clarifications": self.log_all_clarifications,
            "openai_available": OPENAI_AVAILABLE,
            "supported_languages": list(self.clarification_prompts.keys()),
            "settings_source": "intelia_settings" if SETTINGS_AVAILABLE else "environment_variables",
            "detection_enabled": True,
            "specific_breed_patterns_count": sum(len(patterns) for patterns in self.specific_breed_patterns.values()),
            "generic_breed_patterns_count": sum(len(patterns) for patterns in self.generic_breed_patterns.values()),
            "age_patterns_count": sum(len(patterns) for patterns in self.age_patterns.values())
        }

# ==================== INSTANCE GLOBALE ====================

# Instance singleton du système de clarification CORRIGÉ avec GPT-4o-mini
clarification_system = QuestionClarificationSystem()

# ==================== FONCTIONS UTILITAIRES ====================

async def analyze_question_for_clarification(
    question: str, 
    language: str = "fr",
    user_id: str = "unknown", 
    conversation_id: str = None
) -> ClarificationResult:
    """Fonction utilitaire pour analyser les questions avec GPT-4o-mini"""
    return await clarification_system.analyze_question(question, language, user_id, conversation_id)

def format_clarification_response(questions: List[str], language: str, original_question: str) -> str:
    """Formate la réponse de clarification"""
    return clarification_system.format_clarification_response(questions, language, original_question)

def get_clarification_system_stats() -> Dict:
    """Retourne les statistiques du système"""
    return clarification_system.get_stats()

def is_clarification_system_enabled() -> bool:
    """Vérifie si le système de clarification est activé"""
    return clarification_system.enabled

def build_enriched_question(original_question: str, clarification_answers: Dict[str, str], clarification_questions: List[str]) -> str:
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

# ==================== LOGGING DE DÉMARRAGE ====================

logger.info("❓ [QuestionClarificationSystem] Module CORRIGÉ avec GPT-4o-mini initialisé")
logger.info(f"📊 [QuestionClarificationSystem] Statistiques: {clarification_system.get_stats()}")
logger.info("✅ [QuestionClarificationSystem] AMÉLIORATIONS APPLIQUÉES:")
logger.info("   - 🤖 GPT-4o-mini pour meilleure intelligence")
logger.info("   - 🔍 Détection races spécifiques vs génériques")
logger.info("   - 🚨 Clarification obligatoire pour termes génériques")
logger.info("   - 📏 Prompts plus stricts et précis")
logger.info("   - ⚡ Seuils optimisés (confidence: 0.7)")
logger.info("   - 🎯 Logique règles + IA hybride")