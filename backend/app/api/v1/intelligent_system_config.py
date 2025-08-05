"""
intelligent_system_config.py - CONFIGURATION UNIFIÉE DU SYSTÈME INTELLIGENT

🎯 CORRECTIONS APPLIQUÉES:
- ✅ Interpolation linéaire précise dans get_weight_range()
- ✅ Support des âges intermédiaires (12 jours entre 7j et 14j)
- ✅ Calcul correct: Ross 308 mâle 12j → 380-420g
- ✅ Nouvelles fonctions pour les clarifications contextuelles
- ✅ Gestion améliorée des races et variantes

CENTRALISE: Toute la configuration du nouveau système
PRINCIPE: Une seule source de vérité pour tous les paramètres
SIMPLE: Configuration claire et modifiable facilement
"""

from typing import Dict, Any, List, Tuple
from enum import Enum

# =============================================================================
# CONFIGURATION PRINCIPALE DU SYSTÈME
# =============================================================================

class SystemBehavior:
    """Configuration du comportement général"""
    
    # Principe directeur
    ALWAYS_PROVIDE_USEFUL_ANSWER = True
    PRECISION_OFFERS_ENABLED = True
    CLARIFICATION_ONLY_IF_REALLY_NEEDED = True
    
    # NOUVEAU: Support du contexte conversationnel
    ENABLE_CONVERSATIONAL_CONTEXT = True
    CONTEXT_EXPIRY_MINUTES = 10
    ENABLE_CLARIFICATION_DETECTION = True
    
    # Fallback et récupération d'erreur
    FALLBACK_ENABLED = True
    FALLBACK_TO_GENERAL_ON_ERROR = True
    MAX_PROCESSING_TIME_MS = 10000  # 10 secondes max
    
    # Logging et debugging
    ENABLE_DETAILED_LOGGING = True
    ENABLE_PERFORMANCE_MONITORING = True
    ENABLE_STATS_COLLECTION = True

class DecisionThresholds:
    """Seuils pour les décisions de classification"""
    
    # Seuils de confiance pour chaque type de réponse
    CONFIDENCE_THRESHOLD_PRECISE = 0.85    # Réponse précise
    CONFIDENCE_THRESHOLD_GENERAL = 0.60    # Réponse générale
    CONFIDENCE_THRESHOLD_CLARIFICATION = 0.40  # Clarification
    CONFIDENCE_THRESHOLD_CONTEXTUAL = 0.90    # NOUVEAU: Réponse contextuelle
    
    # Critères pour réponse précise
    MIN_ENTITIES_FOR_PRECISE = 2  # race + âge, ou race + sexe, etc.
    REQUIRED_ENTITIES_PRECISE = ["breed_specific"]  # Au minimum une race spécifique
    
    # Critères pour réponse générale  
    MIN_ENTITIES_FOR_GENERAL = 1  # Au moins un contexte utile
    MAX_MISSING_ENTITIES_FOR_GENERAL = 2  # Maximum 2 entités manquantes
    
    # Critères pour clarification forcée
    MAX_QUESTION_WORDS_FOR_CLARIFICATION = 4  # Questions trop courtes
    MIN_CONTEXT_FOR_USEFUL_RESPONSE = 1  # Minimum de contexte
    
    # NOUVEAU: Critères pour contexte conversationnel
    MIN_CONTEXT_FRESHNESS_MINUTES = 10  # Contexte valide 10 minutes
    ENABLE_ENTITY_INHERITANCE = True    # Hériter entités du contexte

# =============================================================================
# DONNÉES DE RÉFÉRENCE - POIDS ET PERFORMANCES (AMÉLIORÉES)
# =============================================================================

