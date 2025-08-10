# app/api/v1/utils/formulas.py
from __future__ import annotations
from typing import Dict, Tuple, Optional

# ⚠️ Ces formules donnent des ordres de grandeur prudents.
# Adaptez les coefficients à vos tables internes si nécessaire.

# -----------------------------
# Eau & ventilation (existant)
# -----------------------------
def estimate_water_intake_l_per_1000(
    *, age_days: Optional[int], ambient_c: Optional[float], species: Optional[str] = None
) -> Tuple[Optional[float], Dict]:
    """Estimation consommation d'eau (L/j/1000 oiseaux) selon âge & T° (approx)."""
    if not age_days:
        return None, {"reason": "missing age"}
    base = max(30.0, 8.0 + 1.8 * age_days)  # ~20°C
    temp = ambient_c if ambient_c is not None else 20.0
    factor = (1.0 + 0.03 * (temp - 20.0)) if temp >= 20 else (1.0 - 0.02 * (20.0 - temp))
    est = base * max(0.6, min(factor, 1.6))
    return est, {"age_days": age_days, "ambient_c": temp}


def min_ventilation_m3h_per_kg(*, age_days: Optional[int], avg_bw_g: Optional[float]) -> Tuple[Optional[float], Dict]:
    """Ventilation minimale (m³/h/kg) — règle conservatrice simple."""
    if avg_bw_g:
        kg = max(0.2, avg_bw_g / 1000.0)
    elif age_days:
        kg = max(0.2, 0.02 * (age_days ** 1.6) / 1000.0)  # approx
    else:
        return None, {"reason": "missing age and weight"}
    val = 0.8 if kg < 1.5 else 1.0
    return val, {"age_days": age_days, "avg_bw_kg": kg}

# -----------------------------
# Indices de production
# -----------------------------
def iep_broiler(
    *, livability_pct: float, avg_weight_kg: float, fcr: float, age_days: int
) -> Tuple[Optional[float], Dict]:
    """
    IEP / EPEF broiler (définition usuelle):
        IEP = (Livability% × Poids vif moyen (kg) × 100) / (FCR × Âge (jours))
    """
    try:
        if not all([livability_pct, avg_weight_kg, fcr, age_days]):
            return None, {"reason": "missing params"}
        if fcr <= 0 or age_days <= 0:
            return None, {"reason": "invalid params"}
        iep = (livability_pct * avg_weight_kg * 100.0) / (fcr * age_days)
        return iep, {
            "livability_pct": livability_pct,
            "avg_weight_kg": avg_weight_kg,
            "fcr": fcr,
            "age_days": age_days,
            "formula": "IEP=(Liv%*BWkg*100)/(FCR*Age)",
        }
    except Exception as e:
        return None, {"error": str(e)}


def epd_layer_placeholder(
    *, hen_day_production_pct: float, avg_egg_weight_g: float
) -> Tuple[Optional[float], Dict]:
    """
    Placeholder (à ajuster à votre convention EPD locale si différente).
    Ici on retourne la masse d'œufs pondus par poule et par jour (g/poule/j):
        EPD ≈ Hen-day % × Poids œuf (g) / 100
    """
    try:
        if hen_day_production_pct is None or avg_egg_weight_g is None:
            return None, {"reason": "missing params"}
        epd = (hen_day_production_pct * avg_egg_weight_g) / 100.0
        return epd, {
            "hen_day_production_pct": hen_day_production_pct,
            "avg_egg_weight_g": avg_egg_weight_g,
            "note": "Placeholder — définissez votre EPD exact si différent.",
        }
    except Exception as e:
        return None, {"error": str(e)}

# -----------------------------
# Coût alimentaire & économie
# -----------------------------
def cout_aliment_par_kg_vif(
    *, prix_aliment_tonne_eur: float, fcr: float
) -> Tuple[Optional[float], Dict]:
    """
    Coût aliment par kg vif (€ / kg vif):
        coût = (prix €/t / 1000) × FCR
    """
    try:
        if prix_aliment_tonne_eur is None or fcr is None:
            return None, {"reason": "missing params"}
        if fcr <= 0 or prix_aliment_tonne_eur <= 0:
            return None, {"reason": "invalid params"}
        eur_per_kg_feed = prix_aliment_tonne_eur / 1000.0
        cost = eur_per_kg_feed * fcr
        return cost, {"prix_aliment_tonne_eur": prix_aliment_tonne_eur, "fcr": fcr}
    except Exception as e:
        return None, {"error": str(e)}

