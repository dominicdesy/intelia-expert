"""
app/api/v1/expert_utilities.py - FONCTIONS UTILITAIRES v3.7.8

🔧 REFACTORISATION: Ce fichier contient toutes les fonctions utilitaires
extraites de expert.py pour améliorer la maintenabilité.

FONCTIONS INCLUSES:
- Extraction d'informations utilisateur
- Gestion des réponses de clarification
- Fonctions de fallback
- Utilitaires de validation
- Helpers de formatage
"""

import os
import re
import logging
import uuid
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Imports sécurisés avec gestion d'erreurs
try:
    from .expert_models import EnhancedExpertResponse, ConcisionLevel
except ImportError as e:
    logger.error(f"❌ Erreur import expert_models: {e}")
    # Fallback classes
    from pydantic import BaseModel
    
    class ConcisionLevel:
        CONCISE = "concise"
        DETAILED = "detailed"
        COMPREHENSIVE = "comprehensive"
    
    class EnhancedExpertResponse(BaseModel):
        question: str
        response: str
        conversation_id: str
        rag_used: bool = False
        rag_score: Optional[float] = None
        timestamp: str
        language: str
        response_time_ms: int
        mode: str
        user: Optional[str] = None
        logged: bool = False
        validation_passed: Optional[bool] = None
        clarification_required_critical: bool = False
        missing_critical_entities: List[str] = []
        variants_tested: List[str] = []
        dynamic_questions: Optional[List[Dict[str, Any]]] = None
        clarification_service_used: bool = False
        clarification_result: Optional[Dict[str, Any]] = None
        processing_steps: List[str] = []
        ai_enhancements_used: List[str] = []
        response_versions: Optional[Dict[str, str]] = None
        clarification_processing: Optional[Dict[str, Any]] = None

# =============================================================================
# FONCTIONS UTILITAIRES EXISTANTES - CONSERVÉES INTÉGRALEMENT
# =============================================================================

def get_user_id_from_request(request):
    """Extrait l'ID utilisateur depuis la requête"""
    try:
        return getattr(request.client, 'host', 'unknown') if request and request.client else 'unknown'
    except Exception:
        return 'unknown'

def extract_breed_and_sex_from_clarification(text, language):
    """Extrait la race et le sexe depuis une réponse de clarification"""
    try:
        # Fallback simple - retourner None pour forcer clarification
        return {"breed": None, "sex": None}
    except Exception:
        return {"breed": None, "sex": None}

# =============================================================================
# FONCTIONS DE RÉPONSE DE CLARIFICATION - CONSERVÉES v3.7.8
# =============================================================================

