"""
app/api/v1/expert_clarification_service.py - SERVICE D'AUTO-CLARIFICATION

🔧 SERVICE INDÉPENDANT:
- Auto-clarification simplifiée avec validation robuste
- Scoring et validation qualité des questions générées
- Fallback intelligent si GPT échoue
- Questions de fallback par type détecté
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

# Import sécurisé au niveau module pour éviter les imports circulaires
try:
    from .expert_models import EnhancedExpertResponse, DynamicClarification
except ImportError as e:
    logger.error(f"❌ Import error for expert_models: {e}")
    # Définir des classes mock si nécessaire
    class EnhancedExpertResponse:
        pass
    class DynamicClarification:
        pass

logger = logging.getLogger(__name__)

# =============================================================================
# FONCTIONS DE VALIDATION ET AUTO-CLARIFICATION
# =============================================================================

def validate_dynamic_questions(questions: List[str], user_question: str = "", language: str = "fr") -> Tuple[float, List[str]]:
    """
    Valide la qualité des questions générées
    
    Returns:
        Tuple[float, List[str]]: (score_qualité, questions_filtrées)
    """
    
    # Validation d'entrée corrigée
    if questions is None:
        logger.warning("🔧 [Question Validation] Questions est None")
        return 0.0, []
    
    if not isinstance(questions, list):
        logger.warning(f"🔧 [Question Validation] Format incorrect: {type(questions)}")
        return 0.0, []
    
    if len(questions) == 0:
        logger.warning("🔧 [Question Validation] Liste vide")
        return 0.0, []
    
    # Mots-clés génériques à filtrer
    generic_keywords = {
        "fr": ["exemple", "par exemple", "etc", "quelque chose", "généralement", "souvent"],
        "en": ["example", "for example", "etc", "something", "generally", "often"],
        "es": ["ejemplo", "por ejemplo", "etc", "algo", "generalmente", "a menudo"]
    }
    
    keywords = generic_keywords.get(language, generic_keywords["fr"])
    
    # Filtrage amélioré avec gestion d'erreurs
    filtered = []
    for i, question in enumerate(questions):
        try:
            if not isinstance(question, str):
                logger.warning(f"🔧 [Question Validation] Question {i} n'est pas une string: {type(question)}")
                continue
                
            question = question.strip()
            
            # Tests de qualité
            if (len(question) > 15 and 
                len(question) < 200 and
                not any(keyword in question.lower() for keyword in keywords) and
                question not in filtered):
                
                # Ajouter point d'interrogation si manquant
                if not question.endswith('?'):
                    question += ' ?'
                    
                filtered.append(question)
        except Exception as e:
            logger.error(f"❌ [Question Validation] Erreur traitement question {i}: {e}")
            continue
    
    # Limiter à 4 questions maximum
    filtered = filtered[:4]
    
    # Calculer score de qualité
    original_count = len(questions)
    if original_count > 0:
        score = len(filtered) / original_count
    else:
        score = 0.0
    
    logger.info(f"🔧 [Question Validation] Score: {score:.2f}, Questions filtrées: {len(filtered)}/{original_count}")
    
    return score, filtered

def auto_clarify_if_needed(question: str, conversation_context: str, language: str = "fr") -> Optional[Dict[str, Any]]:
    """
    Fonction centralisée pour l'auto-clarification
    
    Returns:
        Dict si clarification nécessaire, None sinon
    """
    
    try:
        # Calculer score de complétude de base
        completeness_score = _calculate_basic_completeness_score(question, conversation_context, language)
        
        logger.info(f"🔧 [Auto Clarify] Score complétude: {completeness_score:.2f}")
        
        # Seuil pour déclencher clarification
        if completeness_score < 0.5:
            logger.info("🔧 [Auto Clarify] Clarification nécessaire - génération questions")
            
            # Tenter génération dynamique avec GPT
            questions = _generate_clarification_questions_with_fallback(question, language)
            
            if questions and len(questions) > 0:
                return {
                    "type": "clarification_needed",
                    "message": _get_clarification_intro_message(language),
                    "questions": questions,
                    "completeness_score": completeness_score,
                    "generation_method": "auto_clarification"
                }
            else:
                logger.warning("🔧 [Auto Clarify] Aucune question générée")
                
    except Exception as e:
        logger.error(f"❌ [Auto Clarify] Erreur génération questions: {e}")
    
    return None

def _calculate_basic_completeness_score(question: str, conversation_context: str, language: str = "fr") -> float:
    """Calcule un score de complétude simplifié (0.0 à 1.0)"""
    
    try:
        score = 0.0
        
        # Validation d'entrée
        if not isinstance(question, str) or len(question.strip()) == 0:
            return 0.0
        
        question_clean = question.strip()
        
        # Score de base selon la longueur
        question_length = len(question_clean)
        if question_length > 50:
            score += 0.3
        elif question_length > 25:
            score += 0.2
        
        # Présence de race spécifique
        specific_breeds = ["ross 308", "cobb 500", "hubbard", "arbor acres"]
        if any(breed in question_clean.lower() for breed in specific_breeds):
            score += 0.3
        elif any(word in question_clean.lower() for word in ["poulet", "chicken", "pollo"]):
            score += 0.1
        
        # Présence d'âge
        age_patterns = [r'\d+\s*(?:jour|day|día)s?', r'\d+\s*(?:semaine|week|semana)s?']
        if any(re.search(pattern, question_clean.lower()) for pattern in age_patterns):
            score += 0.2
        
        # Présence de données numériques
        if re.search(r'\d+', question_clean):
            score += 0.1
        
        # Contexte conversationnel disponible
        if conversation_context and isinstance(conversation_context, str) and len(conversation_context.strip()) > 50:
            score += 0.1
        
        return min(score, 1.0)
        
    except Exception as e:
        logger.error(f"❌ [Completeness Score] Erreur calcul: {e}")
        return 0.0

def _generate_clarification_questions_with_fallback(question: str, language: str = "fr") -> List[str]:
    """Génère questions avec fallback si GPT échoue"""
    
    try:
        # Import sécurisé avec gestion d'erreur spécifique
        try:
            from .question_clarification_system import generate_dynamic_clarification_questions_with_validation
            
            # Tenter génération dynamique avec validation
            questions, validation_metadata = generate_dynamic_clarification_questions_with_validation(question, language)
            
            # Vérifier qualité
            score, filtered_questions = validate_dynamic_questions(questions, question, language)
            
            if score >= 0.5 and filtered_questions:
                logger.info(f"✅ [Clarification Generation] Questions GPT validées: {len(filtered_questions)}")
                return filtered_questions
            else:
                logger.warning(f"⚠️ [Clarification Generation] Score trop bas ({score:.2f}) - fallback")
                
        except ImportError as e:
            logger.warning(f"⚠️ [Clarification Generation] Module non disponible: {e} - fallback")
        except AttributeError as e:
            logger.warning(f"⚠️ [Clarification Generation] Fonction non disponible: {e} - fallback")
        except Exception as e:
            logger.warning(f"⚠️ [Clarification Generation] Erreur GPT: {e} - fallback")
            
    except Exception as e:
        logger.error(f"❌ [Clarification Generation] Erreur critique: {e}")
    
    # Fallback : questions basiques selon le type
    return _get_fallback_questions_by_type(question, language)

def _get_fallback_questions_by_type(question: str, language: str = "fr") -> List[str]:
    """Questions de fallback selon le type de question détecté"""
    
    try:
        if not isinstance(question, str):
            logger.error(f"❌ [Fallback Questions] Question invalide: {type(question)}")
            return []
        
        question_lower = question.lower()
        
        # Détection type de question avec gestion d'erreur
        is_weight = any(word in question_lower for word in ["poids", "weight", "peso"])
        is_health = any(word in question_lower for word in ["maladie", "disease", "mort", "death"])
        is_growth = any(word in question_lower for word in ["croissance", "growth", "développement"])
        
        fallback_questions = {
            "fr": {
                "weight": [
                    "Quelle race ou souche spécifique élevez-vous (Ross 308, Cobb 500, etc.) ?",
                    "Quel âge ont actuellement vos poulets (en jours précis) ?",
                    "S'agit-il de mâles, femelles, ou d'un troupeau mixte ?"
                ],
                "health": [
                    "Quelle race ou souche élevez-vous ?",
                    "Quel âge ont vos volailles actuellement ?",
                    "Quels symptômes spécifiques observez-vous ?"
                ],
                "growth": [
                    "Quelle race ou souche spécifique élevez-vous ?",
                    "Quel âge ont-ils actuellement en jours ?",
                    "Quelles sont les conditions d'élevage actuelles ?"
                ],
                "general": [
                    "Pouvez-vous préciser la race ou souche de vos volailles ?",
                    "Quel âge ont actuellement vos animaux ?",
                    "Dans quel contexte d'élevage vous trouvez-vous ?"
                ]
            },
            "en": {
                "weight": [
                    "What specific breed or strain are you raising (Ross 308, Cobb 500, etc.)?",
                    "What is the current age of your chickens (in precise days)?",
                    "Are these males, females, or a mixed flock?"
                ],
                "health": [
                    "What breed or strain are you raising?",
                    "What is the current age of your poultry?",
                    "What specific symptoms are you observing?"
                ],
                "growth": [
                    "What specific breed or strain are you raising?",
                    "What is their current age in days?",
                    "What are the current housing conditions?"
                ],
                "general": [
                    "Could you specify the breed or strain of your poultry?",
                    "What age are your animals currently?",
                    "What farming context are you in?"
                ]
            },
            "es": {
                "weight": [
                    "¿Qué raza o cepa específica está criando (Ross 308, Cobb 500, etc.)?",
                    "¿Cuál es la edad actual de sus pollos (en días precisos)?",
                    "¿Son machos, hembras, o un lote mixto?"
                ],
                "health": [
                    "¿Qué raza o cepa está criando?",
                    "¿Cuál es la edad actual de sus aves?",
                    "¿Qué síntomas específicos está observando?"
                ],
                "growth": [
                    "¿Qué raza o cepa específica está criando?",
                    "¿Cuál es su edad actual en días?",
                    "¿Cuáles son las condiciones actuales de alojamiento?"
                ],
                "general": [
                    "¿Podría especificar la raza o cepa de sus aves?",
                    "¿Qué edad tienen actualmente sus animales?",
                    "¿En qué contexto de cría se encuentra?"
                ]
            }
        }
        
        lang_questions = fallback_questions.get(language, fallback_questions["fr"])
        
        # Sélectionner type approprié
        if is_weight:
            return lang_questions["weight"]
        elif is_health:
            return lang_questions["health"]
        elif is_growth:
            return lang_questions["growth"]
        else:
            return lang_questions["general"]
            
    except Exception as e:
        logger.error(f"❌ [Fallback Questions] Erreur: {e}")
        # Fallback ultime
        return ["Pouvez-vous préciser votre question ?"]

def _get_clarification_intro_message(language: str = "fr") -> str:
    """Message d'introduction pour la clarification"""
    
    messages = {
        "fr": "Votre question manque de contexte. Voici quelques questions pour mieux vous aider :",
        "en": "Your question lacks context. Here are some questions to better help you:",
        "es": "Su pregunta carece de contexto. Aquí hay algunas preguntas para ayudarle mejor:"
    }
    
    return messages.get(language, messages["fr"])

