# app/prompts/prompt_templates.py
from __future__ import annotations
from typing import Dict

_TEMPLATES: Dict[str, str] = {
    "facts_only": (
        "Donne la valeur numérique en premier (unité SI), puis la plage et la source [Doc N]. "
        "Aucune digression."
    ),
    "calc": (
        "Présente le résultat calculé (valeur + unité), liste 2 hypothèses et indique comment affiner."
    ),
    "diagnostic_triage": (
        "Pose au maximum 3 questions pour préciser le cas, puis donne 3 causes probables et 3 actions immédiates sûres."
    ),
}


def get_template(key: str) -> str:
    return _TEMPLATES.get(key, "Réponse concise et structurée.")