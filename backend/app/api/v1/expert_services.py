"""
app/api/v1/expert_services.py - SERVICE PRINCIPAL EXPERT SYSTEM (VERSION PIPELINE AVEC CLARIFICATION CRITIQUE)

🚀 MODIFICATIONS APPLIQUÉES:
1. Agent Contextualizer TOUJOURS ACTIF (même sans entités existantes)
2. Clarification CRITIQUE BLOQUANTE (stoppe avant RAG si nécessaire)
3. Clarification NON CRITIQUE reste non bloquante
4. Agent RAG Enhancer reçoit la question ENRICHIE (pas seulement l'originale)
5. Fallback intelligent VIA agent post-RAG (même sans RAG)
6. Mémoire conversationnelle track les clarifications pendantes

✨ RÉSULTAT: Pipeline plus intelligent avec clarifications critiques bloquantes mais non critiques fluides
"""

import os
import logging
import uuid
import time
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# 🚀 NOUVEAU: Imports centralisation clarification_entities
try:
    from .clarification_entities import normalize_breed_name, infer_sex_from_breed, get_breed_type, get_supported_breeds
    CLARIFICATION_ENTITIES_AVAILABLE = True
    logger.info("✅ [Services] clarification_entities importé avec succès")
except ImportError as e:
    logger.warning(f"⚠️ [Services] clarification_entities non disponible: {e}")
    # Fonctions fallback
    def normalize_breed_name(breed):
        return breed.lower().strip() if breed else "", "manual"
    def infer_sex_from_breed(breed):
        layer_breeds = ['isa brown', 'lohmann brown', 'hy-line', 'bovans', 'shaver']
        is_layer = any(layer in breed.lower() for layer in layer_breeds)
        return "femelles" if is_layer else None, is_layer
    def get_breed_type(breed):
        layer_breeds = ['isa brown', 'lohmann brown', 'hy-line', 'bovans', 'shaver', 'hissex', 'novogen']
        if any(layer in breed.lower() for layer in layer_breeds):
            return "layers"
        broiler_breeds = ['ross 308', 'cobb 500', 'hubbard', 'ross', 'cobb']
        if any(broiler in breed.lower() for broiler in broiler_breeds):
            return "broilers"
        return "unknown"
    def get_supported_breeds():
        return ["ross 308", "cobb 500", "hubbard", "isa brown", "lohmann brown", "hy-line", "bovans", "shaver"]
    CLARIFICATION_ENTITIES_AVAILABLE = False

# Imports sécurisés des modèles
try:
    from .expert_models import (
        EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest,
        ValidationResult, ProcessingContext, VaguenessResponse, ResponseFormat,
        ConcisionLevel, ConcisionMetrics, DynamicClarification
    )
    MODELS_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Erreur import expert_models: {e}")
    from pydantic import BaseModel
    
    # Modèles de fallback
    class ValidationResult:
        def __init__(self, is_valid=True, rejection_message="", confidence=1.0):
            self.is_valid = is_valid
            self.rejection_message = rejection_message
            self.confidence = confidence
    
    class ConcisionLevel:
        CONCISE = "concise"
        STANDARD = "standard"
        DETAILED = "detailed"
        ULTRA_CONCISE = "ultra_concise"
    
    MODELS_AVAILABLE = False

# Imports sécurisés des utilitaires
try:
    from .expert_utils import (
        get_user_id_from_request, 
        build_enriched_question_from_clarification,
        get_enhanced_topics_by_language,
        save_conversation_auto_enhanced,
        extract_breed_and_sex_from_clarification,
        build_enriched_question_with_breed_sex,
        validate_clarification_completeness
    )
    UTILS_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Erreur import expert_utils: {e}")
    # Fonctions fallback
    def get_user_id_from_request(request):
        return getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
    
    def get_enhanced_topics_by_language():
        return {
            "fr": ["Croissance poulets", "Nutrition aviaire", "Santé animale"],
            "en": ["Chicken growth", "Poultry nutrition", "Animal health"],
            "es": ["Crecimiento pollos", "Nutrición aviar", "Salud animal"]
        }
    
    def validate_clarification_completeness(text, missing_info, language):
        return {"is_complete": True, "extracted_info": {}}
    
    UTILS_AVAILABLE = False

# Imports sécurisés des intégrations
try:
    from .expert_integrations import IntegrationsManager
    INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Erreur import expert_integrations: {e}")
    
    # Mock IntegrationsManager
    class IntegrationsManager:
        def __init__(self):
            self.enhanced_clarification_available = False
            self.intelligent_memory_available = False
            self.agricultural_validator_available = False
            self.auth_available = False
            # 🚀 NOUVEAU: Support clarification critique
            self._clarification_functions = {
                'analyze_question_for_clarification_enhanced': self._mock_analyze_clarification
            }
        
        def _mock_analyze_clarification(self, question, language):
            """Mock pour analyse clarification critique"""
            return {
                "clarification_required_critical": False,
                "clarification_required_optional": False,
                "missing_critical_entities": [],
                "missing_optional_entities": [],
                "confidence": 0.5
            }
        
        def get_current_user_dependency(self):
            return lambda: {"id": "fallback", "email": "fallback@intelia.com"}
        
        def is_agricultural_validation_enabled(self):
            return False
    
    INTEGRATIONS_AVAILABLE = False

# 🤖 NOUVEAUX IMPORTS: Agents GPT
try:
    from .agent_contextualizer import agent_contextualizer
    from .agent_rag_enhancer import agent_rag_enhancer
    AGENTS_AVAILABLE = True
    logger.info("✅ [Services] Agents GPT importés avec succès")
except ImportError as e:
    logger.warning(f"⚠️ [Services] Agents GPT non disponibles: {e}")
    # Mocks pour les agents
    class MockAgent:
        async def enrich_question(self, *args, **kwargs):
            return {"enriched_question": args[0], "method_used": "mock", "entities_used": []}
        async def enhance_rag_answer(self, *args, **kwargs):
            return {"enhanced_answer": args[0], "optional_clarifications": [], "method_used": "mock"}
    agent_contextualizer = MockAgent()
    agent_rag_enhancer = MockAgent()
    AGENTS_AVAILABLE = False

# 🧠 NOUVEAU IMPORT: Mémoire conversationnelle
try:
    from .conversation_memory import IntelligentConversationMemory
    CONVERSATION_MEMORY_AVAILABLE = True
    logger.info("✅ [Services] Mémoire conversationnelle importée")
except ImportError as e:
    logger.warning(f"⚠️ [Services] Mémoire conversationnelle non disponible: {e}")
    # Mock pour mémoire avec support clarification
    class MockConversationMemory:
        def get_conversation_context(self, conversation_id):
            return None
        
        def add_message_to_conversation(self, *args, **kwargs):
            pass
        
        def mark_pending_clarification(self, conversation_id, question, critical_entities):
            """🚀 NOUVEAU: Marquer clarification pendante"""
            logger.info(f"🛑 [Mock Memory] Clarification critique marquée: {critical_entities}")
            return True
        
        def clear_pending_clarification(self, conversation_id):
            """Nettoyer clarification résolue"""
            logger.info("✅ [Mock Memory] Clarification résolue")
            return True
    
    CONVERSATION_MEMORY_AVAILABLE = False

# Imports optionnels avec fallbacks
try:
    from .api_enhancement_service import APIEnhancementService
    API_ENHANCEMENT_AVAILABLE = True
except ImportError:
    class APIEnhancementService:
        def detect_vagueness(self, question, language):
            return None
    API_ENHANCEMENT_AVAILABLE = False

try:
    from .prompt_templates import build_structured_prompt, extract_context_from_entities, validate_prompt_context, build_clarification_prompt
    PROMPT_TEMPLATES_AVAILABLE = True
except ImportError:
    def build_structured_prompt(documents, question, context):
        return f"Documents: {documents}\nQuestion: {question}\nContext: {context}"
    def extract_context_from_entities(entities):
        return entities or {}
    PROMPT_TEMPLATES_AVAILABLE = False

logger = logging.getLogger(__name__)

# =============================================================================
# 🚀 NOUVEAU : SYSTÈME CLARIFICATION CRITIQUE VS NON CRITIQUE
# =============================================================================

