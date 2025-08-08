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
                "extrayez les champs suivants si présents: ferme, race, age_jours, lot, date, objectif. "
                "Répondez au format JSON: {\"ferme\":…, \"race\":…, …}. "
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

        # Normalize values
        context = self.normalizer.normalize(context)
        # Validate against dynamic schema
        score, missing = validate_and_score(context, question)
        return context, score, missing

    def _regex_extract(self, question: str) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {}
        # Example: extract age in days
        m = re.search(r"(\d+)\s*(?:jours|jour)", question, re.IGNORECASE)
        if m:
            ctx["age_jours"] = m.group(1)
        # TODO: add more patterns for 'ferme', 'race', etc.
        return ctx
