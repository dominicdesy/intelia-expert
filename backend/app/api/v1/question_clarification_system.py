"""
app/api/v1/question_clarification_system.py - VERSION CORRIGÉE

CORRECTIONS MAJEURES:
1. Détection intelligente des informations déjà présentes
2. Prompts plus précis pour éviter les faux positifs
3. Validation des questions avant génération
4. Seuils d'activation plus stricts
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
    detected_info: Optional[Dict[str, str]] = None  # ✅ NOUVEAU: Info détectée
    
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
    Système de clarification intelligent CORRIGÉ pour les questions agricoles.
    Détecte les informations déjà présentes pour éviter les questions inutiles.
    """
    
    def __init__(self):
        """Initialise le système avec la configuration Intelia CORRIGÉE"""
        
        # Configuration depuis les settings Intelia ou variables d'environnement
        if SETTINGS_AVAILABLE and settings:
            self.enabled = getattr(settings, 'clarification_system_enabled', True)
            self.model = getattr(settings, 'clarification_model', 'gpt-3.5-turbo')
            self.timeout = getattr(settings, 'clarification_timeout', 15)  # ✅ Augmenté
            self.max_questions = getattr(settings, 'clarification_max_questions', 3)  # ✅ Réduit
            self.min_question_length = getattr(settings, 'clarification_min_length', 15)  # ✅ Augmenté
            self.log_all_clarifications = getattr(settings, 'clarification_log_all', True)
            self.confidence_threshold = getattr(settings, 'clarification_confidence_threshold', 0.8)  # ✅ Plus strict
        else:
            # Fallback configuration depuis .env - SEUILS PLUS STRICTS
            self.enabled = os.getenv('ENABLE_CLARIFICATION_SYSTEM', 'true').lower() == 'true'
            self.model = os.getenv('CLARIFICATION_MODEL', 'gpt-3.5-turbo')
            self.timeout = int(os.getenv('CLARIFICATION_TIMEOUT', '15'))  # ✅ Plus long
            self.max_questions = int(os.getenv('CLARIFICATION_MAX_QUESTIONS', '3'))  # ✅ Moins de questions
            self.min_question_length = int(os.getenv('CLARIFICATION_MIN_LENGTH', '15'))  # ✅ Questions plus longues
            self.log_all_clarifications = os.getenv('LOG_ALL_CLARIFICATIONS', 'true').lower() == 'true'
            self.confidence_threshold = float(os.getenv('CLARIFICATION_CONFIDENCE_THRESHOLD', '0.8'))  # ✅ Plus strict
        
        logger.info(f"🔧 [ClarificationSystem] Clarification: {'✅ Activée' if self.enabled else '❌ Désactivée'}")
        logger.info(f"🔧 [ClarificationSystem] Modèle: {self.model}, Timeout: {self.timeout}s")
        logger.info(f"🔧 [ClarificationSystem] Questions max: {self.max_questions}, Seuil: {self.confidence_threshold}")
        
        self._init_patterns()  # ✅ NOUVEAU: Patterns de détection
        self._init_prompts()
        self._init_clarification_logger()

    def _init_patterns(self):
        """✅ NOUVEAU: Initialise les patterns de détection d'informations"""
        
        # Patterns pour détecter les informations déjà présentes
        self.breed_patterns = {
            "fr": [
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro',
                r'poulets?\s+ross', r'poulets?\s+cobb', r'poulets?\s+hubbard'
            ],
            "en": [
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro',
                r'chickens?\s+ross', r'chickens?\s+cobb', r'broilers?\s+ross'
            ],
            "es": [
                r'ross\s*308', r'ross\s*708', r'ross\s*ap95', r'ross\s*pm3',
                r'cobb\s*500', r'cobb\s*700', r'cobb\s*sasso',
                r'hubbard\s*flex', r'hubbard\s*classic',
                r'arbor\s*acres', r'isa\s*15', r'red\s*bro',
                r'pollos?\s+ross', r'pollos?\s+cobb', r'pollos?\s+de\s+engorde'
            ]
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
        
        self.temperature_patterns = [
            r'(\d+(?:\.\d+)?)\s*°?c', r'(\d+(?:\.\d+)?)\s*°?f', r'(\d+(?:\.\d+)?)\s*degrés?',
            r'température\s+(?:de\s+)?(\d+)', r'temperature\s+(?:of\s+)?(\d+)',
            r'temperatura\s+(?:de\s+)?(\d+)'
        ]

    def _detect_existing_info(self, question: str, language: str) -> Dict[str, str]:
        """✅ NOUVEAU: Détecte les informations déjà présentes dans la question"""
        
        detected = {}
        question_lower = question.lower()
        
        # Détection de la race/lignée
        breed_patterns = self.breed_patterns.get(language, self.breed_patterns["fr"])
        for pattern in breed_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["breed"] = match.group(0).strip()
                break
        
        # Détection de l'âge
        age_patterns = self.age_patterns.get(language, self.age_patterns["fr"])
        for pattern in age_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["age"] = match.group(0).strip()
                break
        
        # Détection du poids
        for pattern in self.weight_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["weight"] = match.group(0).strip()
                break
        
        # Détection de la mortalité
        for pattern in self.mortality_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["mortality"] = match.group(0).strip()
                break
        
        # Détection de la température
        for pattern in self.temperature_patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                detected["temperature"] = match.group(0).strip()
                break
        
        return detected

    def _init_prompts(self):
        """✅ CORRIGÉ: Prompts plus précis et intelligents"""
        
        self.clarification_prompts = {
            "fr": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale pour poulets de chair.

Analyse cette question et les informations déjà détectées. Détermine si elle manque d'informations CRITIQUES pour donner une réponse précise.

Question: "{question}"
Informations déjà présentes: {detected_info}

RÈGLES STRICTES:
1. Si la question contient DÉJÀ les informations principales (race/âge/contexte), réponds exactement: "CLEAR"
2. NE demande PAS d'informations déjà présentes dans la question
3. Seulement si des informations VRAIMENT critiques manquent, pose 2-3 questions précises

EXEMPLES DE QUESTIONS DÉJÀ COMPLÈTES (répondre "CLEAR"):
- "Mes poulets Ross 308 de 25 jours ont une mortalité de 3%, est-ce normal?"
- "Poids normal poulet Ross au jour 12?" (race + âge = suffisant)
- "Température optimale pour Ross 308 de 2 semaines?"
- "Mes Cobb 500 de 30 jours pèsent 1.2kg, c'est bien?"

EXEMPLES DE QUESTIONS VRAIMENT VAGUES (clarifier):
- "Mes poulets ne grossissent pas" (manque: race ET âge)
- "Problème de croissance" (manque: race ET âge ET symptômes)
- "Quelle température?" (manque: âge des poulets)

IMPORTANT: Si la race (Ross, Cobb, etc.) ET l'âge sont présents, la question est généralement COMPLÈTE.

Si clarification vraiment nécessaire, pose seulement les questions manquantes:
- Quelle est la race/lignée de vos poulets ?
- Quel âge ont-ils actuellement ?
- Quel est le problème observé précisément ?

Format de réponse si clarification nécessaire:
- Question 1
- Question 2""",

            "en": """You are a veterinary expert specialized in animal health and nutrition for broiler chickens.

Analyze this question and the detected information. Determine if it lacks CRITICAL information to provide a precise answer.

Question: "{question}"
Information already present: {detected_info}

STRICT RULES:
1. If the question already contains main information (breed/age/context), answer exactly: "CLEAR"
2. DO NOT ask for information already present in the question
3. Only if REALLY critical information is missing, ask 2-3 precise questions

EXAMPLES OF ALREADY COMPLETE QUESTIONS (answer "CLEAR"):
- "My Ross 308 chickens at 25 days have 3% mortality, is this normal?"
- "Normal weight Ross chicken day 12?" (breed + age = sufficient)
- "Optimal temperature for Ross 308 at 2 weeks?"
- "My Cobb 500 at 30 days weigh 1.2kg, is this good?"

EXAMPLES OF REALLY VAGUE QUESTIONS (clarify):
- "My chickens aren't growing" (missing: breed AND age)
- "Growth problem" (missing: breed AND age AND symptoms)
- "What temperature?" (missing: chicken age)

IMPORTANT: If breed (Ross, Cobb, etc.) AND age are present, the question is generally COMPLETE.

If clarification really needed, ask only missing questions:
- What breed/line are your chickens?
- How old are they currently?
- What problem are you observing precisely?

Response format if clarification needed:
- Question 1
- Question 2""",

            "es": """Eres un experto veterinario especializado en salud y nutrición animal para pollos de engorde.

Analiza esta pregunta y la información detectada. Determina si carece de información CRÍTICA para dar una respuesta precisa.

Pregunta: "{question}"
Información ya presente: {detected_info}

REGLAS ESTRICTAS:
1. Si la pregunta ya contiene información principal (raza/edad/contexto), responde exactamente: "CLEAR"
2. NO pidas información ya presente en la pregunta
3. Solo si falta información REALMENTE crítica, haz 2-3 preguntas precisas

EJEMPLOS DE PREGUNTAS YA COMPLETAS (responder "CLEAR"):
- "Mis pollos Ross 308 de 25 días tienen 3% mortalidad, ¿es normal?"
- "¿Peso normal pollo Ross día 12?" (raza + edad = suficiente)
- "¿Temperatura óptima para Ross 308 de 2 semanas?"
- "Mis Cobb 500 de 30 días pesan 1.2kg, ¿está bien?"

EJEMPLOS DE PREGUNTAS REALMENTE VAGAS (aclarar):
- "Mis pollos no crecen" (falta: raza Y edad)
- "Problema de crecimiento" (falta: raza Y edad Y síntomas)
- "¿Qué temperatura?" (falta: edad pollos)

IMPORTANTE: Si raza (Ross, Cobb, etc.) Y edad están presentes, la pregunta es generalmente COMPLETA.

Si realmente necesita aclaración, pregunta solo lo que falta:
- ¿Cuál es la raza/línea de sus pollos?
- ¿Qué edad tienen actualmente?
- ¿Qué problema observa precisamente?

Formato de respuesta si necesita aclaración:
- Pregunta 1
- Pregunta 2"""
        }

    def _init_clarification_logger(self):
        """Initialise le logger spécialisé pour les clarifications"""
        self.clarification_logger = logging.getLogger("question_clarification")
        self.clarification_logger.setLevel(logging.INFO)
        
        # Handler pour fichier de clarifications si pas déjà configuré
        if not self.clarification_logger.handlers and self.log_all_clarifications:
            try:
                from logging.handlers import RotatingFileHandler
                
                # Utiliser le même répertoire que la validation agricole
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
        ✅ CORRIGÉ: Analyse une question avec détection intelligente
        """
        
        start_time = time.time()
        
        # Vérification de l'activation du système
        if not self.enabled:
            logger.info(f"🔧 [ClarificationSystem] Système désactivé - question traitée normalement")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="system_disabled"
            )
        
        # Validation des entrées - SEUILS PLUS STRICTS
        if not question or len(question.strip()) < self.min_question_length:
            logger.info(f"⚠️ [ClarificationSystem] Question trop courte: {len(question)} caractères (min: {self.min_question_length})")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="question_too_short"
            )
        
        # ✅ NOUVEAU: Détection intelligente des informations présentes
        detected_info = self._detect_existing_info(question, language)
        
        logger.info(f"🔍 [ClarificationSystem] Analyse: '{question[:80]}...' (langue: {language})")
        logger.info(f"📊 [ClarificationSystem] Info détectées: {detected_info}")
        
        # ✅ NOUVEAU: Si informations critiques déjà présentes, pas de clarification
        if detected_info.get("breed") and detected_info.get("age"):
            logger.info(f"✅ [ClarificationSystem] Race + âge détectés - question complète")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="sufficient_info_detected",
                detected_info=detected_info
            )
        
        # ✅ NOUVEAU: Questions très spécifiques considérées comme complètes
        specific_keywords = {
            "fr": ["poids normal", "température optimale", "mortalité normale", "croissance normale"],
            "en": ["normal weight", "optimal temperature", "normal mortality", "normal growth"],
            "es": ["peso normal", "temperatura óptima", "mortalidad normal", "crecimiento normal"]
        }
        
        question_lower = question.lower()
        keywords = specific_keywords.get(language, specific_keywords["fr"])
        
        if any(keyword in question_lower for keyword in keywords) and detected_info:
            logger.info(f"✅ [ClarificationSystem] Question spécifique avec contexte - complète")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="specific_question_with_context",
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
            # Configuration OpenAI
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
            
            # ✅ CORRIGÉ: Prompt avec informations détectées
            prompt_template = self.clarification_prompts.get(language.lower(), self.clarification_prompts["fr"])
            
            # Formater les informations détectées pour le prompt
            detected_info_str = json.dumps(detected_info, ensure_ascii=False) if detected_info else "Aucune information spécifique détectée"
            
            user_prompt = prompt_template.format(
                question=question, 
                detected_info=detected_info_str
            )
            
            system_prompt = "Tu es un assistant intelligent qui détermine si une question nécessite des clarifications. Sois très conservateur - ne demande des clarifications que si vraiment nécessaire."
            
            # Appel à OpenAI
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Très faible pour cohérence
                max_tokens=300,  # ✅ Réduit pour réponses plus courtes
                timeout=self.timeout
            )
            
            answer = response.choices[0].message.content.strip()
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"🤖 [ClarificationSystem] Réponse GPT: {answer[:100]}...")
            
            # Analyse de la réponse
            if answer.upper().strip() in ["CLEAR", "CLEAR.", "CLEAR !"]:
                result = ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="question_clear_by_gpt",
                    model_used=self.model,
                    detected_info=detected_info
                )
                
                logger.info(f"✅ [ClarificationSystem] Question claire selon GPT ({processing_time_ms}ms)")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            
            # Extraire les questions de clarification
            clarification_questions = self._extract_questions(answer)
            
            # ✅ NOUVEAU: Filtrer les questions qui demandent des infos déjà présentes
            filtered_questions = self._filter_redundant_questions(clarification_questions, detected_info, language)
            
            if filtered_questions and len(filtered_questions) > 0:
                # Limiter le nombre de questions
                limited_questions = filtered_questions[:self.max_questions]
                
                result = ClarificationResult(
                    needs_clarification=True,
                    questions=limited_questions,
                    processing_time_ms=processing_time_ms,
                    reason="clarification_needed",
                    model_used=self.model,
                    confidence_score=self._calculate_confidence_score(question, limited_questions, detected_info),
                    detected_info=detected_info
                )
                
                logger.info(f"❓ [ClarificationSystem] {len(limited_questions)} questions générées ({processing_time_ms}ms)")
                logger.info(f"❓ [ClarificationSystem] Questions: {limited_questions}")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            else:
                logger.info(f"✅ [ClarificationSystem] Questions filtrées - informations suffisantes")
                return ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="questions_filtered_sufficient_info",
                    model_used=self.model,
                    detected_info=detected_info
                )
        
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ [ClarificationSystem] Erreur analyse: {e}")
            
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=processing_time_ms,
                reason=f"error: {str(e)}",
                model_used=self.model,
                detected_info=detected_info
            )

    def _filter_redundant_questions(self, questions: List[str], detected_info: Dict[str, str], language: str) -> List[str]:
        """✅ NOUVEAU: Filtre les questions qui demandent des informations déjà présentes"""
        
        if not questions or not detected_info:
            return questions
        
        filtered = []
        
        # Mots-clés pour identifier les types de questions
        breed_keywords = {
            "fr": ["race", "lignée", "souche", "variété", "ross", "cobb", "hubbard"],
            "en": ["breed", "line", "strain", "variety", "ross", "cobb", "hubbard"],
            "es": ["raza", "línea", "cepa", "variedad", "ross", "cobb", "hubbard"]
        }
        
        age_keywords = {
            "fr": ["âge", "âgé", "jour", "semaine", "mois", "vieux"],
            "en": ["age", "old", "day", "week", "month"],
            "es": ["edad", "día", "semana", "mes", "viejo"]
        }
        
        weight_keywords = {
            "fr": ["poids", "pèse", "kg", "gramme"],
            "en": ["weight", "weigh", "kg", "gram", "pound"],
            "es": ["peso", "pesa", "kg", "gramo"]
        }
        
        keywords_sets = {
            "breed": breed_keywords.get(language, breed_keywords["fr"]),
            "age": age_keywords.get(language, age_keywords["fr"]),
            "weight": weight_keywords.get(language, weight_keywords["fr"])
        }
        
        for question in questions:
            question_lower = question.lower()
            should_keep = True
            
            # Vérifier si la question demande une info déjà présente
            for info_type, keywords in keywords_sets.items():
                if info_type in detected_info:
                    if any(keyword in question_lower for keyword in keywords):
                        logger.info(f"🚫 [ClarificationSystem] Question filtrée (info présente): {question}")
                        should_keep = False
                        break
            
            if should_keep:
                filtered.append(question)
        
        return filtered

    def _extract_questions(self, answer: str) -> List[str]:
        """Extrait les questions de clarification de la réponse GPT"""
        questions = []
        lines = answer.splitlines()
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:  # ✅ Augmenté de 5 à 10
                # Nettoyer les puces et formatage
                cleaned_line = re.sub(r'^[-•*]\s*', '', line)
                cleaned_line = re.sub(r'^\d+\.\s*', '', cleaned_line)
                cleaned_line = cleaned_line.strip()
                
                # Vérifier que c'est une vraie question
                if cleaned_line and len(cleaned_line) > 15 and cleaned_line not in questions:  # ✅ Augmenté
                    # Ajouter un point d'interrogation si manquant
                    if not cleaned_line.endswith('?') and not cleaned_line.endswith(' ?'):
                        if any(word in cleaned_line.lower() for word in ['quel', 'quelle', 'combien', 'comment', 'what', 'how', 'which', 'cuál', 'cómo', 'cuánto']):
                            cleaned_line += ' ?'
                    
                    questions.append(cleaned_line)
        
        return questions

    def _calculate_confidence_score(self, original_question: str, clarification_questions: List[str], detected_info: Dict[str, str]) -> float:
        """✅ CORRIGÉ: Calcule un score de confiance avec informations détectées"""
        
        # Score de base basé sur le nombre de questions
        base_score = min(len(clarification_questions) * 20, 80)  # ✅ Réduit
        
        # Bonus pour informations déjà détectées (moins besoin de clarification)
        info_bonus = len(detected_info) * 15
        
        # Ajustement basé sur la longueur de la question originale
        if len(original_question) < 20:
            length_penalty = 10  # Questions très courtes
        elif len(original_question) < 40:
            length_penalty = 5
        else:
            length_penalty = 0  # Questions longues sont souvent plus détaillées
        
        # Score final (plus d'infos détectées = moins besoin de clarification)
        final_score = max(base_score - info_bonus + length_penalty, 10.0)
        
        return min(final_score, 100.0)

    def format_clarification_response(
        self, 
        questions: List[str], 
        language: str, 
        original_question: str
    ) -> str:
        """Formate la réponse de clarification de manière conviviale"""
        
        intros = {
            "fr": "❓ Pour vous donner la meilleure réponse possible, j'aurais besoin de quelques précisions :",
            "en": "❓ To give you the best possible answer, I would need some clarification:",
            "es": "❓ Para darle la mejor respuesta posible, necesitaría algunas aclaraciones:"
        }
        
        outros = {
            "fr": "\n\nMerci de préciser ces éléments, cela m'aidera à vous donner des conseils adaptés à votre situation spécifique ! 🐔",
            "en": "\n\nPlease provide these details, it will help me give you advice tailored to your specific situation! 🐔",
            "es": "\n\n¡Por favor proporcione estos detalles, me ayudará a darle consejos adaptados a su situación específica! 🐔"
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
        """Log détaillé des décisions de clarification pour analyse"""
        
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
        
        # Log structuré pour analyse
        self.clarification_logger.info(json.dumps(clarification_data, ensure_ascii=False))
        
        # Log standard pour monitoring
        if result.needs_clarification:
            logger.info(
                f"❓ [ClarificationSystem] CLARIFICATION - "
                f"User: {user_id[:8]} | Questions: {len(result.questions)} | "
                f"Confiance: {result.confidence_score:.1f}% | "
                f"Temps: {result.processing_time_ms}ms | "
                f"Info détectées: {len(result.detected_info or {})}"
            )
        else:
            logger.info(
                f"✅ [ClarificationSystem] CLEAR - "
                f"User: {user_id[:8]} | Raison: {result.reason} | "
                f"Temps: {result.processing_time_ms}ms | "
                f"Info détectées: {len(result.detected_info or {})}"
            )

    def get_stats(self) -> Dict:
        """Retourne les statistiques du système pour monitoring"""
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
            "detection_enabled": True,
            "breed_patterns_count": sum(len(patterns) for patterns in self.breed_patterns.values()),
            "age_patterns_count": sum(len(patterns) for patterns in self.age_patterns.values())
        }

# ==================== INSTANCE GLOBALE ====================

# Instance singleton du système de clarification CORRIGÉ
clarification_system = QuestionClarificationSystem()

# ==================== FONCTIONS UTILITAIRES ====================

async def analyze_question_for_clarification(
    question: str, 
    language: str = "fr",
    user_id: str = "unknown", 
    conversation_id: str = None
) -> ClarificationResult:
    """Fonction utilitaire pour analyser les questions - CORRIGÉE"""
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

logger.info("❓ [QuestionClarificationSystem] Module de clarification intelligent CORRIGÉ initialisé")
logger.info(f"📊 [QuestionClarificationSystem] Statistiques: {clarification_system.get_stats()}")
logger.info("✅ [QuestionClarificationSystem] CORRECTIONS APPLIQUÉES:")
logger.info("   - Détection intelligente des informations présentes (race, âge, poids, etc.)")
logger.info("   - Prompts plus précis pour éviter les faux positifs")
logger.info("   - Filtrage des questions redondantes")
logger.info("   - Seuils plus stricts pour l'activation")
logger.info("   - Questions spécifiques reconnues comme complètes")