def _create_incomplete_clarification_response(
    request_data: Any, 
    clarified_entities: Dict[str, str], 
    breed: Optional[str], 
    sex: Optional[str], 
    start_time: float,
    public: bool = False
) -> EnhancedExpertResponse:
    """🔧 CONSERVÉE v3.7.7 + AMÉLIORATION v3.7.8: Crée une réponse pour clarification incomplète avec entités critiques et nouveaux champs"""
    
    # 🔧 FIX: Validation des paramètres d'entrée
    if not isinstance(clarified_entities, dict):
        clarified_entities = {"breed": breed, "sex": sex}
    
    # 🆕 v3.7.7: Extraire entités critiques de la réponse utilisateur aussi
    from .expert_core_functions import _extract_critical_entities_from_question
    
    user_text = getattr(request_data, 'text', '')
    extracted_entities = _extract_critical_entities_from_question(user_text, getattr(request_data, 'language', 'fr'))
    
    # Validation granulaire des informations manquantes avec protection None
    missing_info = []
    missing_details = []
    provided_parts = []
    missing_critical_entities = []  # NOUVEAU CHAMP v3.7.6/v3.7.7
    
    # 🔧 FIX: Vérification breed avec plus de nuances et protection None
    extracted_breed = extracted_entities.get('breed')
    effective_breed = breed or extracted_breed
    
    if not effective_breed or (isinstance(effective_breed, str) and len(effective_breed.strip()) == 0):
        missing_info.append("race/souche")
        missing_details.append("la race/souche (Ross 308, Cobb 500, Hubbard, etc.)")
        missing_critical_entities.append("breed")
    elif isinstance(effective_breed, str) and len(effective_breed.strip()) < 3:  # Breed trop court/vague
        missing_info.append("race/souche complète")
        missing_details.append("la race/souche complète (ex: 'Ross' → 'Ross 308')")
        provided_parts.append(f"Race partielle détectée: {effective_breed}")
        missing_critical_entities.append("breed_complete")
    elif effective_breed:  # breed est valide
        provided_parts.append(f"Race détectée: {effective_breed}")
    
    # 🔧 FIX: Vérification sex avec protection None
    if not sex or (isinstance(sex, str) and len(sex.strip()) == 0):
        missing_info.append("sexe")
        missing_details.append("le sexe (mâles, femelles, ou mixte)")
        missing_critical_entities.append("sex")
    elif sex:  # sex est valide
        provided_parts.append(f"Sexe détecté: {sex}")
    
    # 🆕 v3.7.7: Vérifier aussi âge et poids depuis extraction automatique
    extracted_age = extracted_entities.get('age_in_days')
    extracted_weight = extracted_entities.get('weight_in_grams')
    
    if extracted_age and isinstance(extracted_age, (int, float)) and extracted_age > 0:
        provided_parts.append(f"Âge détecté: {extracted_entities.get('age', extracted_age)} jours")
    else:
        missing_info.append("âge")
        missing_details.append("l'âge précis (13 jours, 2 semaines, etc.)")
        missing_critical_entities.append("age")
    
    if extracted_weight and isinstance(extracted_weight, (int, float)) and extracted_weight > 0:
        provided_parts.append(f"Poids détecté: {extracted_entities.get('weight', extracted_weight)}g")
    else:
        missing_info.append("poids")
        missing_details.append("le poids actuel (800g, 1.2kg, etc.)")
        missing_critical_entities.append("weight")
    
    # 🎯 MESSAGE ADAPTATIF selon ce qui manque réellement v3.7.7/v3.7.8
    if len(missing_info) >= 3:
        error_message = f"Information incomplète. Il manque plusieurs éléments critiques : {', '.join(missing_info)}.\n\n"
    elif len(missing_info) == 2:
        error_message = f"Information incomplète. Il manque encore : {' et '.join(missing_info)}.\n\n"
    elif len(missing_info) == 1:
        error_message = f"Information incomplète. Il manque encore : {missing_info[0]}.\n\n"
    else:
        error_message = "Information incomplète.\n\n"
    
    # Ajouter contexte de ce qui a été fourni VS ce qui manque
    if provided_parts:
        error_message += f"Votre réponse '{user_text}' contient : {', '.join(provided_parts)}.\n"
        error_message += f"Mais il manque encore : {', '.join(missing_details)}.\n\n"
    else:
        error_message += f"Votre réponse '{user_text}' ne contient pas tous les éléments nécessaires.\n\n"
    
    # Exemples contextuels selon ce qui manque v3.7.7/v3.7.8
    error_message += "**Exemples complets requis :**\n"
    
    if len(missing_critical_entities) >= 3:  # Manque breed + age + weight
        error_message += "• 'Ross 308 mâles de 13 jours pesant 800g'\n"
        error_message += "• 'Cobb 500 femelles de 2 semaines pesant 1.2kg'\n" 
        error_message += "• 'Hubbard mixte de 25 jours pesant 950g'\n\n"
    elif "breed" in missing_critical_entities and "age" in missing_critical_entities:
        error_message += f"• 'Ross 308 {sex or 'mâles'} de 13 jours'\n"
        error_message += f"• 'Cobb 500 {sex or 'femelles'} de 2 semaines'\n\n"
    elif "breed" in missing_critical_entities and "weight" in missing_critical_entities:
        error_message += f"• 'Ross 308 {sex or 'mâles'} pesant 800g'\n"
        error_message += f"• 'Cobb 500 {sex or 'femelles'} pesant 1.2kg'\n\n"
    elif "age" in missing_critical_entities and "weight" in missing_critical_entities:
        error_message += f"• '{effective_breed or 'Ross 308'} de 13 jours pesant 800g'\n"
        error_message += f"• '{effective_breed or 'Cobb 500'} de 2 semaines pesant 1.2kg'\n\n"
    elif "breed" in missing_critical_entities:
        error_message += f"• 'Ross 308 {sex or 'mâles'}'\n"
        error_message += f"• 'Cobb 500 {sex or 'femelles'}'\n\n"
    elif "age" in missing_critical_entities:
        error_message += f"• '{effective_breed or 'Ross 308'} de 13 jours'\n"
        error_message += f"• '{effective_breed or 'Cobb 500'} de 2 semaines'\n\n"
    elif "weight" in missing_critical_entities:
        error_message += f"• '{effective_breed or 'Ross 308'} pesant 800g'\n"
        error_message += f"• '{effective_breed or 'Cobb 500'} pesant 1.2kg'\n\n"
    
    error_message += "Pouvez-vous préciser les informations manquantes ?"
    
    # 🔧 FIX: Retourner erreur clarification incomplète avec validation robuste v3.7.8
    mode_suffix = "_public" if public else ""
    conversation_id = getattr(request_data, 'conversation_id', None)
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
    
    language = getattr(request_data, 'language', 'fr')
    if not isinstance(language, str):
        language = 'fr'
    
    logger.info(f"📋 [CLARIFICATION INCOMPLÈTE v3.7.8] Entités critiques manquantes: {missing_critical_entities}")
    logger.info(f"📋 [CLARIFICATION INCOMPLÈTE v3.7.8] Entités extraites automatiquement: {extracted_entities}")
    
    return EnhancedExpertResponse(
        question=user_text,
        response=error_message,
        conversation_id=conversation_id,
        rag_used=False,  # 🆕 v3.7.6/v3.7.7: Toujours False pour clarification incomplète
        rag_score=None,
        timestamp=datetime.now().isoformat(),
        language=language,
        response_time_ms=int((time.time() - start_time) * 1000),
        mode=f"incomplete_clarification_response_v3.7.8{mode_suffix}",
        user=None,
        logged=True,
        validation_passed=False,
        # 🚀 CHAMPS EXISTANTS v3.7.6/v3.7.7 POUR CLARIFICATION INCOMPLÈTE
        clarification_required_critical=True,
        missing_critical_entities=missing_critical_entities,
        variants_tested=[],  # vide pour clarification incomplète
        # 🆕 NOUVEAUX CHAMPS v3.7.8
        dynamic_questions=None,  # Pas de questions dynamiques pour erreurs incomplètes
        clarification_service_used=False,  # Service non utilisé pour erreurs
        clarification_result={
            "clarification_requested": True,
            "clarification_type": f"incomplete_critical_entities_retry_v3.7.8{mode_suffix}",
            "missing_information": missing_info,
            "provided_entities": clarified_entities,
            "provided_parts": provided_parts,
            "missing_details": missing_details,
            "retry_required": True,
            "confidence": 0.3,
            # 🚀 CHAMPS DANS CLARIFICATION_RESULT v3.7.6/v3.7.7
            "clarification_required_critical": True,
            "missing_critical_entities": missing_critical_entities,
            # 🆕 v3.7.7: Ajouter entités extraites automatiquement
            "auto_extracted_entities": extracted_entities,
            "effective_breed": effective_breed,
            "critical_entities_analysis": {
                "breed_detected": effective_breed,
                "age_detected": extracted_age,
                "weight_detected": extracted_weight,
                "sex_detected": sex,
                "validation_summary": f"Missing: {len(missing_critical_entities)} critical entities",
                "extraction_method": "automatic_from_user_response",
                "timestamp": datetime.now().isoformat()
            }
        },
        processing_steps=[
            "incomplete_clarification_response_created_v3.7.8",
            f"missing_entities_{len(missing_critical_entities)}",
            f"provided_parts_{len(provided_parts)}",
            "critical_entities_auto_extraction"
        ],
        ai_enhancements_used=[
            "incomplete_clarification_handling_v3.7.8",
            "critical_entities_validation",
            "adaptive_error_messages",
            "contextual_examples_generation"
        ],
        response_versions=None  # Pas de versions pour erreurs
    )

