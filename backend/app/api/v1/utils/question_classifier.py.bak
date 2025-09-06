# -*- coding: utf-8 -*-
"""
Intent & entity classifier with Chain-of-Thought complexity detection.
- Provides Intention enum and REQUIRED_FIELDS_BY_TYPE
- classify() returns {"intent": Intention, "entities": {...}, "complexity": {...}}
- Designed to be lightweight and robust with regex + keywords
- 🆕 NEW: Complexity scoring for CoT routing
- 🔧 FIXED: Multilingual support for PerfTargets detection
"""
from enum import Enum
import re
from typing import Dict, Any, List, Optional, Tuple

# --- Lexicons ---
LINES = [
    "ross 308", "ross308", "ross 708", "ross708",
    "cobb 500", "cobb500",
    "isa brown", "lohmann brown", "lohmann white",
    "hy-line brown", "hy line brown", "hyline brown"
]

PHASES = ["starter", "démarrage", "grower", "croissance", "finisher", "finition"]
HOUSING = ["tunnel", "ventilation naturelle", "naturelle", "plein air", "free range"]

# 🔧 NEW: Multilingual keywords for better classification
PERF_TARGETS_KEYWORDS = [
    # Français
    "poids", "fcr", "indice de consommation", "gain de poids", "iep", 
    "pourcentage de ponte", "poids d'œuf", "poids d'oeuf",
    # English - CRITICAL FIX
    "weight", "target weight", "body weight", "feed conversion", "feed conversion ratio",
    "weight gain", "egg production", "egg weight", "laying rate", "production rate"
]

NUTRITION_KEYWORDS = [
    # Français
    "protéine", "lysine", "kcal/kg", "énergie", "calcium", "phosphore", "formulation",
    # English
    "protein", "lysine", "energy", "kcal/kg", "calcium", "phosphorus", "formulation"
]

DIAGNOSTIC_KEYWORDS = [
    # Français
    "diagnostic", "symptôme", "symptomes", "symptômes", "diarrhée", "dyspnée", 
    "coquilles molles", "picorent", "mortalité",
    # English
    "diagnosis", "diagnostic", "symptom", "symptoms", "diarrhea", "mortality", 
    "soft shells", "dyspnea", "respiratory"
]

WATER_FEED_KEYWORDS = [
    # Français
    "consommation d'eau", "débit d'eau", "consommation d'aliment",
    # English
    "water consumption", "water intake", "feed intake", "feed consumption"
]

ENV_KEYWORDS = [
    # Français
    "température", "humidité", "co2", "nh3", "ammoniac", "éclairage", "lumens", "lux",
    # English
    "temperature", "humidity", "co2", "nh3", "ammonia", "lighting", "lumens", "lux"
]

VENTILATION_KEYWORDS = [
    # Français
    "ventilation minimale", "débit d'air", "m³/h", "m3/h", "tunnel",
    # English
    "minimum ventilation", "air flow", "m3/h", "tunnel", "ventilation"
]

EQUIPMENT_KEYWORDS = [
    # Français
    "espace mangeoire", "mangeoires", "abreuvoirs", "nipples", "calibrage chaîne",
    # English
    "feeder space", "feeders", "drinkers", "nipples", "equipment"
]

TREATMENT_KEYWORDS = [
    # Français
    "dosage", "dose", "posologie", "enrofloxacine", "amoxicilline", "tylosine",
    # English
    "dosage", "dose", "treatment", "enrofloxacin", "amoxicillin", "tylosin"
]

ECONOMICS_KEYWORDS = [
    # Français
    "coût", "rentabilité", "combien coûte",
    # English
    "cost", "profitability", "how much", "economics", "roi"
]

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
    # 🆕 NOUVELLES INTENTIONS COMPLEXES
    HealthDiagnosis = "HealthDiagnosis"
    OptimizationStrategy = "OptimizationStrategy"
    TroubleshootingMultiple = "TroubleshootingMultiple"
    ProductionAnalysis = "ProductionAnalysis"
    MultiFactor = "MultiFactor"

# Required fields per intent (fields ending with '?' are optional)
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
    # 🆕 NOUVEAUX CHAMPS POUR INTENTIONS COMPLEXES
    Intention.HealthDiagnosis: ["species", "age", "symptoms", "history?"],
    Intention.OptimizationStrategy: ["species", "current_performance", "target?", "constraints?"],
    Intention.TroubleshootingMultiple: ["species", "problems", "timeline?", "context?"],
    Intention.ProductionAnalysis: ["species", "metrics", "timeframe?", "comparison?"],
    Intention.MultiFactor: ["species", "factors", "objective?"]
}

