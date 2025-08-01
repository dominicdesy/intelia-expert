# expert_utils.py - VERSION FINALE COMPLÈTE AVEC CLARIFICATION INTELLIGENTE
"""
app/api/v1/expert_utils.py - UTILITAIRES EXPERT SYSTEM

Fonctions utilitaires pour le système expert
VERSION FINALE : Avec nouvelles fonctions de clarification intelligente
"""

import os
import logging
import uuid
import re
from typing import Dict, Any, Optional, List
from fastapi import Request

logger = logging.getLogger(__name__)

def get_user_id_from_request(request: Request) -> str:
    """Extrait l'user_id depuis la requête"""
    # Essayer d'extraire depuis les headers ou token
    authorization = request.headers.get("authorization", "")
    if authorization:
        # Ici vous pouvez parser le JWT pour extraire l'user_id
        # Pour l'instant, génération d'un ID temporaire
        return f"user_{uuid.uuid4().hex[:8]}"
    
    # Fallback
    return f"anonymous_{uuid.uuid4().hex[:8]}"

def build_enriched_question_from_clarification(
    original_question: str,
    clarification_response: str, 
    conversation_context: str = ""
) -> str:
    """Construit une question enrichie à partir d'une clarification"""
    if conversation_context:
        return f"{original_question}\n\nClarification: {clarification_response}\n\nContexte: {conversation_context}"
    else:
        return f"{original_question}\n\nClarification: {clarification_response}"

# =============================================================================
# ✅ NOUVELLES FONCTIONS DE CLARIFICATION INTELLIGENTE
# =============================================================================

def extract_breed_and_sex_from_clarification(clarification_text: str, language: str = "fr") -> Dict[str, Optional[str]]:
    """
    ✅ NOUVELLE FONCTION : Extrait race et sexe d'une réponse de clarification
    
    Exemples de réponses attendues:
    - "Ross 308 mâles"
    - "Cobb 500 femelles" 
    - "Hubbard troupeau mixte"
    """
    
    clarification_lower = clarification_text.lower().strip()
    result = {"breed": None, "sex": None}
    
    # === EXTRACTION RACE ===
    breed_patterns = [
        # Races spécifiques avec numéros
        (r'ross\s*308', 'Ross 308'),
        (r'ross\s*708', 'Ross 708'),
        (r'cobb\s*500', 'Cobb 500'),
        (r'cobb\s*700', 'Cobb 700'),
        (r'hubbard\s*(?:flex|classic)', 'Hubbard'),
        (r'arbor\s*acres', 'Arbor Acres'),
        
        # Races génériques
        (r'\bhubbard\b', 'Hubbard'),
        (r'\bross\b', 'Ross'),
        (r'\bcobb\b', 'Cobb'),
        (r'\bisa\s*15', 'ISA 15')
    ]
    
    for pattern, breed_name in breed_patterns:
        if re.search(pattern, clarification_lower):
            result["breed"] = breed_name
            break
    
    # === EXTRACTION SEXE ===
    sex_patterns = {
        "fr": [
            (r'\bmâles?\b', 'mâles'),
            (r'\bfemelles?\b', 'femelles'),
            (r'\bmixtes?\b', 'mixte'),
            (r'\btroupeau\s+mixte\b', 'mixte'),
            (r'\bcoqs?\b', 'mâles'),
            (r'\bpoules?\b', 'femelles')
        ],
        "en": [
            (r'\bmales?\b', 'males'),
            (r'\bfemales?\b', 'females'),
            (r'\bmixed?\b', 'mixed'),
            (r'\bmixed\s+flock\b', 'mixed'),
            (r'\brooster\b', 'males'),
            (r'\bhens?\b', 'females')
        ],
        "es": [
            (r'\bmachos?\b', 'machos'),
            (r'\bhembras?\b', 'hembras'),
            (r'\bmixto\b', 'mixto'),
            (r'\blote\s+mixto\b', 'mixto'),
            (r'\bgallos?\b', 'machos'),
            (r'\bgallinas?\b', 'hembras')
        ]
    }
    
    patterns = sex_patterns.get(language, sex_patterns["fr"])
    
    for pattern, sex_name in patterns:
        if re.search(pattern, clarification_lower):
            result["sex"] = sex_name
            break
    
    return result

