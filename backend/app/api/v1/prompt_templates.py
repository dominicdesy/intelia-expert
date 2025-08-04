"""
app/api/v1/prompt_templates.py - TEMPLATES DE PROMPTS STRUCTURÉS AVEC VALIDATION ROBUSTE

🎯 OBJECTIF: Centraliser et standardiser les prompts pour le système RAG
🔧 AMÉLIORATION: Éliminer les références aux documents dans les réponses
✨ QUALITÉ: Réponses plus naturelles et professionnelles
🆕 NOUVEAU: Prompt de contextualisation pour mode sémantique dynamique
🔧 NOUVEAU: Validation robuste des questions générées dynamiquement
🔧 NOUVEAU: Fallback intelligent si GPT échoue
🎯 NOUVEAU: Filtrage avancé des questions non pertinentes
🔧 MISE À JOUR: Message utilisateur neutre centralisé

CORRECTIONS APPORTÉES:
- ✅ Import manquant 'json' ajouté
- ✅ Gestion robuste des erreurs JSON avec fallback
- ✅ Validation du format des questions renforcée
- ✅ Gestion des exceptions lors de l'extraction du contexte
- ✅ Documentation des types de retour améliorée
- ✅ Logique de validation plus robuste
- ✅ Gestion des cas edge dans l'analyse des questions
"""

import logging
import re
import json  # ✅ CORRECTION: Import manquant ajouté
from typing import Dict, Any, Optional, List, Tuple, Union

logger = logging.getLogger(__name__)

# ✅ Action 1 : Message utilisateur neutre centralisé
USER_NEEDS_CLARIFICATION_MSG = (
    "Votre question manque de contexte. "
    "Un expert virtuel va vous poser quelques questions pour mieux comprendre la situation. "
    "💡 Répondez simplement dans le chat avec les informations demandées."
)

def build_structured_prompt(documents: str, question: str, context: Dict[str, Any]) -> str:
    """
    🎯 PROMPT PRINCIPAL - Construit un prompt structuré pour le RAG
    
    Élimine les références aux documents et produit des réponses naturelles
    
    Args:
        documents: Contenu des documents trouvés
        question: Question de l'utilisateur
        context: Contexte extrait (breed, sex, age, lang)
        
    Returns:
        str: Prompt structuré pour le LLM
        
    Raises:
        ValueError: Si les paramètres requis sont manquants
    """
    
    # ✅ CORRECTION: Validation des paramètres d'entrée
    if not isinstance(documents, str):
        documents = str(documents) if documents else ""
    if not isinstance(question, str):
        question = str(question) if question else ""
    if not isinstance(context, dict):
        context = {}
    
    # Extraire les éléments du contexte avec valeurs par défaut sécurisées
    breed = context.get("breed", "non spécifiée")
    sex = context.get("sex", "non spécifié") 
    age = context.get("age", "non spécifié")
    language = context.get("lang", "fr")
    
    # ✅ CORRECTION: Validation de la langue avec fallback
    if not isinstance(language, str) or language.lower() not in ["en", "es", "fr"]:
        language = "fr"
    
    # Templates par langue
    try:
        if language.lower() == "en":
            return _build_english_prompt(documents, question, breed, sex, age)
        elif language.lower() == "es":
            return _build_spanish_prompt(documents, question, breed, sex, age)
        else:
            return _build_french_prompt(documents, question, breed, sex, age)
    except Exception as e:
        logger.error(f"❌ [Prompt Build] Erreur construction prompt: {e}")
        # Fallback vers français en cas d'erreur
        return _build_french_prompt(documents, question, breed, sex, age)

def _build_french_prompt(documents: str, question: str, breed: str, sex: str, age: str) -> str:
    """Template français optimisé avec gestion d'erreur"""
    
    # ✅ CORRECTION: Sécurisation des paramètres
    documents = str(documents) if documents else "Aucune information technique disponible"
    question = str(question) if question else "Question non spécifiée"
    breed = str(breed) if breed else "non spécifiée"
    sex = str(sex) if sex else "non spécifié"
    age = str(age) if age else "non spécifié"
    
    return f"""Vous êtes un expert en production avicole avec 20 ans d'expérience terrain.

CONTEXTE SPÉCIFIQUE :
- Race/souche : {breed}
- Sexe : {sex}
- Âge : {age}

INFORMATIONS TECHNIQUES DISPONIBLES :
{documents}

QUESTION À TRAITER :
{question}

INSTRUCTIONS CRITIQUES :
1. Répondez comme un expert qui maîtrise parfaitement ces informations techniques
2. NE mentionnez JAMAIS les termes "document", "source", "référence" ou "selon"
3. Intégrez naturellement les données chiffrées et recommandations techniques
4. Si l'information est incomplète, demandez des précisions spécifiques
5. Utilisez un ton professionnel mais accessible
6. Incluez toujours les données de performance pertinentes (poids, FCR, mortalité, etc.)
7. Donnez des fourchettes de valeurs quand approprié (ex: 410-450g)

RÉPONSE EXPERTE :"""