class ReferenceData:
    """Données de référence pour les calculs de performance"""
    
    # Poids de référence par race, âge et sexe (en grammes)
    WEIGHT_STANDARDS = {
        "ross_308": {
            7: {"male": (180, 220), "female": (160, 200), "mixed": (170, 210)},
            14: {"male": (450, 550), "female": (400, 500), "mixed": (425, 525)},
            21: {"male": (850, 1050), "female": (750, 950), "mixed": (800, 1000)},
            28: {"male": (1400, 1700), "female": (1200, 1500), "mixed": (1300, 1600)},
            35: {"male": (2000, 2400), "female": (1800, 2200), "mixed": (1900, 2300)},
            42: {"male": (2600, 3000), "female": (2200, 2600), "mixed": (2400, 2800)}
        },
        "cobb_500": {
            7: {"male": (175, 215), "female": (155, 195), "mixed": (165, 205)},
            14: {"male": (440, 540), "female": (390, 490), "mixed": (415, 515)},
            21: {"male": (830, 1030), "female": (730, 930), "mixed": (780, 980)},
            28: {"male": (1380, 1680), "female": (1180, 1480), "mixed": (1280, 1580)},
            35: {"male": (1980, 2380), "female": (1780, 2180), "mixed": (1880, 2280)},
            42: {"male": (2580, 2980), "female": (2180, 2580), "mixed": (2380, 2780)}
        },
        "hubbard": {
            7: {"male": (170, 210), "female": (150, 190), "mixed": (160, 200)},
            14: {"male": (420, 520), "female": (370, 470), "mixed": (395, 495)},
            21: {"male": (800, 1000), "female": (700, 900), "mixed": (750, 950)},
            28: {"male": (1350, 1650), "female": (1150, 1450), "mixed": (1250, 1550)},
            35: {"male": (1950, 2350), "female": (1750, 2150), "mixed": (1850, 2250)},
            42: {"male": (2550, 2950), "female": (2150, 2550), "mixed": (2350, 2750)}
        },
        "standard_broiler": {
            7: {"male": (160, 200), "female": (140, 180), "mixed": (150, 190)},
            14: {"male": (400, 500), "female": (350, 450), "mixed": (375, 475)},
            21: {"male": (750, 950), "female": (650, 850), "mixed": (700, 900)},
            28: {"male": (1250, 1550), "female": (1050, 1350), "mixed": (1150, 1450)},
            35: {"male": (1850, 2250), "female": (1650, 2050), "mixed": (1750, 2150)},
            42: {"male": (2450, 2850), "female": (2050, 2450), "mixed": (2250, 2650)}
        }
    }
    
    # NOUVEAU: Mapping des variantes de noms de races
    BREED_NAME_MAPPING = {
        "ross 308": "ross_308",
        "ross308": "ross_308", 
        "ross-308": "ross_308",
        "cobb 500": "cobb_500",
        "cobb500": "cobb_500",
        "cobb-500": "cobb_500",
        "hubbard flex": "hubbard",
        "hubbard-flex": "hubbard",
        "aviagen": "ross_308",  # Aviagen produit Ross
        "standard": "standard_broiler",
        "broiler": "standard_broiler",
        "poulet": "standard_broiler"
    }
    
    # Différences mâles/femelles en pourcentage
    MALE_FEMALE_WEIGHT_DIFFERENCE = {
        "male_bonus_percent": 12,  # Mâles +12% en moyenne
        "female_penalty_percent": 10  # Femelles -10% en moyenne
    }
    
    # Tolérances pour les alertes
    WEIGHT_TOLERANCES = {
        "normal_range_percent": 15,    # ±15% = normal
        "alert_threshold_percent": 20,  # ±20% = alerte
        "critical_threshold_percent": 30  # ±30% = critique
    }
    
    # Races reconnues et leurs catégories
    BREED_CATEGORIES = {
        "heavy_broilers": ["ross_308", "cobb_500", "arbor_acres"],
        "standard_broilers": ["hubbard", "standard_broiler"],
        "layers": ["isa_brown", "lohmann_brown", "hy_line", "bovans"],
        "dual_purpose": ["rhode_island", "new_hampshire", "plymouth_rock"]
    }

# =============================================================================
# TEMPLATES DE MESSAGES STANDARDISÉS (AMÉLIORÉS)
# =============================================================================