def analyze_question_for_clarification_enhanced(question: str, language: str = "fr") -> dict:
    """
    🛑 ANALYSE CLARIFICATION CRITIQUE vs NON CRITIQUE
    
    🚀 LOGIQUE:
    - CRITIQUE: Informations essentielles manquantes, stoppe le pipeline
    - NON CRITIQUE: Suggestions d'amélioration, ne stoppe pas
    
    Returns:
        dict: {
            "clarification_required_critical": bool,
            "clarification_required_optional": bool, 
            "missing_critical_entities": list,
            "missing_optional_entities": list,
            "confidence": float,
            "reasoning": str
        }
    """
    
    question_lower = question.lower()
    
    # 🐔 DÉTECTION TYPE VOLAILLE
    poultry_type = detect_poultry_type(question_lower)
    
    logger.info(f"🔍 [Critical Clarification] Type volaille détecté: {poultry_type}")
    
    # LOGIQUE CLARIFICATION SELON TYPE
    if poultry_type == "layers":  # Pondeuses
        return analyze_layer_clarification_critical(question_lower, language)
    elif poultry_type == "broilers":  # Poulets de chair
        return analyze_broiler_clarification_critical(question_lower, language)
    else:  # Indéterminé
        return analyze_general_clarification_critical(question_lower, language)

def analyze_layer_clarification_critical(question_lower: str, language: str) -> dict:
    """
    🥚 ANALYSE CLARIFICATION CRITIQUE PONDEUSES
    
    CRITIQUES: race (pour dosages), âge production (pour normes)
    NON CRITIQUES: logement, éclairage, détails secondaires
    """
    
    critical_missing = []
    optional_missing = []
    confidence = 0.0
    
    # ENTITÉS CRITIQUES pour pondeuses
    critical_layer_info = {
        "breed": ["isa", "brown", "lohmann", "hy-line", "race", "souche", "breed"],
        "production_stage": ["semaine", "semaines", "week", "weeks", "âge", "age", "mois", "months", "début", "pic", "fin"]
    }
    
    # ENTITÉS NON CRITIQUES
    optional_layer_info = {
        "production_rate": ["œufs/jour", "eggs/day", "production", "combien", "how many"],
        "housing": ["cage", "sol", "parcours", "free range", "battery", "barn"],
        "lighting": ["lumière", "éclairage", "light", "hours", "heures"],
        "feeding": ["alimentation", "feed", "nutrition", "protein", "protéine"]
    }
    
    # Vérifier entités CRITIQUES
    for info_type, keywords in critical_layer_info.items():
        if not any(keyword in question_lower for keyword in keywords):
            critical_missing.append(info_type)
            confidence += 0.4  # Plus élevé pour critique
    
    # Vérifier entités NON CRITIQUES
    for info_type, keywords in optional_layer_info.items():
        if not any(keyword in question_lower for keyword in keywords):
            optional_missing.append(info_type)
            confidence += 0.1  # Plus faible pour optionnel
    
    # DÉCISION CRITIQUE
    is_critical = len(critical_missing) >= 1  # Au moins 1 entité critique manquante
    is_optional = len(optional_missing) >= 2   # Au moins 2 entités optionnelles manquantes
    
    logger.info(f"🥚 [Layer Critical] Critique: {critical_missing}, Optionnel: {optional_missing}")
    
    return {
        "clarification_required_critical": is_critical,
        "clarification_required_optional": is_optional,
        "missing_critical_entities": critical_missing,
        "missing_optional_entities": optional_missing,
        "confidence": min(confidence, 0.9),
        "reasoning": f"Pondeuses - Entités critiques manquantes: {critical_missing}",
        "poultry_type": "layers"
    }

def analyze_broiler_clarification_critical(question_lower: str, language: str) -> dict:
    """
    🍗 ANALYSE CLARIFICATION CRITIQUE POULETS DE CHAIR
    
    CRITIQUES: race (dosages différents), âge (courbes croissance), sexe (performances)
    NON CRITIQUES: environnement, conditions secondaires
    """
    
    critical_missing = []
    optional_missing = []
    confidence = 0.0
    
    # ENTITÉS CRITIQUES pour poulets de chair
    critical_broiler_info = {
        "breed": ["ross", "cobb", "hubbard", "race", "souche", "breed", "strain"],
        "age": ["jour", "jours", "day", "days", "semaine", "week", "âge", "age"],
        "sex": ["mâle", "male", "femelle", "female", "mixte", "mixed", "sexe", "sex"]
    }
    
    # ENTITÉS NON CRITIQUES
    optional_broiler_info = {
        "weight": ["poids", "weight", "peso", "gramme", "kg", "g"],
        "housing": ["température", "temperature", "ventilation", "density", "densité"],
        "feeding": ["alimentation", "feed", "fcr", "conversion", "nutrition"]
    }
    
    # Vérifier entités CRITIQUES
    for info_type, keywords in critical_broiler_info.items():
        if not any(keyword in question_lower for keyword in keywords):
            critical_missing.append(info_type)
            confidence += 0.3
    
    # Vérifier entités NON CRITIQUES
    for info_type, keywords in optional_broiler_info.items():
        if not any(keyword in question_lower for keyword in keywords):
            optional_missing.append(info_type)
            confidence += 0.1
    
    # DÉCISION CRITIQUE - Plus strict pour poulets de chair
    is_critical = len(critical_missing) >= 2  # Au moins 2 entités critiques manquantes
    is_optional = len(optional_missing) >= 1   # Au moins 1 entité optionnelle manquante
    
    logger.info(f"🍗 [Broiler Critical] Critique: {critical_missing}, Optionnel: {optional_missing}")
    
    return {
        "clarification_required_critical": is_critical,
        "clarification_required_optional": is_optional,
        "missing_critical_entities": critical_missing,
        "missing_optional_entities": optional_missing,
        "confidence": confidence,
        "reasoning": f"Poulets de chair - Entités critiques manquantes: {critical_missing}",
        "poultry_type": "broilers"
    }

def analyze_general_clarification_critical(question_lower: str, language: str) -> dict:
    """
    ❓ ANALYSE CLARIFICATION GÉNÉRALE
    
    CRITIQUE: Type de volaille indéterminé
    NON CRITIQUE: Détails spécifiques
    """
    
    logger.info("❓ [General Critical] Type volaille indéterminé - clarification critique requise")
    
    return {
        "clarification_required_critical": True,  # Type indéterminé = critique
        "clarification_required_optional": False,
        "missing_critical_entities": ["poultry_type", "species"],
        "missing_optional_entities": ["breed", "age", "purpose"],
        "confidence": 0.8,
        "reasoning": "Type de volaille indéterminé - clarification critique nécessaire",
        "poultry_type": "unknown"
    }

def detect_poultry_type(question_lower: str) -> str:
    """
    🔧 Détection type volaille ENHANCED avec fallback intelligent
    Analyse par mots-clés + vérification races via clarification_entities
    """
    
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
    
    # Étape 1: Comptage occurrences mots-clés
    layer_score = sum(1 for keyword in layer_keywords if keyword in question_lower)
    broiler_score = sum(1 for keyword in broiler_keywords if keyword in question_lower)
    
    logger.info(f"🔍 [Enhanced Detection] Layer score: {layer_score}, Broiler score: {broiler_score}")
    
    # Étape 2: Si résultat clair via mots-clés, l'utiliser
    if layer_score > broiler_score:
        logger.info("🔍 [Enhanced Detection] Type déterminé par mots-clés: layers")
        return "layers"
    elif broiler_score > layer_score:
        logger.info("🔍 [Enhanced Detection] Type déterminé par mots-clés: broilers")
        return "broilers"
    
    # Étape 3: Si indécis, analyser les races mentionnées
    logger.info("🔍 [Enhanced Detection] Scores égaux, analyse des races...")
    
    try:
        potential_breeds = extract_breeds_from_question(question_lower)
        logger.info(f"🔍 [Enhanced Detection] Races détectées: {potential_breeds}")
        
        if potential_breeds:
            for breed in potential_breeds:
                # Normaliser la race et obtenir son type
                normalized_breed, _ = normalize_breed_name(breed)
                breed_type = get_breed_type(normalized_breed)
                
                if breed_type == "layers":
                    logger.info(f"🔍 [Enhanced Detection] Race {breed} → layers via clarification_entities")
                    return "layers"
                elif breed_type == "broilers":
                    logger.info(f"🔍 [Enhanced Detection] Race {breed} → broilers via clarification_entities")
                    return "broilers"
                    
    except Exception as e:
        logger.warning(f"⚠️ [Enhanced Detection] Erreur analyse breeds: {e}")
    
    # Étape 4: Fallback final - indéterminé
    logger.info("🔍 [Enhanced Detection] Type indéterminé après analyse complète")
    return "unknown"

def extract_breeds_from_question(question_lower: str) -> List[str]:
    """
    🔍 Extrait les races mentionnées dans la question
    """
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
        matches = re.findall(pattern, question_lower, re.IGNORECASE)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    breed = next((m.strip() for m in match if m.strip()), "")
                else:
                    breed = match.strip()
                
                if breed and 2 <= len(breed) <= 25:
                    found_breeds.append(breed)
    
    # Déduplication
    unique_breeds = []
    seen = set()
    for breed in found_breeds:
        breed_clean = breed.lower()
        if breed_clean not in seen:
            unique_breeds.append(breed)
            seen.add(breed_clean)
    
    return unique_breeds