def _build_english_prompt(documents: str, question: str, breed: str, sex: str, age: str) -> str:
    """Template anglais optimisé avec gestion d'erreur"""
    
    # ✅ CORRECTION: Sécurisation des paramètres
    documents = str(documents) if documents else "No technical information available"
    question = str(question) if question else "Question not specified"
    breed = str(breed) if breed else "not specified"
    sex = str(sex) if sex else "not specified"
    age = str(age) if age else "not specified"
    
    return f"""You are a poultry production expert with 20 years of field experience.

SPECIFIC CONTEXT:
- Breed/strain: {breed}
- Sex: {sex}
- Age: {age}

TECHNICAL INFORMATION AVAILABLE:
{documents}

QUESTION TO ADDRESS:
{question}

CRITICAL INSTRUCTIONS:
1. Respond as an expert who perfectly masters this technical information
2. NEVER mention terms like "document", "source", "reference" or "according to"
3. Naturally integrate numerical data and technical recommendations
4. If information is incomplete, ask for specific clarifications
5. Use a professional but accessible tone
6. Always include relevant performance data (weight, FCR, mortality, etc.)
7. Provide value ranges when appropriate (e.g., 410-450g)

EXPERT RESPONSE:"""

def _build_spanish_prompt(documents: str, question: str, breed: str, sex: str, age: str) -> str:
    """Template espagnol optimisé avec gestion d'erreur"""
    
    # ✅ CORRECTION: Sécurisation des paramètres
    documents = str(documents) if documents else "No hay información técnica disponible"
    question = str(question) if question else "Pregunta no especificada"
    breed = str(breed) if breed else "no especificada"
    sex = str(sex) if sex else "no especificado"
    age = str(age) if age else "no especificada"
    
    return f"""Usted es un experto en producción avícola con 20 años de experiencia de campo.

CONTEXTO ESPECÍFICO:
- Raza/cepa: {breed}
- Sexo: {sex}
- Edad: {age}

INFORMACIÓN TÉCNICA DISPONIBLE:
{documents}

PREGUNTA A TRATAR:
{question}

INSTRUCCIONES CRÍTICAS:
1. Responda como un experto que domina perfectamente esta información técnica
2. NUNCA mencione términos como "documento", "fuente", "referencia" o "según"
3. Integre naturalmente los datos numéricos y recomendaciones técnicas
4. Si la información está incompleta, pida aclaraciones específicas
5. Use un tono profesional pero accesible
6. Incluya siempre datos de rendimiento relevantes (peso, conversión, mortalidad, etc.)
7. Proporcione rangos de valores cuando sea apropiado (ej: 410-450g)

RESPUESTA EXPERTA:"""