# 🆕 NOUVEAUX PATTERNS POUR DÉTECTION DE COMPLEXITÉ
COMPLEXITY_INDICATORS = {
    "multi_symptoms": [
        r"\bet\b.*\bet\b",  # "symptôme A et symptôme B"
        r"plusieurs.*(?:symptômes|problèmes|signes)",
        r"(?:mortalité|ponte).*(?:baisse|chute).*(?:poids|fcr|croissance)"
    ],
    "optimization_keywords": [
        "optimiser", "améliorer", "maximiser", "minimiser", "rentabilité",
        "efficacité", "performance", "stratégie", "comment réduire",
        "comment augmenter", "meilleure façon"
    ],
    "causal_reasoning": [
        "pourquoi", "comment", "quelle.*cause", "qu'est-ce qui",
        "facteurs", "raisons", "origine", "expliquer"
    ],
    "comparative_analysis": [
        "comparer", "différence", "mieux que", "versus", "vs",
        "par rapport", "comparé", "alternative"
    ],
    "multistep_indicators": [
        "d'abord.*puis", "ensuite", "étapes", "procédure", "protocole",
        "plan", "stratégie", "méthode", "approche"
    ]
}

DIAGNOSTIC_COMPLEXITY_PATTERNS = [
    r"diagnostic.*différentiel",
    r"(?:mortalité|perte).*(?:\d+%|\d+\s*pour\s*cent)",
    r"(?:baisse|chute|diminution).*(?:ponte|production|croissance)",
    r"(?:symptômes?|signes?).*(?:multiples?|divers|variés)",
    r"(?:analyse|évaluation).*(?:complète|approfondie|détaillée)"
]

# --- Regex helpers (code original conservé + améliorations) ---
# 🔧 IMPROVED: Better age detection patterns including English
AGE_DAYS_RE = re.compile(r"\b(\d{1,2})\s*(?:j|jours?|day|days?)\b", re.I)
AGE_WEEKS_RE = re.compile(r"\b(\d{1,2})\s*(?:sem|semaines?|wk|wks|weeks?)\b", re.I)
# 🔧 NEW: Support for "X-day-old" and "X-week-old" patterns
AGE_DAY_OLD_RE = re.compile(r"\b(\d{1,2})-day-old\b", re.I)
AGE_WEEK_OLD_RE = re.compile(r"\b(\d{1,2})-week-old\b", re.I)

FLOCK_RE = re.compile(r"\b(\d{2,6})\s*(?:oiseaux?|birds?|poulets?)\b", re.I)

def _normalize_line(q: str) -> Optional[str]:
    ql = q.lower()
    for ln in LINES:
        if ln in ql:
            return ln.replace(" ", "")
    return None

def _infer_species(q: str) -> Optional[str]:
    ql = q.lower()
    if any(k in ql for k in ["isa", "lohmann", "œuf", "oeuf", "egg", "hy-line", "hy line", "hyline", "pondeuse", "layer"]):
        return "layer"
    if any(k in ql for k in ["ross", "cobb", "broiler", "chair", "chicken"]):  # Added "chicken"
        return "broiler"
    return None

def _extract_age(q: str) -> Dict[str, Optional[int]]:
    """🔧 IMPROVED: Better age extraction with English support"""
    # Try day-old patterns first (most specific)
    day_old_match = AGE_DAY_OLD_RE.search(q)
    if day_old_match:
        return {"age_days": int(day_old_match.group(1)), "age_weeks": None}
    
    # Try week-old patterns
    week_old_match = AGE_WEEK_OLD_RE.search(q)
    if week_old_match:
        weeks = int(week_old_match.group(1))
        return {"age_days": weeks * 7, "age_weeks": weeks}
    
    # Fallback to original patterns
    d = AGE_DAYS_RE.search(q)
    w = AGE_WEEKS_RE.search(q)
    return {"age_days": int(d.group(1)) if d else None, "age_weeks": int(w.group(1)) if w else None}

def _detect_phase(q: str) -> Optional[str]:
    ql = q.lower()
    for p in PHASES:
        if p in ql:
            if p.startswith("dém"): return "starter"
            if p == "croissance": return "grower"
            if p == "finition": return "finisher"
            return p
    return None

def _detect_housing(q: str) -> Optional[str]:
    ql = q.lower()
    for h in HOUSING:
        if h in ql:
            if "naturelle" in h: return "naturally_ventilated"
            if "plein air" in h or "free range" in h: return "free_range"
            return h
    return None

