from typing import Dict, Any, List, Tuple
from app.api.v1.utils.config import MAX_CLARIFICATION_ROUNDS

# Define required context fields for a complete question
REQUIRED_FIELDS = ["age_jours", "ferme", "race"]


def validate_and_score(context: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Checks which required fields are present and returns:
      - score (0.0 to 1.0)
      - list of missing fields
    """
    missing = [field for field in REQUIRED_FIELDS if field not in context]
    filled = len(REQUIRED_FIELDS) - len(missing)
    score = filled / len(REQUIRED_FIELDS)
    return score, missing
