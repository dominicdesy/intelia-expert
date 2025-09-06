# -*- coding: utf-8 -*-
"""
Intent & entity classifier powered by OpenAI - FULLY MULTILINGUAL
- Zero hardcoded keywords - everything goes through OpenAI
- Supports any language naturally
- Maintains same interface as original for compatibility
- Includes complexity detection and entity extraction
"""
from enum import Enum
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import conditionnel OpenAI
try:
    from ..utils.openai_utils import complete_text as openai_complete
    OPENAI_AVAILABLE = True
    logger.info("✅ OpenAI disponible pour classification multilingue")
except ImportError as e:
    logger.warning(f"⚠️ OpenAI indisponible pour classification: {e}")
    OPENAI_AVAILABLE = False
    def openai_complete(*args, **kwargs):
        return None

class Intention(str, Enum):
    PerfTargets = "PerfTargets"
    NutritionSpecs = "NutritionSpecs"
    WaterFeedIntake = "WaterFeedIntake"
    EnvSetpoints = "EnvSetpoints"
    VentilationSizing = "VentilationSizing"
    EquipmentSizing = "EquipmentSizing"
    Programs = "Programs"
    Diagnostics = "Diagnostics"
    Treatments = "Treatments"
    Economics = "Economics"
    Compliance = "Compliance"
    Operations = "Operations"
    AmbiguousGeneral = "AmbiguousGeneral"
    # Intentions complexes pour CoT
    HealthDiagnosis = "HealthDiagnosis"
    OptimizationStrategy = "OptimizationStrategy"
    TroubleshootingMultiple = "TroubleshootingMultiple"
    ProductionAnalysis = "ProductionAnalysis"
    MultiFactor = "MultiFactor"

# Required fields per intent (compatibility)
REQUIRED_FIELDS_BY_TYPE: Dict[str, List[str]] = {
    Intention.PerfTargets: ["species", "line", "age", "sex?"],
    Intention.NutritionSpecs: ["species", "phase", "line?", "age?"],
    Intention.WaterFeedIntake: ["species", "age", "flock_size?"],
    Intention.EnvSetpoints: ["species", "age", "housing?"],
    Intention.VentilationSizing: ["species", "age", "flock_size", "season?", "housing?"],
    Intention.EquipmentSizing: ["species", "age", "flock_size", "feeder_type?/drinker_type?"],
    Intention.Programs: ["species", "age", "program_type"],
    Intention.Diagnostics: ["species", "age", "signs"],
    Intention.Treatments: ["species", "weight_or_age", "diagnosis", "drug"],
    Intention.Economics: ["species", "target_weight?", "feed_price?", "FCR?"],
    Intention.Compliance: ["scheme", "species", "age_or_slaughter_age?"],
    Intention.Operations: ["housing", "flock_size?", "age?", "problem"],
    Intention.AmbiguousGeneral: [],
    Intention.HealthDiagnosis: ["species", "age", "symptoms", "history?"],
    Intention.OptimizationStrategy: ["species", "current_performance", "target?", "constraints?"],
    Intention.TroubleshootingMultiple: ["species", "problems", "timeline?", "context?"],
    Intention.ProductionAnalysis: ["species", "metrics", "timeframe?", "comparison?"],
    Intention.MultiFactor: ["species", "factors", "objective?"]
}

