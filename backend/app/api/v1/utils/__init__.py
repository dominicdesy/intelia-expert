# app/api/v1/utils/__init__.py
"""
Utils package — fonctions utilitaires pour le pipeline, la validation et l'intégration.
Exemple d'import :
    from app.api.v1.utils import formulas, units
    from app.api.v1.utils.formulas import estimate_water_intake_l_per_1000
"""

__all__ = [
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
]
