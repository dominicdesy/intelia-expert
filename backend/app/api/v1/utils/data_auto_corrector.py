from typing import Dict, Any

class DataAutoCorrector:
    """
    Corrects and formats context values post-extraction:
      - adjust units if needed
      - basic typo fixes
    """
    @staticmethod
    def correct(context: Dict[str, Any]) -> Dict[str, Any]:
        corrected = {}
        for key, value in context.items():
            # Example: ensure age_jours is int
            if key == "age_jours":
                try:
                    corrected[key] = int(value)
                except (TypeError, ValueError):
                    # fallback to missing or ignore
                    continue
            else:
                corrected[key] = value
        return corrected
