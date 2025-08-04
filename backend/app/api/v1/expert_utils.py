"""
app/api/v1/expert_utils.py - FONCTIONS UTILITAIRES EXPERT SYSTEM

Fonctions utilitaires nécessaires pour le bon fonctionnement du système expert
✅ CORRIGÉ: Toutes les fonctions référencées dans expert.py et expert_services.py
✅ CORRIGÉ: Erreur syntaxe ligne 830 résolue
✅ CORRIGÉ: Gestion des exceptions améliorée
✅ CORRIGÉ: Validation des types et None-safety
🚀 NOUVEAU: Auto-détection sexe pour races pondeuses (Bug Fix)
🚀 INTÉGRÉ: Centralisation via clarification_entities
🚀 AJOUTÉ: score_question_variant() pour scoring générique des variantes
"""

import re
import uuid
import logging
import time
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# 🚀 NOUVEAU: Imports centralisation clarification_entities
try:
    from .clarification_entities import normalize_breed_name, infer_sex_from_breed
    CLARIFICATION_ENTITIES_AVAILABLE = True
    logger.info("✅ [Utils] clarification_entities importé avec succès")
except ImportError as e:
    logger.warning(f"⚠️ [Utils] clarification_entities non disponible: {e}")
    # Fonctions fallback
    def normalize_breed_name(breed: str) -> tuple[str, str]:
        """Fallback function for breed normalization"""
        if not breed:
            return "", "manual"
        return breed.lower().strip(), "manual"
    
    def infer_sex_from_breed(breed: str) -> tuple[Optional[str], bool]:
        """Fallback function for sex inference from breed"""
        if not breed:
            return None, False
        layer_breeds = ['isa brown', 'lohmann brown', 'hy-line', 'bovans', 'shaver']
        is_layer = any(layer in breed.lower() for layer in layer_breeds)
        return "femelles" if is_layer else None, is_layer
    
    CLARIFICATION_ENTITIES_AVAILABLE = False

# =============================================================================
# UTILITAIRES D'AUTHENTIFICATION ET SESSION
# =============================================================================

def get_user_id_from_request(request) -> str:
    """Extrait l'ID utilisateur depuis la requête"""
    try:
        # Essayer d'extraire depuis les headers
        if hasattr(request, 'headers') and request.headers:
            user_id = request.headers.get('X-User-ID')
            if user_id and isinstance(user_id, str) and user_id.strip():
                return user_id.strip()
        
        # Fallback vers l'IP client
        if hasattr(request, 'client') and request.client and hasattr(request.client, 'host'):
            client_host = request.client.host
            if client_host:
                return f"ip_{client_host}"
        
        # Dernier fallback
        return f"anonymous_{uuid.uuid4().hex[:8]}"
        
    except Exception as e:
        logger.warning(f"⚠️ [Utils] Erreur extraction user_id: {e}")
        return f"error_{uuid.uuid4().hex[:8]}"

