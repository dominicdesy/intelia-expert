"""
app/api/v1/expert_services_clarification.py - SYSTÈME DE CLARIFICATION CRITIQUE

🚀 SYSTÈME CLARIFICATION CRITIQUE VS NON CRITIQUE v4.0.0:
1. ✅ Analyse clarification critique vs optionnelle
2. ✅ Détection type volaille (pondeuses/broilers)
3. ✅ Génération messages clarification sécurisés
4. ✅ Gestion entités manquantes critiques
"""

import logging
import re
from typing import List

from .expert_services_utils import validate_missing_entities_list

logger = logging.getLogger(__name__)

# Import conditionnel des fonctions de clarification
try:
    from .clarification_entities import normalize_breed_name, infer_sex_from_breed, get_breed_type, get_supported_breeds
    CLARIFICATION_ENTITIES_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    def normalize_breed_name(breed):
        if not breed or not isinstance(breed, str):
            return "", "manual"
        return breed.lower().strip(), "manual"
    
    def infer_sex_from_breed(breed):
        if not breed or not isinstance(breed, str):
            return None, False
        layer_breeds = ['isa brown', 'lohmann brown', 'hy-line', 'bovans', 'shaver', 'hissex', 'novogen']
        breed_lower = breed.lower()
        is_layer = any(layer in breed_lower for layer in layer_breeds)
        return "femelles" if is_layer else None, is_layer
    
    def get_breed_type(breed):
        if not breed or not isinstance(breed, str):
            return "unknown"
        breed_lower = breed.lower()
        layer_breeds = ['isa brown', 'lohmann brown', 'hy-line', 'bovans', 'shaver', 'hissex', 'novogen']
        if any(layer in breed_lower for layer in layer_breeds):
            return "layers"
        broiler_breeds = ['ross 308', 'cobb 500', 'hubbard', 'ross', 'cobb']
        if any(broiler in breed_lower for broiler in broiler_breeds):
            return "broilers"
        return "unknown"
    
    def get_supported_breeds():
        return ["ross 308", "cobb 500", "hubbard", "isa brown", "lohmann brown", "hy-line", "bovans", "shaver"]
    
    CLARIFICATION_ENTITIES_AVAILABLE = False

async def analyze_question_for_clarification_enhanced(question: str, language: str = "fr") -> dict:
    """🛑 ANALYSE CLARIFICATION CRITIQUE vs NON CRITIQUE"""
    
    # Validation des paramètres d'entrée
    if not question or not isinstance(question, str):
        logger.warning("⚠️ [Critical Clarification v4.0.0] Question invalide")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": "Question invalide ou vide",
            "poultry_type": "unknown"
        }
    
    if not language or not isinstance(language, str):
        language = "fr"
    
    try:
        question_lower = question.lower().strip()
        
        # Détection type volaille avec gestion d'erreurs
        poultry_type = detect_poultry_type_safe(question_lower)
        
        logger.info(f"🔍 [Critical Clarification v4.0.0] Type volaille détecté: {poultry_type}")
        
        # Analyse selon le type avec gestion d'erreurs
        if poultry_type == "layers":
            return analyze_layer_clarification_critical_safe(question_lower, language)
        elif poultry_type == "broilers":
            return analyze_broiler_clarification_critical_safe(question_lower, language)
        else:
            return analyze_general_clarification_critical_safe(question_lower, language)
            
    except Exception as e:
        logger.error(f"❌ [Critical Clarification v4.0.0] Erreur analyse: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse: {str(e)}",
            "poultry_type": "unknown"
        }