def build_enriched_question_with_breed_sex(
    original_question: str,
    breed: Optional[str],
    sex: Optional[str],
    language: str = "fr"
) -> str:
    """
    ✅ NOUVELLE FONCTION : Enrichit une question avec race et sexe extraits
    """
    
    if not breed and not sex:
        return original_question
    
    # Templates d'enrichissement par langue
    templates = {
        "fr": {
            "both": "Pour des {breed} {sex}",
            "breed_only": "Pour des {breed}",
            "sex_only": "Pour des poulets {sex}"
        },
        "en": {
            "both": "For {breed} {sex}",
            "breed_only": "For {breed} chickens",
            "sex_only": "For {sex} chickens"
        },
        "es": {
            "both": "Para pollos {breed} {sex}",
            "breed_only": "Para pollos {breed}",
            "sex_only": "Para pollos {sex}"
        }
    }
    
    template_set = templates.get(language, templates["fr"])
    
    # Construire le préfixe contextuel
    if breed and sex:
        context_prefix = template_set["both"].format(breed=breed, sex=sex)
    elif breed:
        context_prefix = template_set["breed_only"].format(breed=breed)
    elif sex:
        context_prefix = template_set["sex_only"].format(sex=sex)
    else:
        return original_question
    
    # Intégrer à la question originale
    if original_question.lower().startswith(('quel', 'what', 'cuál', 'combien', 'how')):
        return f"{context_prefix}, {original_question.lower()}"
    else:
        return f"{context_prefix}: {original_question}"

def validate_clarification_completeness(
    clarification_text: str,
    missing_info: List[str],
    language: str = "fr"
) -> Dict[str, Any]:
    """
    ✅ NOUVELLE FONCTION : Valide qu'une clarification contient les infos demandées
    """
    
    extracted = extract_breed_and_sex_from_clarification(clarification_text, language)
    
    validation_result = {
        "is_complete": True,
        "still_missing": [],
        "extracted_info": extracted,
        "confidence": 1.0
    }
    
    # Vérifier chaque info manquante
    if "breed" in missing_info and not extracted["breed"]:
        validation_result["is_complete"] = False
        validation_result["still_missing"].append("breed")
        validation_result["confidence"] -= 0.5
    
    if "sex" in missing_info and not extracted["sex"]:
        validation_result["is_complete"] = False
        validation_result["still_missing"].append("sex")
        validation_result["confidence"] -= 0.3
    
    validation_result["confidence"] = max(validation_result["confidence"], 0.0)
    
    return validation_result

def get_performance_clarification_examples(language: str = "fr") -> Dict[str, List[str]]:
    """
    ✅ NOUVELLE FONCTION : Exemples de clarifications pour questions de performance
    """
    
    examples = {
        "fr": {
            "complete_responses": [
                "Ross 308 mâles",
                "Cobb 500 femelles", 
                "Hubbard troupeau mixte",
                "Ross 708 femelles",
                "Arbor Acres mâles"
            ],
            "breed_examples": [
                "Ross 308",
                "Cobb 500",
                "Hubbard Flex",
                "Arbor Acres"
            ],
            "sex_examples": [
                "mâles",
                "femelles", 
                "troupeau mixte"
            ]
        },
        "en": {
            "complete_responses": [
                "Ross 308 males",
                "Cobb 500 females",
                "Hubbard mixed flock",
                "Ross 708 females", 
                "Arbor Acres males"
            ],
            "breed_examples": [
                "Ross 308",
                "Cobb 500", 
                "Hubbard Flex",
                "Arbor Acres"
            ],
            "sex_examples": [
                "males",
                "females",
                "mixed flock"
            ]
        },
        "es": {
            "complete_responses": [
                "Ross 308 machos",
                "Cobb 500 hembras",
                "Hubbard lote mixto",
                "Ross 708 hembras",
                "Arbor Acres machos"
            ],
            "breed_examples": [
                "Ross 308",
                "Cobb 500",
                "Hubbard Flex", 
                "Arbor Acres"
            ],
            "sex_examples": [
                "machos",
                "hembras",
                "lote mixto"
            ]
        }
    }
    
    return examples.get(language, examples["fr"])

