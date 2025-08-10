from typing import Dict, Any

class EntityNormalizer:
    """
    Normalizes extracted context values:
      - strip whitespace
      - unify casing
      - convert numeric strings to int where appropriate
    """
    def normalize(self, context: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for key, value in context.items():
            if isinstance(value, str):
                v = value.strip()
                # Lowercase certain keys except names
                if key != "ferme":
                    v = v.lower()
                # Convert numeric strings to int
                if v.isdigit():
                    normalized[key] = int(v)
                    continue
                normalized[key] = v
            else:
                normalized[key] = value
        return normalized