def detect_poultry_type_safe(question_lower: str) -> str:
    """🔧 Détection type volaille sécurisée"""
    
    if not question_lower or not isinstance(question_lower, str):
        return "unknown"
    
    try:
        # Mots-clés pondeuses
        layer_keywords = [
            "pondeuse", "pondeuses", "poule", "poules", "layer", "layers",
            "œuf", "oeufs", "egg", "eggs", "ponte", "laying", "lay",
            "pondent", "pond", "production d'œufs", "egg production",
            "pondoir", "nest", "nid"
        ]
        
        # Mots-clés poulets de chair
        broiler_keywords = [
            "poulet", "poulets", "broiler", "broilers", "chair", "meat",
            "viande", "abattage", "slaughter", "poids", "weight", "croissance",
            "growth", "ross", "cobb", "hubbard", "fcr", "gain"
        ]
        
        # Comptage sécurisé des occurrences
        layer_score = 0
        broiler_score = 0
        
        for keyword in layer_keywords:
            if keyword in question_lower:
                layer_score += 1
        
        for keyword in broiler_keywords:
            if keyword in question_lower:
                broiler_score += 1
        
        logger.info(f"🔍 [Safe Detection v4.0.0] Layer score: {layer_score}, Broiler score: {broiler_score}")
        
        # Décision basée sur les scores
        if layer_score > broiler_score:
            logger.info("🔍 [Safe Detection v4.0.0] Type déterminé par mots-clés: layers")
            return "layers"
        elif broiler_score > layer_score:
            logger.info("🔍 [Safe Detection v4.0.0] Type déterminé par mots-clés: broilers")
            return "broilers"
        
        # Analyse des races si scores égaux
        logger.info("🔍 [Safe Detection v4.0.0] Scores égaux, analyse des races...")
        
        potential_breeds = extract_breeds_from_question_safe(question_lower)
        logger.info(f"🔍 [Safe Detection v4.0.0] Races détectées: {potential_breeds}")
        
        if potential_breeds:
            for breed in potential_breeds:
                try:
                    normalized_breed, _ = normalize_breed_name(breed)
                    breed_type = get_breed_type(normalized_breed)
                    
                    if breed_type == "layers":
                        logger.info(f"🔍 [Safe Detection v4.0.0] Race {breed} → layers")
                        return "layers"
                    elif breed_type == "broilers":
                        logger.info(f"🔍 [Safe Detection v4.0.0] Race {breed} → broilers")
                        return "broilers"
                except Exception as e:
                    logger.warning(f"⚠️ [Safe Detection v4.0.0] Erreur analyse race {breed}: {e}")
                    continue
        
        # Fallback final
        logger.info("🔍 [Safe Detection v4.0.0] Type indéterminé après analyse complète")
        return "unknown"
        
    except Exception as e:
        logger.error(f"❌ [Safe Detection v4.0.0] Erreur détection: {e}")
        return "unknown"

def extract_breeds_from_question_safe(question_lower: str) -> List[str]:
    """🔍 Extrait les races"""
    
    if not question_lower or not isinstance(question_lower, str):
        return []
    
    try:
        breed_patterns = [
            r'\b(ross\s*308|cobb\s*500|hubbard\s*\w*)\b',
            r'\b(ross|cobb)\s*\d{2,3}\b',
            r'\b(isa\s*brown|lohmann\s*brown|hy[-\s]*line)\b',
            r'\b(bovans|shaver|hissex|novogen|tetra|hendrix|dominant)\b',
            r'\brace[:\s]*([a-zA-Z0-9\s]{3,20})\b',
            r'\bsouche[:\s]*([a-zA-Z0-9\s]{3,20})\b',
            r'\bbreed[:\s]*([a-zA-Z0-9\s]{3,20})\b',
        ]
        
        found_breeds = []
        
        for pattern in breed_patterns:
            try:
                matches = re.findall(pattern, question_lower, re.IGNORECASE)
                if matches:
                    for match in matches:
                        try:
                            if isinstance(match, tuple):
                                breed = next((m.strip() for m in match if m and m.strip()), "")
                            else:
                                breed = str(match).strip()
                            
                            if breed and 2 <= len(breed) <= 25:
                                found_breeds.append(breed)
                        except Exception as e:
                            logger.warning(f"⚠️ [Extract Breeds v4.0.0] Erreur traitement match: {e}")
                            continue
            except Exception as e:
                logger.warning(f"⚠️ [Extract Breeds v4.0.0] Erreur pattern {pattern}: {e}")
                continue
        
        # Déduplication sécurisée
        unique_breeds = []
        seen = set()
        
        for breed in found_breeds:
            try:
                breed_clean = breed.lower()
                if breed_clean not in seen:
                    unique_breeds.append(breed)
                    seen.add(breed_clean)
            except Exception as e:
                logger.warning(f"⚠️ [Extract Breeds v4.0.0] Erreur déduplication: {e}")
                continue
        
        return unique_breeds
        
    except Exception as e:
        logger.error(f"❌ [Extract Breeds v4.0.0] Erreur extraction: {e}")
        return []