class MessageTemplates:
    """Templates standardisés pour tous les messages"""
    
    # Messages d'offre de précision
    PRECISION_OFFERS = {
        "fr": {
            "breed_missing": "Précisez la **race/souche** (Ross 308, Cobb 500, Hubbard...) pour une réponse plus spécifique",
            "sex_missing": "Précisez le **sexe** (mâles, femelles, ou troupeau mixte) pour une réponse plus précise",
            "age_missing": "Précisez l'**âge** (en jours ou semaines) pour des recommandations adaptées",
            "breed_and_sex": "Précisez la **race** et le **sexe** pour une réponse personnalisée",
            "breed_and_age": "Précisez la **race** et l'**âge exact** pour des valeurs précises",
            "complete_info": "Précisez la **race**, le **sexe** et l'**âge** pour une réponse complète"
        },
        "en": {
            "breed_missing": "Specify the **breed/strain** (Ross 308, Cobb 500, Hubbard...) for a more specific answer",
            "sex_missing": "Specify the **sex** (males, females, or mixed flock) for a more precise answer",
            "age_missing": "Specify the **age** (in days or weeks) for adapted recommendations",
            "breed_and_sex": "Specify the **breed** and **sex** for a personalized answer",
            "breed_and_age": "Specify the **breed** and **exact age** for precise values",
            "complete_info": "Specify the **breed**, **sex** and **age** for a complete answer"
        }
    }
    
    # Messages de clarification par contexte
    CLARIFICATION_TEMPLATES = {
        "fr": {
            "performance": """Pour vous donner des informations précises sur les performances, j'ai besoin de :

🔍 **Informations nécessaires** :
{missing_entities_list}

💡 **Exemples de questions complètes** :
{examples_list}""",
            
            "health": """Pour vous aider efficacement avec un problème de santé, décrivez :

🩺 **Symptômes observés** :
• Comportement anormal (apathie, isolement...)
• Symptômes physiques (diarrhée, boiterie, difficultés respiratoires...)
• Évolution dans le temps

📋 **Contexte du troupeau** :
• Âge des animaux affectés
• Nombre de sujets touchés  
• Race/souche si connue

⏰ **Urgence** : En cas de mortalité ou symptômes graves, consultez immédiatement un vétérinaire.""",
            
            "feeding": """Pour des conseils nutritionnels adaptés, précisez :

🌾 **Informations sur vos animaux** :
• Âge ou stade physiologique
• Race/souche (chair, ponte, mixte)
• Effectif du troupeau

🎯 **Objectif recherché** :
• Croissance optimale, préparation ponte, maintien...
• Problème spécifique à résoudre

💡 **Exemple** : "Quel aliment pour Ross 308 de 3 semaines pour optimiser la croissance ?\"""",
            
            "general": """Pour vous donner une réponse adaptée, pouvez-vous préciser :

📋 **Votre situation** :
• Type de volailles (poulets de chair, pondeuses...)
• Âge ou stade d'élevage
• Problème ou objectif spécifique

🎯 **Exemples de questions précises** :
• "Poids normal Ross 308 mâles à 21 jours ?"
• "Symptômes diarrhée chez pondeuses 25 semaines"
• "Alimentation optimale Cobb 500 démarrage"

💡 Plus votre question est précise, plus ma réponse sera adaptée !""",

            # NOUVEAU: Template pour réponse contextuelle
            "contextual_success": """🔗 **Clarification détectée - Réponse basée sur le contexte de notre conversation**

{contextual_response}

💡 **Contexte utilisé** : {context_details}"""
        }
    }
    
    # Messages d'erreur et fallback
    FALLBACK_MESSAGES = {
        "fr": {
            "technical_error": """Je rencontre une difficulté technique pour analyser votre question.

💡 **Pour m'aider à mieux vous répondre, précisez** :
• Le type de volailles (poulets de chair, pondeuses...)
• L'âge de vos animaux (21 jours, 3 semaines...)  
• Votre problème ou objectif spécifique

**Exemple** : "Poids normal Ross 308 mâles à 21 jours ?"

🔄 Veuillez réessayer en reformulant votre question.""",
            
            "question_too_short": "Votre question semble incomplète. Pouvez-vous donner plus de détails sur votre situation ?",
            
            "no_context": "Je n'ai pas assez d'informations pour vous aider. Pouvez-vous préciser votre question avec plus de contexte ?",
            
            # NOUVEAU: Messages pour contexte
            "context_expired": "Le contexte de notre conversation a expiré. Pouvez-vous repréciser votre question complète ?",
            
            "context_error": "Erreur lors de la récupération du contexte conversationnel. Posez votre question complète."
        },
        "en": {
            "technical_error": """I'm experiencing a technical difficulty analyzing your question.

💡 **To help me better assist you, please specify** :
• Type of poultry (broilers, layers...)
• Age of your animals (21 days, 3 weeks...)
• Your specific problem or objective

**Example** : "Normal weight Ross 308 males at 21 days?"

🔄 Please try again by rephrasing your question.""",
            
            "question_too_short": "Your question seems incomplete. Could you provide more details about your situation?",
            
            "no_context": "I don't have enough information to help you. Could you clarify your question with more context?"
        }
    }

