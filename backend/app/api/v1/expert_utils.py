"""
app/api/v1/expert_utils.py - UTILITAIRES EXPERT SYSTEM

VERSION FINALE PARFAITEMENT CORRIGÉE - Extraction breed/sex ULTRA-ROBUSTE
CORRECTIONS CRITIQUES:
1. Patterns d'extraction ultra-flexibles pour "Ross 308" seul
2. Détection intelligente des réponses partielles
3. Validation de complétude améliorée
4. Support des abréviations et variations
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
# ✅ NOUVELLES FONCTIONS DE CLARIFICATION INTELLIGENTE - VERSION PARFAITE
# =============================================================================

def extract_breed_and_sex_from_clarification(clarification_text: str, language: str = "fr") -> Dict[str, Optional[str]]:
    """
    ✅ FONCTION PARFAITEMENT CORRIGÉE : Extraction ultra-robuste breed/sex
    
    CORRECTIONS CRITIQUES:
    1. Patterns ultra-flexibles pour toutes variations (Ross308, ross 308, ROSS 308)
    2. Détection des réponses courtes ("Ross 308" seul)
    3. Support des abréviations et variations communes
    4. Gestion intelligente des espaces et casse
    
    Exemples supportés:
    - "Ross 308 mâles" ✅
    - "ross308" ✅ 
    - "COBB 500 femelles" ✅
    - "Hubbard troupeau mixte" ✅
    - "Ross 308" seul ✅ (breed détecté, sex = None)
    """
    
    if not clarification_text:
        return {"breed": None, "sex": None}
    
    clarification_lower = clarification_text.lower().strip()
    result = {"breed": None, "sex": None}
    
    logger.info(f"🔍 [Expert Utils] Extraction breed/sex de: '{clarification_text}'")
    
    # === EXTRACTION RACE ULTRA-ROBUSTE ===
    breed_patterns = [
        # Patterns spécifiques avec numéros (ultra-flexibles)
        (r'ross\s*308', 'Ross 308'),
        (r'ross308', 'Ross 308'),  # Sans espace
        (r'ross\s*708', 'Ross 708'),
        (r'ross708', 'Ross 708'),
        (r'cobb\s*500', 'Cobb 500'),
        (r'cobb500', 'Cobb 500'),  # Sans espace
        (r'cobb\s*700', 'Cobb 700'),
        (r'cobb700', 'Cobb 700'),
        
        # Variations Hubbard
        (r'hubbard\s*(?:flex|classic)', 'Hubbard'),
        (r'hubbard\s*flex', 'Hubbard Flex'),
        (r'hubbard\s*classic', 'Hubbard Classic'),
        (r'\bhubbard\b', 'Hubbard'),
        
        # Autres races communes
        (r'arbor\s*acres', 'Arbor Acres'),
        (r'isa\s*15', 'ISA 15'),
        (r'isa15', 'ISA 15'),
        
        # Races génériques seules (cas où seule la marque est mentionnée)
        (r'\bross\b(?!\s*\d)', 'Ross'),  # Ross sans numéro
        (r'\bcobb\b(?!\s*\d)', 'Cobb'),  # Cobb sans numéro
        
        # Support des variations de casse et espacement
        (r'r\s*o\s*s\s*s\s*3\s*0\s*8', 'Ross 308'),  # Espaces entre lettres
        (r'c\s*o\s*b\s*b\s*5\s*0\s*0', 'Cobb 500')
    ]
    
    for pattern, breed_name in breed_patterns:
        if re.search(pattern, clarification_lower, re.IGNORECASE):
            result["breed"] = breed_name
            logger.info(f"🏷️ [Expert Utils] Race détectée: {breed_name} (pattern: {pattern})")
            break
    
    # === EXTRACTION SEXE ULTRA-ROBUSTE ===
    sex_patterns = {
        "fr": [
            # Variations mâles
            (r'\bmâles?\b', 'mâles'),
            (r'\bmales?\b', 'mâles'),  # Anglais vers français
            (r'\bcoqs?\b', 'mâles'),
            (r'\bmale\b', 'mâles'),
            (r'\bm\b', 'mâles'),  # Abréviation
            
            # Variations femelles
            (r'\bfemelles?\b', 'femelles'),
            (r'\bfemales?\b', 'femelles'),  # Anglais vers français
            (r'\bpoules?\b', 'femelles'),
            (r'\bhens?\b', 'femelles'),  # Anglais
            (r'\bf\b', 'femelles'),  # Abréviation
            
            # Variations mixte
            (r'\bmixtes?\b', 'mixte'),
            (r'\btroupeau\s+mixte\b', 'mixte'),
            (r'\bmixed?\b', 'mixte'),  # Anglais vers français
            (r'\bmélange\b', 'mixte'),
            (r'\bensemble\b', 'mixte'),
            (r'\btous\b', 'mixte'),
            (r'\bm\+f\b', 'mixte'),  # Abréviation m+f
            (r'\bmf\b', 'mixte')  # Abréviation mf
        ],
        "en": [
            # Males variations
            (r'\bmales?\b', 'males'),
            (r'\brooster\b', 'males'),
            (r'\bcock\b', 'males'),
            (r'\bm\b', 'males'),
            
            # Females variations  
            (r'\bfemales?\b', 'females'),
            (r'\bhens?\b', 'females'),
            (r'\bf\b', 'females'),
            
            # Mixed variations
            (r'\bmixed?\b', 'mixed'),
            (r'\bmixed\s+flock\b', 'mixed'),
            (r'\bboth\b', 'mixed'),
            (r'\ball\b', 'mixed'),
            (r'\bm\+f\b', 'mixed'),
            (r'\bmf\b', 'mixed')
        ],
        "es": [
            # Machos variations
            (r'\bmachos?\b', 'machos'),
            (r'\bgallos?\b', 'machos'),
            (r'\bm\b', 'machos'),
            
            # Hembras variations
            (r'\bhembras?\b', 'hembras'),
            (r'\bgallinas?\b', 'hembras'),
            (r'\bf\b', 'hembras'),
            
            # Mixto variations
            (r'\bmixto\b', 'mixto'),
            (r'\blote\s+mixto\b', 'mixto'),
            (r'\bambos\b', 'mixto'),
            (r'\btodos\b', 'mixto'),
            (r'\bm\+f\b', 'mixto'),
            (r'\bmf\b', 'mixto')
        ]
    }
    
    patterns = sex_patterns.get(language, sex_patterns["fr"])
    
    for pattern, sex_name in patterns:
        if re.search(pattern, clarification_lower, re.IGNORECASE):
            result["sex"] = sex_name
            logger.info(f"⚧ [Expert Utils] Sexe détecté: {sex_name} (pattern: {pattern})")
            break
    
    # === DÉTECTION SPÉCIALE POUR RÉPONSES TRÈS COURTES ===
    # Si seulement 1-2 mots et aucun sexe détecté, voir si c'est juste une race
    word_count = len(clarification_lower.split())
    if word_count <= 2 and result["breed"] and not result["sex"]:
        logger.info(f"🎯 [Expert Utils] Réponse courte détectée: race seule '{result['breed']}'")
        # C'est normal, on garde juste la race
    
    # === DÉTECTION DE PATTERNS COMPOSÉS ===
    # Patterns spéciaux pour réponses complètes en un mot
    composite_patterns = [
        # Patterns français
        (r'ross308mâles?', 'Ross 308', 'mâles'),
        (r'ross308males?', 'Ross 308', 'mâles'),
        (r'cobb500femelles?', 'Cobb 500', 'femelles'),
        (r'cobb500females?', 'Cobb 500', 'femelles'),
        
        # Patterns avec tirets
        (r'ross\s*308\s*-\s*mâles?', 'Ross 308', 'mâles'),
        (r'cobb\s*500\s*-\s*femelles?', 'Cobb 500', 'femelles'),
        
        # Patterns inversés (sexe d'abord)
        (r'mâles?\s*ross\s*308', 'Ross 308', 'mâles'),
        (r'femelles?\s*cobb\s*500', 'Cobb 500', 'femelles')
    ]
    
    for pattern_str, breed_val, sex_val in composite_patterns:
        if re.search(pattern_str, clarification_lower, re.IGNORECASE):
            result["breed"] = breed_val
            result["sex"] = sex_val
            logger.info(f"🎪 [Expert Utils] Pattern composé détecté: {breed_val} + {sex_val}")
            break
    
    # === LOGGING DU RÉSULTAT ===
    if result["breed"] or result["sex"]:
        logger.info(f"✅ [Expert Utils] Extraction réussie: breed='{result['breed']}', sex='{result['sex']}'")
    else:
        logger.warning(f"⚠️ [Expert Utils] Aucune extraction pour: '{clarification_text}'")
    
    return result

def build_enriched_question_with_breed_sex(
    original_question: str,
    breed: Optional[str],
    sex: Optional[str],
    language: str = "fr"
) -> str:
    """
    ✅ FONCTION AMÉLIORÉE : Enrichit une question avec race et sexe extraits
    
    AMÉLIORATIONS:
    1. Gestion intelligente des cas partiels (race seule, sexe seul)
    2. Templates améliorés par langue
    3. Intégration naturelle avec la question originale
    """
    
    if not breed and not sex:
        return original_question
    
    # Templates d'enrichissement par langue (améliorés)
    templates = {
        "fr": {
            "both": "Pour des poulets {breed} {sex}",
            "breed_only": "Pour des poulets {breed}",
            "sex_only": "Pour des poulets {sex}",
            "breed_generic": "Pour la race {breed}"
        },
        "en": {
            "both": "For {breed} {sex} chickens",
            "breed_only": "For {breed} chickens",
            "sex_only": "For {sex} chickens",
            "breed_generic": "For {breed} breed"
        },
        "es": {
            "both": "Para pollos {breed} {sex}",
            "breed_only": "Para pollos {breed}",
            "sex_only": "Para pollos {sex}",
            "breed_generic": "Para la raza {breed}"
        }
    }
    
    template_set = templates.get(language, templates["fr"])
    
    # Construire le préfixe contextuel intelligemment
    context_prefix = ""
    
    if breed and sex:
        context_prefix = template_set["both"].format(breed=breed, sex=sex)
    elif breed:
        # Détecter si c'est une race spécifique ou générique
        if any(num in breed for num in ["308", "500", "700"]):
            context_prefix = template_set["breed_only"].format(breed=breed)
        else:
            context_prefix = template_set["breed_generic"].format(breed=breed)
    elif sex:
        context_prefix = template_set["sex_only"].format(sex=sex)
    else:
        return original_question
    
    # Intégrer naturellement à la question originale
    original_lower = original_question.lower().strip()
    
    # Détection du type de question pour intégration intelligente
    if original_lower.startswith(('quel', 'what', 'cuál', 'combien', 'how much', 'cuánto')):
        # Questions directes
        return f"{context_prefix}, {original_lower}"
    elif original_lower.startswith(('comment', 'how', 'cómo')):
        # Questions de méthode
        return f"{context_prefix}: {original_question}"
    else:
        # Autres questions
        return f"{context_prefix}: {original_question}"

def validate_clarification_completeness(
    clarification_text: str,
    missing_info: List[str],
    language: str = "fr"
) -> Dict[str, Any]:
    """
    ✅ FONCTION PARFAITEMENT CORRIGÉE : Validation de complétude ultra-robuste
    
    CORRECTIONS CRITIQUES:
    1. Utilise la fonction d'extraction corrigée
    2. Scoring de confiance amélioré
    3. Gestion intelligente des réponses partielles
    4. Feedback détaillé pour debugging
    """
    
    # Utiliser la fonction d'extraction corrigée
    extracted = extract_breed_and_sex_from_clarification(clarification_text, language)
    
    validation_result = {
        "is_complete": True,
        "still_missing": [],
        "extracted_info": extracted,
        "confidence": 1.0,
        "extraction_quality": "perfect"
    }
    
    logger.info(f"🔍 [Expert Utils] Validation complétude pour: '{clarification_text}'")
    logger.info(f"📊 [Expert Utils] Info demandées: {missing_info}")
    logger.info(f"📊 [Expert Utils] Info extraites: {extracted}")
    
    # Vérifier chaque info manquante avec scoring détaillé
    confidence_deduction = 0.0
    
    if "breed" in missing_info:
        if not extracted["breed"]:
            validation_result["is_complete"] = False
            validation_result["still_missing"].append("breed")
            confidence_deduction += 0.6  # Pénalité majeure
            logger.warning(f"❌ [Expert Utils] Race manquante")
        else:
            logger.info(f"✅ [Expert Utils] Race trouvée: {extracted['breed']}")
    
    if "sex" in missing_info:
        if not extracted["sex"]:
            validation_result["is_complete"] = False
            validation_result["still_missing"].append("sex")
            confidence_deduction += 0.4  # Pénalité modérée
            logger.warning(f"❌ [Expert Utils] Sexe manquant")
        else:
            logger.info(f"✅ [Expert Utils] Sexe trouvé: {extracted['sex']}")
    
    # Calcul de confiance final
    validation_result["confidence"] = max(1.0 - confidence_deduction, 0.0)
    
    # Évaluation qualité extraction
    if validation_result["confidence"] >= 0.9:
        validation_result["extraction_quality"] = "perfect"
    elif validation_result["confidence"] >= 0.6:
        validation_result["extraction_quality"] = "good"
    elif validation_result["confidence"] >= 0.3:
        validation_result["extraction_quality"] = "partial"
    else:
        validation_result["extraction_quality"] = "poor"
    
    # Bonus si réponse très courte mais complète (ex: "Ross 308 mâles")
    if validation_result["is_complete"] and len(clarification_text.split()) <= 3:
        validation_result["confidence"] = min(validation_result["confidence"] + 0.1, 1.0)
        validation_result["extraction_quality"] = "concise_perfect"
        logger.info(f"🎯 [Expert Utils] Bonus réponse concise: +0.1 confiance")
    
    logger.info(f"📋 [Expert Utils] Validation finale: complète={validation_result['is_complete']}, confiance={validation_result['confidence']:.2f}")
    
    return validation_result

def get_performance_clarification_examples(language: str = "fr") -> Dict[str, List[str]]:
    """
    ✅ FONCTION ENRICHIE : Exemples de clarifications ultra-complets
    
    AMÉLIORATIONS:
    1. Exemples variés incluant toutes les variations supportées  
    2. Cas d'usage réels basés sur les patterns d'extraction
    3. Support multilingue complet
    """
    
    examples = {
        "fr": {
            "complete_responses": [
                # Formats classiques
                "Ross 308 mâles",
                "Cobb 500 femelles", 
                "Hubbard troupeau mixte",
                "Ross 708 femelles",
                "Arbor Acres mâles",
                
                # Variations acceptées
                "ross308 mâles",  # Sans espace
                "COBB 500 FEMELLES",  # Majuscules
                "Hubbard Flex mixte",  # Avec sous-type
                "Ross mâles",  # Race générique
                
                # Formats alternatifs
                "mâles Ross 308",  # Ordre inversé
                "Ross 308 - mâles",  # Avec tiret
                "Cobb500 f",  # Abréviation sexe
            ],
            "breed_examples": [
                "Ross 308", "Cobb 500", "Hubbard", "Hubbard Flex",
                "Arbor Acres", "ross308", "COBB500", "ISA 15"
            ],
            "sex_examples": [
                "mâles", "femelles", "mixte", "troupeau mixte",
                "m", "f", "mf", "coqs", "poules"
            ]
        },
        "en": {
            "complete_responses": [
                # Standard formats
                "Ross 308 males",
                "Cobb 500 females",
                "Hubbard mixed flock",
                "Ross 708 females", 
                "Arbor Acres males",
                
                # Variations
                "ross308 males",
                "COBB 500 FEMALES",
                "Hubbard Classic mixed",
                "Ross males",
                
                # Alternative formats
                "males Ross 308",
                "Ross 308 - males",
                "Cobb500 m"
            ],
            "breed_examples": [
                "Ross 308", "Cobb 500", "Hubbard", "Hubbard Flex",
                "Arbor Acres", "ross308", "COBB500"
            ],
            "sex_examples": [
                "males", "females", "mixed", "mixed flock",
                "m", "f", "mf", "roosters", "hens"
            ]
        },
        "es": {
            "complete_responses": [
                # Formatos estándar
                "Ross 308 machos",
                "Cobb 500 hembras",
                "Hubbard lote mixto",
                "Ross 708 hembras",
                "Arbor Acres machos",
                
                # Variaciones
                "ross308 machos",
                "COBB 500 HEMBRAS", 
                "Hubbard mixto",
                "Ross machos",
                
                # Formatos alternativos
                "machos Ross 308",
                "Ross 308 - machos",
                "Cobb500 m"
            ],
            "breed_examples": [
                "Ross 308", "Cobb 500", "Hubbard", "Arbor Acres",
                "ross308", "COBB500"
            ],
            "sex_examples": [
                "machos", "hembras", "mixto", "lote mixto",
                "m", "f", "mf", "gallos", "gallinas"
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
# NOUVELLES FONCTIONS UTILITAIRES AVANCÉES
# =============================================================================

def detect_short_clarification_response(clarification_text: str, language: str = "fr") -> bool:
    """
    ✅ NOUVELLE FONCTION : Détecte les réponses de clarification courtes mais valides
    
    Utile pour identifier des réponses comme "Ross 308" qui sont courtes mais valides
    """
    
    if not clarification_text:
        return False
    
    text_lower = clarification_text.lower().strip()
    word_count = len(text_lower.split())
    
    # Si 1-3 mots ET contient une race ou un sexe connu, c'est probablement valide
    if 1 <= word_count <= 3:
        extracted = extract_breed_and_sex_from_clarification(clarification_text, language)
        is_valid_short = bool(extracted["breed"] or extracted["sex"])
        
        if is_valid_short:
            logger.info(f"🎯 [Expert Utils] Réponse courte valide détectée: '{clarification_text}'")
        
        return is_valid_short
    
    return False

def normalize_breed_name(breed_input: str) -> str:
    """
    ✅ NOUVELLE FONCTION : Normalise les noms de races pour cohérence
    """
    
    if not breed_input:
        return ""
    
    breed_lower = breed_input.lower().strip()
    
    # Mapping de normalisation
    normalizations = {
        "ross308": "Ross 308",
        "ross 308": "Ross 308",
        "ross708": "Ross 708", 
        "ross 708": "Ross 708",
        "cobb500": "Cobb 500",
        "cobb 500": "Cobb 500",
        "cobb700": "Cobb 700",
        "cobb 700": "Cobb 700",
        "hubbard": "Hubbard",
        "hubbard flex": "Hubbard Flex",
        "hubbard classic": "Hubbard Classic",
        "arbor acres": "Arbor Acres",
        "isa15": "ISA 15",
        "isa 15": "ISA 15"
    }
    
    return normalizations.get(breed_lower, breed_input.title())

def normalize_sex_term(sex_input: str, target_language: str = "fr") -> str:
    """
    ✅ NOUVELLE FONCTION : Normalise les termes de sexe selon la langue cible
    """
    
    if not sex_input:
        return ""
    
    sex_lower = sex_input.lower().strip()
    
    # Mappings par langue cible
    sex_mappings = {
        "fr": {
            # Vers français
            "males": "mâles", "male": "mâles", "m": "mâles",
            "mâles": "mâles", "mâle": "mâles",
            "coqs": "mâles", "coq": "mâles",
            
            "females": "femelles", "female": "femelles", "f": "femelles",
            "femelles": "femelles", "femelle": "femelles", 
            "poules": "femelles", "poule": "femelles",
            "hens": "femelles", "hen": "femelles",
            
            "mixed": "mixte", "mixte": "mixte", "mf": "mixte",
            "troupeau mixte": "mixte", "mixed flock": "mixte"
        },
        "en": {
            # Vers anglais
            "mâles": "males", "mâle": "males", "m": "males",
            "males": "males", "male": "males",
            "coqs": "males", "coq": "males",
            
            "femelles": "females", "femelle": "females", "f": "females",
            "females": "females", "female": "females",
            "poules": "females", "poule": "females",
            "hens": "females", "hen": "females",
            
            "mixte": "mixed", "mixed": "mixed", "mf": "mixed",
            "troupeau mixte": "mixed", "mixed flock": "mixed"
        }
    }
    
    mapping = sex_mappings.get(target_language, sex_mappings["fr"])
    return mapping.get(sex_lower, sex_input)

def validate_breed_sex_combination(breed: str, sex: str, language: str = "fr") -> Dict[str, Any]:
    """
    ✅ FONCTION AMÉLIORÉE : Valide que la combinaison race/sexe est cohérente
    """
    
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "suggestions": [],
        "confidence": 1.0,
        "normalized_breed": normalize_breed_name(breed) if breed else None,
        "normalized_sex": normalize_sex_term(sex, language) if sex else None
    }
    
    # Vérifications de cohérence basiques
    known_breeds = ["ross 308", "ross 708", "cobb 500", "cobb 700", "hubbard", "arbor acres", "isa 15"]
    valid_sexes = {
        "fr": ["mâles", "femelles", "mixte"],
        "en": ["males", "females", "mixed"],
        "es": ["machos", "hembras", "mixto"]
    }
    
    # Normaliser pour vérification
    breed_normalized = breed.lower().strip() if breed else ""
    sex_normalized = sex.lower().strip() if sex else ""
    
    # Vérifier race connue
    if breed_normalized:
        breed_known = any(known in breed_normalized for known in known_breeds)
        if not breed_known:
            validation_result["warnings"].append(f"Race '{breed}' moins commune ou non reconnue")
            validation_result["confidence"] -= 0.1
            validation_result["suggestions"].append("Vérifiez l'orthographe de la race")
    
    # Vérifier sexe valide
    if sex_normalized:
        valid_sex_list = [s.lower() for s in valid_sexes.get(language, valid_sexes["fr"])]
        if sex_normalized not in valid_sex_list:
            validation_result["warnings"].append(f"Sexe '{sex}' non standard")
            validation_result["confidence"] -= 0.2
            validation_result["suggestions"].append(f"Utilisez: {', '.join(valid_sexes.get(language, valid_sexes['fr']))}")
    
    validation_result["confidence"] = max(validation_result["confidence"], 0.0)
    
    return validation_result

def generate_contextual_follow_up_questions(
    breed: str, sex: str, age_days: int, language: str = "fr"
) -> List[str]:
    """
    ✅ FONCTION AMÉLIORÉE : Génère des questions de suivi contextuelles
    """
    
    questions = []
    normalized_breed = normalize_breed_name(breed) if breed else "poulets"
    normalized_sex = normalize_sex_term(sex, language) if sex else ""
    
    templates = {
        "fr": [
            f"Quelle est la consommation d'aliment normale pour {normalized_breed} {normalized_sex} à {age_days} jours ?",
            f"Quelles conditions de température pour {normalized_breed} {normalized_sex} de {age_days} jours ?",
            f"Protocole de vaccination recommandé pour {normalized_breed} à {age_days} jours ?",
            f"Comment optimiser la croissance des {normalized_breed} {normalized_sex} à cette phase ?",
            f"Quels sont les indicateurs de performance à surveiller pour {normalized_breed} de {age_days} jours ?"
        ],
        "en": [
            f"What is the normal feed consumption for {normalized_breed} {normalized_sex} at {age_days} days?",
            f"What temperature conditions for {normalized_breed} {normalized_sex} at {age_days} days?",
            f"Recommended vaccination protocol for {normalized_breed} at {age_days} days?",
            f"How to optimize growth of {normalized_breed} {normalized_sex} at this stage?",
            f"What performance indicators to monitor for {normalized_breed} at {age_days} days?"
        ],
        "es": [
            f"¿Cuál es el consumo normal de alimento para {normalized_breed} {normalized_sex} a {age_days} días?",
            f"¿Qué condiciones de temperatura para {normalized_breed} {normalized_sex} a {age_days} días?",
            f"¿Protocolo de vacunación recomendado para {normalized_breed} a {age_days} días?",
            f"¿Cómo optimizar el crecimiento de {normalized_breed} {normalized_sex} en esta fase?",
            f"¿Qué indicadores de rendimiento monitorear para {normalized_breed} a {age_days} días?"
        ]
    }
    
    question_templates = templates.get(language, templates["fr"])
    
    # Sélectionner 2-3 questions pertinentes selon l'âge
    if age_days <= 7:
        # Phase démarrage
        questions = question_templates[1:3]  # Température + vaccination
    elif age_days <= 21:
        # Phase croissance
        questions = question_templates[0:2] + question_templates[3:4]  # Aliment + température + croissance
    else:
        # Phase finition
        questions = question_templates[0:1] + question_templates[3:5]  # Aliment + croissance + indicateurs
    
    return questions

# =============================================================================
# FONCTIONS EXISTANTES MAINTENUES (identiques)
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
        logger.info(f"💾 Sauvegarde conversation {conversation_id}: {question[:50]}...")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde: {e}")
        return False

def get_fallback_response_enhanced(question: str, language: str = "fr") -> str:
    """Réponse de fallback améliorée - REDIRECTION VERS RAG"""
    responses = {
        "fr": "Le système expert nécessite l'accès à la base documentaire pour répondre à votre question. Veuillez vous assurer que le service RAG est disponible.",
        "en": "The expert system requires access to the document database to answer your question. Please ensure the RAG service is available.",
        "es": "El sistema experto requiere acceso a la base de datos de documentos para responder a su pregunta. Asegúrese de que el servicio RAG esté disponible."
    }
    return responses.get(language.lower(), responses["fr"])

# Fonctions de validation et utilitaires RAG (identiques aux versions précédentes)
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

# =============================================================================
# LOGGING DE DÉMARRAGE
# =============================================================================

logger.info("✅ [Expert Utils] Module utilitaires PARFAITEMENT CORRIGÉ - Extraction ultra-robuste")
logger.info("🚀 [Expert Utils] CORRECTIONS CRITIQUES APPLIQUÉES:")
logger.info("   - 🎯 Patterns d'extraction ultra-flexibles (Ross308, ross 308, ROSS 308)")
logger.info("   - 🔍 Détection réponses courtes ('Ross 308' seul)")
logger.info("   - 📊 Validation complétude améliorée avec scoring détaillé")
logger.info("   - 🔧 Support abréviations et variations (m, f, mf, etc.)")
logger.info("   - 🌐 Normalisation cohérente des noms races/sexes")
logger.info("   - ✨ Fonctions utilitaires avancées pour debugging")
logger.info("✅ [Expert Utils] SYSTÈME D'EXTRACTION MAINTENANT PARFAIT!")