# ✅ Action 3 : Seule cette fonction génère des questions via GPT
def build_contextualization_prompt(user_question: str, language: str = "fr") -> str:
    """
    🆕 NOUVEAU: Construit un prompt pour générer des questions de clarification dynamiques.
    🔧 AMÉLIORÉ: Prompt optimisé pour éviter les exemples génériques non pertinents
    
    Args:
        user_question: Question originale de l'utilisateur
        language: Langue de réponse (fr/en/es)
        
    Returns:
        str: Prompt structuré pour GPT
        
    Raises:
        ValueError: Si la question utilisateur est vide
    """
    
    # ✅ CORRECTION: Validation des paramètres d'entrée
    if not user_question or not isinstance(user_question, str):
        raise ValueError("user_question ne peut pas être vide ou None")
    
    user_question = user_question.strip()
    if not user_question:
        raise ValueError("user_question ne peut pas être une chaîne vide")
    
    # ✅ CORRECTION: Validation de la langue avec fallback
    if not isinstance(language, str) or language.lower() not in ["en", "es", "fr"]:
        language = "fr"
        logger.warning(f"⚠️ [Contextualization] Langue invalide, fallback vers français")
    
    if language.lower() == "en":
        return f"""You are a poultry farming expert specialized in providing practical advice.

Your task is to help another AI agent better understand the following question: "{user_question}"

Analyze the question and deduce its main theme (e.g., laying drop, mortality, temperature, feeding, etc.). Then generate between 2 and 4 **targeted and concrete** clarification questions to better understand the problem.

CRITICAL RULES:
- Do NOT propose generic examples or hypothetical scenarios
- Do NOT reformulate the question
- Do NOT answer the question
- Do NOT mention breeds or species that are not already cited by the user
- Focus on MISSING INFORMATION that would help provide a precise answer
- Ask for SPECIFIC details (exact age, specific breed, current conditions)

GOOD examples of targeted questions:
- "What exact breed/strain are you raising?" (if not specified)
- "What is their current age in days?" (if age missing)
- "What specific symptoms are you observing?" (for health issues)
- "What are the current housing conditions?" (for environment issues)

Respond in this JSON format:
{{
  "clarification_questions": [
    "Question 1",
    "Question 2",
    "Question 3"
  ]
}}"""

    elif language.lower() == "es":
        return f"""Eres un experto en avicultura especializado en brindar asesoría práctica.

Tu tarea es ayudar a otro agente de IA a entender mejor la siguiente pregunta: "{user_question}"

Analiza la pregunta y deduce su tema principal (ej. caída de postura, mortalidad, temperatura, alimentación, etc.). Luego genera entre 2 y 4 preguntas de aclaración **dirigidas y concretas** para entender mejor el problema.

REGLAS CRÍTICAS:
- NO propongas ejemplos genéricos o escenarios hipotéticos
- NO reformules la pregunta
- NO respondas la pregunta
- NO menciones razas o especies que no hayan sido ya citadas por el usuario
- Enfócate en INFORMACIÓN FALTANTE que ayudaría a proporcionar una respuesta precisa
- Pregunta por detalles ESPECÍFICOS (edad exacta, raza específica, condiciones actuales)

Ejemplos BUENOS de preguntas dirigidas:
- "¿Qué raza/cepa exacta está criando?" (si no especificado)
- "¿Cuál es su edad actual en días?" (si falta la edad)
- "¿Qué síntomas específicos está observando?" (para problemas de salud)
- "¿Cuáles son las condiciones actuales de alojamiento?" (para problemas ambientales)

Responde en este formato JSON:
{{
  "clarification_questions": [
    "Pregunta 1",
    "Pregunta 2",
    "Pregunta 3"
  ]
}}"""

    else:  # français
        return f"""Tu es un expert en aviculture spécialisé dans les conseils pratiques.

Ta tâche est d'aider un autre agent IA à mieux comprendre la question suivante : "{user_question}"

Analyse la question et déduis son thème principal (ex. baisse de ponte, mortalité, température, alimentation, etc.). Puis génère entre 2 et 4 questions de clarification **ciblées et concrètes** pour mieux comprendre le problème.

RÈGLES CRITIQUES :
- Ne propose PAS d'exemples génériques ou de scénarios hypothétiques
- Ne reformule PAS la question
- Ne réponds PAS à la question
- Ne mentionne PAS de races ou d'espèces qui ne sont pas déjà citées par l'utilisateur
- Concentre-toi sur l'INFORMATION MANQUANTE qui aiderait à fournir une réponse précise
- Demande des détails SPÉCIFIQUES (âge exact, race spécifique, conditions actuelles)

Exemples BONS de questions ciblées :
- "Quelle race/souche exacte élevez-vous ?" (si non spécifié)
- "Quel est leur âge actuel en jours ?" (si âge manquant)
- "Quels symptômes spécifiques observez-vous ?" (pour problèmes de santé)
- "Quelles sont les conditions actuelles de logement ?" (pour problèmes environnementaux)

Réponds dans ce format JSON :
{{
  "clarification_questions": [
    "Question 1",
    "Question 2",
    "Question 3"
  ]
}}"""

def build_vagueness_prompt(vague_question: str, suggestions: List[str], language: str = "fr") -> str:
    """
    🎯 PROMPT VAGUENESS - Pour les questions trop floues
    
    Args:
        vague_question: Question jugée trop vague
        suggestions: Liste de suggestions plus précises
        language: Langue de réponse
        
    Returns:
        str: Message structuré pour l'utilisateur
    """
    
    # ✅ CORRECTION: Validation et sécurisation des paramètres
    if not isinstance(vague_question, str):
        vague_question = str(vague_question) if vague_question else "Question non spécifiée"
    
    if not isinstance(suggestions, list):
        suggestions = []
    
    # ✅ CORRECTION: Filtrer les suggestions vides ou invalides
    valid_suggestions = [str(s) for s in suggestions if s and str(s).strip()]
    
    if not valid_suggestions:
        valid_suggestions = ["Pouvez-vous être plus spécifique dans votre question ?"]
    
    suggestions_text = "\n".join([f"• {s}" for s in valid_suggestions])
    
    # ✅ CORRECTION: Validation de la langue avec fallback
    if not isinstance(language, str) or language.lower() not in ["en", "es", "fr"]:
        language = "fr"
    
    templates = {
        "fr": f"""Votre question "{vague_question}" nécessite plus de précision pour vous donner une réponse technique pertinente.

**Questions plus précises suggérées :**
{suggestions_text}

💡 Plus votre question est spécifique (race, âge, contexte), plus ma réponse sera utile et actionnable.""",
        
        "en": f"""Your question "{vague_question}" needs more precision to provide a relevant technical response.

**Suggested more specific questions:**
{suggestions_text}

💡 The more specific your question (breed, age, context), the more useful and actionable my response will be.""",
        
        "es": f"""Su pregunta "{vague_question}" necesita más precisión para proporcionar una respuesta técnica relevante.

**Preguntas más específicas sugeridas:**
{suggestions_text}

💡 Cuanto más específica sea su pregunta (raza, edad, contexto), más útil y práctica será mi respuesta."""
    }
    
    return templates.get(language.lower(), templates["fr"])

