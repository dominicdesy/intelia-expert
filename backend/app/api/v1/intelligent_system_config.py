"""
intelligent_system_config.py - CONFIGURATION UNIFIÉE DU SYSTÈME INTELLIGENT

🎯 CENTRALISE: Toute la configuration du nouveau système
🚀 PRINCIPE: Une seule source de vérité pour tous les paramètres
✨ SIMPLE: Configuration claire et modifiable facilement

Sections:
- Comportement général du système
- Seuils de décision et confiance
- Templates et messages standardisés
- Données de référence (poids, races, etc.)
- Configuration de logging et monitoring
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
    
    # Critères pour réponse précise
    MIN_ENTITIES_FOR_PRECISE = 2  # race + âge, ou race + sexe, etc.
    REQUIRED_ENTITIES_PRECISE = ["breed_specific"]  # Au minimum une race spécifique
    
    # Critères pour réponse générale  
    MIN_ENTITIES_FOR_GENERAL = 1  # Au moins un contexte utile
    MAX_MISSING_ENTITIES_FOR_GENERAL = 2  # Maximum 2 entités manquantes
    
    # Critères pour clarification forcée
    MAX_QUESTION_WORDS_FOR_CLARIFICATION = 4  # Questions trop courtes
    MIN_CONTEXT_FOR_USEFUL_RESPONSE = 1  # Minimum de contexte

# =============================================================================
# DONNÉES DE RÉFÉRENCE - POIDS ET PERFORMANCES
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
# TEMPLATES DE MESSAGES STANDARDISÉS
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

💡 Plus votre question est précise, plus ma réponse sera adaptée !"""
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
            
            "no_context": "Je n'ai pas assez d'informations pour vous aider. Pouvez-vous préciser votre question avec plus de contexte ?"
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
        "entity_completeness_weight": 0.7  # Poids de la complétude des entités
    }
    
    # Génération de réponse
    RESPONSE_GENERATION = {
        "enable_dynamic_templates": True,  # Templates dynamiques
        "max_response_length": 2000,      # Longueur maximum de réponse
        "include_examples": True,         # Inclure des exemples
        "include_precision_offers": True,  # Inclure offres de précision
        "format_with_emojis": True        # Formatage avec emojis
    }
    
    # Performance et monitoring
    PERFORMANCE = {
        "cache_responses": False,     # Cache des réponses (désactivé pour simplicité)
        "log_all_interactions": True, # Logger toutes les interactions
        "collect_analytics": True,    # Collecter des analytics
        "alert_on_errors": True       # Alertes en cas d'erreur
    }

# =============================================================================
# FONCTIONS UTILITAIRES DE CONFIGURATION
# =============================================================================

def get_weight_range(breed: str, age_days: int, sex: str = "mixed") -> Tuple[int, int]:
    """
    Récupère la fourchette de poids pour une race, âge et sexe donnés
    
    Args:
        breed: Nom de la race (ross_308, cobb_500, etc.)
        age_days: Âge en jours
        sex: Sexe (male, female, mixed)
        
    Returns:
        Tuple (poids_min, poids_max) en grammes
    """
    breed_key = breed.lower().replace(' ', '_')
    
    # Vérifier si la race existe
    if breed_key not in ReferenceData.WEIGHT_STANDARDS:
        breed_key = "standard_broiler"
    
    breed_data = ReferenceData.WEIGHT_STANDARDS[breed_key]
    
    # Trouver l'âge le plus proche
    available_ages = sorted(breed_data.keys())
    closest_age = min(available_ages, key=lambda x: abs(x - age_days))
    
    # Récupérer la fourchette
    weight_range = breed_data[closest_age].get(sex, breed_data[closest_age]["mixed"])
    
    # Ajuster pour l'âge exact si différent
    if age_days != closest_age and age_days > 0:
        adjustment_factor = age_days / closest_age
        min_weight = int(weight_range[0] * adjustment_factor)
        max_weight = int(weight_range[1] * adjustment_factor)
        return (min_weight, max_weight)
    
    return weight_range

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
    breed_key = breed_name.lower().replace(' ', '_')
    return breed_key in ReferenceData.WEIGHT_STANDARDS

def get_breed_category(breed_name: str) -> str:
    """Retourne la catégorie d'une race"""
    breed_key = breed_name.lower().replace(' ', '_')
    
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
    'validate_weight_range'
]