# -----------------------------
# Dimensionnement équipements
# -----------------------------
def dimension_mangeoires(
    *, effectif: int, age_days: int, type_: str = "chaine"
) -> Tuple[Optional[Dict], Dict]:
    """
    Dimension mangeoires.
    - Chaine: espace par oiseau (cm/oiseau) selon âge.
      <14 j: 2.0 cm ; 14–27 j: 2.5 cm ; >=28 j: 3.5 cm
    - Assiette (pan): oiseaux par assiette.
      <14 j: 45 ; 14–27 j: 20 ; >=28 j: 12
    """
    try:
        if not effectif or effectif <= 0 or age_days is None:
            return None, {"reason": "missing params"}
        t = (type_ or "chaine").lower()
        if "chai" in t:  # chaine
            if age_days < 14:
                cm_per_bird = 2.0
            elif age_days < 28:
                cm_per_bird = 2.5
            else:
                cm_per_bird = 3.5
            total_cm = cm_per_bird * effectif
            return (
                {"type": "chaine", "cm_per_bird": cm_per_bird, "total_cm_required": total_cm},
                {"effectif": effectif, "age_days": age_days},
            )
        else:  # assiette/pan
            if age_days < 14:
                birds_per_pan = 45
            elif age_days < 28:
                birds_per_pan = 20
            else:
                birds_per_pan = 12
            pans = max(1, int(round(effectif / birds_per_pan + 0.499)))
            return (
                {"type": "assiette", "birds_per_pan": birds_per_pan, "pans_required": pans},
                {"effectif": effectif, "age_days": age_days},
            )
    except Exception as e:
        return None, {"error": str(e)}


def dimension_abreuvoirs(
    *, effectif: int, age_days: int, type_: str = "nipple"
) -> Tuple[Optional[Dict], Dict]:
    """
    Dimension abreuvoirs.
    - Nipple: oiseaux par nipple selon âge (démarrage strict).
      <14 j: 10 ; 14–27 j: 12 ; >=28 j: 15
    - Cloche: ~90 oiseaux par cloche (moyenne 80–100).
    """
    try:
        if not effectif or effectif <= 0 or age_days is None:
            return None, {"reason": "missing params"}
        t = (type_ or "nipple").lower()
        if "nipp" in t:
            if age_days < 14:
                birds_per_point = 10
            elif age_days < 28:
                birds_per_point = 12
            else:
                birds_per_point = 15
            points = max(1, int(round(effectif / birds_per_point + 0.499)))
            return (
                {"type": "nipple", "birds_per_point": birds_per_point, "points_required": points},
                {"effectif": effectif, "age_days": age_days},
            )
        else:  # cloche
            birds_per_bell = 90
            bells = max(1, int(round(effectif / birds_per_bell + 0.499)))
            return (
                {"type": "cloche", "birds_per_bell": birds_per_bell, "bells_required": bells},
                {"effectif": effectif, "age_days": age_days},
            )
    except Exception as e:
        return None, {"error": str(e)}

# -----------------------------
# Débit tunnel & chaleur
# -----------------------------
def chaleur_a_extraire_w(*, kg_total: float, charge_thermique_w_kg: float = 10.0) -> Tuple[Optional[float], Dict]:
    """
    Chaleur à extraire (W) ≈ kg_total × charge_thermique (W/kg).
    Par défaut 10 W/kg (conservateur). Augmenter en stress (12–15+ W/kg).
    """
    try:
        if kg_total is None or kg_total <= 0:
            return None, {"reason": "invalid kg_total"}
        heat_w = kg_total * max(5.0, charge_thermique_w_kg)
        return heat_w, {"kg_total": kg_total, "charge_w_kg": charge_thermique_w_kg}
    except Exception as e:
        return None, {"error": str(e)}


def debit_tunnel_m3h(
    *, kg_total: float, deltaT_C: float, charge_thermique_w_kg: float = 10.0
) -> Tuple[Optional[float], Dict]:
    """
    Débit d'air requis (m³/h) à partir de la chaleur à extraire et du ΔT:
        Q(m³/h) = Heat(W) * 3600 / (ρ * Cp * ΔT)
      Approximons (ρ*Cp) ≈ 1206 J/(m³·K) → Q ≈ Heat * 2.985 / ΔT
    """
    try:
        if kg_total is None or kg_total <= 0 or deltaT_C is None or deltaT_C <= 0:
            return None, {"reason": "invalid params"}
        heat_w, _ = chaleur_a_extraire_w(kg_total=kg_total, charge_thermique_w_kg=charge_thermique_w_kg)
        if heat_w is None:
            return None, {"reason": "heat calc failed"}
        q_m3h = heat_w * 2.985 / deltaT_C
        return q_m3h, {"kg_total": kg_total, "deltaT_C": deltaT_C, "charge_w_kg": charge_thermique_w_kg}
    except Exception as e:
        return None, {"error": str(e)}