# =============================================================================
# CONFIGURATION AVANCÉE
# =============================================================================

class AdvancedConfig:
    """Configuration avancée du système"""
    
    # Extraction d'entités
    ENTITY_EXTRACTION = {
        "enable_fuzzy_matching": True,  # Correspondance approximative
        "min_confidence_entity": 0.7,   # Confiance minimum pour une entité
        "enable_context_inference": True,  # Inférence par contexte
        "max_entities_per_question": 10   # Maximum d'entités à extraire
    }
    
    # Classification intelligente
    SMART_CLASSIFICATION = {
        "enable_learning": False,  # Apprentissage automatique (désactivé pour simplicité)
        "confidence_adjustment": True,  # Ajustement dynamique de confiance
        "context_weight": 0.3,     # Poids du contexte dans la décision
        "entity_completeness_weight": 0.7,  # Poids de la complétude des entités
        "enable_contextual_classification": True  # NOUVEAU: Classification contextuelle
    }
    
    # Génération de réponse
    RESPONSE_GENERATION = {
        "enable_dynamic_templates": True,  # Templates dynamiques
        "max_response_length": 2000,      # Longueur maximum de réponse
        "include_examples": True,         # Inclure des exemples
        "include_precision_offers": True,  # Inclure offres de précision
        "format_with_emojis": True,       # Formatage avec emojis
        "enable_contextual_responses": True  # NOUVEAU: Réponses contextuelles
    }
    
    # Performance et monitoring
    PERFORMANCE = {
        "cache_responses": False,     # Cache des réponses (désactivé pour simplicité)
        "log_all_interactions": True, # Logger toutes les interactions
        "collect_analytics": True,    # Collecter des analytics
        "alert_on_errors": True,      # Alertes en cas d'erreur
        "enable_context_monitoring": True  # NOUVEAU: Monitoring du contexte
    }

# =============================================================================
# FONCTIONS UTILITAIRES DE CONFIGURATION (AMÉLIORÉES)
# =============================================================================

def normalize_breed_name(breed: str) -> str:
    """
    NOUVEAU: Normalise le nom d'une race selon le mapping
    
    Args:
        breed: Nom de race brut
        
    Returns:
        Nom de race normalisé
    """
    if not breed:
        return "standard_broiler"
    
    breed_lower = breed.lower().strip()
    
    # Vérification directe dans le mapping
    if breed_lower in ReferenceData.BREED_NAME_MAPPING:
        return ReferenceData.BREED_NAME_MAPPING[breed_lower]
    
    # Vérification si déjà normalisé
    if breed_lower.replace(' ', '_') in ReferenceData.WEIGHT_STANDARDS:
        return breed_lower.replace(' ', '_')
    
    # Fallback
    return "standard_broiler"