def get_enhanced_topics_by_language() -> Dict[str, list]:
    """✅ FONCTION AMÉLIORÉE : Topics enrichis avec exemples de clarification"""
    return {
        "fr": [
            "Poids Ross 308 mâles à 21 jours",
            "Croissance Cobb 500 femelles semaine 3", 
            "Conditions environnementales optimales",
            "Protocoles de vaccination par race",
            "Diagnostic problèmes de santé",
            "Nutrition selon âge et sexe",
            "Gestion de la mortalité",
            "Température et humidité par phase"
        ],
        "en": [
            "Ross 308 males weight at 21 days",
            "Cobb 500 females growth week 3",
            "Optimal environmental conditions", 
            "Vaccination protocols by breed",
            "Health problem diagnosis",
            "Nutrition by age and sex",
            "Mortality management",
            "Temperature and humidity by phase"
        ],
        "es": [
            "Peso Ross 308 machos a 21 días",
            "Crecimiento Cobb 500 hembras semana 3",
            "Condiciones ambientales óptimas",
            "Protocolos vacunación por raza", 
            "Diagnóstico problemas de salud",
            "Nutrición según edad y sexo",
            "Gestión de mortalidad",
            "Temperatura y humedad por fase"
        ]
    }

# =============================================================================
# FONCTIONS EXISTANTES MAINTENUES
# =============================================================================

async def save_conversation_auto_enhanced(
    conversation_id: str,
    question: str,
    response: str,
    user_id: str,
    language: str = "fr"
) -> bool:
    """Sauvegarde automatique de conversation"""
    try:
        # Ici vous pouvez intégrer avec votre système de logging
        logger.info(f"💾 Sauvegarde conversation {conversation_id}: {question[:50]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")
        return False

def get_fallback_response_enhanced(question: str, language: str = "fr") -> str:
    """
    Réponse de fallback améliorée - REDIRECTION VERS RAG
    
    NOTE: Cette fonction ne doit plus être utilisée avec des données codées.
    Elle redirige vers le système RAG.
    """
    responses = {
        "fr": "Le système expert nécessite l'accès à la base documentaire pour répondre à votre question. Veuillez vous assurer que le service RAG est disponible.",
        "en": "The expert system requires access to the document database to answer your question. Please ensure the RAG service is available.",
        "es": "El sistema experto requiere acceso a la base de datos de documentos para responder a su pregunta. Asegúrese de que el servicio RAG esté disponible."
    }
    return responses.get(language.lower(), responses["fr"])

# =============================================================================
# FONCTIONS DÉPRÉCIÉES - AVEC DONNÉES CODÉES SUPPRIMÉES
# =============================================================================

async def process_question_with_enhanced_prompt_DEPRECATED(
    question: str, 
    language: str = "fr", 
    speed_mode: str = "balanced",
    extracted_entities: Optional[Dict] = None,
    conversation_context: str = ""
) -> str:
    """
    ❌ FONCTION DÉPRÉCIÉE - SUPPRIMÉE
    
    Cette fonction contenait des données Ross 308 codées en dur.
    Toutes les réponses doivent maintenant passer par le RAG qui contient
    les documents de référence officiels (Performance Objectives, etc.).
    """
    
    logger.error("❌ [Expert Utils] ERREUR: Tentative d'utilisation de fonction dépréciée")
    logger.error("❌ [Expert Utils] Architecture actuelle: RAG-First obligatoire")
    
    raise RuntimeError(
        "ERREUR ARCHITECTURE: process_question_with_enhanced_prompt est dépréciée. "
        "Toutes les requêtes doivent passer par le système RAG qui contient "
        "les Performance Objectives officiels d'Aviagen."
    )

