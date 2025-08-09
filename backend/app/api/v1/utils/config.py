# app/api/v1/utils/config.py
import os

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

# --- Nouveaux paliers (avec overrides via ENV) ---
CLARIFY_MAX = _clamp01(float(os.getenv("CLARIFY_MAX", "0.40")))   # < 0.40 -> poser des questions
WARN_MAX    = _clamp01(float(os.getenv("WARN_MAX", "0.70")))      # 0.40–0.70 -> réponse avec avertissement
FULL_MIN    = _clamp01(float(os.getenv("FULL_MIN", "0.90")))      # >= 0.90 -> réponse complète

# Cohérence simple (au cas où quelqu’un mettrait des ENV incohérents)
if not (CLARIFY_MAX <= WARN_MAX <= FULL_MIN):
    CLARIFY_MAX, WARN_MAX, FULL_MIN = 0.40, 0.70, 0.90  # défauts sains

COMPLETENESS_THRESHOLDS = {
    "clarify_max": CLARIFY_MAX,
    "warn_max": WARN_MAX,
    "full_min": FULL_MIN,
}

def choose_strategy(score: float) -> str:
    """Retourne: 'clarification' | 'answer_with_warning' | 'answer'"""
    s = _clamp01(float(score))
    if s < CLARIFY_MAX:
        return "clarification"
    if s < WARN_MAX:
        return "answer_with_warning"
    return "answer" if s >= FULL_MIN else "answer_with_warning"

# --- Compatibilité ascendante (ton code existant peut encore lire ce champ) ---
COMPLETENESS_THRESHOLD: float = WARN_MAX  # seuil minimal pour “réponse utile” sans être “complète”

# --- Tours de clarification ---
MAX_CLARIFICATION_ROUNDS: int = int(os.getenv("MAX_CLARIFICATION_ROUNDS", "3"))