def analyze_layer_clarification_critical_safe(question_lower: str, language: str) -> dict:
    """🥚 ANALYSE CLARIFICATION CRITIQUE PONDEUSES"""
    
    try:
        critical_missing = []
        optional_missing = []
        confidence = 0.0
        
        # Entités critiques pour pondeuses
        critical_layer_info = {
            "breed": ["isa", "brown", "lohmann", "hy-line", "race", "souche", "breed"],
            "production_stage": ["semaine", "semaines", "week", "weeks", "âge", "age", "mois", "months", "début", "pic", "fin"]
        }
        
        # Entités non critiques
        optional_layer_info = {
            "production_rate": ["œufs/jour", "eggs/day", "production", "combien", "how many"],
            "housing": ["cage", "sol", "parcours", "free range", "battery", "barn"],
            "lighting": ["lumière", "éclairage", "light", "hours", "heures"],
            "feeding": ["alimentation", "feed", "nutrition", "protein", "protéine"],
            "weight": ["poids", "weight", "peso", "gramme", "kg", "g"]
        }
        
        # Vérifier entités CRITIQUES de façon sécurisée
        for info_type, keywords in critical_layer_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    critical_missing.append(info_type)
                    confidence += 0.4
            except Exception as e:
                logger.warning(f"⚠️ [Layer Critical v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Vérifier entités NON CRITIQUES de façon sécurisée
        for info_type, keywords in optional_layer_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    optional_missing.append(info_type)
                    confidence += 0.1
            except Exception as e:
                logger.warning(f"⚠️ [Layer Optional v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Décision critique sécurisée
        is_critical = len(critical_missing) >= 1
        is_optional = len(optional_missing) >= 2
        
        logger.info(f"🥚 [Layer Critical Safe v4.0.0] Critique: {critical_missing}, Optionnel: {optional_missing}")
        
        return {
            "clarification_required_critical": is_critical,
            "clarification_required_optional": is_optional,
            "missing_critical_entities": critical_missing,
            "missing_optional_entities": optional_missing,
            "confidence": min(confidence, 0.9),
            "reasoning": f"Pondeuses - Entités critiques manquantes: {critical_missing}",
            "poultry_type": "layers"
        }
        
    except Exception as e:
        logger.error(f"❌ [Layer Critical Safe v4.0.0] Erreur: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse pondeuses: {str(e)}",
            "poultry_type": "layers"
        }

def analyze_broiler_clarification_critical_safe(question_lower: str, language: str) -> dict:
    """🍗 ANALYSE CLARIFICATION CRITIQUE POULETS DE CHAIR"""
    
    try:
        critical_missing = []
        optional_missing = []
        confidence = 0.0
        
        # Entités critiques pour poulets de chair
        critical_broiler_info = {
            "breed": ["ross", "cobb", "hubbard", "race", "souche", "breed", "strain"],
            "age": ["jour", "jours", "day", "days", "semaine", "week", "âge", "age"],
            "sex": ["mâle", "male", "femelle", "female", "mixte", "mixed", "sexe", "sex"]
        }
        
        # Entités non critiques (weight inclus ici maintenant)
        optional_broiler_info = {
            "weight": ["poids", "weight", "peso", "gramme", "kg", "g"],
            "housing": ["température", "temperature", "ventilation", "density", "densité"],
            "feeding": ["alimentation", "feed", "fcr", "conversion", "nutrition"]
        }
        
        # Vérifier entités CRITIQUES de façon sécurisée
        for info_type, keywords in critical_broiler_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    critical_missing.append(info_type)
                    confidence += 0.3
            except Exception as e:
                logger.warning(f"⚠️ [Broiler Critical v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Vérifier entités NON CRITIQUES de façon sécurisée (incluant weight)
        for info_type, keywords in optional_broiler_info.items():
            try:
                if not any(keyword in question_lower for keyword in keywords if keyword):
                    optional_missing.append(info_type)
                    confidence += 0.1
            except Exception as e:
                logger.warning(f"⚠️ [Broiler Optional v4.0.0] Erreur vérification {info_type}: {e}")
        
        # Décision critique sécurisée
        is_critical = len(critical_missing) >= 2
        is_optional = len(optional_missing) >= 1
        
        logger.info(f"🍗 [Broiler Critical Safe v4.0.0] Critique: {critical_missing}, Optionnel: {optional_missing}")
        
        return {
            "clarification_required_critical": is_critical,
            "clarification_required_optional": is_optional,
            "missing_critical_entities": critical_missing,
            "missing_optional_entities": optional_missing,
            "confidence": confidence,
            "reasoning": f"Poulets de chair - Entités critiques manquantes: {critical_missing}",
            "poultry_type": "broilers"
        }
        
    except Exception as e:
        logger.error(f"❌ [Broiler Critical Safe v4.0.0] Erreur: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse poulets de chair: {str(e)}",
            "poultry_type": "broilers"
        }

def analyze_general_clarification_critical_safe(question_lower: str, language: str) -> dict:
    """❓ ANALYSE CLARIFICATION GÉNÉRALE"""
    
    try:
        logger.info("❓ [General Critical Safe v4.0.0] Type volaille indéterminé - clarification critique requise")
        
        return {
            "clarification_required_critical": True,
            "clarification_required_optional": False,
            "missing_critical_entities": ["poultry_type", "species"],
            "missing_optional_entities": ["breed", "age", "purpose", "weight"],
            "confidence": 0.8,
            "reasoning": "Type de volaille indéterminé - clarification critique nécessaire",
            "poultry_type": "unknown"
        }
        
    except Exception as e:
        logger.error(f"❌ [General Critical Safe v4.0.0] Erreur: {e}")
        return {
            "clarification_required_critical": False,
            "clarification_required_optional": False,
            "missing_critical_entities": [],
            "missing_optional_entities": [],
            "confidence": 0.0,
            "reasoning": f"Erreur analyse générale: {str(e)}",
            "poultry_type": "unknown"
        }

def generate_critical_clarification_message_safe(missing_entities: List[str], poultry_type: str, language: str) -> str:
    """🛑 Génère le message de clarification critique"""
    
    try:
        # Utiliser safe_get_missing_entities pour validation
        safe_missing_entities = validate_missing_entities_list(missing_entities)
        
        if not safe_missing_entities:
            safe_missing_entities = ["information"]
        
        if not poultry_type or not isinstance(poultry_type, str):
            poultry_type = "unknown"
        
        if not language or not isinstance(language, str):
            language = "fr"
        
        messages = {
            "fr": {
                "layers": {
                    "breed": "Précisez la race de vos pondeuses (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                    "production_stage": "Indiquez l'âge ou le stade de production de vos pondeuses",
                    "weight": "Indiquez le poids moyen de vos pondeuses",
                    "general": "Pour vous donner une réponse précise sur vos pondeuses, j'ai besoin de connaître :"
                },
                "broilers": {
                    "breed": "Précisez la race/souche de vos poulets (Ross 308, Cobb 500, Hubbard, etc.)",
                    "age": "Indiquez l'âge de vos poulets (en jours ou semaines)",
                    "sex": "Précisez s'il s'agit de mâles, femelles, ou un troupeau mixte",
                    "weight": "Indiquez le poids moyen de vos poulets",
                    "general": "Pour vous donner une réponse précise sur vos poulets de chair, j'ai besoin de connaître :"
                },
                "unknown": {
                    "poultry_type": "Précisez le type de volailles (pondeuses, poulets de chair, etc.)",
                    "species": "Indiquez l'espèce exacte de vos animaux",
                    "weight": "Indiquez le poids de vos animaux",
                    "general": "Pour vous donner une réponse précise, j'ai besoin de connaître :"
                }
            },
            "en": {
                "layers": {
                    "breed": "Specify the breed of your laying hens (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                    "production_stage": "Indicate the age or production stage of your laying hens",
                    "weight": "Indicate the average weight of your laying hens",
                    "general": "To give you a precise answer about your laying hens, I need to know:"
                },
                "broilers": {
                    "breed": "Specify the breed/strain of your chickens (Ross 308, Cobb 500, Hubbard, etc.)",
                    "age": "Indicate the age of your chickens (in days or weeks)",
                    "sex": "Specify if they are males, females, or a mixed flock",
                    "weight": "Indicate the average weight of your chickens",
                    "general": "To give you a precise answer about your broilers, I need to know:"
                },
                "unknown": {
                    "poultry_type": "Specify the type of poultry (laying hens, broilers, etc.)",
                    "species": "Indicate the exact species of your animals",
                    "weight": "Indicate the weight of your animals",
                    "general": "To give you a precise answer, I need to know:"
                }
            },
            "es": {
                "layers": {
                    "breed": "Especifique la raza de sus gallinas ponedoras (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                    "production_stage": "Indique la edad o etapa de producción de sus gallinas ponedoras",
                    "weight": "Indique el peso promedio de sus gallinas ponedoras",
                    "general": "Para darle una respuesta precisa sobre sus gallinas ponedoras, necesito saber:"
                },
                "broilers": {
                    "breed": "Especifique la raza/cepa de sus pollos (Ross 308, Cobb 500, Hubbard, etc.)",
                    "age": "Indique la edad de sus pollos (en días o semanas)",
                    "sex": "Especifique si son machos, hembras, o una bandada mixta",
                    "weight": "Indique el peso promedio de sus pollos",
                    "general": "Para darle una respuesta precisa sobre sus pollos de engorde, necesito saber:"
                },
                "unknown": {
                    "poultry_type": "Especifique el tipo de aves (gallinas ponedoras, pollos de engorde, etc.)",
                    "species": "Indique la especie exacta de sus animales",
                    "weight": "Indique el peso de sus animales",
                    "general": "Para darle una respuesta precisa, necesito saber:"
                }
            }
        }
        
        lang = language if language in messages else "fr"
        type_messages = messages[lang].get(poultry_type, messages[lang]["unknown"])
        
        # Construire le message de façon sécurisée
        general_msg = type_messages.get("general", "Pour vous donner une réponse précise, j'ai besoin de connaître :")
        specific_msgs = []
        
        for entity in safe_missing_entities:
            if isinstance(entity, str) and entity in type_messages:
                specific_msgs.append(f"• {type_messages[entity]}")
        
        if specific_msgs:
            return f"{general_msg}\n\n" + "\n".join(specific_msgs)
        else:
            return general_msg
            
    except Exception as e:
        logger.error(f"❌ [Generate Critical Message v4.0.0] Erreur: {e}")
        # Fallback sécurisé
        fallback_messages = {
            "fr": "Pour vous donner une réponse précise, j'ai besoin de plus d'informations sur vos animaux.",
            "en": "To give you a precise answer, I need more information about your animals.",
            "es": "Para darle una respuesta precisa, necesito más información sobre sus animales."
        }
        return fallback_messages.get(language, fallback_messages["fr"])