def _detect_sex(q: str) -> Optional[str]:
    """🔧 IMPROVED: Better sex detection with English support"""
    ql = q.lower()
    if "mâle" in ql or "males" in ql or "male" in ql: return "male"
    if "femelle" in ql or "females" in ql or "female" in ql: return "female"
    if "mixte" in ql or "mixed" in ql: return "mixed"
    return None

def _detect_program_type(q: str) -> Optional[str]:
    ql = q.lower()
    if "vaccin" in ql or "vaccination" in ql: return "vaccination"
    if "éclairage" in ql or "lumière" in ql or "lighting" in ql: return "lighting"
    if "démarrage" in ql or "brooding" in ql: return "brooding"
    if "alimentation" in ql and "programme" in ql: return "feeding_program"
    return None

def _has_any(ql: str, words: List[str]) -> bool:
    """🔧 IMPROVED: Case-insensitive matching"""
    ql_lower = ql.lower()
    return any(w.lower() in ql_lower for w in words)

# 🆕 NOUVELLES FONCTIONS DE DÉTECTION DE COMPLEXITÉ

def _detect_complexity_score(q: str) -> Dict[str, Any]:
    """
    Calcule un score de complexité pour déterminer si CoT est nécessaire
    """
    ql = q.lower()
    complexity_score = 0
    complexity_factors = []
    
    # 1. Multi-symptômes / Multi-problèmes (+30 points)
    for pattern in COMPLEXITY_INDICATORS["multi_symptoms"]:
        if re.search(pattern, ql, re.I):
            complexity_score += 30
            complexity_factors.append("multi_symptoms")
            break
    
    # 2. Mots-clés d'optimisation (+25 points)
    optimization_matches = sum(1 for kw in COMPLEXITY_INDICATORS["optimization_keywords"] if kw in ql)
    if optimization_matches > 0:
        complexity_score += min(25, optimization_matches * 10)
        complexity_factors.append("optimization")
    
    # 3. Raisonnement causal (+20 points)
    causal_matches = sum(1 for pattern in COMPLEXITY_INDICATORS["causal_reasoning"] if re.search(pattern, ql, re.I))
    if causal_matches > 0:
        complexity_score += min(20, causal_matches * 8)
        complexity_factors.append("causal_reasoning")
    
    # 4. Analyse comparative (+15 points)
    comparative_matches = sum(1 for kw in COMPLEXITY_INDICATORS["comparative_analysis"] if kw in ql)
    if comparative_matches > 0:
        complexity_score += min(15, comparative_matches * 7)
        complexity_factors.append("comparative")
    
    # 5. Indicateurs multi-étapes (+20 points)
    multistep_matches = sum(1 for kw in COMPLEXITY_INDICATORS["multistep_indicators"] if kw in ql)
    if multistep_matches > 0:
        complexity_score += min(20, multistep_matches * 10)
        complexity_factors.append("multistep")
    
    # 6. Patterns de diagnostic complexe (+25 points)
    diagnostic_matches = sum(1 for pattern in DIAGNOSTIC_COMPLEXITY_PATTERNS if re.search(pattern, ql, re.I))
    if diagnostic_matches > 0:
        complexity_score += min(25, diagnostic_matches * 12)
        complexity_factors.append("complex_diagnostic")
    
    # 7. Longueur de la question (+5-15 points)
    word_count = len(q.split())
    if word_count > 20:
        complexity_score += 15
        complexity_factors.append("long_question")
    elif word_count > 12:
        complexity_score += 8
        complexity_factors.append("medium_question")
    
    # 8. Présence de chiffres/pourcentages dans contexte complexe (+10 points)
    if re.search(r'\d+%|\d+\s*pour\s*cent', ql) and any(kw in ql for kw in ["baisse", "augmentation", "problème", "objectif"]):
        complexity_score += 10
        complexity_factors.append("quantified_problem")
    
    # Classification du niveau de complexité
    if complexity_score >= 50:
        complexity_level = "high"
        needs_cot = True
    elif complexity_score >= 25:
        complexity_level = "medium"
        needs_cot = True
    else:
        complexity_level = "simple"
        needs_cot = False
    
    return {
        "score": complexity_score,
        "level": complexity_level,
        "needs_cot": needs_cot,
        "factors": complexity_factors,
        "word_count": word_count
    }

