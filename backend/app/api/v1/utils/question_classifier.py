# app/api/v1/utils/question_classifier.py
from __future__ import annotations

from typing import Dict, Any
from app.api.v1.pipeline.intent_registry import infer_intent

def classify_question(question: Dict[str, Any] | str) -> str:
    """
    Classification légère — délègue aux signaux du registry.
    Accepte texte brut ou dict avec clé 'text'.
    """
    if isinstance(question, dict):
        text = str(question.get("text") or question.get("question") or "")
    else:
        text = str(question or "")
    return infer_intent(text)
