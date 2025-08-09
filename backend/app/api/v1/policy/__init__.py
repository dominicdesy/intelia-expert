# app/api/v1/policy/__init__.py
"""
Policy package — contient les règles de sécurité, de conformité et les garde-fous métier.
Exemple d'import :
    from app.api.v1.policy import safety_rules
    from app.api.v1.policy.safety_rules import requires_vet_redirect
"""

from . import safety_rules

__all__ = [
    "safety_rules",
]