async def _fallback_expert_response(
    request_data: Any, 
    start_time: float, 
    current_user: Optional[Dict[str, Any]], 
    error_message: str = "Service non disponible"
) -> EnhancedExpertResponse:
    """🔧 FALLBACK v3.7.8: Réponse de secours si service expert non disponible"""
    
    try:
        conversation_id = getattr(request_data, 'conversation_id', None)
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        language = getattr(request_data, 'language', 'fr')
        user_email = current_user.get('email') if current_user else None
        
        fallback_response = f"""Je suis désolé, le service expert n'est temporairement pas disponible.

**Erreur:** {error_message}

**Pour obtenir de l'aide avec vos questions d'aviculture:**
• Vérifiez que votre question contient la race (Ross 308, Cobb 500, etc.)
• Précisez l'âge de vos animaux (13 jours, 2 semaines, etc.)
• Indiquez le sexe (mâles, femelles, mixte)
• Mentionnez le poids actuel si pertinent

**Exemple de question complète:**
"Quel est le poids normal d'un poulet Ross 308 mâle de 12 jours ?"

Veuillez réessayer dans quelques instants."""

        return EnhancedExpertResponse(
            question=request_data.text,
            response=fallback_response,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=int((time.time() - start_time) * 1000),
            mode="fallback_service_unavailable_v3.7.8",
            user=user_email,
            logged=True,
            validation_passed=False,
            clarification_required_critical=False,
            missing_critical_entities=[],
            variants_tested=[],
            dynamic_questions=None,
            clarification_service_used=False,
            clarification_result=None,
            processing_steps=["fallback_response_generated_v3.7.8"],
            ai_enhancements_used=["fallback_service_v3.7.8"],
            response_versions=None
        )
        
    except Exception as e:
        logger.error(f"❌ [FALLBACK] Erreur création réponse fallback: {e}")
        # Réponse ultra-minimale en cas d'erreur critique
        return EnhancedExpertResponse(
            question=getattr(request_data, 'text', 'Question non disponible'),
            response="Service temporairement indisponible. Veuillez réessayer.",
            conversation_id=str(uuid.uuid4()),
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language="fr",
            response_time_ms=int((time.time() - start_time) * 1000),
            mode="critical_fallback_v3.7.8",
            user=None,
            logged=False,
            validation_passed=False,
            clarification_required_critical=False,
            missing_critical_entities=[],
            variants_tested=[],
            dynamic_questions=None,
            clarification_service_used=False,
            clarification_result=None,
            processing_steps=["critical_fallback"],
            ai_enhancements_used=[],
            response_versions=None
        )

