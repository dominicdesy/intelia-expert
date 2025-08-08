import os
import openai
from typing import List
from app.api.v1.utils.config import MAX_CLARIFICATION_ROUNDS

# Configure OpenAI key for GPT-based clarification
openai.api_key = os.getenv("OPENAI_API_KEY")

class ClarificationManager:
    """
    Generates clarification questions based on missing fields.
    Uses OpenAI GPT for dynamic question formulation with a rule-based fallback.
    """
    def __init__(self, use_gpt: bool = True):
        self.use_gpt = use_gpt

    def generate(self, missing_fields: List[str], round_number: int = 1) -> List[str]:
        if round_number > MAX_CLARIFICATION_ROUNDS or not missing_fields:
            return []

        # Use GPT to craft questions if enabled
        if self.use_gpt:
            prompt = (
                f"Vous êtes un assistant avicole. Il manque les informations suivantes pour répondre précisément : {missing_fields}. "
                "Formulez 2 ou 3 questions courtes et précises en français pour obtenir ces détails."
            )
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=150
                )
                content = resp.choices[0].message.content.strip()
                # Split into individual questions
                questions = [q.strip("-• \n") for q in content.split("\n") if q.strip()]
                if questions:
                    return questions
            except Exception:
                # In case of API error, fallback to rule-based
                pass

        # Rule-based fallback
        questions: List[str] = []
        for field in missing_fields:
            if field == "age_jours":
                questions.append("Quel est l'âge des sujets en jours ?")
            elif field == "ferme":
                questions.append("Quel est le nom de la ferme concernée ?")
            elif field == "race":
                questions.append("Quelle est la race ou le génotype de l'animal ?")
            else:
                questions.append(f"Pouvez-vous préciser : {field} ?")
        return questions
