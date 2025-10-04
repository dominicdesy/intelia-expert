# -*- coding: utf-8 -*-
"""
Generation module - Génération et construction des réponses
Version 3.4 - Simplifié et consolidé
"""

from .generators import EnhancedResponseGenerator, create_enhanced_generator

# Note: prompt_builder.py supprimé - fonctionnalité intégrée dans generators.py
# Note: enhanced_response_generator.py supprimé (doublon)

__all__ = ["EnhancedResponseGenerator", "create_enhanced_generator"]
