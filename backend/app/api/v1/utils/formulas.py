# -*- coding: utf-8 -*-
"""
Compute-first helpers (generic baselines; tune constants to your standards).
All functions return simple numeric outputs for quick guidance.
"""
from typing import Optional

# --- Production & economics ---

def iep(ep: float, survie_pct: float, fcr: float, poids_vif_kg: float, age_jours: int) -> Optional[float]:
    """Indice d'Efficacité de Production (variante générique)."""
    try:
        return (ep * (survie_pct/100.0) * poids_vif_kg) / (fcr * max(1, age_jours)) * 100.0
    except Exception:
        return None

def cout_aliment_par_kg_vif(prix_aliment_tonne: float, fcr: float) -> Optional[float]:
    """Feed cost per kg live weight = (€/t / 1000) * FCR"""
    try:
        return (prix_aliment_tonne / 1000.0) * fcr
    except Exception:
        return None

def cout_total_aliment(effectif: int, poids_abattage_kg: float, fcr: float, prix_tonne: float, survie_pct: float = 95.0) -> Optional[float]:
    """Total feed cost for the flock until slaughter (order of magnitude)."""
    try:
        oiseaux_vivants = effectif * (survie_pct/100.0)
        kg_vifs = oiseaux_vivants * poids_abattage_kg
        kg_aliment = kg_vifs * fcr
        return kg_aliment * (prix_tonne/1000.0)
    except Exception:
        return None

# --- Environment setpoints ---

def setpoint_temp_C_broiler(age_jours: int, housing: str = "tunnel") -> float:
    """Generic broiler temp curve (°C)."""
    if age_jours <= 1: return 32.0
    if age_jours <= 7: return 30.0
    if age_jours <= 14: return 27.0
    if age_jours <= 21: return 24.0
    if age_jours <= 28: return 22.0
    return 21.0

def setpoint_hr_pct(age_jours: int) -> float:
    """Generic target RH% by age."""
    if age_jours <= 7: return 65.0
    if age_jours <= 21: return 60.0
    return 55.0

def co2_max_ppm() -> int:
    """Max acceptable CO2 ppm (generic)."""
    return 3000

def nh3_max_ppm() -> int:
    """Max acceptable NH3 ppm (generic)."""
    return 20

def lux_program_broiler(age_jours: int) -> float:
    """Generic lux by age for broilers."""
    if age_jours <= 7: return 30.0
    if age_jours <= 21: return 10.0
    return 5.0

# --- Ventilation & heat ---

def vent_min_m3h_par_kg(age_jours: int, saison: str = "hiver") -> float:
    """Minimal ventilation guideline (m3/h/kg) by age & season (very generic)."""
    base = 0.6 if saison == "hiver" else 1.0
    if age_jours <= 7: return base * 0.3
    if age_jours <= 21: return base * 0.8
    return base * 1.2

def vent_min_total_m3h(poids_moy_kg: float, effectif: int, age_jours: int, saison: str = "hiver") -> float:
    """m3/h = m3/h/kg * kg_total"""
    kg_total = max(0.0, poids_moy_kg) * max(0, effectif)
    return vent_min_m3h_par_kg(age_jours, saison) * kg_total

def debit_tunnel_m3h(kg_total: float, charge_thermique_w_kg: float=15.0, deltaT_C: float=5.0) -> Optional[float]:
    """Rough tunnel airflow sizing from heat removal needs."""
    try:
        heat_w = kg_total * charge_thermique_w_kg
        return heat_w / (0.33 * max(1e-3, deltaT_C))
    except Exception:
        return None

def chaleur_a_extraire_w(kg_total: float, charge_thermique_w_kg: float=15.0) -> Optional[float]:
    try:
        return kg_total * charge_thermique_w_kg
    except Exception:
        return None

# --- Water & equipment ---

def conso_eau_j(effectif: int, age_jours: int, temp_C: float=20.0) -> Optional[float]:
    """Daily water consumption for the flock (L/day)."""
    if effectif <= 0: return None
    base_per_bird = 0.05 if age_jours < 7 else (0.12 if age_jours < 21 else 0.18)
    temp_factor = 1.0 + max(0.0, (temp_C - 20.0)) * 0.03
    return effectif * base_per_bird * temp_factor

def debit_eau_l_min(effectif: int, age_jours: int, nipples_par_ligne: int, lignes: int) -> Optional[float]:
    """Total water flow needed (L/min) assuming nipples per line and lines available."""
    if effectif <= 0 or nipples_par_ligne <= 0 or lignes <= 0: return None
    # Take daily water, convert to L/min averaged on 12h drinking window
    daily = conso_eau_j(effectif, age_jours) or 0.0
    return daily / (12.0 * 60.0)

def dimension_mangeoires(effectif: int, age_jours: int, type: str='chaîne') -> Optional[float]:
    """Total required feeder space (cm)."""
    if effectif <= 0: return None
    per_bird = 2.0 if age_jours < 14 else (3.0 if age_jours < 28 else 4.0)
    if type == 'assiette':
        per_bird *= 0.8
    return per_bird * effectif

def dimension_abreuvoirs(effectif: int, age_jours: int, type: str='nipple') -> Optional[float]:
    """#nipples (if nipple) or cm (if bell)."""
    if effectif <= 0: return None
    if type == 'nipple':
        return round(effectif / 12.0, 1)
    per_bird_cm = 1.0 if age_jours < 14 else 1.5
    return per_bird_cm * effectif
