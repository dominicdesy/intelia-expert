"""
app/api/v1/prompt_templates.py - TEMPLATES DE PROMPTS STRUCTURÉS AVEC VALIDATION

🎯 OBJECTIF: Centraliser et standardiser les prompts pour le système RAG
🔧 AMÉLIORATION: Éliminer les références aux documents dans les réponses
✨ QUALITÉ: Réponses plus naturelles et professionnelles
🆕 NOUVEAU: Prompt de contextualisation pour mode sémantique dynamique
🔧 NOUVEAU: Validation des questions générées dynamiquement
🐛 FIX: Ajout import List manquant (CORRIGÉ)
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

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

# 🆕 NOUVEAU: Prompt de contextualisation pour mode sémantique dynamique (MODIFIÉ)
def build_contextualization_prompt(user_question: str, language: str = "fr") -> str:
    """
    🆕 NOUVEAU: Construit un prompt pour générer des questions de clarification dynamiques.
    🔧 MODIFIÉ: Prompt optimisé pour éviter les exemples génériques non pertinents
    
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

Do not propose generic examples.
Do not reformulate the question.
Do not answer the question.
Do not mention breeds or species that are not already cited by the user.

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

No propongas ejemplos genéricos.
No reformules la pregunta.
No respondas la pregunta.
No menciones razas o especies que no hayan sido ya citadas por el usuario.

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

Ne propose pas d'exemples génériques.
Ne reformule pas la question.
Ne réponds pas à la question.
Ne mentionne pas de races ou d'espèces qui ne sont pas déjà citées par l'utilisateur.

Réponds dans ce format JSON :
{{
  "clarification_questions": [
    "Question 1",
    "Question 2",
    "Question 3"
  ]
}}"""

def build_clarification_prompt(missing_info: list, detected_age: str, language: str = "fr") -> str:
    """
    🎪 PROMPT CLARIFICATION - Pour les demandes de clarification spécialisées
    """
    
    if language.lower() == "en":
        return _build_clarification_english(missing_info, detected_age)
    elif language.lower() == "es":
        return _build_clarification_spanish(missing_info, detected_age)
    else:
        return _build_clarification_french(missing_info, detected_age)

def _build_clarification_french(missing_info: list, detected_age: str) -> str:
    """Clarification française"""
    
    missing_text = ", ".join(missing_info)
    
    return f"""Pour vous donner le poids de référence exact d'un poulet de {detected_age} jours, j'ai besoin de préciser :

• **{missing_text}**

Ces informations sont essentielles car les performances varient significativement selon :
- La race/souche (Ross 308, Cobb 500, Hubbard, etc.)
- Le sexe (mâles plus lourds, femelles différents besoins)

**Exemples de réponses complètes :**
• "Ross 308 mâles"
• "Cobb 500 femelles" 
• "Hubbard troupeau mixte"

💡 Répondez simplement avec ces informations pour obtenir les données précises."""

def _build_clarification_english(missing_info: list, detected_age: str) -> str:
    """Clarification anglaise"""
    
    missing_text = ", ".join(missing_info)
    
    return f"""To give you the exact reference weight for a {detected_age}-day chicken, I need to clarify:

• **{missing_text}**

This information is essential because performance varies significantly based on:
- Breed/strain (Ross 308, Cobb 500, Hubbard, etc.)
- Sex (males heavier, females different requirements)

**Examples of complete responses:**
• "Ross 308 males"
• "Cobb 500 females"
• "Hubbard mixed flock"

💡 Simply respond with this information to get precise data."""

def _build_clarification_spanish(missing_info: list, detected_age: str) -> str:
    """Clarification espagnole"""
    
    missing_text = ", ".join(missing_info)
    
    return f"""Para darle el peso de referencia exacto de un pollo de {detected_age} días, necesito aclarar:

• **{missing_text}**

Esta información es esencial porque el rendimiento varía significativamente según:
- Raza/cepa (Ross 308, Cobb 500, Hubbard, etc.)
- Sexo (machos más pesados, hembras diferentes requerimientos)