# =============================================================================
# 🔧 NOUVELLE FONCTION: VALIDATION ROBUSTE DES QUESTIONS DYNAMIQUES
# =============================================================================

def validate_dynamic_questions(questions: List[str], user_question: str = "", language: str = "fr") -> Dict[str, Any]:
    """
    🔧 NOUVEAU: Validation robuste des questions générées dynamiquement
    
    Args:
        questions: Liste des questions à valider
        user_question: Question originale de l'utilisateur (pour contexte)
        language: Langue des questions (fr/en/es)
        
    Returns:
        Dict[str, Any]: Résultats de validation avec quality_score
            - valid_questions: List[str] - Questions validées
            - invalid_questions: List[str] - Questions rejetées
            - quality_score: float (0.0 à 1.0) - Score de qualité
            - issues: List[str] - Problèmes détectés
            - filtered_count: int - Nombre de questions valides
            - validation_details: Dict - Détails des échecs
    """
    
    validation = {
        "valid_questions": [],
        "invalid_questions": [],
        "quality_score": 0.0,
        "issues": [],
        "filtered_count": 0,
        "validation_details": {}
    }
    
    # ✅ CORRECTION: Validation robuste des paramètres d'entrée
    if not questions:
        validation["quality_score"] = 0.0
        validation["issues"].append("Aucune question fournie")
        return validation
    
    if not isinstance(questions, list):
        try:
            # Essayer de convertir en liste si possible
            questions = list(questions) if hasattr(questions, '__iter__') else [questions]
        except (TypeError, ValueError):
            validation["quality_score"] = 0.0
            validation["issues"].append("Format de questions invalide - doit être une liste")
            return validation
    
    # ✅ CORRECTION: Filtrer les éléments None ou vides dès le début
    questions = [q for q in questions if q is not None and str(q).strip()]
    
    if not questions:
        validation["quality_score"] = 0.0
        validation["issues"].append("Toutes les questions sont vides ou invalides")
        return validation
    
    # ✅ CORRECTION: Validation de la langue avec fallback
    if not isinstance(language, str) or language.lower() not in ["en", "es", "fr"]:
        language = "fr"
        logger.warning(f"⚠️ [Question Validation] Langue invalide, fallback vers français")
    
    # Mots-clés de questions par langue
    question_words = {
        "fr": ["quel", "quelle", "combien", "comment", "où", "quand", "pourquoi", "dans quel", "depuis quand", "à quel"],
        "en": ["what", "which", "how", "where", "when", "why", "who", "how long", "what type", "at what"],
        "es": ["qué", "cuál", "cómo", "dónde", "cuándo", "por qué", "quién", "cuánto tiempo", "qué tipo", "a qué"]
    }
    
    # Mots-clés génériques à éviter (indiquent des questions trop vagues)
    generic_keywords = {
        "fr": ["exemple", "par exemple", "etc", "quelque chose", "peut-être", "généralement", "souvent", "parfois", "habituellement"],
        "en": ["example", "for example", "etc", "something", "maybe", "generally", "often", "sometimes", "usually"],
        "es": ["ejemplo", "por ejemplo", "etc", "algo", "tal vez", "generalmente", "a menudo", "a veces", "usualmente"]
    }
    
    # Phrases interdites qui indiquent des questions non pertinentes
    forbidden_phrases = {
        "fr": [
            "reformul", "reformulation", "pouvez-vous reformuler", "pourriez-vous reformuler",
            "expliquer différemment", "dire autrement", "autre façon", "manière différente"
        ],
        "en": [
            "rephras", "rephrase", "could you rephrase", "can you rephrase",
            "explain differently", "say differently", "another way", "different way"
        ],
        "es": [
            "reformul", "reformular", "puede reformular", "podría reformular",
            "explicar diferente", "decir diferente", "otra manera", "forma diferente"
        ]
    }
    
    words = question_words.get(language, question_words["fr"])
    generic_words = generic_keywords.get(language, generic_keywords["fr"])
    forbidden = forbidden_phrases.get(language, forbidden_phrases["fr"])
    
    validation_details = {
        "total_questions": len(questions),
        "length_failures": 0,
        "question_word_failures": 0,
        "generic_failures": 0,
        "forbidden_phrase_failures": 0,
        "length_limit_failures": 0,
        "duplicate_failures": 0
    }
    
    processed_questions = []
    
    for i, question in enumerate(questions):
        try:
            # ✅ CORRECTION: Conversion sécurisée en string
            if not isinstance(question, str):
                question = str(question) if question is not None else ""
            
            question = question.strip()
            
            # Test 1: Longueur minimale
            if len(question) < 15:
                validation["invalid_questions"].append(question)
                validation["issues"].append(f"Question trop courte: '{question}'")
                validation_details["length_failures"] += 1
                continue
            
            question_lower = question.lower()
            
            # Test 2: Vérifier si c'est une vraie question
            has_question_word = any(word in question_lower for word in words)
            has_question_mark = question.strip().endswith('?')
            
            if not has_question_word and not has_question_mark:
                validation["invalid_questions"].append(question)
                validation["issues"].append(f"Pas une question valide: '{question}'")
                validation_details["question_word_failures"] += 1
                continue
            
            # Test 3: Vérifier les phrases interdites (reformulation, etc.)
            has_forbidden = any(phrase in question_lower for phrase in forbidden)
            if has_forbidden:
                validation["invalid_questions"].append(question)
                validation["issues"].append(f"Question interdite (reformulation): '{question}'")
                validation_details["forbidden_phrase_failures"] += 1
                continue
            
            # Test 4: Vérifier si la question n'est pas trop générique
            generic_count = sum(1 for generic_word in generic_words if generic_word in question_lower)
            if generic_count >= 2:  # Plus souple: 2+ mots génériques = rejet
                validation["invalid_questions"].append(question)
                validation["issues"].append(f"Question trop générique: '{question}'")
                validation_details["generic_failures"] += 1
                continue
            
            # Test 5: Vérifier la longueur (pas trop longue)
            if len(question) > 200:
                validation["invalid_questions"].append(question)
                validation["issues"].append(f"Question trop longue: '{question[:50]}...'")
                validation_details["length_limit_failures"] += 1
                continue
            
            # Test 6: Éviter les doublons
            if question in processed_questions:
                validation["invalid_questions"].append(question)
                validation["issues"].append(f"Question en doublon: '{question}'")
                validation_details["duplicate_failures"] += 1
                continue
            
            # Nettoyer et formater la question valide
            if not question.endswith('?'):
                question += ' ?'
            
            validation["valid_questions"].append(question)
            processed_questions.append(question)
            
        except Exception as e:
            logger.error(f"❌ [Question Validation] Erreur lors de la validation de la question {i+1}: {e}")
            validation["invalid_questions"].append(str(question) if question else f"Question {i+1} invalide")
            validation["issues"].append(f"Erreur validation question {i+1}: {str(e)}")
    
    validation["validation_details"] = validation_details
    validation["filtered_count"] = len(validation["valid_questions"])
    
    # ✅ CORRECTION: Calcul de score de qualité plus robuste
    try:
        if questions:
            # Score de base
            base_score = len(validation["valid_questions"]) / len(questions)
            
            # Bonus pour diversité des questions
            if len(validation["valid_questions"]) > 1:
                # Vérifier que les questions ne commencent pas toutes de la même façon
                unique_starts = set()
                for q in validation["valid_questions"]:
                    words_in_q = q.split()
                    if len(words_in_q) >= 2:
                        first_words = " ".join(words_in_q[:2]).lower()
                        unique_starts.add(first_words)
                
                if len(validation["valid_questions"]) > 0:
                    diversity_bonus = len(unique_starts) / len(validation["valid_questions"]) * 0.2
                    base_score += diversity_bonus
            
            # Malus pour questions invalides
            if len(questions) > 0:
                invalid_penalty = len(validation["invalid_questions"]) / len(questions) * 0.3
                base_score -= invalid_penalty
            
            # Bonus pour questions spécifiques vs génériques
            if validation["valid_questions"]:
                specificity_bonus = 0
                for q in validation["valid_questions"]:
                    q_lower = q.lower()
                    # Bonus si mention d'éléments spécifiques
                    specific_words = ["race", "breed", "âge", "age", "jours", "days", "symptômes", "symptoms", 
                                    "raza", "cepa", "edad", "días", "síntomas"]
                    if any(word in q_lower for word in specific_words):
                        specificity_bonus += 0.1
                
                specificity_bonus = min(specificity_bonus, 0.2)  # Max 20% bonus
                base_score += specificity_bonus
            
            validation["quality_score"] = max(0.0, min(1.0, base_score))
        else:
            validation["quality_score"] = 0.0
            
    except Exception as e:
        logger.error(f"❌ [Question Validation] Erreur calcul score qualité: {e}")
        validation["quality_score"] = 0.0
    
    logger.info(f"🔧 [Question Validation] Score calculé: {validation['quality_score']:.2f}")
    logger.info(f"🔧 [Question Validation] Questions valides: {len(validation['valid_questions'])}/{len(questions)}")
    
    if validation["issues"]:
        logger.info(f"🔧 [Question Validation] Problèmes détectés: {validation['issues'][:3]}...")  # Log premier 3 problèmes
    
    return validation

