# -*- coding: utf-8 -*-
"""
Normalize entities for downstream use.
- Broiler: prefer age_days
- Layer: prefer age_weeks
- Infer species from line if absent
"""
from typing import Dict, Any

def normalize(context: Dict[str, Any]) -> Dict[str, Any]:
    entities = context.get("entities", {})
    species = entities.get("species")
    age_days = entities.get("age_days")
    age_weeks = entities.get("age_weeks")
    line = entities.get("line") or ""

    if not species and line:
        if any(x in line for x in ["isa","lohmann","hyline"]):
            species = "layer"
        elif any(x in line for x in ["ross","cobb"]):
            species = "broiler"

    if species == "broiler":
        if age_days is None and age_weeks is not None:
            age_days = age_weeks * 7
        entities["age_days"] = age_days
        entities["age_weeks"] = None
    elif species == "layer":
        if age_weeks is None and age_days is not None:
            age_weeks = round(age_days / 7)
        entities["age_weeks"] = age_weeks
        entities["age_days"] = None

    context["entities"] = entities
    return context