def _classify_intent_enhanced(q: str) -> Tuple[Intention, Dict[str, Any]]:
    """
    Classification enrichie avec détection d'intentions complexes
    🔧 FIXED: Multilingual keyword support
    """
    ql = q.lower()
    complexity_info = _detect_complexity_score(q)
    
    # 🆕 NOUVELLES INTENTIONS COMPLEXES (priorité haute si complexité détectée)
    if complexity_info["needs_cot"]:
        # Diagnostic complexe
        if (_has_any(ql, DIAGNOSTIC_KEYWORDS) and 
            (complexity_info["score"] >= 40 or "complex_diagnostic" in complexity_info["factors"])):
            return Intention.HealthDiagnosis, complexity_info
        
        # Optimisation/stratégie
        if (_has_any(ql, ["optimiser", "améliorer", "stratégie", "rentabilité", "efficacité"]) and
            complexity_info["score"] >= 35):
            return Intention.OptimizationStrategy, complexity_info
        
        # Troubleshooting multiple
        if ("multi_symptoms" in complexity_info["factors"] or 
            _has_any(ql, ["plusieurs problèmes", "multiples", "divers problèmes"])):
            return Intention.TroubleshootingMultiple, complexity_info
        
        # Analyse de production complexe
        if (_has_any(ql, ["analyse", "évaluation", "performance", "comparaison"]) and
            complexity_info["score"] >= 30):
            return Intention.ProductionAnalysis, complexity_info
        
        # Multi-facteurs générique
        if complexity_info["score"] >= 50:
            return Intention.MultiFactor, complexity_info
    
    # 🔧 INTENTIONS CLASSIQUES (FIXED avec support multilingue)
    if _has_any(ql, TREATMENT_KEYWORDS):
        return Intention.Treatments, complexity_info
    if _has_any(ql, DIAGNOSTIC_KEYWORDS):
        return Intention.Diagnostics, complexity_info
    # 🔧 CRITICAL FIX: Now includes English "weight" keywords
    if _has_any(ql, PERF_TARGETS_KEYWORDS):
        return Intention.PerfTargets, complexity_info
    if _has_any(ql, NUTRITION_KEYWORDS):
        return Intention.NutritionSpecs, complexity_info
    if _has_any(ql, WATER_FEED_KEYWORDS):
        return Intention.WaterFeedIntake, complexity_info
    if _has_any(ql, ENV_KEYWORDS):
        return Intention.EnvSetpoints, complexity_info
    if _has_any(ql, VENTILATION_KEYWORDS):
        return Intention.VentilationSizing, complexity_info
    if _has_any(ql, EQUIPMENT_KEYWORDS):
        return Intention.EquipmentSizing, complexity_info
    if _detect_program_type(ql):
        return Intention.Programs, complexity_info
    if _has_any(ql, ECONOMICS_KEYWORDS):
        return Intention.Economics, complexity_info
    if _has_any(ql, ["label rouge", "plein air", "catégorie a+", "enrichissements obligatoires", "densité maximale"]):
        return Intention.Compliance, complexity_info
    if _has_any(ql, ["maintenance", "extracteurs", "condensation", "ammoniaque"]) or _has_any(ql, ["ventilation insuffisante"]):
        return Intention.Operations, complexity_info
    
    return Intention.AmbiguousGeneral, complexity_info

def classify(question: str) -> Dict[str, Any]:
    """
    Classification principale avec enrichissements CoT
    🔧 IMPROVED: Better multilingual support
    """
    intent, complexity_info = _classify_intent_enhanced(question)
    line = _normalize_line(question) or None
    species = _infer_species(question)
    sex = _detect_sex(question)
    age = _extract_age(question)  # Now handles "18-day-old" correctly
    phase = _detect_phase(question)
    housing = _detect_housing(question)
    program_type = _detect_program_type(question)

    entities = {
        "species": species,
        "line": line,
        "sex": sex,
        "age_days": age["age_days"],
        "age_weeks": age["age_weeks"],
        "phase": phase,
        "housing": housing,
        "program_type": program_type
    }

    return {
        "intent": intent,
        "entities": entities,
        # 🆕 NOUVELLES MÉTADONNÉES DE COMPLEXITÉ
        "complexity": complexity_info
    }

# 🆕 NOUVELLES FONCTIONS UTILITAIRES

def should_use_cot(classification_result: Dict[str, Any]) -> bool:
    """
    Détermine si Chain-of-Thought doit être utilisé pour cette classification
    """
    complexity = classification_result.get("complexity", {})
    return complexity.get("needs_cot", False)

def get_complexity_level(classification_result: Dict[str, Any]) -> str:
    """
    Retourne le niveau de complexité: 'simple', 'medium', 'high'
    """
    complexity = classification_result.get("complexity", {})
    return complexity.get("level", "simple")

def get_complexity_factors(classification_result: Dict[str, Any]) -> List[str]:
    """
    Retourne la liste des facteurs de complexité détectés
    """
    complexity = classification_result.get("complexity", {})
    return complexity.get("factors", [])
