# app/api/v1/prompts/__init__.py
"""
Prompts package — contient les modèles de prompt utilisés par le pipeline et le RAG.
Exemple d'import :
    from app.api.v1.prompts import prompt_templates
    from app.api.v1.prompts.prompt_templates import get_template
"""

from . import prompt_templates

__all__ = [
    "prompt_templates",
]