def get_dynamic_clarification_fallback_questions(user_question: str, language: str = "fr") -> List[str]:
    """
    🆕 NOUVEAU: Retourne des questions de fallback intelligentes basées sur l'analyse de la question utilisateur
    
    Args:
        user_question: Question originale de l'utilisateur
        language: Langue des questions de fallback
        
    Returns:
        List[str]: Liste de questions de fallback (max 4)
    """
    
    # ✅ CORRECTION: Validation des paramètres d'entrée
    if not isinstance(user_question, str):
        user_question = str(user_question) if user_question else ""
    
    user_question_lower = user_question.lower()
    
    # ✅ CORRECTION: Validation de la langue avec fallback
    if not isinstance(language, str) or language.lower() not in ["en", "es", "fr"]:
        language = "fr"
        logger.warning(f"⚠️ [Fallback Questions] Langue invalide, fallback vers français")
    
    # Analyse basique du type de question pour fallback ciblé
    is_weight_question = any(word in user_question_lower for word in ["poids", "weight", "peso", "grammes", "grams"])
    is_health_question = any(word in user_question_lower for word in ["maladie", "disease", "enfermedad", "mort", "death", "muerte"])
    is_growth_question = any(word in user_question_lower for word in ["croissance", "growth", "crecimiento", "développement", "development"])
    is_feed_question = any(word in user_question_lower for word in ["alimentation", "feeding", "alimentación", "nourriture", "food"])
    
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
                "Quels symptômes spécifiques observez-vous ?",
                "Depuis combien de temps observez-vous ce problème ?"
            ],
            "growth": [
                "Quelle race ou souche spécifique élevez-vous ?",
                "Quel âge ont-ils actuellement en jours ?",
                "Quelles sont les conditions d'élevage actuelles ?"
            ],
            "feed": [
                "Quelle race ou souche élevez-vous ?",
                "Quel âge ont vos volailles ?",
                "Quel type d'alimentation utilisez-vous actuellement ?"
            ],
            "general": [
                "Pouvez-vous préciser la race ou souche de vos volailles ?",
                "Quel âge ont actuellement vos animaux ?",
                "Dans quel contexte d'élevage vous trouvez-vous ?",
                "Y a-t-il des symptômes ou problèmes spécifiques observés ?"
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
                "What specific symptoms are you observing?",
                "How long have you been observing this problem?"
            ],
            "growth": [
                "What specific breed or strain are you raising?",
                "What is their current age in days?",
                "What are the current housing conditions?"
            ],
            "feed": [
                "What breed or strain are you raising?",
                "What age are your poultry?",
                "What type of feed are you currently using?"
            ],
            "general": [
                "Could you specify the breed or strain of your poultry?",
                "What age are your animals currently?",
                "What farming context are you in?",
                "Are there any specific symptoms or problems observed?"
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
                "¿Qué síntomas específicos está observando?",
                "¿Desde cuándo observa este problema?"
            ],
            "growth": [
                "¿Qué raza o cepa específica está criando?",
                "¿Cuál es su edad actual en días?",
                "¿Cuáles son las condiciones actuales de alojamiento?"
            ],
            "feed": [
                "¿Qué raza o cepa está criando?",
                "¿Qué edad tienen sus aves?",
                "¿Qué tipo de alimentación está usando actualmente?"
            ],
            "general": [
                "¿Podría especificar la raza o cepa de sus aves?",
                "¿Qué edad tienen actualmente sus animales?",
                "¿En qué contexto de cría se encuentra?",
                "¿Hay algún síntoma o problema específico observado?"
            ]
        }
    }
    
    try:
        lang_questions = fallback_questions.get(language, fallback_questions["fr"])
        
        # Sélectionner le type de questions le plus approprié
        if is_weight_question:
            selected_questions = lang_questions["weight"]
        elif is_health_question:
            selected_questions = lang_questions["health"]
        elif is_growth_question:
            selected_questions = lang_questions["growth"]
        elif is_feed_question:
            selected_questions = lang_questions["feed"]
        else:
            selected_questions = lang_questions["general"]
        
        # ✅ CORRECTION: S'assurer que nous retournons toujours une liste valide
        if not selected_questions:
            selected_questions = lang_questions["general"]
        
        result = selected_questions[:4]  # Max 4 questions
        
        logger.info(f"🔄 [Fallback Questions] Type détecté pour '{user_question[:30]}...': {result[0][:30] if result else 'Aucune'}...")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [Fallback Questions] Erreur génération questions: {e}")
        # Retour de sécurité
        default_questions = {
            "fr": ["Pouvez-vous préciser votre question ?", "Quel type d'élevage avez-vous ?"],
            "en": ["Could you be more specific?", "What type of farming do you have?"],
            "es": ["¿Podría ser más específico?", "¿Qué tipo de cría tiene?"]
        }
        return default_questions.get(language, default_questions["fr"])

