import os
import re
import json
from typing import Dict, List, Tuple, Any
from app.api.v1.utils.entity_normalizer import EntityNormalizer
from app.api.v1.utils.validation_pipeline import validate_and_score
from app.api.v1.utils.openai_utils import safe_chat_completion

class ContextExtractor:
    """
    Extracts structured context from a raw question.
    Uses GPT via safe_chat_completion to parse key fields into JSON,
    then falls back to regex extraction on failure.
    Returns: (context_dict, completeness_score, missing_fields)
    """
    def __init__(self, use_gpt: bool = True):
        self.normalizer = EntityNormalizer()
        self.use_gpt = use_gpt

    def extract(self, question: str) -> Tuple[Dict[str, Any], float, List[str]]:
        context: Dict[str, Any] = {}
        if self.use_gpt:
            prompt = (
                "Vous êtes un assistant avicole. À partir de la question utilisateur, "
                "extrayez les champs suivants si présents: age_jours, production_type, age_phase, sex_category, "
                "site_type, housing_type, activity, parameter, numeric_value, issue, user_role, objective, breed. "
                "Répondez au format JSON avec ces clés si trouvées." 
                f"Question: {question}"
            )
            try:
                resp = safe_chat_completion(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=256
                )
                extracted = json.loads(resp.choices[0].message.content.strip())
                if isinstance(extracted, dict):
                    context.update(extracted)
                else:
                    context = self._regex_extract(question)
            except Exception:
                context = self._regex_extract(question)
        else:
            context = self._regex_extract(question)

        context = self.normalizer.normalize(context)
        score, missing = validate_and_score(context, question)
        return context, score, missing

    def _regex_extract(self, question: str) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {}
        patterns = {
            "production_type": r"\b(?:broiler|layer|breeder|pullet)s?\b",
            "age_phase": r"\b(?:day|d|week|wk|wks|month|mo)s?[-\s]*old\b|\b(?:at|from|on)?\s?\b(?:day\s?\d{1,2}|week\s?\d{1,2})\b",
            "sex_category": r"\b(?:male|female|mixed flock|pullets?|cockerels?)\b",
            "site_type": r"\b(?:hatchery|barn|house|processing plant|feed mill)\b",
            "housing_type": r"\b(?:tunnel-ventilated|open-sided|enriched cage|aviary|floor|slatted floor)\b",
            "activity": r"\b(?:feeding|vaccination|beak trimming|culling|catching|lighting|ventilation|weighing|sampling)\b",
            "parameter": r"\b(?:weight|body weight|FCR|feed conversion|mortality|water intake|egg production|temperature|humidity|NH3|CO2|uniformity)\b",
            "numeric_value": r"""
                \b
                (\d+(?:[\.,]\d+)?\s*
                (?:
                    kg|g|mg|\u00b5g|mcg|lb|lbs|oz|
                    l|L|ml|mL|gal|gallon[s]?|qt[s]?|
                    \u00b0C|\u00b0F|C|F|
                    cm|mm|m|in(?:ch)?(?:es)?|ft|feet|
                    ppm|%|bpm|IU|
                    g/bird|lb/bird|oz/bird|
                    g/day|g/bird/day|lb/day|
                    birds|eggs|head[s]?|
                    cal|kcal|kcal/kg|kcal/lb
                ))
                \b
            """,
            "issue": r"\b(" + "|".join([
                "heat stress", "thermal stress", "feather pecking", "pecking", "cannibalism",
                "aggression", "fighting", "lethargy", "inactivity", "reduced mobility",
                "lameness", "leg problems", "limping", "breast blister", "keel bone damage",
                "footpad dermatitis", "footpad lesions", "slipping", "loss of balance", "paralysis", "paresis",
                "high mortality", "sudden death syndrome", "sudden death", "flip[- ]?over", "low viability",
                "low livability", "deformities", "skeletal defects",
                "wet litter", "ammonia smell", "high NH3", "high temperature", "overheating",
                "cold drafts", "low barn temperature", "poor air quality", "low airflow", "CO2 buildup",
                "underfeeding", "feed restriction", "poor FCR", "high feed conversion ratio",
                "waterline blockage", "no access to water", "nutrient deficiency", "excess salt",
                "poor formulation",
                "respiratory issues", "sneezing", "rales", "enteritis", "diarrhea", "wet droppings",
                "bacterial infection", "colibacillosis", "viral outbreak", "IBV", "NDV", "AI", "coccidiosis",
                "vaccination failure", "poor immune response",
                "low egg production", "drop in lay rate", "thin shells", "shell defects", "poor shell quality",
                "dirty eggs", "soiled eggs", "floor eggs", "eggs outside nesting area", "egg binding"
            ]) + r")\b",
            "user_role": r"\b(?:farmer|grower|veterinarian|nutritionist|technician|supervisor|consultant)\b",
            "objective": r"\b(?:optimize|improve|detect|prevent|reduce|increase|adjust|monitor)\b",
            "breed": r"\b(ross\s?\d{3}|ross|cobb\s?\d{3}|cobb|hubbard|dekalb|hy-?line|lohmann|isa\s?brown|isa)\b",
        }

        for field, pat in patterns.items():
            matches = re.findall(pat, question, re.IGNORECASE | re.VERBOSE)
            if matches:
                ctx[field] = matches[0] if len(matches) == 1 else matches
        return ctx