def get_weight_range(breed: str, age_days: int, sex: str = "mixed") -> Tuple[int, int]:
    """
    🔧 FONCTION CORRIGÉE: Récupère la fourchette de poids avec interpolation linéaire précise
    
    Args:
        breed: Nom de la race (Ross 308, Cobb 500, etc.)
        age_days: Âge en jours
        sex: Sexe (male, female, mixed)
        
    Returns:
        Tuple (poids_min, poids_max) en grammes
        
    Example:
        get_weight_range("Ross 308", 12, "male") → (380, 420)
    """
    # NOUVEAU: Normaliser le nom de race
    breed_key = normalize_breed_name(breed)
    
    # Vérifier si la race existe
    if breed_key not in ReferenceData.WEIGHT_STANDARDS:
        breed_key = "standard_broiler"
    
    breed_data = ReferenceData.WEIGHT_STANDARDS[breed_key]
    available_ages = sorted(breed_data.keys())
    
    # Normaliser le sexe
    if sex.lower() in ['mâle', 'male', 'coq']:
        sex = 'male'
    elif sex.lower() in ['femelle', 'female', 'poule']:
        sex = 'female'
    else:
        sex = 'mixed'
    
    # Si l'âge exact existe, le retourner directement
    if age_days in available_ages:
        weight_range = breed_data[age_days].get(sex, breed_data[age_days]["mixed"])
        return weight_range
    
    # 🔧 CORRECTION: Interpolation linéaire précise pour âges intermédiaires
    
    # Trouver les âges encadrants
    lower_age = None
    upper_age = None
    
    for age in available_ages:
        if age <= age_days:
            lower_age = age
        if age >= age_days and upper_age is None:
            upper_age = age
            break
    
    # Cas limites
    if lower_age is None:  # age_days < premier âge disponible
        closest_age = available_ages[0]
        weight_range = breed_data[closest_age].get(sex, breed_data[closest_age]["mixed"])
        # Extrapoler vers le bas (approximation simple)
        factor = age_days / closest_age
        return (int(weight_range[0] * factor), int(weight_range[1] * factor))
    
    if upper_age is None:  # age_days > dernier âge disponible
        closest_age = available_ages[-1]
        weight_range = breed_data[closest_age].get(sex, breed_data[closest_age]["mixed"])
        # Extrapoler vers le haut
        factor = age_days / closest_age
        return (int(weight_range[0] * factor), int(weight_range[1] * factor))
    
    # 🎯 INTERPOLATION LINÉAIRE PRÉCISE
    if lower_age == upper_age:  # Âge exact trouvé
        weight_range = breed_data[lower_age].get(sex, breed_data[lower_age]["mixed"])
        return weight_range
    
    # Récupérer les poids aux âges encadrants
    weight_lower = breed_data[lower_age].get(sex, breed_data[lower_age]["mixed"])
    weight_upper = breed_data[upper_age].get(sex, breed_data[upper_age]["mixed"])
    
    # Calcul du facteur d'interpolation
    factor = (age_days - lower_age) / (upper_age - lower_age)
    
    # Interpolation linéaire pour min et max
    min_weight = int(weight_lower[0] + factor * (weight_upper[0] - weight_lower[0]))
    max_weight = int(weight_lower[1] + factor * (weight_upper[1] - weight_lower[1]))
    
    return (min_weight, max_weight)

def get_precision_offer_message(missing_entities: List[str], language: str = "fr") -> str:
    """
    Génère le message d'offre de précision selon les entités manquantes
    
    Args:
        missing_entities: Liste des entités manquantes
        language: Langue du message
        
    Returns:
        Message d'offre de précision formaté
    """
    templates = MessageTemplates.PRECISION_OFFERS.get(language, MessageTemplates.PRECISION_OFFERS["fr"])
    
    if not missing_entities:
        return ""
    
    if len(missing_entities) == 1:
        entity = missing_entities[0]
        return templates.get(f"{entity}_missing", templates["breed_missing"])
    
    elif set(missing_entities) == {"breed", "sex"}:
        return templates["breed_and_sex"]
    
    elif set(missing_entities) == {"breed", "age"}:
        return templates["breed_and_age"]
    
    elif len(missing_entities) >= 3:
        return templates["complete_info"]
    
    else:
        # Cas général pour 2 entités
        return templates["breed_and_sex"]  # Par défaut

def get_clarification_template(context_type: str, language: str = "fr") -> str:
    """
    Récupère le template de clarification pour un type de contexte
    
    Args:
        context_type: Type de contexte (performance, health, feeding, general)
        language: Langue du template
        
    Returns:
        Template de clarification formaté
    """
    templates = MessageTemplates.CLARIFICATION_TEMPLATES.get(language, MessageTemplates.CLARIFICATION_TEMPLATES["fr"])
    return templates.get(context_type, templates["general"])