def get_hardcoded_ross_308_data_DEPRECATED():
    """❌ FONCTION SUPPRIMÉE - DONNÉES TRANSFÉRÉES VERS RAG"""
    
    logger.error("❌ [Expert Utils] Tentative d'accès aux données codées supprimées")
    
    raise RuntimeError(
        "DONNÉES SUPPRIMÉES: Les données Ross 308 ne sont plus codées en dur. "
        "Elles se trouvent dans la base documentaire RAG. "
        "Utilisez le système RAG pour accéder aux Performance Objectives officiels."
    )

# =============================================================================
# NOUVELLES FONCTIONS UTILITAIRES RAG-FIRST
# =============================================================================

def validate_rag_availability(app_state) -> bool:
    """Valide que le système RAG est disponible"""
    process_rag = getattr(app_state, 'process_question_with_rag', None)
    return process_rag is not None

def log_rag_dependency_error(function_name: str, question: str):
    """Log les erreurs de dépendance RAG"""
    logger.error(f"❌ [Expert Utils] {function_name}: RAG non disponible")
    logger.error(f"❌ [Expert Utils] Question: {question[:100]}...")
    logger.error(f"❌ [Expert Utils] Action requise: Vérifier initialisation RAG")
    logger.error(f"❌ [Expert Utils] Documents requis: Ross 308 Performance Objectives")

def get_rag_error_response(language: str = "fr") -> str:
    """Retourne un message d'erreur approprié quand RAG est indisponible"""
    
    messages = {
        "fr": (
            "Service temporairement indisponible. "
            "Le système expert nécessite l'accès à la base documentaire "
            "pour fournir des informations précises sur les performances "
            "des races de poulets. Veuillez réessayer plus tard."
        ),
        "en": (
            "Service temporarily unavailable. "
            "The expert system requires access to the document database "
            "to provide accurate information about chicken breed performance. "
            "Please try again later."
        ),
        "es": (
            "Servicio temporalmente no disponible. "
            "El sistema experto requiere acceso a la base de datos de documentos "
            "para proporcionar información precisa sobre el rendimiento de las razas de pollos. "
            "Por favor, inténtelo de nuevo más tarde."
        )
    }
    
    return messages.get(language.lower(), messages["fr"])

def suggest_rag_setup_check() -> Dict[str, Any]:
    """Suggère les vérifications à effectuer pour le setup RAG"""
    
    return {
        "checks_required": [
            "Vérifier que process_question_with_rag est initialisé dans app.state",
            "Confirmer que la base documentaire contient les Performance Objectives Ross 308",
            "Tester la connectivité vers le système de vectorisation",
            "Valider que les documents sont correctement indexés"
        ],
        "critical_documents": [
            "Ross 308 Performance Objectives 2022 (Aviagen)",
            "Cobb 500 Performance Standards", 
            "Guides de nutrition avicole",
            "Protocoles de vaccination"
        ],
        "test_questions": [
            "Quel est le poids d'un Ross 308 au jour 18 ?",
            "Quelles sont les conditions optimales pour l'élevage ?",
            "Protocoles de vaccination recommandés ?"
        ]
    }

# =============================================================================
# FONCTIONS DE VALIDATION AVANCÉES
# =============================================================================