def generate_critical_clarification_message(missing_entities: List[str], poultry_type: str, language: str) -> str:
    """
    🛑 Génère le message de clarification critique selon le type et la langue
    """
    
    messages = {
        "fr": {
            "layers": {
                "breed": "Précisez la race de vos pondeuses (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                "production_stage": "Indiquez l'âge ou le stade de production de vos pondeuses",
                "general": "Pour vous donner une réponse précise sur vos pondeuses, j'ai besoin de connaître :"
            },
            "broilers": {
                "breed": "Précisez la race/souche de vos poulets (Ross 308, Cobb 500, Hubbard, etc.)",
                "age": "Indiquez l'âge de vos poulets (en jours ou semaines)",
                "sex": "Précisez s'il s'agit de mâles, femelles, ou un troupeau mixte",
                "general": "Pour vous donner une réponse précise sur vos poulets de chair, j'ai besoin de connaître :"
            },
            "unknown": {
                "poultry_type": "Précisez le type de volailles (pondeuses, poulets de chair, etc.)",
                "species": "Indiquez l'espèce exacte de vos animaux",
                "general": "Pour vous donner une réponse précise, j'ai besoin de connaître :"
            }
        },
        "en": {
            "layers": {
                "breed": "Specify the breed of your laying hens (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                "production_stage": "Indicate the age or production stage of your laying hens",
                "general": "To give you a precise answer about your laying hens, I need to know:"
            },
            "broilers": {
                "breed": "Specify the breed/strain of your chickens (Ross 308, Cobb 500, Hubbard, etc.)",
                "age": "Indicate the age of your chickens (in days or weeks)",
                "sex": "Specify if they are males, females, or a mixed flock",
                "general": "To give you a precise answer about your broilers, I need to know:"
            },
            "unknown": {
                "poultry_type": "Specify the type of poultry (laying hens, broilers, etc.)",
                "species": "Indicate the exact species of your animals",
                "general": "To give you a precise answer, I need to know:"
            }
        },
        "es": {
            "layers": {
                "breed": "Especifique la raza de sus gallinas ponedoras (ISA Brown, Lohmann Brown, Hy-Line, etc.)",
                "production_stage": "Indique la edad o etapa de producción de sus gallinas ponedoras",
                "general": "Para darle una respuesta precisa sobre sus gallinas ponedoras, necesito saber:"
            },
            "broilers": {
                "breed": "Especifique la raza/cepa de sus pollos (Ross 308, Cobb 500, Hubbard, etc.)",
                "age": "Indique la edad de sus pollos (en días o semanas)",
                "sex": "Especifique si son machos, hembras, o una bandada mixta",
                "general": "Para darle una respuesta precisa sobre sus pollos de engorde, necesito saber:"
            },
            "unknown": {
                "poultry_type": "Especifique el tipo de aves (gallinas ponedoras, pollos de engorde, etc.)",
                "species": "Indique la especie exacta de sus animales",
                "general": "Para darle una respuesta precisa, necesito saber:"
            }
        }
    }
    
    lang = language if language in messages else "fr"
    type_messages = messages[lang].get(poultry_type, messages[lang]["unknown"])
    
    # Construire le message
    general_msg = type_messages["general"]
    specific_msgs = []
    
    for entity in missing_entities:
        if entity in type_messages:
            specific_msgs.append(f"• {type_messages[entity]}")
    
    if specific_msgs:
        return f"{general_msg}\n\n" + "\n".join(specific_msgs)
    else:
        return general_msg

# =============================================================================
# 🚀 SERVICE PRINCIPAL EXPERT AVEC PIPELINE CLARIFICATION CRITIQUE
# =============================================================================

