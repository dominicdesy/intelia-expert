# -*- coding: utf-8 -*-
# app/api/v1/utils/__init__.py
"""
Utils package — fonctions utilitaires pour le pipeline, la validation et l'intégration.

Exemples :
    from app.api.v1.utils import formulas, units
    from app.api.v1.utils import conso_eau_j, vent_min_m3h_par_kg
    from app.api.v1.utils.question_classifier import classify, Intention

Notes :
- On expose au niveau package quelques fonctions "courantes" de formulas.
- On garde les imports module-level pour éviter les boucles d'import (pas d'import du pipeline ici).
- Alias de rétro-compatibilité : estimate_water_intake_l_per_1000 -> conso_eau_j(..., effectif=1000).
"""

# --- Modules utilitaires (importables tels quels) ---
from . import config
from . import entity_normalizer
from . import data_auto_corrector
from . import validation_pipeline
from . import response_generator
from . import integrations
from . import openai_utils
from . import question_classifier
from . import formulas
from . import units
from . import taxonomy

# Optionnels (présents dans ton arbo)
try:
    from . import context_validator     # si utilisé par ailleurs
except Exception:
    context_validator = None
try:
    from . import conversation_tracker  # si utilisé par ailleurs
except Exception:
    conversation_tracker = None

# --- Exposition de fonctions fréquemment utilisées (convenience re-exports) ---
from .formulas import (
    conso_eau_j,
    debit_eau_l_min,
    dimension_mangeoires,
    dimension_abreuvoirs,
    vent_min_m3h_par_kg,
    vent_min_total_m3h,
    setpoint_temp_C_broiler,
    setpoint_hr_pct,
    co2_max_ppm,
    nh3_max_ppm,
    lux_program_broiler,
    cout_aliment_par_kg_vif,
    cout_total_aliment,
    iep,
    debit_tunnel_m3h,
    chaleur_a_extraire_w,
)

# --- Alias rétro-compatibilité ---
def estimate_water_intake_l_per_1000(age_days: int, temp_C: float = 20.0) -> float:
    """
    Ancien alias utilisé dans certains appels historiques.
    Équivaut à conso_eau_j(effectif=1000, age_jours=age_days, temp_C=temp_C).
    """
    val = conso_eau_j(1000, age_days, temp_C)
    return float(val or 0.0)

__all__ = [
    # modules
    "config",
    "entity_normalizer",
    "data_auto_corrector",
    "validation_pipeline",
    "response_generator",
    "integrations",
    "openai_utils",
    "question_classifier",
    "formulas",
    "units",
    "taxonomy",
    "context_validator",
    "conversation_tracker",
    # re-exports (functions)
    "conso_eau_j",
    "debit_eau_l_min",
    "dimension_mangeoires",
    "dimension_abreuvoirs",
    "vent_min_m3h_par_kg",
    "vent_min_total_m3h",
    "setpoint_temp_C_broiler",
    "setpoint_hr_pct",
    "co2_max_ppm",
    "nh3_max_ppm",
    "lux_program_broiler",
    "cout_aliment_par_kg_vif",
    "cout_total_aliment",
    "iep",
    "debit_tunnel_m3h",
    "chaleur_a_extraire_w",
    # back-compat
    "estimate_water_intake_l_per_1000",
]