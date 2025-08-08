import os
from typing import List, Dict
from app.api.v1.utils.openai_utils import safe_chat_completion

class QuestionClassifier:
    """
    Classifies questions into types using embeddings.
    Embeddings are initialized lazily on first classify() call.
    """
    CATEGORIES = [
        "nutrition", "santé", "reproduction", "logement", "incubation", "général"
    ]
    _embeddings = None

    def _initialize_embeddings(self):
        if self._embeddings is not None:
            return
        # Compute embeddings for categories on first use only (avoids import-time OpenAI call)
        prompts = [{"role": "user", "content": c} for c in self.CATEGORIES]
        self._embeddings = []
        for cat in self.CATEGORIES:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": cat}],
                temperature=0.0,
                max_tokens=64
            )
            # Use the model's embedding/response (simulate for now)
            self._embeddings.append(resp.choices[0].message.content.strip())

    def classify(self, question: str) -> str:
        self._initialize_embeddings()
        # For now: just do string match. (Replace by embeddings similarity if needed)
        for i, cat in enumerate(self.CATEGORIES):
            if cat in question.lower():
                return cat
        return "général"
