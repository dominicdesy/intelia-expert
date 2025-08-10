# -*- coding: utf-8 -*-
"""
Computes completeness and returns targeted follow-up questions.
"""
from typing import Dict, Any, List
from ..utils.question_classifier import Intention, REQUIRED_FIELDS_BY_TYPE

def compute_completeness(intent: Intention, entities: Dict[str, Any]) -> Dict[str, Any]:
    required = REQUIRED_FIELDS_BY_TYPE.get(intent, [])
    missing: List[str] = []

    def present(field: str) -> bool:
        val = entities.get(field)
        return val is not None and val != ""

    for f in required:
        if f.endswith("?"):
            continue
        norm = f.replace("-", "_").replace(" ", "_")
        if "/" in norm:
            alts = [x.strip() for x in norm.split("/")]
            if not any(present(a) for a in alts):
                missing.append(f)
        else:
            if not present(norm):
                missing.append(f)

    denom = max(1, len([f for f in required if not f.endswith("?")]))
    score = 1.0 - (len(missing) / denom)
    questions: List[Dict[str, Any]] = []

    j = " ".join(missing)
    if "species" in j:
        questions.append({"field":"species","question":"Broilers (poulets de chair) ou pondeuses ?","options":["broiler","layer"]})
    if "line" in j:
        questions.append({"field":"line","question":"Quelle lignée ?","options":["Ross 308","Ross 708","Cobb 500","ISA Brown","Lohmann Brown","Lohmann White","Hy-Line Brown"]})
    if "age" in j or "age_days" in j or "age_weeks" in j:
        questions.append({"field":"age","question":"Âge exact ? (jours broilers, semaines pondeuses)"})
    if "sex" in j:
        questions.append({"field":"sex","question":"Sexe ?","options":["male","female","mixed"]})
    if "phase" in j:
        questions.append({"field":"phase","question":"Phase ?","options":["starter","grower","finisher"]})
    if "flock_size" in j:
        questions.append({"field":"flock_size","question":"Effectif (nb d’oiseaux) ?"})
    if "housing" in j:
        questions.append({"field":"housing","question":"Type de bâtiment ?","options":["tunnel","naturally_ventilated","free_range"]})
    if "program_type" in j:
        questions.append({"field":"program_type","question":"Type de programme ?","options":["vaccination","lighting","brooding","feeding_program"]})

    return {
        "completeness_score": round(score,3),
        "missing_fields": missing,
        "follow_up_questions": questions[:3]
    }
