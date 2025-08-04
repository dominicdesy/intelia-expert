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
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple

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
    """
    
    # Extraire les éléments du contexte
    breed = context.get("breed", "non spécifiée")
    sex = context.get("sex", "non spécifié") 
    age = context.get("age", "non spécifié")
    language = context.get("lang", "fr")
    
    # Templates par langue
    if language.lower() == "en":
        return _build_english_prompt(documents, question, breed, sex, age)
    elif language.lower() == "es":
        return _build_spanish_prompt(documents, question, breed, sex, age)
    else:
        return _build_french_prompt(documents, question, breed, sex, age)

def _build_french_prompt(documents: str, question: str, breed: str, sex: str, age: str) -> str:
    """Template français optimisé"""
    
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
    """Template anglais optimisé"""
    
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
    """Template espagnol optimisé"""
    
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
        Prompt structuré pour GPT
    """
    
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

def build_vagueness_prompt(vague_question: str, suggestions: list, language: str = "fr") -> str:
    """
    🎯 PROMPT VAGUENESS - Pour les questions trop floues
    """
    
    suggestions_text = "\n".join([f"• {s}" for s in suggestions])
    
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
        Dict avec résultats de validation incluant quality_score
    """
    
    validation = {
        "valid_questions": [],
        "invalid_questions": [],
        "quality_score": 0.0,
        "issues": [],
        "filtered_count": 0,
        "validation_details": {}
    }
    
    if not questions or not isinstance(questions, list):
        validation["quality_score"] = 0.0
        validation["issues"].append("Aucune question fournie ou format incorrect")
        return validation
    
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
        if not isinstance(question, str):
            validation["invalid_questions"].append(f"Question {i+1}: Not a string")
            validation["issues"].append(f"Question {i+1} n'est pas une chaîne de caractères")
            continue
        
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
    
    validation["validation_details"] = validation_details
    validation["filtered_count"] = len(validation["valid_questions"])
    
    # Calculer score de qualité amélioré
    if questions:
        # Score de base
        base_score = len(validation["valid_questions"]) / len(questions)
        
        # Bonus pour diversité des questions
        if len(validation["valid_questions"]) > 1:
            # Vérifier que les questions ne commencent pas toutes de la même façon
            unique_starts = set()
            for q in validation["valid_questions"]:
                first_words = " ".join(q.split()[:2]).lower()
                unique_starts.add(first_words)
            
            diversity_bonus = len(unique_starts) / len(validation["valid_questions"]) * 0.2
            base_score += diversity_bonus
        
        # Malus pour questions invalides
        invalid_penalty = len(validation["invalid_questions"]) / len(questions) * 0.3
        base_score -= invalid_penalty
        
        # Bonus pour questions spécifiques vs génériques
        if validation["valid_questions"]:
            specificity_bonus = 0
            for q in validation["valid_questions"]:
                q_lower = q.lower()
                # Bonus si mention d'éléments spécifiques
                if any(word in q_lower for word in ["race", "breed", "âge", "age", "jours", "days", "symptômes", "symptoms"]):
                    specificity_bonus += 0.1
            
            specificity_bonus = min(specificity_bonus, 0.2)  # Max 20% bonus
            base_score += specificity_bonus
        
        validation["quality_score"] = max(0.0, min(1.0, base_score))
    
    logger.info(f"🔧 [Question Validation] Score calculé: {validation['quality_score']:.2f}")
    logger.info(f"🔧 [Question Validation] Questions valides: {len(validation['valid_questions'])}/{len(questions)}")
    
    if validation["issues"]:
        logger.info(f"🔧 [Question Validation] Problèmes détectés: {validation['issues'][:3]}...")  # Log premier 3 problèmes
    
    return validation

def get_dynamic_clarification_fallback_questions(user_question: str, language: str = "fr") -> List[str]:
    """
    🆕 NOUVEAU: Retourne des questions de fallback intelligentes basées sur l'analyse de la question utilisateur
    """
    
    user_question_lower = user_question.lower() if user_question else ""
    
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
    
    logger.info(f"🔄 [Fallback Questions] Type détecté pour '{user_question[:30]}...': {selected_questions[0][:30]}...")
    
    return selected_questions[:4]  # Max 4 questions

# =============================================================================
# UTILITAIRES POUR EXTRACTION CONTEXTE (CONSERVÉS)
# =============================================================================

def extract_context_from_entities(extracted_entities: Dict[str, Any]) -> Dict[str, str]:
    """
    🔍 EXTRACTION - Extrait le contexte depuis les entités pour le prompt
    """
    
    context = {
        "breed": "non spécifiée",
        "sex": "non spécifié", 
        "age": "non spécifié",
        "lang": "fr"
    }
    
    if not extracted_entities:
        return context
    
    # Breed/Race
    if "breed" in extracted_entities and extracted_entities["breed"]:
        context["breed"] = str(extracted_entities["breed"]).strip()
    
    # Sex/Sexe  
    if "sex" in extracted_entities and extracted_entities["sex"]:
        context["sex"] = str(extracted_entities["sex"]).strip()
    
    # Age/Âge - multiple formats possibles
    age_candidates = ["age", "days", "weeks", "jours", "semaines"]
    for candidate in age_candidates:
        if candidate in extracted_entities and extracted_entities[candidate]:
            age_value = extracted_entities[candidate]
            if isinstance(age_value, (int, float)):
                if candidate in ["weeks", "semaines"]:
                    context["age"] = f"{age_value} semaine{'s' if age_value > 1 else ''}"
                else:
                    context["age"] = f"{age_value} jour{'s' if age_value > 1 else ''}"
            else:
                context["age"] = str(age_value).strip()
            break
    
    # Langue
    if "language" in extracted_entities and extracted_entities["language"]:
        context["lang"] = str(extracted_entities["language"]).strip()
    
    logger.info(f"🔍 [Prompt Context] Contexte extrait: {context}")
    
    return context

def validate_prompt_context(context: Dict[str, str]) -> Dict[str, Any]:
    """
    ✅ VALIDATION - Valide et nettoie le contexte pour le prompt
    """
    
    validation_result = {
        "is_valid": True,
        "completeness_score": 0.0,
        "missing_elements": [],
        "warnings": []
    }
    
    # Vérifier chaque élément
    elements_score = 0
    total_elements = 4  # breed, sex, age, lang
    
    if context.get("breed") and context["breed"] != "non spécifiée":
        elements_score += 1
    else:
        validation_result["missing_elements"].append("breed")
    
    if context.get("sex") and context["sex"] != "non spécifié":
        elements_score += 1
    else:
        validation_result["missing_elements"].append("sex")
    
    if context.get("age") and context["age"] != "non spécifié":
        elements_score += 1
    else:
        validation_result["missing_elements"].append("age")
    
    if context.get("lang"):
        elements_score += 1
    
    validation_result["completeness_score"] = elements_score / total_elements
    
    # Warnings pour contexte incomplet
    if validation_result["completeness_score"] < 0.5:
        validation_result["warnings"].append("Contexte très incomplet - clarification recommandée")
    elif validation_result["completeness_score"] < 0.75:
        validation_result["warnings"].append("Contexte partiellement incomplet")
    
    logger.info(f"✅ [Prompt Validation] Score: {validation_result['completeness_score']:.1%}, Manque: {validation_result['missing_elements']}")
    
    return validation_result

# =============================================================================
# CONFIGURATION ET LOGGING
# =============================================================================

logger.info("✅ [Prompt Templates] Templates de prompts structurés chargés avec validation robuste")
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
logger.info("🔧 [Prompt Templates] NOUVELLE FONCTIONNALITÉ VALIDATION ROBUSTE:")
logger.info("   - ✅ Validation complète des questions générées (validate_dynamic_questions)")
logger.info("   - 🎯 Filtrage avancé: longueur, mots-clés, phrases interdites")
logger.info("   - 📊 Score de qualité détaillé (0.0 à 1.0)")
logger.info("   - 🚫 Détection reformulations et questions génériques")
logger.info("   - 🔍 Bonus diversité et spécificité")
logger.info("   - 📋 Logs détaillés des échecs de validation")
logger.info("   - 🔄 Fallback intelligent par type de question (poids/santé/croissance/alimentation)")
logger.info("🧹 [Prompt Templates] OBJECTIF: Éliminer références aux documents")
logger.info("✨ [Prompt Templates] RÉSULTAT: Réponses naturelles et professionnelles + questions validées robustement")
logger.info("🔧 [Prompt Templates] AMÉLIORATION: Validation complète avec fallback intelligent")
logger.info("🔧 [Prompt Templates] NOUVEAU: Message utilisateur neutre centralisé")
logger.info("✅ [Prompt Templates] Action 1: USER_NEEDS_CLARIFICATION_MSG centralisé")
logger.info("✅ [Prompt Templates] Action 3: Seule build_contextualization_prompt génère des questions")