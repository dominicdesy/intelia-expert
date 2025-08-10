# -*- coding: utf-8 -*-
"""
Intent & entity classifier.
- Provides Intention enum and REQUIRED_FIELDS_BY_TYPE
- classify() returns {"intent": Intention, "entities": {...}}
- Designed to be lightweight and robust with regex + keywords
"""
from enum import Enum
import re
from typing import Dict, Any, List, Optional

# --- Lexicons ---
LINES = [
    "ross 308", "ross308", "ross 708", "ross708",
    "cobb 500", "cobb500",
    "isa brown", "lohmann brown", "lohmann white",
    "hy-line brown", "hy line brown", "hyline brown"
]

PHASES = ["starter", "démarrage", "grower", "croissance", "finisher", "finition"]
HOUSING = ["tunnel", "ventilation naturelle", "naturelle", "plein air", "free range"]

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
    Intention.AmbiguousGeneral: []
}

# --- Regex helpers ---
AGE_DAYS_RE = re.compile(r"\b(\d{1,2})\s*(?:j|jours?|day|days)\b", re.I)
AGE_WEEKS_RE = re.compile(r"\b(\d{1,2})\s*(?:sem|semaines?|wk|wks|weeks?)\b", re.I)
FLOCK_RE = re.compile(r"\b(\d{2,6})\s*(?:oiseaux?|birds?|poulets?)\b", re.I)

def _normalize_line(q: str) -> Optional[str]:
    ql = q.lower()
    for ln in LINES:
        if ln in ql:
            return ln.replace(" ", "")
    return None

def _infer_species(q: str) -> Optional[str]:
    ql = q.lower()
    if any(k in ql for k in ["isa", "lohmann", "œuf", "oeuf", "egg", "hy-line", "hy line", "hyline", "pondeuse"]):
        return "layer"
    if any(k in ql for k in ["ross", "cobb", "broiler", "chair"]):
        return "broiler"
    return None

def _extract_age(q: str) -> Dict[str, Optional[int]]:
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
    return any(w in ql for w in words)

def _classify_intent(q: str) -> Intention:
    ql = q.lower()
    if _has_any(ql, ["dosage", "dose", "posologie", "enrofloxacine", "amoxicilline", "tylosine"]):
        return Intention.Treatments
    if _has_any(ql, ["diagnostic", "symptôme", "symptomes", "symptômes", "diarrhée", "dyspnée", "coquilles molles", "picorent", "mortalité"]):
        return Intention.Diagnostics
    if _has_any(ql, ["poids", "fcr", "indice de consommation", "gain de poids", "iep", "pourcentage de ponte", "poids d'œuf", "poids d'oeuf"]):
        return Intention.PerfTargets
    if _has_any(ql, ["protéine", "lysine", "kcal/kg", "énergie", "calcium", "phosphore", "formulation"]):
        return Intention.NutritionSpecs
    if _has_any(ql, ["consommation d'eau", "débit d'eau", "consommation d’aliment", "consommation d'aliment"]):
        return Intention.WaterFeedIntake
    if _has_any(ql, ["température", "humidité", "co2", "nh3", "ammoniac", "éclairage", "lumens", "lux"]):
        return Intention.EnvSetpoints
    if _has_any(ql, ["ventilation minimale", "débit d'air", "m³/h", "m3/h", "tunnel"]):
        return Intention.VentilationSizing
    if _has_any(ql, ["espace mangeoire", "mangeoires", "abreuvoirs", "nipples", "calibrage chaîne"]):
        return Intention.EquipmentSizing
    if _detect_program_type(ql):
        return Intention.Programs
    if _has_any(ql, ["coût", "rentabilité", "combien coûte"]):
        return Intention.Economics
    if _has_any(ql, ["label rouge", "plein air", "catégorie a+", "enrichissements obligatoires", "densité maximale"]):
        return Intention.Compliance
    if _has_any(ql, ["maintenance", "extracteurs", "condensation", "ammoniaque"]) or _has_any(ql, ["ventilation insuffisante"]):
        return Intention.Operations
    return Intention.AmbiguousGeneral

def classify(question: str) -> Dict[str, Any]:
    intent = _classify_intent(question)
    line = _normalize_line(question) or None
    species = _infer_species(question)
    sex = _detect_sex(question)
    age = _extract_age(question)
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

    return {"intent": intent, "entities": entities}
