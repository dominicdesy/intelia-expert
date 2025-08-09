from typing import Dict, Any, List, Tuple
from app.api.v1.utils.config import MAX_CLARIFICATION_ROUNDS
from app.api.v1.utils.question_classifier import classify_question, REQUIRED_FIELDS_BY_TYPE

def validate_and_score(context: Dict[str, Any], question: str) -> Tuple[float, List[str]]:
    """
    Checks which required fields are present based on question category and returns:
      - score (0.0 to 1.0)
      - list of missing fields
    """
    # 1. Classify the question (nutrition, sante, etc.)
    q_type = classify_question(question)
    required_fields = REQUIRED_FIELDS_BY_TYPE.get(q_type, [])

    # 2. Identify missing fields
    missing = [f for f in required_fields if f not in context]
    filled = len(required_fields) - len(missing)

    # 3. Compute completeness score
    score = (filled / len(required_fields)) if required_fields else 1.0
    return score, missing
