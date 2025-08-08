import os
import re
import json
import openai
from typing import Dict, List, Tuple
from app.api.v1.utils.entity_normalizer import EntityNormalizer
from app.api.v1.utils.validation_pipeline import validate_and_score

# Configure OpenAI for context extraction
openai.api_key = os.getenv("OPENAI_API_KEY")

class ContextExtractor:
    """
    Extracts structured context from a raw question.
    Uses OpenAI GPT for dynamic extraction and falls back to regex-based extraction.
    Returns a tuple: (context_dict, completeness_score, missing_fields)
    """
    def __init__(self, use_gpt: bool = True):
        self.normalizer = EntityNormalizer()
        self.use_gpt = use_gpt

    def extract(self, question: str) -> Tuple[Dict[str, str], float, List[str]]:
        context: Dict[str, str] = {}
        if self.use_gpt:
            prompt = (
                "Vous êtes un assistant avicole. À partir de la question utilisateur, "
                "extrayez les champs suivants si présents: ferme, race, age_jours, lot, date, objectif. "
                "Répondez au format JSON comme {\"ferme\":..., \"race\":..., ...}. "
                f"Question: {question}"
            )
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=256
                )
                extracted = json.loads(resp.choices[0].message.content.strip())
                if isinstance(extracted, dict):
                    context.update(extracted)
            except Exception:
                # Fallback to regex on any error
                context = self._regex_extract(question)
        else:
            context = self._regex_extract(question)

        # Normalize extracted values
        context = self.normalizer.normalize(context)

        # Validate and score
        score, missing = validate_and_score(context)
        return context, score, missing

    def _regex_extract(self, question: str) -> Dict[str, str]:
        ctx: Dict[str, str] = {}
        # Example: extract age in days
        age_match = re.search(r"(\d+)\s*(?:jours|jour)", question, re.IGNORECASE)
        if age_match:
            ctx["age_jours"] = age_match.group(1)
        # Additional regex patterns can be added here (ferme, race, etc.)
        return ctx