**Ejemplos de respuestas completas:**
• "Ross 308 machos"
• "Cobb 500 hembras"
• "Hubbard lote mixto"

💡 Responda simplemente con esta información para obtener datos precisos."""

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
# UTILITAIRES POUR EXTRACTION CONTEXTE
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
# 🔧 NOUVELLES FONCTIONS POUR VALIDATION QUESTIONS DYNAMIQUES
# =============================================================================

def validate_dynamic_questions(questions: List[str], language: str = "fr") -> Dict[str, Any]:
    """
    🔧 NOUVEAU: Valide la qualité des questions générées dynamiquement
    
    Args:
        questions: Liste des questions à valider
        language: Langue des questions (fr/en/es)
        
    Returns:
        Dict avec résultats de validation incluant quality_score
    """
    
    validation = {
        "valid_questions": [],
        "invalid_questions": [],
        "quality_score": 0.0,
        "issues": []
    }
    
    if not questions:
        validation["quality_score"] = 0.0
        validation["issues"].append("Aucune question fournie")
        return validation
    
    # Mots-clés de questions par langue
    question_words = {
        "fr": ["quel", "quelle", "combien", "comment", "où", "quand", "pourquoi", "dans quel", "depuis quand"],
        "en": ["what", "which", "how", "where", "when", "why", "who", "how long", "what type"],
        "es": ["qué", "cuál", "cómo", "dónde", "cuándo", "por qué", "quién", "cuánto tiempo", "qué tipo"]
    }
    
    # Mots-clés génériques à éviter (indiquent des questions trop vagues)
    generic_keywords = {
        "fr": ["exemple", "par exemple", "etc", "quelque chose", "peut-être", "généralement"],
        "en": ["example", "for example", "etc", "something", "maybe", "generally"],
        "es": ["ejemplo", "por ejemplo", "etc", "algo", "tal vez", "generalmente"]
    }
    
    words = question_words.get(language, question_words["fr"])
    generic_words = generic_keywords.get(language, generic_keywords["fr"])
    
    for question in questions:
        if not question or len(question.strip()) < 10:
            validation["invalid_questions"].append(question)
            validation["issues"].append(f"Question trop courte: '{question}'")
            continue
        
        question_lower = question.lower().strip()
        
        # Vérifier si c'est une vraie question
        has_question_word = any(word in question_lower for word in words)
        has_question_mark = question.strip().endswith('?')
        
        if not has_question_word and not has_question_mark:
            validation["invalid_questions"].append(question)
            validation["issues"].append(f"Pas une question valide: '{question}'")
            continue
        
        # Vérifier si la question n'est pas trop générique
        is_generic = any(generic_word in question_lower for generic_word in generic_words)
        if is_generic:
            validation["invalid_questions"].append(question)
            validation["issues"].append(f"Question trop générique: '{question}'")
            continue
        
        # Vérifier la longueur (pas trop courte, pas trop longue)
        if len(question) < 20:
            validation["invalid_questions"].append(question)
            validation["issues"].append(f"Question manque de contexte: '{question}'")
            continue
        
        if len(question) > 150:
            validation["invalid_questions"].append(question)
            validation["issues"].append(f"Question trop longue: '{question[:50]}...'")
            continue
        
        # Si toutes les validations passent
        validation["valid_questions"].append(question)
    
    # Calculer score de qualité
    if questions:
        base_score = len(validation["valid_questions"]) / len(questions)
        
        # Bonus pour diversité des questions
        if len(validation["valid_questions"]) > 1:
            # Vérifier que les questions ne sont pas trop similaires
            unique_starts = set()
            for q in validation["valid_questions"]:
                first_words = " ".join(q.split()[:3]).lower()
                unique_starts.add(first_words)
            
            diversity_bonus = len(unique_starts) / len(validation["valid_questions"]) * 0.2
            base_score += diversity_bonus
        
        # Malus pour questions invalides
        invalid_penalty = len(validation["invalid_questions"]) / len(questions) * 0.3
        base_score -= invalid_penalty
        
        validation["quality_score"] = max(0.0, min(1.0, base_score))
    
    logger.info(f"🔧 [Question Validation] Score calculé: {validation['quality_score']:.2f}")
    logger.info(f"🔧 [Question Validation] Questions valides: {len(validation['valid_questions'])}/{len(questions)}")
    
    return validation

def get_dynamic_clarification_examples(language: str = "fr") -> List[str]:
    """
    🆕 NOUVEAU: Retourne des exemples de questions dynamiques par langue
    """
    
    examples = {
        "fr": [
            "Quelle race ou souche spécifique élevez-vous ?",
            "Quel âge ont actuellement vos volailles ?",
            "Quels symptômes ou problèmes observez-vous ?",
            "Quelle est votre configuration d'élevage ?",
            "Quel type d'alimentation utilisez-vous ?",
            "Combien d'animaux avez-vous dans votre troupeau ?",
            "Depuis combien de temps observez-vous ce problème ?",
            "Quelles sont les conditions environnementales actuelles ?"
        ],
        "en": [
            "What specific breed or strain are you raising?",
            "What age are your birds currently?",
            "What symptoms or issues are you observing?",
            "What is your housing setup?",
            "What type of feed are you using?",
            "How many animals do you have in your flock?",
            "How long have you been observing this problem?",
            "What are the current environmental conditions?"
        ],
        "es": [
            "¿Qué raza o cepa específica está criando?",
            "¿Qué edad tienen actualmente sus aves?",
            "¿Qué síntomas o problemas está observando?",
            "¿Cuál es su configuración de alojamiento?",
            "¿Qué tipo de alimentación está usando?",
            "¿Cuántos animales tiene en su lote?",
            "¿Desde cuándo está observando este problema?",
            "¿Cuáles son las condiciones ambientales actuales?"
        ]
    }
    
    return examples.get(language, examples["fr"])

# =============================================================================
# CONFIGURATION ET LOGGING
# =============================================================================

logger.info("✅ [Prompt Templates] Templates de prompts structurés chargés avec validation")
logger.info("🎯 [Prompt Templates] Fonctionnalités disponibles:")
logger.info("   - 🇫🇷 Prompts français optimisés")
logger.info("   - 🇬🇧 Prompts anglais optimisés") 
logger.info("   - 🇪🇸 Prompts espagnols optimisés")
logger.info("   - 🎪 Prompts de clarification spécialisés")
logger.info("   - 🎯 Prompts pour questions floues")
logger.info("   - 🔍 Extraction contexte depuis entités")
logger.info("   - ✅ Validation qualité contexte")
logger.info("🆕 [Prompt Templates] FONCTIONNALITÉ MODE SÉMANTIQUE:")
logger.info("   - 🎭 Prompt de contextualisation pour mode sémantique dynamique")
logger.info("   - 🤖 Génération intelligente de questions via GPT")
logger.info("   - 🌐 Support multilingue pour questions dynamiques")
logger.info("   - 📝 Exemples de questions par langue")
logger.info("🔧 [Prompt Templates] NOUVELLE FONCTIONNALITÉ VALIDATION:")
logger.info("   - ✅ Validation qualité questions générées (validate_dynamic_questions)")
logger.info("   - 📊 Score de qualité (0.0 à 1.0)")
logger.info("   - 🎯 Filtrage questions génériques/trop courtes/trop longues")
logger.info("   - 🔍 Vérification mots-clés question par langue")
logger.info("   - 📈 Bonus diversité + malus répétition")
logger.info("   - 📝 Logs détaillés résultats validation")
logger.info("🧹 [Prompt Templates] OBJECTIF: Éliminer références aux documents")
logger.info("✨ [Prompt Templates] RÉSULTAT: Réponses naturelles et professionnelles + questions validées")
logger.info("🐛 [Prompt Templates] FIX: Import List ajouté - erreur corrigée!")
logger.info("🔧 [Prompt Templates] AMÉLIORATION: Prompt contextualisation optimisé pour éviter exemples génériques")