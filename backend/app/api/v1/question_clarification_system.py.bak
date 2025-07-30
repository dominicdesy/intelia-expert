"""
app/api/v1/question_clarification_system.py

Module spécialisé pour la clarification intelligente des questions.
Détecte automatiquement les questions nécessitant des informations supplémentaires
et génère des questions de clarification pertinentes.
Intégré avec le système de configuration Intelia.
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
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour les logs"""
        return {
            "needs_clarification": self.needs_clarification,
            "questions": self.questions,
            "questions_count": len(self.questions) if self.questions else 0,
            "confidence_score": self.confidence_score,
            "processing_time_ms": self.processing_time_ms,
            "reason": self.reason,
            "model_used": self.model_used
        }

class QuestionClarificationSystem:
    """
    Système de clarification intelligent pour les questions agricoles.
    Intégré avec le système de configuration Intelia.
    """
    
    def __init__(self):
        """Initialise le système avec la configuration Intelia"""
        
        # Configuration depuis les settings Intelia ou variables d'environnement
        if SETTINGS_AVAILABLE and settings:
            self.enabled = getattr(settings, 'clarification_system_enabled', True)
            self.model = getattr(settings, 'clarification_model', 'gpt-3.5-turbo')
            self.timeout = getattr(settings, 'clarification_timeout', 10)
            self.max_questions = getattr(settings, 'clarification_max_questions', 4)
            self.min_question_length = getattr(settings, 'clarification_min_length', 10)
            self.log_all_clarifications = getattr(settings, 'clarification_log_all', True)
            self.confidence_threshold = getattr(settings, 'clarification_confidence_threshold', 0.7)
        else:
            # Fallback configuration depuis .env
            self.enabled = os.getenv('ENABLE_CLARIFICATION_SYSTEM', 'true').lower() == 'true'
            self.model = os.getenv('CLARIFICATION_MODEL', 'gpt-3.5-turbo')
            self.timeout = int(os.getenv('CLARIFICATION_TIMEOUT', '10'))
            self.max_questions = int(os.getenv('CLARIFICATION_MAX_QUESTIONS', '4'))
            self.min_question_length = int(os.getenv('CLARIFICATION_MIN_LENGTH', '10'))
            self.log_all_clarifications = os.getenv('LOG_ALL_CLARIFICATIONS', 'true').lower() == 'true'
            self.confidence_threshold = float(os.getenv('CLARIFICATION_CONFIDENCE_THRESHOLD', '0.7'))
        
        logger.info(f"🔧 [ClarificationSystem] Clarification: {'✅ Activée' if self.enabled else '❌ Désactivée'}")
        logger.info(f"🔧 [ClarificationSystem] Modèle: {self.model}, Timeout: {self.timeout}s")
        logger.info(f"🔧 [ClarificationSystem] Questions max: {self.max_questions}, Seuil: {self.confidence_threshold}")
        
        self._init_prompts()
        self._init_clarification_logger()

    def _init_prompts(self):
        """Initialise les prompts spécialisés multi-langues"""
        
        self.clarification_prompts = {
            "fr": """Tu es un expert vétérinaire spécialisé en santé et nutrition animale, particulièrement pour les poulets de chair.

Analyse cette question et détermine si elle manque d'informations importantes pour donner une réponse précise et utile.

Question: "{question}"

RÈGLES D'ANALYSE:
1. Si la question est CLAIRE et COMPLÈTE (contient race/âge/contexte suffisant), réponds exactement: "CLEAR"
2. Si la question manque d'informations CRITIQUES, liste 2-4 questions de clarification courtes et précises

EXEMPLES DE QUESTIONS CLAIRES (répondre "CLEAR"):
- "Mes poulets Ross 308 de 25 jours ont une mortalité de 3%, est-ce normal?"
- "Quelle température maintenir pour des poulets de chair de 2 semaines en bâtiment fermé?"

EXEMPLES DE QUESTIONS VAGUES (clarifier):
- "Mes oiseaux ne grossissent pas" → Manque: race, âge, alimentation
- "Quelle température?" → Manque: âge des poulets, type de bâtiment
- "Problème de mortalité" → Manque: taux, âge, symptômes

Si clarification nécessaire, pose des questions spécifiques comme:
- Quelle est la race/lignée de vos poulets (Ross 308, Cobb 500, etc.) ?
- Quel âge ont vos poulets actuellement ?
- Quel est le taux de mortalité observé ?
- Dans quel type de bâtiment (fermé, semi-ouvert, plein air) ?
- Quel programme alimentaire utilisez-vous ?

Format de réponse si clarification nécessaire:
- Question 1
- Question 2
- Question 3""",

            "en": """You are a veterinary expert specialized in animal health and nutrition, particularly for broiler chickens.

Analyze this question and determine if it lacks important information to provide a precise and useful answer.

Question: "{question}"

ANALYSIS RULES:
1. If the question is CLEAR and COMPLETE (contains breed/age/sufficient context), answer exactly: "CLEAR"
2. If the question lacks CRITICAL information, list 2-4 short and precise clarification questions

EXAMPLES OF CLEAR QUESTIONS (answer "CLEAR"):
- "My Ross 308 chickens at 25 days have 3% mortality, is this normal?"
- "What temperature to maintain for 2-week-old broiler chickens in closed housing?"

EXAMPLES OF VAGUE QUESTIONS (clarify):
- "My birds aren't growing" → Missing: breed, age, feeding
- "What temperature?" → Missing: chicken age, building type
- "Mortality problem" → Missing: rate, age, symptoms

If clarification needed, ask specific questions like:
- What breed/line are your chickens (Ross 308, Cobb 500, etc.)?
- How old are your chickens currently?
- What mortality rate are you observing?
- What type of housing (closed, semi-open, free-range)?
- What feeding program are you using?

Response format if clarification needed:
- Question 1
- Question 2
- Question 3""",

            "es": """Eres un experto veterinario especializado en salud y nutrición animal, particularmente para pollos de engorde.

Analiza esta pregunta y determina si carece de información importante para dar una respuesta precisa y útil.

Pregunta: "{question}"

REGLAS DE ANÁLISIS:
1. Si la pregunta es CLARA y COMPLETA (contiene raza/edad/contexto suficiente), responde exactamente: "CLEAR"
2. Si la pregunta carece de información CRÍTICA, lista 2-4 preguntas de aclaración cortas y precisas

EJEMPLOS DE PREGUNTAS CLARAS (responder "CLEAR"):
- "Mis pollos Ross 308 de 25 días tienen 3% de mortalidad, ¿es normal?"
- "¿Qué temperatura mantener para pollos de engorde de 2 semanas en alojamiento cerrado?"

EJEMPLOS DE PREGUNTAS VAGAS (aclarar):
- "Mis aves no crecen" → Falta: raza, edad, alimentación
- "¿Qué temperatura?" → Falta: edad pollos, tipo edificio
- "Problema mortalidad" → Falta: tasa, edad, síntomas

Si necesita aclaración, haz preguntas específicas como:
- ¿Cuál es la raza/línea de sus pollos (Ross 308, Cobb 500, etc.)?
- ¿Qué edad tienen sus pollos actualmente?
- ¿Qué tasa de mortalidad está observando?
- ¿En qué tipo de alojamiento (cerrado, semi-abierto, campo abierto)?
- ¿Qué programa de alimentación utiliza?

Formato de respuesta si necesita aclaración:
- Pregunta 1
- Pregunta 2
- Pregunta 3"""
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
        Analyse une question pour déterminer si des clarifications sont nécessaires
        
        Args:
            question: La question à analyser
            language: Langue de la question
            user_id: ID utilisateur pour les logs
            conversation_id: ID de conversation pour le suivi
            
        Returns:
            ClarificationResult: Résultat de l'analyse
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
        
        # Validation des entrées
        if not question or len(question.strip()) < self.min_question_length:
            logger.warning(f"⚠️ [ClarificationSystem] Question trop courte: {len(question)} caractères")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="question_too_short"
            )
        
        if not OPENAI_AVAILABLE or not openai:
            logger.warning(f"⚠️ [ClarificationSystem] OpenAI non disponible")
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=int((time.time() - start_time) * 1000),
                reason="openai_unavailable"
            )
        
        try:
            logger.info(f"🔍 [ClarificationSystem] Analyse: '{question[:100]}...' (langue: {language}, user: {user_id[:8]})")
            
            # Configuration OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning(f"⚠️ [ClarificationSystem] Clé API OpenAI manquante")
                return ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    reason="openai_key_missing"
                )
            
            openai.api_key = api_key
            
            # Préparation du prompt
            prompt_template = self.clarification_prompts.get(language.lower(), self.clarification_prompts["fr"])
            user_prompt = prompt_template.format(question=question)
            
            system_prompt = "Tu es un assistant intelligent qui détermine si une question nécessite des clarifications. Sois précis et cohérent."
            
            # Appel à OpenAI
            response = openai.chat.completions.create(
                model=self.model,
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
            
            # Analyse de la réponse
            if answer.upper().strip() in ["CLEAR", "CLEAR.", "CLEAR !"]:
                result = ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="question_clear",
                    model_used=self.model
                )
                
                logger.info(f"✅ [ClarificationSystem] Question claire - traitement normal ({processing_time_ms}ms)")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            
            # Extraire les questions de clarification
            clarification_questions = self._extract_questions(answer)
            
            if clarification_questions:
                # Limiter le nombre de questions
                limited_questions = clarification_questions[:self.max_questions]
                
                result = ClarificationResult(
                    needs_clarification=True,
                    questions=limited_questions,
                    processing_time_ms=processing_time_ms,
                    reason="clarification_needed",
                    model_used=self.model,
                    confidence_score=self._calculate_confidence_score(question, limited_questions)
                )
                
                logger.info(f"❓ [ClarificationSystem] {len(limited_questions)} questions générées ({processing_time_ms}ms)")
                logger.info(f"❓ [ClarificationSystem] Questions: {limited_questions}")
                
                if self.log_all_clarifications:
                    await self._log_clarification_decision(
                        question, language, user_id, conversation_id, result
                    )
                
                return result
            else:
                logger.warning(f"⚠️ [ClarificationSystem] Aucune question valide extraite de: {answer}")
                return ClarificationResult(
                    needs_clarification=False,
                    processing_time_ms=processing_time_ms,
                    reason="no_valid_questions_extracted",
                    model_used=self.model
                )
        
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"❌ [ClarificationSystem] Erreur analyse: {e}")
            
            return ClarificationResult(
                needs_clarification=False,
                processing_time_ms=processing_time_ms,
                reason=f"error: {str(e)}",
                model_used=self.model
            )

    def _extract_questions(self, answer: str) -> List[str]:
        """Extrait les questions de clarification de la réponse GPT"""
        questions = []
        lines = answer.splitlines()
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:  # Filtrer les lignes vides ou trop courtes
                # Nettoyer les puces et formatage
                cleaned_line = re.sub(r'^[-•*]\s*', '', line)
                cleaned_line = re.sub(r'^\d+\.\s*', '', cleaned_line)
                cleaned_line = cleaned_line.strip()
                
                # Vérifier que c'est une vraie question
                if cleaned_line and len(cleaned_line) > 10 and cleaned_line not in questions:
                    # Ajouter un point d'interrogation si manquant
                    if not cleaned_line.endswith('?') and not cleaned_line.endswith(' ?'):
                        if any(word in cleaned_line.lower() for word in ['quel', 'quelle', 'combien', 'comment', 'what', 'how', 'which', 'cuál', 'cómo', 'cuánto']):
                            cleaned_line += ' ?'
                    
                    questions.append(cleaned_line)
        
        return questions

    def _calculate_confidence_score(self, original_question: str, clarification_questions: List[str]) -> float:
        """Calcule un score de confiance pour la décision de clarification"""
        # Score basé sur le nombre de questions et la longueur de la question originale
        base_score = min(len(clarification_questions) * 25, 100)
        
        # Ajustement basé sur la longueur de la question originale
        if len(original_question) < 30:
            length_bonus = 20  # Questions courtes ont plus de chances d'être vagues
        elif len(original_question) < 60:
            length_bonus = 10
        else:
            length_bonus = 0  # Questions longues sont souvent plus détaillées
        
        return min(base_score + length_bonus, 100.0)

    def format_clarification_response(
        self, 
        questions: List[str], 
        language: str, 
        original_question: str
    ) -> str:
        """
        Formate la réponse de clarification de manière conviviale
        
        Args:
            questions: Liste des questions de clarification
            language: Langue de la réponse
            original_question: Question originale
            
        Returns:
            str: Réponse formatée
        """
        
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
                "confidence_threshold": self.confidence_threshold
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
                f"Temps: {result.processing_time_ms}ms"
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
            "settings_source": "intelia_settings" if SETTINGS_AVAILABLE else "environment_variables"
        }

# ==================== INSTANCE GLOBALE ====================

# Instance singleton du système de clarification
clarification_system = QuestionClarificationSystem()

# ==================== FONCTIONS UTILITAIRES ====================

async def analyze_question_for_clarification(
    question: str, 
    language: str = "fr",
    user_id: str = "unknown", 
    conversation_id: str = None
) -> ClarificationResult:
    """
    Fonction utilitaire pour analyser les questions
    
    Args:
        question: La question à analyser
        language: Langue de la question
        user_id: ID utilisateur pour les logs
        conversation_id: ID de conversation
        
    Returns:
        ClarificationResult: Résultat de l'analyse
    """
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
    """
    Construit une question enrichie avec les réponses de clarification
    
    Args:
        original_question: Question originale
        clarification_answers: Réponses aux questions de clarification (index -> réponse)
        clarification_questions: Questions de clarification originales
        
    Returns:
        str: Question enrichie
    """
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

logger.info("❓ [QuestionClarificationSystem] Module de clarification intelligent initialisé")
logger.info(f"📊 [QuestionClarificationSystem] Statistiques: {clarification_system.get_stats()}")