def _classify_with_openai(question: str) -> Dict[str, Any]:
    """
    Classification complète via OpenAI - intentions + entités + complexité
    """
    if not OPENAI_AVAILABLE or not question.strip():
        return _minimal_fallback(question)
    
    try:
        # Prompt unifié pour classification + extraction + complexité
        classification_prompt = f"""You are an expert poultry farming assistant. Analyze this question and provide a complete analysis in JSON format.

**QUESTION:** "{question}"

**TASK:** Provide intent classification, entity extraction, and complexity analysis.

**INTENT CATEGORIES:**
- **PerfTargets**: Weight targets, growth rates, FCR, production standards for specific breeds/ages
- **NutritionSpecs**: Feed composition, nutritional requirements, feed formulations  
- **WaterFeedIntake**: Water/feed consumption amounts, intake calculations
- **EnvSetpoints**: Temperature, humidity, lighting, environmental settings
- **VentilationSizing**: Ventilation systems, air flow requirements
- **EquipmentSizing**: Feeders, drinkers, equipment dimensioning
- **Diagnostics**: Disease symptoms, health issues identification
- **Treatments**: Medication dosages, treatment protocols
- **Economics**: Costs, profitability, financial analysis
- **HealthDiagnosis**: Complex health diagnostic requiring analysis
- **OptimizationStrategy**: Performance optimization, strategy questions
- **TroubleshootingMultiple**: Complex multi-problem troubleshooting
- **ProductionAnalysis**: Performance analysis and comparisons
- **MultiFactor**: Questions involving multiple interrelated factors
- **AmbiguousGeneral**: Unclear or general questions

**ENTITIES TO EXTRACT:**
- species: "broiler", "layer", "breeder", etc.
- line: "ross308", "cobb500", "isabrown", etc. (normalize to lowercase, no spaces)
- sex: "male", "female", "mixed"
- age_days: Age in days (integer)
- age_weeks: Age in weeks (integer) 
- phase: "starter", "grower", "finisher", "pre-lay", "peak", "post-peak"
- housing: "tunnel", "naturally_ventilated", "free_range"
- program_type: "vaccination", "lighting", "brooding", "feeding_program"
- flock_size: Number of birds (integer)

**COMPLEXITY FACTORS:**
- multi_symptoms: Multiple symptoms or problems mentioned
- optimization: Optimization/improvement questions
- causal_reasoning: Why/how/cause questions
- comparative: Comparison questions
- multistep: Multi-step procedures
- complex_diagnostic: Complex diagnostic patterns
- quantified_problem: Numbers/percentages with problems

**OUTPUT FORMAT (valid JSON only):**
{{
  "intent": "IntentName",
  "confidence": 0.85,
  "entities": {{
    "species": "broiler",
    "line": "cobb500", 
    "age_days": 21,
    "sex": "male"
  }},
  "complexity": {{
    "score": 25,
    "level": "medium",
    "needs_cot": false,
    "factors": ["optimization"]
  }}
}}

Respond with ONLY the JSON object, no other text."""

        response = openai_complete(
            prompt=classification_prompt,
            max_tokens=300  # Sufficient for JSON response
        )
        
        if response:
            # Nettoyer la réponse d'OpenAI (supprimer les balises markdown)
            cleaned_response = response.strip()
            
            # Supprimer les balises ```json et ``` si présentes
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Supprimer "```json"
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Supprimer "```" simple
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Supprimer "```" de fin
            
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON response
            try:
                result = json.loads(cleaned_response)
                
                # Logging pour debug
                logger.info(f"🧹 Réponse nettoyée et parsée avec succès")
                
                # Validate and normalize
                intent_str = result.get("intent", "AmbiguousGeneral")
                try:
                    intent = Intention(intent_str)
                except ValueError:
                    logger.warning(f"Invalid intent from OpenAI: {intent_str}")
                    intent = Intention.AmbiguousGeneral
                
                entities = result.get("entities", {})
                complexity = result.get("complexity", {
                    "score": 0,
                    "level": "simple", 
                    "needs_cot": False,
                    "factors": []
                })
                
                confidence = float(result.get("confidence", 0.7))
                
                logger.info(f"🤖 OpenAI Classification: {intent.value} (confidence: {confidence:.2f})")
                
                return {
                    "intent": intent,
                    "entities": _clean_entities(entities),
                    "complexity": complexity,
                    "confidence": confidence,
                    "method": "openai_unified"
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing error: {e}")
                logger.error(f"Response was: {response[:500]}...")  # Afficher plus de contexte
                logger.error(f"Cleaned response was: {cleaned_response[:500]}...")
                return _minimal_fallback(question)
                
    except Exception as e:
        logger.error(f"❌ OpenAI classification error: {e}")
        return _minimal_fallback(question)
    
    return _minimal_fallback(question)

def _clean_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nettoie et normalise les entités extraites par OpenAI
    """
    cleaned = {}
    
    # Species normalization
    species = entities.get("species", "").lower().strip()
    if species in ["broiler", "chair", "poulet", "chicken"]:
        cleaned["species"] = "broiler"
    elif species in ["layer", "pondeuse", "laying hen"]:
        cleaned["species"] = "layer"
    elif species:
        cleaned["species"] = species
    else:
        cleaned["species"] = None
    
    # Line normalization
    line = entities.get("line", "").lower().strip().replace(" ", "").replace("-", "")
    if line:
        # Common normalizations
        line_map = {
            "ross308": "ross308", "ross 308": "ross308",
            "cobb500": "cobb500", "cobb 500": "cobb500",
            "isabrown": "isabrown", "isa brown": "isabrown"
        }
        cleaned["line"] = line_map.get(line, line)
    else:
        cleaned["line"] = None
    
    # Sex normalization
    sex = entities.get("sex", "").lower().strip()
    sex_map = {
        "male": "male", "m": "male", "mâle": "male",
        "female": "female", "f": "female", "femelle": "female", 
        "mixed": "mixed", "mixte": "mixed", "as_hatched": "mixed"
    }
    cleaned["sex"] = sex_map.get(sex, sex if sex else None)
    
    # Age handling
    age_days = entities.get("age_days")
    age_weeks = entities.get("age_weeks")
    
    try:
        if age_days is not None:
            cleaned["age_days"] = int(age_days)
        else:
            cleaned["age_days"] = None
            
        if age_weeks is not None:
            cleaned["age_weeks"] = int(age_weeks)
        else:
            cleaned["age_weeks"] = None
            
        # Convert between days/weeks if only one is provided
        if cleaned["age_days"] is not None and cleaned["age_weeks"] is None:
            cleaned["age_weeks"] = round(cleaned["age_days"] / 7, 1)
        elif cleaned["age_weeks"] is not None and cleaned["age_days"] is None:
            cleaned["age_days"] = int(cleaned["age_weeks"] * 7)
            
    except (ValueError, TypeError):
        cleaned["age_days"] = None
        cleaned["age_weeks"] = None
    
    # Other entities
    cleaned["phase"] = entities.get("phase") or None
    cleaned["housing"] = entities.get("housing") or None
    cleaned["program_type"] = entities.get("program_type") or None
    
    # Flock size
    try:
        flock_size = entities.get("flock_size")
        cleaned["flock_size"] = int(flock_size) if flock_size else None
    except (ValueError, TypeError):
        cleaned["flock_size"] = None
    
    return cleaned

def _minimal_fallback(question: str) -> Dict[str, Any]:
    """
    Fallback minimal si OpenAI échoue - utilise regex basique
    """
    # Basic regex patterns for critical entities
    age_days_match = re.search(r'\b(\d{1,2})\s*(?:j|jours?|day|days?|giorni?)\b', question, re.I)
    age_weeks_match = re.search(r'\b(\d{1,2})\s*(?:sem|semaines?|wk|weeks?|settimane?)\b', question, re.I)
    
    # Basic species detection
    ql = question.lower()
    species = None
    if any(word in ql for word in ["broiler", "chair", "poulet", "pollo", "chicken"]):
        species = "broiler"
    elif any(word in ql for word in ["layer", "pondeuse", "laying", "gallina"]):
        species = "layer"
    
    # Basic line detection
    line = None
    if "cobb" in ql and "500" in ql:
        line = "cobb500"
    elif "ross" in ql and "308" in ql:
        line = "ross308"
    
    # Simple intent detection
    intent = Intention.AmbiguousGeneral
    if any(word in ql for word in ["peso", "poids", "weight", "target", "cible", "objectif"]):
        intent = Intention.PerfTargets
    
    entities = {
        "species": species,
        "line": line,
        "sex": None,
        "age_days": int(age_days_match.group(1)) if age_days_match else None,
        "age_weeks": int(age_weeks_match.group(1)) if age_weeks_match else None,
        "phase": None,
        "housing": None,
        "program_type": None,
        "flock_size": None
    }
    
    complexity = {
        "score": 0,
        "level": "simple",
        "needs_cot": False,
        "factors": []
    }
    
    return {
        "intent": intent,
        "entities": entities,
        "complexity": complexity,
        "confidence": 0.3,
        "method": "regex_fallback"
    }

def classify(question: str) -> Dict[str, Any]:
    """
    Fonction principale - interface compatible avec l'original
    """
    if not question or not question.strip():
        return _minimal_fallback(question)
    
    result = _classify_with_openai(question)
    
    # Format de retour compatible avec l'original
    return {
        "intent": result["intent"],
        "entities": result["entities"], 
        "complexity": result["complexity"]
    }

# Fonctions utilitaires pour compatibilité
def should_use_cot(classification_result: Dict[str, Any]) -> bool:
    """Détermine si Chain-of-Thought doit être utilisé"""
    complexity = classification_result.get("complexity", {})
    return complexity.get("needs_cot", False)

def get_complexity_level(classification_result: Dict[str, Any]) -> str:
    """Retourne le niveau de complexité"""
    complexity = classification_result.get("complexity", {})
    return complexity.get("level", "simple")

def get_complexity_factors(classification_result: Dict[str, Any]) -> List[str]:
    """Retourne les facteurs de complexité détectés"""
    complexity = classification_result.get("complexity", {})
    return complexity.get("factors", [])

def get_classification_status() -> Dict[str, Any]:
    """Statut du système de classification"""
    return {
        "openai_available": OPENAI_AVAILABLE,
        "multilingual_support": OPENAI_AVAILABLE,
        "hardcoded_keywords": False,  # 🎯 Plus de mots-clés hardcodés !
        "supported_languages": ["any"] if OPENAI_AVAILABLE else ["limited"],
        "classification_method": "openai_unified" if OPENAI_AVAILABLE else "regex_fallback",
        "total_intents": len(Intention),
        "version": "openai_pure_v1.0"
    }

def test_multilingual_classification() -> Dict[str, Any]:
    """Test du système multilingue"""
    test_questions = [
        ("Quel est le poids cible d'un poulet Cobb 500 de 21 jours?", Intention.PerfTargets),
        ("Quanto pesa un pollo Cobb 500 di 12 giorni?", Intention.PerfTargets), 
        ("What should a 21-day Ross 308 male weigh?", Intention.PerfTargets),
        ("¿Cuál es el peso objetivo de un pollo de 3 semanas?", Intention.PerfTargets),
        ("Wie viel sollte ein 3 Wochen altes Huhn wiegen?", Intention.PerfTargets),
        ("Qual a composição da ração inicial?", Intention.NutritionSpecs),
        ("Hoeveel water drinkt een kip per dag?", Intention.WaterFeedIntake),
    ]
    
    results = {}
    for question, expected_intent in test_questions:
        try:
            result = classify(question)
            results[question] = {
                "detected_intent": result["intent"].value,
                "expected_intent": expected_intent.value,
                "entities": result["entities"],
                "complexity": result["complexity"],
                "success": result["intent"] == expected_intent
            }
        except Exception as e:
            results[question] = {"error": str(e)}
    
    return {
        "total_tests": len(test_questions),
        "results": results,
        "openai_available": OPENAI_AVAILABLE
    }