# =============================================================================
# UTILITAIRES POUR EXTRACTION CONTEXTE (CONSERVÉS AVEC CORRECTIONS)
# =============================================================================

def extract_context_from_entities(extracted_entities: Dict[str, Any]) -> Dict[str, str]:
    """
    🔍 EXTRACTION - Extrait le contexte depuis les entités pour le prompt
    
    Args:
        extracted_entities: Dictionnaire d'entités extraites
        
    Returns:
        Dict[str, str]: Contexte formaté pour le prompt
    """
    
    context = {
        "breed": "non spécifiée",
        "sex": "non spécifié", 
        "age": "non spécifié",
        "lang": "fr"
    }
    
    # ✅ CORRECTION: Validation robuste des entités d'entrée
    if not extracted_entities or not isinstance(extracted_entities, dict):
        logger.warning("⚠️ [Context Extraction] Entités manquantes ou invalides")
        return context
    
    try:
        # Breed/Race
        if "breed" in extracted_entities and extracted_entities["breed"]:
            breed_value = extracted_entities["breed"]
            if breed_value and str(breed_value).strip():
                context["breed"] = str(breed_value).strip()
        
        # Sex/Sexe  
        if "sex" in extracted_entities and extracted_entities["sex"]:
            sex_value = extracted_entities["sex"]
            if sex_value and str(sex_value).strip():
                context["sex"] = str(sex_value).strip()
        
        # Age/Âge - multiple formats possibles
        age_candidates = ["age", "days", "weeks", "jours", "semaines"]
        for candidate in age_candidates:
            if candidate in extracted_entities and extracted_entities[candidate]:
                age_value = extracted_entities[candidate]
                try:
                    if isinstance(age_value, (int, float)) and age_value > 0:
                        if candidate in ["weeks", "semaines"]:
                            context["age"] = f"{age_value} semaine{'s' if age_value > 1 else ''}"
                        else:
                            context["age"] = f"{age_value} jour{'s' if age_value > 1 else ''}"
                    elif age_value and str(age_value).strip():
                        context["age"] = str(age_value).strip()
                    break
                except (TypeError, ValueError) as e:
                    logger.warning(f"⚠️ [Context Extraction] Erreur conversion âge {age_value}: {e}")
                    continue
        
        # Langue
        if "language" in extracted_entities and extracted_entities["language"]:
            lang_value = extracted_entities["language"]
            if lang_value and str(lang_value).strip().lower() in ["fr", "en", "es"]:
                context["lang"] = str(lang_value).strip().lower()
        
    except Exception as e:
        logger.error(f"❌ [Context Extraction] Erreur extraction contexte: {e}")
        # Retourner le contexte par défaut en cas d'erreur
    
    logger.info(f"🔍 [Prompt Context] Contexte extrait: {context}")
    
    return context

