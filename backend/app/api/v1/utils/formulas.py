# app/utils/formulas.py
from __future__ import annotations
from typing import Dict, Tuple, Optional

# Ces formules sont des approximations raisonnables pour un premier jet.
# À affiner avec vos tables internes / littérature.


def estimate_water_intake_l_per_1000(*, age_days: Optional[int], ambient_c: Optional[float], species: Optional[str] = None) -> Tuple[Optional[float], Dict]:
    """Estimation consommation d'eau (L/j/1000 oiseaux) en fonction de l'âge et T°.
    Hypothèses simples: base par âge + facteur T°.
    """
    if not age_days:
        return None, {"reason": "missing age"}
    # base approximative (broilers): augmente avec l'âge
    base = max(30.0, 8.0 + 1.8 * age_days)  # L/j/1000 à ~20°C (très grossier)
    temp = ambient_c if ambient_c is not None else 20.0
    # facteur T°: +3% par °C au-dessus de 20°C, -2% par °C en-dessous
    if temp >= 20:
        factor = 1.0 + 0.03 * (temp - 20.0)
    else:
        factor = 1.0 - 0.02 * (20.0 - temp)
    est = base * max(0.6, min(factor, 1.6))
    return est, {"age_days": age_days, "ambient_c": temp}


def min_ventilation_m3h_per_kg(*, age_days: Optional[int], avg_bw_g: Optional[float]) -> Tuple[Optional[float], Dict]:
    """Estimation ventilation minimale (m³/h/kg). Placeholder conservateur.
    Ex: 0.7–1.2 m³/h/kg selon âge/poids (à ajuster par T°, NH3/CO2).
    """
    if avg_bw_g:
        kg = max(0.2, avg_bw_g / 1000.0)
    elif age_days:
        # approx poids ~ 0.02 * age^1.6 (grossier)
        kg = max(0.2, 0.02 * (age_days ** 1.6) / 1000.0)
    else:
        return None, {"reason": "missing age and weight"}
    # règle minimale simple
    val = 0.8 if kg < 1.5 else 1.0
    return val, {"age_days": age_days, "avg_bw_kg": kg}