class ExpertService:
    """Service principal pour le système expert avec clarification critique"""
    
    def __init__(self):
        self.integrations = IntegrationsManager()
        self.enhancement_service = APIEnhancementService() if API_ENHANCEMENT_AVAILABLE else None
        
        # 🧠 Initialiser la mémoire conversationnelle
        if CONVERSATION_MEMORY_AVAILABLE:
            try:
                self.conversation_memory = IntelligentConversationMemory()
                logger.info("✅ [Expert Service] Mémoire conversationnelle initialisée")
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur init mémoire: {e}")
                self.conversation_memory = MockConversationMemory()
        else:
            self.conversation_memory = MockConversationMemory()
            logger.warning("⚠️ [Expert Service] Mémoire conversationnelle mock utilisée")
        
        # Configuration avec clarification critique
        self.config = {
            "enable_concise_responses": True,
            "default_concision_level": ConcisionLevel.CONCISE,
            "max_response_length": {"ultra_concise": 50, "concise": 200, "standard": 500, "detailed": 1000},
            "fallback_mode": not all([MODELS_AVAILABLE, UTILS_AVAILABLE, INTEGRATIONS_AVAILABLE]),
            # 🚀 NOUVEAU: Clarification critique bloquante
            "critical_clarification_blocking": True,
            "optional_clarification_non_blocking": True,
            # 🤖 Agents toujours actifs
            "agents_always_active": True,
            "agents_enabled": AGENTS_AVAILABLE,
            "conversation_memory_enabled": CONVERSATION_MEMORY_AVAILABLE
        }
        
        logger.info("🚀 [Expert Service] Service expert initialisé avec clarification critique")
        logger.info(f"🛑 [Expert Service] Clarification critique bloquante: {self.config['critical_clarification_blocking']}")
        logger.info(f"💡 [Expert Service] Clarification optionnelle non bloquante: {self.config['optional_clarification_non_blocking']}")
    
    def get_current_user_dependency(self):
        """Retourne la dépendance pour l'authentification"""
        return self.integrations.get_current_user_dependency()
    
    async def process_expert_question(
        self,
        request_data: EnhancedQuestionRequest,
        request: Request,
        current_user: Optional[Dict[str, Any]] = None,
        start_time: float = None
    ) -> EnhancedExpertResponse:
        """🚀 MÉTHODE PRINCIPALE AVEC CLARIFICATION CRITIQUE"""
        
        if start_time is None:
            start_time = time.time()
        
        try:
            logger.info("🚀 [ExpertService] Traitement avec clarification critique")
            
            # Extraction sécurisée des paramètres
            question_text = getattr(request_data, 'text', 'Question vide')
            language = getattr(request_data, 'language', 'fr')
            conversation_id = getattr(request_data, 'conversation_id', None) or str(uuid.uuid4())
            
            logger.info(f"📝 [ExpertService] Question: '{question_text[:100]}...'")
            logger.info(f"🌐 [ExpertService] Langue: {language}")
            logger.info(f"🆔 [ExpertService] Conversation: {conversation_id}")
            
            # Variables de traitement
            processing_steps = ["initialization", "parameter_extraction"]
            ai_enhancements_used = []
            
            # === AUTHENTIFICATION SÉCURISÉE ===
            user_id = self._extract_user_id_safe(current_user, request_data, request)
            user_email = current_user.get("email") if current_user else None
            
            processing_steps.append("authentication")
            
            # === VALIDATION QUESTION ===
            if not question_text or len(question_text.strip()) < 3:
                return self._create_error_response(
                    "Question trop courte", question_text, conversation_id, language, start_time
                )
            
            processing_steps.append("question_validation")
            
            # === MODE FALLBACK ===
            if self.config["fallback_mode"]:
                logger.info("🔄 [ExpertService] Mode fallback activé")
                return await self._process_question_fallback(
                    question_text, conversation_id, language, user_email, start_time, processing_steps
                )
            
            # === TRAITEMENT PIPELINE AVEC CLARIFICATION CRITIQUE ===
            return await self._process_question_critical_clarification_pipeline(
                request_data, request, current_user, start_time, processing_steps, ai_enhancements_used,
                question_text, language, conversation_id, user_id
            )
                
        except Exception as e:
            logger.error(f"❌ [ExpertService] Erreur critique: {e}")
            return self._create_error_response(
                f"Erreur interne: {str(e)}", 
                getattr(request_data, 'text', 'Question inconnue'), 
                getattr(request_data, 'conversation_id', str(uuid.uuid4())), 
                getattr(request_data, 'language', 'fr'), 
                start_time
            )
    
    async def _process_question_critical_clarification_pipeline(
        self, request_data, request, current_user, start_time, processing_steps, ai_enhancements_used,
        question_text, language, conversation_id, user_id
    ) -> EnhancedExpertResponse:
        """🛑 NOUVEAU: Pipeline avec clarification critique bloquante"""
        
        logger.info("🛑 [ExpertService] Pipeline clarification critique activé")
        processing_steps.append("critical_clarification_pipeline_activated")
        
        # === TRAITEMENT CLARIFICATION (SI APPLICABLE) ===
        is_clarification = getattr(request_data, 'is_clarification_response', False)
        
        if is_clarification:
            logger.info("🎪 [ExpertService] Mode clarification détecté")
            processing_steps.append("clarification_mode_detected")
            
            clarification_result = self._process_clarification_enhanced(request_data, processing_steps, language)
            if clarification_result:
                return clarification_result
        
        # === VALIDATION AGRICOLE ===
        if self.integrations.agricultural_validator_available:
            try:
                validation_result = await self._validate_agricultural_question_safe(
                    question_text, language, current_user
                )
                processing_steps.append("agricultural_validation")
                
                if not validation_result.is_valid:
                    return self._create_validation_error_response(
                        validation_result, question_text, conversation_id, language, start_time
                    )
            except Exception as e:
                logger.warning(f"⚠️ [ExpertService] Erreur validation agricole: {e}")
        
        # 🛑 === ÉTAPE CRITIQUE: ANALYSE CLARIFICATION AVANT RAG ===
        try:
            logger.info("🛑 [Pipeline] Analyse clarification critique AVANT RAG")
            
            # 🚀 MODIFICATION 1: Utiliser la fonction d'analyse critique
            if hasattr(self.integrations, '_clarification_functions') and 'analyze_question_for_clarification_enhanced' in self.integrations._clarification_functions:
                clarification_result = self.integrations._clarification_functions['analyze_question_for_clarification_enhanced'](question_text, language)
            else:
                # Fallback vers notre fonction locale
                clarification_result = analyze_question_for_clarification_enhanced(question_text, language)
            
            processing_steps.append("critical_clarification_analysis")
            ai_enhancements_used.append("critical_clarification_analysis")
            
            # 🛑 MODIFICATION 2: Vérifier si clarification critique requise
            if clarification_result.get("clarification_required_critical", False):
                logger.info("🛑 [Pipeline] Clarification critique requise - ARRÊT AVANT RAG")
                processing_steps.append("critical_clarification_blocking")
                
                # 🚀 MODIFICATION 3: Marquer dans la mémoire
                missing_critical_entities = clarification_result.get("missing_critical_entities", [])
                
                try:
                    self.conversation_memory.mark_pending_clarification(
                        conversation_id, question_text, missing_critical_entities
                    )
                    logger.info(f"🧠 [Pipeline] Clarification critique marquée en mémoire: {missing_critical_entities}")
                except Exception as e:
                    logger.error(f"❌ [Pipeline] Erreur marquage mémoire: {e}")
                
                # 🚀 MODIFICATION 4: Générer message de clarification critique
                poultry_type = clarification_result.get("poultry_type", "unknown")
                critical_message = generate_critical_clarification_message(
                    missing_critical_entities, poultry_type, language
                )
                
                # 🚀 MODIFICATION 5: Retourner immédiatement la réponse de clarification
                response_time_ms = int((time.time() - start_time) * 1000)
                
                if MODELS_AVAILABLE:
                    return EnhancedExpertResponse(
                        question=question_text,
                        response=critical_message,
                        conversation_id=conversation_id,
                        rag_used=False,
                        rag_score=None,
                        timestamp=datetime.now().isoformat(),
                        language=language,
                        response_time_ms=response_time_ms,
                        mode="clarification_blocking",
                        user=current_user.get("email") if current_user else None,
                        logged=True,
                        validation_passed=True,
                        processing_steps=processing_steps,
                        ai_enhancements_used=ai_enhancements_used,
                        # 🚀 NOUVEAUX CHAMPS CLARIFICATION CRITIQUE
                        clarification_required_critical=True,
                        missing_critical_entities=missing_critical_entities,
                        clarification_confidence=clarification_result.get("confidence", 0.8),
                        clarification_reasoning=clarification_result.get("reasoning", "Informations critiques manquantes"),
                        pipeline_version="critical_clarification",
                        pipeline_blocked_at="before_rag"
                    )
                else:
                    return self._create_basic_response(
                        question_text, critical_message, conversation_id, 
                        language, response_time_ms, processing_steps
                    )
                
        except Exception as e:
            logger.error(f"❌ [Pipeline] Erreur analyse clarification critique: {e}")
            # Continuer le pipeline normal en cas d'erreur
            processing_steps.append("critical_clarification_error_continue")
        
        # 🚀 === PIPELINE NORMAL SI PAS DE CLARIFICATION CRITIQUE ===
        logger.info("✅ [Pipeline] Pas de clarification critique - continuation pipeline normal")
        
        try:
            # 🧠 ÉTAPE 1: RÉCUPÉRATION CONTEXTE CONVERSATIONNEL
            conversation_context = None
            entities = {}
            missing_entities = []
            formatted_context = ""
            
            if self.conversation_memory:
                try:
                    conversation_context = self.conversation_memory.get_conversation_context(conversation_id)
                    if conversation_context:
                        entities = conversation_context.consolidated_entities.to_dict()
                        missing_entities = conversation_context.get_missing_entities()
                        formatted_context = conversation_context.get_formatted_context()
                        
                        logger.info(f"🧠 [Pipeline] Contexte récupéré: {len(entities)} entités")
                    else:
                        logger.info("🆕 [Pipeline] Nouvelle conversation")
                except Exception as e:
                    logger.error(f"❌ [Pipeline] Erreur récupération contexte: {e}")
            
            # 🤖 ÉTAPE 2: AGENT CONTEXTUALIZER - TOUJOURS ACTIF
            question_for_rag = question_text
            contextualization_info = {}
            
            if self.config["agents_enabled"]:
                try:
                    logger.info("🤖 [Pipeline] Agent Contextualizer - TOUJOURS ACTIF")
                    
                    contextualization_result = await agent_contextualizer.enrich_question(
                        question=question_text,
                        entities=entities,
                        missing_entities=missing_entities,
                        conversation_context=formatted_context,
                        language=language
                    )
                    
                    question_for_rag = contextualization_result["enriched_question"]
                    contextualization_info = contextualization_result
                    ai_enhancements_used.append(f"contextualizer_{contextualization_result['method_used']}")
                    
                    if question_for_rag != question_text:
                        logger.info(f"✨ [Pipeline] Question enrichie par agent")
                    else:
                        logger.info("📝 [Pipeline] Question maintenue (déjà optimale)")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline] Erreur Agent Contextualizer: {e}")
                    question_for_rag = question_text
            
            # 💡 ÉTAPE 2.5: SUGGESTIONS CLARIFICATION NON CRITIQUES (NON BLOQUANTES)
            optional_clarifications = []
            
            if self.config["optional_clarification_non_blocking"] and not is_clarification:
                try:
                    logger.info("💡 [Pipeline] Génération suggestions clarification optionnelles")
                    
                    # Utiliser le résultat déjà calculé ou recalculer
                    if 'clarification_result' not in locals():
                        if hasattr(self.integrations, '_clarification_functions') and 'analyze_question_for_clarification_enhanced' in self.integrations._clarification_functions:
                            clarification_result = self.integrations._clarification_functions['analyze_question_for_clarification_enhanced'](question_text, language)
                        else:
                            clarification_result = analyze_question_for_clarification_enhanced(question_text, language)
                    
                    if clarification_result.get("clarification_required_optional", False):
                        optional_missing = clarification_result.get("missing_optional_entities", [])
                        if optional_missing:
                            optional_clarifications = self._generate_optional_clarification_suggestions(
                                optional_missing, clarification_result.get("poultry_type", "unknown"), language
                            )
                            ai_enhancements_used.append("optional_clarification_suggestions")
                            
                        logger.info(f"💡 [Pipeline] {len(optional_clarifications)} suggestions optionnelles générées")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline] Erreur suggestions optionnelles: {e}")
            
            # 🤖 ÉTAPE 3: TRAITEMENT RAG AVEC QUESTION ENRICHIE
            rag_answer = ""
            rag_score = None
            mode = "unknown"
            
            # Vérifier disponibilité RAG
            app = request.app
            process_rag = getattr(app.state, 'process_question_with_rag', None)
            
            if process_rag:
                logger.info("🔍 [Pipeline] Système RAG disponible - Question enrichie utilisée")
                processing_steps.append("rag_processing_with_enriched_question")
                ai_enhancements_used.append("rag_system_enriched")
                
                result = await process_rag(
                    question=question_for_rag,
                    user=current_user,
                    language=language,
                    speed_mode=getattr(request_data, 'speed_mode', 'balanced')
                )
                
                rag_answer = str(result.get("response", ""))
                rag_score = result.get("score", 0.0)
                mode = "rag_processing_with_enriched_question"
                
            else:
                logger.info("🔄 [Pipeline] RAG non disponible - Fallback avec question enrichie")
                processing_steps.append("no_rag_fallback_enriched")
                
                fallback_data = self._generate_fallback_responses(question_for_rag, language)
                rag_answer = fallback_data["response"]
                rag_score = None
                mode = "no_rag_fallback_enriched"
            
            # 🤖 ÉTAPE 4: AGENT RAG ENHANCER - AVEC QUESTION ENRICHIE
            final_answer = rag_answer
            enhancement_info = {}
            additional_clarifications = []
            
            if self.config["agents_enabled"]:
                try:
                    logger.info("🔧 [Pipeline] Agent RAG Enhancer avec question enrichie")
                    
                    enhancement_result = await agent_rag_enhancer.enhance_rag_answer(
                        rag_answer=rag_answer,
                        entities=entities,
                        missing_entities=missing_entities,
                        conversation_context=formatted_context,
                        original_question=question_text,
                        enriched_question=question_for_rag,
                        language=language
                    )
                    
                    final_answer = enhancement_result["enhanced_answer"]
                    additional_clarifications.extend(enhancement_result.get("optional_clarifications", []))
                    enhancement_info = enhancement_result
                    ai_enhancements_used.append(f"rag_enhancer_{enhancement_result['method_used']}")
                    
                    if final_answer != rag_answer:
                        logger.info(f"🔧 [Pipeline] Réponse améliorée par agent")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline] Erreur Agent RAG Enhancer: {e}")
                    final_answer = rag_answer if rag_answer else self._generate_fallback_responses(question_for_rag, language)["response"]
            
            # 💡 ÉTAPE 5: CONSOLIDATION CLARIFICATIONS OPTIONNELLES
            all_optional_clarifications = []
            
            if optional_clarifications:
                all_optional_clarifications.extend(optional_clarifications)
            
            if additional_clarifications:
                all_optional_clarifications.extend(additional_clarifications)
            
            # Déduplication
            unique_optional_clarifications = list(dict.fromkeys(all_optional_clarifications))
            
            if unique_optional_clarifications:
                logger.info(f"💡 [Pipeline] {len(unique_optional_clarifications)} clarifications optionnelles consolidées")
            
            # 🧠 ÉTAPE 6: MISE À JOUR MÉMOIRE CONVERSATIONNELLE
            if self.conversation_memory:
                try:
                    # Ajouter la question utilisateur (enrichie pour l'historique)
                    self.conversation_memory.add_message_to_conversation(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        message=question_for_rag,
                        role="user",
                        language=language
                    )
                    
                    # Ajouter la réponse système
                    self.conversation_memory.add_message_to_conversation(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        message=final_answer,
                        role="assistant",
                        language=language
                    )
                    
                    processing_steps.append("conversation_memory_updated")
                    
                except Exception as e:
                    logger.error(f"❌ [Pipeline] Erreur mise à jour mémoire: {e}")
            
        except Exception as e:
            logger.error(f"❌ [Pipeline] Erreur traitement pipeline normal: {e}")
            processing_steps.append("pipeline_error_fallback")
            
            try:
                if self.config["agents_enabled"]:
                    error_enhancement = await agent_rag_enhancer.enhance_rag_answer(
                        rag_answer=f"Je m'excuse, il y a eu une erreur technique: {str(e)}",
                        entities={},
                        missing_entities=[],
                        conversation_context="",
                        original_question=question_text,
                        enriched_question=question_text,
                        language=language
                    )
                    final_answer = error_enhancement["enhanced_answer"]
                else:
                    raise e
            except:
                fallback_data = self._generate_fallback_responses(question_text, language)
                final_answer = fallback_data["response"]
            
            rag_score = None
            mode = "pipeline_error_fallback"
            enhancement_info = {}
            unique_optional_clarifications = []
            contextualization_info = {}
        
        # === CONSTRUCTION RÉPONSE FINALE ===
        response_time_ms = int((time.time() - start_time) * 1000)
        user_email = current_user.get("email") if current_user else None
        
        # Construire la réponse avec toutes les améliorations
        response = EnhancedExpertResponse(
            question=question_text,
            response=final_answer,
            conversation_id=conversation_id,
            rag_used=bool(rag_score),
            rag_score=rag_score,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode=mode,
            user=user_email,
            logged=True,
            validation_passed=True,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used
        )
        
        # Métadonnées pipeline avec clarification critique
        if self.config["agents_enabled"]:
            if contextualization_info:
                response.contextualization_info = contextualization_info
                response.enriched_question = question_for_rag
                
            if enhancement_info:
                response.enhancement_info = enhancement_info
        
        # Clarifications optionnelles (non bloquantes)
        if unique_optional_clarifications:
            response.optional_clarifications = unique_optional_clarifications
            response.clarification_mode = "optional_non_blocking"
        
        # Métadonnées mémoire
        if self.conversation_memory and conversation_context:
            response.conversation_context = {
                "total_exchanges": conversation_context.total_exchanges,
                "conversation_urgency": conversation_context.conversation_urgency,
                "entities_count": len([k for k, v in entities.items() if v is not None]),
                "missing_entities": missing_entities,
                "overall_confidence": conversation_context.consolidated_entities.confidence_overall
            }
        
        # Marquer comme pipeline avec clarification critique
        response.pipeline_version = "critical_clarification"
        response.pipeline_improvements = [
            "agents_always_active",
            "critical_clarification_blocking",
            "optional_clarification_non_blocking", 
            "enriched_question_to_rag",
            "intelligent_fallback"
        ]
        
        return response
    
    def _generate_optional_clarification_suggestions(self, missing_entities: List[str], poultry_type: str, language: str) -> List[str]:
        """
        💡 Génère des suggestions de clarification optionnelles (non bloquantes)
        """
        
        suggestions = {
            "fr": {
                "layers": {
                    "production_rate": "Combien d'œufs produisent-elles actuellement par jour ?",
                    "housing": "Comment sont-elles logées ? (cages, sol, parcours libre)",
                    "lighting": "Combien d'heures de lumière reçoivent-elles par jour ?",
                    "feeding": "Quel type d'alimentation utilisez-vous ?"
                },
                "broilers": {
                    "weight": "Quel est leur poids actuel ?",
                    "housing": "Quelles sont les conditions d'élevage ? (température, densité)",
                    "feeding": "Quel type d'aliment utilisez-vous ? (démarrage, croissance, finition)"
                },
                "unknown": {
                    "breed": "Quelle est la race exacte de vos volailles ?",
                    "age": "Quel est l'âge de vos animaux ?",
                    "purpose": "Quel est l'objectif de votre élevage ?"
                }
            },
            "en": {
                "layers": {
                    "production_rate": "How many eggs are they currently producing per day?",
                    "housing": "How are they housed? (cages, floor, free range)",
                    "lighting": "How many hours of light do they receive per day?",
                    "feeding": "What type of feed are you using?"
                },
                "broilers": {
                    "weight": "What is their current weight?",
                    "housing": "What are the farming conditions? (temperature, density)",
                    "feeding": "What type of feed are you using? (starter, grower, finisher)"
                },
                "unknown": {
                    "breed": "What is the exact breed of your poultry?",
                    "age": "What is the age of your animals?",
                    "purpose": "What is the purpose of your farming?"
                }
            },
            "es": {
                "layers": {
                    "production_rate": "¿Cuántos huevos están produciendo actualmente por día?",
                    "housing": "¿Cómo están alojadas? (jaulas, suelo, corral libre)",
                    "lighting": "¿Cuántas horas de luz reciben por día?",
                    "feeding": "¿Qué tipo de alimento está usando?"
                },
                "broilers": {
                    "weight": "¿Cuál es su peso actual?",
                    "housing": "¿Cuáles son las condiciones de cría? (temperatura, densidad)",
                    "feeding": "¿Qué tipo de alimento está usando? (iniciador, crecimiento, acabado)"
                },
                "unknown": {
                    "breed": "¿Cuál es la raza exacta de sus aves?",
                    "age": "¿Cuál es la edad de sus animales?",
                    "purpose": "¿Cuál es el propósito de su cría?"
                }
            }
        }
        
        lang = language if language in suggestions else "fr"
        type_suggestions = suggestions[lang].get(poultry_type, suggestions[lang]["unknown"])
        
        result = []
        for entity in missing_entities:
            if entity in type_suggestions:
                result.append(type_suggestions[entity])
        
        return result
    
    # === TOUTES LES AUTRES MÉTHODES PRÉSERVÉES ===
    
    def _process_clarification_enhanced(self, request_data, processing_steps, language) -> Optional[EnhancedExpertResponse]:
        """Traitement clarification avec auto-détection pondeuses"""
        
        original_question = getattr(request_data, 'original_question', None)
        clarification_text = getattr(request_data, 'text', '')
        conversation_id = getattr(request_data, 'conversation_id', str(uuid.uuid4()))
        
        if not original_question:
            logger.warning("⚠️ [ExpertService] Clarification sans question originale")
            return None
        
        # Extraction entités avec auto-détection pondeuses
        if UTILS_AVAILABLE:
            entities = extract_breed_and_sex_from_clarification(clarification_text, language)
        else:
            entities = self._extract_entities_fallback(clarification_text)
        
        if not entities:
            entities = {"breed": None, "sex": None}
        
        logger.info(f"🔍 [Enhanced Clarification] Entités extraites: {entities}")
        
        # Si entités incomplètes, demander clarification
        if not entities.get('breed') or not entities.get('sex'):
            processing_steps.append("incomplete_clarification")
            
            missing = []
            if not entities.get('breed'):
                missing.append("race")
            if not entities.get('sex'):
                missing.append("sexe")
            
            # Messages d'erreur selon langue
            error_messages = {
                "fr": f"Information incomplète. Il manque encore: {', '.join(missing)}.\n\nExemples complets:\n• 'Ross 308 mâles'\n• 'Cobb 500 femelles'\n• 'ISA Brown' (pour pondeuses)",
                "en": f"Incomplete information. Still missing: {', '.join(missing)}.\n\nComplete examples:\n• 'Ross 308 males'\n• 'Cobb 500 females'\n• 'ISA Brown' (for layers)",
                "es": f"Información incompleta. Aún falta: {', '.join(missing)}.\n\nEjemplos completos:\n• 'Ross 308 machos'\n• 'Cobb 500 hembras'\n• 'ISA Brown' (para ponedoras)"
            }
            
            error_message = error_messages.get(language, error_messages["fr"])
            
            return EnhancedExpertResponse(
                question=clarification_text,
                response=error_message,
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=language,
                response_time_ms=50,
                mode="incomplete_clarification_enhanced",
                user=None,
                logged=True,
                validation_passed=False,
                processing_steps=processing_steps,
                ai_enhancements_used=["enhanced_clarification_processing", "layer_breed_auto_detection"]
            )
        
        # Enrichir la question originale
        if UTILS_AVAILABLE:
            enriched_question = build_enriched_question_with_breed_sex(
                original_question, entities['breed'], entities['sex'], language
            )
        else:
            enriched_question = f"Pour des poulets {entities['breed']} {entities['sex']}: {original_question}"
        
        request_data.text = enriched_question
        request_data.is_clarification_response = False
        
        logger.info(f"✨ [ExpertService] Question enrichie: {enriched_question}")
        processing_steps.append("question_enriched_enhanced")
        
        # 🧠 Nettoyer la clarification pendante en mémoire
        try:
            self.conversation_memory.clear_pending_clarification(conversation_id)
            logger.info("✅ [ExpertService] Clarification critique résolue en mémoire")
        except Exception as e:
            logger.error(f"❌ [ExpertService] Erreur nettoyage clarification: {e}")
        
        return None  # Continuer le traitement avec la question enrichie
    
    async def _process_question_fallback(
        self, question_text: str, conversation_id: str, language: str, 
        user_email: str, start_time: float, processing_steps: List[str]
    ) -> EnhancedExpertResponse:
        """Traitement en mode fallback"""
        
        logger.info("🔄 [ExpertService] Traitement mode fallback")
        processing_steps.append("fallback_mode_activated")
        
        # Réponses de base par type de question
        fallback_responses = self._generate_fallback_responses(question_text, language)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Construction réponse fallback
        if MODELS_AVAILABLE:
            return EnhancedExpertResponse(
                question=question_text,
                response=fallback_responses["response"],
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=language,
                response_time_ms=response_time_ms,
                mode="fallback_basic_response",
                user=user_email,
                logged=True,
                validation_passed=True,
                processing_steps=processing_steps,
                ai_enhancements_used=["fallback_response_generation"]
            )
        else:
            return self._create_basic_response(
                question_text, fallback_responses["response"], conversation_id, 
                language, response_time_ms, processing_steps
            )
    
    def _extract_entities_fallback(self, text: str) -> Dict[str, str]:
        """Extraction d'entités fallback sans dépendances externes"""
        
        entities = {}
        text_lower = text.lower()
        
        # Détection race simple avec pondeuses
        race_patterns = [
            r'\b(ross\s*308|cobb\s*500|hubbard|isa\s*brown|lohmann\s*brown|hy[-\s]*line|bovans|shaver)\b'
        ]
        
        for pattern in race_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                breed = match.group(1).strip()
                entities['breed'] = breed
                
                # Utiliser clarification_entities pour normaliser et inférer le sexe
                normalized_breed, _ = normalize_breed_name(breed)
                inferred_sex, was_inferred = infer_sex_from_breed(normalized_breed)
                
                if was_inferred and inferred_sex:
                    entities['sex'] = "femelles"
                    logger.info(f"🥚 [Fallback Auto-Fix] Race détectée: {normalized_breed} → sexe='femelles'")
                
                break
        
        # Détection sexe simple (si pas déjà fixé par pondeuses)
        if not entities.get('sex'):
            if any(sex in text_lower for sex in ['mâle', 'male']):
                entities['sex'] = 'mâles'
            elif any(sex in text_lower for sex in ['femelle', 'female']):
                entities['sex'] = 'femelles'
            elif any(sex in text_lower for sex in ['mixte', 'mixed']):
                entities['sex'] = 'mixte'
        
        return entities
    
    def _generate_fallback_responses(self, question: str, language: str) -> Dict[str, Any]:
        """Génère des réponses de fallback intelligentes"""
        
        question_lower = question.lower()
        
        # Détection et réponses spécialisées pondeuses
        if any(word in question_lower for word in ['pondeuse', 'pondeuses', 'ponte', 'œuf', 'oeufs', 'egg']):
            responses = {
                "fr": "Pour les pondeuses qui ne pondent pas assez, vérifiez : la race et l'âge (pic de ponte vers 25-30 semaines), l'alimentation (16-18% protéines), l'éclairage (14-16h/jour), le logement (espace suffisant) et l'état de santé. Une pondeuse ISA Brown produit normalement 300-320 œufs par an.",
                "en": "For laying hens not producing enough eggs, check: breed and age (peak laying around 25-30 weeks), feeding (16-18% protein), lighting (14-16h/day), housing (adequate space) and health status. An ISA Brown layer normally produces 300-320 eggs per year.",
                "es": "Para gallinas ponedoras que no ponen suficientes huevos, verifique: raza y edad (pico de puesta hacia 25-30 semanas), alimentación (16-18% proteínas), iluminación (14-16h/día), alojamiento (espacio adecuado) y estado de salud. Una ponedora ISA Brown produce normalmente 300-320 huevos por año."
            }
        # Autres détections de type de question
        elif any(word in question_lower for word in ['poids', 'weight', 'peso', 'gramme', 'kg']):
            responses = {
                "fr": "Pour une réponse précise sur le poids, j'aurais besoin de connaître la race, le sexe et l'âge des poulets. En général, un poulet de chair Ross 308 pèse environ 350-400g à 3 semaines.",
                "en": "For a precise weight answer, I would need to know the breed, sex and age of the chickens. Generally, a Ross 308 broiler weighs around 350-400g at 3 weeks.",
                "es": "Para una respuesta precisa sobre el peso, necesitaría conocer la raza, sexo y edad de los pollos. En general, un pollo de engorde Ross 308 pesa alrededor de 350-400g a las 3 semanas."
            }
        elif any(word in question_lower for word in ['mortalité', 'mortality', 'mortalidad', 'mort']):
            responses = {
                "fr": "La mortalité normale en élevage de poulets de chair est généralement inférieure à 5%. Si vous observez des taux plus élevés, vérifiez les conditions d'élevage, la ventilation et consultez un vétérinaire.",
                "en": "Normal mortality in broiler farming is generally below 5%. If you observe higher rates, check farming conditions, ventilation and consult a veterinarian.",
                "es": "La mortalidad normal en la cría de pollos de engorde es generalmente inferior al 5%. Si observa tasas más altas, verifique las condiciones de cría, ventilación y consulte a un veterinario."
            }
        elif any(word in question_lower for word in ['température', 'temperature', 'temperatura', 'chaleur']):
            responses = {
                "fr": "La température optimale pour les poulets varie selon l'âge: 35°C à 1 jour, puis diminution de 2-3°C par semaine jusqu'à 21°C vers 5-6 semaines.",
                "en": "Optimal temperature for chickens varies by age: 35°C at 1 day, then decrease by 2-3°C per week until 21°C around 5-6 weeks.",
                "es": "La temperatura óptima para pollos varía según la edad: 35°C al día 1, luego disminución de 2-3°C por semana hasta 21°C alrededor de 5-6 semanas."
            }
        elif any(word in question_lower for word in ['alimentation', 'nutrition', 'alimentación', 'nourriture']):
            responses = {
                "fr": "L'alimentation des poulets doit être adaptée à leur âge: aliment démarrage (0-10j), croissance (11-35j), finition (36j+). Assurez-vous d'un accès constant à l'eau propre.",
                "en": "Chicken feeding should be adapted to their age: starter feed (0-10d), grower (11-35d), finisher (36d+). Ensure constant access to clean water.",
                "es": "La alimentación de pollos debe adaptarse a su edad: iniciador (0-10d), crecimiento (11-35d), acabado (36d+). Asegure acceso constante a agua limpia."
            }
        else:
            responses = {
                "fr": "Je suis votre assistant IA spécialisé en santé et nutrition animale. Pour vous donner une réponse plus précise, pourriez-vous me donner plus de détails sur votre question ?",
                "en": "I am your AI assistant specialized in animal health and nutrition. To give you a more precise answer, could you provide more details about your question?",
                "es": "Soy su asistente de IA especializado en salud y nutrición animal. Para darle una respuesta más precisa, ¿podría proporcionar más detalles sobre su pregunta?"
            }
        
        return {
            "response": responses.get(language, responses["fr"]),
            "type": "fallback",
            "confidence": 0.7
        }
    
    # === AUTRES MÉTHODES UTILITAIRES INCHANGÉES ===
    
    def _extract_user_id_safe(self, current_user, request_data, request) -> str:
        """Extraction sécurisée de l'ID utilisateur"""
        try:
            if current_user and "id" in current_user:
                return current_user["id"]
            elif hasattr(request_data, 'user_id') and request_data.user_id:
                return request_data.user_id
            elif UTILS_AVAILABLE:
                return get_user_id_from_request(request)
            else:
                return f"fallback_{uuid.uuid4().hex[:8]}"
        except Exception as e:
            logger.warning(f"⚠️ [ExpertService] Erreur extraction user_id: {e}")
            return f"error_{uuid.uuid4().hex[:8]}"
    
    async def _validate_agricultural_question_safe(self, question: str, language: str, current_user) -> ValidationResult:
        """Validation agricole sécurisée"""
        try:
            if self.integrations.agricultural_validator_available:
                return self.integrations.validate_agricultural_question(
                    question=question, language=language, 
                    user_id=current_user.get("id") if current_user else "unknown",
                    request_ip="unknown"
                )
            else:
                # Validation basique par mots-clés
                agricultural_keywords = [
                    'poulet', 'chicken', 'pollo', 'élevage', 'farming', 'cría',
                    'animal', 'nutrition', 'santé', 'health', 'salud',
                    'vétérinaire', 'veterinary', 'veterinario',
                    'pondeuse', 'pondeuses', 'layer', 'layers', 'œuf', 'egg'
                ]
                
                question_lower = question.lower()
                is_agricultural = any(keyword in question_lower for keyword in agricultural_keywords)
                
                return ValidationResult(
                    is_valid=is_agricultural,
                    rejection_message="Question hors domaine agricole" if not is_agricultural else "",
                    confidence=0.8 if is_agricultural else 0.3
                )
        except Exception as e:
            logger.error(f"❌ [ExpertService] Erreur validation agricole: {e}")
            return ValidationResult(is_valid=True, rejection_message="", confidence=0.5)
    
    def _create_basic_response(self, question, response, conversation_id, language, response_time_ms, processing_steps):
        """Crée une réponse basique quand les modèles Pydantic ne sont pas disponibles"""
        return {
            "question": question,
            "response": response,
            "conversation_id": conversation_id,
            "rag_used": False,
            "rag_score": None,
            "timestamp": datetime.now().isoformat(),
            "language": language,
            "response_time_ms": response_time_ms,
            "mode": "basic_fallback_response",
            "user": None,
            "logged": True,
            "validation_passed": True,
            "processing_steps": processing_steps,
            "ai_enhancements_used": ["basic_fallback"],
            "fallback_mode": True,
            "models_available": MODELS_AVAILABLE
        }
    
    def _create_error_response(self, error_message, question, conversation_id, language, start_time):
        """Crée une réponse d'erreur"""
        response_time_ms = int((time.time() - start_time) * 1000)
        
        error_responses = {
            "fr": f"Je m'excuse, {error_message}. Veuillez reformuler votre question.",
            "en": f"I apologize, {error_message}. Please rephrase your question.",
            "es": f"Me disculpo, {error_message}. Por favor reformule su pregunta."
        }
        
        response_text = error_responses.get(language, error_responses["fr"])
        
        if MODELS_AVAILABLE:
            return EnhancedExpertResponse(
                question=question,
                response=response_text,
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=language,
                response_time_ms=response_time_ms,
                mode="error_response",
                user=None,
                logged=True,
                validation_passed=False,
                processing_steps=["error_occurred"],
                ai_enhancements_used=["error_handling"]
            )
        else:
            return self._create_basic_response(
                question, response_text, conversation_id, language, response_time_ms, ["error_occurred"]
            )
    
    def _create_validation_error_response(self, validation_result, question, conversation_id, language, start_time):
        """Crée une réponse d'erreur de validation"""
        response_time_ms = int((time.time() - start_time) * 1000)
        
        if MODELS_AVAILABLE:
            return EnhancedExpertResponse(
                question=question,
                response=validation_result.rejection_message,
                conversation_id=conversation_id,
                rag_used=False,
                rag_score=None,
                timestamp=datetime.now().isoformat(),
                language=language,
                response_time_ms=response_time_ms,
                mode="validation_error",
                user=None,
                logged=True,
                validation_passed=False,
                validation_confidence=validation_result.confidence,
                processing_steps=["validation_failed"],
                ai_enhancements_used=["agricultural_validation"]
            )
        else:
            return self._create_basic_response(
                question, validation_result.rejection_message, conversation_id, 
                language, response_time_ms, ["validation_failed"]
            )
    
    # === MÉTHODES FEEDBACK ET TOPICS (AMÉLIORÉES) ===
    
    async def process_feedback(self, feedback_data: FeedbackRequest) -> Dict[str, Any]:
        """Traitement du feedback avec gestion d'erreur"""
        try:
            rating = getattr(feedback_data, 'rating', 'neutral')
            comment = getattr(feedback_data, 'comment', None)
            conversation_id = getattr(feedback_data, 'conversation_id', None)
            
            logger.info(f"📊 [ExpertService] Feedback reçu: {rating}")
            
            # Tentative de mise à jour via intégrations
            feedback_updated = False
            if self.integrations.logging_available and conversation_id:
                try:
                    rating_numeric = {"positive": 1, "negative": -1, "neutral": 0}.get(rating, 0)
                    feedback_updated = await self.integrations.update_feedback(conversation_id, rating_numeric)
                except Exception as e:
                    logger.error(f"❌ [ExpertService] Erreur update feedback: {e}")
            
            return {
                "success": True,
                "message": "Feedback enregistré avec succès (Pipeline Clarification Critique)",
                "rating": rating,
                "comment": comment,
                "conversation_id": conversation_id,
                "feedback_updated_in_db": feedback_updated,
                "pipeline_version": "critical_clarification",
                "improvements_active": [
                    "agents_always_active",
                    "critical_clarification_blocking",
                    "optional_clarification_non_blocking", 
                    "enriched_question_to_rag",
                    "intelligent_fallback"
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [ExpertService] Erreur traitement feedback: {e}")
            return {
                "success": False,
                "message": f"Erreur traitement feedback: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_suggested_topics(self, language: str) -> Dict[str, Any]:
        """Récupération des topics suggérés avec gestion d'erreur"""
        try:
            lang = language.lower() if language else "fr"
            if lang not in ["fr", "en", "es"]:
                lang = "fr"
            
            if UTILS_AVAILABLE:
                topics_by_language = get_enhanced_topics_by_language()
            else:
                # Topics enrichis avec pondeuses
                topics_by_language = {
                    "fr": [
                        "Croissance poulets de chair", 
                        "Problèmes de ponte pondeuses",
                        "Nutrition aviaire", 
                        "Santé animale", 
                        "Environnement élevage",
                        "Mortalité élevée - diagnostic"
                    ],
                    "en": [
                        "Broiler chicken growth", 
                        "Laying hen production problems",
                        "Poultry nutrition", 
                        "Animal health", 
                        "Farming environment",
                        "High mortality - diagnosis"
                    ],
                    "es": [
                        "Crecimiento pollos de engorde", 
                        "Problemas puesta gallinas",
                        "Nutrición aviar", 
                        "Salud animal", 
                        "Ambiente cría",
                        "Alta mortalidad - diagnóstico"
                    ]
                }
            
            topics = topics_by_language.get(lang, topics_by_language["fr"])
            
            return {
                "topics": topics,
                "language": lang,
                "count": len(topics),
                "pipeline_version": "critical_clarification",
                "improvements_active": [
                    "agents_always_active",
                    "critical_clarification_blocking",
                    "optional_clarification_non_blocking", 
                    "enriched_question_to_rag",
                    "intelligent_fallback"
                ],
                "system_status": {
                    "models_available": MODELS_AVAILABLE,
                    "utils_available": UTILS_AVAILABLE,
                    "integrations_available": INTEGRATIONS_AVAILABLE,
                    "api_enhancement_available": API_ENHANCEMENT_AVAILABLE,
                    "prompt_templates_available": PROMPT_TEMPLATES_AVAILABLE,
                    "agents_available": AGENTS_AVAILABLE,
                    "conversation_memory_available": CONVERSATION_MEMORY_AVAILABLE
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [ExpertService] Erreur topics: {e}")
            return {
                "topics": ["Erreur de récupération des topics"],
                "language": language,
                "count": 1,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# =============================================================================
# 🚀 FONCTION DE TEST POUR VÉRIFIER LES CLARIFICATIONS CRITIQUES
# =============================================================================

def test_critical_clarification_system():
    """Test du système de clarification critique vs optionnelle"""
    
    test_scenarios = [
        {
            "name": "Question broiler sans race ni âge - CRITIQUE",
            "question": "Mes poulets ne grossissent pas bien",
            "expected_critical": True,
            "expected_entities": ["breed", "age"]
        },
        {
            "name": "Question pondeuse sans race - CRITIQUE",
            "question": "Mes pondeuses ne pondent pas",
            "expected_critical": True,
            "expected_entities": ["breed"]
        },
        {
            "name": "Question Ross 308 avec âge - OPTIONNEL",
            "question": "Mes Ross 308 de 21 jours pèsent 800g",
            "expected_critical": False,
            "expected_optional": True
        },
        {
            "name": "Question type indéterminé - CRITIQUE",
            "question": "Problème avec mes animaux",
            "expected_critical": True,
            "expected_entities": ["poultry_type", "species"]
        },
        {
            "name": "Question ISA Brown complète - PAS DE CLARIFICATION",
            "question": "Mes ISA Brown de 30 semaines pondent 280 œufs",
            "expected_critical": False,
            "expected_optional": False
        }
    ]
    
    print("🧪 [Test Clarification Critique] Démarrage des tests...")
    
    for scenario in test_scenarios:
        print(f"\n🎯 Scénario: {scenario['name']}")
        print(f"   Question: {scenario['question']}")
        
        # Test de l'analyse critique
        result = analyze_question_for_clarification_enhanced(scenario['question'], "fr")
        
        is_critical = result.get("clarification_required_critical", False)
        is_optional = result.get("clarification_required_optional", False)
        missing_critical = result.get("missing_critical_entities", [])
        missing_optional = result.get("missing_optional_entities", [])
        
        print(f"   🛑 Critique: {is_critical} (attendu: {scenario.get('expected_critical', False)})")
        print(f"   💡 Optionnel: {is_optional} (attendu: {scenario.get('expected_optional', False)})")
        print(f"   📋 Entités critiques manquantes: {missing_critical}")
        print(f"   📝 Entités optionnelles manquantes: {missing_optional}")
        
        # Vérification des attentes
        if 'expected_critical' in scenario:
            status = "✅" if is_critical == scenario['expected_critical'] else "❌"
            print(f"   {status} Test critique: {'PASSED' if is_critical == scenario['expected_critical'] else 'FAILED'}")
        
        if 'expected_entities' in scenario and is_critical:
            expected_entities = scenario['expected_entities']
            entities_match = all(entity in missing_critical for entity in expected_entities)
            status = "✅" if entities_match else "❌"
            print(f"   {status} Test entités: {'PASSED' if entities_match else 'FAILED'}")
    
    print("\n🚀 [Test Clarification Critique] Résumé des améliorations:")
    print("   🛑 Clarification CRITIQUE: Stoppe avant RAG")
    print("   💡 Clarification OPTIONNELLE: Suggestions non bloquantes")
    print("   🧠 Mémoire: Track clarifications pendantes")
    print("   🎯 Précision: Détection type volaille améliorée")
    print("   🌐 Multilingue: Support FR/EN/ES")
    print("   ✅ Pipeline: Plus intelligent et adaptatif")
    
    print("✅ [Test Clarification Critique] Tests terminés!")

# =============================================================================
# CONFIGURATION FINALE AVEC CLARIFICATION CRITIQUE
# =============================================================================

logger.info("🛑" * 50)
logger.info("🛑 [EXPERT SERVICE] CLARIFICATION CRITIQUE - MODIFICATIONS APPLIQUÉES!")
logger.info("🛑 [NOUVELLES FONCTIONNALITÉS IMPLÉMENTÉES]:")
logger.info("")
logger.info("🛑 [1. CLARIFICATION CRITIQUE BLOQUANTE]:")
logger.info("   ✅ AVANT: Toutes clarifications non bloquantes")
logger.info("   ✅ APRÈS: Clarifications CRITIQUES stoppent avant RAG")
logger.info("   ✅ RÉSULTAT: Évite réponses imprécises sur infos critiques")
logger.info("")
logger.info("💡 [2. CLARIFICATION OPTIONNELLE NON BLOQUANTE]:")
logger.info("   ✅ AVANT: Pas de distinction critique/optionnel")
logger.info("   ✅ APRÈS: Suggestions optionnelles en parallèle RAG")
logger.info("   ✅ RÉSULTAT: Fluidité + suggestions d'amélioration")
logger.info("")
logger.info("🧠 [3. MÉMOIRE CLARIFICATIONS PENDANTES]:")
logger.info("   ✅ NOUVEAU: mark_pending_clarification() en mémoire")
logger.info("   ✅ NOUVEAU: clear_pending_clarification() après résolution")
logger.info("   ✅ RÉSULTAT: Suivi état clarifications par conversation")
logger.info("")
logger.info("🎯 [4. DÉTECTION CRITIQUE INTELLIGENTE]:")
logger.info("   ✅ POULETS DE CHAIR: race + âge + sexe (critique)")
logger.info("   ✅ PONDEUSES: race + stade production (critique)")
logger.info("   ✅ INDÉTERMINÉ: type volaille (critique)")
logger.info("   ✅ RÉSULTAT: Précision maximale sur entités essentielles")
logger.info("")
logger.info("🌐 [5. MESSAGES CLARIFICATION MULTILINGUES]:")
logger.info("   ✅ FRANÇAIS: Messages contextuels par type")
logger.info("   ✅ ANGLAIS: Traductions adaptées")
logger.info("   ✅ ESPAGNOL: Support complet")
logger.info("   ✅ RÉSULTAT: UX naturelle selon langue utilisateur")
logger.info("")
logger.info("🔄 [NOUVEAU FLUX PIPELINE CRITIQUE]:")
logger.info("   📝 Question → 🛑 Analyse Clarification CRITIQUE")
logger.info("   ❓ → Si CRITIQUE: ARRÊT + Message + Mémoire")
logger.info("   ✅ → Si OK: 🤖 Contextualizer + 💡 Optionnelles")
logger.info("   🔍 → RAG avec question enrichie")
logger.info("   🔧 → Enhancer + Consolidation clarifications")
logger.info("   📤 → Réponse finale + suggestions optionnelles")
logger.info("")
logger.info("🎯 [LOGIQUE CRITIQUE vs OPTIONNELLE]:")
logger.info("   🛑 CRITIQUE: Informations ESSENTIELLES pour réponse précise")
logger.info("   💡 OPTIONNELLE: Améliorations SOUHAITABLES mais pas bloquantes")
logger.info("   ⚖️ ÉQUILIBRE: Qualité garantie + Fluidité préservée")
logger.info("")
logger.info("📊 [NOUVEAUX CHAMPS RÉPONSE]:")
logger.info("   - clarification_required_critical: bool")
logger.info("   - missing_critical_entities: list")
logger.info("   - clarification_confidence: float")
logger.info("   - clarification_reasoning: str")
logger.info("   - pipeline_blocked_at: str")
logger.info("")
logger.info("✨ [STATUS FINAL]:")
logger.info("   🛑 CLARIFICATION CRITIQUE OPÉRATIONNELLE")
logger.info("   🧠 MÉMOIRE CONVERSATIONNELLE INTÉGRÉE")
logger.info("   🎯 PRÉCISION MAXIMALE GARANTIE")
logger.info("   💡 SUGGESTIONS INTELLIGENTES PRÉSERVÉES")
logger.info("   🚀 PIPELINE PLUS INTELLIGENT ET ADAPTATIF")
logger.info("🛑" * 50)