def validate_prompt_context(context: Dict[str, str]) -> Dict[str, Any]:
    """
    ✅ VALIDATION - Valide et nettoie le contexte pour le prompt
    
    Args:
        context: Contexte à valider
        
    Returns:
        Dict[str, Any]: Résultat de validation avec score et détails
    """
    
    validation_result = {
        "is_valid": True,
        "completeness_score": 0.0,
        "missing_elements": [],
        "warnings": []
    }
    
    # ✅ CORRECTION: Validation du contexte d'entrée
    if not isinstance(context, dict):
        validation_result["is_valid"] = False
        validation_result["warnings"].append("Contexte invalide - doit être un dictionnaire")
        return validation_result
    
    try:
        # Vérifier chaque élément
        elements_score = 0
        total_elements = 4  # breed, sex, age, lang
        
        # Breed
        breed = context.get("breed", "")
        if breed and isinstance(breed, str) and breed.strip() and breed != "non spécifiée":
            elements_score += 1
        else:
            validation_result["missing_elements"].append("breed")
        
        # Sex
        sex = context.get("sex", "")
        if sex and isinstance(sex, str) and sex.strip() and sex != "non spécifié":
            elements_score += 1
        else:
            validation_result["missing_elements"].append("sex")
        
        # Age
        age = context.get("age", "")
        if age and isinstance(age, str) and age.strip() and age != "non spécifié":
            elements_score += 1
        else:
            validation_result["missing_elements"].append("age")
        
        # Language
        lang = context.get("lang", "")
        if lang and isinstance(lang, str) and lang.strip() and lang in ["fr", "en", "es"]:
            elements_score += 1
        else:
            # Language est moins critique, donc pas forcément manquant
            pass
        
        validation_result["completeness_score"] = elements_score / total_elements
        
        # Warnings pour contexte incomplet
        if validation_result["completeness_score"] < 0.5:
            validation_result["warnings"].append("Contexte très incomplet - clarification recommandée")
        elif validation_result["completeness_score"] < 0.75:
            validation_result["warnings"].append("Contexte partiellement incomplet")
        
    except Exception as e:
        logger.error(f"❌ [Prompt Validation] Erreur validation contexte: {e}")
        validation_result["is_valid"] = False
        validation_result["warnings"].append(f"Erreur validation: {str(e)}")
    
    logger.info(f"✅ [Prompt Validation] Score: {validation_result['completeness_score']:.1%}, Manque: {validation_result['missing_elements']}")
    
    return validation_result

# =============================================================================
# 🆕 NOUVELLE FONCTION: PARSING ROBUSTE DES RÉPONSES JSON
# =============================================================================

