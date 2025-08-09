# app/api/v1/utils/units.py
from __future__ import annotations
from typing import Tuple

# Conversions de base
CFM_PER_M3H = 0.588577  # 1 m³/h ≈ 0.5886 CFM
MJ_PER_KCAL = 0.004184

def c_to_f(c: float) -> float: return c * 9.0 / 5.0 + 32.0
def f_to_c(f: float) -> float: return (f - 32.0) * 5.0 / 9.0

def m3h_to_cfm(m3h: float) -> float: return m3h * CFM_PER_M3H
def cfm_to_m3h(cfm: float) -> float: return cfm / CFM_PER_M3H

def kcalkg_to_mjkg(k: float) -> float: return k * MJ_PER_KCAL
def mjkg_to_kcalkg(m: float) -> float: return m / MJ_PER_KCAL

def ppm_to_mg_m3(ppm: float, gas_mw: float = 17.031) -> float:
    """Approx. NH3 MW=17.031 g/mol at 25°C, 1 atm => mg/m³ ≈ ppm * MW / 24.45"""
    return ppm * gas_mw / 24.45

def mg_m3_to_ppm(mg_m3: float, gas_mw: float = 17.031) -> float:
    return mg_m3 * 24.45 / gas_mw

def fmt_value_unit(value: float, unit: str) -> Tuple[float, str]:
    return float(value), str(unit)

# Helpers d’arrondi & normalisation d’unités
def round_sig(x: float, sig: int = 3) -> float:
    """Arrondi significatif simple."""
    if x == 0 or sig <= 0: return 0.0
    from math import log10, floor
    p = -int(floor(log10(abs(x)))) + (sig - 1)
    return round(x, max(0, p))

def normalize_unit_label(unit: str) -> str:
    """Unifie les notations d’unités usuelles."""
    u = (unit or "").strip().lower()
    u = u.replace("m3", "m³").replace(" / ", "/").replace(" ", "")
    u = u.replace("kcalkg", "kcal/kg").replace("kcal.kg", "kcal/kg")
    u = u.replace("m³/h/kg", "m³/h/kg").replace("m3/h/kg", "m³/h/kg")
    return u