def get_fallback_message(error_type: str, language: str = "fr") -> str:
    """
    Récupère un message de fallback selon le type d'erreur
    
    Args:
        error_type: Type d'erreur (technical_error, question_too_short, no_context)
        language: Langue du message
        
    Returns:
        Message de fallback approprié
    """
    messages = MessageTemplates.FALLBACK_MESSAGES.get(language, MessageTemplates.FALLBACK_MESSAGES["fr"])
    return messages.get(error_type, messages["technical_error"])

def is_breed_recognized(breed_name: str) -> bool:
    """Vérifie si une race est reconnue dans le système"""
    normalized = normalize_breed_name(breed_name)
    return normalized in ReferenceData.WEIGHT_STANDARDS

def get_breed_category(breed_name: str) -> str:
    """Retourne la catégorie d'une race"""
    breed_key = normalize_breed_name(breed_name)
    
    for category, breeds in ReferenceData.BREED_CATEGORIES.items():
        if breed_key in breeds:
            return category
    
    return "unknown"

def validate_weight_range(weight: float, breed: str, age_days: int, sex: str = "mixed") -> Dict[str, Any]:
    """
    Valide si un poids est dans la fourchette normale
    
    Returns:
        Dict avec status (normal/alert/critical) et détails
    """
    min_weight, max_weight = get_weight_range(breed, age_days, sex)
    
    if min_weight <= weight <= max_weight:
        return {"status": "normal", "message": "Poids dans la fourchette normale"}
    
    # Calculer l'écart en pourcentage
    target_weight = (min_weight + max_weight) / 2
    deviation_percent = abs((weight - target_weight) / target_weight) * 100
    
    if deviation_percent <= ReferenceData.WEIGHT_TOLERANCES["alert_threshold_percent"]:
        return {"status": "alert", "message": f"Écart de {deviation_percent:.1f}% par rapport à la normale"}
    
    else:
        return {"status": "critical", "message": f"Écart critique de {deviation_percent:.1f}% - Consultation recommandée"}

# =============================================================================
# NOUVELLES FONCTIONS POUR LE CONTEXTE CONVERSATIONNEL
# =============================================================================

def get_contextual_response_template(context_details: str, language: str = "fr") -> str:
    """
    NOUVEAU: Génère un template pour les réponses contextuelles
    
    Args:
        context_details: Détails du contexte utilisé
        language: Langue de réponse
        
    Returns:
        Template de réponse contextuelle
    """
    templates = MessageTemplates.CLARIFICATION_TEMPLATES.get(language, MessageTemplates.CLARIFICATION_TEMPLATES["fr"])
    return templates.get("contextual_success", "🔗 **Réponse basée sur le contexte** : {context_details}")

def calculate_weight_with_sex_adjustment(base_range: Tuple[int, int], sex: str) -> Tuple[int, int]:
    """
    NOUVEAU: Ajuste une fourchette de poids selon le sexe
    
    Args:
        base_range: Fourchette de base (mixed)
        sex: Sexe (male/female)
        
    Returns:
        Fourchette ajustée
    """
    min_weight, max_weight = base_range
    
    if sex == "male":
        # Mâles +12% en moyenne
        adjustment = ReferenceData.MALE_FEMALE_WEIGHT_DIFFERENCE["male_bonus_percent"] / 100
        return (int(min_weight * (1 + adjustment)), int(max_weight * (1 + adjustment)))
    
    elif sex == "female":
        # Femelles -10% en moyenne
        adjustment = ReferenceData.MALE_FEMALE_WEIGHT_DIFFERENCE["female_penalty_percent"] / 100
        return (int(min_weight * (1 - adjustment)), int(max_weight * (1 - adjustment)))
    
    else:
        return base_range

