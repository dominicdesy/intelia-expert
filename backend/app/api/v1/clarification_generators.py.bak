"""
app/api/v1/clarification_generators.py - GÉNÉRATION DES QUESTIONS

Contient:
- Génération dynamique avec GPT + validation
- Questions adaptatives par règles
- Extraction texte libre
- Fallbacks intelligents
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any

from .clarification_entities import ClarificationMode

# Import OpenAI sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """Générateur de questions de clarification avec validation robuste"""
    
    def __init__(self, model: str = "gpt-4o-mini", timeout: int = 25, max_questions: int = 4):
        self.model = model
        self.timeout = timeout
        self.max_questions = max_questions
        self.validation_threshold = 0.5
        self.enable_validation = True
        self.enable_fallback = True
        
        # Templates de questions adaptatives
        self.adaptive_templates = {
            "fr": {
                "breed": "Quelle est la race/lignée exacte de vos poulets (Ross 308, Cobb 500, Lohmann LSL-Lite, etc.) ?",
                "age": "Quel âge ont-ils actuellement (en jours précis) ?",
                "symptoms": "Quels symptômes spécifiques observez-vous ?",
                "housing": "Dans quel type d'élevage sont-ils logés (bâtiment fermé, semi-ouvert, plein air) ?",
                "feed": "Quel type d'alimentation utilisez-vous actuellement ?",
                "duration": "Depuis combien de temps observez-vous ce problème ?",
                "conditions": "Quelles sont les conditions environnementales actuelles (température, humidité) ?"
            },
            "en": {
                "breed": "What is the exact breed/line of your chickens (Ross 308, Cobb 500, Lohmann LSL-Lite, etc.)?",
                "age": "How old are they currently (in precise days)?",
                "symptoms": "What specific symptoms do you observe?",
                "housing": "What type of housing are they in (closed building, semi-open, free-range)?",
                "feed": "What type of feed are you currently using?",
                "duration": "How long have you been observing this problem?",
                "conditions": "What are the current environmental conditions (temperature, humidity)?"
            },
            "es": {
                "breed": "¿Cuál es la raza/línea exacta de sus pollos (Ross 308, Cobb 500, Lohmann LSL-Lite, etc.)?",
                "age": "¿Qué edad tienen actualmente (en días precisos)?",
                "symptoms": "¿Qué síntomas específicos observa?",
                "housing": "¿En qué tipo de alojamiento están (edificio cerrado, semi-abierto, campo libre)?",
                "feed": "¿Qué tipo de alimentación está usando actualmente?",
                "duration": "¿Desde cuándo observa este problema?",
                "conditions": "¿Cuáles son las condiciones ambientales actuales (temperatura, humedad)?"
            }
        }
        
        # Fallback basiques
        self.basic_fallbacks = {
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

    def generate_dynamic_questions_with_validation(self, user_question: str, language: str = "fr") -> Tuple[List[str], Dict[str, Any]]:
        """
        🆕 Génère jusqu'à 4 questions de clarification via GPT avec validation robuste automatique
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
            # Vérifier disponibilité OpenAI
            if not OPENAI_AVAILABLE or not openai:
                logger.warning("⚠️ [Dynamic Generator] OpenAI non disponible - fallback intelligent")
                validation_metadata["fallback_used"] = True
                validation_metadata["fallback_reason"] = "openai_unavailable"
                fallback_questions = self._get_intelligent_fallback(user_question, language)
                return fallback_questions, validation_metadata

            # Configuration OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("⚠️ [Dynamic Generator] Clé API OpenAI manquante - fallback intelligent")
                validation_metadata["fallback_used"] = True
                validation_metadata["fallback_reason"] = "api_key_missing"
                fallback_questions = self._get_intelligent_fallback(user_question, language)
                return fallback_questions, validation_metadata
            
            openai.api_key = api_key

            # Construire le prompt contextualisé
            prompt = self._build_dynamic_prompt(user_question, language)
            logger.info(f"🤖 [Dynamic Generator] Prompt généré pour: '{user_question[:50]}...'")

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
            
            logger.info(f"🤖 [Dynamic Generator] Réponse reçue ({len(content)} chars)")
            
            # Parser la réponse JSON avec fallback
            questions = self._parse_gpt_response(content, language)
            validation_metadata["questions_generated"] = len(questions)
            
            # Validation robuste des questions générées
            if self.enable_validation and questions:
                validation_metadata["validation_performed"] = True
                
                validation_result = self._validate_questions(questions, user_question, language)
                validation_metadata["validation_score"] = validation_result.get("quality_score", 0.0)
                
                logger.info(f"🔧 [Question Validation] Score qualité: {validation_metadata['validation_score']:.2f}")
                
                # Vérifier si validation échoue
                if validation_metadata["validation_score"] < self.validation_threshold:
                    logger.warning(f"⚠️ [Question Validation] Score trop bas ({validation_metadata['validation_score']:.2f} < {self.validation_threshold})")
                    
                    valid_questions = validation_result.get("valid_questions", [])
                    if valid_questions and len(valid_questions) >= 1:
                        questions = valid_questions[:self.max_questions]
                        validation_metadata["questions_validated"] = len(questions)
                    else:
                        if self.enable_fallback:
                            validation_metadata["fallback_used"] = True
                            validation_metadata["fallback_reason"] = "validation_failed"
                            fallback_questions = self._get_intelligent_fallback(user_question, language)
                            return fallback_questions, validation_metadata
                        else:
                            questions = []
                else:
                    # Validation réussie
                    questions = validation_result.get("valid_questions", questions)[:self.max_questions]
                    validation_metadata["questions_validated"] = len(questions)
                    
            else:
                # Pas de validation - nettoyage basique
                questions = self._clean_questions(questions)
                validation_metadata["questions_validated"] = len(questions)
            
            if questions:
                logger.info(f"✅ [Dynamic Generator] {len(questions)} questions générées et validées")
                return questions, validation_metadata
            else:
                logger.warning("⚠️ [Dynamic Generator] Aucune question finale - fallback")
                if self.enable_fallback:
                    validation_metadata["fallback_used"] = True
                    validation_metadata["fallback_reason"] = "no_final_questions"
                    fallback_questions = self._get_intelligent_fallback(user_question, language)
                    return fallback_questions, validation_metadata
                else:
                    return [], validation_metadata
            
        except Exception as e:
            logger.error(f"❌ [Dynamic Generator] Erreur génération: {e}")
            validation_metadata["fallback_used"] = True
            validation_metadata["fallback_reason"] = f"exception: {str(e)}"
            
            if self.enable_fallback:
                fallback_questions = self._get_intelligent_fallback(user_question, language)
                return fallback_questions, validation_metadata
            else:
                return [], validation_metadata

    def generate_adaptive_questions(self, language: str, missing_info: List[str], question_type: str) -> List[str]:
        """Génère des questions adaptatives selon les informations manquantes"""
        
        templates = self.adaptive_templates.get(language, self.adaptive_templates["fr"])
        questions = []
        
        # Priorise selon le type de question
        priority_mapping = {
            "growth": ["breed", "age"],
            "weight": ["breed", "age"],
            "health": ["breed", "age", "symptoms"],
            "mortality": ["breed", "age", "symptoms", "duration"],
            "environment": ["breed", "age", "conditions"],
            "feeding": ["breed", "age", "feed"],
            "performance": ["breed", "age"],
            "laying": ["breed", "age"]
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

    def _build_dynamic_prompt(self, user_question: str, language: str) -> str:
        """Construit le prompt pour génération dynamique"""
        
        prompt_templates = {
            "fr": f"""Tu es un expert vétérinaire en aviculture. Un utilisateur pose cette question :

"{user_question}"

Génère 2-4 questions de clarification TRÈS SPÉCIFIQUES et CONTEXTUELLES pour cette situation précise.

RÈGLES STRICTES:
- Questions PRÉCISES liées à la situation décrite
- Évite les questions trop génériques
- Focus sur les détails techniques importants
- Adapte au contexte de la question

Réponds UNIQUEMENT avec ce format JSON:
{{
  "clarification_questions": [
    "Question précise 1 ?",
    "Question précise 2 ?", 
    "Question précise 3 ?"
  ]
}}""",
            
            "en": f"""You are a veterinary expert in poultry farming. A user asks this question:

"{user_question}"

Generate 2-4 VERY SPECIFIC and CONTEXTUAL clarification questions for this precise situation.

STRICT RULES:
- PRECISE questions related to the described situation
- Avoid too generic questions
- Focus on important technical details
- Adapt to the question context

Respond ONLY with this JSON format:
{{
  "clarification_questions": [
    "Precise question 1?",
    "Precise question 2?", 
    "Precise question 3?"
  ]
}}""",
            
            "es": f"""Eres un experto veterinario en avicultura. Un usuario hace esta pregunta:

"{user_question}"

Genera 2-4 preguntas de aclaración MUY ESPECÍFICAS y CONTEXTUALES para esta situación precisa.

REGLAS ESTRICTAS:
- Preguntas PRECISAS relacionadas con la situación descrita
- Evita preguntas demasiado genéricas
- Enfócate en detalles técnicos importantes
- Adapta al contexto de la pregunta

Responde SOLO con este formato JSON:
{{
  "clarification_questions": [
    "Pregunta precisa 1?",
    "Pregunta precisa 2?", 
    "Pregunta precisa 3?"
  ]
}}"""
        }
        
        return prompt_templates.get(language, prompt_templates["fr"])

    def _parse_gpt_response(self, content: str, language: str) -> List[str]:
        """Parse la réponse GPT pour extraire les questions"""
        
        questions = []
        
        try:
            # Chercher JSON
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                questions = data.get("clarification_questions", [])
                logger.info(f"🤖 [Parser] {len(questions)} questions extraites du JSON")
            else:
                logger.warning("⚠️ [Parser] Pas de JSON - extraction texte libre")
                questions = self._extract_questions_from_text(content, language)
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ [Parser] Erreur JSON: {e}")
            questions = self._extract_questions_from_text(content, language)
        
        return questions

    def _extract_questions_from_text(self, text: str, language: str) -> List[str]:
        """Extrait les questions depuis un texte libre"""
        
        questions = []
        lines = text.split('\n')
        
        # Mots-clés de questions par langue
        question_keywords = {
            "fr": ['quel', 'quelle', 'comment', 'combien', 'où', 'quand', 'pourquoi', 'depuis quand'],
            "en": ['what', 'how', 'which', 'where', 'when', 'why', 'how long', 'what type'],
            "es": ['qué', 'cuál', 'cómo', 'dónde', 'cuándo', 'por qué', 'cuánto tiempo', 'qué tipo']
        }
        
        keywords = question_keywords.get(language, question_keywords["fr"])
        
        for line in lines:
            line = line.strip()
            
            if ('?' in line or any(word in line.lower() for word in keywords)):
                # Nettoyer la ligne
                cleaned = re.sub(r'^[-•*\d]+\.?\s*', '', line)
                cleaned = cleaned.strip()
                
                if (len(cleaned) > 15 and len(cleaned) < 150 and 
                    len(questions) < self.max_questions and cleaned not in questions):
                    
                    if not cleaned.endswith('?'):
                        cleaned += ' ?'
                    questions.append(cleaned)
        
        return questions

    def _validate_questions(self, questions: List[str], user_question: str, language: str) -> Dict[str, Any]:
        """Validation robuste des questions générées"""
        
        valid_questions = []
        quality_scores = []
        
        # Mots interdits génériques
        forbidden_phrases = {
            "fr": ["par exemple", "généralement", "souvent", "habituellement", "etc"],
            "en": ["for example", "generally", "often", "usually", "etc"],
            "es": ["por ejemplo", "generalmente", "a menudo", "usualmente", "etc"]
        }
        
        forbidden = forbidden_phrases.get(language, forbidden_phrases["fr"])
        
        for question in questions:
            if not isinstance(question, str):
                continue
                
            q = question.strip()
            score = 0.0
            
            # Critères de validation
            if len(q) >= 20 and len(q) <= 150:
                score += 0.3
            
            if '?' in q:
                score += 0.2
                
            if not any(phrase in q.lower() for phrase in forbidden):
                score += 0.2
                
            # Bonus spécificité technique
            tech_terms = ["race", "lignée", "souche", "âge", "jours", "température", "symptômes", 
                         "breed", "strain", "age", "days", "temperature", "symptoms",
                         "raza", "cepa", "edad", "días", "temperatura", "síntomas"]
            if any(term in q.lower() for term in tech_terms):
                score += 0.3
            
            quality_scores.append(score)
            
            if score >= 0.5:  # Seuil de qualité
                valid_questions.append(q)
        
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return {
            "valid_questions": valid_questions,
            "quality_score": avg_score,
            "individual_scores": quality_scores
        }

    def _clean_questions(self, questions: List[str]) -> List[str]:
        """Nettoyage basique des questions"""
        
        cleaned = []
        for q in questions[:self.max_questions]:
            if isinstance(q, str) and len(q.strip()) > 10:
                cleaned_q = q.strip()
                if not cleaned_q.endswith('?'):
                    cleaned_q += ' ?'
                cleaned.append(cleaned_q)
        return cleaned

    def _get_intelligent_fallback(self, user_question: str, language: str) -> List[str]:
        """Fallback intelligent basé sur le contenu de la question"""
        
        question_lower = user_question.lower()
        
        # Détection du type de question pour fallback adapté
        if any(word in question_lower for word in ["croissance", "growth", "crecimiento", "poids", "weight", "peso"]):
            return self.generate_adaptive_questions(language, ["breed", "age"], "growth")
        elif any(word in question_lower for word in ["maladie", "disease", "enfermedad", "mort", "mort", "muerte"]):
            return self.generate_adaptive_questions(language, ["breed", "age", "symptoms"], "health")
        elif any(word in question_lower for word in ["température", "temperature", "temperatura", "environnement"]):
            return self.generate_adaptive_questions(language, ["breed", "age", "conditions"], "environment")
        else:
            # Fallback générique
            return self.basic_fallbacks.get(language, self.basic_fallbacks["fr"])