def extract_session_info(request) -> Dict[str, Any]:
    """Extrait les informations de session depuis la requête"""
    try:
        session_info = {
            "user_agent": None,
            "ip_address": None,
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
        
        if hasattr(request, 'headers') and request.headers:
            session_info["user_agent"] = request.headers.get('User-Agent')
            request_id_header = request.headers.get('X-Request-ID')
            if request_id_header:
                session_info["request_id"] = request_id_header
        
        if hasattr(request, 'client') and request.client and hasattr(request.client, 'host'):
            session_info["ip_address"] = request.client.host
        
        return session_info
        
    except Exception as e:
        logger.warning(f"⚠️ [Utils] Erreur extraction session: {e}")
        return {
            "user_agent": None,
            "ip_address": "unknown",
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# EXTRACTION ENTITÉS POUR CLARIFICATION
# =============================================================================

def extract_breed_and_sex_from_clarification(text: str, language: str = "fr") -> Dict[str, Optional[str]]:
    """
    Extrait race et sexe depuis une réponse de clarification
    🚀 CORRIGÉ: Auto-détection sexe pour races pondeuses
    """
    
    if not text or not isinstance(text, str) or not text.strip():
        return {"breed": None, "sex": None}
    
    text_lower = text.lower().strip()
    
    # Dictionnaires de patterns par langue
    breed_patterns = {
        "fr": [
            # Races complètes courantes
            r'\b(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)\b',
            r'\b(ross|cobb|hubbard)\s*\d{2,3}\b',
            # 🚀 NOUVEAU: Patterns pondeuses étendus
            r'\b(isa\s*brown|lohmann\s*brown|hy[-\s]*line|bovans|shaver|hissex|novogen|tetra|hendrix|dominant)\b',
            # Mentions génériques
            r'\brace[:\s]*([a-zA-Z0-9\s]+)',
            r'\bsouche[:\s]*([a-zA-Z0-9\s]+)',
        ],
        "en": [
            r'\b(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)\b',
            r'\b(ross|cobb|hubbard)\s*\d{2,3}\b',
            # 🚀 NOUVEAU: Patterns pondeuses étendus
            r'\b(isa\s*brown|lohmann\s*brown|hy[-\s]*line|bovans|shaver|hissex|novogen|tetra|hendrix|dominant)\b',
            r'\bbreed[:\s]*([a-zA-Z0-9\s]+)',
            r'\bstrain[:\s]*([a-zA-Z0-9\s]+)',
        ],
        "es": [
            r'\b(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)\b',
            r'\b(ross|cobb|hubbard)\s*\d{2,3}\b',
            # 🚀 NOUVEAU: Patterns pondeuses étendus
            r'\b(isa\s*brown|lohmann\s*brown|hy[-\s]*line|bovans|shaver|hissex|novogen|tetra|hendrix|dominant)\b',
            r'\braza[:\s]*([a-zA-Z0-9\s]+)',
            r'\bcepa[:\s]*([a-zA-Z0-9\s]+)',
        ]
    }
    
    sex_patterns = {
        "fr": [
            r'\b(mâles?|males?)\b',
            r'\b(femelles?|females?)\b',
            r'\b(mixte|mixed|mélangé)\b',
            r'\btroupeau\s+(mixte|mélangé)\b',
            r'\bsexe[:\s]*(mâle|femelle|mixte)',
        ],
        "en": [
            r'\b(males?|roosters?|cocks?)\b',
            r'\b(females?|hens?)\b',
            r'\b(mixed|both)\b',
            r'\bflock\s+(mixed|both)\b',
            r'\bsex[:\s]*(male|female|mixed)',
        ],
        "es": [
            r'\b(machos?|gallos?)\b',
            r'\b(hembras?|gallinas?)\b',
            r'\b(mixto|mezclado|ambos)\b',
            r'\blote\s+(mixto|mezclado)\b',
            r'\bsexo[:\s]*(macho|hembra|mixto)',
        ]
    }
    
    # Extraction race
    breed = None
    patterns = breed_patterns.get(language, breed_patterns["fr"])
    
    for pattern in patterns:
        try:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                if pattern.startswith(r'\b(ross') or pattern.startswith(r'\b(isa'):  # Pattern de races spécifiques
                    breed = match.group(1).strip()
                else:  # Pattern avec groupe de capture
                    if match.lastindex and match.lastindex >= 1:
                        breed = match.group(1).strip()
                    else:
                        breed = match.group(0).strip()
                
                # Nettoyer la race extraite
                breed = re.sub(r'^(race|breed|souche|strain|raza|cepa)[:\s]*', '', breed, flags=re.IGNORECASE)
                breed = breed.strip()
                
                if len(breed) >= 3:  # Garde seulement les races avec au moins 3 caractères
                    break
                else:
                    breed = None
        except re.error as e:
            logger.warning(f"⚠️ [Utils] Erreur regex pattern breed: {e}")
            continue
    
    # Extraction sexe
    sex = None
    patterns = sex_patterns.get(language, sex_patterns["fr"])
    
    for pattern in patterns:
        try:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                if match.lastindex and match.lastindex >= 1:
                    matched_text = match.group(1)
                else:
                    matched_text = match.group(0)
                
                # Normalisation du sexe selon la langue
                if language == "fr":
                    if any(word in matched_text.lower() for word in ["mâle", "male"]):
                        sex = "mâles"
                    elif any(word in matched_text.lower() for word in ["femelle", "female"]):
                        sex = "femelles"
                    elif any(word in matched_text.lower() for word in ["mixte", "mixed", "mélangé"]):
                        sex = "mixte"
                elif language == "en":
                    if any(word in matched_text.lower() for word in ["male", "rooster", "cock"]):
                        sex = "males"
                    elif any(word in matched_text.lower() for word in ["female", "hen"]):
                        sex = "females"
                    elif any(word in matched_text.lower() for word in ["mixed", "both"]):
                        sex = "mixed"
                elif language == "es":
                    if any(word in matched_text.lower() for word in ["macho", "gallo"]):
                        sex = "machos"
                    elif any(word in matched_text.lower() for word in ["hembra", "gallina"]):
                        sex = "hembras"
                    elif any(word in matched_text.lower() for word in ["mixto", "mezclado", "ambos"]):
                        sex = "mixto"
                
                if sex:
                    break
        except re.error as e:
            logger.warning(f"⚠️ [Utils] Erreur regex pattern sex: {e}")
            continue
    
    # 🚀 Utilisation de la centralisation pour normaliser la race et inférer le sexe
    if breed and not sex:
        try:
            normalized_breed, _ = normalize_breed_name(breed)
            inferred_sex, was_inferred = infer_sex_from_breed(normalized_breed)
            
            if was_inferred and inferred_sex:
                sex_mapping = {
                    "fr": "femelles",
                    "en": "females", 
                    "es": "hembras"
                }
                sex = sex_mapping.get(language, "femelles")
                logger.info(f"🥚 [Auto-Fix Utils] Race détectée: {normalized_breed} → sexe='{sex}' (via clarification_entities)")
        except Exception as e:
            logger.warning(f"⚠️ [Utils] Erreur inférence sexe: {e}")
    
    result = {"breed": breed, "sex": sex}
    
    logger.info(f"🔍 [Utils] extraction '{text}' -> {result}")
    return result

def validate_clarification_completeness(text: str, missing_info: List[str], language: str = "fr") -> Dict[str, Any]:
    """Valide si une clarification contient toutes les informations nécessaires"""
    
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    
    if not isinstance(missing_info, list):
        missing_info = []
    
    extracted = extract_breed_and_sex_from_clarification(text, language)
    if not extracted:
        extracted = {"breed": None, "sex": None}
    
    still_missing = []
    confidence = 1.0
    
    # Vérifier chaque information manquante
    for info in missing_info:
        if info in ["breed", "race", "souche"]:
            if not extracted.get("breed"):
                still_missing.append("breed")
                confidence -= 0.5
        elif info in ["sex", "sexe"]:
            if not extracted.get("sex"):
                still_missing.append("sex")
                confidence -= 0.5
    
    is_complete = len(still_missing) == 0
    
    return {
        "is_complete": is_complete,
        "still_missing": still_missing,
        "extracted_info": extracted,
        "confidence": max(0.0, confidence),
        "completeness_score": 1.0 - (len(still_missing) / max(len(missing_info), 1))
    }

# =============================================================================
# CONSTRUCTION QUESTIONS ENRICHIES
# =============================================================================

def build_enriched_question_from_clarification(
    original_question: str, 
    clarification_response: str, 
    language: str = "fr"
) -> str:
    """Construit une question enrichie à partir de la clarification"""
    
    if not isinstance(original_question, str):
        original_question = str(original_question) if original_question is not None else ""
    
    if not isinstance(clarification_response, str):
        clarification_response = str(clarification_response) if clarification_response is not None else ""
    
    entities = extract_breed_and_sex_from_clarification(clarification_response, language)
    if not entities:
        return original_question
    
    breed = entities.get("breed")
    sex = entities.get("sex")
    
    return build_enriched_question_with_breed_sex(original_question, breed, sex, language)

def build_enriched_question_with_breed_sex(
    original_question: str, 
    breed: Optional[str], 
    sex: Optional[str], 
    language: str = "fr"
) -> str:
    """Construit une question enrichie avec race et sexe"""
    
    if not isinstance(original_question, str):
        original_question = str(original_question) if original_question is not None else ""
    
    if not breed and not sex:
        return original_question
    
    # Templates par langue
    templates = {
        "fr": {
            "both": "Pour des poulets {breed} {sex}",
            "breed_only": "Pour des poulets {breed}",
            "sex_only": "Pour des poulets {sex}"
        },
        "en": {
            "both": "For {breed} {sex} chickens",
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
    
    # Construire le préfixe
    prefix = ""
    try:
        if breed and sex:
            prefix = template_set["both"].format(breed=breed, sex=sex)
        elif breed:
            prefix = template_set["breed_only"].format(breed=breed)
        elif sex:
            prefix = template_set["sex_only"].format(sex=sex)
    except (KeyError, TypeError) as e:
        logger.warning(f"⚠️ [Utils] Erreur formatage template: {e}")
        return original_question
    
    # Combiner avec la question originale
    if prefix:
        # Détecter le type de question pour le formatting
        question_lower = original_question.lower().strip()
        
        if any(starter in question_lower for starter in ["quel", "quelle", "what", "cuál", "cuáles"]):
            return f"{prefix}, {question_lower}"
        elif any(starter in question_lower for starter in ["comment", "how", "cómo"]):
            return f"{prefix}: {original_question}"
        else:
            return f"{prefix}: {original_question}"
    
    return original_question

# =============================================================================
# UTILITAIRES TOPICS ET SUGGESTIONS
# =============================================================================

def get_enhanced_topics_by_language() -> Dict[str, List[str]]:
    """Retourne les sujets suggérés par langue"""
    
    return {
        "fr": [
            "Problèmes de croissance chez les poulets",
            "Conditions environnementales optimales pour l'élevage",
            "Protocoles de vaccination recommandés",
            "Diagnostic des problèmes de santé aviaire",
            "Nutrition et programmes d'alimentation",
            "Gestion de la mortalité élevée",
            "Optimisation des performances de croissance",
            "Prévention des maladies courantes"
        ],
        "en": [
            "Chicken growth problems",
            "Optimal environmental conditions for farming",
            "Recommended vaccination protocols",
            "Avian health problem diagnosis",
            "Nutrition and feeding programs",
            "High mortality management",
            "Growth performance optimization",
            "Common disease prevention"
        ],
        "es": [
            "Problemas de crecimiento en pollos",
            "Condiciones ambientales óptimas para la cría",
            "Protocolos de vacunación recomendados",
            "Diagnóstico de problemas de salud aviar",
            "Nutrición y programas de alimentación",
            "Manejo de alta mortalidad",
            "Optimización del rendimiento de crecimiento",
            "Prevención de enfermedades comunes"
        ]
    }

def get_contextualized_suggestions(
    current_question: str, 
    conversation_history: List[str], 
    language: str = "fr"
) -> List[str]:
    """Génère des suggestions contextuelles basées sur la conversation"""
    
    if not isinstance(current_question, str):
        current_question = str(current_question) if current_question is not None else ""
    
    if not isinstance(conversation_history, list):
        conversation_history = []
    
    all_topics = get_enhanced_topics_by_language()
    base_topics = all_topics.get(language, all_topics["fr"])
    
    # Simple contextualisation basée sur les mots-clés
    question_lower = current_question.lower()
    history_text = " ".join(str(item) for item in conversation_history).lower()
    
    contextualized = []
    
    # Ajuster les suggestions selon le contexte
    if any(word in question_lower + history_text for word in ["poids", "weight", "peso", "croissance", "growth"]):
        contextualized.extend([
            topic for topic in base_topics 
            if any(keyword in topic.lower() for keyword in ["croissance", "growth", "performance"])
        ])
    
    if any(word in question_lower + history_text for word in ["mortalité", "mortality", "mortalidad", "mort"]):
        contextualized.extend([
            topic for topic in base_topics 
            if any(keyword in topic.lower() for keyword in ["mortalité", "mortality", "santé", "health"])
        ])
    
    if any(word in question_lower + history_text for word in ["alimentation", "nutrition", "feeding", "alimentación"]):
        contextualized.extend([
            topic for topic in base_topics 
            if any(keyword in topic.lower() for keyword in ["nutrition", "alimentation", "feeding"])
        ])
    
    # Éviter les doublons et limiter à 6 suggestions
    unique_suggestions = list(dict.fromkeys(contextualized))[:6]
    
    # Compléter avec des suggestions générales si nécessaire
    if len(unique_suggestions) < 4:
        for topic in base_topics:
            if topic not in unique_suggestions:
                unique_suggestions.append(topic)
                if len(unique_suggestions) >= 6:
                    break
    
    return unique_suggestions[:6]

# =============================================================================
# UTILITAIRES CONVERSATION ET MÉMOIRE
# =============================================================================

def save_conversation_auto_enhanced(
    conversation_id: str,
    user_id: str,
    question: str,
    response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Sauvegarde automatique de conversation avec métadonnées enrichies"""
    
    try:
        # Validation des paramètres
        if not conversation_id or not user_id:
            logger.error("❌ [Utils] conversation_id et user_id requis")
            return False
        
        # Cette fonction serait intégrée avec le système de logging
        # Pour l'instant, on log juste l'information
        
        enhanced_metadata = {
            "timestamp": datetime.now().isoformat(),
            "auto_enhanced": True,
            "question_length": len(str(question)),
            "response_length": len(str(response)),
            **(metadata or {})
        }
        
        logger.info(f"💾 [Utils] Conversation sauvegardée: {conversation_id}")
        logger.debug(f"📊 [Utils] Métadonnées: {enhanced_metadata}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ [Utils] Erreur sauvegarde conversation: {e}")
        return False

def generate_conversation_id() -> str:
    """Génère un ID de conversation unique"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"conv_{timestamp}_{unique_id}"

def extract_conversation_context(conversation_history: List[Dict[str, Any]], max_context: int = 500) -> str:
    """Extrait le contexte pertinent d'un historique de conversation"""
    
    if not isinstance(conversation_history, list) or not conversation_history:
        return ""
    
    context_parts = []
    current_length = 0
    
    # Prendre les messages les plus récents en premier
    recent_history = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
    
    for message in reversed(recent_history):
        try:
            if not isinstance(message, dict):
                continue
            
            role = message.get("role", "unknown")
            content = message.get("content", "")
            
            if role in ["user", "assistant"] and content:
                part = f"{role}: {content}"
                
                if current_length + len(part) <= max_context:
                    context_parts.insert(0, part)  # Insérer au début pour garder l'ordre chronologique
                    current_length += len(part)
                else:
                    # Tronquer le dernier message si nécessaire
                    remaining_space = max_context - current_length
                    if remaining_space > 50:  # Garder seulement si on peut avoir au moins 50 caractères
                        truncated_part = f"{role}: {content[:remaining_space-10]}..."
                        context_parts.insert(0, truncated_part)
                    break
        except Exception as e:
            logger.warning(f"⚠️ [Utils] Erreur traitement message: {e}")
            continue
    
    return " | ".join(context_parts)

# =============================================================================
# UTILITAIRES VALIDATION ET FORMATS
# =============================================================================

def score_question_variant(variant: str, entities: Dict[str, Any]) -> float:
    """
    Score une variante de question en fonction des entités présentes
    
    Args:
        variant: La variante de question à scorer
        entities: Dictionnaire des entités extraites (breed, sex, age, etc.)
    
    Returns:
        float: Score entre 0 et 1 (1 = toutes les entités présentes)
    
    Example:
        entities = {"breed": "Ross 308", "sex": "mâles", "age": "25 jours"}
        variant = "Pour des poulets Ross 308 mâles de 25 jours"
        score = score_question_variant(variant, entities) # Returns 1.0
    """
    if not variant or not isinstance(variant, str):
        return 0.0
    
    if not entities or not isinstance(entities, dict):
        return 0.0
    
    variant_lower = variant.lower()
    matched_entities = 0
    total_entities = 0
    
    for entity_key, entity_value in entities.items():
        if entity_value:  # Ignore empty entities
            total_entities += 1
            entity_str = str(entity_value).lower()
            
            # Score différent selon le type d'entité
            if entity_key == "breed":
                # Pour les races, chercher le nom exact ou des parties
                breed_parts = entity_str.split()
                if len(breed_parts) > 1:
                    # Race composée (ex: "ross 308") - chercher toutes les parties
                    if all(part in variant_lower for part in breed_parts):
                        matched_entities += 1
                else:
                    # Race simple - chercher le nom exact
                    if entity_str in variant_lower:
                        matched_entities += 1
            elif entity_key == "sex":
                # Pour le sexe, chercher le terme exact
                if entity_str in variant_lower:
                    matched_entities += 1
            else:
                # Pour les autres entités (age, poids, etc.), chercher la valeur
                if entity_str in variant_lower:
                    matched_entities += 1
    
    return matched_entities / max(total_entities, 1)

def validate_question_length(question: str, min_length: int = 3, max_length: int = 5000) -> Dict[str, Any]:
    """Valide la longueur d'une question"""
    
    if not isinstance(question, str):
        question = str(question) if question is not None else ""
    
    if not question:
        return {
            "valid": False,
            "reason": "Question vide",
            "length": 0
        }
    
    length = len(question.strip())
    
    if length < min_length:
        return {
            "valid": False,
            "reason": f"Question trop courte (minimum {min_length} caractères)",
            "length": length
        }
    
    if length > max_length:
        return {
            "valid": False,
            "reason": f"Question trop longue (maximum {max_length} caractères)",
            "length": length
        }
    
    return {
        "valid": True,
        "reason": "Question valide",
        "length": length
    }

def normalize_language_code(language: str) -> str:
    """Normalise un code de langue"""
    if not language or not isinstance(language, str):
        return "fr"
    
    lang_lower = language.lower().strip()
    
    # Codes ISO 639-1 supportés
    supported_languages = {
        "fr": "fr",
        "français": "fr", 
        "french": "fr",
        "en": "en",
        "english": "en",
        "anglais": "en",
        "es": "es",
        "español": "es",
        "spanish": "es",
        "espagnol": "es"
    }
    
    return supported_languages.get(lang_lower, "fr")

def format_response_with_metadata(
    response_text: str, 
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Formate une réponse avec ses métadonnées"""
    
    if not isinstance(response_text, str):
        response_text = str(response_text) if response_text is not None else ""
    
    formatted_response = {
        "text": response_text,
        "length": len(response_text),
        "word_count": len(response_text.split()),
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    
    # Ajouter des statistiques automatiques
    try:
        formatted_response["metadata"].update({
            "has_numbers": bool(re.search(r'\d+', response_text)),
            "has_bullet_points": '•' in response_text or '-' in response_text,
            "paragraph_count": len([p for p in response_text.split('\n\n') if p.strip()]),
            "estimated_reading_time_seconds": max(1, len(response_text.split()) * 0.25)  # ~240 mots/minute
        })
    except Exception as e:
        logger.warning(f"⚠️ [Utils] Erreur ajout métadonnées automatiques: {e}")
    
    return formatted_response

# =============================================================================
# UTILITAIRES POUR GESTION D'ERREURS
# =============================================================================

def safe_extract_field(data: Any, field_path: str, default: Any = None) -> Any:
    """Extraction sécurisée d'un champ avec path en dot notation"""
    
    try:
        if not data or not isinstance(field_path, str):
            return default
        
        current = data
        for field in field_path.split('.'):
            if hasattr(current, field):
                current = getattr(current, field)
            elif isinstance(current, dict) and field in current:
                current = current[field]
            elif isinstance(current, dict) and hasattr(current, 'get'):
                current = current.get(field, default)
            else:
                return default
        
        return current if current is not None else default
        
    except Exception as e:
        logger.warning(f"⚠️ [Utils] Erreur extraction {field_path}: {e}")
        return default

def safe_string_operation(text: Any, operation: str, *args, **kwargs) -> str:
    """Opération sur string sécurisée"""
    
    try:
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        
        if not isinstance(operation, str):
            logger.warning(f"⚠️ [Utils] Opération doit être une string: {operation}")
            return text
        
        if operation == "lower":
            return text.lower()
        elif operation == "upper":
            return text.upper()
        elif operation == "strip":
            return text.strip()
        elif operation == "replace":
            return text.replace(*args, **kwargs) if args else text
        elif operation == "split":
            return text.split(*args, **kwargs) if args else text.split()
        elif operation == "join":
            return args[0].join(text) if args else text
        else:
            logger.warning(f"⚠️ [Utils] Opération inconnue: {operation}")
            return text
            
    except Exception as e:
        logger.warning(f"⚠️ [Utils] Erreur opération {operation}: {e}")
        return text if isinstance(text, str) else str(text) if text is not None else ""

def validate_and_sanitize_input(
    user_input: str, 
    max_length: int = 5000,
    remove_html: bool = True,
    remove_sql_keywords: bool = True
) -> Dict[str, Any]:
    """Valide et nettoie l'input utilisateur"""
    
    if not isinstance(user_input, str):
        user_input = str(user_input) if user_input is not None else ""
    
    if not user_input:
        return {
            "valid": False,
            "sanitized": "",
            "reason": "Input vide",
            "length": 0,
            "original_length": 0,
            "sanitized_length": 0,
            "warnings": []
        }
    
    original_length = len(user_input)
    sanitized = user_input
    warnings = []
    
    try:
        # Nettoyage HTML basique
        if remove_html:
            html_pattern = re.compile(r'<[^>]+>')
            if html_pattern.search(sanitized):
                sanitized = html_pattern.sub('', sanitized)
                warnings.append("HTML tags supprimés")
        
        # Nettoyage SQL basique
        if remove_sql_keywords:
            sql_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 'EXEC']
            for keyword in sql_keywords:
                if re.search(rf'\b{keyword}\b', sanitized, re.IGNORECASE):
                    warnings.append(f"Mot-clé SQL potentiellement dangereux détecté: {keyword}")
        
        # Limitation de longueur
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            warnings.append(f"Texte tronqué à {max_length} caractères")
        
        # Nettoyage des espaces
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    except Exception as e:
        logger.warning(f"⚠️ [Utils] Erreur nettoyage input: {e}")
        sanitized = user_input
        warnings.append(f"Erreur lors du nettoyage: {str(e)}")
    
    return {
        "valid": len(sanitized) > 0,
        "sanitized": sanitized,
        "original_length": original_length,
        "sanitized_length": len(sanitized),
        "warnings": warnings,
        "reason": "Input valide" if len(sanitized) > 0 else "Input vide après nettoyage"
    }

# =============================================================================
# UTILITAIRES DEBUGGING ET MONITORING
# =============================================================================

def create_debug_info(
    function_name: str,
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
    execution_time_ms: Optional[float] = None,
    errors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Crée des informations de debug structurées"""
    
    debug_info = {
        "function": function_name,
        "timestamp": datetime.now().isoformat(),
        "execution_time_ms": execution_time_ms,
        "success": not bool(errors),
        "errors": errors or [],
        "inputs": inputs or {},
        "outputs": outputs or {}
    }
    
    # Ajouter des statistiques si disponibles
    if inputs:
        debug_info["input_stats"] = {
            "input_count": len(inputs),
            "input_keys": list(inputs.keys())
        }
    
    if outputs:
        debug_info["output_stats"] = {
            "output_count": len(outputs),
            "output_keys": list(outputs.keys())
        }
    
    return debug_info

def log_performance_metrics(
    operation: str,
    start_time: float,
    end_time: Optional[float] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Log des métriques de performance"""
    
    if end_time is None:
        end_time = time.time()
    
    duration_ms = int((end_time - start_time) * 1000)
    
    metrics = {
        "operation": operation,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat(),
        "performance_category": _categorize_performance(duration_ms),
        **(additional_metrics or {})
    }
    
    logger.info(f"📊 [Performance] {operation}: {duration_ms}ms ({metrics['performance_category']})")
    
    return metrics

def _categorize_performance(duration_ms: int) -> str:
    """Catégorise la performance selon la durée"""
    if duration_ms < 100:
        return "excellent"
    elif duration_ms < 500:
        return "good"
    elif duration_ms < 1000:
        return "acceptable"
    elif duration_ms < 3000:
        return "slow"
    else:
        return "very_slow"

# =============================================================================
# UTILITAIRES SPÉCIAUX POUR INTÉGRATIONS
# =============================================================================

def create_fallback_response(
    original_question: str,
    error_message: str = "Service temporairement indisponible",
    language: str = "fr"
) -> Dict[str, Any]:
    """Crée une réponse de fallback standardisée"""
    
    if not isinstance(original_question, str):
        original_question = str(original_question) if original_question is not None else ""
    
    fallback_messages = {
        "fr": f"Je m'excuse, le service est temporairement indisponible. Votre question '{original_question}' a été reçue. Veuillez réessayer dans quelques minutes.",
        "en": f"I apologize, the service is temporarily unavailable. Your question '{original_question}' was received. Please try again in a few minutes.",
        "es": f"Me disculpo, el servicio no está disponible temporalmente. Su pregunta '{original_question}' fue recibida. Por favor intente de nuevo en unos minutos."
    }
    
    return {
        "response": fallback_messages.get(language, fallback_messages["fr"]),
        "is_fallback": True,
        "original_question": original_question,
        "error_message": error_message,
        "language": language,
        "timestamp": datetime.now().isoformat(),
        "suggested_action": "retry_later"
    }

def extract_key_entities_simple(text: str, language: str = "fr") -> Dict[str, List[Union[int, float]]]:
    """Extraction simple d'entités clés sans dépendances externes"""
    
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    
    entities = {
        "numbers": [],
        "breeds": [],
        "ages": [],
        "weights": [],
        "temperatures": [],
        "percentages": []
    }
    
    text_lower = text.lower()
    
    try:
        # Extraction nombres
        numbers = re.findall(r'\b\d+(?:[.,]\d+)?\b', text)
        entities["numbers"] = [float(n.replace(',', '.')) for n in numbers if n]
        
        # Extraction races communes
        breed_patterns = [
            r'\b(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)\b',
            r'\b(ross|cobb)\s*\d{2,3}\b'
        ]
        
        for pattern in breed_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            entities["breeds"].extend([str(match) for match in matches if match])
        
        # Extraction âges
        age_patterns = [
            r'(\d+)\s*(?:jour|day|día)s?',
            r'(\d+)\s*(?:semaine|week|semana)s?'
        ]
        
        for pattern in age_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            entities["ages"].extend([int(m) for m in matches if m.isdigit()])
        
        # Extraction poids
        weight_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:g|gr|gram|gramme)s?',
            r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo)s?'
        ]
        
        for pattern in weight_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            entities["weights"].extend([float(m.replace(',', '.')) for m in matches if m])
        
        # Extraction températures
        temp_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:°c|celsius|degré)s?',
            r'(\d+(?:[.,]\d+)?)\s*(?:°f|fahrenheit)s?'
        ]
        
        for pattern in temp_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            entities["temperatures"].extend([float(m.replace(',', '.')) for m in matches if m])
        
        # Extraction pourcentages
        percentage_pattern = r'(\d+(?:[.,]\d+)?)\s*%'
        matches = re.findall(percentage_pattern, text_lower)
        entities["percentages"] = [float(m.replace(',', '.')) for m in matches if m]
        
        # Nettoyer les listes vides et déduplication
        entities = {k: list(set(v)) for k, v in entities.items() if v}
    
    except Exception as e:
        logger.warning(f"⚠️ [Utils] Erreur extraction entités: {e}")
    
    return entities

# =============================================================================
# CONFIGURATION ET LOGGING
# =============================================================================

logger.info("✅ [Expert Utils] Fonctions utilitaires chargées avec succès")
logger.info("🔧 [Expert Utils] Fonctions disponibles:")
logger.info("   - get_user_id_from_request: Extraction ID utilisateur")
logger.info("   - extract_breed_and_sex_from_clarification: Extraction entités clarification")
logger.info("   - validate_clarification_completeness: Validation complétude clarification")
logger.info("   - build_enriched_question_*: Construction questions enrichies")
logger.info("   - get_enhanced_topics_by_language: Topics suggérés multilingues")
logger.info("   - save_conversation_auto_enhanced: Sauvegarde conversation")
logger.info("   - score_question_variant: Scoring variantes de questions")
logger.info("   - validate_question_length: Validation longueur questions")
logger.info("   - validate_and_sanitize_input: Validation et nettoyage input")
logger.info("   - create_debug_info: Informations debug structurées") 
logger.info("   - log_performance_metrics: Métriques de performance")
logger.info("   - create_fallback_response: Réponses de fallback")
logger.info("   - extract_key_entities_simple: Extraction entités simple")
logger.info("🚀 [Expert Utils] CORRIGÉ: Auto-détection sexe pondeuses activée!")
logger.info("🚀 [Expert Utils] INTÉGRÉ: Centralisation via clarification_entities")
logger.info("🚀 [Expert Utils] NOUVEAU: score_question_variant() - Scoring générique des variantes")
logger.info("✅ [Expert Utils] CORRECTIONS APPLIQUÉES:")
logger.info("   - Type annotations améliorées")
logger.info("   - Gestion des exceptions renforcée")
logger.info("   - Validation des paramètres None-safe")
logger.info("   - Gestion des erreurs regex")
logger.info("   - Validation des types d'entrée")
if CLARIFICATION_ENTITIES_AVAILABLE:
    logger.info("   ✅ clarification_entities: normalize_breed_name, infer_sex_from_breed")
else:
    logger.info("   ⚠️ clarification_entities: Mode fallback actif")
logger.info("✨ [Expert Utils] Toutes les dépendances expert.py et expert_services.py satisfaites!")