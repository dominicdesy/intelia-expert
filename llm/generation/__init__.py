# -*- coding: utf-8 -*-
"""
Generation module - Génération et construction des réponses
Version corrigée sans doublons
"""

from .generators import EnhancedResponseGenerator, create_enhanced_generator
from .prompt_builder import PromptBuilder

# Note: enhanced_response_generator.py supprimé (doublon)
# Toutes les fonctionnalités sont maintenant dans generators.py

__all__ = [
    "EnhancedResponseGenerator",
    "create_enhanced_generator",
    "PromptBuilder"
]