def validate_breed_sex_combination(breed: str, sex: str, language: str = "fr") -> Dict[str, Any]:
    """
    ✅ NOUVELLE FONCTION : Valide que la combinaison race/sexe est cohérente
    """
    
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "suggestions": [],
        "confidence": 1.0
    }
    
    # Normaliser les entrées
    breed_normalized = breed.lower().strip() if breed else ""
    sex_normalized = sex.lower().strip() if sex else ""
    
    # Vérifications de cohérence
    known_breeds = ["ross 308", "ross 708", "cobb 500", "cobb 700", "hubbard", "arbor acres"]
    valid_sexes = {
        "fr": ["mâles", "femelles", "mixte"],
        "en": ["males", "females", "mixed"],
        "es": ["machos", "hembras", "mixto"]
    }
    
    # Vérifier race connue
    if breed_normalized and not any(known in breed_normalized for known in known_breeds):
        validation_result["warnings"].append(f"Race '{breed}' moins courante")
        validation_result["confidence"] -= 0.2
    
    # Vérifier sexe valide
    if sex_normalized and sex_normalized not in [s.lower() for s in valid_sexes.get(language, valid_sexes["fr"])]:
        validation_result["warnings"].append(f"Sexe '{sex}' non reconnu")
        validation_result["confidence"] -= 0.3
    
    validation_result["confidence"] = max(validation_result["confidence"], 0.0)
    
    return validation_result

def generate_contextual_follow_up_questions(
    breed: str, sex: str, age_days: int, language: str = "fr"
) -> List[str]:
    """
    ✅ NOUVELLE FONCTION : Génère des questions de suivi contextuelles
    """
    
    questions = []
    
    templates = {
        "fr": [
            f"Quelle est la consommation d'aliment normale pour {breed} {sex} à {age_days} jours ?",
            f"Quelles conditions de température pour {breed} {sex} de {age_days} jours ?",
            f"Protocole de vaccination recommandé pour {breed} à {age_days} jours ?",
            f"Comment optimiser la croissance des {breed} {sex} à cette phase ?"
        ],
        "en": [
            f"What is the normal feed consumption for {breed} {sex} at {age_days} days?",
            f"What temperature conditions for {breed} {sex} at {age_days} days?",
            f"Recommended vaccination protocol for {breed} at {age_days} days?",
            f"How to optimize growth of {breed} {sex} at this stage?"
        ],
        "es": [
            f"¿Cuál es el consumo normal de alimento para {breed} {sex} a {age_days} días?",
            f"¿Qué condiciones de temperatura para {breed} {sex} a {age_days} días?",
            f"¿Protocolo de vacunación recomendado para {breed} a {age_days} días?",
            f"¿Cómo optimizar el crecimiento de {breed} {sex} en esta fase?"
        ]
    }
    
    question_templates = templates.get(language, templates["fr"])
    
    # Sélectionner 2-3 questions pertinentes selon l'âge
    if age_days <= 7:
        # Phase jeune poulet
        questions = question_templates[:2]
    elif age_days <= 21:
        # Phase croissance
        questions = [question_templates[0], question_templates[2]]
    else:
        # Phase finition
        questions = [question_templates[0], question_templates[3]]
    
    return questions

# =============================================================================
# LOGGING DE MIGRATION
# =============================================================================

logger.info("✅ [Expert Utils] Module utilitaires final - RAG-First + Clarification intelligente")
logger.info("✅ [Expert Utils] Compatible avec toutes les améliorations API")
logger.info("   - ❌ Données codées supprimées")
logger.info("   - ✅ Architecture RAG-First obligatoire")
logger.info("   - ✅ Support complet nouvelles fonctionnalités")
logger.info("🎯 [Expert Utils] Nouvelles fonctions de clarification:")
logger.info("   - extract_breed_and_sex_from_clarification()")
logger.info("   - build_enriched_question_with_breed_sex()")
logger.info("   - validate_clarification_completeness()")
logger.info("   - get_performance_clarification_examples()")
logger.info("   - validate_breed_sex_combination()")
logger.info("   - generate_contextual_follow_up_questions()")
logger.info("   - get_enhanced_topics_by_language() [amélioré]")
logger.info("🚀 [Expert Utils] Système de clarification intelligent opérationnel !")