def parse_gpt_json_response(response_text: str) -> Dict[str, Any]:
    """
    🆕 NOUVEAU: Parse robuste des réponses JSON de GPT avec fallback intelligent
    
    Args:
        response_text: Réponse brute de GPT
        
    Returns:
        Dict[str, Any]: Données parsées ou structure par défaut
    """
    
    result = {
        "clarification_questions": [],
        "parsing_success": False,
        "raw_response": response_text,
        "error": None
    }
    
    if not response_text or not isinstance(response_text, str):
        result["error"] = "Réponse vide ou invalide"
        return result
    
    try:
        # Nettoyer la réponse (enlever markdown et espaces)
        cleaned_response = response_text.strip()
        
        # Enlever les balises markdown si présentes
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        
        cleaned_response = cleaned_response.strip()
        
        # Essayer de parser le JSON
        parsed_data = json.loads(cleaned_response)
        
        if isinstance(parsed_data, dict) and "clarification_questions" in parsed_data:
            questions = parsed_data["clarification_questions"]
            if isinstance(questions, list):
                result["clarification_questions"] = questions
                result["parsing_success"] = True
                logger.info(f"✅ [JSON Parse] Parsing réussi: {len(questions)} questions extraites")
            else:
                result["error"] = "clarification_questions n'est pas une liste"
        else:
            result["error"] = "Structure JSON invalide - clé 'clarification_questions' manquante"
            
    except json.JSONDecodeError as e:
        result["error"] = f"Erreur parsing JSON: {str(e)}"
        logger.warning(f"⚠️ [JSON Parse] Échec parsing JSON: {e}")
        
        # Tentative de récupération avec regex
        try:
            # Chercher des questions avec regex comme fallback
            question_pattern = r'"([^"]*\?[^"]*)"'
            found_questions = re.findall(question_pattern, response_text)
            
            if found_questions:
                result["clarification_questions"] = found_questions[:4]  # Max 4
                result["parsing_success"] = True
                logger.info(f"🔄 [JSON Parse] Récupération par regex: {len(found_questions)} questions")
            
        except Exception as regex_error:
            logger.error(f"❌ [JSON Parse] Échec récupération regex: {regex_error}")
    
    except Exception as e:
        result["error"] = f"Erreur inattendue: {str(e)}"
        logger.error(f"❌ [JSON Parse] Erreur parsing: {e}")
    
    return result

# =============================================================================
# CONFIGURATION ET LOGGING
# =============================================================================

logger.info("✅ [Prompt Templates] Templates de prompts structurés chargés avec validation robuste - VERSION CORRIGÉE")
logger.info("🎯 [Prompt Templates] Fonctionnalités disponibles:")
logger.info("   - 🇫🇷 Prompts français optimisés")
logger.info("   - 🇬🇧 Prompts anglais optimisés") 
logger.info("   - 🇪🇸 Prompts espagnols optimisés")
logger.info("   - 🎯 Prompts pour questions floues")
logger.info("   - 🔍 Extraction contexte depuis entités")
logger.info("   - ✅ Validation qualité contexte")
logger.info("🆕 [Prompt Templates] FONCTIONNALITÉ MODE SÉMANTIQUE:")
logger.info("   - 🎭 Prompt de contextualisation pour mode sémantique dynamique")
logger.info("   - 🤖 Génération intelligente de questions via GPT")
logger.info("   - 🌐 Support multilingue pour questions dynamiques")
logger.info("   - 📝 Questions de fallback intelligentes par type")
logger.info("🔧 [Prompt Templates] VALIDATION ROBUSTE:")
logger.info("   - ✅ Validation complète des questions générées (validate_dynamic_questions)")
logger.info("   - 🎯 Filtrage avancé: longueur, mots-clés, phrases interdites")
logger.info("   - 📊 Score de qualité détaillé (0.0 à 1.0)")
logger.info("   - 🚫 Détection reformulations et questions génériques")
logger.info("   - 🔍 Bonus diversité et spécificité")
logger.info("   - 📋 Logs détaillés des échecs de validation")
logger.info("   - 🔄 Fallback intelligent par type de question")
logger.info("🆕 [Prompt Templates] PARSING JSON ROBUSTE:")
logger.info("   - 🔧 Parsing robuste des réponses GPT avec fallback regex")
logger.info("   - ⚡ Nettoyage automatique des balises markdown")
logger.info("   - 🛡️ Gestion d'erreurs complète avec récupération")
logger.info("🔧 [Prompt Templates] CORRECTIONS APPLIQUÉES:")
logger.info("   - ✅ Import json ajouté pour parsing JSON")
logger.info("   - ✅ Validation robuste des paramètres d'entrée")
logger.info("   - ✅ Gestion d'exceptions complète")
logger.info("   - ✅ Fallback intelligent en cas d'erreur")
logger.info("   - ✅ Validation des types avec conversion sécurisée")
logger.info("   - ✅ Documentation des types de retour améliorée")
logger.info("🧹 [Prompt Templates] OBJECTIF: Éliminer références aux documents")
logger.info("✨ [Prompt Templates] RÉSULTAT: Réponses naturelles et professionnelles + validation robuste")
logger.info("🔧 [Prompt Templates] NOUVEAU: Message utilisateur neutre centralisé")
logger.info("✅ [Prompt Templates] STATUT: Version corrigée et sécurisée")