# app/api/v1/pipeline/intent_registry.py
from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple

"""
Intent Registry — universel, extensible
- Chaque intention déclare: signaux (regex), slots requis, sources préférées, answer_mode
- Fournit des helpers: infer_intent(), get_intent_spec(), derive_answer_mode()
"""

_INTENTS: Dict[str, Dict[str, Any]] = {
    # --- Nutrition / objectifs ---
    "nutrition.optimize": {
        "signals": [
            r"\b(phosphore\s+digestible|lysine|protéine|énergie|kcal\/kg|np|dP)\b",
            r"\b(starter|pré-?starter|grower|finisher|phase)\b",
            r"\b(optimiser|optimisation|ajuster|formulation|éco(?:nomique)?)\b",
        ],
        "slots_required": ["species", "line", "phase"],
        "preferred_sources": ["nutrition_specs", "performance_objectives"],
        "answer_mode": "table+recommendations",
    },

    # --- Cibles de performance / poids / FCR ---
    "targets.weight": {
        "signals": [
            r"\b(poids|poids\s+cible|target\s+weight|bw|id[ée]al)\b",
            r"\b(j|jours|day|d)\s*\d{1,3}\b",
        ],
        "slots_required": ["species", "line", "sex", "age_days"],
        "preferred_sources": ["performance_objectives", "broiler_handbook"],
        "answer_mode": "numeric",
    },
    "targets.fcr": {
        "signals": [r"\b(fcr|indice\s+de\s+consommation|feed\s*conversion)\b"],
        "slots_required": ["species", "age_days"],
        "preferred_sources": ["performance_objectives", "nutrition_specs"],
        "answer_mode": "numeric",
    },

    # --- Eau / environnement / éclairage ---
    "water.intake": {
        "signals": [r"\b(water\s*intake|consommation\s+d['e]au|eau\s/j)\b"],
        "slots_required": ["species", "age_days"],
        "preferred_sources": ["brooding_guides", "environmental_guides"],
        "answer_mode": "numeric",
    },
    "environment.min_vent": {
        "signals": [r"\b(ventilation\s+minimale|min\s*vent|condensation|hiver)\b"],
        "slots_required": ["species", "age_days"],
        "preferred_sources": ["ventilation_guides", "environmental_guides"],
        "answer_mode": "procedure+numbers",
    },
    "lighting.program": {
        "signals": [r"\b(lumi[eè]re|photop[ée]riode|lux|lumens)\b"],
        "slots_required": ["species", "age_days"],
        "preferred_sources": ["broiler_handbook", "layer_handbook"],
        "answer_mode": "procedure",
    },

    # --- Coûts / IEP ---
    "kpi.iep": {
        "signals": [r"\b(iep|epef|production\s+efficiency)\b"],
        "slots_required": ["species", "age_days"],
        "preferred_sources": ["economic_guides", "performance_objectives"],
        "answer_mode": "numeric",
    },
    "cost.feed": {
        "signals": [r"\b(co[uû]t\s+aliment|feed\s+cost|€/t|€/kg\s+vif)\b"],
        "slots_required": ["species"],
        "preferred_sources": ["economic_guides"],
        "answer_mode": "numeric",
    },
    "cost.heating": {
        "signals": [r"\b(co[uû]t\s+chauffage|heating\s+cost|fuel|propane|gaz)\b"],
        "slots_required": ["species", "temp_outside"],
        "preferred_sources": ["engineering_specs"],
        "answer_mode": "calculator",
    },

    # --- Équipements ---
    "equipment.nipples.setup": {
        "signals": [r"\b(nipple|abreuvoirs?|hauteur|pression|réglage)\b", r"\b(day-?old|démarrage)\b"],
        "slots_required": ["species", "age_days"],
        "preferred_sources": ["equipment_manuals", "brooding_guides"],
        "answer_mode": "procedure+table",
    },
    "feeding.chain.calibration": {
        "signals": [r"\b(cha[iî]ne|chain|calibrage|calibration|débit)\b", r"\b(grower|finisher|phase)\b"],
        "slots_required": ["species", "phase"],
        "preferred_sources": ["equipment_manuals", "operation_guides"],
        "answer_mode": "procedure+numbers",
    },

    # --- Densités / conformité / labels ---
    "stocking.density": {
        "signals": [r"\b(densit[ée]|kg\/m2|m²\/oiseau|canicule|38\s*°c)\b"],
        "slots_required": ["species"],
        "preferred_sources": ["welfare_standards", "label_guides", "regulations"],
        "answer_mode": "table+rules",
    },
    "compliance.label": {
        "signals": [r"\b(label\s+rouge|plein\s+air|cahier\s+des\s+charges)\b"],
        "slots_required": ["jurisdiction"],
        "preferred_sources": ["regulations", "label_specs"],
        "answer_mode": "rules",
    },

    # --- Pondues / œufs ---
    "eggs.quality": {
        "signals": [r"\b(cat[ée]gorie\s*a\+?|qualit[ée]\s+coquille|sale\s+coquille)\b"],
        "slots_required": ["species"],
        "preferred_sources": ["layer_handbook", "quality_guides"],
        "answer_mode": "targets+procedure",
    },

    # --- Général ---
    "general": {
        "signals": [r".*"],  # toujours vrai en dernier recours
        "slots_required": [],
        "preferred_sources": ["broiler_handbook", "layer_handbook", "general_guides"],
        "answer_mode": "standard",
    },
}

# ordre d’évaluation des intents
_ORDER: List[str] = [
    "nutrition.optimize",
    "targets.weight",
    "targets.fcr",
    "water.intake",
    "environment.min_vent",
    "lighting.program",
    "kpi.iep",
    "cost.feed",
    "cost.heating",
    "equipment.nipples.setup",
    "feeding.chain.calibration",
    "stocking.density",
    "compliance.label",
    "eggs.quality",
    "general",
]

def infer_intent(text: str, fallback: str = "general") -> str:
    t = (text or "").lower()
    for name in _ORDER:
        for rx in _INTENTS[name]["signals"]:
            if re.search(rx, t, re.I):
                return name
    return fallback

def get_intent_spec(name: str) -> Dict[str, Any]:
    return _INTENTS.get(name, _INTENTS["general"])

def derive_answer_mode(name: str) -> str:
    return str(get_intent_spec(name).get("answer_mode") or "standard")

def required_slots(name: str) -> List[str]:
    return list(get_intent_spec(name).get("slots_required") or [])

def preferred_sources(name: str) -> List[str]:
    return list(get_intent_spec(name).get("preferred_sources") or [])

def looks_numeric_first(name: str) -> bool:
    mode = derive_answer_mode(name)
    return any(x in mode for x in ["numeric", "numbers", "table"])