# =============================================================================
# CLASSE DE SERVICE DE CLARIFICATION
# =============================================================================

class ExpertClarificationService:
    """Service centralisé pour la gestion de la clarification"""
    
    def __init__(self):
        logger.info("✅ [Clarification Service] Service d'auto-clarification initialisé")
    
    def detect_performance_question_needing_clarification(
        self, question: str, language: str = "fr"
    ) -> Optional[Dict[str, Any]]:
        """Détection améliorée des questions techniques nécessitant race/sexe"""
        
        try:
            if not isinstance(question, str) or len(question.strip()) == 0:
                logger.warning("❌ [Performance Detection] Question invalide")
                return None
            
            question_lower = question.lower()
            
            weight_age_patterns = {
                "fr": [
                    r'(?:poids|pèse)\s+.*?(\d+)\s*(?:jour|semaine)s?',
                    r'(\d+)\s*(?:jour|semaine)s?.*?(?:poids|pèse)',
                    r'(?:quel|combien)\s+.*?(?:poids|pèse).*?(\d+)',
                    r'(?:croissance|développement).*?(\d+)\s*(?:jour|semaine)',
                    r'(\d+)\s*(?:jour|semaine).*?(?:normal|référence|standard)'
                ],
                "en": [
                    r'(?:weight|weigh)\s+.*?(\d+)\s*(?:day|week)s?',
                    r'(\d+)\s*(?:day|week)s?.*?(?:weight|weigh)',
                    r'(?:what|how much)\s+.*?(?:weight|weigh).*?(\d+)',
                    r'(?:growth|development).*?(\d+)\s*(?:day|week)',
                    r'(\d+)\s*(?:day|week).*?(?:normal|reference|standard)'
                ],
                "es": [
                    r'(?:peso|pesa)\s+.*?(\d+)\s*(?:día|semana)s?',
                    r'(\d+)\s*(?:día|semana)s?.*?(?:peso|pesa)',
                    r'(?:cuál|cuánto)\s+.*?(?:peso|pesa).*?(\d+)',
                    r'(?:crecimiento|desarrollo).*?(\d+)\s*(?:día|semana)',
                    r'(\d+)\s*(?:día|semana).*?(?:normal|referencia|estándar)'
                ]
            }
            
            patterns = weight_age_patterns.get(language, weight_age_patterns["fr"])
            
            age_detected = None
            for pattern in patterns:
                try:
                    match = re.search(pattern, question_lower)
                    if match:
                        age_detected = match.group(1)
                        break
                except re.error as e:
                    logger.error(f"❌ [Performance Detection] Erreur regex: {e}")
                    continue
            
            if not age_detected:
                return None
            
            breed_patterns = [
                r'\b(ross\s*308|ross\s*708|cobb\s*500|cobb\s*700|hubbard|arbor\s*acres)\b',
                r'\b(broiler|poulet|chicken|pollo)\s+(ross|cobb|hubbard)',
                r'\brace\s*[:\-]?\s*(ross|cobb|hubbard)'
            ]
            
            sex_patterns = [
                r'\b(mâle|male|macho)s?\b',
                r'\b(femelle|female|hembra)s?\b',
                r'\b(coq|hen|poule|gallina)\b',
                r'\b(mixte|mixed|misto)\b'
            ]
            
            has_breed = any(re.search(pattern, question_lower, re.IGNORECASE) for pattern in breed_patterns)
            has_sex = any(re.search(pattern, question_lower, re.IGNORECASE) for pattern in sex_patterns)
            
            if not has_breed and not has_sex:
                return {
                    "type": "performance_question_missing_breed_sex",
                    "age_detected": age_detected,
                    "question_type": "weight_performance",
                    "missing_info": ["breed", "sex"],
                    "confidence": 0.95
                }
            
            elif not has_breed or not has_sex:
                missing = []
                if not has_breed:
                    missing.append("breed")
                if not has_sex:
                    missing.append("sex")
                
                return {
                    "type": "performance_question_partial_info",
                    "age_detected": age_detected,
                    "question_type": "weight_performance", 
                    "missing_info": missing,
                    "confidence": 0.8
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [Performance Detection] Erreur critique: {e}")
            return None
    
    def generate_performance_clarification_response(
        self, question: str, clarification_info: Dict, language: str, conversation_id: str
    ) -> EnhancedExpertResponse:
        """Génère la demande de clarification optimisée"""
        
        try:
            age = clarification_info.get("age_detected", "X")
            missing_info = clarification_info.get("missing_info", [])
            
            clarification_messages = {
                "fr": {
                    "both_missing": f"Pour vous donner le poids de référence exact d'un poulet de {age} jours, j'ai besoin de :\n\n• **Race/souche** : Ross 308, Cobb 500, Hubbard, etc.\n• **Sexe** : Mâles, femelles, ou troupeau mixte\n\nPouvez-vous préciser ces informations ?",
                    "breed_missing": f"Pour le poids exact à {age} jours, quelle est la **race/souche** (Ross 308, Cobb 500, Hubbard, etc.) ?",
                    "sex_missing": f"Pour le poids exact à {age} jours, s'agit-il de **mâles, femelles, ou d'un troupeau mixte** ?"
                },
                "en": {
                    "both_missing": f"To give you the exact reference weight for a {age}-day chicken, I need:\n\n• **Breed/strain**: Ross 308, Cobb 500, Hubbard, etc.\n• **Sex**: Males, females, or mixed flock\n\nCould you specify this information?",
                    "breed_missing": f"For the exact weight at {age} days, what is the **breed/strain** (Ross 308, Cobb 500, Hubbard, etc.)?",
                    "sex_missing": f"For the exact weight at {age} days, are these **males, females, or a mixed flock**?"
                },
                "es": {
                    "both_missing": f"Para darle el peso de referencia exacto de un pollo de {age} días, necesito:\n\n• **Raza/cepa**: Ross 308, Cobb 500, Hubbard, etc.\n• **Sexo**: Machos, hembras, o lote mixto\n\n¿Podría especificar esta información?",
                    "breed_missing": f"Para el peso exacto a los {age} días, ¿cuál es la **raza/cepa** (Ross 308, Cobb 500, Hubbard, etc.)?",
                    "sex_missing": f"Para el peso exacto a los {age} días, ¿son **machos, hembras, o un lote mixto**?"
                }
            }
            
            messages = clarification_messages.get(language, clarification_messages["fr"])
            
            if len(missing_info) >= 2:
                response_text = messages["both_missing"]
            elif "breed" in missing_info:
                response_text = messages["breed_missing"]
            else:
                response_text = messages["sex_missing"]
            
            examples = {
                "fr": "\n\n**Exemples de réponses :**\n• \"Ross 308 mâles\"\n• \"Cobb 500 femelles\"\n• \"Hubbard troupeau mixte\"",
                "en": "\n\n**Example responses:**\n• \"Ross 308 males\"\n• \"Cobb 500 females\"\n• \"Hubbard mixed flock\"",
                "es": "\n\n**Ejemplos de respuestas:**\n• \"Ross 308 machos\"\n• \"Cobb 500 hembras\"\n• \"Hubbard lote mixto\""
            }
            
            response_text += examples.get(language, examples["fr"])
            
            return EnhancedExpertResponse(
                question=question,
                response=response_text,
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=language,
                response_time_ms=50,
                mode="smart_performance_clarification_corrected",
                user=None,
                logged=True,
                validation_passed=True,
                clarification_result={
                    "clarification_requested": True,
                    "clarification_type": "performance_breed_sex",
                    "missing_information": missing_info,
                    "age_detected": age,
                    "confidence": clarification_info.get("confidence", 0.9)
                },
                processing_steps=["smart_clarification_triggered"],
                ai_enhancements_used=["performance_question_detection", "targeted_clarification"]
            )
            
        except Exception as e:
            logger.error(f"❌ [Performance Clarification] Erreur génération réponse: {e}")
            # Retourner une réponse par défaut en cas d'erreur
            return self._create_fallback_response(question, conversation_id, language)
    
    def create_semantic_dynamic_clarification_response(
        self, question: str, clarification_result, language: str, conversation_id: str
    ) -> EnhancedExpertResponse:
        """Crée une réponse de clarification sémantique dynamique"""
        
        try:
            # Validation des paramètres d'entrée
            if not hasattr(clarification_result, 'questions'):
                logger.error("❌ [Semantic Clarification] clarification_result manque l'attribut 'questions'")
                return self._create_fallback_response(question, conversation_id, language)
            
            # Formater les questions de clarification
            if clarification_result.questions and len(clarification_result.questions) > 0:
                if len(clarification_result.questions) == 1:
                    response_text = f"❓ Pour mieux comprendre votre situation et vous aider efficacement :\n\n{clarification_result.questions[0]}"
                else:
                    formatted_questions = "\n".join([f"• {q}" for q in clarification_result.questions])
                    response_text = f"❓ Pour mieux comprendre votre situation et vous aider efficacement :\n\n{formatted_questions}"
                
                response_text += "\n\nCela me permettra de vous donner les conseils les plus pertinents ! 🐔"
            else:
                response_text = "❓ Pouvez-vous préciser votre question pour que je puisse mieux vous aider ?"
            
            return EnhancedExpertResponse(
                question=question,
                response=response_text,
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=language,
                response_time_ms=getattr(clarification_result, 'processing_time_ms', 100),
                mode="semantic_dynamic_clarification",
                user=None,
                logged=True,
                validation_passed=True,
                clarification_result={
                    "clarification_requested": True,
                    "clarification_type": "semantic_dynamic",
                    "questions_generated": len(clarification_result.questions) if hasattr(clarification_result, 'questions') and clarification_result.questions else 0,
                    "confidence": getattr(clarification_result, 'confidence_score', 0.5),
                    "model_used": getattr(clarification_result, 'model_used', 'fallback'),
                    "generation_time_ms": getattr(clarification_result, 'processing_time_ms', 100)
                },
                processing_steps=["semantic_dynamic_clarification_triggered"],
                ai_enhancements_used=["semantic_dynamic_clarification", "gpt_question_generation"],
                dynamic_clarification=DynamicClarification(
                    original_question=question,
                    clarification_questions=getattr(clarification_result, 'questions', []),
                    confidence=getattr(clarification_result, 'confidence_score', 0.5)
                )
            )
            
        except Exception as e:
            logger.error(f"❌ [Semantic Clarification] Erreur création réponse: {e}")
            return self._create_fallback_response(question, conversation_id, language)
    
    def _create_fallback_response(self, question: str, conversation_id: str, language: str) -> EnhancedExpertResponse:
        """Crée une réponse de fallback en cas d'erreur"""
        
        fallback_messages = {
            "fr": "Je ne peux pas traiter votre question pour le moment. Pouvez-vous la reformuler ?",
            "en": "I cannot process your question at the moment. Could you rephrase it?",
            "es": "No puedo procesar su pregunta en este momento. ¿Podría reformularla?"
        }
        
        return EnhancedExpertResponse(
            question=question,
            response=fallback_messages.get(language, fallback_messages["fr"]),
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=10,
            mode="fallback_error_response",
            user=None,
            logged=True,
            validation_passed=False,
            clarification_result={
                "clarification_requested": False,
                "error": "fallback_response_created"
            },
            processing_steps=["error_fallback"],
            ai_enhancements_used=[]
        )

logger.info("✅ [Clarification Service] Service d'auto-clarification initialisé")