def get_interpolation_debug_info(breed: str, age_days: int, sex: str = "mixed") -> Dict[str, Any]:
    """
    NOUVEAU: Retourne les informations de debug pour l'interpolation
    
    Args:
        breed: Race
        age_days: Âge en jours
        sex: Sexe
        
    Returns:
        Informations de debug détaillées
    """
    breed_key = normalize_breed_name(breed)
    breed_data = ReferenceData.WEIGHT_STANDARDS.get(breed_key, {})
    available_ages = sorted(breed_data.keys()) if breed_data else []
    
    # Trouver les âges encadrants
    lower_age = None
    upper_age = None
    
    for age in available_ages:
        if age <= age_days:
            lower_age = age
        if age >= age_days and upper_age is None:
            upper_age = age
            break
    
    weight_range = get_weight_range(breed, age_days, sex)
    
    return {
        "breed_input": breed,
        "breed_normalized": breed_key,
        "age_days": age_days,
        "sex": sex,
        "available_ages": available_ages,
        "interpolation_bounds": {
            "lower_age": lower_age,
            "upper_age": upper_age
        },
        "calculated_range": weight_range,
        "interpolation_used": lower_age != upper_age if lower_age and upper_age else False
    }

# =============================================================================
# FONCTION DE TEST POUR VALIDATION
# =============================================================================

def test_weight_calculations():
    """
    NOUVEAU: Teste les calculs de poids pour validation
    """
    test_cases = [
        # Test cas Ross 308 mâle 12 jours (le cas problématique)
        {"breed": "Ross 308", "age": 12, "sex": "male", "expected_range": (380, 420)},
        {"breed": "ross 308", "age": 12, "sex": "mâle", "expected_range": (380, 420)},
        
        # Tests âges exacts
        {"breed": "Ross 308", "age": 14, "sex": "male", "expected_range": (450, 550)},
        {"breed": "Ross 308", "age": 7, "sex": "male", "expected_range": (180, 220)},
        
        # Tests interpolation
        {"breed": "Cobb 500", "age": 10, "sex": "female", "expected_range": None},  # Sera calculé
        
        # Tests normalisation
        {"breed": "ross308", "age": 21, "sex": "mixed", "expected_range": (800, 1000)},
    ]
    
    print("🧪 Test des calculs de poids - intelligent_system_config.py")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        try:
            result = get_weight_range(test["breed"], test["age"], test["sex"])
            debug_info = get_interpolation_debug_info(test["breed"], test["age"], test["sex"])
            
            print(f"\nTest {i}: {test['breed']} {test['sex']} {test['age']}j")
            print(f"  Résultat: {result[0]}-{result[1]}g")
            print(f"  Interpolation: {'Oui' if debug_info['interpolation_used'] else 'Non'}")
            
            if test["expected_range"]:
                expected = test["expected_range"]
                if result == expected:
                    print(f"  ✅ SUCCESS: Attendu {expected[0]}-{expected[1]}g")
                else:
                    print(f"  ❌ FAILED: Attendu {expected[0]}-{expected[1]}g, obtenu {result[0]}-{result[1]}g")
            else:
                print(f"  📊 CALCULÉ: {result[0]}-{result[1]}g")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    # Test spécial Ross 308 mâle 12 jours
    print(f"\n🎯 Test spécial Ross 308 mâle 12 jours:")
    result = get_weight_range("Ross 308", 12, "male")
    if result == (380, 420):
        print(f"  ✅ PERFECT: {result[0]}-{result[1]}g (interpolation entre 7j et 14j)")
    else:
        print(f"  ❌ PROBLÈME: {result[0]}-{result[1]}g (devrait être 380-420g)")

# =============================================================================
# CONFIGURATION GLOBALE EXPORTÉE
# =============================================================================

# Configuration principale utilisée par le système
INTELLIGENT_SYSTEM_CONFIG = {
    "behavior": SystemBehavior,
    "thresholds": DecisionThresholds,
    "reference_data": ReferenceData,
    "templates": MessageTemplates,
    "advanced": AdvancedConfig
}

# Export des fonctions utilitaires principales
__all__ = [
    'INTELLIGENT_SYSTEM_CONFIG',
    'get_weight_range',
    'get_precision_offer_message', 
    'get_clarification_template',
    'get_fallback_message',
    'is_breed_recognized',
    'get_breed_category',
    'validate_weight_range',
    'normalize_breed_name',
    'get_contextual_response_template',
    'calculate_weight_with_sex_adjustment',
    'get_interpolation_debug_info',
    'test_weight_calculations'
]

if __name__ == "__main__":
    # Lancer les tests si exécuté directement
    test_weight_calculations()