# =============================================================================
# FONCTIONS DE VALIDATION ET FORMATAGE
# =============================================================================

def validate_question_text(text: str) -> bool:
    """Valide qu'un texte de question est valide"""
    try:
        if not text or not isinstance(text, str):
            return False
        
        text_clean = text.strip()
        if len(text_clean) < 3:
            return False
        
        # Vérifier qu'il n'y a pas que des espaces ou caractères spéciaux
        if not re.search(r'[a-zA-ZÀ-ÿ0-9]', text_clean):
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ [VALIDATION] Erreur validation question: {e}")
        return False

def format_response_time(start_time: float) -> int:
    """Formate le temps de réponse en millisecondes"""
    try:
        return int((time.time() - start_time) * 1000)
    except Exception:
        return 0

def safe_get_attribute(obj: Any, attr_name: str, default: Any = None) -> Any:
    """Récupère un attribut de manière sécurisée"""
    try:
        return getattr(obj, attr_name, default)
    except Exception:
        return default

def safe_update_dict(target_dict: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Met à jour un dictionnaire de manière sécurisée"""
    try:
        if not isinstance(target_dict, dict):
            target_dict = {}
        if not isinstance(updates, dict):
            return target_dict
        
        target_dict.update(updates)
        return target_dict
    except Exception as e:
        logger.error(f"❌ [SAFE UPDATE] Erreur: {e}")
        return target_dict

def generate_conversation_id() -> str:
    """Génère un ID de conversation unique"""
    try:
        return str(uuid.uuid4())
    except Exception:
        return f"fallback_{int(time.time())}"

def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Nettoie et limite la longueur d'un texte"""
    try:
        if not isinstance(text, str):
            text = str(text)
        
        # Nettoyer les caractères de contrôle
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Limiter la longueur
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text.strip()
    except Exception:
        return ""

def extract_numbers_from_text(text: str) -> List[int]:
    """Extrait tous les nombres d'un texte"""
    try:
        if not isinstance(text, str):
            return []
        
        numbers = re.findall(r'\d+', text)
        return [int(num) for num in numbers]
    except Exception:
        return []

def is_agricultural_question(text: str) -> bool:
    """Détermine si une question est liée à l'agriculture/aviculture"""
    try:
        if not isinstance(text, str):
            return False
        
        text_lower = text.lower()
        
        agricultural_keywords = [
            "poulet", "chicken", "pollo", "volaille", "poultry", "ave",
            "ross", "cobb", "hubbard", "arbor", "isa", "lohmann",
            "élevage", "farming", "cría", "feed", "alimentation", "alimentación",
            "poids", "weight", "peso", "croissance", "growth", "crecimiento",
            "température", "temperature", "temperatura", "ventilation",
            "mortalité", "mortality", "mortalidad", "vaccination", "vacunación",
            "incubation", "incubación", "ponte", "laying", "puesta",
            "maladie", "disease", "enfermedad", "symptôme", "symptom", "síntoma"
        ]
        
        return any(keyword in text_lower for keyword in agricultural_keywords)
    except Exception:
        return False

def extract_age_from_text(text: str, language: str = "fr") -> Optional[Dict[str, Any]]:
    """Extrait l'âge depuis un texte avec conversion en jours"""
    try:
        if not isinstance(text, str):
            return None
        
        text_lower = text.lower()
        
        # Patterns d'âge selon la langue
        age_patterns = {
            "fr": [
                (r'(\d+)\s*j(?:our)?s?', 1, "jours"),
                (r'(\d+)\s*sem(?:aine)?s?', 7, "semaines"),
                (r'(\d+)\s*mois', 30, "mois")
            ],
            "en": [
                (r'(\d+)\s*day?s?', 1, "days"),
                (r'(\d+)\s*week?s?', 7, "weeks"),
                (r'(\d+)\s*month?s?', 30, "months")
            ],
            "es": [
                (r'(\d+)\s*día?s?', 1, "días"),
                (r'(\d+)\s*semana?s?', 7, "semanas"),
                (r'(\d+)\s*mes(?:es)?', 30, "meses")
            ]
        }
        
        patterns = age_patterns.get(language, age_patterns["fr"])
        
        for pattern, multiplier, unit in patterns:
            match = re.search(pattern, text_lower)
            if match:
                age_value = int(match.group(1))
                return {
                    "original_text": match.group(0),
                    "value": age_value,
                    "unit": unit,
                    "days": age_value * multiplier,
                    "confidence": 0.9
                }
        
        return None
    except Exception as e:
        logger.error(f"❌ [AGE EXTRACTION] Erreur: {e}")
        return None

def extract_weight_from_text(text: str, language: str = "fr") -> Optional[Dict[str, Any]]:
    """Extrait le poids depuis un texte avec conversion en grammes"""
    try:
        if not isinstance(text, str):
            return None
        
        text_lower = text.lower()
        
        # Patterns de poids selon la langue
        weight_patterns = [
            (r'(\d+(?:\.\d+)?)\s*kg', 1000, "kg"),
            (r'(\d+(?:\.\d+)?)\s*kilo', 1000, "kilo"),
            (r'(\d+)\s*g(?:ramme)?s?', 1, "g"),
            (r'(\d+(?:\.\d+)?)\s*lb', 453.592, "lb")
        ]
        
        for pattern, multiplier, unit in weight_patterns:
            match = re.search(pattern, text_lower)
            if match:
                weight_value = float(match.group(1))
                return {
                    "original_text": match.group(0),
                    "value": weight_value,
                    "unit": unit,
                    "grams": int(weight_value * multiplier),
                    "confidence": 0.9
                }
        
        return None
    except Exception as e:
        logger.error(f"❌ [WEIGHT EXTRACTION] Erreur: {e}")
        return None

def extract_breed_from_text(text: str, language: str = "fr") -> Optional[Dict[str, Any]]:
    """Extrait la race/souche depuis un texte"""
    try:
        if not isinstance(text, str):
            return None
        
        text_lower = text.lower()
        
        # Races spécifiques avec patterns
        specific_breeds = [
            (r'\b(ross\s*308|ross308)\b', "Ross 308", 0.95),
            (r'\b(ross\s*708|ross708)\b', "Ross 708", 0.95),
            (r'\b(cobb\s*500|cobb500)\b', "Cobb 500", 0.95),
            (r'\b(cobb\s*700|cobb700)\b', "Cobb 700", 0.95),
            (r'\b(hubbard)\b', "Hubbard", 0.90),
            (r'\b(arbor\s*acres|arbor)\b', "Arbor Acres", 0.90),
            (r'\b(isa\s*brown|isa)\b', "ISA Brown", 0.90),
            (r'\b(lohmann|lohman)\b', "Lohmann", 0.85)
        ]
        
        for pattern, breed_name, confidence in specific_breeds:
            match = re.search(pattern, text_lower)
            if match:
                return {
                    "original_text": match.group(0),
                    "normalized_name": breed_name,
                    "confidence": confidence,
                    "type": "specific"
                }
        
        # Termes génériques
        generic_patterns = [
            (r'\bpoulets?\b', "poulet", 0.3),
            (r'\bpoules?\b', "poule", 0.3),
            (r'\bchickens?\b', "chicken", 0.3),
            (r'\bbroilers?\b', "broiler", 0.4),
            (r'\bpollos?\b', "pollo", 0.3)
        ]
        
        for pattern, breed_name, confidence in generic_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return {
                    "original_text": match.group(0),
                    "normalized_name": breed_name,
                    "confidence": confidence,
                    "type": "generic"
                }
        
        return None
    except Exception as e:
        logger.error(f"❌ [BREED EXTRACTION] Erreur: {e}")
        return None

def format_entity_for_display(entity_data: Dict[str, Any], entity_type: str) -> str:
    """Formate une entité pour l'affichage"""
    try:
        if not isinstance(entity_data, dict):
            return str(entity_data)
        
        if entity_type == "age" and "days" in entity_data:
            days = entity_data["days"]
            original = entity_data.get("original_text", "")
            return f"{original} ({days} jours)"
        
        elif entity_type == "weight" and "grams" in entity_data:
            grams = entity_data["grams"]
            original = entity_data.get("original_text", "")
            return f"{original} ({grams}g)"
        
        elif entity_type == "breed" and "normalized_name" in entity_data:
            return entity_data["normalized_name"]
        
        else:
            return entity_data.get("original_text", str(entity_data))
    
    except Exception as e:
        logger.error(f"❌ [FORMAT ENTITY] Erreur: {e}")
        return str(entity_data)

def calculate_confidence_score(entities: Dict[str, Any]) -> float:
    """Calcule un score de confiance global basé sur les entités détectées"""
    try:
        if not isinstance(entities, dict):
            return 0.0
        
        confidence_values = []
        confidence_data = entities.get("confidence", {})
        
        for entity_type, confidence in confidence_data.items():
            if isinstance(confidence, (int, float)):
                confidence_values.append(confidence)
        
        if not confidence_values:
            return 0.0
        
        # Score moyen pondéré
        return sum(confidence_values) / len(confidence_values)
    
    except Exception as e:
        logger.error(f"❌ [CONFIDENCE SCORE] Erreur: {e}")
        return 0.0

def detect_question_urgency(text: str, language: str = "fr") -> str:
    """Détecte le niveau d'urgence d'une question"""
    try:
        if not isinstance(text, str):
            return "normal"
        
        text_lower = text.lower()
        
        urgency_keywords = {
            "high": {
                "fr": ["urgent", "immédiat", "rapide", "critique", "grave", "emergency", "mort", "mourir"],
                "en": ["urgent", "immediate", "quick", "critical", "serious", "emergency", "dying", "death"],
                "es": ["urgente", "inmediato", "rápido", "crítico", "grave", "emergencia", "muriendo", "muerte"]
            },
            "low": {
                "fr": ["préventif", "routine", "normal", "planifier", "futur"],
                "en": ["preventive", "routine", "normal", "planning", "future"],
                "es": ["preventivo", "rutina", "normal", "planificar", "futuro"]
            }
        }
        
        # Vérifier urgence élevée
        high_keywords = urgency_keywords["high"].get(language, urgency_keywords["high"]["fr"])
        if any(keyword in text_lower for keyword in high_keywords):
            return "high"
        
        # Vérifier urgence faible
        low_keywords = urgency_keywords["low"].get(language, urgency_keywords["low"]["fr"])
        if any(keyword in text_lower for keyword in low_keywords):
            return "low"
        
        return "normal"
    
    except Exception:
        return "normal"

def build_entity_summary(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Construit un résumé des entités détectées"""
    try:
        if not isinstance(entities, dict):
            return {}
        
        summary = {
            "total_entities": 0,
            "detected_types": [],
            "missing_types": [],
            "confidence_average": 0.0,
            "coherence_issues": entities.get("coherence_issues", []),
            "details": {}
        }
        
        critical_entities = ["breed", "age_in_days", "weight_in_grams", "sex"]
        
        for entity_type in critical_entities:
            entity_value = entities.get(entity_type)
            if entity_value is not None:
                summary["total_entities"] += 1
                summary["detected_types"].append(entity_type)
                summary["details"][entity_type] = entity_value
            else:
                summary["missing_types"].append(entity_type)
        
        # Calculer confiance moyenne
        confidence_data = entities.get("confidence", {})
        if confidence_data:
            confidence_values = [v for v in confidence_data.values() if isinstance(v, (int, float))]
            if confidence_values:
                summary["confidence_average"] = sum(confidence_values) / len(confidence_values)
        
        return summary
    
    except Exception as e:
        logger.error(f"❌ [ENTITY SUMMARY] Erreur: {e}")
        return {}

# =============================================================================
# FONCTIONS DE FORMATAGE ET PRÉSENTATION
# =============================================================================

def format_clarification_message(missing_entities: List[str], language: str = "fr") -> str:
    """Formate un message de clarification selon les entités manquantes"""
    try:
        if not missing_entities:
            return ""
        
        messages = {
            "fr": {
                "intro": "Pour vous donner une réponse précise, j'ai besoin de quelques informations supplémentaires :",
                "breed": "Quelle est la race ou souche de vos animaux ?",
                "age": "Quel est l'âge précis de vos animaux ?",
                "weight": "Quel est le poids actuel de vos animaux ?",
                "sex": "S'agit-il de mâles, femelles, ou un troupeau mixte ?"
            },
            "en": {
                "intro": "To give you an accurate answer, I need some additional information:",
                "breed": "What is the breed or strain of your animals?",
                "age": "What is the precise age of your animals?",
                "weight": "What is the current weight of your animals?",
                "sex": "Are these males, females, or a mixed flock?"
            },
            "es": {
                "intro": "Para darle una respuesta precisa, necesito información adicional:",
                "breed": "¿Cuál es la raza o cepa de sus animales?",
                "age": "¿Cuál es la edad precisa de sus animales?",
                "weight": "¿Cuál es el peso actual de sus animales?",
                "sex": "¿Son machos, hembras, o un lote mixto?"
            }
        }
        
        lang_messages = messages.get(language, messages["fr"])
        result = lang_messages["intro"] + "\n\n"
        
        for i, entity in enumerate(missing_entities, 1):
            entity_key = entity.replace("_in_days", "").replace("_in_grams", "")
            if entity_key in lang_messages:
                result += f"{i}. {lang_messages[entity_key]}\n"
        
        return result.strip()
    
    except Exception as e:
        logger.error(f"❌ [FORMAT CLARIFICATION] Erreur: {e}")
        return "Information supplémentaire nécessaire."

def create_entity_options(entity_type: str, language: str = "fr") -> List[str]:
    """Crée une liste d'options pour un type d'entité"""
    try:
        options = {
            "breed": {
                "fr": ["Ross 308", "Cobb 500", "Hubbard", "Arbor Acres", "ISA Brown", "Autre"],
                "en": ["Ross 308", "Cobb 500", "Hubbard", "Arbor Acres", "ISA Brown", "Other"],
                "es": ["Ross 308", "Cobb 500", "Hubbard", "Arbor Acres", "ISA Brown", "Otro"]
            },
            "age": {
                "fr": ["1 semaine", "2 semaines", "3 semaines", "1 mois", "Plus d'1 mois"],
                "en": ["1 week", "2 weeks", "3 weeks", "1 month", "More than 1 month"],
                "es": ["1 semana", "2 semanas", "3 semanas", "1 mes", "Más de 1 mes"]
            },
            "weight": {
                "fr": ["200-500g", "500g-1kg", "1-1.5kg", "1.5-2kg", "Plus de 2kg"],
                "en": ["200-500g", "500g-1kg", "1-1.5kg", "1.5-2kg", "More than 2kg"],
                "es": ["200-500g", "500g-1kg", "1-1.5kg", "1.5-2kg", "Más de 2kg"]
            },
            "sex": {
                "fr": ["Mâles", "Femelles", "Mixte"],
                "en": ["Males", "Females", "Mixed"],
                "es": ["Machos", "Hembras", "Mixto"]
            }
        }
        
        entity_key = entity_type.replace("_in_days", "").replace("_in_grams", "")
        return options.get(entity_key, {}).get(language, [])
    
    except Exception as e:
        logger.error(f"❌ [CREATE OPTIONS] Erreur: {e}")
        return []

# =============================================================================
# LOGGING ET INITIALISATION FINALE v3.7.8
# =============================================================================

logger.info("🚀" * 50)
logger.info("🚀 [EXPERT UTILITIES] VERSION 3.7.8 - UTILITAIRES REFACTORISÉS!")
logger.info("🚀 [REFACTORISATION]:")
logger.info("   ✅ Fonctions utilitaires extraites de expert.py")
logger.info("   ✅ Code conservé intégralement")
logger.info("   ✅ Fonctions de validation ajoutées")
logger.info("   ✅ Helpers de formatage créés")
logger.info("   ✅ Extraction d'entités améliorée")
logger.info("   ✅ Gestion d'erreur robuste")
logger.info("")
logger.info("🔧 [FONCTIONS DISPONIBLES v3.7.8]:")
logger.info("   - get_user_id_from_request")
logger.info("   - extract_breed_and_sex_from_clarification")
logger.info("   - _create_incomplete_clarification_response")
logger.info("   - _fallback_expert_response")
logger.info("   - validate_question_text")
logger.info("   - format_response_time")
logger.info("   - safe_get_attribute")
logger.info("   - safe_update_dict")
logger.info("   - generate_conversation_id")
logger.info("   - sanitize_text")
logger.info("   - extract_numbers_from_text")
logger.info("   - is_agricultural_question")
logger.info("   - extract_age_from_text")
logger.info("   - extract_weight_from_text")
logger.info("   - extract_breed_from_text")
logger.info("   - format_entity_for_display")
logger.info("   - calculate_confidence_score")
logger.info("   - detect_question_urgency")
logger.info("   - build_entity_summary")
logger.info("   - format_clarification_message")
logger.info("   - create_entity_options")
logger.info("")
logger.info("✅ [RÉSULTAT ATTENDU v3.7.8]:")
logger.info("   ✅ Utilitaires séparés et réutilisables")
logger.info("   ✅ Fonctions de validation robustes")
logger.info("   ✅ Helpers de formatage complets")
logger.info("   ✅ Extraction d'entités avancée")
logger.info("   ✅ Gestion d'erreur sécurisée")
logger.info("   ✅ SYNTAXE PYTHON 100% CORRECTE")
logger.info("🚀" * 50)